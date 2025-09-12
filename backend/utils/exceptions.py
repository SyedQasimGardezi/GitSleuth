"""Custom exceptions for GitSleuth application"""

class GitSleuthException(Exception):
    """Base exception for GitSleuth application"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class RepositoryError(GitSleuthException):
    """Repository-related errors"""
    pass

class IndexingError(GitSleuthException):
    """Indexing-related errors"""
    pass

class QueryError(GitSleuthException):
    """Query-related errors"""
    pass

class ValidationError(GitSleuthException):
    """Validation-related errors"""
    pass

class ConfigurationError(GitSleuthException):
    """Configuration-related errors"""
    pass

class RateLimitError(GitSleuthException):
    """Rate limiting errors"""
    pass

class ConversationError(GitSleuthException):
    """Conversation-related errors"""
    pass

class ChunkingError(GitSleuthException):
    """Chunking-related errors"""
    pass

class EmbeddingError(GitSleuthException):
    """Embedding-related errors"""
    pass

class DatabaseError(GitSleuthException):
    """Database-related errors"""
    pass
