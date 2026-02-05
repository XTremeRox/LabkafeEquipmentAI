"""
FastAPI routes for quotation processing endpoints.
"""

import os
import uuid
import logging
import time
import json
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from fastapi.responses import JSONResponse
from typing import Dict

from api.models import (
    UploadResponse,
    ExtractRequest,
    ExtractResponse,
    LineItem,
    LineItemEdit,
    SuggestRequest,
    SuggestResponse,
    Suggestion,
    QuoteHistoryRequest,
    QuoteHistoryResponse,
    QuoteHistoryItem,
    SubmitRequest,
    SubmitResponse
)
from api.ocr import process_file
from api.extractor import extract_line_items, clean_and_filter_line_items
from api.matcher import get_suggestions, generate_embeddings_batch
from api.database import search_vectors_batch
from api.database import get_quote_history, get_items_by_skus, get_quote_history_bulk

logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary file storage (in production, use proper file storage)
UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory storage for uploaded files and extracted data
_file_storage: Dict[str, Dict] = {}


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file (image, PDF, Excel, Word) for processing.
    Returns file_id for subsequent operations.
    """
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Store file metadata
        _file_storage[file_id] = {
            'filename': file.filename,
            'file_path': file_path,
            'file_type': None,
            'extracted_text': None,
            'line_items': None
        }
        
        logger.info(f"Uploaded file: {file.filename} with ID: {file_id}")
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_type="unknown",
            message="File uploaded successfully"
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.post("/extract", response_model=ExtractResponse)
async def extract_items(request: ExtractRequest):
    """
    Extract structured line items from uploaded file.
    Performs OCR (if needed) and structured extraction.
    """
    try:
        if request.file_id not in _file_storage:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = _file_storage[request.file_id]
        file_path = file_info['file_path']
        filename = file_info['filename']
        
        # Process file (OCR/extract text)
        logger.info(f"Processing file: {filename}")
        extracted_text, file_type = process_file(file_path, filename)
        
        # Update file info
        file_info['file_type'] = file_type
        file_info['extracted_text'] = extracted_text
        
        # Extract structured line items
        logger.info("Extracting structured line items...")
        line_items = extract_line_items(extracted_text)
        line_items = clean_and_filter_line_items(line_items)
        
        # Update file info
        file_info['line_items'] = [item.dict() for item in line_items]
        
        logger.info(f"Extracted {len(line_items)} line items")
        
        return ExtractResponse(
            line_items=line_items,
            raw_text=extracted_text[:1000]  # Return first 1000 chars as preview
        )
        
    except Exception as e:
        logger.error(f"Error extracting items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract items: {str(e)}")


@router.post("/suggest", response_model=SuggestResponse)
async def get_suggestions_for_items(request: SuggestRequest, response: Response):
    """
    Get top-3 suggestions for each line item using hybrid matching.
    Generates embeddings in bulk (BATCH_SIZE from env) like generate_vectors.py.
    Timing breakdown is logged and returned in X-Suggest-Timing response header.
    """
    t_start = time.perf_counter()
    timing = {"steps": {}, "total_ms": 0}

    try:
        suggestions_dict = {}

        # Collect (line_item, requirement) pairs
        t0 = time.perf_counter()
        items_to_process = []
        for line_item in request.line_items:
            requirement = line_item.description or line_item.text
            if not requirement or not requirement.strip():
                continue
            items_to_process.append((line_item, requirement.strip()))
        timing["steps"]["collect_items"] = round((time.perf_counter() - t0) * 1000, 1)

        # Batch generate embeddings
        t0 = time.perf_counter()
        all_requirements = [req for _, req in items_to_process]
        all_embeddings = generate_embeddings_batch(all_requirements)
        timing["steps"]["embeddings_api"] = round((time.perf_counter() - t0) * 1000, 1)

        # Batch vector search (single matrix multiply for all queries)
        t0 = time.perf_counter()
        valid_embeddings = [e for e in all_embeddings if e is not None]
        if valid_embeddings:
            valid_arr = np.stack(valid_embeddings)
            batch_vector_results = search_vectors_batch(valid_arr, top_k=6)
        else:
            batch_vector_results = []
        # Map back to per-item: None embedding -> empty list
        vidx = 0
        vector_results_per_item = []
        for emb in all_embeddings:
            if emb is not None:
                vector_results_per_item.append(batch_vector_results[vidx])
                vidx += 1
            else:
                vector_results_per_item.append([])
        t_vector_batch = (time.perf_counter() - t0) * 1000

        # Get suggestions for each item (use pre-computed vector results)
        matcher_timing = {}
        all_suggestion_lists = []
        for (line_item, requirement), vec_results in zip(items_to_process, vector_results_per_item):
            suggestion_list = get_suggestions(
                requirement,
                top_k=3,
                vector_results=vec_results,
                _timing=matcher_timing,
                skip_item_lookup=True,
            )
            all_suggestion_lists.append((line_item, suggestion_list))

        # Batch fetch items and quote history (single query each)
        t0 = time.perf_counter()
        all_skus = [
            s["sku"]
            for _, sugg_list in all_suggestion_lists
            for s in sugg_list
        ]
        items_cache = get_items_by_skus(all_skus) if all_skus else {}
        quote_cache = get_quote_history_bulk(all_skus, limit_per_sku=3) if all_skus else {}
        t_batch_db = (time.perf_counter() - t0) * 1000

        # Enrich suggestions with item details and quote history
        for line_item, suggestion_list in all_suggestion_lists:
            formatted_suggestions = []
            for sugg in suggestion_list:
                item = items_cache.get(sugg["sku"], {})
                quote_history = quote_cache.get(sugg["sku"], [])
                quote_items = [
                    QuoteHistoryItem(
                        date=str(q.get("date", q.get("created_at", ""))),
                        customer=q.get("customer", q.get("customer_name")),
                        quantity=q.get("quantity"),
                        price=q.get("price", q.get("unit_price")),
                        quote_id=q.get("id"),
                    )
                    for q in quote_history
                ]
                formatted_suggestions.append(Suggestion(
                    sku=sugg["sku"],
                    item_name=item.get("name", sugg.get("item_name") or "Unknown"),
                    confidence_score=sugg["confidence_score"],
                    historical_frequency=sugg.get("historical_frequency"),
                    vector_similarity=sugg.get("vector_similarity"),
                    image=item.get("image"),
                    price=item.get("amt"),
                    last_3_quotes=quote_items,
                ))
            item_id = line_item.id if line_item.id else hash(line_item.description)
            suggestions_dict[item_id] = formatted_suggestions

        timing["steps"]["matching"] = round(
            matcher_timing.get("historical_mappings", 0)
            + t_vector_batch
            + matcher_timing.get("vector_search", 0)
            + matcher_timing.get("get_item_by_sku", 0),
            1,
        )
        timing["steps"]["quote_history"] = 0  # Now part of batch_db
        timing["steps"]["batch_db"] = round(t_batch_db, 1)
        # Sub-breakdown for matching (helps identify DB vs compute bottlenecks)
        if matcher_timing:
            detail = {k: round(v, 1) for k, v in matcher_timing.items()}
            detail["vector_search_batch"] = round(t_vector_batch, 1)
            timing["steps"]["_matching_detail"] = detail
        timing["total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
        timing["items_count"] = len(items_to_process)

        response.headers["X-Suggest-Timing"] = json.dumps(timing)
        detail = timing["steps"].get("_matching_detail", {})
        h = detail.get("historical_mappings") or 0
        v = detail.get("vector_search_batch") or detail.get("vector_search") or 0
        logger.info(
            f"Suggest completed in {timing['total_ms']}ms for {timing['items_count']} items | "
            f"embeddings: {timing['steps'].get('embeddings_api', 0)}ms, "
            f"matching: {timing['steps'].get('matching', 0)}ms (history:{h:.0f} vector:{v:.0f}), "
            f"batch_db: {timing['steps'].get('batch_db', 0)}ms"
        )
        return SuggestResponse(suggestions=suggestions_dict)
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.post("/quote-history", response_model=QuoteHistoryResponse)
async def get_quote_history_for_sku(request: QuoteHistoryRequest):
    """
    Get quote history (last N quotations) for a specific SKU.
    """
    try:
        quotes = get_quote_history(request.sku_id, limit=request.limit)
        
        quote_items = []
        for quote in quotes:
            quote_items.append(QuoteHistoryItem(
                date=str(quote.get('date', quote.get('created_at', ''))),
                customer=quote.get('customer', quote.get('customer_name')),
                quantity=quote.get('quantity'),
                price=quote.get('price', quote.get('unit_price')),
                quote_id=quote.get('id')
            ))
        
        return QuoteHistoryResponse(
            sku_id=request.sku_id,
            quotes=quote_items
        )
        
    except Exception as e:
        logger.error(f"Error getting quote history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quote history: {str(e)}")


@router.post("/submit", response_model=SubmitResponse)
async def submit_quotation(request: SubmitRequest):
    """
    Final submission of quotation.
    TODO: Update sku_mapping_history with frequencies for learning.
    """
    try:
        # Validate that all line items have mappings
        for line_item in request.line_items:
            item_id = line_item.id if line_item.id else hash(line_item.description)
            if item_id not in request.selected_mappings:
                logger.warning(f"Line item {item_id} has no selected mapping")
        
        # TODO: Update sku_mapping_history table
        # For each line_item -> sku_id mapping:
        #   1. Get requirement_string from line_item.description
        #   2. Check if mapping exists in sku_mapping_history
        #   3. If exists, increment frequency
        #   4. If not exists, insert new record with frequency=1
        #   5. Update last_updated timestamp
        
        logger.info("Quotation submitted successfully")
        logger.info("TODO: Implement learning mechanism to update sku_mapping_history")
        
        return SubmitResponse(
            success=True,
            message="Quotation submitted successfully. Learning mechanism pending implementation."
        )
        
    except Exception as e:
        logger.error(f"Error submitting quotation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit quotation: {str(e)}")
