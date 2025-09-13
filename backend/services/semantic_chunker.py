from tree_sitter import Language, Parser
from pathlib import Path
from typing import List, Dict, Any, Optional

class SemanticChunker:
    # Prebuilt extension map (class-level, no reallocation)
    EXTENSION_MAP = {
        '.py': 'python', '.js': 'javascript', '.jsx': 'javascript',
        '.ts': 'typescript', '.tsx': 'typescript',
        '.java': 'java', '.cpp': 'cpp', '.c': 'cpp',
        '.h': 'cpp', '.hpp': 'cpp'
    }

    NODE_TYPES = {
        'python': [
            'function_definition', 'class_definition', 'import_statement',
            'import_from_statement', 'decorated_definition', 'async_function_definition'
        ],
        'javascript': [
            'function_declaration', 'class_declaration', 'method_definition',
            'import_statement', 'export_statement', 'arrow_function'
        ],
        'typescript': [
            'function_declaration', 'class_declaration', 'method_definition',
            'import_statement', 'export_statement', 'arrow_function',
            'interface_declaration', 'type_alias_declaration'
        ],
        'java': [
            'class_declaration', 'method_declaration', 'constructor_declaration',
            'import_declaration', 'interface_declaration', 'enum_declaration'
        ],
        'cpp': [
            'function_definition', 'class_specifier', 'namespace_definition',
            'include_directive', 'struct_specifier', 'enum_specifier'
        ]
    }

    def __init__(self, so_path: str = "build/my-languages.so"):
        """
        Initialize parsers. You must precompile with something like:
        Language.build_library(
            "build/my-languages.so",
            [
                "vendor/tree-sitter-python",
                "vendor/tree-sitter-javascript",
                "vendor/tree-sitter-typescript/tsx",
                "vendor/tree-sitter-java",
                "vendor/tree-sitter-cpp"
            ]
        )
        """
        self.parsers: Dict[str, Parser] = {}
        try:
            self.languages = {
                "python": Language(so_path, "python"),
                "javascript": Language(so_path, "javascript"),
                "typescript": Language(so_path, "typescript"),
                "java": Language(so_path, "java"),
                "cpp": Language(so_path, "cpp"),
            }
            for lang, ts_lang in self.languages.items():
                parser = Parser()
                parser.set_language(ts_lang)
                self.parsers[lang] = parser
        except Exception as e:
            print(f"[WARN] Failed to init tree-sitter: {e}")
            self.parsers = {}

    def get_language_from_extension(self, file_extension: str) -> Optional[str]:
        """Fast lookup for extension → language"""
        return self.EXTENSION_MAP.get(file_extension.lower())

    def extract_semantic_chunks(
        self, content: str, file_path: str, file_type: str
    ) -> List[Dict[str, Any]]:
        """Extract semantic chunks from code content"""
        lang = self.get_language_from_extension(file_type)
        if lang and lang in self.parsers:
            try:
                tree = self.parsers[lang].parse(content.encode("utf8"))
                return self._extract_from_ast(tree, content, file_path, lang)
            except Exception as e:
                print(f"[WARN] Tree-sitter failed for {file_path}: {e}")
        # Fallback if unsupported
        return self._fallback_chunking(content, file_path)

    def _extract_from_ast(
        self, tree, content: str, file_path: str, language: str
    ) -> List[Dict[str, Any]]:
        """Iterative AST traversal for speed"""
        chunks = []
        lines = content.splitlines()
        wanted_nodes = set(self.NODE_TYPES.get(language, []))

        cursor = tree.walk()
        stack = [cursor.node]

        while stack:
            node = stack.pop()
            if node.type in wanted_nodes:
                start, end = node.start_point[0], node.end_point[0]
                code_block = "\n".join(lines[start:end + 1])
                if len(code_block.strip()) > 50:
                    chunks.append({
                        "content": code_block,
                        "file_path": file_path,
                        "start_line": start + 1,
                        "end_line": end + 1,
                        "type": node.type,
                        "language": language,
                        "is_semantic": True
                    })
            # push children
            stack.extend(node.children)

        return chunks

    def _fallback_chunking(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Fallback when parsing fails: chunk by paragraphs (~100 lines)"""
        chunks = []
        lines = content.splitlines()
        step = 100  # configurable batch size

        for i in range(0, len(lines), step):
            section = "\n".join(lines[i:i+step]).strip()
            if len(section) > 50:
                chunks.append({
                    "content": section,
                    "file_path": file_path,
                    "start_line": i + 1,
                    "end_line": min(i+step, len(lines)),
                    "type": "text_section",
                    "language": "text",
                    "is_semantic": False
                })
        return chunks

    def chunk_document(
        self, content: str, file_path: str, file_type: str
    ) -> List[Dict[str, Any]]:
        if not content or len(content) < 10:
            return []

        chunks = self.extract_semantic_chunks(content, file_path, file_type)
        if not chunks:
            chunks = self._fallback_chunking(content, file_path)

        for i, ch in enumerate(chunks):
            ch["chunk_id"] = i
            ch["chunk_size"] = len(ch["content"])

        return chunks
