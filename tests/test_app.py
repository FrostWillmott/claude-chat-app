import pytest
import json
import os
from unittest.mock import patch, MagicMock

from app import app, conversation_manager

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-key'
    
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_index_route(client):
    """Test that the index route returns the index.html template"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Claude Chat' in response.data

def test_conversation_api(client):
    """Test that the conversation API returns empty conversation for new session"""
    response = client.get('/api/conversation')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'messages' in data
    assert 'files' in data
    assert 'search_history' in data
    assert isinstance(data['messages'], list)
    assert isinstance(data['files'], list)
    assert isinstance(data['search_history'], list)

@patch('app.anthropic_client')
def test_chat_api_empty_message(mock_anthropic, client):
    """Test that the chat API rejects empty messages"""
    response = client.post('/api/chat', 
                          json={'message': ''},
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

@patch('app.anthropic_client')
def test_chat_api_valid_message(mock_anthropic, client):
    """Test that the chat API processes valid messages"""
    # Mock the Anthropic client response
    mock_content = MagicMock()
    mock_content.text = "This is a test response from Claude"
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_response.usage.output_tokens = 10
    mock_anthropic.messages.create.return_value = mock_response
    
    response = client.post('/api/chat', 
                          json={'message': 'Hello, Claude!'},
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'response' in data
    assert data['response'] == "This is a test response from Claude"
    assert 'message_id' in data
    assert 'timestamp' in data

def test_clear_conversation(client):
    """Test that the clear API clears the conversation"""
    # First add a message to the conversation
    with client.session_transaction() as session:
        session['session_id'] = 'test-session'
    
    conversation_manager.add_message('test-session', 'user', 'Test message')
    
    # Then clear the conversation
    response = client.post('/api/clear', 
                          json={},
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify conversation is cleared
    conversation = conversation_manager.get_or_create_conversation('test-session')
    assert len(conversation['messages']) == 0

@patch('app.WebSearcher.search_web')
def test_search_api(mock_search_web, client):
    """Test that the search API returns search results"""
    mock_search_web.return_value = [
        {
            'title': 'Test Result',
            'url': 'https://example.com',
            'snippet': 'This is a test search result',
            'source': 'test'
        }
    ]
    
    response = client.post('/api/search', 
                          json={'query': 'test query'},
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'results' in data
    assert len(data['results']) == 1
    assert data['results'][0]['title'] == 'Test Result'

def test_search_api_empty_query(client):
    """Test that the search API rejects empty queries"""
    response = client.post('/api/search', 
                          json={'query': ''},
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

@patch('app.WebSearcher.fetch_page_content')
def test_fetch_api(mock_fetch_page_content, client):
    """Test that the fetch API returns page content"""
    mock_fetch_page_content.return_value = "This is test page content"
    
    response = client.post('/api/fetch', 
                          json={'url': 'https://example.com'},
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'content' in data
    assert data['content'] == "This is test page content"

def test_fetch_api_empty_url(client):
    """Test that the fetch API rejects empty URLs"""
    response = client.post('/api/fetch', 
                          json={'url': ''},
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data