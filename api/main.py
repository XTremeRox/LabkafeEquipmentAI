"""
FastAPI main application file.
Handles startup/shutdown events and CORS configuration.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.database import load_vectors_to_memory
from api import routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting up AI Quotation API...")
    try:
        load_vectors_to_memory()
        logger.info("Vectors loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load vectors: {e}")
        logger.error("API will start but matching may not work properly")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Quotation API...")


# Create FastAPI app
app = FastAPI(
    title="AI Quotation API",
    description="AI-powered intelligent quotation engine",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for PHP frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api", tags=["quotation"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Quotation API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from api.database import _vectors_cache, _item_skus
    
    return {
        "status": "healthy",
        "vectors_loaded": _vectors_cache is not None,
        "items_count": len(_item_skus) if _item_skus else 0
    }
