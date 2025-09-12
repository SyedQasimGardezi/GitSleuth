import tree_sitter
from tree_sitter import Language, Parser
from pathlib import Path
from typing import List, Dict, Any
import os

class SemanticChunker:
    def __init__(self):
        self.parsers = {}
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """Initialize tree-sitter parsers for different languages"""
        try:
            # Python parser
            PY_LANGUAGE = Language('tree_sitter_python', 'python')
            self.parsers['python'] = Parser(PY_LANGUAGE)
            
            # JavaScript parser
            JS_LANGUAGE = Language('tree_sitter_javascript', 'javascript')
            self.parsers['javascript'] = Parser(JS_LANGUAGE)
            
            # TypeScript parser
            TS_LANGUAGE = Language('tree_sitter_typescript', 'typescript')
            self.parsers['typescript'] = Parser(TS_LANGUAGE)
            
            # Java parser
            JAVA_LANGUAGE = Language('tree_sitter_java', 'java')
            self.parsers['java'] = Parser(JAVA_LANGUAGE)
            
            # C++ parser
            CPP_LANGUAGE = Language('tree_sitter_cpp', 'cpp')
            self.parsers['cpp'] = Parser(CPP_LANGUAGE)
            
        except Exception as e:
            print(f"Warning: Could not initialize tree-sitter parsers: {e}")
            self.parsers = {}
    
    def get_language_from_extension(self, file_extension: str) -> str:
        """Map file extension to tree-sitter language"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'cpp',
            '.h': 'cpp',
            '.hpp': 'cpp'
        }
        return extension_map.get(file_extension.lower(), None)
    
    def extract_semantic_chunks(self, content: str, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """Extract semantic chunks from code content"""
        chunks = []
        
        # Get language for tree-sitter parsing
        language = self.get_language_from_extension(file_type)
        
        if language and language in self.parsers:
            try:
                # Parse with tree-sitter
                tree = self.parsers[language].parse(bytes(content, 'utf8'))
                chunks = self._extract_from_ast(tree, content, file_path, language)
            except Exception as e:
                print(f"Tree-sitter parsing failed for {file_path}: {e}")
                # Fallback to basic chunking
                chunks = self._fallback_chunking(content, file_path)
        else:
            # Fallback to basic chunking for unsupported languages
            chunks = self._fallback_chunking(content, file_path)
        
        return chunks
    
    def _extract_from_ast(self, tree, content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
        """Extract semantic chunks from AST"""
        chunks = []
        lines = content.split('\n')
        
        def traverse_node(node, depth=0):
            if node.type in self._get_semantic_node_types(language):
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                # Extract the code block
                code_block = '\n'.join(lines[node.start_point[0]:node.end_point[0] + 1])
                
                if len(code_block.strip()) > 50:  # Only include substantial chunks
                    chunk = {
                        'content': code_block,
                        'file_path': file_path,
                        'start_line': start_line,
                        'end_line': end_line,
                        'type': node.type,
                        'language': language,
                        'is_semantic': True
                    }
                    chunks.append(chunk)
            
            # Traverse children
            for child in node.children:
                traverse_node(child, depth + 1)
        
        traverse_node(tree.root_node)
        return chunks
    
    def _get_semantic_node_types(self, language: str) -> List[str]:
        """Get semantic node types for each language"""
        node_types = {
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
        return node_types.get(language, [])
    
    def _fallback_chunking(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Fallback to basic chunking when tree-sitter fails"""
        # Simple chunking by double newlines
        chunks = []
        sections = content.split('\n\n')
        
        for i, section in enumerate(sections):
            if len(section.strip()) > 50:
                chunk = {
                    'content': section.strip(),
                    'file_path': file_path,
                    'start_line': None,
                    'end_line': None,
                    'type': 'text_section',
                    'language': 'text',
                    'is_semantic': False
                }
                chunks.append(chunk)
        
        return chunks
    
    def chunk_document(self, content: str, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """Main method to chunk a document semantically"""
        if not content or len(content.strip()) < 10:
            return []
        
        # Try semantic chunking first
        chunks = self.extract_semantic_chunks(content, file_path, file_type)
        
        # If no semantic chunks found, fallback to basic chunking
        if not chunks:
            chunks = self._fallback_chunking(content, file_path)
        
        # Add metadata to each chunk
        for i, chunk in enumerate(chunks):
            chunk['chunk_id'] = i
            chunk['chunk_size'] = len(chunk['content'])
        
        return chunks
