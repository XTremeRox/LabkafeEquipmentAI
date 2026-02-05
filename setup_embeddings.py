"""
Setup script to generate embeddings for all items in the database.
Connects to DigitalOcean Managed PostgreSQL, fetches item names,
generates embeddings using OpenAI text-embedding-3-small, and updates
the items.name_vector column.
"""

import asyncio
import os
import logging
from typing import List, Tuple, Optional
from dotenv import load_dotenv
import asyncpg
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 100))
OPENAI_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536


async def connect_db() -> asyncpg.Connection:
    """Create async database connection using credentials from .env"""
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def fetch_all_items(conn: asyncpg.Connection) -> List[Tuple[int, str]]:
    """
    Fetch all items with NULL or empty name_vector.
    Returns list of tuples: (id, name)
    """
    try:
        query = """
            SELECT id, name 
            FROM items 
            WHERE name_vector IS NULL 
               OR name_vector = '[]'::vector
               OR array_length(name_vector::float[], 1) IS NULL
            ORDER BY id
        """
        rows = await conn.fetch(query)
        items = [(row['id'], row['name']) for row in rows]
        logger.info(f"Fetched {len(items)} items needing embeddings")
        return items
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        raise


async def generate_embeddings_batch(
    client: AsyncOpenAI,
    item_names: List[str]
) -> List[Optional[List[float]]]:
    """
    Generate embeddings for a batch of item names using OpenAI.
    Returns list of embeddings (or None for failed items).
    """
    try:
        response = await client.embeddings.create(
            model=OPENAI_MODEL,
            input=item_names
        )
        embeddings = [item.embedding for item in response.data]
        logger.info(f"Generated {len(embeddings)} embeddings for batch")
        return embeddings
    except Exception as e:
        logger.error(f"Failed to generate embeddings for batch: {e}")
        return [None] * len(item_names)


async def update_vectors(
    conn: asyncpg.Connection,
    item_id: int,
    embedding: List[float]
) -> bool:
    """
    Update name_vector column for a single item.
    Returns True if successful, False otherwise.
    """
    try:
        # Convert list to PostgreSQL vector format
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        query = """
            UPDATE items 
            SET name_vector = $1::vector 
            WHERE id = $2
        """
        await conn.execute(query, embedding_str, item_id)
        return True
    except Exception as e:
        logger.error(f"Failed to update vector for item {item_id}: {e}")
        return False


async def process_batch(
    conn: asyncpg.Connection,
    client: AsyncOpenAI,
    batch_items: List[Tuple[int, str]]
) -> Tuple[int, int]:
    """
    Process a batch of items: generate embeddings and update database.
    Returns tuple: (success_count, failed_count)
    """
    item_ids = [item[0] for item in batch_items]
    item_names = [item[1] for item in batch_items]
    
    # Generate embeddings
    embeddings = await generate_embeddings_batch(client, item_names)
    
    # Update database
    success_count = 0
    failed_count = 0
    
    for item_id, embedding in zip(item_ids, embeddings):
        if embedding is None:
            failed_count += 1
            logger.warning(f"Failed to generate embedding for item {item_id}")
            continue
        
        if await update_vectors(conn, item_id, embedding):
            success_count += 1
        else:
            failed_count += 1
    
    return success_count, failed_count


async def main():
    """Main function to orchestrate the embedding generation process"""
    conn = None
    try:
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Connect to database
        conn = await connect_db()
        
        # Fetch all items needing embeddings
        items = await fetch_all_items(conn)
        
        if not items:
            logger.info("No items need embeddings. All items are up to date.")
            return
        
        # Process items in batches
        total_items = len(items)
        total_success = 0
        total_failed = 0
        
        logger.info(f"Starting to process {total_items} items in batches of {BATCH_SIZE}")
        
        for i in range(0, total_items, BATCH_SIZE):
            batch = items[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (total_items + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            success, failed = await process_batch(conn, client, batch)
            total_success += success
            total_failed += failed
            
            # Show progress
            processed = min(i + BATCH_SIZE, total_items)
            progress = (processed / total_items) * 100
            logger.info(
                f"Progress: {processed}/{total_items} ({progress:.1f}%) - "
                f"Success: {total_success}, Failed: {total_failed}"
            )
        
        # Final summary
        logger.info("=" * 60)
        logger.info("Embedding generation complete!")
        logger.info(f"Total items processed: {total_items}")
        logger.info(f"Successful: {total_success}")
        logger.info(f"Failed: {total_failed}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise
    finally:
        if conn:
            await conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())
