"""Tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from main import app
from utils.exceptions import GitSleuthException

client = TestClient(app)

class TestIndexEndpoint:
    """Test /index endpoint"""
    
    def test_index_valid_repo(self):
        """Test indexing a valid repository"""
        with patch('main.process_repository') as mock_process:
            response = client.post("/index", json={"repo_url": "https://github.com/facebook/react"})
            
            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert data["message"] == "Repository indexing started."
            assert data["repo_url"] == "https://github.com/facebook/react"
    
    def test_index_invalid_repo(self):
        """Test indexing an invalid repository"""
        response = client.post("/index", json={"repo_url": "not-a-github-url"})
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
    
    def test_index_empty_repo(self):
        """Test indexing with empty repository URL"""
        response = client.post("/index", json={"repo_url": ""})
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

class TestStatusEndpoint:
    """Test /status endpoint"""
    
    def test_status_valid_session(self):
        """Test getting status for valid session"""
        # First create a session
        with patch('main.process_repository'):
            index_response = client.post("/index", json={"repo_url": "https://github.com/facebook/react"})
            session_id = index_response.json()["session_id"]
        
        # Then get status
        response = client.get(f"/status/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "progress" in data
    
    def test_status_invalid_session(self):
        """Test getting status for invalid session"""
        response = client.get("/status/invalid-session-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

class TestQueryEndpoint:
    """Test /query endpoint"""
    
    def test_query_without_session(self):
        """Test querying without valid session"""
        response = client.post("/query", json={
            "session_id": "invalid-session",
            "question": "What is this code doing?"
        })
        
        assert response.status_code == 404
    
    def test_query_invalid_question(self):
        """Test querying with invalid question"""
        # First create a session
        with patch('main.process_repository'):
            index_response = client.post("/index", json={"repo_url": "https://github.com/facebook/react"})
            session_id = index_response.json()["session_id"]
        
        # Mock session as ready
        with patch('main.sessions') as mock_sessions:
            mock_sessions.__contains__ = MagicMock(return_value=True)
            mock_sessions.__getitem__ = MagicMock(return_value={"status": "ready"})
            
            # Mock RAG service
            with patch('main.rag_service.query') as mock_query:
                mock_query.return_value = {
                    "answer": "Test answer",
                    "sources": [],
                    "confidence": "high",
                    "conversation_id": "test-conv"
                }
                
                response = client.post("/query", json={
                    "session_id": session_id,
                    "question": ""  # Empty question
                })
                
                assert response.status_code == 422

class TestHealthEndpoint:
    """Test health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code in [200, 503]  # Could be healthy or unhealthy
        data = response.json()
        assert "overall_status" in data
        assert "timestamp" in data
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "application_metrics" in data
        assert "cache_metrics" in data
    
    def test_stats_endpoint(self):
        """Test stats endpoint"""
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_sessions" in data
        assert "uptime" in data

class TestConversationEndpoints:
    """Test conversation management endpoints"""
    
    def test_get_conversation(self):
        """Test getting conversation"""
        response = client.get("/conversation/invalid-conversation-id")
        
        assert response.status_code == 404
    
    def test_get_conversation_history(self):
        """Test getting conversation history"""
        response = client.get("/conversation/invalid-conversation-id/history")
        
        assert response.status_code == 404
    
    def test_get_conversation_stats(self):
        """Test getting conversation stats"""
        response = client.get("/conversation/invalid-conversation-id/stats")
        
        assert response.status_code == 404
    
    def test_delete_conversation(self):
        """Test deleting conversation"""
        response = client.delete("/conversation/invalid-conversation-id")
        
        assert response.status_code == 404

class TestErrorHandling:
    """Test error handling"""
    
    def test_validation_error_handling(self):
        """Test validation error handling"""
        response = client.post("/index", json={"repo_url": "invalid-url"})
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "message" in data
    
    def test_rate_limit_handling(self):
        """Test rate limit handling"""
        # This would require mocking the rate limiter
        # For now, just test that the endpoint exists
        response = client.get("/health")
        assert response.status_code in [200, 503]

class TestCaching:
    """Test caching functionality"""
    
    def test_cached_query(self):
        """Test that queries are cached"""
        # This would require more complex setup with actual sessions
        # For now, just test that the endpoint exists
        response = client.get("/metrics")
        assert response.status_code == 200
