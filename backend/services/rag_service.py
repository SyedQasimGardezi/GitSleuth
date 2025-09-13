import os
import re
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import config
from .semantic_chunker import SemanticChunker
from .conversation_manager import ConversationManager
from utils.logger import get_logger
from utils.exceptions import EmbeddingError, DatabaseError


class RAGService:
    def __init__(self):
        self.logger = get_logger(__name__)

        # Config
        self.openai_api_key = config.get("OPENAI_API_KEY")
        self.chroma_db_path = config.get("CHROMA_DB_PATH")
        self.chunk_size = config.get("CHUNK_SIZE", 1000)
        self.chunk_overlap = config.get("CHUNK_OVERLAP", 100)
        self.max_tokens = config.get("OPENAI_MAX_TOKENS", 4000)
        self.temperature = config.get("OPENAI_TEMPERATURE", 0.1)
        self.model_name = config.get("OPENAI_MODEL", "gpt-4")

        # OpenAI services
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

        # ChromaDB
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

        # Thread pool for parallel file I/O + embeddings
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count() or 4)

        # Prompt template

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert code analyst. Answer questions about the provided codebase based ONLY on the code snippets provided.

        Guidelines:
        1. Base your answer ONLY on the provided code context.
        2. Be specific and reference exact file names and line numbers when possible.
        3. If the context doesn't contain enough information, say so clearly.
        4. Focus on code structure, functionality, and relationships.
        5. Provide clear, actionable insights about the codebase.

        Confidence Rating:
        - Determine the confidence based on how strongly the provided context supports your answer.
        - High: Answer is fully supported by the code context.
        - Medium: Answer is partially supported by the context.
        - Low: Answer is mostly a guess or context is missing.

        Code Context:
        {context}

        Previous Conversation:
        {conversation_context}

        Question: {question}

        Answer your response **followed by confidence in this exact format**:
        <answer_text>
        [CONFIDENCE: high/medium/low]
        Do NOT skip the confidence rating.
        """),
            ("human", "{question}")
        ])


    # ------------------ FAST INDEXING ------------------

    async def create_index(self, repo_path: str, session_id: str):
        """Parallel file reading, batching embeddings, async Chroma writes"""
        collection_name = f"repo_{session_id}"

        # reset collection if exists
        try:
            self.chroma_client.delete_collection(collection_name)
        except Exception:
            pass

        collection = self.chroma_client.create_collection(
            name=collection_name,
            metadata={"session_id": session_id, "repo_path": repo_path},
        )

        # Collect all files
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".pytest_cache"}]
            for file in files:
                path = Path(root) / file
                if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf"}:
                    all_files.append(path)

        # Parallel read + chunk
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(self.executor, self._process_file, path, repo_path) for path in all_files]
        results = await asyncio.gather(*tasks)

        # Flatten list of docs
        chunks: List[Document] = [doc for docs in results for doc in docs if docs]

        self.logger.info(f"Total chunks: {len(chunks)}")

        # ------------------ Parallel embedding + write ------------------
        batch_size = 512
        semaphore = asyncio.Semaphore(4)  # limit concurrency

        async def embed_and_write(batch, i):
            async with semaphore:
                texts = [c.page_content for c in batch]
                metadatas = [c.metadata for c in batch]
                ids = [f"{session_id}_{c.metadata['chunk_id']}" for c in batch]

                embeddings = await loop.run_in_executor(self.executor, self.embeddings.embed_documents, texts)

                await loop.run_in_executor(
                    self.executor,
                    lambda: collection.add(
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas,
                        ids=ids,
                    )
                )

                self.logger.info(f"Embedded {i+len(batch)}/{len(chunks)} chunks")

        tasks = [
            embed_and_write(chunks[i:i + batch_size], i)
            for i in range(0, len(chunks), batch_size)
        ]
        await asyncio.gather(*tasks)

        return len(chunks)

    def _process_file(self, file_path: Path, repo_path: str) -> List[Document]:
        """Read + chunk one file"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                return []

            relative = str(file_path.relative_to(repo_path))
            semantic_chunks = self.semantic_chunker.chunk_document(content, relative, file_path.suffix)

            docs = []
            for i, chunk in enumerate(semantic_chunks):
                docs.append(Document(
                    page_content=chunk["content"],
                    metadata={
                        "file_path": relative,
                        "file_name": file_path.name,
                        "file_type": file_path.suffix,
                        "chunk_id": i,
                        "start_line": chunk.get("start_line"),
                        "end_line": chunk.get("end_line"),
                        "chunk_type": chunk.get("type", "text"),
                        "language": chunk.get("language", "text"),
                        "is_semantic": chunk.get("is_semantic", False),
                    },
                ))
            return docs
        except Exception as e:
            self.logger.warning(f"Failed to process {file_path}: {e}")
            return []

    # ------------------ QUERY ------------------


    async def query(self, question: str, session_id: str, conversation_id: str = None, conversation_history=None):
        """Query Chroma + LLM and return answer with accurate confidence."""
        collection_name = f"repo_{session_id}"
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception:
            raise Exception("Repo not indexed")

        # Create conversation if not exists
        if not conversation_id:
            conversation_id = self.conversation_manager.create_conversation(session_id)

        self.conversation_manager.add_message(conversation_id, "user", question)
        conversation_context = self.conversation_manager.get_conversation_context(conversation_id)

        # Embed query
        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(self.executor, self.embeddings.embed_query, question)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )

        context_parts, sources = [], []
        distances = results["distances"][0] if results["distances"] and results["distances"][0] else []

        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], distances):
            # Skip very distant matches
            if dist > 0.8:
                continue
            file_info = f"File: {meta['file_path']}"
            if meta.get("start_line"):
                file_info += f" (lines {meta.get('start_line')}-{meta.get('end_line')})"
            context_parts.append(f"{file_info}\n{doc}")
            sources.append({
                "file": meta["file_path"],
                "snippet": doc[:200] + "...",
                "line_number": meta.get("start_line")
            })

        # Determine confidence based on average embedding distance
        def compute_confidence(distances: list) -> str:
            if not distances:
                return "low"
            avg_distance = sum(distances) / len(distances)
            if avg_distance < 0.25:
                return "high"
            elif avg_distance < 0.5:
                return "medium"
            else:
                return "low"

        if not context_parts:
            confidence = "low"
            answer = "No relevant context found"
            self.conversation_manager.add_message(conversation_id, "assistant", answer, confidence=confidence)
            return {
                "answer": answer,
                "sources": [],
                "confidence": confidence,
                "conversation_id": conversation_id
            }

        # Prepare prompt
        prompt = self.prompt_template.format_messages(
            context="\n\n---\n\n".join(context_parts),
            conversation_context=conversation_context,
            question=question,
        )

        # LLM call
        response = await self.llm.ainvoke(prompt)
        answer = response.content.strip()

        # Override confidence from embedding similarity
        confidence = compute_confidence(distances)

        # Append confidence to answer for display (optional)
        answer_with_confidence = f"{answer}\n\n[CONFIDENCE: {confidence}]"

        # Save assistant message
        self.conversation_manager.add_message(conversation_id, "assistant", answer_with_confidence, confidence=confidence)

        return {
            "answer": answer_with_confidence,
            "sources": sources,
            "confidence": confidence,
            "conversation_id": conversation_id
        }
