"""
Incremental update: sync new items from MySQL, generate vectors for new items only, rebuild cache.
Does NOT touch tables_data.
"""

import os
import sqlite3
import logging
import sys

# Ensure scripts directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from clone_database import connect_mysql, add_vector_column
from generate_vectors import run_generate_vectors
from load_vectors_to_memory import run_rebuild_cache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LOCAL_DB_PATH = os.getenv('LOCAL_DB_PATH', 'local_quotation.db')
BATCH_SIZE = 500


def run_update():
    """
    Incremental update:
    1. Connect to MySQL and SQLite
    2. Fetch new items from MySQL (internal_migration_id > max_local)
    3. Insert new rows into local items
    4. Generate vectors for new items only
    5. Rebuild vectors_cache.pkl
    """
    mysql_conn = None
    sqlite_conn = None

    try:
        logger.info("=" * 60)
        logger.info("Connecting to MySQL and SQLite...")
        logger.info("=" * 60)
        mysql_conn = connect_mysql()
        sqlite_conn = sqlite3.connect(LOCAL_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row

        # Check if items table exists
        cursor = sqlite_conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='items'"
        )
        if not cursor.fetchone():
            raise RuntimeError(
                "Local items table not found. Please run first-time setup: python scripts/sync.py -> Setup new"
            )

        # Get max internal_migration_id from local
        cursor.execute(
            "SELECT COALESCE(MAX(internal_migration_id), 0) as max_id FROM items"
        )
        local_max_id = cursor.fetchone()[0]
        logger.info(f"Local max internal_migration_id: {local_max_id}")

        # Fetch new items from MySQL (with valid SKU)
        mysql_cursor = mysql_conn.cursor()
        mysql_cursor.execute(
            """
            SELECT * FROM items
            WHERE internal_migration_id > %s
              AND sku IS NOT NULL
              AND sku != ''
            ORDER BY internal_migration_id
            """,
            (local_max_id,)
        )
        new_rows = mysql_cursor.fetchall()
        mysql_cursor.close()

        if not new_rows:
            logger.info("No new items in MySQL. Skipping insert, generating vectors for any missing, rebuilding cache.")
        else:
            logger.info(f"Found {len(new_rows)} new items in MySQL")

            # Get column names from first row (DictCursor returns dicts)
            columns = list(new_rows[0].keys())
            # Ensure we don't insert name_vector (MySQL doesn't have it; local has it as NULL)
            if 'name_vector' in columns:
                columns = [c for c in columns if c != 'name_vector']

            placeholders = ','.join(['?' for _ in columns])
            insert_sql = f"INSERT INTO items ({','.join(columns)}) VALUES ({placeholders})"

            inserted = 0
            for i in range(0, len(new_rows), BATCH_SIZE):
                batch = new_rows[i:i + BATCH_SIZE]
                values = []
                for row in batch:
                    row_values = []
                    for col in columns:
                        value = row[col]
                        if value is None:
                            row_values.append(None)
                        elif isinstance(value, bytes):
                            row_values.append(value)
                        else:
                            row_values.append(str(value) if value is not None else None)
                    values.append(tuple(row_values))
                cursor.executemany(insert_sql, values)
                sqlite_conn.commit()
                inserted += len(batch)
                logger.info(f"Inserted {inserted}/{len(new_rows)} new items")

            logger.info(f"Inserted {len(new_rows)} new items into local database")

        # Add name_vector column if missing
        add_vector_column(sqlite_conn)

        logger.info("")
        logger.info("=" * 60)
        logger.info("Generating vectors for new items (incremental mode)...")
        logger.info("=" * 60)
        run_generate_vectors(overwrite=False)

        logger.info("")
        logger.info("=" * 60)
        logger.info("Rebuilding vectors cache...")
        logger.info("=" * 60)
        run_rebuild_cache()

        logger.info("")
        logger.info("=" * 60)
        logger.info("Incremental update complete!")
        logger.info("Restart the API to pick up the new cache.")
        logger.info("=" * 60)

    finally:
        if mysql_conn:
            mysql_conn.close()
            logger.info("MySQL connection closed")
        if sqlite_conn:
            sqlite_conn.close()
            logger.info("SQLite connection closed")


def main():
    """Entry point for incremental update"""
    try:
        run_update()
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise


if __name__ == "__main__":
    main()
