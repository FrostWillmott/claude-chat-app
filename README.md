# Claude Chat Web App

A modern web-based chat interface for Claude Sonnet 4, built with Flask and Poetry.

## Features

- 🎨 Modern, responsive UI similar to claude.ai
- 💬 Real-time chat with Claude Sonnet 4
- 📝 Conversation history (session-based)
- 🗑️ Clear conversation functionality
- 📱 Mobile-friendly design
- ⚡ Fast and lightweight

## Setup

1. **Clone and navigate to the project directory**

2. **Install Poetry** (if you haven't already):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Get your Anthropic API key**:
   - Visit https://console.anthropic.com/
   - Create an account and generate an API key

5. **Create a `.env` file** in the project root:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   SECRET_KEY=your-secret-key-for-flask-sessions
   FLASK_ENV=development
   PORT=5000
   ```

6. **Create the templates directory**:
   ```bash
   mkdir templates
   ```
   Then save the HTML content as `templates/index.html`

## Running the App

1. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

## Project Structure

```
claude-chat-app/
├── pyproject.toml          # Poetry configuration
├── app.py                  # Flask application
├── templates/
│   └── index.html         # Main chat interface
├── .env                   # Environment variables (create this)
├── README.md              # This file
└── .gitignore            # Git ignore file
```

## Development

- The app uses Flask with session-based conversation storage
- Messages are stored in memory (use a database for production)
- The UI is responsive and works on mobile devices
- Real-time features can be added with WebSocket support

## Production Deployment

For production deployment:

1. Set `FLASK_ENV=production` in your `.env`
2. Use a proper database (PostgreSQL, MongoDB, etc.)
3. Use a production WSGI server (Gunicorn, uWSGI)
4. Set up proper logging and monitoring
5. Use environment variables for sensitive data

## API Endpoints

- `GET /` - Main chat interface
- `POST /api/chat` - Send message to Claude
- `GET /api/conversation` - Get conversation history
- `POST /api/clear` - Clear conversation