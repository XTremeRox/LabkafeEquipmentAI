"""
Interactive wrapper for database and vector sync.
Run this script to choose: Setup new (full clone) or Update (incremental).
"""

import os
import sys
import logging

# Ensure scripts directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Change to project root (parent of scripts/) so paths like local_quotation.db resolve correctly
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_project_root)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LOCAL_DB_PATH = os.getenv('LOCAL_DB_PATH', 'local_quotation.db')
VECTORS_CACHE_PATH = os.getenv('VECTORS_CACHE_PATH', 'vectors_cache.pkl')


def show_banner():
    """Print the script banner"""
    print()
    print("=" * 60)
    print("  Database & Vector Sync - AI Quotation")
    print("=" * 60)
    print()


def show_menu():
    """Display the menu and return user choice (1, 2, or 3)"""
    print("Choose an option:")
    print()
    print("  [1] Setup new  - Remove local DB and cache, full clone, vectors, cache")
    print("  [2] Update     - Sync new items only, compute vectors, update cache")
    print("  [3] Exit")
    print()
    while True:
        choice = input("Enter choice (1/2/3): ").strip()
        if choice in ('1', '2', '3'):
            return choice
        print("Invalid choice. Enter 1, 2, or 3.")


def confirm_setup_new():
    """Prompt for confirmation before destructive setup. Returns True if confirmed."""
    db_path = os.path.abspath(LOCAL_DB_PATH)
    cache_path = os.path.abspath(VECTORS_CACHE_PATH)

    print()
    print("This will DELETE existing local data:")
    if os.path.exists(LOCAL_DB_PATH):
        print(f"  - {db_path}")
    else:
        print(f"  - {db_path} (does not exist)")
    if os.path.exists(VECTORS_CACHE_PATH):
        print(f"  - {cache_path}")
    else:
        print(f"  - {cache_path} (does not exist)")
    print()
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    return confirm == 'yes'


def remove_local_data():
    """Remove local database and vectors cache files"""
    removed = []
    if os.path.exists(LOCAL_DB_PATH):
        try:
            os.remove(LOCAL_DB_PATH)
            logger.info(f"Removed {LOCAL_DB_PATH}")
            removed.append(LOCAL_DB_PATH)
        except OSError as e:
            logger.error(f"Failed to remove {LOCAL_DB_PATH}: {e}")
            raise
    else:
        logger.info(f"{LOCAL_DB_PATH} does not exist, skipping")

    if os.path.exists(VECTORS_CACHE_PATH):
        try:
            os.remove(VECTORS_CACHE_PATH)
            logger.info(f"Removed {VECTORS_CACHE_PATH}")
            removed.append(VECTORS_CACHE_PATH)
        except OSError as e:
            logger.error(f"Failed to remove {VECTORS_CACHE_PATH}: {e}")
            raise
    else:
        logger.info(f"{VECTORS_CACHE_PATH} does not exist, skipping")

    return removed


def run_setup_new_simple():
    """Run first-time setup"""
    import importlib.util
    setup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1_setup.py')
    spec = importlib.util.spec_from_file_location("one_setup", setup_path)
    one_setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(one_setup)
    one_setup.run_setup()


def run_update_simple():
    """Run incremental update"""
    import importlib.util
    update_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '2_update_items.py')
    spec = importlib.util.spec_from_file_location("two_update", update_path)
    two_update = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(two_update)
    two_update.run_update()


def main():
    """Main entry point"""
    show_banner()
    choice = show_menu()

    if choice == '3':
        logger.info("Exiting.")
        return

    if choice == '1':
        if not confirm_setup_new():
            logger.info("Aborted. No changes made.")
            return
        logger.info("Removing existing local data...")
        remove_local_data()
        logger.info("")
        logger.info("Starting first-time setup...")
        run_setup_new_simple()
    elif choice == '2':
        logger.info("Starting incremental update...")
        run_update_simple()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
