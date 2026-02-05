# Troubleshooting Guide

## OpenAI Client Initialization Error

### Error: `Client.__init__() got an unexpected keyword argument 'proxies'`

This is a known compatibility issue between OpenAI SDK and httpx versions.

#### Solution 1: Upgrade Dependencies (Recommended)

```bash
pip install --upgrade openai httpx
```

Or update `requirements.txt` and reinstall:
```bash
pip install -r requirements.txt --upgrade
```

#### Solution 2: Pin Compatible Versions

If upgrading doesn't work, try pinning specific versions:

```bash
pip install openai==1.12.0 httpx==0.27.0
```

#### Solution 3: Check Environment Variables

Remove any proxy-related environment variables that might interfere:

```bash
# Windows
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=

# Linux/Mac
unset HTTP_PROXY
unset HTTPS_PROXY
unset http_proxy
unset https_proxy
```

#### Solution 4: Use Environment Variable for API Key

Instead of passing `api_key` parameter, set it as environment variable:

```python
import os
os.environ['OPENAI_API_KEY'] = 'your-key-here'
from openai import OpenAI
client = OpenAI()  # Will use environment variable
```

## Database Connection Issues

### SSL Certificate Error

**Error:** `SSL connection error` or `certificate verify failed`

**Solution:**
1. Ensure `ca-certificate.crt` exists in project root
2. Check `SSL_CA_PATH` in `.env` points to correct file
3. Verify certificate file is readable

### Connection Timeout

**Error:** `Connection timeout` or `Can't connect to MySQL server`

**Solution:**
1. Verify `DB_HOST` and `DB_PORT` in `.env`
2. Check firewall settings
3. Ensure MySQL server allows connections from your IP
4. Verify SSL certificate is correct for managed database

## Vector Generation Issues

### "No items need embeddings"

**Cause:** All items already have vectors, or query is incorrect

**Solution:**
- Check SQLite database has items: `sqlite3 local_quotation.db "SELECT COUNT(*) FROM items"`
- Verify items have NULL or empty `name_vector`: `sqlite3 local_quotation.db "SELECT COUNT(*) FROM items WHERE name_vector IS NULL"`

### OpenAI API Rate Limits

**Error:** `Rate limit exceeded` or `429 Too Many Requests`

**Solution:**
1. Reduce `BATCH_SIZE` in `.env` (default: 100, try 50 or 25)
2. Add delays between batches in `generate_vectors.py`
3. Check OpenAI API usage limits
4. Use OpenAI API key with higher rate limits

### Vector Generation Fails Silently

**Symptoms:** Script completes but no vectors generated

**Solution:**
1. Check OpenAI API key is valid
2. Verify API quota/credits available
3. Check logs for specific error messages
4. Test API key: `python -c "from openai import OpenAI; client = OpenAI(api_key='your-key'); print(client.models.list())"`

## Vector Cache Issues

### "Cache file uses old format"

**Error:** Cache file was created with old schema (item_ids instead of item_skus)

**Solution:**
1. Delete old cache: `rm vectors_cache.pkl` (or `del vectors_cache.pkl` on Windows)
2. Regenerate: `python scripts/load_vectors_to_memory.py`

### "Vectors not loaded" on API startup

**Error:** API starts but vectors aren't loaded

**Solution:**
1. Verify `vectors_cache.pkl` exists
2. Check `VECTORS_CACHE_PATH` in `.env`
3. Regenerate cache: `python scripts/load_vectors_to_memory.py`
4. Check API startup logs for specific errors

## API Endpoint Issues

### CORS Errors

**Error:** `Access-Control-Allow-Origin` or CORS policy errors

**Solution:**
1. Check `api/main.py` CORS configuration
2. Update `allow_origins` to match your frontend URL
3. Ensure FastAPI server is running

### 404 Not Found

**Error:** API endpoints return 404

**Solution:**
1. Verify API server is running: `http://localhost:8000/health`
2. Check endpoint URLs in PHP files match API routes
3. Ensure routes are registered in `api/main.py`

## Frontend Issues

### Suggestions Not Loading

**Symptoms:** Page loads but no suggestions appear

**Solution:**
1. Check browser console for JavaScript errors
2. Verify API is accessible: `http://localhost:8000/api/suggest`
3. Check `API_BASE_URL` in PHP files matches your API server
4. Verify vectors are loaded (check API health endpoint)

### File Upload Fails

**Error:** Upload button doesn't work or files don't upload

**Solution:**
1. Check `UPLOAD_DIR` exists and is writable
2. Verify file size limits in FastAPI
3. Check browser console for errors
4. Verify API endpoint `/api/upload` is accessible

## Performance Issues

### Slow Suggestions

**Symptoms:** Suggestions take too long to load

**Solution:**
1. Verify vectors cache is loaded (check API health)
2. Check database indexes exist
3. Reduce number of items being processed
4. Optimize batch sizes

### High Memory Usage

**Symptoms:** System runs out of memory

**Solution:**
1. Reduce `BATCH_SIZE` for vector generation
2. Process items in smaller batches
3. Increase system RAM
4. Consider using FAISS instead of NumPy for very large datasets

## Getting Help

If issues persist:
1. Check logs in console/terminal output
2. Verify all environment variables are set correctly
3. Test each component individually
4. Check GitHub issues for known problems
