"""
One-time script to create sku_mapping_history table from tables_data.
Processes historical quotations to extract requirement_string -> sku mappings
and aggregates frequencies.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from collections import defaultdict

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


def create_mapping_history_table(sqlite_conn):
    """Create sku_mapping_history table if it doesn't exist"""
    cursor = sqlite_conn.cursor()
    
    # Drop old table if it exists with wrong schema
    cursor.execute("DROP TABLE IF EXISTS sku_mapping_history")
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS sku_mapping_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requirement_string TEXT NOT NULL,
        sku TEXT NOT NULL,
        frequency INTEGER DEFAULT 1,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(requirement_string, sku)
    )
    """
    
    cursor.execute(create_sql)
    
    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_requirement_string 
        ON sku_mapping_history(requirement_string)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sku 
        ON sku_mapping_history(sku)
    """)
    
    sqlite_conn.commit()
    logger.info("Created sku_mapping_history table with indexes")


def get_tables_data_schema(sqlite_conn) -> List[str]:
    """Get column names from tables_data table"""
    cursor = sqlite_conn.cursor()
    cursor.execute("PRAGMA table_info(tables_data)")
    columns = [row[1] for row in cursor.fetchall()]
    return columns


def extract_mappings_from_tables_data(sqlite_conn) -> Dict[str, Dict[str, int]]:
    """
    Extract requirement_string -> sku mappings from tables_data.
    Returns dict: {requirement_string: {sku: frequency}}
    Uses 'requirement' and 'sku' columns directly from tables_data.
    """
    cursor = sqlite_conn.cursor()
    
    # Use requirement and sku columns directly
    requirement_col = 'requirement'
    sku_col = 'sku'
    
    logger.info(f"Using requirement column: {requirement_col}")
    logger.info(f"Using SKU column: {sku_col}")
    
    # Query to extract mappings
    query = f"""
        SELECT {requirement_col}, {sku_col}
        FROM tables_data
        WHERE {requirement_col} IS NOT NULL 
          AND {requirement_col} != ''
          AND {sku_col} IS NOT NULL
          AND {sku_col} != ''
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Aggregate frequencies
    mappings = defaultdict(lambda: defaultdict(int))
    
    for row in rows:
        requirement = str(row[0]).strip()
        sku = str(row[1]).strip()
        
        if requirement and sku:
            mappings[requirement][sku] += 1
    
    logger.info(f"Extracted {len(mappings)} unique requirement strings")
    total_mappings = sum(sum(freqs.values()) for freqs in mappings.values())
    logger.info(f"Total mappings found: {total_mappings}")
    
    return mappings


def insert_mappings(sqlite_conn, mappings: Dict[str, Dict[str, int]]):
    """Insert aggregated mappings into sku_mapping_history table"""
    cursor = sqlite_conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM sku_mapping_history")
    sqlite_conn.commit()
    logger.info("Cleared existing sku_mapping_history data")
    
    # Insert mappings
    insert_sql = """
        INSERT INTO sku_mapping_history (requirement_string, sku, frequency)
        VALUES (?, ?, ?)
    """
    
    total_inserted = 0
    for requirement_string, sku_freqs in mappings.items():
        for sku, frequency in sku_freqs.items():
            cursor.execute(insert_sql, (requirement_string, sku, frequency))
            total_inserted += 1
    
    sqlite_conn.commit()
    logger.info(f"Inserted {total_inserted} mappings into sku_mapping_history")


def verify_items_exist(sqlite_conn):
    """Verify that all SKUs in mappings exist in items table"""
    cursor = sqlite_conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT sku 
        FROM sku_mapping_history 
        WHERE sku NOT IN (SELECT sku FROM items WHERE sku IS NOT NULL AND sku != '')
    """)
    
    invalid_skus = cursor.fetchall()
    if invalid_skus:
        logger.warning(f"Found {len(invalid_skus)} SKUs that don't exist in items table")
        logger.warning("These mappings will still be stored but may not match items")
    else:
        logger.info("All SKUs in mappings exist in items table")


def main():
    """Main function to create sku_mapping_history from tables_data"""
    sqlite_conn = None
    
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(LOCAL_DB_PATH)
        logger.info(f"Connected to SQLite database: {LOCAL_DB_PATH}")
        
        # Create table
        logger.info("=" * 60)
        logger.info("Creating sku_mapping_history table...")
        logger.info("=" * 60)
        create_mapping_history_table(sqlite_conn)
        
        # Extract mappings from tables_data
        logger.info("=" * 60)
        logger.info("Extracting mappings from tables_data...")
        logger.info("=" * 60)
        mappings = extract_mappings_from_tables_data(sqlite_conn)
        
        # Insert mappings
        logger.info("=" * 60)
        logger.info("Inserting mappings into sku_mapping_history...")
        logger.info("=" * 60)
        insert_mappings(sqlite_conn, mappings)
        
        # Verify data integrity
        verify_items_exist(sqlite_conn)
        
        # Show summary
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sku_mapping_history")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT requirement_string) FROM sku_mapping_history")
        unique_requirements = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(frequency) FROM sku_mapping_history")
        total_frequency = cursor.fetchone()[0]
        
        logger.info("=" * 60)
        logger.info("sku_mapping_history creation complete!")
        logger.info(f"Total mappings: {total_count}")
        logger.info(f"Unique requirement strings: {unique_requirements}")
        logger.info(f"Total frequency count: {total_frequency}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if sqlite_conn:
            sqlite_conn.close()
            logger.info("SQLite connection closed")


if __name__ == "__main__":
    main()
