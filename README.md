# 🔍 GitSleuth

> **AI-Powered GitHub Repository Analyzer with Real-Time Chat Interface**

An advanced full-stack web application that indexes public GitHub repositories and enables intelligent code analysis through Retrieval-Augmented Generation (RAG) techniques. With cutting-edge features like semantic chunking, conversational memory, confidence scoring, and a ChatGPT-style real-time chat interface, GitSleuth provides developers with powerful insights into any codebase.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-purple.svg)](https://openai.com)

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🚀 **Core Capabilities**
- 🔍 **Repository Indexing** - Clone and process GitHub repositories
- 🤖 **AI-Powered Q&A** - Ask questions using GPT-4
- 📊 **Vector Search** - ChromaDB for semantic code search
- 🎨 **Modern UI** - Clean, responsive React frontend

</td>
<td width="50%">

### 🧠 **Advanced Features**
- 💬 **Real-Time Chat Interface** - ChatGPT-style conversation experience
- 🧠 **Semantic Chunking** - Tree-sitter language parsing
- 🎯 **Confidence Scoring** - AI quality assessment
- ⚡ **Instant Messaging** - Immediate message display with smooth transitions

</td>
</tr>
</table>

## 🛠️ Tech Stack

<div align="center">

| **Backend** | **Frontend** | **AI/ML** |
|-------------|--------------|-----------|
| 🐍 **Python 3.8+** | ⚛️ **React 18** | 🤖 **OpenAI GPT-4o-mini** |
| 🚀 **FastAPI** | 🎨 **Tailwind CSS** | 📊 **ChromaDB** |
| 🔗 **LangChain** | 📡 **Axios** | 🧠 **Tree-sitter** |
| 📁 **GitPython** | 🎯 **Lucide Icons** | 💬 **Real-Time Chat** |

</div>

## Project Structure

```
github_ragproject/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration settings and environment
│   ├── requirements.txt       # Python dependencies
│   ├── env.example            # Environment variables template
│   ├── models/
│   │   ├── __init__.py        # Package initialization
│   │   └── schemas.py         # Pydantic models and data structures
│   ├── services/
│   │   ├── __init__.py        # Package initialization
│   │   ├── repo_processor.py  # Repository cloning and file processing
│   │   ├── rag_service.py     # RAG pipeline implementation
│   │   ├── conversation_manager.py # Conversation history management
│   │   └── semantic_chunker.py # Tree-sitter based code chunking
│   ├── utils/
│   │   ├── cache.py           # Caching utilities
│   │   ├── exceptions.py      # Custom exception classes
│   │   ├── health.py          # Health check and monitoring
│   │   ├── logger.py          # Logging configuration
│   │   ├── rate_limiter.py    # Rate limiting implementation
│   │   └── validators.py      # Input validation utilities
│   ├── chroma_db/             # ChromaDB vector database storage
│   ├── temp_repos/            # Temporary repository clones
│   └── logs/                  # Application logs
├── frontend/
│   ├── public/
│   │   └── index.html         # HTML template
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── index.js          # React entry point
│   │   └── index.css          # Global styles and animations
│   ├── package.json          # Node.js dependencies
│   ├── package-lock.json     # Dependency lock file
│   ├── tailwind.config.js    # Tailwind CSS configuration
│   └── postcss.config.js     # PostCSS configuration
├── install_dependencies.bat  # One-click dependency installation
├── setup.bat                 # Project setup script
├── start_backend.bat         # Backend startup script
├── start_frontend.bat        # Frontend startup script
└── README.md                 # Project documentation
```

## 🚀 Quick Start

<div align="center">

### ⚡ **One-Click Setup** (Recommended)

```bash
git clone https://github.com/SyedQasimGardezi/GitSleuth.git
cd GitSleuth
install_dependencies.bat
```

**Then start the application:**
```bash
start_backend.bat    # Terminal 1
start_frontend.bat   # Terminal 2
```

🌐 **Open** [http://localhost:3000](http://localhost:3000)

</div>

---

### 🔧 **Manual Setup**

<details>
<summary><b>Click to expand manual setup instructions</b></summary>

#### Prerequisites
- Python 3.8+
- Node.js 16+
- Git

#### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

</details>

## 📖 How to Use

<div align="center">

### 🎯 **3 Simple Steps**

| Step | Action | Description |
|------|--------|-------------|
| **1️⃣** | **Index** | Enter GitHub repo URL and click "Index" |
| **2️⃣** | **Wait** | Watch real-time progress until ready |
| **3️⃣** | **Ask** | Start asking questions about the codebase |

</div>

---

### 💬 **Example Questions**

<table>
<tr>
<td width="50%">

#### 🔍 **Basic Analysis**
- "Where is authentication logic handled?"
- "What is the purpose of the database.js file?"
- "How does the user model look like?"
- "What are the main components in this React app?"

</td>
<td width="50%">

#### 🧠 **Follow-up Questions**
- "Can you show me the implementation details?"
- "What other files use this function?"
- "How is error handling done in this module?"
- "What are the dependencies of this class?"

</td>
</tr>
</table>

### ✨ **Advanced Features**

<details>
<summary><b>💬 Real-Time Chat Interface</b></summary>

- **ChatGPT-Style UI**: Fixed input at bottom with scrollable messages
- **Instant Messaging**: User messages appear immediately
- **Thinking Indicator**: "GitSleuth is thinking..." with animated dots
- **Smooth Transitions**: Thinking message smoothly becomes response
- **Auto-Scroll**: Automatically scrolls to new messages
- **Keyboard Shortcuts**: Enter to send, Shift+Enter for new line
- **Welcome Screen**: Interactive suggestions for new users

</details>

<details>
<summary><b>💬 Conversational Memory</b></summary>

- **Context Awareness**: Previous questions inform new answers
- **Natural Flow**: Ask follow-up questions naturally
- **History View**: See all previous conversations
- **Clear Option**: Reset conversation when needed

</details>

<details>
<summary><b>🎯 Confidence Scoring</b></summary>

- **High Confidence** 🟢 - Reliable, well-supported answers
- **Medium Confidence** 🟡 - Somewhat reliable answers  
- **Low Confidence** 🔴 - Uncertain or incomplete answers

</details>

<details>
<summary><b>🧠 Semantic Chunking</b></summary>

- **Language-Aware**: Preserves complete functions and classes
- **Better Context**: More accurate source references
- **Line Numbers**: Precise code location information

</details>

<details>
<summary><b>⚡ Performance Optimizations</b></summary>

- **Faster Model**: GPT-4o-mini for quicker responses
- **Optimized Prompts**: Concise prompts for faster processing
- **Reduced Context**: Smaller context size for better performance
- **Smart Caching**: Embedding cache for repeated queries
- **Batch Processing**: Efficient embedding generation

</details>

## API Endpoints

### POST /index
Start indexing a GitHub repository.

**Request:**
```json
{
  "repo_url": "https://github.com/user/repo"
}
```

**Response:**
```json
{
  "message": "Repository indexing started.",
  "session_id": "unique_id"
}
```

### GET /status/{session_id}
Get indexing status for a session.

**Response:**
```json
{
  "status": "indexing" | "ready" | "error",
  "message": "Details...",
  "progress": 50
}
```

### POST /query
Query the indexed repository with conversation support.

**Request:**
```json
{
  "session_id": "unique_id",
  "question": "How does the user model look like?",
  "conversation_history": [
    {
      "role": "user",
      "content": "What authentication methods are used?",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "role": "assistant", 
      "content": "The system uses JWT tokens...",
      "confidence": "high"
    }
  ]
}
```

**Response:**
```json
{
  "answer": "The user model is defined in `models/user.py` and contains fields like...",
  "sources": [
    {
      "file": "models/user.py",
      "snippet": "class User...",
      "line_number": 15
    }
  ],
  "confidence": "high",
  "conversation_id": "conv_12345"
}
```

### GET /sessions
Get all available sessions from both memory and ChromaDB.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "unique_id",
      "status": "ready",
      "repo_url": "https://github.com/user/repo",
      "created_at": 1642234567
    }
  ]
}
```

### Conversation Management

#### GET /conversation/{conversation_id}
Get full conversation details.

#### GET /conversation/{conversation_id}/history
Get conversation history with optional limit.

#### DELETE /conversation/{conversation_id}
Clear conversation history.

#### GET /conversation/{conversation_id}/stats
Get conversation statistics.

## Advanced Features

### Semantic Chunking
The system uses **tree-sitter** for language-aware code parsing:

- **Supported Languages**: Python, JavaScript, TypeScript, Java, C++
- **Semantic Units**: Functions, classes, methods, imports, interfaces
- **Fallback**: RecursiveCharacterTextSplitter for unsupported languages
- **Benefits**: Preserves code structure and context

### Conversational Memory
- **Session-based**: Each repository session maintains conversation history
- **Context Awareness**: Previous questions and answers inform new responses
- **Memory Management**: Configurable conversation length limits
- **Clear Function**: Users can clear conversation history

### Confidence Scoring
- **AI Assessment**: GPT-4 evaluates answer quality based on context relevance
- **Three Levels**: High, Medium, Low confidence scores
- **Visual Indicators**: Color-coded confidence badges in UI
- **Transparency**: Users can gauge answer reliability

## File Processing

The system intelligently filters files during indexing:

### Included File Types
- Source code: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.cpp`, `.c`, `.h`, `.cs`, `.php`, `.rb`, `.go`, `.rs`, `.swift`, `.kt`, `.scala`
- Web files: `.html`, `.css`, `.scss`, `.sass`, `.less`, `.vue`, `.svelte`
- Configuration: `.json`, `.yaml`, `.yml`, `.xml`
- Documentation: `.md`, `.txt`

### Excluded Directories
- `.git`, `node_modules`, `__pycache__`, `.pytest_cache`
- `venv`, `env`, `.venv`, `.env`
- `dist`, `build`, `target`, `.next`, `.nuxt`
- `coverage`, `.nyc_output`, `vendor`, `bower_components`
- `.gradle`, `.idea`, `.vscode`

### File Size Limits
- Maximum file size: 1MB
- Binary files are automatically excluded

## Assumptions and Limitations

1. **Repository Access**: Only public GitHub repositories are supported
2. **File Size**: Large files (>1MB) are skipped to maintain performance
3. **Binary Files**: Image, video, and other binary files are excluded
4. **Rate Limits**: OpenAI API rate limits may affect large repositories
5. **Memory Usage**: Large repositories may require significant memory for processing

## Development Timeline

### Phase 1: Core Implementation (4 hours)
- **Backend Development**: 2 hours
- **Frontend Development**: 1.5 hours  
- **Integration & Testing**: 30 minutes

### Phase 2: Advanced Features (2 hours)
- **Semantic Chunking**: 45 minutes
- **Conversational Memory**: 45 minutes
- **Confidence Scoring**: 30 minutes

### Phase 3: UI/UX Enhancements (2 hours)
- **ChatGPT-Style Interface**: 1 hour
- **Real-Time Chat Features**: 45 minutes
- **Performance Optimizations**: 15 minutes

### Total Development Time: ~8 hours

## Future Enhancements

- **Repository Caching**: Cache processed repositories for faster access
- **Advanced Filtering**: More sophisticated file filtering based on repository structure
- **Multi-language Support**: Extend tree-sitter support to more programming languages
- **Export Conversations**: Save conversation history to files
- **Advanced Analytics**: Detailed usage statistics and insights
- **Voice Interface**: Speech-to-text and text-to-speech capabilities
- **Code Highlighting**: Syntax highlighting in chat responses
- **File Previews**: Inline code file previews in chat
- **Dark Mode**: Theme switching for better user experience
- **Mobile App**: Native mobile application for on-the-go code analysis

## Troubleshooting

### Common Issues

1. **"Repository not found" error:**
   - Ensure the repository URL is correct and public
   - Check your internet connection

2. **"OpenAI API error":**
   - Verify the API key is correctly set in `config.py`
   - Check your OpenAI API usage limits

3. **"ChromaDB error":**
   - Ensure write permissions in the project directory
   - Try deleting the `chroma_db` folder and reindexing

4. **Frontend not connecting to backend:**
   - Ensure the backend is running on port 8000
   - Check CORS settings in `main.py`

5. **Tree-sitter parsing errors:**
   - Ensure all tree-sitter language packages are installed
   - Check that the language parsers are properly compiled

6. **Conversation memory issues:**
   - Conversations are stored in memory and will be lost on server restart
   - For production, consider using Redis or a database for persistence

### Performance Tips

- **Large Repositories**: Consider excluding large directories in the ignore list
- **Memory Usage**: Monitor memory usage when processing very large repositories
- **API Rate Limits**: The system processes embeddings in batches to respect rate limits

## 🚀 Why GitSleuth?

<div align="center">

### **vs. Basic RAG Systems**

| Feature | Basic RAG | **GitSleuth** |
|---------|-----------|---------------|
| **Code Understanding** | ❌ Breaks functions | ✅ **Preserves complete code units** |
| **Conversation** | ❌ No memory | ✅ **Context-aware follow-ups** |
| **Answer Quality** | ❌ No confidence | ✅ **AI confidence scoring** |
| **Source References** | ❌ Basic file refs | ✅ **Line numbers + context** |
| **User Interface** | ❌ Basic forms | ✅ **ChatGPT-style real-time chat** |
| **Response Speed** | ❌ Slow processing | ✅ **Optimized for speed** |
| **User Experience** | ❌ Static interface | ✅ **Smooth animations & transitions** |

</div>

---

### 🎯 **Key Advantages**

<details>
<summary><b>🧠 Semantic Understanding</b></summary>

**Before**: Simple text splitting that could break code functions  
**After**: Tree-sitter parsing preserves complete functions, classes, and methods  
**Result**: More accurate context and better answer quality

</details>

<details>
<summary><b>💬 Conversational Intelligence</b></summary>

**Before**: Each question treated independently  
**After**: Maintains conversation history for context-aware follow-ups  
**Result**: Natural, flowing conversations about code

</details>

<details>
<summary><b>🎯 Confidence Transparency</b></summary>

**Before**: No indication of answer reliability  
**After**: AI-powered confidence scoring with visual indicators  
**Result**: Users can gauge answer trustworthiness

</details>

<details>
<summary><b>💬 Real-Time Chat Experience</b></summary>

**Before**: Static form-based interface with slow responses  
**After**: ChatGPT-style real-time chat with instant messaging  
**Result**: Natural, engaging conversation experience with immediate feedback

</details>

## 🎮 Try It Out

<div align="center">

### **Popular Repositories to Test**

| Repository | Language | Description |
|------------|----------|-------------|
| [**React**](https://github.com/facebook/react) | JavaScript | Popular UI library |
| [**Vue.js**](https://github.com/vuejs/vue) | JavaScript | Progressive framework |
| [**Express**](https://github.com/expressjs/express) | JavaScript | Web framework |
| [**Django**](https://github.com/django/django) | Python | Web framework |

</div>

---

### 🎯 **Sample Questions to Try**

- *"How does the component lifecycle work in this React app?"*
- *"What authentication methods are implemented?"*
- *"Show me the main routing configuration"*
- *"How is state management handled?"*

### 💬 **Chat Interface Features**

- **Welcome Screen**: Interactive suggestion cards for new users
- **Instant Messaging**: Messages appear immediately when sent
- **Thinking Indicator**: Animated "GitSleuth is thinking..." with bouncing dots
- **Smooth Transitions**: Thinking message smoothly becomes response
- **Auto-Scroll**: Automatically scrolls to new messages
- **Keyboard Shortcuts**: Enter to send, Shift+Enter for new line
- **Character Counter**: Real-time character count in input
- **Error Handling**: Smooth error message transitions

<div align="center">

**🚀 Ready to explore? Start with any repository above!**

</div>

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

---

## 📄 License

This project is for demonstration purposes as part of a take-home assignment.

---

<div align="center">

### ⭐ **Star this repository if you found it helpful!**

**Made with ❤️ by [Syed Qasim Gardezi](https://github.com/SyedQasimGardezi)**

</div>
