# LabkafeEquipmentAI

**Auto-suggestion backend for automated quotes based on requirements.** It suggests catalog items from requirement text so quotes can be created quickly. Currently **text matching** is used; requirement input from other file types (images, PDFs, Excel, etc.) is **in plan**.

## Project Overview
LabkafeEquipmentAI is an auto-suggestion backend that powers automated quotations: given a requirement (e.g. "Test Tube 10ml"), it suggests the best-matching catalog items. It can be used with a PHP-based quotation portal or other frontends. Right now matching is driven by **text requirements**; support for requirements extracted from multiple file input types is planned.

## The Core Problem
Clients send requirements in various formats (e.g., "Test Tube 10ml"). Our catalog has 9,000+ items. Sometimes we quote the exact match; other times we provide alternatives based on stock, budget, or quality. We need a system that "remembers" these historical decisions.

## Pipeline
**Current:** Requirement text → **Hybrid Matcher** (suggestions) → User selects/edits → Final mapping updates `sku_mapping_history`.  
**In plan:** Requirement input from multiple file types (Image, Excel, PDF, etc.) → extraction → requirement list → same suggestion and approval flow.

## Technical Stack
- **Frontend/UI:** PHP (Existing Portal integration).
- **Backend API:** FastAPI (Python 3.10+).
- **OCR:** Google Cloud Document AI (PDFs & structured documents) + Vision API (fallback for images).
- **Intelligence:** OpenAI GPT-4o (Structured Extraction).
- **Semantic Search:** OpenAI `text-embedding-3-small` + FAISS/NumPy (Vector matching).
- **Database:** Managed MySQL (Digital Ocean).

## Key Logic: The Hybrid Matcher
Every requirement line is scored using a weighted average:
1. **Historical Mapping (70% weight):** A `sku_mapping_history` table stores how often a specific requirement string was matched to a specific SKU in the past.
2. **Vector Similarity (30% weight):** Semantic similarity between the requirement text and the `items` catalog using embeddings.

**Final Score Formula:** $Score = (History\_Freq\_Normalized \times 0.7) + (Vector\_Similarity \times 0.3)$

## Efficiency & Automation Strategy
To minimize human intervention, the system employs three specific speed-up tactics:
1. **Pre-cached Vector Index:** Item embeddings are calculated once and stored in memory (NumPy/FAISS) for sub-millisecond matching.
1.5. **Batch ProcessingL** Item embeddings for cache misses are sent in batches to text-embedding-3-small for calculating vectors. 
2. **Top-3 Suggestion UI:** The system provides the best match and two alternatives, allowing one-click corrections.
3. **Confidence Thresholding:** - **High Confidence (>0.85):** Highlighted as "Ready to Quote."
   - **Low Confidence (<0.60):** Flagged for mandatory manual review.

## Data Learning Loop
When a user finalizes a quote in the PHP portal, a signal is sent to the `/learn` endpoint. This updates the frequency of the `requirement_string -> sku_id` mapping, ensuring the 70% "History" weight becomes more accurate over time.

## Learning Mechanism (Feedback Loop)
Whenever a quotation is finalized in the PHP UI, the final SKU selections are sent back to the Python API to update the `sku_mapping_history`. This ensures the system "learns" from human corrections in real-time.

## Producing the local database and vectors

The matching system uses a local SQLite database and a precomputed vector cache. To create them:

1. **Local database (`local_quotation.db`):** Clone from MySQL (see [SETUP.md](SETUP.md) §3):
   ```bash
   python scripts/clone_database.py
   ```
2. **Vectors in DB:** Generate embeddings for items (see [SETUP.md](SETUP.md) §5):
   ```bash
   python scripts/generate_vectors.py
   ```
3. **Vector cache (`vectors_cache.pkl`):** Load vectors into cache for fast API startup (see [SETUP.md](SETUP.md) §6):
   ```bash
   python scripts/load_vectors_to_memory.py
   ```

Full details, prerequisites, and optional steps (SKU mapping history, etc.) are in **[SETUP.md](SETUP.md)**.

## Project Structure
- `/api`: FastAPI backend for OCR, Embedding, and Scoring logic.
- `/scripts`: Python scripts for local DB syncing and Vector generation.
- `/web`: PHP components for the User Verification interface.