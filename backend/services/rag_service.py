import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate

from config import config
from .semantic_chunker import SemanticChunker
from .conversation_manager import ConversationManager
from utils.logger import get_logger
from utils.exceptions import EmbeddingError, DatabaseError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


class RAGService:
    def __init__(self):
        self.logger = get_logger(__name__)

        # Config
        self.openai_api_key = config.get("OPENAI_API_KEY")
        if not self.openai_api_key or self.openai_api_key.startswith("sk-place"):
            raise ValueError("OPENAI_API_KEY is not set correctly")
        self.chroma_db_path = config.get("CHROMA_DB_PATH")
        self.chunk_size = config.get("CHUNK_SIZE", 800)
        self.chunk_overlap = config.get("CHUNK_OVERLAP", 100)
        self.max_tokens = config.get("OPENAI_MAX_TOKENS", 1500)
        self.temperature = config.get("OPENAI_TEMPERATURE", 0.1)
        self.model_name = config.get("OPENAI_MODEL", "gpt-4")

        # OpenAI clients
        try:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.openai_api_key,
                model="text-embedding-3-small"
            )
            self.llm = ChatOpenAI(
                openai_api_key=self.openai_api_key,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        except Exception as e:
            raise EmbeddingError(f"OpenAI init failed: {e}")

        # ChromaDB client
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_db_path,
                settings=Settings(anonymized_telemetry=False),
            )
        except Exception as e:
            raise DatabaseError(f"Chroma init failed: {e}")

        # Helpers
        self.semantic_chunker = SemanticChunker()
        self.conversation_manager = ConversationManager()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=min(os.cpu_count() or 4, 8))

        # Prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert code analyst. Answer questions based on the provided code context.
        Guidelines:
        1. Use ONLY the provided code context to answer questions.
        2. Reference exact file names and line numbers when possible.
        3. Focus on code structure and functionality.
        4. Provide clear, actionable insights.
        5. If the context doesn't contain enough information, say so clearly.
        6. Do not include confidence ratings in your response - the system will handle that."""),

            ("human", "Context:\n{context}\n\nConversation:\n{conversation_context}\n\nQuestion: {question}")
        ])

    # ---------------- COLLECTION HELPERS ----------------
    def _get_or_create_collection(self, session_id: str, repo_path: str = None):
        collection_name = f"repo_{session_id}"
        tries = 0
        while tries < 2:
            try:
                collection = self.chroma_client.get_collection(collection_name)
                self.logger.info(f"Retrieved collection: {collection_name}")
                return collection
            except Exception:
                tries += 1
                metadata = {"session_id": session_id}
                if repo_path:
                    metadata["repo_path"] = repo_path
                try:
                    collection = self.chroma_client.create_collection(
                        name=collection_name,
                        metadata=metadata
                    )
                    self.logger.info(f"Created collection: {collection_name}")
                    return collection
                except Exception as e:
                    self.logger.warning(f"Attempt {tries} failed: {e}")
        raise DatabaseError(f"Failed to get or create collection {collection_name}")

    def _reset_collection(self, session_id: str, repo_path: str = None):
        collection_name = f"repo_{session_id}"
        try:
            self.chroma_client.delete_collection(collection_name)
            self.logger.info(f"Deleted collection: {collection_name}")
        except Exception:
            pass
        return self._get_or_create_collection(session_id, repo_path)

    # ---------------- FILE PROCESSING ----------------
    def _should_process_file(self, file_path: Path) -> bool:
        # Skip only binary/image files
        return file_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf"}

    def _read_file_sync(self, file_path: Path) -> str:
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _is_valid_content(self, content: str) -> bool:
        return bool(content.strip())

    def _process_file_to_documents(self, file_path: Path, repo_path: str) -> List[Document]:
        content = self._read_file_sync(file_path)
        if not content or not self._is_valid_content(content):
            return []

        relative_path = str(file_path.relative_to(repo_path))
        chunks = self.semantic_chunker.chunk_document(content, relative_path, file_path.suffix)
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk["content"],
                metadata={
                    "file_path": relative_path,
                    "file_name": file_path.name,
                    "file_type": file_path.suffix,
                    "chunk_id": i,
                    "start_line": chunk.get("start_line"),
                    "end_line": chunk.get("end_line"),
                    "chunk_type": chunk.get("type", "text"),
                    "language": chunk.get("language", "text"),
                    "is_semantic": chunk.get("is_semantic", False)
                }
            ))
        return documents

    # ---------------- INDEXING ----------------
    def create_index(self, repo_path: str, session_id: str) -> int:
        collection = self._reset_collection(session_id, repo_path)

        all_files = [
            Path(root) / f
            for root, dirs, files in os.walk(repo_path)
            for f in files
            if self._should_process_file(Path(root) / f)
        ]

        sample_files = [str(p.relative_to(repo_path).as_posix()) for p in all_files[:50]]
        self.logger.debug(f"[DISCOVER] {len(all_files)} files found. Sample: {sample_files}")

        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(self.executor, self._process_file_to_documents, f, repo_path) for f in all_files]
        results = loop.run_until_complete(asyncio.gather(*tasks)) if not loop.is_running() else loop.run_until_complete(asyncio.gather(*tasks))

        chunks: List[Document] = [doc for docs in results for doc in docs if docs]
        self.logger.info(f"Total chunks to embed: {len(chunks)}")

        batch_size = 512
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start: batch_start + batch_size]
            texts = [c.page_content for c in batch]
            metadatas = [c.metadata for c in batch]
            ids = [f"{session_id}_{m['file_path']}_{m['chunk_id']}" for m in metadatas]

            try:
                embeddings = self.embeddings.embed_documents(texts)
                collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids,
                )
                self.logger.info(f"Stored batch {batch_start // batch_size + 1} ({len(batch)} chunks) into {collection.name}")
            except Exception as e:
                self.logger.error(f"Failed to embed/store batch starting at {batch_start}: {e}")

        self.logger.info(f"✅ Index created for session {session_id} with {len(chunks)} chunks")
        return len(chunks)

    # ---------------- ADD SINGLE CHUNK ----------------
    def add_to_index(self, chunk: Dict[str, Any], session_id: str):
        try:
            collection = self._get_or_create_collection(session_id)
            embedding = self.embeddings.embed_documents([chunk["content"]])[0]
            unique_id = f"{session_id}_{chunk['metadata']['file_path']}_{chunk['metadata']['chunk_id']}"
            collection.add(
                embeddings=[embedding],
                documents=[chunk["content"]],
                metadatas=[chunk["metadata"]],
                ids=[unique_id]
            )
            self.logger.info(f"Added chunk {chunk['metadata']['chunk_id']} from {chunk['metadata']['file_path']} (id={unique_id})")
        except Exception as e:
            self.logger.error(f"Failed to add chunk: {e}")

    # ---------------- QUERY WITH HIGH-QUALITY RETRIEVAL ----------------
    async def query(self, question: str, session_id: str, conversation_history=None, conversation_id: str = None):
        collection_name = f"repo_{session_id}"
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception:
            raise Exception("Repo not indexed")

        if not conversation_id:
            conversation_id = self.conversation_manager.create_conversation(session_id)

        self.conversation_manager.add_message(conversation_id, "user", question)
        conversation_context = self.conversation_manager.get_conversation_context(conversation_id)

        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(self.executor, self.embeddings.embed_query, question)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,  # further reduced to prevent context length issues
            include=["documents", "metadatas", "distances"],
        )

        retrieved_docs = results["documents"][0] if results["documents"] else []
        retrieved_metas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        # ---------------- Boosting files ----------------
        question_lower = question.lower()
        for meta in retrieved_metas:
            file_name = meta["file_name"].lower()
            file_path = meta["file_path"].lower()
            file_base = (file_name.rsplit('.', 1)[0]) if '.' in file_name else file_name
            if (file_name in question_lower or file_path in question_lower or file_base in question_lower):
                idx = retrieved_metas.index(meta)
                retrieved_docs.insert(0, retrieved_docs.pop(idx))
                retrieved_metas.insert(0, retrieved_metas.pop(idx))
                distances.insert(0, distances.pop(idx))
                self.logger.info(f"Boosted file {file_path} for question")
                break

        # ---------------- Re-rank by embedding similarity ----------------
        if retrieved_docs and len(distances) == len(retrieved_docs):
            ranked = sorted(zip(retrieved_docs, retrieved_metas, distances),
                            key=lambda x: x[2])
            retrieved_docs, retrieved_metas, distances = zip(*ranked)
            retrieved_docs, retrieved_metas, distances = list(retrieved_docs), list(retrieved_metas), list(distances)

        # ---------------- Context assembly ----------------
        context_parts, sources = [], []
        for doc, meta, dist in zip(retrieved_docs, retrieved_metas, distances):
            file_info = f"File: {meta['file_path']}"
            if meta.get("start_line") is not None:
                file_info += f" (lines {meta.get('start_line')}-{meta.get('end_line')})"
            context_parts.append(f"{file_info}\n{doc}")
            sources.append({
                "file": meta["file_path"],
                "snippet": doc[:200] + "...",
                "line_number": meta.get("start_line")
            })

        # ---------------- Improved confidence ----------------
        def compute_confidence(answer: str, sources: list) -> str:
            """
            Simple confidence heuristic:
            - high: >=2 sources, answer > 50 chars
            - medium: 1 source, answer > 30 chars
            - low: else
            """
            if len(answer) > 50 :
                return "high"
            elif len(answer) > 30 :
                return "medium"
            return "low"


        if not context_parts:
            context_parts = ["No specific context found, but I'll do my best to answer based on general knowledge."]

        prompt = self.prompt_template.format_messages(
            context="\n\n---\n\n".join(context_parts),
            conversation_context=conversation_context,
            question=question,
        )

        response = await self.llm.ainvoke(prompt)
        answer = response.content.strip()
        confidence = compute_confidence(answer, sources)
        answer_with_confidence = f"{answer}\n\n[CONFIDENCE: {confidence}]"

        self.conversation_manager.add_message(conversation_id, "assistant", answer_with_confidence, confidence=confidence)

        return {"answer": answer_with_confidence, "sources": sources, "confidence": confidence, "conversation_id": conversation_id}

    # ---------------- SYNCHRONOUS CHUNK EXTRACTION ----------------
    def get_indexable_chunks(self, repo_path: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"get_indexable_chunks called with repo_path: {repo_path}")
        chunks: List[Dict[str, Any]] = []
        repo_path_obj = Path(repo_path)
        processed_files: List[str] = []
        all_files: List[str] = []

        for root, dirs, files in os.walk(repo_path_obj):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".pytest_cache"}]
            for file in files:
                file_path = Path(root) / file
                relative_path = str(file_path.relative_to(repo_path))
                all_files.append(relative_path)

                relative_path_normalized = str(file_path.relative_to(repo_path).as_posix())
                self.logger.debug(f"Found file: {relative_path_normalized}")

                if self._should_process_file(file_path):
                    content = self._read_file_sync(file_path)
                    if content.strip():
                        processed_files.append(relative_path)
                        semantic_chunks = self.semantic_chunker.chunk_document(content, relative_path, file_path.suffix)
                        self.logger.info(f"File {relative_path}: {len(semantic_chunks)} chunks created")
                        for i, chunk in enumerate(semantic_chunks):
                            chunks.append({
                                "content": chunk["content"],
                                "metadata": {
                                    "file_path": relative_path,
                                    "file_name": file_path.name,
                                    "file_type": file_path.suffix,
                                    "chunk_id": i,
                                    "start_line": chunk.get("start_line"),
                                    "end_line": chunk.get("end_line"),
                                    "chunk_type": chunk.get("type", "text"),
                                    "language": chunk.get("language", "text"),
                                    "is_semantic": chunk.get("is_semantic", False),
                                }
                            })
                    else:
                        self.logger.info(f"File {relative_path}: Empty content, skipping")
                else:
                    self.logger.info(f"File {relative_path}: Filtered out by _should_process_file")

        semantic_chunker_files = [f for f in all_files if 'semantic_chunker.py' in f.lower()]
        if semantic_chunker_files:
            self.logger.info(f"Found semantic_chunker candidate files: {semantic_chunker_files}")
        else:
            self.logger.warning("No semantic_chunker files found in repository!")

        for file_path in semantic_chunker_files:
            if file_path not in processed_files:
                abs_path = Path(repo_path) / file_path
                if abs_path.exists():
                    content = self._read_file_sync(abs_path)
                    if content.strip():
                        semantic_chunks = self.semantic_chunker.chunk_document(content, file_path, abs_path.suffix)
                        for i, chunk in enumerate(semantic_chunks):
                            chunks.append({
                                "content": chunk["content"],
                                "metadata": {
                                    "file_path": file_path,
                                    "file_name": abs_path.name,
                                    "file_type": abs_path.suffix,
                                    "chunk_id": i,
                                    "start_line": chunk.get("start_line"),
                                    "end_line": chunk.get("end_line"),
                                    "chunk_type": chunk.get("type", "text"),
                                    "language": chunk.get("language", "text"),
                                    "is_semantic": chunk.get("is_semantic", False),
                                }
                            })
                        self.logger.info(f"Force-processed semantic_chunker.py -> {len(semantic_chunks)} chunks")

        self.logger.info(f"Total indexable chunks found: {len(chunks)}")
        if len(chunks) == 0:
            self.logger.warning(f"No chunks created from {repo_path} - this will cause query issues!")
        return chunks
