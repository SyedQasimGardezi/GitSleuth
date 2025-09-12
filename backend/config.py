import os

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# ChromaDB Configuration
CHROMA_DB_PATH = "./chroma_db"

# Text Processing Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_FILE_SIZE = 1024 * 1024  # 1MB

# Valid file extensions
VALID_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', 
    '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
    '.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.html', '.css',
    '.scss', '.sass', '.less', '.vue', '.svelte'
}

# Directories to ignore
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.pytest_cache', 
    'venv', 'env', '.venv', '.env', 'dist', 'build', 
    'target', '.next', '.nuxt', 'coverage', '.nyc_output',
    'vendor', 'bower_components', '.gradle', '.idea', '.vscode'
}
