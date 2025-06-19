import os
import secrets
import uuid
import json
import requests
import magic
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from io import BytesIO

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import anthropic
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document
import pandas as pd
import markdown

load_dotenv()

app = Flask(__name__)
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if os.getenv('FLASK_ENV') == 'development':
        SECRET_KEY = 'dev-secret-key-not-for-production'
        print("WARNING: Using development SECRET_KEY. Set SECRET_KEY environment variable for production!")
    else:
        SECRET_KEY = secrets.token_hex(32)
        print("WARNING: Generated random SECRET_KEY. Set SECRET_KEY environment variable to persist sessions!")

app.config['SECRET_KEY'] = SECRET_KEY

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app, cors_allowed_origins="*")

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

try:
    anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
except Exception as e:
    print(f"Error initializing Anthropic client: {e}")
    anthropic_client = None

BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')
SEARCH_ENDPOINTS = {
    'brave': 'https://api.search.brave.com/res/v1/web/search',
    'duckduckgo': 'https://api.duckduckgo.com/'
}

class FileProcessor:
    @staticmethod
    def process_file(file: FileStorage) -> Dict[str, str]:
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")
            file.save(file_path)

            # Detect file type
            mime_type = magic.from_file(file_path, mime=True)
            content = ""

            if mime_type == 'application/pdf':
                content = FileProcessor._extract_pdf_text(file_path)
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                content = FileProcessor._extract_docx_text(file_path)
            elif mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
                content = FileProcessor._extract_excel_text(file_path)
            elif mime_type.startswith('text/'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = f"Unsupported file type: {mime_type}"

            # Clean up
            os.remove(file_path)

            return {
                'filename': filename,
                'content': content[:10000],  # Limit content size
                'mime_type': mime_type,
                'size': len(content)
            }
        except Exception as e:
            return {'filename': file.filename, 'content': f"Error processing file: {str(e)}", 'error': True}

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    @staticmethod
    def _extract_docx_text(file_path: str) -> str:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

    @staticmethod
    def _extract_excel_text(file_path: str) -> str:
        df = pd.read_excel(file_path)
        return df.to_string()

class WebSearcher:
    @staticmethod
    def search_web(query: str, num_results: int = 5) -> List[Dict]:
        try:
            if BRAVE_API_KEY:
                return WebSearcher._search_brave(query, num_results)
            else:
                return WebSearcher._search_duckduckgo(query, num_results)
        except Exception as e:
            print(f"Search error: {e}")
            return []

    @staticmethod
    def _search_brave(query: str, num_results: int) -> List[Dict]:
        headers = {
            'X-Subscription-Token': BRAVE_API_KEY,
            'Accept': 'application/json'
        }
        params = {
            'q': query,
            'count': num_results,
            'search_lang': 'en',
            'country': 'us',
            'safesearch': 'moderate'
        }

        response = requests.get(SEARCH_ENDPOINTS['brave'], headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get('web', {}).get('results', []):
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('description', ''),
                    'source': 'brave'
                })
            return results
        return []

    @staticmethod
    def _search_duckduckgo(query: str, num_results: int) -> List[Dict]:
        try:
            url = f"https://html.duckduckgo.com/html/?q={query}"
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Claude Chat App)'}
            response = requests.get(url, headers=headers, timeout=10)

            soup = BeautifulSoup(response.content, 'html.parser')
            results = []

            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')

                if title_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href', ''),
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                        'source': 'duckduckgo'
                    })

            return results
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return []

    @staticmethod
    def fetch_page_content(url: str) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Claude Chat App)'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text[:5000]  # Limit content size
        except Exception as e:
            return f"Error fetching content: {str(e)}"

class ExtendedThinking:
    @staticmethod
    def create_thinking_prompt(query: str, mode: str, research_context: str = "") -> str:

        base_thinking = """<thinking>
I need to think through this query carefully and systematically. Let me break this down step by step.

First, let me understand what the user is asking:
{query}

Let me analyze the key components and consider multiple angles:
1. What are the main aspects I need to address?
2. Are there any assumptions I should question?
3. What additional context or information might be relevant?
4. How can I provide the most helpful and comprehensive response?

{mode_specific_thinking}

Let me also consider potential counterarguments or alternative perspectives to ensure I'm being thorough and balanced in my analysis.
</thinking>

{response_instruction}"""

        mode_prompts = {
            'deep_analysis': {
                'thinking': """
For this deep analysis, I should:
- Examine the underlying principles and mechanisms
- Consider historical context and precedents
- Analyze cause-and-effect relationships
- Look for patterns and connections
- Evaluate different theoretical frameworks
- Consider long-term implications and consequences
""",
                'instruction': "Provide a comprehensive, multi-layered analysis that examines the topic from multiple angles, including underlying principles, historical context, and broader implications."
            },

            'research_synthesis': {
                'thinking': f"""
For this research synthesis, I need to:
- Gather information from multiple reliable sources
- Compare and contrast different viewpoints
- Identify consensus and areas of disagreement
- Evaluate the quality and credibility of sources
- Synthesize findings into coherent insights
- Note any gaps in current knowledge

Research context available: {research_context}
""",
                'instruction': "Conduct thorough research using available sources, synthesize findings from multiple perspectives, and provide a well-supported analysis with proper attribution."
            },

            'strategic_thinking': {
                'thinking': """
For strategic thinking, I should:
- Define the problem or opportunity clearly
- Analyze the current situation and context
- Identify key stakeholders and their interests
- Consider various strategic options and scenarios
- Evaluate risks, benefits, and trade-offs
- Think about implementation challenges
- Consider short-term and long-term implications
""",
                'instruction': "Think strategically about this issue, considering multiple scenarios, stakeholder perspectives, implementation challenges, and both short-term and long-term implications."
            },

            'creative_exploration': {
                'thinking': """
For creative exploration, I should:
- Challenge conventional assumptions
- Look for unconventional connections and analogies
- Consider "what if" scenarios
- Think about the problem from different perspectives
- Explore interdisciplinary approaches
- Generate multiple innovative solutions
- Build on ideas to create new possibilities
""",
                'instruction': "Explore this topic creatively, challenging assumptions, making unexpected connections, and generating innovative ideas and solutions."
            }
        }

        selected_mode = mode_prompts.get(mode, mode_prompts['deep_analysis'])

        return base_thinking.format(
            query=query,
            mode_specific_thinking=selected_mode['thinking'],
            response_instruction=selected_mode['instruction']
        )

class ConversationManager:
    def __init__(self):
        self.conversations = {}

    def get_or_create_conversation(self, session_id):
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'messages': [],
                'created_at': datetime.now(),
                'last_updated': datetime.now(),
                'files': [],
                'search_history': []
            }
        return self.conversations[session_id]

    def add_message(self, session_id, role, content, message_type='text', metadata=None):
        conversation = self.get_or_create_conversation(session_id)
        message = {
            'id': str(uuid.uuid4()),
            'role': role,
            'content': content,
            'type': message_type,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        conversation['messages'].append(message)
        conversation['last_updated'] = datetime.now()
        return message

    def add_file(self, session_id, file_info):
        conversation = self.get_or_create_conversation(session_id)
        conversation['files'].append(file_info)

    def add_search(self, session_id, query, results):
        conversation = self.get_or_create_conversation(session_id)
        search_entry = {
            'query': query,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        conversation['search_history'].append(search_entry)

    def get_messages_for_api(self, session_id):
        conversation = self.get_or_create_conversation(session_id)
        api_messages = []

        for msg in conversation['messages']:
            if msg['role'] in ['user', 'assistant']:
                content = msg['content']

                # Add file context if available
                if msg['type'] == 'file' and 'file_content' in msg['metadata']:
                    content = f"File: {msg['metadata']['filename']}\nContent: {msg['metadata']['file_content']}\n\nUser query: {content}"

                api_messages.append({'role': msg['role'], 'content': content})

        return api_messages

    def export_conversation(self, session_id):
        conversation = self.get_or_create_conversation(session_id)
        return {
            'messages': conversation['messages'],
            'files': conversation['files'],
            'search_history': conversation['search_history'],
            'created_at': conversation['created_at'].isoformat(),
            'last_updated': conversation['last_updated'].isoformat()
        }

conversation_manager = ConversationManager()

@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if not anthropic_client:
        return jsonify({'error': 'Claude API not configured'}), 500

    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        use_search = data.get('use_search', False)
        search_query = data.get('search_query', '')
        thinking_mode = data.get('thinking_mode', 'normal')  # New parameter

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        # Handle web search if requested
        search_results = []
        research_context = ""
        if use_search and search_query:
            search_results = WebSearcher.search_web(search_query)
            conversation_manager.add_search(session_id, search_query, search_results)

            # Add search context to the message
            if search_results:
                search_context = "\n\nWeb search results:\n"
                for i, result in enumerate(search_results[:3], 1):
                    search_context += f"{i}. {result['title']}\n{result['snippet']}\nURL: {result['url']}\n\n"
                user_message += search_context
                research_context = search_context

        # Apply extended thinking if requested
        if thinking_mode != 'normal':
            enhanced_prompt = ExtendedThinking.create_thinking_prompt(
                user_message, thinking_mode, research_context
            )
            user_message = enhanced_prompt

        # Add user message to conversation
        user_msg = conversation_manager.add_message(
            session_id,
            'user',
            data.get('message', '').strip(),  # Store original message
            metadata={'thinking_mode': thinking_mode, 'enhanced_prompt_used': thinking_mode != 'normal'}
        )

        # Get conversation history for API
        messages = conversation_manager.get_messages_for_api(session_id)

        # Replace the last message with enhanced prompt if using extended thinking
        if thinking_mode != 'normal':
            messages[-1]['content'] = user_message

        # Adjust token limit based on thinking mode
        max_tokens = 4000 if thinking_mode == 'normal' else 6000

        # Get response from Claude
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=messages
        )

        claude_response = response.content[0].text

        # Add Claude's response to conversation
        claude_message = conversation_manager.add_message(
            session_id,
            'assistant',
            claude_response,
            metadata={
                'search_used': use_search,
                'search_results': search_results,
                'thinking_mode': thinking_mode,
                'token_usage': response.usage.output_tokens if hasattr(response, 'usage') else None
            }
        )

        return jsonify({
            'response': claude_response,
            'message_id': claude_message['id'],
            'timestamp': claude_message['timestamp'],
            'search_results': search_results if use_search else [],
            'thinking_mode': thinking_mode,
            'token_usage': response.usage.output_tokens if hasattr(response, 'usage') else None
        })

    except anthropic.APIError as e:
        return jsonify({'error': f'Claude API error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Process the file
        file_info = FileProcessor.process_file(file)

        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        # Add file to conversation
        conversation_manager.add_file(session_id, file_info)

        # Add file message to conversation
        conversation_manager.add_message(
            session_id,
            'user',
            f"Uploaded file: {file_info['filename']}",
            message_type='file',
            metadata={
                'filename': file_info['filename'],
                'file_content': file_info['content'],
                'mime_type': file_info.get('mime_type', ''),
                'size': file_info.get('size', 0)
            }
        )

        return jsonify({
            'success': True,
            'filename': file_info['filename'],
            'content_preview': file_info['content'][:500] + '...' if len(file_info['content']) > 500 else file_info['content'],
            'size': file_info.get('size', 0)
        })

    except Exception as e:
        return jsonify({'error': f'File processing error: {str(e)}'}), 500

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()

        if not query:
            return jsonify({'error': 'Search query cannot be empty'}), 400

        results = WebSearcher.search_web(query)

        session_id = session.get('session_id')
        if session_id:
            conversation_manager.add_search(session_id, query, results)

        return jsonify({'results': results})

    except Exception as e:
        return jsonify({'error': f'Search error: {str(e)}'}), 500

@app.route('/api/fetch', methods=['POST'])
def fetch_url():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400

        content = WebSearcher.fetch_page_content(url)

        return jsonify({'content': content})

    except Exception as e:
        return jsonify({'error': f'Fetch error: {str(e)}'}), 500

@app.route('/api/conversation')
def get_conversation():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'messages': [], 'files': [], 'search_history': []})

    conversation = conversation_manager.get_or_create_conversation(session_id)
    return jsonify({
        'messages': conversation['messages'],
        'files': conversation['files'],
        'search_history': conversation['search_history']
    })

@app.route('/api/conversation/export')
def export_conversation():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No conversation found'}), 404

    conversation_data = conversation_manager.export_conversation(session_id)

    return jsonify(conversation_data)

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    session_id = session.get('session_id')
    if session_id and session_id in conversation_manager.conversations:
        conversation_manager.conversations[session_id] = {
            'messages': [],
            'created_at': datetime.now(),
            'last_updated': datetime.now(),
            'files': [],
            'search_history': []
        }
    return jsonify({'success': True})

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
