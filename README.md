# Lecture-to-Study-Pack Generator

A web application that transforms lecture content into structured study materials using AI. Upload lecture recordings or transcripts, and generate summaries, detailed notes, practice questions, and multiple-choice questions.

---

## 1. Project Overview

The Lecture-to-Study-Pack Generator is a web application that helps students convert lecture content into structured study materials. Users can upload lecture recordings (PDF/DOCX) or manually enter lecture transcripts, then use AI to generate study packs containing summaries, detailed notes, practice questions, and multiple-choice questions (MCQs).

The application uses a local LLM (Qwen3-4B via llama.cpp) by default, with support for hosted OpenAI-compatible providers and Anthropic as alternatives.

---

## 2. Features

### Authentication & Authorization
- **User registration** with username, email, and password
- **Secure login/logout** with Flask sessions
- **Password hashing** using Werkzeug
- **User-owned lectures** - each lecture belongs to its creator
- **Authorization** - users can only access their own lectures and study packs

### Lecture Management
- **Manual lecture creation** - type or paste lecture transcripts
- **Document upload** - PDF and DOCX files with automatic text extraction
- **Lecture listing** - view all your lectures
- **Lecture editing and deletion**

### Study Pack Generation
Four study material types:
- **Summary** - Concise overview with key concepts and main ideas
- **Notes** - Detailed structured notes with headings, bullet points, and tables
- **Questions** - Practice questions with answers (recall, comprehension, application)
- **MCQs** - Multiple-choice questions with 4 options, correct answer, and explanations

### AI Pipeline
- **Task Router** - Routes natural language requests to the appropriate task type (summary, notes, questions, mcqs)
- **Model Selection** - Chooses the best available provider (local llama.cpp, hosted OpenAI-compatible, or Anthropic)
- **RAG (Retrieval-Augmented Generation)** - Keyword-based retrieval from lecture chunks
- **Local LLM** - Qwen3-4B via llama.cpp (default)
- **Alternative providers** - Hosted OpenAI-compatible APIs, Anthropic

### Study Pack Storage
- Generated study packs are saved to SQLite database
- Each study pack stores summary, notes, questions, and MCQs per lecture
- View generated content in the web interface

### Frontend Features
- **Light/Dark theme** toggle with localStorage persistence
- Responsive design (desktop, tablet, mobile)
- Clean, professional UI with Markdown rendering
- Real-time loading states during generation

---

## 3. Technology Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| HTML5 | Structure |
| CSS3 | Styling (custom, no frameworks) |
| Vanilla JavaScript | Interactivity, API calls, theme management |
| marked.js | Markdown rendering in browser |

### Backend
| Technology | Purpose |
|------------|---------|
| Python 3.x | Runtime |
| Flask 3.0 | Web framework |
| Werkzeug | Password hashing, security |

### Database
| Technology | Purpose |
|------------|---------|
| SQLite | Local database (file-based) |

### AI/ML
| Technology | Purpose |
|------------|---------|
| llama.cpp | Local LLM inference server |
| Qwen3-4B GGUF (Q4_K_M) | Default local LLM model |
| RAG | Retrieval-Augmented Generation (keyword-based) |
| Task Router | Routes user requests to task types |
| Model Selection | Chooses best available LLM provider |

### Document Processing
| Library | Purpose |
|---------|---------|
| pypdf (4.0.0) | PDF text extraction |
| python-docx (1.1.0) | DOCX text extraction |

### Testing
- Custom test scripts in `tests/` (integration-style API tests)
- No external test framework required

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  (HTML / CSS / Vanilla JavaScript + marked.js)                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FLASK API                                │
│  (Authentication, Lecture CRUD, Upload, Generation, Search)    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Task Router  │ │ Model Select │ │    RAG       │
    │ (Task Router)│ │ (Model Sel.) │ │ (Retrieval)  │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
                   ┌──────────────────┐
                   │  LLM Provider    │
                   │  (llama.cpp /    │
                   │   Hosted /      │
                   │   Anthropic)     │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │   SQLite DB      │
                   │ (study_packs,    │
                   │  lectures, users)│
                   └──────────────────┘
```

**Flow:**
1. User uploads/creates lecture → stored in SQLite with user ownership
2. Lecture content chunked and stored for RAG
3. User requests study pack (summary/notes/questions/mcqs)
4. Task Router identifies task type
5. Model Selection picks best available provider
3. RAG retrieves relevant lecture chunks
4. LLM generates study material
4. Result saved to `study_packs` table and displayed

---

## 5. RAG Pipeline

The current RAG implementation uses **keyword-based retrieval** (not semantic/vector embeddings).

### Implementation Details:
- **Chunking**: Lecture text split into overlapping chunks (~500 chars, 50 char overlap)
- **Storage**: Chunks stored in `lecture_chunks` table linked to lecture and user
- **Query Building**: Task-specific search terms (e.g., "definitions concepts facts" for MCQs)
- **Search**: Keyword overlap scoring (distinct word matches × 20 + frequency bonus)
- **Fallback**: If no keyword matches, returns first N chunks
- **Context Assembly**: Top chunks combined (max 3000 chars) for LLM context

### What is NOT implemented:
- ❌ Vector embeddings / semantic search
- ❌ Vector databases (FAISS, Chroma, Pinecone, etc.)
- ❌ Embedding models (sentence-transformers, etc.)
- ❌ Semantic similarity search

The current approach is **keyword-based** (TF-like scoring on word overlap).

---

## 6. Project Structure

```
Lecture-to-Study-Pack/
├── .env.example          # Environment variable template
├── .gitignore
├── app.py                # Flask application entry point
├── database.py           # SQLite operations
├── requirements.txt      # Python dependencies
├── database.db           # SQLite database (ignored by git)
├── services/
│   ├── __init__.py
│   ├── document_processor.py   # PDF/DOCX text extraction
│   ├── llm_service.py          # LLM provider integration
│   ├── model_selection.py      # Provider/model selection
│   ├── rag_service.py          # RAG chunking & retrieval
│   └── task_router.py          # Task type routing
├── static/
│   ├── script.js         # Frontend JavaScript
│   └── style.css         # Frontend styles
├── templates/
│   └── index.html        # Single-page application
├── tests/
│   ├── test_all_tasks.py     # Full integration tests
│   ├── test_html.py          # Basic HTML endpoint test
│   └── test_quick_verify.py  # Quick API verification
├── uploads/                # User uploads (gitignored)
└── database.db             # SQLite database (gitignored)
```

---

## 7. Prerequisites

Before running the project, ensure you have:

| Requirement | Details |
|-------------|---------|
| **Python** | 3.8+ (tested on 3.10+) |
| **Flask** | Installed via `requirements.txt` |
| **SQLite** | Built into Python standard library |
| **llama.cpp** | Local inference server |
| **Qwen3-4B GGUF** | Q4_K_M quantization recommended |

No external APIs required for default local setup.

---

## 8. Local Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd Lecture-to-Study-Pack
```

### 2. Create and activate virtual environment
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/macOS bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your settings (at minimum, change SECRET_KEY)
```

### 5. Start llama.cpp server (required for default local LLM)
```bash
# Download Qwen3-4B GGUF (Q4_K_M) model first
# Then start the server:
llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_K_M --host 0.0.0.0 --port 8080
```
> **Important**: Keep this terminal running. The llama.cpp server must stay running while you use the application.

### 6. Start Flask application
```bash
python app.py
```

### 7. Access the application
Open your browser to: `http://127.0.0.1:5000/`

### 8. Deactivate virtual environment (when done)
```bash
deactivate
```

---

## 9. Environment Variables

Configure using `.env` (copy from `.env.example`):

| Category | Variables |
|----------|-----------|
| **Flask** | `SECRET_KEY` - Flask session secret (change in production) |
| **Local LLM** | `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_API_KEY`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_TIMEOUT`, `LOCAL_LLM_MAX_TOKENS` |
| **Hosted LLM** | `HOSTED_LLM_BASE_URL`, `HOSTED_LLM_API_KEY`, `HOSTED_LLM_MODEL`, `HOSTED_LLM_TIMEOUT`, `HOSTED_LLM_MAX_TOKENS` |
| **Anthropic** | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_TIMEOUT`, `ANTHROPIC_MAX_TOKENS` |
| **Model Selection** | `DEFAULT_MODEL_PROVIDER` (local, openai_compatible, anthropic) |

See `.env.example` for all variables with descriptions and default values.

---

## 10. How to Use

1. **Register** - Create an account with username, email, and password
2. **Login** - Sign in to access your dashboard
3. **Create Lecture** - Either:
   - Upload a PDF/DOCX file (text extracted automatically)
   - Or manually enter lecture title and content
4. **Generate Study Pack**:
   - Select a lecture from dropdown
   - Choose study type: Summary, Notes, Questions, or MCQs
   - Click "Generate Study Pack"
4. **Review** - Generated material renders as formatted Markdown
5. **Study** - Content is saved automatically to your study packs

---

## 11. Testing

The project includes integration tests in `tests/`:

| Test File | Purpose |
|-----------|---------|
| `test_all_tasks.py` | Full integration test for all 4 task types |
| `test_quick_verify.py` | Quick API verification |
| `test_html.py` | Basic HTML endpoint test |

### Running Tests
```bash
# Ensure Flask app is running on http://127.0.0.1:5000
python tests/test_all_tasks.py
python tests/test_quick_verify.py
python tests/test_html.py
```

> **Note**: Tests require a running Flask server and llama.cpp server. They are integration-style tests, not unit tests. Run manually; no test framework configured.

---

## 12. Security Notes

- **Secrets in environment** - All secrets (API keys, secrets) stored in `.env` (gitignored)
- **No secrets in code** - `.env` is gitignored; only `.env.example` is tracked
- **Password hashing** - Passwords hashed with Werkzeug (`generate_password_hash` / `check_password_hash`)
- **Authorization** - Users can only access their own lectures and study packs
- **Session management** - Flask sessions with secure cookies
- **Local LLM** - Default llama.cpp setup intended for local development/testing only

---

## 12. Deployment / Production Notes

> ⚠️ **This project is configured for local development.**

For production deployment, you would need to:

1. **Use a hosted LLM provider** (OpenAI, Anthropic, Together.ai, Fireworks, etc.) instead of local llama.cpp
2. **Replace SQLite** with a production database (PostgreSQL, MySQL)
3. **Configure proper secret management** (not `.env` files)
4. **Use a production WSGI server** (Gunicorn, uWSGI) behind a reverse proxy (Nginx)
5. **Enable HTTPS** with valid TLS certificates
6. **Set up proper logging and monitoring**
7. **Configure CORS and security headers**

The current local llama.cpp/Qwen setup is intended for **local development and testing only**.

---

## 13. Future Scope

Planned improvements (not yet implemented):

- [ ] **Semantic RAG** - Semantic search capabilities (not yet implemented; current RAG is keyword-based)
- [ ] **Production database** - PostgreSQL/MySQL support
- [ ] **Docker deployment** - Containerized deployment with docker-compose
- [ ] **Hosted deployment** - Render, Fly.io, Railway, etc.
- [ ] **More study formats** - Flashcards, mind maps, concept maps
- [ ] **Evaluation framework** - Automated quality evaluation of generated content
- [ ] **Batch processing** - Multiple lecture processing
- [ ] **Export formats** - PDF, Anki, Quizlet export
- [ ] **Collaborative features** - Shared study packs, comments

---

## 14. License

No license has been specified for this project yet.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `python -m venv venv` | Create virtual environment |
| `.\venv\Scripts\Activate.ps1` | Activate venv (Windows PowerShell) |
| `pip install -r requirements.txt` | Install dependencies |
| `cp .env.example .env` | Create local config |
| `llama-server -hf Qwen/Qwen3-4B-GGUF:Q4_K_M --host 0.0.0.0 --port 8080` | Start llama.cpp |
| `python app.py` | Start Flask app |

---

*Built as a college project to demonstrate RAG, LLM integration, and full-stack web development.*