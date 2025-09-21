from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.concurrency import run_in_threadpool
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

# Function to restore sessions from ChromaDB collections
def restore_sessions_from_chromadb():
    """Restore sessions from existing ChromaDB collections on startup"""
    try:
        import chromadb
        from pathlib import Path
        
        chroma_db_path = Path('./chroma_db')
        if not chroma_db_path.exists():
            logger.info("ChromaDB directory does not exist, no sessions to restore")
            return
            
        client = chromadb.PersistentClient(path=str(chroma_db_path))
        collections = client.list_collections()
        
        logger.info(f"Found {len(collections)} ChromaDB collections")
        
        restored_count = 0
        for collection in collections:
            # Extract session ID from collection name (format: repo_{session_id})
            if collection.name.startswith('repo_'):
                session_id = collection.name[5:]  # Remove 'repo_' prefix
                
                # Check if session already exists
                if session_id not in sessions:
                    try:
                        # Get collection metadata to determine if it's ready
                        docs = collection.get(limit=1)
                        if docs['documents']:
                            # Collection has documents, mark as ready
                            sessions[session_id] = {
                                "status": "ready",
                                "repo_url": "https://github.com/SyedQasimGardezi/GitSleuth",  # Default for now
                                "message": "Repository ready for querying!",
                                "progress": 100,
                                "created_at": time.time() - 3600,  # Assume created 1 hour ago
                                "restored": True
                            }
                            restored_count += 1
                            logger.info(f"Restored session {session_id} from ChromaDB collection {collection.name}")
                        else:
                            logger.info(f"Collection {collection.name} has no documents, skipping")
                    except Exception as e:
                        logger.warning(f"Failed to restore session {session_id}: {e}")
                else:
                    logger.info(f"Session {session_id} already exists, skipping")
        
        logger.info(f"Restored {restored_count} sessions from ChromaDB collections")
        logger.info(f"Total sessions in memory: {len(sessions)}")
        
    except Exception as e:
        logger.error(f"Failed to restore sessions from ChromaDB: {e}")

# Restore sessions on startup
restore_sessions_from_chromadb()

# Confidence computation function
def compute_confidence(answer: str, sources: list) -> str:
    """Compute confidence level based on answer quality and source relevance"""
    if not answer or len(answer.strip()) < 10:
        return "low"
    
    if not sources or len(sources) == 0:
        return "low"
    
    # Check for indicators of high confidence
    if len(sources) >= 3 and len(answer) > 100:
        return "high"
    elif len(sources) >= 2 and len(answer) > 50:
        return "medium"
    else:
        return "low"

# Security
security = HTTPBearer(auto_error=False)

# Middleware for request processing
@app.middleware("http")
async def process_request(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    client_ip = request.client.host if request.client else "unknown"

    try:
        # Rate limiting
        if config.get('RATE_LIMIT_ENABLED', True):
            session_id = request.headers.get('X-Session-ID', 'anonymous')
            is_query = request.url.path.endswith('/query')
            rate_limiter.is_allowed(client_ip, session_id, is_query)

        # Process request
        response = await call_next(request)
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

# Exception handlers
@app.exception_handler(GitSleuthException)
async def gitsleuth_exception_handler(request: Request, exc: GitSleuthException):
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
    logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": exc.message,
            "details": exc.details
        }
    )

# ---- API Endpoints ----
@app.post("/index")
async def index_repository(request: IndexRequest, background_tasks: BackgroundTasks):
    try:
        validated_url = URLValidator.validate_github_url(request.repo_url)
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
        sessions[session_id] = {
            "status": "indexing",
            "repo_url": validated_url,
            "message": "Repository indexing started...",
            "progress": 0,
            "created_at": time.time()
        }

        # Start background indexing
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
    try:
        validated_session_id = SessionValidator.validate_session_id(session_id)
        if validated_session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        session_data = sessions[validated_session_id]
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
    try:
        validated_session_id = SessionValidator.validate_session_id(request.session_id)
        validated_question = TextValidator.validate_question(request.question)
        validated_history = TextValidator.validate_conversation_history(request.conversation_history)

        # Check if session exists in memory, if not try to restore from ChromaDB
        if validated_session_id not in sessions:
            # Try to restore session from ChromaDB
            try:
                import chromadb
                from pathlib import Path
                
                chroma_db_path = Path('./chroma_db')
                if chroma_db_path.exists():
                    client = chromadb.PersistentClient(path=str(chroma_db_path))
                    collection_name = f"repo_{validated_session_id}"
                    
                    try:
                        collection = client.get_collection(collection_name)
                        # If collection exists, restore the session
                        sessions[validated_session_id] = {
                            "status": "ready",
                            "repo_url": "restored_from_chromadb",
                            "message": "Session restored from ChromaDB",
                            "progress": 100,
                            "created_at": time.time()
                        }
                        logger.info(f"Restored session {validated_session_id} from ChromaDB collection {collection_name}")
                    except Exception:
                        # Collection doesn't exist, session is invalid
                        raise HTTPException(status_code=404, detail="Session not found")
                else:
                    raise HTTPException(status_code=404, detail="Session not found")
            except Exception as e:
                logger.error(f"Failed to restore session {validated_session_id}: {e}")
                raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[validated_session_id]
        if session["status"] != "ready":
            raise HTTPException(status_code=400, detail="Repository not ready for querying")

        cache_key = f"query:{validated_session_id}:{hash(validated_question)}"
        if config.get('CACHE_ENABLED', True):
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached result for query in session {validated_session_id}")
                return QueryResponse(**cached_result)

            result = await rag_service.query(
                question=validated_question,
                session_id=validated_session_id,
                conversation_history=validated_history
            )

            if config.get('CACHE_ENABLED', True):
                cache_manager.set(cache_key, result, ttl=config.get('CACHE_TTL', 3600))

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
    conversation = conversation_manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@app.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 10):
    history = conversation_manager.get_conversation_history(conversation_id, limit)
    return {"history": history}

@app.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    success = conversation_manager.clear_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation cleared successfully"}

@app.get("/conversation/{conversation_id}/stats")
async def get_conversation_stats(conversation_id: str):
    stats = conversation_manager.get_conversation_stats(conversation_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return stats

# ---- Background Repository Processing with concurrency ----
MAX_FILE_CONCURRENCY = 10
MAX_CHUNK_CONCURRENCY = 10

async def process_repository(session_id: str, repo_url: str):
    try:
        sessions[session_id]["status"] = "indexing"
        sessions[session_id]["message"] = "Starting repository processing..."
        sessions[session_id]["progress"] = 0

        # Step 1: Clone repository
        sessions[session_id]["message"] = "Cloning repository..."
        sessions[session_id]["progress"] = 5
        repo_path = await run_in_threadpool(repo_processor.clone_repo, repo_url)
        await asyncio.sleep(0)

        # Step 2: Process files concurrently
        files = await run_in_threadpool(repo_processor.get_files, repo_path)
        total_files = len(files)
        file_counter = 0

        async def process_file(file_path):
            nonlocal file_counter
            await run_in_threadpool(repo_processor.process_file, file_path, session_id)
            file_counter += 1
            sessions[session_id]["progress"] = 5 + int((file_counter / total_files) * 45)
            sessions[session_id]["message"] = f"Processing file {file_counter}/{total_files}"
            await asyncio.sleep(0)

        file_semaphore = asyncio.Semaphore(MAX_FILE_CONCURRENCY)
        async def sem_file(file_path):
            async with file_semaphore:
                await process_file(file_path)

        await asyncio.gather(*(sem_file(f) for f in files))

        # Step 3: Index vector chunks concurrently
        sessions[session_id]["message"] = "Creating vector index..."
        index_chunks = await run_in_threadpool(rag_service.get_indexable_chunks, repo_path)
        total_chunks = len(index_chunks)
        chunk_counter = 0

        async def index_chunk(chunk):
            nonlocal chunk_counter
            await run_in_threadpool(rag_service.add_to_index, chunk, session_id)
            chunk_counter += 1
            sessions[session_id]["progress"] = 50 + int((chunk_counter / total_chunks) * 45)
            sessions[session_id]["message"] = f"Indexing chunk {chunk_counter}/{total_chunks}"
            await asyncio.sleep(0)

        chunk_semaphore = asyncio.Semaphore(MAX_CHUNK_CONCURRENCY)
        async def sem_chunk(chunk):
            async with chunk_semaphore:
                await index_chunk(chunk)

        await asyncio.gather(*(sem_chunk(c) for c in index_chunks))

        # Step 4: Complete
        sessions[session_id]["status"] = "ready"
        sessions[session_id]["message"] = "Repository ready for querying!"
        sessions[session_id]["progress"] = 100

    except Exception as e:
        sessions[session_id]["status"] = "error"
        sessions[session_id]["message"] = f"Indexing failed: {str(e)}"
        sessions[session_id]["progress"] = 0

# ---- Health, metrics, root ----
@app.get("/")
async def root():
    return {"message": "GitSleuth API is running", "version": "1.0.0", "status": "healthy", "timestamp": time.time()}

@app.get("/health")
async def health_check():
    try:
        health_data = health_checker.run_all_checks()
        status_code = 200 if health_data['overall_status'] == 'healthy' else 503
        return JSONResponse(status_code=status_code, content=health_data)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=503, content={"overall_status": "unhealthy", "error": str(e), "timestamp": time.time()})

@app.get("/health/{check_name}")
async def specific_health_check(check_name: str):
    try:
        result = health_checker.run_health_check(check_name)
        status_code = 200 if 'error' not in result else 503
        return JSONResponse(status_code=status_code, content=result)
    except Exception as e:
        logger.error(f"Health check {check_name} failed: {e}")
        return JSONResponse(status_code=503, content={"error": str(e)})

@app.get("/metrics")
async def get_metrics():
    try:
        metrics = metrics_collector.get_metrics()
        cache_stats = cache_manager.get_stats()
        return {"application_metrics": metrics, "cache_metrics": cache_stats, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise GitSleuthException(f"Failed to get metrics: {str(e)}")

@app.get("/stats")
async def get_stats():
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

@app.get("/sessions")
async def get_sessions():
    """Get all available sessions"""
    try:
        import chromadb
        from pathlib import Path
        
        available_sessions = []
        
        # Add sessions from memory
        for session_id, session_data in sessions.items():
            available_sessions.append({
                "session_id": session_id,
                "status": session_data["status"],
                "repo_url": session_data.get("repo_url", "unknown"),
                "created_at": session_data.get("created_at", 0)
            })
        
        # Add sessions from ChromaDB that aren't in memory
        chroma_db_path = Path('./chroma_db')
        if chroma_db_path.exists():
            client = chromadb.PersistentClient(path=str(chroma_db_path))
            collections = client.list_collections()
            
            for collection in collections:
                if collection.name.startswith('repo_'):
                    session_id = collection.name[5:]  # Remove 'repo_' prefix
                    if session_id not in sessions:
                        available_sessions.append({
                            "session_id": session_id,
                            "status": "ready",
                            "repo_url": "restored_from_chromadb",
                            "created_at": 0
                        })
        
        return {"sessions": available_sessions}
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        return {"sessions": []}

# ---- Run app ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.get('API_HOST', '0.0.0.0'),
        port=config.get('API_PORT', 8000),
        reload=config.get('API_RELOAD', False),
        log_level=config.get('LOG_LEVEL', 'info').lower()
    )