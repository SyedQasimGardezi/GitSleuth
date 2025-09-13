import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class SemanticChunker:
    EXTENSION_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'cpp',
        '.cpp': 'cpp',
        '.h': 'cpp',
        '.hpp': 'cpp'
    }

    def get_language_from_extension(self, file_extension: str) -> Optional[str]:
        return self.EXTENSION_MAP.get(file_extension.lower())

    def chunk_document(
        self, content: str, file_path: str, file_type: str
    ) -> List[Dict[str, Any]]:
        if not content or len(content.strip()) < 10:
            return []

        lang = self.get_language_from_extension(file_type)
        
        # Try language-specific chunking
        if lang == "python":
            chunks = self._extract_python_chunks(content, file_path)
        elif lang == "javascript":
            chunks = self._extract_javascript_chunks(content, file_path)
        elif lang == "typescript":
            chunks = self._extract_typescript_chunks(content, file_path)
        elif lang == "java":
            chunks = self._extract_java_chunks(content, file_path)
        elif lang == "cpp":
            chunks = self._extract_cpp_chunks(content, file_path)
        else:
            chunks = self._fallback_chunking(content, file_path)

        # Add metadata
        for i, ch in enumerate(chunks):
            ch["chunk_id"] = i
            ch["chunk_size"] = len(ch["content"])

        return chunks

    # ---------------- PYTHON CHUNKING ----------------
    def _extract_python_chunks(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start_line = node.lineno - 1
                    end_line = max(getattr(node.body[-1], 'lineno', node.lineno), node.lineno)
                    code_block = "\n".join(lines[node.lineno - 1:end_line])
                    if len(code_block.strip()) > 20:
                        chunks.append({
                            "content": code_block,
                            "file_path": file_path,
                            "start_line": start_line + 1,
                            "end_line": end_line,
                            "type": type(node).__name__,
                            "language": "python",
                            "is_semantic": True
                        })
        except Exception:
            # If AST parsing fails, fallback
            return self._fallback_chunking(content, file_path)

        # If no semantic chunks found, fallback
        if not chunks:
            return self._fallback_chunking(content, file_path)

        return chunks

    # ---------------- JAVASCRIPT CHUNKING ----------------
    def _extract_javascript_chunks(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        lines = content.splitlines()
        
        # Find functions, classes, and objects
        patterns = [
            (r'^(export\s+)?(async\s+)?function\s+(\w+)', 'function'),
            (r'^(export\s+)?class\s+(\w+)', 'class'),
            (r'^(export\s+)?const\s+(\w+)\s*=\s*(async\s+)?\(', 'arrow_function'),
            (r'^(export\s+)?let\s+(\w+)\s*=\s*(async\s+)?\(', 'arrow_function'),
            (r'^(export\s+)?var\s+(\w+)\s*=\s*(async\s+)?\(', 'arrow_function'),
        ]
        
        for i, line in enumerate(lines):
            for pattern, chunk_type in patterns:
                if re.match(pattern, line.strip()):
                    # Find the end of the block
                    end_line = self._find_block_end(lines, i)
                    if end_line > i:
                        code_block = "\n".join(lines[i:end_line])
                        if len(code_block.strip()) > 20:
                            chunks.append({
                                "content": code_block,
                                "file_path": file_path,
                                "start_line": i + 1,
                                "end_line": end_line,
                                "type": chunk_type,
                                "language": "javascript",
                                "is_semantic": True
                            })
        
        return chunks if chunks else self._fallback_chunking(content, file_path)

    # ---------------- TYPESCRIPT CHUNKING ----------------
    def _extract_typescript_chunks(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        lines = content.splitlines()
        
        # TypeScript patterns
        patterns = [
            (r'^(export\s+)?(async\s+)?function\s+(\w+)', 'function'),
            (r'^(export\s+)?class\s+(\w+)', 'class'),
            (r'^(export\s+)?interface\s+(\w+)', 'interface'),
            (r'^(export\s+)?type\s+(\w+)', 'type'),
            (r'^(export\s+)?const\s+(\w+)\s*:\s*\w+\s*=\s*(async\s+)?\(', 'arrow_function'),
            (r'^(export\s+)?let\s+(\w+)\s*:\s*\w+\s*=\s*(async\s+)?\(', 'arrow_function'),
        ]
        
        for i, line in enumerate(lines):
            for pattern, chunk_type in patterns:
                if re.match(pattern, line.strip()):
                    end_line = self._find_block_end(lines, i)
                    if end_line > i:
                        code_block = "\n".join(lines[i:end_line])
                        if len(code_block.strip()) > 20:
                            chunks.append({
                                "content": code_block,
                                "file_path": file_path,
                                "start_line": i + 1,
                                "end_line": end_line,
                                "type": chunk_type,
                                "language": "typescript",
                                "is_semantic": True
                            })
        
        return chunks if chunks else self._fallback_chunking(content, file_path)

    # ---------------- JAVA CHUNKING ----------------
    def _extract_java_chunks(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        lines = content.splitlines()
        
        patterns = [
            (r'^(public|private|protected)?\s*(static\s+)?(final\s+)?class\s+(\w+)', 'class'),
            (r'^(public|private|protected)?\s*(static\s+)?(final\s+)?(void|\w+)\s+(\w+)\s*\(', 'method'),
            (r'^(public|private|protected)?\s*(static\s+)?(final\s+)?(\w+)\s+(\w+)\s*;', 'field'),
        ]
        
        for i, line in enumerate(lines):
            for pattern, chunk_type in patterns:
                if re.match(pattern, line.strip()):
                    end_line = self._find_block_end(lines, i)
                    if end_line > i:
                        code_block = "\n".join(lines[i:end_line])
                        if len(code_block.strip()) > 20:
                            chunks.append({
                                "content": code_block,
                                "file_path": file_path,
                                "start_line": i + 1,
                                "end_line": end_line,
                                "type": chunk_type,
                                "language": "java",
                                "is_semantic": True
                            })
        
        return chunks if chunks else self._fallback_chunking(content, file_path)

    # ---------------- C++ CHUNKING ----------------
    def _extract_cpp_chunks(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        lines = content.splitlines()
        
        patterns = [
            (r'^(class|struct)\s+(\w+)', 'class'),
            (r'^(\w+::)?(\w+)\s+(\w+)\s*\(', 'function'),
            (r'^#include\s*<[^>]+>', 'include'),
            (r'^#define\s+(\w+)', 'define'),
        ]
        
        for i, line in enumerate(lines):
            for pattern, chunk_type in patterns:
                if re.match(pattern, line.strip()):
                    end_line = self._find_block_end(lines, i)
                    if end_line > i:
                        code_block = "\n".join(lines[i:end_line])
                        if len(code_block.strip()) > 20:
                            chunks.append({
                                "content": code_block,
                                "file_path": file_path,
                                "start_line": i + 1,
                                "end_line": end_line,
                                "type": chunk_type,
                                "language": "cpp",
                                "is_semantic": True
                            })
        
        return chunks if chunks else self._fallback_chunking(content, file_path)

    # ---------------- HELPER METHODS ----------------
    def _find_block_end(self, lines: List[str], start_line: int) -> int:
        """Find the end of a code block by counting braces/brackets"""
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char in ['"', "'"] and not in_string:
                    in_string = True
                    continue
                elif char in ['"', "'"] and in_string:
                    in_string = False
                    continue
                    
                if not in_string:
                    if char in ['{', '(']:
                        brace_count += 1
                    elif char in ['}', ')']:
                        brace_count -= 1
                        if brace_count == 0:
                            return i + 1
        
        return len(lines)

    # ---------------- FALLBACK CHUNKING ----------------
    def _fallback_chunking(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        lines = content.splitlines()
        step = max(10, len(lines) // 2)  # chunk small files into at least 1-2 chunks
        for i in range(0, len(lines), step):
            section = "\n".join(lines[i:i+step]).strip()
            if len(section) > 0:  # include even very small sections
                chunks.append({
                    "content": section,
                    "file_path": file_path,
                    "start_line": i + 1,
                    "end_line": min(i + step, len(lines)),
                    "type": "text_section",
                    "language": "text",
                    "is_semantic": False
                })
        return chunks