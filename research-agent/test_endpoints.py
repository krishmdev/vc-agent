import requests
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from main import app, generate_resource_article, resource_chat_endpoint
from fastapi.testclient import TestClient

client = TestClient(app)

def test_generate_resource_article_mocked():
    """
    Test the generate_resource_article endpoint with a mocked Gemini client.
    This ensures the endpoint logic is correct without making real API calls.
    """
    with patch("main.genai.Client") as MockClient:
        # Setup mock
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.text = "# Mocked Article\nThis is a test article."
        mock_instance.models.generate_content.return_value = mock_response

        # Payload
        payload = {
            "question": "How to calculate TAM?",
            "module": "market",
            "context": "B2B SaaS"
        }

        # Request
        response = client.post("/generate_resource_article", json=payload)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "# Mocked Article" in data["content"]

def test_resource_chat_endpoint_mocked():
    """
    Test the resource_chat endpoint with a mocked Gemini client.
    """
    with patch("main.genai.Client") as MockClient:
         # Setup mock
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.text = "This is a mocked answer."
        mock_instance.models.generate_content.return_value = mock_response

        payload = {
            "message": "Explain the first point.",
            "history": [],
            "resource_context": "Some article content..."
        }

        response = client.post("/resource_chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "This is a mocked answer."

if __name__ == "__main__":
    # If run directly, run pytest
    pytest.main([__file__])
