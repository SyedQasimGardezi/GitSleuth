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
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Chat prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert code analyst. Answer questions about the provided codebase based ONLY on the code snippets provided. 

Guidelines:
1. Base your answer ONLY on the provided code context
2. Be specific and reference exact file names and line numbers when possible
3. If the context doesn't contain enough information, say so clearly
4. Focus on code structure, functionality, and relationships
5. Provide clear, actionable insights about the codebase

Code Context:
{context}

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
        
        # Process all files in the repository
        documents = []
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
                        # Create document
                        relative_path = str(file_path.relative_to(repo_path))
                        doc = Document(
                            page_content=content,
                            metadata={
                                "file_path": relative_path,
                                "file_name": file_path.name,
                                "file_type": file_path.suffix
                            }
                        )
                        documents.append(doc)
                
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
        
        # Split documents into chunks
        chunks = []
        for doc in documents:
            doc_chunks = self.text_splitter.split_documents([doc])
            for chunk in doc_chunks:
                chunk.metadata["chunk_id"] = len(chunks)
                chunks.append(chunk)
        
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
    
    async def query(self, question: str, session_id: str) -> Dict[str, Any]:
        """Query the indexed repository"""
        collection_name = f"repo_{session_id}"
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except:
            raise Exception("Repository not indexed or session not found")
        
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
                
            context_parts.append(f"File: {metadata['file_path']}\n{doc}")
            
            # Extract relevant snippet (first 200 chars)
            snippet = doc[:200] + "..." if len(doc) > 200 else doc
            
            sources.append({
                "file": metadata["file_path"],
                "snippet": snippet,
                "line_number": None  # Could be enhanced to include line numbers
            })
        
        if not context_parts:
            return {
                "answer": "I couldn't find relevant information in the codebase to answer your question. Please try rephrasing your question or check if the repository was indexed correctly.",
                "sources": []
            }
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate answer using LLM
        prompt = self.prompt_template.format_messages(
            context=context,
            question=question
        )
        
        response = await self.llm.ainvoke(prompt)
        answer = response.content
        
        return {
            "answer": answer,
            "sources": sources
        }
    
    def delete_session(self, session_id: str):
        """Delete session data"""
        collection_name = f"repo_{session_id}"
        try:
            self.chroma_client.delete_collection(collection_name)
        except:
            pass
