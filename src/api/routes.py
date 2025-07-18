"""
FastAPI routes for the Research Paper Summarization System.
"""

import os
import uuid
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from fastapi.responses import JSONResponse

from ..services.orchestrator import AgentOrchestrator
from ..config.settings import settings

def truncate_by_words(text: str, max_words: int) -> str:
    """Truncates text to a specified number of words."""
    if not text:
        return ""
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return text

# Create router
router = APIRouter(prefix="/api/v1")

# Initialize orchestrator
orchestrator = AgentOrchestrator()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Research Paper Summarization API",
        "version": "1.0.0"
    }


@router.post("/process/search")
async def process_search_request(request: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Process research papers based on search query.
    
    Args:
        request: Dictionary containing search parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        Workflow ID and initial status
    """
    try:
        # Validate request - accept both 'search_query' and 'query' for backwards compatibility
        search_query = request.get('search_query') or request.get('query')
        if not search_query:
            raise HTTPException(status_code=400, detail="search_query or query is required")
        
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Add background task for processing
        background_tasks.add_task(
            _process_search_background,
            workflow_id,
            request
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "processing",
            "message": "Search request submitted for processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/upload")
async def process_upload_request(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...),
    topics: List[str] = Form(default=[])
):
    """
    Process uploaded PDF/text files.
    
    Args:
        background_tasks: FastAPI background tasks
        files: List of uploaded files
        topics: List of topics (optional)
        
    Returns:
        Workflow ID and initial status
    """
    try:
        # Save uploaded files
        file_paths = []
        for file in files:
            file_path = settings.uploads_dir / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            file_paths.append(str(file_path))
        
        # Filter empty topics
        topics_list = [topic.strip() for topic in topics if topic.strip()]
        
        # Prepare request
        request = {
            'file_paths': file_paths,
            'topics': topics_list
        }
        
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Add background task for processing
        background_tasks.add_task(
            _process_upload_background,
            workflow_id,
            request
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "processing",
            "message": "Upload request submitted for processing",
            "uploaded_files": [file.filename for file in files],
            "topics": topics_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    Get the status of a workflow.
    
    Args:
        workflow_id: Unique workflow identifier
        
    Returns:
        Workflow status information
    """
    try:
        status = orchestrator.get_workflow_status(workflow_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Ensure the status is JSON serializable (like the original)
        try:
            # Test JSON serialization
            import json
            json.dumps(status)
            return status
        except TypeError as e:
            print(f"❌ JSON serialization error in status endpoint: {e}")
            # Return a safe version of the status
            safe_status = {
                'id': status.get('id', workflow_id),
                'status': status.get('status', 'unknown'),
                'progress': status.get('progress', 0),
                'message': status.get('message', 'Processing...'),
                'created_at': status.get('created_at', None)
            }
            
            # Add results if available and safe
            if status.get('results') and status.get('status') == 'completed':
                try:
                    # Try to include results but with simplified structure
                    results = status['results']
                    safe_results = {
                        'workflow_id': results.get('workflow_id'),
                        'papers_processed': results.get('papers_processed', 0),
                        'status': results.get('status'),
                        'papers': [],  # Initialize empty, will populate below
                        'summaries': results.get('summaries', []),
                        'audio_files': results.get('audio_files', [])
                    }
                    
                    # Ensure papers are properly truncated for API
                    papers_data = results.get('papers', [])
                    safe_papers = []
                    for paper_data in papers_data:
                        if hasattr(paper_data, 'to_dict'):
                            # This is a ResearchPaper object, use truncated dict
                            safe_papers.append(paper_data.to_dict(truncate_for_api=True))
                        elif isinstance(paper_data, dict):
                            # This is already a dict, use as-is (should be truncated from background task)
                            safe_papers.append(paper_data)
                        else:
                            # Unknown type, skip
                            continue
                    safe_results['papers'] = safe_papers
                    
                    # Handle synthesis separately to avoid nested dict issues
                    if results.get('synthesis'):
                        synthesis = results['synthesis']
                        safe_synthesis = {
                            'synthesis': synthesis.get('synthesis', ''),
                            'paper_count': synthesis.get('paper_count', 0)
                        }
                        safe_results['synthesis'] = safe_synthesis
                    
                    safe_status['results'] = safe_results
                    
                except Exception as synthesis_error:
                    print(f"⚠️ Error including synthesis in status: {synthesis_error}")
                    safe_status['results'] = {
                        'status': 'completed',
                        'papers_processed': status.get('results', {}).get('papers_processed', 0),
                        'message': 'Results available but synthesis data simplified due to formatting'
                    }
            
            return safe_status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/test")
async def test_search_processing(request: Dict[str, Any]):
    """
    Test endpoint to debug search processing without background tasks.
    """
    try:
        # Normalize request data
        search_query = request.get('search_query') or request.get('query')
        if not search_query:
            return {"error": "search_query or query is required"}
        
        # Add search_query if missing
        if 'query' in request and 'search_query' not in request:
            request['search_query'] = request['query']
        
        # Test basic orchestrator import
        from ..services.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()
        
        return {
            "status": "success",
            "message": f"Test successful for query: '{search_query}'",
            "normalized_request": {
                "search_query": request.get('search_query'),
                "max_papers": request.get('max_papers', 5)
            }
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


async def _process_search_background(workflow_id: str, request: Dict[str, Any]):
    """Background task for processing search requests"""
    try:
        # Normalize request data - ensure 'search_query' field exists
        if 'query' in request and 'search_query' not in request:
            request['search_query'] = request['query']
        
        print(f"🚀 Starting background processing for workflow {workflow_id}")
        print(f"🔍 Query: {request.get('search_query')}")
        
        # Create workflow entry and update status
        orchestrator.workflow_manager.create_workflow(workflow_id, "processing")
        
        # Stage 1: Starting search
        orchestrator.workflow_manager.update_workflow(
            workflow_id, 
            message="Searching ArXiv database...", 
            progress=20.0
        )
        
        # Add a small delay to make progress visible
        await asyncio.sleep(1.0)
        
        # Get papers
        papers = await orchestrator.agents['discovery'].process(request)
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            message=f"Found {len(papers)} papers",
            progress=30.0
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(0.5)
        
        if not papers:
            orchestrator.workflow_manager.update_workflow(
                workflow_id,
                status="completed",
                progress=100.0,
                message="No papers found",
                results={
                    'papers': [],
                    'papers_processed': 0,
                    'classifications': [],
                    'summaries': [],
                    'synthesis': {'synthesis': 'No papers found for the search query', 'paper_count': 0},
                    'audio_files': [],
                    'status': 'completed'
                }
            )
            return
        
        # Stage 2: Classification and Summarization (30-70%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=35.0,
            message="Starting paper analysis..."
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(0.5)
        
        summaries = []
        classifications = []
        total_papers = len(papers)
        
        for i, paper in enumerate(papers):
            # Update progress for each paper processed
            paper_progress = 35 + int((i / total_papers) * 35)  # 35-70% range
            orchestrator.workflow_manager.update_workflow(
                workflow_id, 
                progress=paper_progress, 
                message=f"Analyzing paper {i+1}/{total_papers}: {paper.title[:50]}..."
            )
            
            # Add delay to make progress visible
            await asyncio.sleep(1.0)
            
            # Process classification and summarization
            classification = await orchestrator.agents['classification'].process(paper)
            summary = await orchestrator.agents['summarization'].process(paper)
            classifications.append(classification)
            summaries.append(summary)
            # Update paper topics
            paper.topics = classification
        
        # Stage 3: Synthesis (70-85%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=75.0,
            message="Synthesizing findings across papers..."
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(1.0)
        
        synthesis_input = {
            'papers': papers,
            'classifications': classifications,
            'summaries': summaries
        }
        synthesis = await orchestrator.agents['synthesis'].process(synthesis_input)
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=85.0,
            message="Synthesis completed"
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(0.5)
        
        # Stage 4: Audio generation (85-95%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=90.0,
            message="Generating audio summary..."
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(1.0)
        
        audio_files = await orchestrator.agents['audio'].process(synthesis)
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=95.0,
            message="Audio generation completed"
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(0.5)
        
        # Final processing (95-100%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=98.0,
            message="Finalizing results..."
        )
        
        # Convert audio file paths to accessible URLs
        audio_urls = []
        for audio_file in audio_files:
            if audio_file.startswith('audio/'):
                # Convert to URL path: audio/file.mp3 -> /audio/file.mp3
                filename = audio_file.split('/', 1)[1]
                audio_url = f"/audio/{filename}"
                audio_urls.append(audio_url)
            else:
                audio_urls.append(audio_file)
        
        # Convert papers to serializable format
        papers_data = []
        for paper in papers:
            # Ensure abstract is reasonable length for UI display
            abstract_preview = truncate_by_words(paper.abstract, 100)
                
            paper_dict = {
                'id': paper.id,
                'title': paper.title,
                'authors': paper.authors,
                'abstract': abstract_preview,
                'content': paper.content[:100] + "..." if len(paper.content) > 150 else paper.content,  # Truncate for UI
                'doi': paper.doi,
                'url': paper.url,
                'topics': paper.topics
            }
            papers_data.append(paper_dict)
        
        result = {
            'workflow_id': workflow_id,
            'papers': papers_data,
            'papers_processed': len(papers),
            'summaries': summaries,
            'classifications': classifications,
            'synthesis': synthesis,
            'audio_files': audio_urls,
            'status': 'completed'
        }
        
        # Store results in the workflow
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            status="completed",
            progress=100.0,
            message="Processing completed successfully!",
            results=result
        )
        
        print(f"✅ Workflow {workflow_id} completed successfully!")
        print(f"� Processed {len(papers)} papers")
        print(f"🎯 Generated {len(summaries)} summaries")
        print(f"🔊 Created {len(audio_files)} audio files")
        print(f"�💾 Results stored for workflow {workflow_id}")
        
    except Exception as e:
        print(f"❌ Error processing workflow {workflow_id}: {e}")
        import traceback
        print(f"📍 Traceback: {traceback.format_exc()}")
        
        # Update workflow with error status
        error_result = {
            'workflow_id': workflow_id,
            'error': str(e),
            'status': 'failed'
        }
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            status="failed",
            message=f"Processing failed: {str(e)}",
            progress=0.0,
            results=error_result
        )


async def _process_upload_background(workflow_id: str, request: Dict[str, Any]):
    """Background task for processing upload requests"""
    try:
        print(f"🚀 Starting background processing for upload workflow {workflow_id}")
        print(f"📁 Files: {request.get('file_paths', [])}")
        print(f"🏷️ Topics: {request.get('topics', [])}")
        
        # Create workflow entry and update status
        orchestrator.workflow_manager.create_workflow(workflow_id, "processing")
        
        # Stage 1: Processing uploaded files
        orchestrator.workflow_manager.update_workflow(
            workflow_id, 
            message="Processing uploaded files...", 
            progress=10.0
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(1.0)
        
        # Extract content from files
        papers = await orchestrator.agents['extraction'].process(request)
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            message=f"Extracted content from {len(papers)} files",
            progress=25.0
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(0.5)
        
        if not papers:
            orchestrator.workflow_manager.update_workflow(
                workflow_id,
                status="completed",
                progress=100.0,
                message="No content could be extracted from uploaded files",
                results={
                    'papers': [],
                    'papers_processed': 0,
                    'classifications': [],
                    'summaries': [],
                    'synthesis': {'synthesis': 'No content could be extracted from uploaded files', 'paper_count': 0},
                    'audio_files': [],
                    'status': 'completed'
                }
            )
            return
        
        # Stage 2: Classification and Summarization (25-65%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=30.0,
            message="Starting document analysis..."
        )
        
        # Add delay to make progress visible
        await asyncio.sleep(0.5)
        
        summaries = []
        classifications = []
        total_papers = len(papers)
        
        for i, paper in enumerate(papers):
            # Update progress for each paper processed
            paper_progress = 30 + int((i / total_papers) * 35)  # 30-65% range
            orchestrator.workflow_manager.update_workflow(
                workflow_id, 
                progress=paper_progress, 
                message=f"Analyzing document {i+1}/{total_papers}: {paper.title[:50]}..."
            )
            
            # Add delay to make progress visible
            await asyncio.sleep(1.0)
            
            # Process classification and summarization
            classification = await orchestrator.agents['classification'].process(paper)
            summary = await orchestrator.agents['summarization'].process(paper)
            
            classifications.append(classification)
            summaries.append(summary)
            # Update paper topics
            paper.topics = classification
        
        # Stage 3: Synthesis (65-80%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=70.0,
            message="Synthesizing findings across documents..."
        )
        
        synthesis_input = {
            'papers': papers,
            'classifications': classifications,
            'summaries': summaries
        }
        synthesis = await orchestrator.agents['synthesis'].process(synthesis_input)
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=80.0,
            message="Synthesis completed"
        )
        
        # Stage 4: Audio generation (80-95%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=85.0,
            message="Generating audio summary..."
        )
        
        audio_files = await orchestrator.agents['audio'].process(synthesis)
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=95.0,
            message="Audio generation completed"
        )
        
        # Final processing (95-100%)
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            progress=98.0,
            message="Finalizing results..."
        )
        
        # Convert audio file paths to accessible URLs
        audio_urls = []
        for audio_file in audio_files:
            if audio_file.startswith('audio/'):
                # Convert to URL path: audio/file.mp3 -> /audio/file.mp3
                filename = audio_file.split('/', 1)[1]
                audio_url = f"/audio/{filename}"
                audio_urls.append(audio_url)
            else:
                audio_urls.append(audio_file)
        
        # Convert papers to serializable format - EXACT SAME LOGIC AS SEARCH
        papers_data = []
        for paper in papers:
            # Use EXACTLY the same abstract processing as search functionality
            abstract_preview = truncate_by_words(paper.abstract, 100)
                
            paper_dict = {
                'id': paper.id,
                'title': paper.title,
                'authors': paper.authors,
                'abstract': abstract_preview,
                'content': paper.content[:100] + "..." if len(paper.content) > 150 else paper.content,  # Truncate for UI
                'doi': paper.doi,
                'url': paper.url,
                'topics': paper.topics
            }
            papers_data.append(paper_dict)
        
        result = {
            'workflow_id': workflow_id,
            'papers': papers_data,
            'papers_processed': len(papers),
            'summaries': summaries,
            'classifications': classifications,
            'synthesis': synthesis,
            'audio_files': audio_urls,
            'status': 'completed'
        }
        
        # Store results in the workflow
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            status="completed",
            progress=100.0,
            message="Upload processing completed successfully!",
            results=result
        )
        
        print(f"✅ Upload workflow {workflow_id} completed successfully!")
        print(f"📄 Processed {len(papers)} documents")
        print(f"🎯 Generated {len(summaries)} summaries")
        print(f"🔊 Created {len(audio_files)} audio files")
        print(f"💾 Results stored for workflow {workflow_id}")
        
    except Exception as e:
        print(f"❌ Error processing upload workflow {workflow_id}: {e}")
        import traceback
        print(f"📍 Traceback: {traceback.format_exc()}")
        
        # Update workflow with error status
        error_result = {
            'workflow_id': workflow_id,
            'error': str(e),
            'status': 'failed'
        }
        
        orchestrator.workflow_manager.update_workflow(
            workflow_id,
            status="failed",
            message=f"Upload processing failed: {str(e)}",
            progress=0.0,
            results=error_result
        )
