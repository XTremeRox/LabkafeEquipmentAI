"""
Script to clone MySQL database tables (items and tables_data) to local SQLite database.
Connects to remote MySQL using .env credentials and creates a local SQLite database.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import pymysql

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
SSL_CA_PATH = os.getenv('SSL_CA_PATH', 'ca-certificate.crt')


def connect_mysql():
    """Create MySQL connection using credentials from .env with SSL certificate"""
    try:
        # Get SSL certificate path
        ssl_ca = None
        if os.path.exists(SSL_CA_PATH):
            ssl_ca = SSL_CA_PATH
            logger.info(f"Using SSL certificate: {ssl_ca}")
        else:
            logger.warning(f"SSL certificate not found at {SSL_CA_PATH}, connecting without SSL")
        
        # Build SSL configuration
        ssl_config = {}
        if ssl_ca:
            ssl_config = {
                'ca': ssl_ca,
                'check_hostname': False  # Managed databases often use self-signed certs
            }
        
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            ssl=ssl_config if ssl_config else None
        )
        logger.info("Successfully connected to MySQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MySQL database: {e}")
        raise


def get_table_schema(mysql_conn, table_name: str) -> List[Dict[str, Any]]:
    """Get column information for a MySQL table"""
    cursor = mysql_conn.cursor()
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    cursor.close()
    return columns


def mysql_to_sqlite_type(mysql_type: str) -> str:
    """Convert MySQL data type to SQLite data type"""
    mysql_type = mysql_type.lower()
    
    if 'int' in mysql_type:
        return 'INTEGER'
    elif 'float' in mysql_type or 'double' in mysql_type or 'decimal' in mysql_type:
        return 'REAL'
    elif 'text' in mysql_type or 'varchar' in mysql_type or 'char' in mysql_type:
        return 'TEXT'
    elif 'blob' in mysql_type or 'binary' in mysql_type:
        return 'BLOB'
    elif 'date' in mysql_type or 'time' in mysql_type or 'timestamp' in mysql_type or 'datetime' in mysql_type:
        return 'TEXT'
    else:
        return 'TEXT'  # Default to TEXT


def create_sqlite_table(sqlite_conn, table_name: str, mysql_columns: List[Dict[str, Any]], primary_key: str = None):
    """Create SQLite table based on MySQL table schema"""
    cursor = sqlite_conn.cursor()
    
    # Build column definitions
    column_defs = []
    for col in mysql_columns:
        col_name = col['Field']
        col_type = mysql_to_sqlite_type(col['Type'])
        
        # Handle primary key
        if col['Key'] == 'PRI' or (primary_key and col_name == primary_key):
            col_type += ' PRIMARY KEY'
            if 'auto_increment' in col.get('Extra', '').lower():
                col_type += ' AUTOINCREMENT'
        
        # Handle NOT NULL
        if col['Null'] == 'NO':
            col_type += ' NOT NULL'
        
        column_defs.append(f"{col_name} {col_type}")
    
    # Create table
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
    cursor.execute(create_sql)
    sqlite_conn.commit()
    logger.info(f"Created table {table_name} in SQLite")


def clone_table(mysql_conn, sqlite_conn, table_name: str, batch_size: int = 1000):
    """Clone a table from MySQL to SQLite"""
    logger.info(f"Starting to clone table: {table_name}")
    
    mysql_cursor = mysql_conn.cursor()
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get all data from MySQL
    mysql_cursor.execute(f"SELECT * FROM {table_name}")
    
    # Get column names
    columns = [desc[0] for desc in mysql_cursor.description]
    
    # Clear existing data if table exists
    sqlite_cursor.execute(f"DELETE FROM {table_name}")
    sqlite_conn.commit()
    
    # Fetch and insert in batches
    total_rows = 0
    while True:
        rows = mysql_cursor.fetchmany(batch_size)
        if not rows:
            break
        
        # Prepare placeholders
        placeholders = ','.join(['?' for _ in columns])
        insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
        
        # Convert rows to tuples
        values = []
        for row in rows:
            row_values = []
            for col in columns:
                value = row[col]
                # Handle None and special types
                if value is None:
                    row_values.append(None)
                elif isinstance(value, bytes):
                    row_values.append(value)
                else:
                    row_values.append(str(value) if value is not None else None)
            values.append(tuple(row_values))
        
        sqlite_cursor.executemany(insert_sql, values)
        sqlite_conn.commit()
        
        total_rows += len(rows)
        logger.info(f"Cloned {total_rows} rows from {table_name}")
    
    mysql_cursor.close()
    logger.info(f"Completed cloning {table_name}: {total_rows} total rows")


def add_vector_column(sqlite_conn):
    """Add name_vector column to items table if it doesn't exist"""
    cursor = sqlite_conn.cursor()
    try:
        cursor.execute("ALTER TABLE items ADD COLUMN name_vector BLOB")
        sqlite_conn.commit()
        logger.info("Added name_vector column to items table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("name_vector column already exists")
        else:
            raise


def main():
    """Main function to orchestrate the database cloning process"""
    mysql_conn = None
    sqlite_conn = None
    
    try:
        # Connect to MySQL
        mysql_conn = connect_mysql()
        
        # Connect to SQLite (create if doesn't exist)
        sqlite_conn = sqlite3.connect(LOCAL_DB_PATH)
        logger.info(f"Connected to SQLite database: {LOCAL_DB_PATH}")
        
        # Clone items table
        logger.info("=" * 60)
        logger.info("Cloning items table...")
        logger.info("=" * 60)
        
        # Get schema and create table
        items_schema = get_table_schema(mysql_conn, 'items')
        create_sqlite_table(sqlite_conn, 'items', items_schema, primary_key='id')
        
        # Clone data
        clone_table(mysql_conn, sqlite_conn, 'items')
        
        # Add name_vector column
        add_vector_column(sqlite_conn)
        
        # Clone tables_data table
        logger.info("=" * 60)
        logger.info("Cloning tables_data table...")
        logger.info("=" * 60)
        
        # Get schema and create table
        tables_data_schema = get_table_schema(mysql_conn, 'tables_data')
        create_sqlite_table(sqlite_conn, 'tables_data', tables_data_schema)
        
        # Clone data
        clone_table(mysql_conn, sqlite_conn, 'tables_data')
        
        logger.info("=" * 60)
        logger.info("Database cloning complete!")
        logger.info(f"Local database saved at: {LOCAL_DB_PATH}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("1. Run: python scripts/create_sku_mapping_history.py")
        logger.info("2. Run: python scripts/generate_vectors.py  (REQUIRED - generates embeddings)")
        logger.info("3. Run: python scripts/load_vectors_to_memory.py  (REQUIRED - creates cache)")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if mysql_conn:
            mysql_conn.close()
            logger.info("MySQL connection closed")
        if sqlite_conn:
            sqlite_conn.close()
            logger.info("SQLite connection closed")


if __name__ == "__main__":
    main()
