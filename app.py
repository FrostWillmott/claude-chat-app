import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Anthropic client
try:
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
except Exception as e:
    print(f"Error initializing Anthropic client: {e}")
    client = None

# Store conversations in memory (in production, use a database)
conversations = {}

class ConversationManager:
    def __init__(self):
        self.conversations = {}

    def get_or_create_conversation(self, session_id):
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'messages': [],
                'created_at': datetime.now(),
                'last_updated': datetime.now()
            }
        return self.conversations[session_id]

    def add_message(self, session_id, role, content):
        conversation = self.get_or_create_conversation(session_id)
        message = {
            'id': str(uuid.uuid4()),
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        conversation['messages'].append(message)
        conversation['last_updated'] = datetime.now()
        return message

    def get_messages_for_api(self, session_id):
        conversation = self.get_or_create_conversation(session_id)
        return [{'role': msg['role'], 'content': msg['content']}
                for msg in conversation['messages'] if msg['role'] in ['user', 'assistant']]

conversation_manager = ConversationManager()

@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if not client:
        return jsonify({'error': 'Claude API not configured'}), 500

    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        # Add user message to conversation
        conversation_manager.add_message(session_id, 'user', user_message)

        # Get conversation history for API
        messages = conversation_manager.get_messages_for_api(session_id)

        # Get response from Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=messages
        )

        claude_response = response.content[0].text
        used_model    = response.model

        # Add Claude's response to conversation
        claude_message = conversation_manager.add_message(session_id, 'assistant', claude_response)

        return jsonify({
            'response': claude_response,
            'model': used_model,
            'message_id': claude_message['id'],
            'timestamp': claude_message['timestamp']
        })

    except anthropic.APIError as e:
        return jsonify({'error': f'Claude API error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/conversation')
def get_conversation():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'messages': []})

    conversation = conversation_manager.get_or_create_conversation(session_id)
    return jsonify({'messages': conversation['messages']})

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    session_id = session.get('session_id')
    if session_id and session_id in conversation_manager.conversations:
        conversation_manager.conversations[session_id]['messages'] = []
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