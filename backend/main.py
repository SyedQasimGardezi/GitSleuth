from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import asyncio
import uuid
import time
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

from services.repo_processor import RepoProcessor
from services.rag_service import RAGService
from services.conversation_manager import ConversationManager
from models.schemas import IndexRequest, QueryRequest, StatusResponse, QueryResponse, ConversationHistory
from utils.logger import setup_logger, get_logger
from utils.exceptions import GitSleuthException, ValidationError, RateLimitError
from utils.validators import URLValidator, TextValidator, SessionValidator
from utils.rate_limiter import rate_limiter
from utils.cache import cache_manager
from utils.health import health_checker, metrics_collector
from config import config

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(
    level=config.get('LOG_LEVEL', 'INFO'),
    log_file=config.get('LOG_FILE'),
    json_format=config.get('LOG_FORMAT') == 'json'
)

app = FastAPI(
    title="GitSleuth API",
    version="1.0.0",
    description="AI-Powered GitHub Repository Analyzer with RAG",
    docs_url="/docs" if config.is_development() else None,
    redoc_url="/redoc" if config.is_development() else None
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('CORS_ORIGINS', ['http://localhost:3000']),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# In-memory storage for sessions (in production, use Redis or database)
sessions: Dict[str, dict] = {}

# Initialize services
repo_processor = RepoProcessor()
rag_service = RAGService()
conversation_manager = ConversationManager()

# Security
security = HTTPBearer(auto_error=False)

# Middleware for request processing
@app.middleware("http")
async def process_request(request: Request, call_next):
    """Process requests with logging, metrics, and rate limiting"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Add request ID to headers
    request.state.request_id = request_id
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Rate limiting
        if config.get('RATE_LIMIT_ENABLED', True):
            session_id = request.headers.get('X-Session-ID', 'anonymous')
            is_query = request.url.path.endswith('/query')
            
            rate_limiter.is_allowed(client_ip, session_id, is_query)
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        processing_time = time.time() - start_time
        metrics_collector.increment_counter('requests_total')
        metrics_collector.increment_counter('requests_successful')
        metrics_collector.record_response_time(processing_time)
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = str(processing_time)
        
        logger.info(f"Request {request_id} completed in {processing_time:.3f}s")
        
        return response
        
    except RateLimitError as e:
        metrics_collector.increment_counter('requests_failed')
        logger.warning(f"Rate limit exceeded for {client_ip}: {e}")
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "message": str(e)},
            headers={"X-Request-ID": request_id}
        )
    except Exception as e:
        metrics_collector.increment_counter('requests_failed')
        logger.error(f"Request {request_id} failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "message": "An unexpected error occurred"},
            headers={"X-Request-ID": request_id}
        )

# Global exception handler
@app.exception_handler(GitSleuthException)
async def gitsleuth_exception_handler(request: Request, exc: GitSleuthException):
    """Handle custom GitSleuth exceptions"""
    logger.error(f"GitSleuth exception: {exc.message}", extra={
        'error_code': exc.error_code,
        'details': exc.details,
        'request_id': getattr(request.state, 'request_id', None)
    })
    
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code or "GitSleuthError",
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.message}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": exc.message,
            "details": exc.details
        }
    )

@app.post("/index")
async def index_repository(request: IndexRequest, background_tasks: BackgroundTasks):
    """Start indexing a GitHub repository"""
    try:
        # Validate repository URL
        validated_url = URLValidator.validate_github_url(request.repo_url)
        
        # Check cache for existing session
        cache_key = f"repo_index:{validated_url}"
        if config.get('CACHE_ENABLED', True):
            cached_session = cache_manager.get(cache_key)
            if cached_session and cached_session.get('status') == 'ready':
                logger.info(f"Repository {validated_url} already indexed, returning cached session")
                return {
                    "message": "Repository already indexed.",
                    "session_id": cached_session['session_id'],
                    "cached": True
                }
        
        session_id = str(uuid.uuid4())
        
        # Initialize session
        sessions[session_id] = {
            "status": "indexing",
            "repo_url": validated_url,
            "message": "Repository indexing started...",
            "progress": 0,
            "created_at": time.time()
        }
        
        # Start background indexing task
        background_tasks.add_task(process_repository, session_id, validated_url)
        
        logger.info(f"Started indexing repository {validated_url} with session {session_id}")
        
        return {
            "message": "Repository indexing started.",
            "session_id": session_id,
            "repo_url": validated_url
        }
        
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to start indexing: {e}")
        raise GitSleuthException(f"Failed to start repository indexing: {str(e)}")

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get indexing status for a session"""
    try:
        # Validate session ID
        validated_session_id = SessionValidator.validate_session_id(session_id)
        
        if validated_session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = sessions[validated_session_id]
        
        # Add additional metadata
        session_data['session_id'] = validated_session_id
        session_data['uptime'] = time.time() - session_data.get('created_at', time.time())
        
        return StatusResponse(**session_data)
        
    except ValidationError as e:
        raise e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for session {session_id}: {e}")
        raise GitSleuthException(f"Failed to get session status: {str(e)}")

@app.post("/query")
async def query_repository(request: QueryRequest):
    """Query the indexed repository with conversation support"""
    try:
        # Validate inputs
        validated_session_id = SessionValidator.validate_session_id(request.session_id)
        validated_question = TextValidator.validate_question(request.question)
        validated_history = TextValidator.validate_conversation_history(request.conversation_history)
        
        if validated_session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[validated_session_id]
        if session["status"] != "ready":
            raise HTTPException(status_code=400, detail="Repository not ready for querying")
        
        # Check cache for similar queries
        cache_key = f"query:{validated_session_id}:{hash(validated_question)}"
        if config.get('CACHE_ENABLED', True):
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached result for query in session {validated_session_id}")
                return QueryResponse(**cached_result)
        
        # Query the RAG service with conversation support
        result = await rag_service.query(
            question=validated_question,
            session_id=validated_session_id,
            conversation_history=validated_history
        )
        
        # Cache the result
        if config.get('CACHE_ENABLED', True):
            cache_manager.set(cache_key, result, ttl=config.get('CACHE_TTL', 3600))
        
        # Record metrics
        metrics_collector.increment_counter('queries_total')
        metrics_collector.increment_counter('queries_successful')
        
        logger.info(f"Query processed successfully for session {validated_session_id}")
        
        return QueryResponse(**result)
        
    except ValidationError as e:
        raise e
    except HTTPException:
        raise
    except Exception as e:
        metrics_collector.increment_counter('queries_failed')
        logger.error(f"Query failed for session {request.session_id}: {e}")
        raise GitSleuthException(f"Query failed: {str(e)}")

@app.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    conversation = conversation_manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

@app.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 10):
    """Get conversation history"""
    history = conversation_manager.get_conversation_history(conversation_id, limit)
    return {"history": history}

@app.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history"""
    success = conversation_manager.clear_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation cleared successfully"}

@app.get("/conversation/{conversation_id}/stats")
async def get_conversation_stats(conversation_id: str):
    """Get conversation statistics"""
    stats = conversation_manager.get_conversation_stats(conversation_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return stats

async def process_repository(session_id: str, repo_url: str):
    """Background task to process repository"""
    try:
        sessions[session_id]["message"] = "Cloning repository..."
        sessions[session_id]["progress"] = 10
        
        # Clone and process repository
        repo_path = await repo_processor.clone_and_process_repo(repo_url, session_id)
        
        sessions[session_id]["message"] = "Creating vector index..."
        sessions[session_id]["progress"] = 50
        
        # Create vector index
        await rag_service.create_index(repo_path, session_id)
        
        sessions[session_id]["status"] = "ready"
        sessions[session_id]["message"] = "Repository ready for querying!"
        sessions[session_id]["progress"] = 100
        
    except Exception as e:
        sessions[session_id]["status"] = "error"
        sessions[session_id]["message"] = f"Indexing failed: {str(e)}"
        sessions[session_id]["progress"] = 0

@app.get("/")
async def root():
    """Root endpoint with basic API information"""
    return {
        "message": "GitSleuth API is running",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        health_data = health_checker.run_all_checks()
        status_code = 200 if health_data['overall_status'] == 'healthy' else 503
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )

@app.get("/health/{check_name}")
async def specific_health_check(check_name: str):
    """Specific health check endpoint"""
    try:
        result = health_checker.run_health_check(check_name)
        status_code = 200 if 'error' not in result else 503
        
        return JSONResponse(
            status_code=status_code,
            content=result
        )
    except Exception as e:
        logger.error(f"Health check {check_name} failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": str(e)}
        )

@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    try:
        metrics = metrics_collector.get_metrics()
        cache_stats = cache_manager.get_stats()
        
        return {
            "application_metrics": metrics,
            "cache_metrics": cache_stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise GitSleuthException(f"Failed to get metrics: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get application statistics"""
    try:
        return {
            "active_sessions": len(sessions),
            "ready_sessions": len([s for s in sessions.values() if s.get('status') == 'ready']),
            "indexing_sessions": len([s for s in sessions.values() if s.get('status') == 'indexing']),
            "error_sessions": len([s for s in sessions.values() if s.get('status') == 'error']),
            "conversations": len(conversation_manager.conversations),
            "uptime": time.time() - health_checker.start_time,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise GitSleuthException(f"Failed to get stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Use configuration values
    uvicorn.run(
        app,
        host=config.get('API_HOST', '0.0.0.0'),
        port=config.get('API_PORT', 8000),
        reload=config.get('API_RELOAD', False),
        log_level=config.get('LOG_LEVEL', 'info').lower()
    )
