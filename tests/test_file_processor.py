import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from io import BytesIO

from app import app, FileProcessor
from werkzeug.datastructures import FileStorage

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_process_text_file():
    """Test processing a text file"""
    # Create a temporary text file
    content = "This is a test text file."
    file_obj = BytesIO(content.encode('utf-8'))
    file = FileStorage(
        stream=file_obj,
        filename="test.txt",
        content_type="text/plain"
    )
    
    # Mock magic.from_file to return text/plain
    with patch('magic.from_file', return_value='text/plain'):
        # Mock open to return our file content
        with patch('builtins.open', return_value=BytesIO(content.encode('utf-8'))):
            # Mock os.remove to avoid actually removing files
            with patch('os.remove'):
                result = FileProcessor.process_file(file)
    
    assert result['filename'] == 'test.txt'
    assert result['content'] == 'This is a test text file.'
    assert result['mime_type'] == 'text/plain'

def test_process_pdf_file():
    """Test processing a PDF file"""
    # Create a mock PDF file
    file_obj = BytesIO(b'mock pdf content')
    file = FileStorage(
        stream=file_obj,
        filename="test.pdf",
        content_type="application/pdf"
    )
    
    # Mock magic.from_file to return application/pdf
    with patch('magic.from_file', return_value='application/pdf'):
        # Mock _extract_pdf_text to return a predefined content
        with patch.object(FileProcessor, '_extract_pdf_text', return_value='Extracted PDF content'):
            # Mock os.remove to avoid actually removing files
            with patch('os.remove'):
                result = FileProcessor.process_file(file)
    
    assert result['filename'] == 'test.pdf'
    assert result['content'] == 'Extracted PDF content'
    assert result['mime_type'] == 'application/pdf'

def test_process_docx_file():
    """Test processing a DOCX file"""
    # Create a mock DOCX file
    file_obj = BytesIO(b'mock docx content')
    file = FileStorage(
        stream=file_obj,
        filename="test.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    
    # Mock magic.from_file to return docx mime type
    with patch('magic.from_file', return_value='application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
        # Mock _extract_docx_text to return a predefined content
        with patch.object(FileProcessor, '_extract_docx_text', return_value='Extracted DOCX content'):
            # Mock os.remove to avoid actually removing files
            with patch('os.remove'):
                result = FileProcessor.process_file(file)
    
    assert result['filename'] == 'test.docx'
    assert result['content'] == 'Extracted DOCX content'
    assert result['mime_type'] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

def test_process_excel_file():
    """Test processing an Excel file"""
    # Create a mock Excel file
    file_obj = BytesIO(b'mock excel content')
    file = FileStorage(
        stream=file_obj,
        filename="test.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Mock magic.from_file to return excel mime type
    with patch('magic.from_file', return_value='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
        # Mock _extract_excel_text to return a predefined content
        with patch.object(FileProcessor, '_extract_excel_text', return_value='Extracted Excel content'):
            # Mock os.remove to avoid actually removing files
            with patch('os.remove'):
                result = FileProcessor.process_file(file)
    
    assert result['filename'] == 'test.xlsx'
    assert result['content'] == 'Extracted Excel content'
    assert result['mime_type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def test_process_unsupported_file():
    """Test processing an unsupported file type"""
    # Create a mock unsupported file
    file_obj = BytesIO(b'mock binary content')
    file = FileStorage(
        stream=file_obj,
        filename="test.bin",
        content_type="application/octet-stream"
    )
    
    # Mock magic.from_file to return binary mime type
    with patch('magic.from_file', return_value='application/octet-stream'):
        # Mock os.remove to avoid actually removing files
        with patch('os.remove'):
            result = FileProcessor.process_file(file)
    
    assert result['filename'] == 'test.bin'
    assert "Unsupported file type" in result['content']
    assert result['mime_type'] == 'application/octet-stream'

def test_upload_api(client):
    """Test the file upload API endpoint"""
    # Create a mock text file
    content = "This is a test text file."
    file_obj = BytesIO(content.encode('utf-8'))
    
    # Mock FileProcessor.process_file to return a predefined result
    with patch.object(FileProcessor, 'process_file', return_value={
        'filename': 'test.txt',
        'content': 'This is a test text file.',
        'mime_type': 'text/plain',
        'size': len(content)
    }):
        response = client.post(
            '/api/upload',
            data={'file': (file_obj, 'test.txt', 'text/plain')},
            content_type='multipart/form-data'
        )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['filename'] == 'test.txt'
    assert 'content_preview' in data

def test_upload_api_no_file(client):
    """Test the file upload API endpoint with no file"""
    response = client.post(
        '/api/upload',
        data={},
        content_type='multipart/form-data'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data