"""
Database connection and query functions for SQLite.
Handles in-memory vector loading and search operations.
"""

import os
import sqlite3
import logging
import pickle
import numpy as np
from typing import List, Tuple, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LOCAL_DB_PATH = os.getenv('LOCAL_DB_PATH', 'local_quotation.db')
VECTORS_CACHE_PATH = os.getenv('VECTORS_CACHE_PATH', 'vectors_cache.pkl')

# Global in-memory cache
_vectors_cache: Optional[np.ndarray] = None
_item_skus: Optional[List[str]] = None
_item_names: Optional[List[str]] = None
_item_sku_to_index: Optional[Dict[str, int]] = None


def get_db_connection() -> sqlite3.Connection:
    """Get SQLite database connection"""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_vectors_to_memory():
    """Load vectors cache into memory on startup"""
    global _vectors_cache, _item_skus, _item_names, _item_sku_to_index
    
    try:
        if not os.path.exists(VECTORS_CACHE_PATH):
            logger.warning(f"Vectors cache not found at {VECTORS_CACHE_PATH}")
            logger.warning("Please run scripts/load_vectors_to_memory.py first")
            return
        
        with open(VECTORS_CACHE_PATH, 'rb') as f:
            cache_data = pickle.load(f)
        
        _vectors_cache = cache_data['vectors']
        # Handle backward compatibility
        if 'item_skus' in cache_data:
            _item_skus = cache_data['item_skus']
        else:
            # Old format - need to regenerate
            raise ValueError("Cache file uses old format. Please regenerate vectors cache by running scripts/load_vectors_to_memory.py")
        _item_names = cache_data['item_names']
        
        # Create mapping from SKU to index for fast lookup
        _item_sku_to_index = {sku: idx for idx, sku in enumerate(_item_skus)}
        
        logger.info(f"Loaded {len(_item_skus)} items with vectors into memory")
        logger.info(f"Vector array shape: {_vectors_cache.shape}")
        
    except Exception as e:
        logger.error(f"Failed to load vectors cache: {e}")
        raise


def get_vectors() -> Tuple[np.ndarray, List[str], List[str]]:
    """Get in-memory vectors, item SKUs, and names"""
    if _vectors_cache is None:
        raise RuntimeError("Vectors not loaded. Call load_vectors_to_memory() first.")
    return _vectors_cache, _item_skus, _item_names


def get_item_by_sku(sku: str) -> Optional[Dict]:
    """Get item details by SKU"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items WHERE sku = ?", (sku,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_items_by_skus(skus: List[str]) -> Dict[str, Dict]:
    """Batch get item details by SKUs. Returns {sku: item_dict}. Uses single query."""
    if not skus:
        return {}
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(skus))
        cursor.execute(f"SELECT * FROM items WHERE sku IN ({placeholders})", skus)
        return {dict(row)["sku"]: dict(row) for row in cursor.fetchall()}
    finally:
        conn.close()


def get_historical_frequency(requirement_string: str, sku: str) -> int:
    """Get historical frequency for a requirement_string -> sku mapping"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT frequency 
            FROM sku_mapping_history 
            WHERE requirement_string = ? AND sku = ?
        """, (requirement_string, sku))
        
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def get_all_historical_mappings(requirement_string: str) -> Dict[str, int]:
    """Get all historical mappings for a requirement string"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sku, frequency 
            FROM sku_mapping_history 
            WHERE requirement_string = ?
        """, (requirement_string,))
        
        return {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


def get_quote_history(sku: str, limit: int = 3) -> List[Dict]:
    """Get last N quote history entries for a SKU from tables_data"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT * 
            FROM tables_data 
            WHERE sku = ?
            ORDER BY id DESC
            LIMIT ?
        """
        cursor.execute(query, (sku, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_quote_history_bulk(skus: List[str], limit_per_sku: int = 3) -> Dict[str, List[Dict]]:
    """Batch get quote history for multiple SKUs. Returns {sku: [quote1, quote2, ...]}."""
    if not skus:
        return {}
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(skus))
        cursor.execute(
            f"""
            SELECT * FROM tables_data 
            WHERE sku IN ({placeholders})
            ORDER BY sku, id DESC
            """,
            skus,
        )
        rows = cursor.fetchall()
        # Group by SKU, keep only first limit_per_sku per SKU
        result: Dict[str, List[Dict]] = {sku: [] for sku in skus}
        for row in rows:
            d = dict(row)
            sku = d["sku"]
            if len(result[sku]) < limit_per_sku:
                result[sku].append(d)
        return result
    finally:
        conn.close()


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def search_vectors(query_vector: np.ndarray, top_k: int = 3) -> List[Tuple[str, float]]:
    """
    Search for most similar vectors using cosine similarity.
    Returns list of (sku, similarity_score) tuples.
    """
    if _vectors_cache is None:
        raise RuntimeError("Vectors not loaded")

    # Calculate cosine similarities
    similarities = np.dot(_vectors_cache, query_vector) / (
        np.linalg.norm(_vectors_cache, axis=1) * np.linalg.norm(query_vector)
    )

    # Get top K indices
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Return SKU strings and scores
    results = []
    for idx in top_indices:
        sku = _item_skus[idx]
        score = float(similarities[idx])
        results.append((sku, score))

    return results


def search_vectors_batch(
    query_vectors: np.ndarray, top_k: int = 6
) -> List[List[Tuple[str, float]]]:
    """
    Batch search for similar vectors. Single matrix multiply for all queries.
    query_vectors: (num_queries, embedding_dim)
    Returns list of results, one per query: [[(sku, score), ...], ...]
    """
    if _vectors_cache is None:
        raise RuntimeError("Vectors not loaded")
    if len(query_vectors) == 0:
        return []

    # Normalize cache and queries for cosine similarity
    cache_norms = np.linalg.norm(_vectors_cache, axis=1, keepdims=True)
    cache_norms[cache_norms == 0] = 1e-10
    query_norms = np.linalg.norm(query_vectors, axis=1, keepdims=True)
    query_norms[query_norms == 0] = 1e-10

    # similarities[i, j] = similarity of query i to catalog item j
    similarities = np.dot(query_vectors, _vectors_cache.T) / (
        query_norms * cache_norms.T
    )

    results = []
    for i in range(len(query_vectors)):
        top_indices = np.argsort(similarities[i])[::-1][:top_k]
        results.append([
            (_item_skus[idx], float(similarities[i, idx]))
            for idx in top_indices
        ])
    return results
