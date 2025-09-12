from pydantic import BaseModel
from typing import List, Optional

class IndexRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    session_id: str
    question: str

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
