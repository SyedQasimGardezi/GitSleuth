import os
import json
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
import asyncio
from config import OPENAI_API_KEY, CHROMA_DB_PATH, CHUNK_SIZE, CHUNK_OVERLAP
from .semantic_chunker import SemanticChunker
from .conversation_manager import ConversationManager

class RAGService:
    def __init__(self):
        self.openai_api_key = OPENAI_API_KEY
        
        # Initialize OpenAI services
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)
        self.llm = ChatOpenAI(
            openai_api_key=self.openai_api_key,
            model="gpt-4",
            temperature=0.1
        )
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize services
        self.semantic_chunker = SemanticChunker()
        self.conversation_manager = ConversationManager()
        
        # Text splitter for fallback chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Chat prompt template with confidence scoring
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert code analyst. Answer questions about the provided codebase based ONLY on the code snippets provided. 

Guidelines:
1. Base your answer ONLY on the provided code context
2. Be specific and reference exact file names and line numbers when possible
3. If the context doesn't contain enough information, say so clearly
4. Focus on code structure, functionality, and relationships
5. Provide clear, actionable insights about the codebase
6. At the end of your answer, provide a confidence score: [CONFIDENCE: high/medium/low]

Code Context:
{context}

Previous Conversation:
{conversation_context}

Question: {question}

Answer:"""),
            ("human", "{question}")
        ])
    
    async def create_index(self, repo_path: str, session_id: str):
        """Create vector index for the repository"""
        collection_name = f"repo_{session_id}"
        
        # Create or get collection
        try:
            collection = self.chroma_client.get_collection(collection_name)
            self.chroma_client.delete_collection(collection_name)
        except:
            pass
        
        collection = self.chroma_client.create_collection(
            name=collection_name,
            metadata={"session_id": session_id, "repo_path": repo_path}
        )
        
        # Process all files in the repository with semantic chunking
        chunks = []
        for root, dirs, files in os.walk(repo_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.pytest_cache'}]
            
            for file in files:
                file_path = Path(root) / file
                
                # Skip binary files and large files
                if file_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf'}:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if content and len(content.strip()) > 0:
                        relative_path = str(file_path.relative_to(repo_path))
                        
                        # Use semantic chunking
                        semantic_chunks = self.semantic_chunker.chunk_document(
                            content, relative_path, file_path.suffix
                        )
                        
                        # Convert to Document objects
                        for chunk_data in semantic_chunks:
                            doc = Document(
                                page_content=chunk_data['content'],
                                metadata={
                                    "file_path": relative_path,
                                    "file_name": file_path.name,
                                    "file_type": file_path.suffix,
                                    "chunk_id": len(chunks),
                                    "start_line": chunk_data.get('start_line'),
                                    "end_line": chunk_data.get('end_line'),
                                    "chunk_type": chunk_data.get('type', 'text'),
                                    "language": chunk_data.get('language', 'text'),
                                    "is_semantic": chunk_data.get('is_semantic', False)
                                }
                            )
                            chunks.append(doc)
                
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
        
        # Generate embeddings and store in ChromaDB
        print(f"Creating embeddings for {len(chunks)} chunks...")
        
        # Process in batches to avoid rate limits
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Generate embeddings
            texts = [chunk.page_content for chunk in batch]
            embeddings = self.embeddings.embed_documents(texts)
            
            # Prepare data for ChromaDB
            ids = [f"{session_id}_{chunk.metadata['chunk_id']}" for chunk in batch]
            metadatas = [chunk.metadata for chunk in batch]
            
            # Add to collection
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"Processed batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
        
        print(f"Index created with {len(chunks)} chunks")
    
    async def query(self, question: str, session_id: str, conversation_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Query the indexed repository with conversation support"""
        collection_name = f"repo_{session_id}"
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except:
            raise Exception("Repository not indexed or session not found")
        
        # Create conversation if not provided
        if not conversation_id:
            conversation_id = self.conversation_manager.create_conversation(session_id)
        
        # Add user message to conversation
        self.conversation_manager.add_message(conversation_id, "user", question)
        
        # Get conversation context
        conversation_context = self.conversation_manager.get_conversation_context(conversation_id)
        
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(question)
        
        # Search for relevant chunks
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=["documents", "metadatas", "distances"]
        )
        
        # Prepare context
        context_parts = []
        sources = []
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results["documents"][0], 
            results["metadatas"][0], 
            results["distances"][0]
        )):
            # Skip if distance is too high (low relevance)
            if distance > 0.8:
                continue
                
            # Enhanced context with line numbers if available
            file_info = f"File: {metadata['file_path']}"
            if metadata.get('start_line') and metadata.get('end_line'):
                file_info += f" (lines {metadata['start_line']}-{metadata['end_line']})"
            elif metadata.get('start_line'):
                file_info += f" (line {metadata['start_line']})"
            
            context_parts.append(f"{file_info}\n{doc}")
            
            # Extract relevant snippet
            snippet = doc[:200] + "..." if len(doc) > 200 else doc
            
            sources.append({
                "file": metadata["file_path"],
                "snippet": snippet,
                "line_number": metadata.get('start_line')
            })
        
        if not context_parts:
            answer = "I couldn't find relevant information in the codebase to answer your question. Please try rephrasing your question or check if the repository was indexed correctly."
            confidence = "low"
        else:
            context = "\n\n---\n\n".join(context_parts)
            
            # Generate answer using LLM with conversation context
            prompt = self.prompt_template.format_messages(
                context=context,
                conversation_context=conversation_context,
                question=question
            )
            
            response = await self.llm.ainvoke(prompt)
            answer = response.content
            
            # Extract confidence score from answer
            confidence = self._extract_confidence_score(answer)
            
            # Clean answer (remove confidence score from text)
            answer = self._clean_confidence_from_answer(answer)
        
        # Add assistant message to conversation
        self.conversation_manager.add_message(conversation_id, "assistant", answer, confidence)
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "conversation_id": conversation_id
        }
    
    def _extract_confidence_score(self, answer: str) -> str:
        """Extract confidence score from LLM response"""
        import re
        
        # Look for [CONFIDENCE: high/medium/low] pattern
        confidence_match = re.search(r'\[CONFIDENCE:\s*(high|medium|low)\]', answer, re.IGNORECASE)
        
        if confidence_match:
            return confidence_match.group(1).lower()
        
        # Default confidence based on answer length and content
        if len(answer) < 50:
            return "low"
        elif "I couldn't find" in answer or "not enough information" in answer:
            return "low"
        elif len(answer) > 200 and "file" in answer.lower():
            return "high"
        else:
            return "medium"
    
    def _clean_confidence_from_answer(self, answer: str) -> str:
        """Remove confidence score from answer text"""
        import re
        
        # Remove [CONFIDENCE: ...] pattern
        cleaned = re.sub(r'\[CONFIDENCE:\s*(high|medium|low)\]', '', answer, flags=re.IGNORECASE)
        return cleaned.strip()
    
    def delete_session(self, session_id: str):
        """Delete session data"""
        collection_name = f"repo_{session_id}"
        try:
            self.chroma_client.delete_collection(collection_name)
        except:
            pass
