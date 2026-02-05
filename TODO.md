# TODO

## Plan: Update local DB with new SKUs and calculate their vectors for future use

**Goal:** When re-fetching from the online (MySQL) database, update the local DB with only new (or changed) SKUs/items, compute their embeddings in batch, and update the database and vector cache so they are available for matching.

## Incremental database sync and vector updates

When re-fetching from the online (MySQL) database, support incremental updates instead of full replace:

1. **Clone script (`scripts/clone_database.py`)**
   - **Items:** Sync by SKU: only INSERT new SKUs from MySQL; optionally UPDATE existing rows (e.g. when `name` changes) and set `name_vector = NULL` for changed items so vectors get regenerated. Optionally DELETE local items whose SKU no longer exists in MySQL.
   - **tables_data:** Sync incrementally by unique key (e.g. `internal_migration_id` or `id`): only INSERT rows that do not exist locally; optionally delete local rows no longer present in MySQL.
   - Do not use full `DELETE FROM table` + re-insert; build a set of existing keys and insert/update only as needed.

2. **Vectors**
   - Use existing incremental behavior: set `OVERWRITE_EXISTING_VECTORS=false` in `.env` so `generate_vectors.py` only processes items where `name_vector IS NULL` (batch processing unchanged).
   - After clone, new/changed items will have NULL `name_vector` and will be picked up by the next run of `generate_vectors.py`.

3. **Cache**
   - After generating vectors, run `load_vectors_to_memory.py` to refresh `vectors_cache.pkl`. No code change needed.

4. **Workflow**
   - Document or script: (1) incremental clone → (2) `generate_vectors.py` (incremental) → (3) `load_vectors_to_memory.py`.

5. **Optional**
   - Detect “changed” items: when updating an existing item from MySQL, if `name` changed set `name_vector = NULL` so embeddings are regenerated for that SKU.
