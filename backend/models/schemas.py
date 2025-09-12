from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class IndexRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    session_id: str
    question: str
    conversation_history: Optional[List[Dict[str, str]]] = []

class StatusResponse(BaseModel):
    status: str  # "indexing" | "ready" | "error"
    message: str
    progress: Optional[int] = 0

class Source(BaseModel):
    file: str
    snippet: str
    line_number: Optional[int] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: str  # "high" | "medium" | "low"
    conversation_id: str

class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime
    confidence: Optional[str] = None

class ConversationHistory(BaseModel):
    session_id: str
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime
