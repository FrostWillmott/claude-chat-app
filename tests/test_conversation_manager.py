import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

from app import ConversationManager

@pytest.fixture
def conversation_manager():
    return ConversationManager()

def test_get_or_create_conversation(conversation_manager):
    """Test creating a new conversation"""
    session_id = 'test-session-id'
    
    # Get a new conversation
    conversation = conversation_manager.get_or_create_conversation(session_id)
    
    # Check that the conversation was created with the expected structure
    assert session_id in conversation_manager.conversations
    assert 'messages' in conversation
    assert 'created_at' in conversation
    assert 'last_updated' in conversation
    assert 'files' in conversation
    assert 'search_history' in conversation
    assert isinstance(conversation['messages'], list)
    assert isinstance(conversation['files'], list)
    assert isinstance(conversation['search_history'], list)
    assert isinstance(conversation['created_at'], datetime)
    assert isinstance(conversation['last_updated'], datetime)
    
    # Get the same conversation again
    conversation2 = conversation_manager.get_or_create_conversation(session_id)
    
    # Check that we got the same conversation
    assert conversation is conversation2

def test_add_message(conversation_manager):
    """Test adding a message to a conversation"""
    session_id = 'test-session-id'
    role = 'user'
    content = 'Test message'
    
    # Add a message
    message = conversation_manager.add_message(session_id, role, content)
    
    # Check that the message was added with the expected structure
    conversation = conversation_manager.get_or_create_conversation(session_id)
    assert len(conversation['messages']) == 1
    assert conversation['messages'][0] == message
    assert message['role'] == role
    assert message['content'] == content
    assert message['type'] == 'text'
    assert 'id' in message
    assert 'timestamp' in message
    assert 'metadata' in message
    assert isinstance(message['metadata'], dict)

def test_add_message_with_metadata(conversation_manager):
    """Test adding a message with metadata"""
    session_id = 'test-session-id'
    role = 'assistant'
    content = 'Test response'
    message_type = 'response'
    metadata = {'token_count': 100, 'model': 'claude-sonnet-4'}
    
    # Add a message with metadata
    message = conversation_manager.add_message(session_id, role, content, message_type, metadata)
    
    # Check that the message was added with the expected structure
    conversation = conversation_manager.get_or_create_conversation(session_id)
    assert len(conversation['messages']) == 1
    assert conversation['messages'][0] == message
    assert message['role'] == role
    assert message['content'] == content
    assert message['type'] == message_type
    assert message['metadata'] == metadata

def test_add_file(conversation_manager):
    """Test adding a file to a conversation"""
    session_id = 'test-session-id'
    file_info = {
        'filename': 'test.txt',
        'content': 'Test file content',
        'mime_type': 'text/plain',
        'size': 17
    }
    
    # Add a file
    conversation_manager.add_file(session_id, file_info)
    
    # Check that the file was added
    conversation = conversation_manager.get_or_create_conversation(session_id)
    assert len(conversation['files']) == 1
    assert conversation['files'][0] == file_info

def test_add_search(conversation_manager):
    """Test adding a search to a conversation"""
    session_id = 'test-session-id'
    query = 'test query'
    results = [
        {
            'title': 'Test Result',
            'url': 'https://example.com',
            'snippet': 'This is a test search result',
            'source': 'test'
        }
    ]
    
    # Add a search
    conversation_manager.add_search(session_id, query, results)
    
    # Check that the search was added
    conversation = conversation_manager.get_or_create_conversation(session_id)
    assert len(conversation['search_history']) == 1
    assert conversation['search_history'][0]['query'] == query
    assert conversation['search_history'][0]['results'] == results
    assert 'timestamp' in conversation['search_history'][0]

def test_get_messages_for_api(conversation_manager):
    """Test getting messages formatted for the API"""
    session_id = 'test-session-id'
    
    # Add some messages
    conversation_manager.add_message(session_id, 'user', 'User message 1')
    conversation_manager.add_message(session_id, 'assistant', 'Assistant response 1')
    conversation_manager.add_message(session_id, 'user', 'User message 2')
    
    # Add a file message
    conversation_manager.add_message(
        session_id, 
        'user', 
        'File message', 
        'file', 
        {
            'filename': 'test.txt',
            'file_content': 'Test file content'
        }
    )
    
    # Get messages for API
    api_messages = conversation_manager.get_messages_for_api(session_id)
    
    # Check that the messages are formatted correctly
    assert len(api_messages) == 4
    assert api_messages[0]['role'] == 'user'
    assert api_messages[0]['content'] == 'User message 1'
    assert api_messages[1]['role'] == 'assistant'
    assert api_messages[1]['content'] == 'Assistant response 1'
    assert api_messages[2]['role'] == 'user'
    assert api_messages[2]['content'] == 'User message 2'
    assert api_messages[3]['role'] == 'user'
    assert 'File: test.txt' in api_messages[3]['content']
    assert 'Content: Test file content' in api_messages[3]['content']

def test_export_conversation(conversation_manager):
    """Test exporting a conversation"""
    session_id = 'test-session-id'
    
    # Add some data to the conversation
    conversation_manager.add_message(session_id, 'user', 'User message')
    conversation_manager.add_message(session_id, 'assistant', 'Assistant response')
    conversation_manager.add_file(session_id, {'filename': 'test.txt', 'content': 'Test content'})
    conversation_manager.add_search(session_id, 'test query', [{'title': 'Test Result'}])
    
    # Export the conversation
    exported = conversation_manager.export_conversation(session_id)
    
    # Check that the export has the expected structure
    assert 'messages' in exported
    assert 'files' in exported
    assert 'search_history' in exported
    assert 'created_at' in exported
    assert 'last_updated' in exported
    assert len(exported['messages']) == 2
    assert len(exported['files']) == 1
    assert len(exported['search_history']) == 1
    assert isinstance(exported['created_at'], str)
    assert isinstance(exported['last_updated'], str)