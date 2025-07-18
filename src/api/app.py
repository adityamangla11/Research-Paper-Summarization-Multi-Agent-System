"""
FastAPI application setup for the Research Paper Summarization System.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket
from contextlib import asynccontextmanager
import json
import asyncio

from .routes import router
from ..models.database import init_database
from ..config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting Research Paper Summarization API...")
    init_database()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down API...")


# Create FastAPI application
app = FastAPI(
    title="Research Paper Summarization API",
    description="An intelligent system for discovering, analyzing, and summarizing research papers",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.templates_dir)), name="static")

# Mount audio files directory for serving audio files
app.mount("/audio", StaticFiles(directory=str(settings.audio_dir)), name="audio")


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": "Research Paper Summarization API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/health",
            "search": "/api/v1/process/search",
            "upload": "/api/v1/process/upload",
            "status": "/api/v1/status/{workflow_id}",
            "docs": "/docs",
            "web_app": "/app"
        }
    }


@app.get("/app", response_class=HTMLResponse)
async def get_web_app():
    """Serve the web application interface"""
    try:
        html_file = settings.templates_dir / "index.html"
        if html_file.exists():
            with open(html_file, "r") as f:
                return HTMLResponse(content=f.read())
        else:
            # Return a simple HTML page if index.html doesn't exist
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Research Paper Summarization</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Research Paper Summarization API</h1>
                    <p>Welcome to the Research Paper Summarization System!</p>
                    
                    <h2>Available Endpoints:</h2>
                    <div class="endpoint">
                        <strong>POST /api/v1/process/search</strong><br>
                        Search and process research papers from academic databases
                    </div>
                    <div class="endpoint">
                        <strong>POST /api/v1/process/upload</strong><br>
                        Upload and process PDF/text files
                    </div>
                    <div class="endpoint">
                        <strong>GET /api/v1/status/{workflow_id}</strong><br>
                        Get the status of a processing workflow
                    </div>
                    <div class="endpoint">
                        <strong>GET /docs</strong><br>
                        Interactive API documentation
                    </div>
                    
                    <p><a href="/docs">Go to API Documentation</a></p>
                </div>
            </body>
            </html>
            """)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error loading web app</h1><p>{str(e)}</p>")


@app.websocket("/ws/status/{workflow_id}")
async def websocket_status(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time status updates"""
    await websocket.accept()
    print(f"INFO:     WebSocket connection opened for workflow {workflow_id}")
    
    try:
        # Use the same orchestrator instance as the routes
        from .routes import orchestrator
        
        while True:
            # Get current status
            status = orchestrator.get_workflow_status(workflow_id)
            
            if status:
                # Ensure status is JSON serializable before sending
                try:
                    # Test JSON serialization first
                    json.dumps(status)
                    await websocket.send_text(json.dumps(status))
                    print(f"📡 Sent WebSocket status: {status.get('status')} - {status.get('progress', 0)}%")
                except TypeError as e:
                    print(f"❌ WebSocket JSON error: {e}")
                    # Create a safe version without problematic fields
                    safe_status = {
                        'id': status.get('id', workflow_id),
                        'status': status.get('status', 'unknown'),
                        'progress': status.get('progress', 0),
                        'message': status.get('message', 'Processing...'),
                        'created_at': status.get('created_at', None)
                    }
                    
                    # Try to include results if available
                    if status.get('results') and status.get('status') == 'completed':
                        try:
                            results = status['results']
                            # Test if results are serializable
                            json.dumps(results)
                            safe_status['results'] = results
                            print(f"✅ WebSocket: Included results in safe status")
                        except TypeError as results_error:
                            print(f"⚠️ WebSocket: Results not serializable: {results_error}")
                            # Create simplified results
                            safe_results = {
                                'status': 'completed',
                                'papers_processed': len(results.get('papers', [])) if isinstance(results, dict) else 0,
                                'message': 'Results available but simplified for WebSocket'
                            }
                            safe_status['results'] = safe_results
                    
                    await websocket.send_text(json.dumps(safe_status))
                    print(f"📡 Sent safe WebSocket status: {safe_status.get('status')} - {safe_status.get('progress', 0)}%")
                
                # If workflow is completed or failed, send final update and close
                if status.get('status') in ['completed', 'failed']:
                    print(f"INFO:     WebSocket closing for completed workflow {workflow_id}")
                    await asyncio.sleep(1)  # Give client time to process final update
                    break
            else:
                print(f"❌ WebSocket: Workflow {workflow_id} not found")
                await websocket.send_text(json.dumps({
                    'status': 'not_found',
                    'error': 'Workflow not found',
                    'workflow_id': workflow_id
                }))
                break
            
            # Wait before next update (reduced for more responsive updates)
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ WebSocket error for {workflow_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                'error': f'WebSocket error: {str(e)}',
                'workflow_id': workflow_id
            }))
        except:
            pass
    finally:
        try:
            await websocket.close()
            print(f"INFO:     WebSocket connection closed for workflow {workflow_id}")
        except:
            pass
