# Claude Chat Web App

A modern web-based chat interface for Claude Sonnet 4, built with Flask and Poetry.

## Features

- 🎨 Modern, responsive UI similar to claude.ai
- 💬 Real-time chat with Claude Sonnet 4
- 📝 Conversation history (session-based)
- 🗑️ Clear conversation functionality
- 📱 Mobile-friendly design
- ⚡ Fast and lightweight
- 📄 File upload and processing (PDF, DOCX, Excel, text files)
- 🔍 Web search integration (Brave Search API or DuckDuckGo fallback)
- 🧠 Extended thinking modes (deep analysis, research synthesis, strategic thinking, creative exploration)
- 📊 Markdown rendering for rich text responses
- 💾 Export conversation functionality

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
   BRAVE_API_KEY=your-brave-api-key-here  # Optional: for better search results
   ```

## Running the App

### Option 1: Using Poetry (Local Development)

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

### Option 2: Using Docker

1. **Build and start the Docker container**:
   ```bash
   docker-compose up -d
   ```

2. **Open your browser** and go to:
   ```
   http://localhost:5000
   ```

3. **Stop the Docker container** when you're done:
   ```bash
   docker-compose down
   ```

Note: When using Docker, you can set environment variables in a `.env` file in the project root, or pass them directly to the `docker-compose up` command.

## Project Structure

```
claude-chat-app/
├── pyproject.toml          # Poetry configuration
├── poetry.lock             # Poetry lock file
├── poetry.toml             # Poetry configuration
├── app.py                  # Flask application
├── templates/
│   └── index.html         # Main chat interface
├── static/
│   ├── css/
│   │   └── style.css      # CSS styles
│   └── js/
│       └── app.js         # JavaScript functionality
├── tests/
│   ├── test_app.py        # Tests for Flask routes
│   ├── test_file_processor.py # Tests for file processing
│   ├── test_web_searcher.py # Tests for web search
│   └── test_conversation_manager.py # Tests for conversation management
├── uploads/               # Temporary file upload directory (created at runtime)
├── .env                   # Environment variables (create this)
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── .dockerignore          # Files to exclude from Docker build
├── README.md              # This file
└── .gitignore            # Git ignore file
```

## Development

- The app uses Flask with session-based conversation storage
- Messages are stored in memory (use a database for production)
- The UI is responsive and works on mobile devices
- WebSocket support is included for real-time features
- File processing supports PDF, DOCX, Excel, and text files
- Web search uses Brave Search API (if configured) or DuckDuckGo as fallback
- Extended thinking modes provide different response styles from Claude

## Production Deployment

For production deployment:

1. Set `FLASK_ENV=production` in your `.env`
2. Use a proper database (PostgreSQL, MongoDB, etc.)
3. Use a production WSGI server (Gunicorn, uWSGI)
4. Set up proper logging and monitoring
5. Use environment variables for sensitive data

### Using Docker for Production

The included Docker configuration provides a good starting point for production deployment:

1. **Build the Docker image**:
   ```bash
   docker build -t claude-chat-app .
   ```

2. **Run the container with production settings**:
   ```bash
   docker run -d -p 5000:5000 \
     -e FLASK_ENV=production \
     -e ANTHROPIC_API_KEY=your-api-key \
     -e SECRET_KEY=your-secret-key \
     claude-chat-app
   ```

3. **For a more complete setup, use Docker Compose**:
   ```bash
   docker-compose up -d
   ```

For a full production deployment, consider:
- Adding a reverse proxy (Nginx, Traefik)
- Setting up SSL/TLS certificates
- Implementing container orchestration (Kubernetes, Docker Swarm)
- Adding monitoring and logging solutions

## API Endpoints

- `GET /` - Main chat interface
- `POST /api/chat` - Send message to Claude
- `GET /api/conversation` - Get conversation history
- `POST /api/clear` - Clear conversation
- `POST /api/upload` - Upload a file
- `POST /api/search` - Search the web
- `POST /api/fetch` - Fetch content from a URL
- `GET /api/conversation/export` - Export conversation history

## Running Tests

Run the tests using pytest:

```bash
poetry run pytest
```

Or with coverage:

```bash
poetry run pytest --cov=app tests/
```
