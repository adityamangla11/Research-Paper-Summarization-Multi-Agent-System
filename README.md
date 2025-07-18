# Research Paper Summarization System

An AI-powered system for discovering, processing, and summarizing research papers with audio generation capabilities.

## 🆕 NEW FEATURES

- **🌐 Web User Interface**: Beautiful, responsive web interface at `/app`
- **📊 Real-time Results**: See progress and results in the browser instead of terminal
- **💫 Interactive Experience**: Upload files, search papers, and view results seamlessly
- **📈 Progress Tracking**: Live progress updates with visual indicators

## Features

- **Multi-source Discovery**: Search across arXiv, PubMed, and Semantic Scholar
- **Intelligent Processing**: Automated classification and summarization using BART/T5 models
- **Audio Generation**: Convert summaries to podcast-style audio using ElevenLabs TTS
- **Real-time Updates**: WebSocket support for live progress tracking
- **RESTful API**: Easy integration with web and mobile applications
- **Interactive Web UI**: User-friendly interface for non-technical users

## Project Structure

```
├── main.py              # Main application file (FastAPI server + all agents)
├── templates/           # Web interface templates
│   └── index.html      # Main web UI (NEW!)
├── test_system.py      # System test script (NEW!)
├── agents.ipynb         # Agent implementations (Jupyter notebook)
├── apis.ipynb          # API endpoints (Jupyter notebook)
├── audio.ipynb         # Audio generation (Jupyter notebook)
├── db_schema.sql       # Database schema
├── requirements.txt    # Python dependencies
├── test_api.py        # API test script
├── .env.example       # Environment variables template
├── uploads/           # Uploaded PDF files
├── audio/            # Generated audio files
└── vahan_env/        # Python virtual environment
```

## Quick Start

### 1. Activate the Virtual Environment

```bash
source vahan_env/bin/activate
```

### 2. Install Dependencies (if needed)

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys (optional for basic functionality)
```

### 4. Run the Server

```bash
python main.py
```

### 5. Access the Application

**🌐 Web Interface (RECOMMENDED):**
- Open your browser and go to: http://localhost:8000/app
- Use the intuitive web interface to search papers or upload files
- View results with real-time progress tracking

**📚 API Documentation:**
- FastAPI docs: http://localhost:8000/docs
- Health check: http://localhost:8000

### 6. Test the System

```bash
python test_system.py
```

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

## What's Different Now? 🎉

### Before (Old System):
- ❌ Only API endpoints accessible via `/docs`
- ❌ Results only shown in terminal logs
- ❌ No visual progress tracking
- ❌ Difficult for non-technical users
- ❌ No real-time feedback

### After (New System):
- ✅ Beautiful web interface at `/app`
- ✅ Results displayed in browser with formatting
- ✅ Real-time progress bars and status updates
- ✅ Easy file upload with drag & drop
- ✅ Tabbed interface for different workflows
- ✅ Visual paper cards with summaries
- ✅ Responsive design for mobile/desktop
- ✅ Error handling with user-friendly messages

## API Endpoints

### Health Check
```
GET /
```

### Web Interface
```
GET /app
```

### Search and Process Papers
```
POST /api/v1/process/search
Content-Type: application/json

{
  "query": "machine learning",
  "topics": ["AI", "ML"],
  "max_papers": 10,
  "from_year": 2020,
  "to_year": 2024,
  "publication_type": "cs",
  "min_citations": 10,
  "must_include": ["neural network", "deep learning"],
  "must_exclude": ["blockchain", "cryptocurrency"]
}
```

**New Advanced Search Parameters:**
- `from_year` (int, optional): Filter papers from this year onwards
- `to_year` (int, optional): Filter papers up to this year  
- `publication_type` (str, optional): Publication category (e.g., 'cs', 'physics', 'math')
- `min_citations` (int, optional): Minimum citation count (Note: Not supported by ArXiv API)
- `must_include` (list, optional): Terms that must be included in the paper
- `must_exclude` (list, optional): Terms that must be excluded from the paper

## Advanced Search Filtering

The extended search endpoint now supports sophisticated filtering options that are passed to the ArXiv API:

### Date Filtering
- **from_year**: Filter papers submitted from this year onwards
- **to_year**: Filter papers submitted up to this year
- Date filtering uses ArXiv's `submittedDate` field in format `YYYYMMDDHHMMSS`

### Publication Type Filtering
- **publication_type**: Filter by ArXiv category
- Supported values: `cs` (Computer Science), `physics`, `math`, `stat`, `econ`, `bio`, `finance`
- Maps to ArXiv category prefixes (e.g., `cs` becomes `cat:cs.*`)

### Content Filtering
- **must_include**: List of terms that must appear in the paper (AND operation)
- **must_exclude**: List of terms that must NOT appear in the paper (NOT operation)
- Terms are searched across all fields using ArXiv's `all:` prefix

### Citation Filtering
- **min_citations**: Minimum citation count requirement
- ⚠️ **Note**: ArXiv API doesn't provide citation data, so this filter is logged but not applied

### Example Advanced Search
```json
{
  "query": "natural language processing",
  "max_papers": 15,
  "from_year": 2021,
  "to_year": 2024,
  "publication_type": "cs",
  "must_include": ["transformer", "attention mechanism"],
  "must_exclude": ["blockchain", "cryptocurrency"],
  "topics": ["Natural Language Processing", "Machine Learning"]
}
```

This generates an ArXiv query like:
```
all:natural language processing AND all:transformer AND all:attention mechanism 
ANDNOT all:blockchain ANDNOT all:cryptocurrency 
AND submittedDate:[20210101000000 TO 20241231235959] 
AND cat:cs.*
```

### Upload and Process PDFs
```
POST /api/v1/process/upload
Content-Type: multipart/form-data

files: [file1.pdf, file2.pdf, ...]
topics: ["AI", "ML"]
```

### Get Workflow Status
```
GET /api/v1/status/{workflow_id}
```

### WebSocket Status Updates
```
WS /ws/status/{workflow_id}
```

### Real-time Status Updates
```
WebSocket: /ws/status/{workflow_id}
```

## Running in Jupyter Notebooks

You can also run the individual components in Jupyter notebooks:

### 1. Start Jupyter
```bash
jupyter notebook
```

### 2. Open and run notebooks:
- `agents.ipynb` - Core agent implementations
- `apis.ipynb` - API server with FastAPI
- `audio.ipynb` - Audio generation functionality

## API Documentation

Once the server is running, visit:
- Interactive API docs: `http://127.0.0.1:8000/docs`
- ReDoc documentation: `http://127.0.0.1:8000/redoc`

## Example Usage

### Using curl

```bash
# Basic search for papers
curl -X POST "http://127.0.0.1:8000/api/v1/process/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "machine learning",
       "topics": ["AI", "ML"],
       "max_papers": 5
     }'

# Advanced search with filtering
curl -X POST "http://127.0.0.1:8000/api/v1/process/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "deep learning healthcare",
       "max_papers": 10,
       "from_year": 2022,
       "to_year": 2024,
       "publication_type": "cs",
       "must_include": ["neural network", "medical imaging"],
       "must_exclude": ["blockchain", "cryptocurrency"],
       "topics": ["Machine Learning", "Healthcare", "AI"]
     }'

# Check status
curl "http://127.0.0.1:8000/api/v1/status/{workflow_id}"
```

### Using Python

```python
import httpx
import asyncio

async def search_papers():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/process/search",
            params={
                "query": "artificial intelligence",
                "topics": ["AI", "Machine Learning"],
                "max_papers": 10
            }
        )
        return response.json()

result = asyncio.run(search_papers())
print(result)
```

## Database Setup (Optional)

If you want to use PostgreSQL for persistent storage:

### 1. Install PostgreSQL
```bash
brew install postgresql  # macOS
```

### 2. Create Database
```bash
createdb research_papers
```

### 3. Run Schema
```bash
psql research_papers < db_schema.sql
```

## Environment Variables

Create a `.env` file with:

```env
# Required for audio generation
ELEVENLABS_API_KEY=your_api_key_here

# Optional for enhanced summarization
OPENAI_API_KEY=your_openai_key_here

# Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:pass@localhost:5432/research_papers

# App settings
DEBUG=True
LOG_LEVEL=INFO
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find and kill process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

2. **Import errors**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt --force-reinstall
   ```

3. **Audio generation fails**
   - Ensure ElevenLabs API key is set in `.env`
   - Check your ElevenLabs account quota

4. **Notebook kernel issues**
   ```bash
   # Restart Jupyter kernel
   jupyter kernelspec list
   jupyter kernelspec remove python3
   python -m ipykernel install --user --name=vahan_env
   ```

## Development

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement the `process` method
3. Add to the orchestrator's agent dictionary

### Extending APIs

1. Add new endpoints to `main.py`
2. Update the orchestrator pipeline as needed
3. Add corresponding tests to `test_api.py`

## Performance Notes

- The system uses async/await for concurrent processing
- Background tasks prevent API blocking
- WebSocket connections provide real-time updates
- Mock implementations are used for development - replace with actual integrations

## Next Steps

1. Implement actual API integrations (arXiv, PubMed, etc.)
2. Add proper PDF extraction using PyPDF2 or similar
3. Integrate with real LLM APIs for summarization
4. Add user authentication and rate limiting
5. Implement proper database integration
6. Add comprehensive error handling and logging

## Support

For issues or questions, please check the troubleshooting section or create an issue in the project repository.
