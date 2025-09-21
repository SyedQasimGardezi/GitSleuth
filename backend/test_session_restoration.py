#!/usr/bin/env python3
"""
Test script to verify session restoration from ChromaDB collections
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent))

import chromadb
import time

def test_session_restoration():
    """Test session restoration from ChromaDB collections"""
    try:
        chroma_db_path = Path('./chroma_db')
        if not chroma_db_path.exists():
            print("ChromaDB directory does not exist")
            return
            
        client = chromadb.PersistentClient(path=str(chroma_db_path))
        collections = client.list_collections()
        
        print(f"Found {len(collections)} ChromaDB collections")
        
        sessions = {}
        restored_count = 0
        
        for collection in collections:
            # Extract session ID from collection name (format: repo_{session_id})
            if collection.name.startswith('repo_'):
                session_id = collection.name[5:]  # Remove 'repo_' prefix
                
                # Check if session already exists
                if session_id not in sessions:
                    try:
                        # Get collection metadata to determine if it's ready
                        docs = collection.get(limit=1)
                        if docs['documents']:
                            # Collection has documents, mark as ready
                            sessions[session_id] = {
                                "status": "ready",
                                "repo_url": "https://github.com/SyedQasimGardezi/GitSleuth",
                                "message": "Repository ready for querying!",
                                "progress": 100,
                                "created_at": time.time() - 3600,
                                "restored": True
                            }
                            restored_count += 1
                            print(f"✓ Restored session {session_id} from ChromaDB collection {collection.name}")
                        else:
                            print(f"⚠ Collection {collection.name} has no documents, skipping")
                    except Exception as e:
                        print(f"✗ Failed to restore session {session_id}: {e}")
                else:
                    print(f"ℹ Session {session_id} already exists, skipping")
        
        print(f"\nRestored {restored_count} sessions from ChromaDB collections")
        print(f"Total sessions in memory: {len(sessions)}")
        
        # Test query with one of the restored sessions
        if sessions:
            first_session_id = list(sessions.keys())[0]
            print(f"\nTesting query with session: {first_session_id}")
            
            # Test the query endpoint
            import requests
            try:
                response = requests.post('http://localhost:8000/query', json={
                    'question': 'TELL ME ABOUT setup.bat', 
                    'session_id': first_session_id, 
                    'conversation_history': []
                })
                print(f"Query Status: {response.status_code}")
                if response.status_code == 200:
                    print("✓ Query successful!")
                    result = response.json()
                    print(f"Answer: {result.get('answer', 'No answer')[:200]}...")
                    print(f"Confidence: {result.get('confidence', 'Unknown')}")
                else:
                    print(f"✗ Query failed: {response.text}")
            except Exception as e:
                print(f"✗ Query request failed: {e}")
        
    except Exception as e:
        print(f"✗ Failed to restore sessions from ChromaDB: {e}")

if __name__ == "__main__":
    test_session_restoration()
