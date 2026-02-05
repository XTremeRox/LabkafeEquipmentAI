"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class UploadResponse(BaseModel):
    """Response after file upload"""
    file_id: str
    filename: str
    file_type: str
    message: str


class LineItem(BaseModel):
    """Represents a single line item from extracted data"""
    id: Optional[int] = None
    text: str = Field(..., description="Original text from document")
    quantity: Optional[float] = None
    unit: Optional[str] = None
    description: str = Field(..., description="Cleaned requirement description")


class LineItemEdit(BaseModel):
    """Line item with user edits"""
    id: Optional[int] = None
    text: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    description: str


class ExtractRequest(BaseModel):
    """Request to extract line items from uploaded file"""
    file_id: str


class ExtractResponse(BaseModel):
    """Response with extracted line items"""
    line_items: List[LineItem]
    raw_text: Optional[str] = None


class QuoteHistoryItem(BaseModel):
    """Single quote history entry"""
    date: str
    customer: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    quote_id: Optional[int] = None


class Suggestion(BaseModel):
    """Single suggestion for a line item"""
    sku: str
    item_name: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    historical_frequency: Optional[int] = None
    vector_similarity: Optional[float] = None
    image: Optional[str] = None
    price: Optional[float] = None
    last_3_quotes: List[QuoteHistoryItem] = []


class SuggestRequest(BaseModel):
    """Request for suggestions"""
    line_items: List[LineItemEdit]


class SuggestResponse(BaseModel):
    """Response with suggestions for each line item"""
    suggestions: Dict[int, List[Suggestion]] = Field(
        ..., 
        description="Map of line_item_id to list of top-3 suggestions"
    )


class QuoteHistoryRequest(BaseModel):
    """Request for quote history"""
    sku: str
    limit: int = Field(default=3, ge=1, le=10)


class QuoteHistoryResponse(BaseModel):
    """Response with quote history"""
    sku: str
    quotes: List[QuoteHistoryItem]


class SubmitRequest(BaseModel):
    """Final submission request"""
    line_items: List[LineItemEdit]
    selected_mappings: Dict[int, str] = Field(
        ..., 
        description="Map of line_item_id to selected sku"
    )


class SubmitResponse(BaseModel):
    """Response after submission"""
    success: bool
    message: str
    # TODO: Update sku_mapping_history with frequencies
