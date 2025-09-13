import os
from pathlib import Path
from typing import Dict, Any, Optional
from utils.validators import ConfigValidator
from utils.exceptions import ConfigurationError
from utils.logger import get_logger

logger = get_logger(__name__)

class Config:
    """Configuration management with validation"""

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._load_config()

    # ---------------------------
    # Env Helpers
    # ---------------------------
    def _get_required_env(self, key: str, default: Optional[str] = None) -> str:
        """Get required environment variable or raise ConfigurationError"""
        value = os.getenv(key, default)
        if not value:
            raise ConfigurationError(f"Required environment variable {key} not set")
        return value

    def _get_env_bool(self, key: str, default: str = "false") -> bool:
        return os.getenv(key, default).strip().lower() in {"true", "1", "yes"}

    def _get_env_int(self, key: str, default: str) -> int:
        try:
            return int(os.getenv(key, default))
        except ValueError:
            raise ConfigurationError(f"Invalid integer for {key}")

    def _get_env_float(self, key: str, default: str) -> float:
        try:
            return float(os.getenv(key, default))
        except ValueError:
            raise ConfigurationError(f"Invalid float for {key}")

    # ---------------------------
    # Config Loader
    # ---------------------------
    def _load_config(self) -> None:
        try:
            # OpenAI Configuration
            self._config["OPENAI_API_KEY"] = self._get_required_env("OPENAI_API_KEY")
            self._config["OPENAI_MODEL"] = os.getenv("OPENAI_MODEL", "gpt-4")
            self._config["OPENAI_TEMPERATURE"] = self._get_env_float("OPENAI_TEMPERATURE", "0.1")
            self._config["OPENAI_MAX_TOKENS"] = self._get_env_int("OPENAI_MAX_TOKENS", "4000")

            # API Configuration
            self._config["API_HOST"] = os.getenv("API_HOST", "0.0.0.0")
            self._config["API_PORT"] = self._get_env_int("API_PORT", "8000")
            self._config["API_WORKERS"] = self._get_env_int("API_WORKERS", "1")
            self._config["API_RELOAD"] = self._get_env_bool("API_RELOAD", "false")

            # Database Configuration
            self._config["CHROMA_DB_PATH"] = os.getenv("CHROMA_DB_PATH", "./chroma_db")
            self._config["CHROMA_COLLECTION_PREFIX"] = os.getenv("CHROMA_COLLECTION_PREFIX", "repo_")

            # Text Processing Configuration
            self._config["CHUNK_SIZE"] = self._get_env_int("CHUNK_SIZE", "1000")
            self._config["CHUNK_OVERLAP"] = self._get_env_int("CHUNK_OVERLAP", "200")
            self._config["MAX_FILE_SIZE"] = self._get_env_int("MAX_FILE_SIZE", str(1024 * 1024))  # 1 MB
            self._config["MAX_FILES_PER_REPO"] = self._get_env_int("MAX_FILES_PER_REPO", "10000")

            # Rate Limiting Configuration
            self._config["RATE_LIMIT_ENABLED"] = self._get_env_bool("RATE_LIMIT_ENABLED", "true")
            self._config["RATE_LIMIT_REQUESTS_PER_MINUTE"] = self._get_env_int("RATE_LIMIT_REQUESTS_PER_MINUTE", "100")
            self._config["RATE_LIMIT_QUERIES_PER_MINUTE"] = self._get_env_int("RATE_LIMIT_QUERIES_PER_MINUTE", "20")

            # Caching Configuration
            self._config["CACHE_ENABLED"] = self._get_env_bool("CACHE_ENABLED", "true")
            self._config["CACHE_TTL"] = self._get_env_int("CACHE_TTL", "3600")  # 1 hour
            self._config["CACHE_TYPE"] = os.getenv("CACHE_TYPE", "memory")  # memory or file

            # Logging Configuration
            self._config["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
            log_file = os.getenv("LOG_FILE", "logs/gitsleuth.log")
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            self._config["LOG_FILE"] = log_file
            self._config["LOG_FORMAT"] = os.getenv("LOG_FORMAT", "json")  # json or text

            # Security Configuration
            self._config["CORS_ORIGINS"] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            self._config["SECRET_KEY"] = self._get_required_env(
                "SECRET_KEY", "gitsleuth-secret-key-change-in-production"
            )

            # File Processing Configuration
            self._config["VALID_EXTENSIONS"] = {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
                ".cs", ".php", ".rb", ".go", ".rs", ".swift", ".kt", ".scala",
                ".md", ".txt", ".json", ".yaml", ".yml", ".xml", ".html", ".css",
                ".scss", ".sass", ".less", ".vue", ".svelte",
            }

            self._config["IGNORE_DIRS"] = {
                ".git", "node_modules", "__pycache__", ".pytest_cache",
                "venv", "env", ".venv", ".env", "dist", "build",
                "target", ".next", ".nuxt", "coverage", ".nyc_output",
                "vendor", "bower_components", ".gradle", ".idea", ".vscode",
            }

            # Final Validation
            self._validate_config()

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration error: {e}")

    # ---------------------------
    # Validation
    # ---------------------------
    def _validate_config(self) -> None:
        try:
            # Validate OpenAI
            ConfigValidator.validate_openai_key(self._config["OPENAI_API_KEY"])

            # Validate chunk configuration
            chunk_size = ConfigValidator.validate_chunk_size(self._config["CHUNK_SIZE"])
            chunk_overlap = ConfigValidator.validate_chunk_overlap(
                self._config["CHUNK_OVERLAP"], chunk_size
            )
            self._config["CHUNK_SIZE"] = chunk_size
            self._config["CHUNK_OVERLAP"] = chunk_overlap

            # Validate ranges
            if not (1 <= self._config["API_PORT"] <= 65535):
                raise ConfigurationError("API_PORT must be between 1 and 65535")
            if not (0 <= self._config["OPENAI_TEMPERATURE"] <= 2):
                raise ConfigurationError("OPENAI_TEMPERATURE must be between 0 and 2")
            if self._config["MAX_FILE_SIZE"] < 1024:  # At least 1KB
                raise ConfigurationError("MAX_FILE_SIZE must be at least 1024 bytes")

            logger.info("Configuration validated successfully")

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ConfigurationError(f"Configuration validation error: {e}")

    # ---------------------------
    # Accessors
    # ---------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()

    def update(self, key: str, value: Any) -> None:
        self._config[key] = value

    def is_development(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "development"

    def is_production(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


# ---------------------------
# Global Instance + Exports
# ---------------------------
config = Config()

OPENAI_API_KEY = config.get("OPENAI_API_KEY")
API_HOST = config.get("API_HOST")
API_PORT = config.get("API_PORT")
CHROMA_DB_PATH = config.get("CHROMA_DB_PATH")
CHUNK_SIZE = config.get("CHUNK_SIZE")
CHUNK_OVERLAP = config.get("CHUNK_OVERLAP")
MAX_FILE_SIZE = config.get("MAX_FILE_SIZE")
VALID_EXTENSIONS = config.get("VALID_EXTENSIONS")
IGNORE_DIRS = config.get("IGNORE_DIRS")
