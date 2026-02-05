"""
Structured extraction using OpenAI GPT-4o.
Converts unstructured OCR text into structured line items.
"""

import os
import logging
import json
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

from api.models import LineItem

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_MODEL = 'gpt-4o'


def extract_line_items(text: str) -> List[LineItem]:
    """
    Extract structured line items from unstructured text using GPT-4o.
    Returns list of LineItem objects.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found")
    
    client = OpenAI(api_key=api_key)
    
    # Create prompt for structured extraction
    prompt = f"""Extract line items from the following text. Identify product descriptions, quantities, and units.

Text to process:
{text}

Extract all line items and return them as a JSON array. Each item should have:
- text: The original text line
- description: Cleaned product/requirement description
- quantity: Numeric quantity if mentioned (or null)
- unit: Unit of measurement if mentioned (or null)

Return only valid JSON array, no additional text. Example format:
[
  {{
    "text": "Test Tube 10ml - 50 pieces",
    "description": "Test Tube 10ml",
    "quantity": 50,
    "unit": "pieces"
  }},
  {{
    "text": "Beaker 100ml",
    "description": "Beaker 100ml",
    "quantity": null,
    "unit": null
  }}
]
"""
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured data from unstructured text. Always return valid JSON arrays."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )
        
        # Parse response
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from response
        try:
            # Try parsing as JSON directly
            parsed = json.loads(content)
            if isinstance(parsed, list):
                items_data = parsed
            elif isinstance(parsed, dict) and 'items' in parsed:
                items_data = parsed['items']
            else:
                items_data = []
        except json.JSONDecodeError:
            # Try to extract JSON array from text (might be wrapped in markdown or text)
            import re
            # Look for JSON array pattern
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                try:
                    items_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error(f"Could not parse JSON array from response: {content}")
                    return []
            else:
                logger.error(f"Could not find JSON array in response: {content}")
                return []
        
        # Convert to LineItem objects
        line_items = []
        for idx, item_data in enumerate(items_data):
            try:
                line_item = LineItem(
                    id=idx + 1,
                    text=item_data.get('text', ''),
                    description=item_data.get('description', item_data.get('text', '')),
                    quantity=item_data.get('quantity'),
                    unit=item_data.get('unit')
                )
                line_items.append(line_item)
            except Exception as e:
                logger.warning(f"Failed to parse line item {idx}: {e}")
                continue
        
        logger.info(f"Extracted {len(line_items)} line items from text")
        return line_items
        
    except Exception as e:
        logger.error(f"Error extracting line items: {e}")
        # Fallback: create a single line item from the text
        return [LineItem(
            id=1,
            text=text[:200],  # Truncate if too long
            description=text[:200],
            quantity=None,
            unit=None
        )]


def clean_and_filter_line_items(line_items: List[LineItem]) -> List[LineItem]:
    """
    Clean and filter extracted line items.
    Remove empty items, normalize descriptions, etc.
    """
    cleaned = []
    
    for item in line_items:
        # Skip empty descriptions
        if not item.description or not item.description.strip():
            continue
        
        # Normalize description (remove extra whitespace)
        item.description = ' '.join(item.description.split())
        item.text = ' '.join(item.text.split())
        
        cleaned.append(item)
    
    logger.info(f"Filtered to {len(cleaned)} valid line items")
    return cleaned
