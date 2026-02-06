"""
Script to load all items and vectors from SQLite into memory (NumPy arrays).
This creates a pickle file that can be loaded quickly by the API on startup.
"""

import os
import sqlite3
import logging
import pickle
import numpy as np
from typing import List, Tuple, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
LOCAL_DB_PATH = os.getenv('LOCAL_DB_PATH', 'local_quotation.db')
VECTORS_CACHE_PATH = os.getenv('VECTORS_CACHE_PATH', 'vectors_cache.pkl')


def load_items_and_vectors(conn: sqlite3.Connection) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Load all items with vectors from SQLite.
    Returns:
        - vectors: NumPy array of shape (num_items, embedding_dim)
        - item_skus: List of SKU strings corresponding to vectors
        - item_names: List of item names corresponding to vectors
    """
    cursor = conn.cursor()
    
    # Fetch all items with vectors and valid SKU
    cursor.execute("""
        SELECT sku, name, name_vector 
        FROM items 
        WHERE name_vector IS NOT NULL 
          AND name_vector != ''
          AND length(name_vector) > 0
          AND sku IS NOT NULL
          AND sku != ''
        ORDER BY sku
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        logger.warning("No items with vectors found in database")
        return np.array([]), [], []
    
    item_skus = []
    item_names = []
    vectors_list = []
    
    for row in rows:
        sku, item_name, vector_blob = row
        
        try:
            # Unpickle the vector
            vector = pickle.loads(vector_blob)
            
            # Ensure it's a NumPy array
            if not isinstance(vector, np.ndarray):
                vector = np.array(vector, dtype=np.float32)
            
            # Validate dimension
            if vector.shape[0] != 1536:
                logger.warning(f"SKU {sku} has incorrect vector dimension: {vector.shape[0]}")
                continue
            
            item_skus.append(sku)
            item_names.append(item_name)
            vectors_list.append(vector)
            
        except Exception as e:
            logger.warning(f"Failed to load vector for SKU {sku}: {e}")
            continue
    
    if not vectors_list:
        logger.error("No valid vectors found")
        return np.array([]), [], []
    
    # Convert to NumPy array
    vectors_array = np.array(vectors_list, dtype=np.float32)
    
    logger.info(f"Loaded {len(item_skus)} items with vectors")
    logger.info(f"Vector array shape: {vectors_array.shape}")
    
    return vectors_array, item_skus, item_names


def save_cache(vectors: np.ndarray, item_skus: List[str], item_names: List[str]):
    """Save vectors cache to pickle file"""
    cache_data = {
        'vectors': vectors,
        'item_skus': item_skus,
        'item_names': item_names,
        'num_items': len(item_skus),
        'embedding_dim': vectors.shape[1] if len(vectors) > 0 else 1536
    }
    
    with open(VECTORS_CACHE_PATH, 'wb') as f:
        pickle.dump(cache_data, f)
    
    logger.info(f"Saved vectors cache to {VECTORS_CACHE_PATH}")
    logger.info(f"Cache size: {len(item_skus)} items, {vectors.shape[1]} dimensions")


def load_cache() -> Tuple[np.ndarray, List[str], List[str]]:
    """Load vectors cache from pickle file"""
    if not os.path.exists(VECTORS_CACHE_PATH):
        raise FileNotFoundError(f"Cache file not found: {VECTORS_CACHE_PATH}")
    
    with open(VECTORS_CACHE_PATH, 'rb') as f:
        cache_data = pickle.load(f)
    
    logger.info(f"Loaded vectors cache from {VECTORS_CACHE_PATH}")
    logger.info(f"Cache contains {cache_data['num_items']} items")
    
    # Handle backward compatibility (old cache might have item_ids)
    if 'item_skus' in cache_data:
        return cache_data['vectors'], cache_data['item_skus'], cache_data['item_names']
    else:
        # Old format - need to regenerate
        raise ValueError("Cache file uses old format. Please regenerate vectors cache.")


def run_rebuild_cache():
    """
    Load vectors from SQLite and rebuild vectors_cache.pkl.
    Callable from other scripts (e.g. 1_setup.py, 2_update_items.py).
    """
    conn = None
    try:
        conn = connect_sqlite()

        logger.info("=" * 60)
        logger.info("Loading items and vectors from database...")
        logger.info("=" * 60)

        vectors, item_skus, item_names = load_items_and_vectors(conn)

        if len(item_skus) == 0:
            raise ValueError("No vectors found. Please run generate_vectors.py first.")

        logger.info("=" * 60)
        logger.info("Saving vectors cache...")
        logger.info("=" * 60)

        save_cache(vectors, item_skus, item_names)

        logger.info("=" * 60)
        logger.info("Vector cache rebuild complete!")
        logger.info(f"Ready to use {len(item_skus)} items for matching")
        logger.info("=" * 60)

    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")


def connect_sqlite():
    """Create SQLite connection"""
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        logger.info(f"Connected to SQLite database: {LOCAL_DB_PATH}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQLite database: {e}")
        raise


def main():
    """Main function to load vectors and create cache"""
    try:
        run_rebuild_cache()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
