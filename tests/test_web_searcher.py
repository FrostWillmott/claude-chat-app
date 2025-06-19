import pytest
import json
from unittest.mock import patch, MagicMock

from app import WebSearcher

def test_search_web_brave():
    """Test web search using Brave Search API"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'web': {
            'results': [
                {
                    'title': 'Test Result 1',
                    'url': 'https://example.com/1',
                    'description': 'This is test result 1'
                },
                {
                    'title': 'Test Result 2',
                    'url': 'https://example.com/2',
                    'description': 'This is test result 2'
                }
            ]
        }
    }
    
    with patch('app.BRAVE_API_KEY', 'mock-api-key'):
        with patch('requests.get', return_value=mock_response):
            results = WebSearcher.search_web('test query', 2)
    
    assert len(results) == 2
    assert results[0]['title'] == 'Test Result 1'
    assert results[0]['url'] == 'https://example.com/1'
    assert results[0]['snippet'] == 'This is test result 1'
    assert results[0]['source'] == 'brave'
    
    assert results[1]['title'] == 'Test Result 2'
    assert results[1]['url'] == 'https://example.com/2'
    assert results[1]['snippet'] == 'This is test result 2'
    assert results[1]['source'] == 'brave'

def test_search_web_duckduckgo():
    """Test web search using DuckDuckGo"""
    # Create mock HTML response with search results
    mock_html = """
    <div class="result">
        <a class="result__a" href="https://example.com/1">Test Result 1</a>
        <a class="result__snippet">This is test result 1</a>
    </div>
    <div class="result">
        <a class="result__a" href="https://example.com/2">Test Result 2</a>
        <a class="result__snippet">This is test result 2</a>
    </div>
    """
    
    mock_response = MagicMock()
    mock_response.content = mock_html.encode('utf-8')
    
    with patch('app.BRAVE_API_KEY', None):
        with patch('requests.get', return_value=mock_response):
            results = WebSearcher.search_web('test query', 2)
    
    assert len(results) == 2
    assert results[0]['title'] == 'Test Result 1'
    assert results[0]['url'] == 'https://example.com/1'
    assert results[0]['snippet'] == 'This is test result 1'
    assert results[0]['source'] == 'duckduckgo'
    
    assert results[1]['title'] == 'Test Result 2'
    assert results[1]['url'] == 'https://example.com/2'
    assert results[1]['snippet'] == 'This is test result 2'
    assert results[1]['source'] == 'duckduckgo'

def test_search_web_error():
    """Test web search error handling"""
    with patch('app.BRAVE_API_KEY', 'mock-api-key'):
        with patch('requests.get', side_effect=Exception('Test error')):
            results = WebSearcher.search_web('test query')
    
    assert results == []

def test_fetch_page_content():
    """Test fetching page content"""
    mock_html = """
    <html>
        <head>
            <title>Test Page</title>
            <script>This should be removed</script>
            <style>This should be removed</style>
        </head>
        <body>
            <h1>Test Page Content</h1>
            <p>This is a test paragraph.</p>
        </body>
    </html>
    """
    
    mock_response = MagicMock()
    mock_response.content = mock_html.encode('utf-8')
    
    with patch('requests.get', return_value=mock_response):
        content = WebSearcher.fetch_page_content('https://example.com')
    
    assert 'Test Page Content' in content
    assert 'This is a test paragraph.' in content
    assert 'This should be removed' not in content

def test_fetch_page_content_error():
    """Test fetch page content error handling"""
    with patch('requests.get', side_effect=Exception('Test error')):
        content = WebSearcher.fetch_page_content('https://example.com')
    
    assert 'Error fetching content' in content