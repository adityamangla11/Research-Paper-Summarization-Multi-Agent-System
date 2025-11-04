# Research Paper Summarization System

An AI-powered system for discovering, processing, and summarizing research papers with audio generation capabilities.

## Features

- **🌐 Web User Interface**: Simple and responsive web interface
- **Multi-source Discovery**: Search across arXiv, PubMed, and Semantic Scholar
- **Intelligent Processing**: Automated classification and summarization using BART/T5 models
- **Audio Generation**: Convert summaries to podcast-style audio using ElevenLabs TTS
- **Real-time Updates**: WebSocket support for live progress tracking
- **RESTful API**: Easy integration with web and mobile applications
- **Interactive Web UI**: User-friendly interface for non-technical users


## Quick Start

### 1. Install Dependencies 

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python main.py
```

### 3. Access the Application

**🌐 Web Interface (RECOMMENDED):**
- Open your browser and go to: http://localhost:8000/app
- Use the intuitive web interface to search papers or upload files
- View results with real-time progress tracking

**📚 API Documentation:**
- FastAPI docs: http://localhost:8000/docs
- Health check: http://localhost:8000

## 🎯 How to Use

### Option 1: Web Interface (Easiest)

1. **Start the server**: `python main.py`
2. **Open browser**: Go to http://localhost:8000/app
3. **Search Papers**: 
   - Enter search terms like "machine learning" or "natural language processing"
   - Select number of papers and optional topics
   - Click "Search & Analyze Papers"
4. **Upload Files**:
   - Switch to "Upload Files" tab
   - Select PDF or text files
   - Add optional topics
   - Click "Upload & Process Files"
5. **View Results**:
   - Switch to "Results" tab
   - Watch real-time progress
   - View detailed analysis when complete

### Option 2: API Endpoints

#### Search and Process Papers

```bash
curl -X POST "http://localhost:8000/api/v1/process/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "machine learning",
       "topics": ["AI", "Machine Learning"],
       "max_papers": 5
     }'
```

#### Upload and Process Files

```bash
curl -X POST "http://localhost:8000/api/v1/process/upload" \
     -F "files=@your_paper.pdf" \
     -F "topics=AI" \
     -F "topics=Machine Learning"
```

#### Check Status

```bash
curl "http://localhost:8000/api/v1/status/{workflow_id}"
```

## Support

For issues or questions, please check the troubleshooting section or create an issue in the project repository.
