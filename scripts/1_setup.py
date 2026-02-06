"""
First-time setup: clone database, create SKU mapping history, generate vectors, build cache.
Orchestrates clone_database, create_sku_mapping_history, generate_vectors, load_vectors_to_memory.
"""

import logging
import sys
import os

# Ensure scripts directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from clone_database import run_clone
from create_sku_mapping_history import main as run_create_sku_mapping_history
from generate_vectors import run_generate_vectors
from load_vectors_to_memory import run_rebuild_cache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_setup():
    """
    Full first-time setup:
    1. Clone items + tables_data from MySQL to SQLite
    2. Create sku_mapping_history from tables_data
    3. Generate vectors for all items
    4. Build vectors_cache.pkl
    """
    logger.info("=" * 60)
    logger.info("STEP 1/4: Cloning database from MySQL to SQLite...")
    logger.info("=" * 60)
    run_clone()

    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 2/4: Creating sku_mapping_history from tables_data...")
    logger.info("=" * 60)
    run_create_sku_mapping_history()

    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 3/4: Generating embeddings for all items...")
    logger.info("=" * 60)
    run_generate_vectors(overwrite=True)

    logger.info("")
    logger.info("=" * 60)
    logger.info("STEP 4/4: Building vectors cache...")
    logger.info("=" * 60)
    run_rebuild_cache()

    logger.info("")
    logger.info("=" * 60)
    logger.info("First-time setup complete!")
    logger.info("You can now start the API: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
    logger.info("=" * 60)


def main():
    """Entry point for first-time setup"""
    try:
        run_setup()
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise


if __name__ == "__main__":
    main()
