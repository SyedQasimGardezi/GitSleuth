import chromadb
from pathlib import Path

def check_collections():
    chroma_db_path = Path('./chroma_db')
    client = chromadb.PersistentClient(path=str(chroma_db_path))
    collections = client.list_collections()
    
    print('Available collections:')
    for collection in collections:
        print(f'  {collection.name}')
        try:
            docs = collection.get(limit=3)
            if docs['documents']:
                print(f'    Sample documents: {len(docs["documents"])} docs')
        except Exception as e:
            print(f'    Error getting docs: {e}')
        print()

if __name__ == "__main__":
    check_collections()
