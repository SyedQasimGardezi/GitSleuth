from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

from services.repo_processor import RepoProcessor
from services.rag_service import RAGService
from services.conversation_manager import ConversationManager
from models.schemas import IndexRequest, QueryRequest, StatusResponse, QueryResponse, ConversationHistory

# Load environment variables
load_dotenv()

app = FastAPI(title="GitSleuth API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for sessions (in production, use Redis or database)
sessions: Dict[str, dict] = {}

# Initialize services
repo_processor = RepoProcessor()
rag_service = RAGService()
conversation_manager = ConversationManager()

@app.post("/index")
async def index_repository(request: IndexRequest, background_tasks: BackgroundTasks):
    """Start indexing a GitHub repository"""
    session_id = str(uuid.uuid4())
    
    # Initialize session
    sessions[session_id] = {
        "status": "indexing",
        "repo_url": request.repo_url,
        "message": "Repository indexing started...",
        "progress": 0
    }
    
    # Start background indexing task
    background_tasks.add_task(process_repository, session_id, request.repo_url)
    
    return {"message": "Repository indexing started.", "session_id": session_id}

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get indexing status for a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return StatusResponse(**sessions[session_id])

@app.post("/query")
async def query_repository(request: QueryRequest):
    """Query the indexed repository with conversation support"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    if session["status"] != "ready":
        raise HTTPException(status_code=400, detail="Repository not ready for querying")
    
    try:
        # Query the RAG service with conversation support
        result = await rag_service.query(
            question=request.question,
            session_id=request.session_id,
            conversation_history=request.conversation_history
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

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
    return {"message": "GitSleuth API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
