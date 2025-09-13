import os
import shutil
from pathlib import Path
from git import Repo
from typing import List
import aiofiles
import asyncio
from fastapi.concurrency import run_in_threadpool
from config import VALID_EXTENSIONS, IGNORE_DIRS, MAX_FILE_SIZE


class RepoProcessor:
    def __init__(self):
        self.temp_dir = Path("temp_repos")
        self.temp_dir.mkdir(exist_ok=True)

        self.valid_extensions = {ext.lower() for ext in VALID_EXTENSIONS}
        self.ignore_dirs = set(IGNORE_DIRS)

    async def clone_and_process_repo(self, repo_url: str, session_id: str) -> str:
        """
        Clone repository and return path to processed files.
        Uses threadpool to avoid blocking event loop.
        """
        repo_path = self.temp_dir / session_id

        # Clean existing directory if any
        if repo_path.exists():
            shutil.rmtree(repo_path)

        # Clone repo in threadpool (non-blocking)
        print(f"Cloning {repo_url}...")
        await run_in_threadpool(Repo.clone_from, repo_url, repo_path)

        # Process files
        processed_files = await self._process_files(repo_path)
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
