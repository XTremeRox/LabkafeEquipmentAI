# Document AI Setup Guide

## Overview
This project uses Google Cloud Document AI for better OCR quality, especially for PDFs and structured documents. Document AI provides superior text extraction compared to Vision API alone.

## Prerequisites
1. Google Cloud Platform (GCP) account
2. Document AI API enabled in your GCP project
3. Service account with Document AI permissions

## Setup Steps

### 1. Enable Document AI API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to "APIs & Services" > "Library"
4. Search for "Document AI API"
5. Click "Enable"

### 2. Create a Document AI Processor
1. Go to [Document AI](https://console.cloud.google.com/ai/document-ai)
2. Click "Create Processor"
3. Select "Document OCR" processor type (or "Form Parser" if you need structured form extraction)
4. Choose a location (e.g., "us" or "eu")
5. Give it a name (e.g., "quotation-ocr-processor")
6. Click "Create"
7. **Copy the Processor ID** (you'll need this for `.env`)

### 3. Create Service Account (if not already done)
1. Go to "IAM & Admin" > "Service Accounts"
2. Create a new service account or use existing one
3. Grant roles:
   - `Document AI API User`
   - `Storage Object Viewer` (if processing files from Cloud Storage)
4. Create and download JSON key file
5. Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the key file path

### 4. Configure Environment Variables
Add to your `.env` file:
```env
DOCUMENT_AI_PROJECT_ID=your-gcp-project-id
DOCUMENT_AI_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=your-processor-id-here
USE_DOCUMENT_AI_FOR_IMAGES=true
```

### 5. Install Dependencies
```bash
pip install google-cloud-documentai
```

## Configuration Options

### USE_DOCUMENT_AI_FOR_IMAGES
- `true`: Use Document AI for images (better quality, especially for handwriting)
- `false`: Use Vision API for images (faster, cheaper for simple images)

**Recommendation**: Set to `true` for best quality, especially if you process handwritten notes.

## What Document AI Provides

### Benefits Over Vision API
1. **Better PDF Handling**: Native PDF support, multi-page processing
2. **Improved OCR Quality**: More accurate text extraction
3. **Layout Understanding**: Preserves document structure
4. **Table Extraction**: Better handling of tables and structured data
5. **Handwriting Recognition**: Superior handwriting OCR

### Still Using GPT-4o
Document AI handles OCR/text extraction. GPT-4o is still used for:
- Structured extraction (description, quantity, unit)
- Business logic understanding
- Validation and normalization
- Domain knowledge application

## Cost Considerations

- **Document AI**: ~$1.50 per 1,000 pages
- **Vision API**: ~$1.50 per 1,000 images
- Pricing is similar, but Document AI provides better quality

## Troubleshooting

### "Processor not found" error
- Verify `DOCUMENT_AI_PROCESSOR_ID` is correct
- Check that processor exists in the specified location
- Ensure service account has access to the processor

### "Permission denied" error
- Verify service account has `Document AI API User` role
- Check `GOOGLE_APPLICATION_CREDENTIALS` is set correctly
- Ensure Document AI API is enabled in your project

### Fallback to Vision API
If Document AI fails, the system automatically falls back to Vision API for images. PDFs will show an error if Document AI fails (Vision API doesn't handle PDFs well).

## Testing

Test the setup:
```python
from api.ocr import process_file

# Test PDF
text, file_type = process_file('test.pdf', 'test.pdf')
print(f"Extracted {len(text)} characters")

# Test image
text, file_type = process_file('test.jpg', 'test.jpg')
print(f"Extracted {len(text)} characters")
```

## Migration Notes

- Existing Vision API code remains as fallback
- Document AI is used for PDFs by default
- Images use Document AI if `USE_DOCUMENT_AI_FOR_IMAGES=true`
- Excel/Word/CSV extraction unchanged (uses pandas/python-docx)
