# Quick Start Guide

## Essential Setup Steps (In Order)

Follow these steps in order to get the system running:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Clone Database
```bash
python scripts/clone_database.py
```
✅ Clones items and tables_data from MySQL to SQLite

### 4. Create Mapping History
```bash
python scripts/create_sku_mapping_history.py
```
✅ Creates historical requirement → SKU mappings

### 5. Generate Vectors ⚠️ REQUIRED
```bash
python scripts/generate_vectors.py
```
✅ **MUST RUN THIS** - Generates embeddings for all items using parallel workers
⏱️ Takes 2-5 minutes for 9,000+ items (with 10 workers)
⚙️ Configure `NUM_WORKERS` in `.env` to adjust parallelism (default: 10)

### 6. Load Vectors Cache ⚠️ REQUIRED
```bash
python scripts/load_vectors_to_memory.py
```
✅ **MUST RUN THIS** - Creates cache file for fast matching
📁 Creates `vectors_cache.pkl`

### 7. Start API Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
✅ API starts and loads vectors cache

### 8. Test the System
- Open `web/test_suggestions.php` in browser
- Enter items manually to test suggestions
- Or use `web/upload.php` for full OCR workflow

## Common Issues

### "Vectors not loaded" error
- Run step 5: `python scripts/generate_vectors.py`
- Then run step 6: `python scripts/load_vectors_to_memory.py`
- Restart API server

### "No suggestions found"
- Check that vectors were generated (step 5)
- Check that cache was created (step 6)
- Verify API health: `http://localhost:8000/health`

### Database connection fails
- Check SSL certificate path in `.env`
- Verify `ca-certificate.crt` exists in project root
- Check MySQL credentials

## Workflow Summary

```
Clone DB → Create History → Generate Vectors → Load Cache → Start API → Test
```

**Critical Path:** Steps 5 and 6 are REQUIRED for the matching system to work!
