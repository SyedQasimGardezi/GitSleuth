#!/usr/bin/env python3
"""
Demo script for GitSleuth
This script demonstrates how to use the GitSleuth API programmatically
"""

import requests
import time
import json

API_BASE_URL = "http://localhost:8000"

def demo_gitsleuth():
    print("🚀 GitSleuth Demo")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"✅ API Status: {response.json()['message']}")
    except Exception as e:
        print(f"❌ API is not running. Please start the backend first.")
        print("   Run: cd backend && python main.py")
        return
    
    # Demo repository (a small, well-documented repo)
    demo_repo = "https://github.com/octocat/Hello-World"
    print(f"\n📦 Demo Repository: {demo_repo}")
    
    # Step 1: Index the repository
    print("\n1️⃣ Starting repository indexing...")
    try:
        response = requests.post(f"{API_BASE_URL}/index", json={"repo_url": demo_repo})
        if response.status_code == 200:
            session_id = response.json()["session_id"]
            print(f"   Session ID: {session_id}")
        else:
            print(f"   ❌ Failed to start indexing: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Step 2: Wait for indexing to complete
    print("\n2️⃣ Waiting for indexing to complete...")
    max_wait = 60  # 1 minute
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE_URL}/status/{session_id}")
            if response.status_code == 200:
                status = response.json()
                print(f"   Status: {status['status']} - {status['message']}")
                
                if status["status"] == "ready":
                    print("   ✅ Indexing completed!")
                    break
                elif status["status"] == "error":
                    print(f"   ❌ Indexing failed: {status['message']}")
                    return
            else:
                print(f"   ❌ Status check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Error checking status: {e}")
            return
        
        time.sleep(2)
    
    if time.time() - start_time >= max_wait:
        print("   ⏰ Timeout waiting for indexing")
        return
    
    # Step 3: Ask questions
    print("\n3️⃣ Asking questions about the repository...")
    
    questions = [
        "What is this repository about?",
        "What files are included in this repository?",
        "What is the main purpose of this code?",
        "Are there any configuration files?",
        "What programming languages are used?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n   Question {i}: {question}")
        try:
            response = requests.post(f"{API_BASE_URL}/query", json={
                "session_id": session_id,
                "question": question
            })
            
            if response.status_code == 200:
                result = response.json()
                print(f"   Answer: {result['answer']}")
                
                if result['sources']:
                    print(f"   Sources: {len(result['sources'])} files referenced")
                    for source in result['sources'][:2]:  # Show first 2 sources
                        print(f"     - {source['file']}")
            else:
                print(f"   ❌ Query failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error querying: {e}")
        
        time.sleep(1)  # Small delay between questions
    
    print("\n🎉 Demo completed successfully!")
    print("\n💡 Try the web interface at http://localhost:3000")
    print("   Or use your own repository URLs!")

if __name__ == "__main__":
    demo_gitsleuth()
