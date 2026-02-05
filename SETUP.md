# Setup Guide

To produce the **local database** (`local_quotation.db`) and **vector cache** (`vectors_cache.pkl`), complete **steps 3, 5, and 6** below (clone DB → generate vectors → load cache).

## Prerequisites

1. Python 3.10 or higher
2. MySQL database access (for cloning)
3. OpenAI API key
4. Google Cloud Vision API credentials
5. PHP server (XAMPP/Apache) for frontend

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your:
- MySQL database credentials
- SSL certificate path (SSL_CA_PATH, default: ca-certificate.crt)
- OpenAI API key
- Google Cloud credentials (set GOOGLE_APPLICATION_CREDENTIALS)
- Document AI configuration (PROJECT_ID, LOCATION, PROCESSOR_ID)

### 3. Clone Database from MySQL to SQLite

Run the database cloning script:

```bash
python scripts/clone_database.py
```

This will:
- Connect to your MySQL database (using SSL certificate)
- Clone `items` and `tables_data` tables to local SQLite
- Add `name_vector` column to items table

**Important:** After cloning, you MUST generate vectors (Step 5) before the matching system will work.

### 4. Create SKU Mapping History (One-time)

Run the mapping history creation script:

```bash
python scripts/create_sku_mapping_history.py
```

This will:
- Extract requirement → SKU mappings from `tables_data`
- Create `sku_mapping_history` table with frequencies
- Enable historical matching (70% weight in hybrid algorithm)

**Note:** You may need to update column names in this script based on your actual `tables_data` schema.

### 5. Generate Embeddings (REQUIRED)

**This step is required after cloning the database.** Generate embeddings for all items:

```bash
python scripts/generate_vectors.py
```

This will:
- Generate embeddings using OpenAI `text-embedding-3-small` for each item name
- Store vectors in SQLite database (`name_vector` column)
- Process items in batches using parallel workers (configurable via `NUM_WORKERS` in `.env`)
- Use hyperthreading for faster processing (default: 10 workers)

**Configuration:**
- `BATCH_SIZE`: Items per batch (default: 100)
- `NUM_WORKERS`: Number of parallel workers (default: 5, customizable)
- `OVERWRITE_EXISTING_VECTORS`: Overwrite existing vectors (default: true)

**Note:** 
- With 5 workers, processing 9,000+ items typically takes 3-6 minutes
- If you experience "database is locked" errors, reduce `NUM_WORKERS` to 3-4
- The script includes retry logic and lock handling for SQLite concurrency

### 6. Load Vectors to Memory Cache (REQUIRED)

**This step is required after generating vectors.** Create the in-memory cache for fast matching:

```bash
python scripts/load_vectors_to_memory.py
```

This will:
- Load all items and vectors from SQLite
- Create `vectors_cache.pkl` file for fast API startup
- Enable sub-millisecond vector matching

**Note:** This cache file is loaded when the API starts. Regenerate it if you add new items or update vectors.

### 7. Start FastAPI Server

**Prerequisites:** Make sure you've completed steps 5 and 6 (generate vectors and load cache) before starting the API.

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will:
- Load vectors cache on startup
- Be available at `http://localhost:8000`
- Show health status at `http://localhost:8000/health`

**If vectors aren't loaded:** The API will start but matching won't work. Check the startup logs for errors.

### 8. Access Frontend

- **Upload & Process**: Open `web/upload.php` in your browser through your PHP server
- **Test Suggestions**: Open `web/test_suggestions.php` to manually test the suggestion algorithm without OCR

## Usage Flow

1. **Upload**: Upload image/PDF/Excel/Word document
2. **Edit**: Review and edit extracted line items
3. **Suggestions**: Get AI-powered suggestions with historical quote data
4. **Submit**: Finalize quotation (learning mechanism TODO)

## API Endpoints

- `POST /api/upload` - Upload file
- `POST /api/extract` - Extract line items from uploaded file
- `POST /api/suggest` - Get suggestions for line items
- `POST /api/quote-history` - Get quote history for SKU
- `POST /api/submit` - Submit final quotation

## Troubleshooting

### Database Connection Issues
- Verify MySQL credentials in `.env`
- Ensure MySQL server is accessible
- Check SSL certificate path (`SSL_CA_PATH`) - should point to `ca-certificate.crt` in project root
- Verify SSL certificate file exists and is readable

### Vector Generation Issues
- Check OpenAI API key is valid
- Verify API quota/limits

### Google Cloud API Issues
- Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Verify service account JSON file path
- Create a Document AI processor in Google Cloud Console:
  1. Go to Document AI in Google Cloud Console
  2. Create a new processor (use "Document OCR" processor type)
  3. Copy the Processor ID and set `DOCUMENT_AI_PROCESSOR_ID` in `.env`
  4. Set `DOCUMENT_AI_PROJECT_ID` to your GCP project ID
  5. Set `DOCUMENT_AI_LOCATION` (usually 'us' or 'eu')

### Frontend Not Connecting
- Ensure FastAPI server is running on port 8000
- Update `API_BASE_URL` in PHP files if using different port

## Notes

- The learning mechanism in `/api/submit` endpoint is marked as TODO
- Column names in `create_sku_mapping_history.py` may need adjustment based on your schema
- The system loads all vectors into RAM on startup for performance
