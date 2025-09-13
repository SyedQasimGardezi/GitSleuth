import os
import shutil
from pathlib import Path
from git import Repo
from typing import List
import aiofiles
import asyncio
from fastapi.concurrency import run_in_threadpool
# Import config values directly to avoid circular imports
import os
VALID_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
    ".cs", ".php", ".rb", ".go", ".rs", ".swift", ".kt", ".scala",
    ".md", ".txt", ".json", ".yaml", ".yml", ".xml", ".html", ".css",
    ".scss", ".sass", ".less", ".vue", ".svelte",
}

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache",
    "venv", "env", ".venv", ".env", "dist", "build",
    "target", ".next", ".nuxt", "coverage", ".nyc_output",
    "vendor", "bower_components", ".gradle", ".idea", ".vscode",
}

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "1048576"))  # 1 MB


class RepoProcessor:
    def __init__(self):
        self.temp_dir = Path("temp_repos")
        self.temp_dir.mkdir(exist_ok=True)

        self.valid_extensions = {ext.lower() for ext in VALID_EXTENSIONS}
        self.ignore_dirs = set(IGNORE_DIRS)

    def clone_repo(self, repo_url: str) -> str:
        """
        Clone repository and return path to cloned repo.
        Synchronous method for use with run_in_threadpool.
        """
        import uuid
        repo_path = self.temp_dir / str(uuid.uuid4())

        # Clean existing directory if any
        if repo_path.exists():
            shutil.rmtree(repo_path)

        # Clone repo
        print(f"Cloning {repo_url}...")
        Repo.clone_from(repo_url, repo_path)
        print(f"Repository cloned to {repo_path}")

        return str(repo_path)

    def get_files(self, repo_path: str) -> List[str]:
        """
        Get list of files to process from repository.
        Synchronous method for use with run_in_threadpool.
        """
        files = []
        repo_path_obj = Path(repo_path)
        
        for root, dirs, filenames in os.walk(repo_path_obj):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_process_file(file_path):
                    files.append(str(file_path))
        
        print(f"Found {len(files)} files to process")
        return files

    def process_file(self, file_path: str, session_id: str) -> None:
        """
        Process a single file and add to vector store.
        Synchronous method for use with run_in_threadpool.
        """
        try:
            file_path_obj = Path(file_path)
            if self._should_process_file(file_path_obj):
                # Read file content
                content = self._read_file_sync(file_path_obj)
                if content and self._is_valid_content(content):
                    # This will be handled by the RAG service
                    print(f"Processed file: {file_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def _read_file_sync(self, file_path: Path) -> str:
        """Read file content synchronously with fallback encodings"""
        for encoding in ("utf-8", "latin-1"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                break
        return ""

    async def clone_and_process_repo(self, repo_url: str, session_id: str, rag_service=None) -> str:
        repo_path = self.temp_dir / session_id
        if repo_path.exists():
            shutil.rmtree(repo_path)

        print(f"Cloning {repo_url}...")
        await run_in_threadpool(Repo.clone_from, repo_url, repo_path)

        # Process files and store in RAGService
        processed_files = await self._process_files(repo_path, session_id, rag_service)
        print(f"Processed {len(processed_files)} files")

        return str(repo_path)


    async def _process_files(self, repo_path: Path) -> List[Path]:
        """Process and filter files in the repository asynchronously"""
        tasks = []

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

            for file in files:
                file_path = Path(root) / file

                if self._should_process_file(file_path):
                    tasks.append(self._validate_file(file_path))

        # Run tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter valid files
        return [res for res in results if isinstance(res, Path)]

    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed"""
        if file_path.suffix.lower() not in self.valid_extensions:
            return False

        if any(part in self.ignore_dirs for part in file_path.parts):
            return False

        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                return False
        except OSError:
            return False

        return True

    async def _validate_file(self, file_path: Path) -> Path | None:
        """Read and validate file content"""
        try:
            content = await self._read_file(file_path)
            if content and self._is_valid_content(content):
                return file_path
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
        return None

    async def _read_file(self, file_path: Path) -> str:
        """Read file content with fallback encodings"""
        for encoding in ("utf-8", "latin-1"):
            try:
                async with aiofiles.open(file_path, "r", encoding=encoding) as f:
                    return await f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                break
        return ""

    def _is_valid_content(self, content: str) -> bool:
        """Check if content is valid for processing"""
        if not content.strip():
            return False
        if "\x00" in content:  # likely binary
            return False
        return True

    async def get_file_content(self, file_path: str) -> str:
        """Get content of a specific file asynchronously"""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception:
            return ""