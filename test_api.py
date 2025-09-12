#!/usr/bin/env python3
"""
Simple test script to verify the GitSleuth API is working
"""

import requests
import time
import json

API_BASE_URL = "http://localhost:8000"

def test_api():
    print("Testing GitSleuth API...")
    
    # Test 1: Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"✅ API is running: {response.json()}")
    except Exception as e:
        print(f"❌ API is not running: {e}")
        return
    
    # Test 2: Index a small repository
    test_repo = "https://github.com/octocat/Hello-World"
    print(f"\n📦 Testing with repository: {test_repo}")
    
    try:
        # Start indexing
        response = requests.post(f"{API_BASE_URL}/index", json={"repo_url": test_repo})
        if response.status_code == 200:
            session_id = response.json()["session_id"]
            print(f"✅ Indexing started with session ID: {session_id}")
        else:
            print(f"❌ Failed to start indexing: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error starting indexing: {e}")
        return
    
    # Test 3: Poll for status
    print("\n⏳ Waiting for indexing to complete...")
    max_attempts = 30  # 1 minute timeout
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{API_BASE_URL}/status/{session_id}")
            if response.status_code == 200:
                status = response.json()
                print(f"Status: {status['status']} - {status['message']}")
                
                if status["status"] == "ready":
                    print("✅ Indexing completed successfully!")
                    break
                elif status["status"] == "error":
                    print(f"❌ Indexing failed: {status['message']}")
                    return
            else:
                print(f"❌ Failed to get status: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return
        
        time.sleep(2)
        attempt += 1
    
    if attempt >= max_attempts:
        print("❌ Timeout waiting for indexing to complete")
        return
    
    # Test 4: Query the repository
    print("\n❓ Testing query functionality...")
    test_questions = [
        "What is this repository about?",
        "What files are in this repository?",
        "What is the main purpose of this code?"
    ]
    
    for question in test_questions:
        try:
            print(f"\nQuestion: {question}")
            response = requests.post(f"{API_BASE_URL}/query", json={
                "session_id": session_id,
                "question": question
            })
            
            if response.status_code == 200:
                result = response.json()
                print(f"Answer: {result['answer']}")
                if result['sources']:
                    print(f"Sources: {len(result['sources'])} files referenced")
            else:
                print(f"❌ Query failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error querying: {e}")
    
    print("\n🎉 API test completed!")

if __name__ == "__main__":
    test_api()
