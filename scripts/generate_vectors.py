"""
Script to generate embeddings for all items in the local SQLite database.
Uses OpenAI text-embedding-3-small to generate vectors and stores them in SQLite.
Supports parallel processing with configurable number of workers for faster generation.
"""

import os
import sqlite3
import logging
import pickle
import numpy as np
from typing import List, Tuple, Optional
from dotenv import load_dotenv
import openai
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 100))
NUM_WORKERS = int(os.getenv('NUM_WORKERS', 5))
OPENAI_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536
OVERWRITE_EXISTING = os.getenv('OVERWRITE_EXISTING_VECTORS', 'true').lower() == 'true'

# Thread-safe counters
success_counter = {'count': 0}
failed_counter = {'count': 0}
lock = threading.Lock()


def connect_sqlite():
    """Create SQLite connection (thread-safe with timeout)"""
    try:
        # Use check_same_thread=False for thread safety
        # Each thread gets its own connection
        # Add timeout to handle database locks gracefully
        conn = sqlite3.connect(
            LOCAL_DB_PATH,
            check_same_thread=False,
            timeout=30.0  # 30 second timeout for database operations
        )
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        # Set busy timeout to wait for locks
        conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQLite database: {e}")
        raise


def fetch_items_without_vectors(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    """
    Fetch all items that need vectors.
    If OVERWRITE_EXISTING is True, fetches all items. Otherwise, only items without vectors.
    Returns list of tuples: (sku, name)
    """
    cursor = conn.cursor()
    
    if OVERWRITE_EXISTING:
        # Fetch all items with valid SKU (will overwrite existing vectors)
        cursor.execute("""
            SELECT sku, name 
            FROM items 
            WHERE sku IS NOT NULL
              AND sku != ''
            ORDER BY sku
        """)
        logger.info("Overwrite mode: Will regenerate vectors for all items")
    else:
        # Only fetch items without vectors
        cursor.execute("""
            SELECT sku, name 
            FROM items 
            WHERE (name_vector IS NULL 
               OR name_vector = ''
               OR length(name_vector) = 0)
              AND sku IS NOT NULL
              AND sku != ''
            ORDER BY sku
        """)
        logger.info("Incremental mode: Will only process items without vectors")
    
    items = cursor.fetchall()
    logger.info(f"Found {len(items)} items to process")
    return items


def generate_embeddings_batch(
    client: OpenAI,
    item_names: List[str]
) -> List[Optional[List[float]]]:
    """
    Generate embeddings for a batch of item names using OpenAI.
    Returns list of embeddings (or None for failed items).
    """
    try:
        response = client.embeddings.create(
            model=OPENAI_MODEL,
            input=item_names
        )
        embeddings = [item.embedding for item in response.data]
        return embeddings
    except Exception as e:
        logger.error(f"Failed to generate embeddings for batch: {e}")
        return [None] * len(item_names)


def update_vector(
    conn: sqlite3.Connection,
    sku: str,
    embedding: List[float],
    retries: int = 5
) -> bool:
    """
    Update name_vector column for a single item by SKU.
    Stores as pickled NumPy array in BLOB format.
    Includes retry logic for database locks with exponential backoff.
    Returns True if successful, False otherwise.
    """
    for attempt in range(retries):
        try:
            # Convert to NumPy array and pickle
            embedding_array = np.array(embedding, dtype=np.float32)
            vector_blob = pickle.dumps(embedding_array)
            
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE items 
                SET name_vector = ? 
                WHERE sku = ?
            """, (vector_blob, sku))
            
            # Don't commit here - let the batch commit handle it
            return True
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and attempt < retries - 1:
                # Database is locked, wait and retry with exponential backoff
                import time
                wait_time = min((attempt + 1) * 0.2, 2.0)  # Max 2 seconds
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"Failed to update vector for SKU {sku} after {retries} attempts: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to update vector for SKU {sku}: {e}")
            return False
    
    return False


def process_batch_worker(
    batch_items: List[Tuple[str, str]],
    batch_num: int,
    total_batches: int,
    api_key: str
) -> Tuple[int, int]:
    """
    Process a batch of items in a worker thread.
    Returns tuple: (success_count, failed_count)
    """
    # Create separate database connection for this worker
    conn = connect_sqlite()
    client = None
    
    try:
        # Initialize OpenAI client for this worker
        try:
            client = OpenAI(api_key=api_key)
        except TypeError as e:
            if 'proxies' in str(e):
                os.environ['OPENAI_API_KEY'] = api_key
                client = openai.OpenAI()
            else:
                raise
        
        item_skus = [item[0] for item in batch_items]
        item_names = [item[1] for item in batch_items]
        
        # Generate embeddings
        embeddings = generate_embeddings_batch(client, item_names)
        
        # Update database (batch updates to reduce lock contention)
        success_count = 0
        failed_count = 0
        
        # Process embeddings and update database
        # Use batch transaction to reduce lock contention
        try:
            for sku, embedding in zip(item_skus, embeddings):
                if embedding is None:
                    failed_count += 1
                    logger.warning(f"[Worker] Failed to generate embedding for SKU {sku}")
                    continue
                
                if update_vector(conn, sku, embedding):
                    success_count += 1
                else:
                    failed_count += 1
            
            # Commit all updates in this batch at once
            conn.commit()
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                logger.warning(f"[Worker] Database locked during commit, retrying...")
                import time
                time.sleep(0.5)
                try:
                    conn.commit()
                except Exception as retry_error:
                    logger.error(f"[Worker] Failed to commit after retry: {retry_error}")
                    conn.rollback()
            else:
                logger.error(f"[Worker] Error updating vectors: {e}")
                conn.rollback()
        except Exception as e:
            logger.error(f"[Worker] Error updating vectors: {e}")
            conn.rollback()
            raise
        
        # Small delay to reduce database lock contention between batches
        import time
        time.sleep(0.1)  # 100ms delay between batches to reduce lock contention
        
        # Update global counters thread-safely
        with lock:
            success_counter['count'] += success_count
            failed_counter['count'] += failed_count
        
        logger.info(
            f"[Batch {batch_num}/{total_batches}] Processed {len(batch_items)} items - "
            f"Success: {success_count}, Failed: {failed_count}"
        )
        
        return success_count, failed_count
        
    except Exception as e:
        logger.error(f"[Worker] Error processing batch {batch_num}: {e}")
        return 0, len(batch_items)
    finally:
        if conn:
            conn.close()


def main():
    """Main function to orchestrate the embedding generation process with parallel processing"""
    try:
        # Initialize OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Connect to database (main connection for fetching items)
        conn = connect_sqlite()
        
        try:
            # Fetch all items needing embeddings
            items = fetch_items_without_vectors(conn)
            
            if not items:
                logger.info("No items need embeddings. All items are up to date.")
                return
            
            # Reset counters
            success_counter['count'] = 0
            failed_counter['count'] = 0
            
            # Prepare batches
            total_items = len(items)
            batches = []
            for i in range(0, total_items, BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                batches.append((batch, batch_num))
            
            total_batches = len(batches)
            
            logger.info("=" * 60)
            logger.info(f"Starting parallel processing with {NUM_WORKERS} workers")
            logger.info(f"Total items: {total_items}")
            logger.info(f"Batch size: {BATCH_SIZE}")
            logger.info(f"Total batches: {total_batches}")
            logger.info(f"Overwrite existing vectors: {OVERWRITE_EXISTING}")
            logger.info("=" * 60)
            
            # Process batches in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
                # Submit all batches to workers
                future_to_batch = {
                    executor.submit(
                        process_batch_worker,
                        batch_items,
                        batch_num,
                        total_batches,
                        api_key
                    ): batch_num
                    for batch_items, batch_num in batches
                }
                
                # Process completed batches
                completed = 0
                for future in as_completed(future_to_batch):
                    batch_num = future_to_batch[future]
                    try:
                        success, failed = future.result()
                        completed += 1
                        
                        # Show progress
                        progress = (completed / total_batches) * 100
                        logger.info(
                            f"Progress: {completed}/{total_batches} batches ({progress:.1f}%) - "
                            f"Total Success: {success_counter['count']}, "
                            f"Total Failed: {failed_counter['count']}"
                        )
                    except Exception as e:
                        logger.error(f"Batch {batch_num} generated an exception: {e}")
            
            # Final summary
            logger.info("=" * 60)
            logger.info("Embedding generation complete!")
            logger.info(f"Total items processed: {total_items}")
            logger.info(f"Successful: {success_counter['count']}")
            logger.info(f"Failed: {failed_counter['count']}")
            logger.info(f"Workers used: {NUM_WORKERS}")
            logger.info("=" * 60)
            
        finally:
            conn.close()
            logger.info("Database connection closed")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
