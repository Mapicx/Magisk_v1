from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import Resume_getter
from . import models
import logging
import time
import sys

# ============================================================================
# Configure Logging - Simple and Clean
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)

logger = logging.getLogger("FastAPI")
logger.setLevel(logging.INFO)

# Also configure uvicorn loggers
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

# Create all tables
Base.metadata.create_all(bind=engine) # type: ignore

app = FastAPI(
    title="Resume Optimization API",
    description="Upload and manage resumes for AI optimization."
)

# Simple logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    client_ip = request.client.host if request.client else 'unknown'
    logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
    
    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Error processing {request.method} {request.url.path}: {str(e)}", exc_info=True)
        raise
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {request.method} {request.url.path} - Status {response.status_code} - {process_time:.3f}s")
    
    # Flush to ensure immediate output
    sys.stdout.flush()
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(Resume_getter.router)

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI application shutting down")

@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "API is working!", "status": "healthy"}

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy", "message": "API is running"}