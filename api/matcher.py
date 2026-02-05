"""
Hybrid matching algorithm combining historical frequency (70%) and vector similarity (30%).
"""

import logging
import os
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict, Tuple, Optional

from api.database import (
    get_vectors,
    get_all_historical_mappings,
    get_item_by_sku,
    search_vectors,
    search_vectors_batch,
)

# Load .env from project root (not cwd) so BATCH_SIZE is correct regardless of startup dir
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)

OPENAI_MODEL = 'text-embedding-3-small'
HISTORY_WEIGHT = 0.7
VECTOR_WEIGHT = 0.3
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 100))
logger.info(f"Embeddings BATCH_SIZE={BATCH_SIZE} (from env)")


def generate_embedding(text: str) -> np.ndarray:
    """Generate embedding for a single text using OpenAI"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    
    client = OpenAI(api_key=api_key)
    
    response = client.embeddings.create(
        model=OPENAI_MODEL,
        input=text
    )
    
    return np.array(response.data[0].embedding, dtype=np.float32)


def generate_embeddings_batch(texts: List[str]) -> List[Optional[np.ndarray]]:
    """
    Generate embeddings for multiple texts in bulk (one API call per batch).
    Uses BATCH_SIZE from env. Uses raw HTTP to guarantee exactly 1 request per batch
    (OpenAI client may split internally based on token limits).
    Returns list of embeddings (None for failed items), same order as input.
    """
    import httpx

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")

    all_embeddings: List[Optional[np.ndarray]] = []
    num_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(f"Embeddings: {len(texts)} items, BATCH_SIZE={BATCH_SIZE} -> {num_batches} API call(s) to OpenAI")

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        try:
            with httpx.Client(timeout=120.0) as http_client:
                response = http_client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": OPENAI_MODEL,
                        "input": batch,
                        "encoding_format": "float",
                    },
                )
                response.raise_for_status()
                data = response.json()
            embeddings = [
                np.array(item["embedding"], dtype=np.float32)
                for item in sorted(data["data"], key=lambda x: x["index"])
            ]
            all_embeddings.extend(embeddings)
        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch {i // BATCH_SIZE + 1}: {e}")
            all_embeddings.extend([None] * len(batch))

    return all_embeddings


def normalize_frequencies(frequencies: Dict[str, int]) -> Dict[str, float]:
    """Normalize frequency values to 0-1 scale"""
    if not frequencies:
        return {}
    
    max_freq = max(frequencies.values())
    if max_freq == 0:
        return {sku: 0.0 for sku in frequencies.keys()}
    
    return {sku: freq / max_freq for sku, freq in frequencies.items()}


def calculate_hybrid_score(
    requirement_string: str,
    top_k: int = 10,
    query_vector: Optional[np.ndarray] = None,
    vector_results: Optional[List[Tuple[str, float]]] = None,
    _timing: Optional[Dict[str, float]] = None,
) -> List[Tuple[str, float, Dict]]:
    """
    Calculate hybrid scores for all items matching a requirement string.
    Returns list of (sku, final_score, metadata) tuples sorted by score descending.
    
    Args:
        requirement_string: The requirement text to match
        top_k: Number of top results to return
        query_vector: Optional pre-computed embedding (skips API call when provided)
    
    Returns:
        List of tuples: (sku, final_score, {
            'historical_score': float,
            'vector_score': float,
            'historical_frequency': int,
            'vector_similarity': float
        })
    """
    # Step 1: Get historical mappings
    t0 = time.perf_counter() if _timing is not None else None
    historical_mappings = get_all_historical_mappings(requirement_string)
    normalized_history = normalize_frequencies(historical_mappings)
    if _timing is not None:
        _timing["historical_mappings"] = _timing.get("historical_mappings", 0) + (time.perf_counter() - t0) * 1000

    # Step 2: Get embedding - only when we need to run vector search (vector_results not provided)
    if vector_results is None and query_vector is None:
        try:
            query_vector = generate_embedding(requirement_string)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            query_vector = None

    # Step 3: Get vector similarities (use pre-computed or search)
    if vector_results is None:
        vector_results = []
        if query_vector is not None:
            t0 = time.perf_counter() if _timing is not None else None
            try:
                vector_results = search_vectors(query_vector, top_k=top_k * 2)
            except Exception as e:
                logger.error(f"Failed to search vectors: {e}")
            if _timing is not None:
                _timing["vector_search"] = _timing.get("vector_search", 0) + (time.perf_counter() - t0) * 1000
    
    # Step 4: Combine scores
    combined_scores: Dict[str, Dict] = {}
    
    # Add historical scores
    for sku, normalized_freq in normalized_history.items():
        combined_scores[sku] = {
            'historical_score': normalized_freq * HISTORY_WEIGHT,
            'vector_score': 0.0,
            'historical_frequency': historical_mappings.get(sku, 0),
            'vector_similarity': 0.0,
            'final_score': normalized_freq * HISTORY_WEIGHT
        }
    
    # Add vector scores
    for sku, vector_sim in vector_results:
        if sku not in combined_scores:
            combined_scores[sku] = {
                'historical_score': 0.0,
                'vector_score': vector_sim * VECTOR_WEIGHT,
                'historical_frequency': 0,
                'vector_similarity': vector_sim,
                'final_score': vector_sim * VECTOR_WEIGHT
            }
        else:
            # Combine with existing historical score
            combined_scores[sku]['vector_score'] = vector_sim * VECTOR_WEIGHT
            combined_scores[sku]['vector_similarity'] = vector_sim
            combined_scores[sku]['final_score'] = (
                combined_scores[sku]['historical_score'] +
                vector_sim * VECTOR_WEIGHT
            )
    
    # Step 5: Sort by final score and return top K
    sorted_results = sorted(
        combined_scores.items(),
        key=lambda x: x[1]['final_score'],
        reverse=True
    )[:top_k]
    
    # Format results
    results = []
    for sku, metadata in sorted_results:
        results.append((sku, metadata['final_score'], metadata))
    
    return results


def get_suggestions(
    requirement_string: str,
    top_k: int = 3,
    query_vector: Optional[np.ndarray] = None,
    vector_results: Optional[List[Tuple[str, float]]] = None,
    _timing: Optional[Dict[str, float]] = None,
    skip_item_lookup: bool = False,
    items_cache: Optional[Dict[str, Dict]] = None,
) -> List[Dict]:
    """
    Get top-K suggestions for a requirement string.
    Returns list of suggestion dictionaries with all metadata.
    When query_vector is provided, skips embedding generation (use for bulk flow).
    When skip_item_lookup=True or items_cache is provided, skips/uses cache for item details.
    """
    try:
        hybrid_results = calculate_hybrid_score(
            requirement_string,
            top_k=top_k,
            query_vector=query_vector,
            vector_results=vector_results,
            _timing=_timing,
        )

        use_cache = items_cache is not None
        suggestions = []
        t0 = time.perf_counter() if _timing is not None and not (skip_item_lookup or use_cache) else None
        for sku, final_score, metadata in hybrid_results:
            item = items_cache.get(sku) if use_cache else (None if skip_item_lookup else get_item_by_sku(sku))
            if not skip_item_lookup and not use_cache and not item:
                logger.warning(f"Item with SKU {sku} not found in database")
                continue

            suggestion = {
                'sku': sku,
                'item_name': item.get('name', 'Unknown') if item else None,
                'confidence_score': final_score,
                'historical_frequency': metadata['historical_frequency'],
                'vector_similarity': metadata['vector_similarity'],
                'historical_score': metadata['historical_score'],
                'vector_score': metadata['vector_score'],
                'image': item.get('image') if item else None,
                'price': item.get('amt') if item else None,
            }
            suggestions.append(suggestion)
        if t0 is not None and _timing is not None:
            _timing["get_item_by_sku"] = _timing.get("get_item_by_sku", 0) + (time.perf_counter() - t0) * 1000

        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting suggestions for '{requirement_string}': {e}")
        return []
