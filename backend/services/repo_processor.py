import os
import shutil
import asyncio
from pathlib import Path
from git import Repo
from typing import List, Set
import aiofiles
from config import VALID_EXTENSIONS, IGNORE_DIRS, MAX_FILE_SIZE

class RepoProcessor:
    def __init__(self):
        self.temp_dir = Path("temp_repos")
        self.temp_dir.mkdir(exist_ok=True)
        
        # File extensions to process
        self.valid_extensions = VALID_EXTENSIONS
        
        # Directories to ignore
        self.ignore_dirs = IGNORE_DIRS
    
    async def clone_and_process_repo(self, repo_url: str, session_id: str) -> str:
        """Clone repository and return path to processed files"""
        repo_path = self.temp_dir / session_id
        
        # Clean up existing directory
        if repo_path.exists():
            shutil.rmtree(repo_path)
        
        # Clone repository
        print(f"Cloning {repo_url}...")
        repo = Repo.clone_from(repo_url, repo_path)
        
        # Process files
        processed_files = await self._process_files(repo_path)
        print(f"Processed {len(processed_files)} files")
        
        return str(repo_path)
    
    async def _process_files(self, repo_path: Path) -> List[Path]:
        """Process and filter files in the repository"""
        processed_files = []
        
        for root, dirs, files in os.walk(repo_path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                # Check if file should be processed
                if self._should_process_file(file_path):
                    try:
                        # Read and validate file content
                        content = await self._read_file(file_path)
                        if content and self._is_valid_content(content):
                            processed_files.append(file_path)
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        continue
        
        return processed_files
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed"""
        # Check extension
        if file_path.suffix.lower() not in self.valid_extensions:
            return False
        
        # Check if file is in ignored directory
        for part in file_path.parts:
            if part in self.ignore_dirs:
                return False
        
        # Check file size (skip very large files)
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                return False
        except:
            return False
        
        return True
    
    async def _read_file(self, file_path: Path) -> str:
        """Read file content with proper encoding"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                async with aiofiles.open(file_path, 'r', encoding='latin-1') as f:
                    return await f.read()
            except:
                return ""
        except Exception:
            return ""
    
    def _is_valid_content(self, content: str) -> bool:
        """Check if content is valid for processing"""
        if not content or len(content.strip()) == 0:
            return False
        
        # Skip binary-like content
        if content.count('\x00') > 0:
            return False
        
        return True
    
    def get_file_content(self, file_path: str) -> str:
        """Get content of a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""
