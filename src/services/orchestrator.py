"""
Workflow management service for orchestrating the research paper processing pipeline.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..models.data_models import ResearchPaper, ProcessingRequest, ProcessingResult
from ..models.database import WorkflowModel, get_db, DATABASE_AVAILABLE
from ..agents.discovery_agent import DiscoveryAgent
from ..agents.extraction_agent import ExtractionAgent
from ..agents.classification_agent import ClassificationAgent
from ..agents.summarization_agent import SummarizationAgent
from ..agents.synthesis_agent import SynthesisAgent
from ..agents.audio_agent import AudioAgent


class WorkflowManager:
    """Manages workflow state and persistence"""
    
    def __init__(self):
        self.workflows = {}  # In-memory storage for workflows
    
    def create_workflow(self, workflow_id: str, status: str = "pending"):
        """Create a new workflow entry"""
        workflow_data = {
            'id': workflow_id,
            'status': status,
            'progress': 0.0,
            'message': 'Workflow created',
            'created_at': datetime.now().isoformat()  # Convert to string for JSON serialization
        }
        
        self.workflows[workflow_id] = workflow_data
        
        # Also save to database if available
        if DATABASE_AVAILABLE:
            try:
                db = next(get_db())
                workflow_model = WorkflowModel(
                    id=workflow_id,
                    status=status,
                    progress=0.0,
                    message='Workflow created'
                )
                db.add(workflow_model)
                db.commit()
                db.close()
            except Exception as e:
                print(f"Warning: Could not save workflow to database: {e}")
    
    def update_workflow(self, workflow_id: str, **kwargs):
        """Update workflow status"""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].update(kwargs)
            print(f"📝 Updated workflow {workflow_id}: status={kwargs.get('status')}, progress={kwargs.get('progress')}")
            if 'results' in kwargs:
                print(f"📊 Results stored for workflow {workflow_id}: {type(kwargs['results'])}")
        
        # Also update database if available
        if DATABASE_AVAILABLE:
            try:
                db = next(get_db())
                workflow = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
                if workflow:
                    for key, value in kwargs.items():
                        if hasattr(workflow, key):
                            setattr(workflow, key, value)
                    db.commit()
                db.close()
            except Exception as e:
                print(f"Warning: Could not update workflow in database: {e}")
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Get workflow status"""
        return self.workflows.get(workflow_id)


class AgentOrchestrator:
    """Orchestrates the execution of multiple agents in the research paper processing pipeline"""
    
    def __init__(self):
        # Initialize all agents
        self.agents = {
            'discovery': DiscoveryAgent(),
            'extraction': ExtractionAgent(),
            'classification': ClassificationAgent(),
            'summarization': SummarizationAgent(),
            'synthesis': SynthesisAgent(),
            'audio': AudioAgent()
        }
        
        self.workflow_manager = WorkflowManager()
    
    async def process_research_request(self, request: Dict) -> Dict:
        """
        Process a complete research request through the agent pipeline.
        
        Args:
            request: Dictionary containing request parameters
            
        Returns:
            Dictionary containing processing results
        """
        # Don't create a new workflow here, let the caller manage it
        try:
            # Determine request type and process accordingly
            if request.get('search_query'):
                result = await self._process_search_request_direct(request)
            elif request.get('file_paths'):
                result = await self._process_upload_request_direct(request)
            else:
                raise ValueError("Invalid request: must contain either 'search_query' or 'file_paths'")
            
            return result
            
        except Exception as e:
            print(f"❌ Error in process_research_request: {e}")
            raise
    
    async def _process_search_request_direct(self, request: Dict) -> Dict:
        """Process a search-based request without workflow management"""
        
        print("🔍 Starting search processing...")
        
        # Step 1: Discovery
        papers = await self.agents['discovery'].process(request)
        print(f"📚 Discovery found {len(papers)} papers")
        
        if not papers:
            return {
                'papers': [],
                'papers_processed': 0,
                'classifications': [],
                'summaries': [],
                'synthesis': {'synthesis': 'No papers found for the search query', 'paper_count': 0},
                'audio_files': [],
                'status': 'completed'
            }
        
        # Step 2: Classification and Summarization
        print("🏷️ Starting classification and summarization...")
        classifications = []
        summaries = []
        
        for i, paper in enumerate(papers):
            print(f"Processing paper {i+1}/{len(papers)}: {paper.title[:50]}...")
            
            # Classification
            classification = await self.agents['classification'].process(paper)
            classifications.append(classification)
            # Update paper topics
            paper.topics = classification
            
            # Summarization
            summary = await self.agents['summarization'].process(paper)
            summaries.append(summary)
        
        # Step 3: Synthesis
        print("🧠 Starting synthesis...")
        synthesis_input = {
            'papers': papers,
            'classifications': classifications,
            'summaries': summaries
        }
        synthesis = await self.agents['synthesis'].process(synthesis_input)
        
        # Step 4: Audio generation
        print("🔊 Starting audio generation...")
        audio_files = await self.agents['audio'].process(synthesis)
        
        # Convert audio file paths to accessible URLs (like the original)
        audio_urls = []
        for audio_file in audio_files:
            if audio_file.startswith('audio/'):
                # Convert to URL path: audio/file.mp3 -> /audio/file.mp3
                filename = audio_file.split('/', 1)[1]
                audio_url = f"/audio/{filename}"
                audio_urls.append(audio_url)
            else:
                audio_urls.append(audio_file)
        
        # Convert papers to serializable format - use consistent .to_dict() now
        papers_data = [paper.to_dict() for paper in papers]
        
        result = {
            'papers': papers_data,
            'papers_processed': len(papers),
            'classifications': classifications,
            'summaries': summaries,
            'synthesis': synthesis,
            'audio_files': audio_urls,
            'status': 'completed'
        }
        
        print(f"✅ Search processing complete: {len(papers)} papers processed")
        return result
    
    async def _process_upload_request_direct(self, request: Dict) -> Dict:
        """Process an upload-based request without workflow management"""
        
        print("📁 Starting upload processing...")
        
        # Step 1: Extraction
        papers = await self.agents['extraction'].process(request)
        print(f"📄 Extraction found {len(papers)} papers")
        
        if not papers:
            return {
                'papers': [],
                'classifications': [],
                'summaries': [],
                'synthesis': {'synthesis': 'No content extracted from files'},
                'audio_files': []
            }
        
        # Continue with the same pipeline as search requests
        return await self._continue_processing_pipeline_direct(papers)
    
    async def _continue_processing_pipeline_direct(self, papers: List[ResearchPaper]) -> Dict:
        """Continue processing pipeline from classification onwards without workflow management"""
        
        # Step 2: Classification
        print("🏷️ Starting classification...")
        classifications = []
        for paper in papers:
            classification = await self.agents['classification'].process(paper)
            classifications.append(classification)
            paper.topics = classification
        
        # Step 3: Summarization
        print("📝 Starting summarization...")
        summaries = []
        for paper in papers:
            summary = await self.agents['summarization'].process(paper)
            summaries.append(summary)
        
        # Step 4: Synthesis
        print("🧠 Starting synthesis...")
        synthesis_input = {
            'papers': papers,
            'classifications': classifications,
            'summaries': summaries
        }
        synthesis = await self.agents['synthesis'].process(synthesis_input)
        
        # Step 5: Audio generation
        print("🔊 Starting audio generation...")
        audio_files = await self.agents['audio'].process(synthesis)
        
        result = {
            'papers': [paper.to_dict() for paper in papers],  # Now consistently truncated
            'classifications': classifications,
            'summaries': summaries,
            'synthesis': synthesis,
            'audio_files': audio_files
        }
        
        print(f"✅ Upload processing complete: {len(papers)} papers processed")
        return result
    
    async def _process_search_request(self, workflow_id: str, request: Dict) -> Dict:
        """Process a search-based request"""
        
        # Step 1: Discovery
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=10.0,
            message="Searching for papers..."
        )
        
        papers = await self.agents['discovery'].process(request)
        
        if not papers:
            return {
                'workflow_id': workflow_id,
                'papers': [],
                'message': 'No papers found'
            }
        
        # Step 2: Classification
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=30.0,
            message="Classifying papers..."
        )
        
        classifications = []
        for paper in papers:
            classification = await self.agents['classification'].process(paper)
            classifications.append(classification)
            # Update paper topics
            paper.topics = classification
        
        # Step 3: Summarization
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=60.0,
            message="Generating summaries..."
        )
        
        summaries = []
        for paper in papers:
            summary = await self.agents['summarization'].process(paper)
            summaries.append(summary)
        
        # Step 4: Synthesis
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=80.0,
            message="Synthesizing findings..."
        )
        
        synthesis_input = {
            'papers': papers,
            'classifications': classifications,
            'summaries': summaries
        }
        synthesis = await self.agents['synthesis'].process(synthesis_input)
        
        # Step 5: Audio generation
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=90.0,
            message="Generating audio..."
        )
        
        audio_files = await self.agents['audio'].process(synthesis)
        
        return {
            'workflow_id': workflow_id,
            'papers': [paper.to_dict() for paper in papers],
            'classifications': classifications,
            'summaries': summaries,
            'synthesis': synthesis,
            'audio_files': audio_files
        }
    
    async def _process_upload_request(self, workflow_id: str, request: Dict) -> Dict:
        """Process an upload-based request"""
        
        # Step 1: Extraction
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=10.0,
            message="Extracting content from files..."
        )
        
        papers = await self.agents['extraction'].process(request)
        
        if not papers:
            return {
                'workflow_id': workflow_id,
                'papers': [],
                'message': 'No content extracted from files'
            }
        
        # Continue with the same pipeline as search requests
        return await self._continue_processing_pipeline(workflow_id, papers)
    
    async def _continue_processing_pipeline(self, workflow_id: str, papers: List[ResearchPaper]) -> Dict:
        """Continue processing pipeline from classification onwards"""
        
        # Step 2: Classification
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=30.0,
            message="Classifying papers..."
        )
        
        classifications = []
        for paper in papers:
            classification = await self.agents['classification'].process(paper)
            classifications.append(classification)
            paper.topics = classification
        
        # Step 3: Summarization
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=60.0,
            message="Generating summaries..."
        )
        
        summaries = []
        for paper in papers:
            summary = await self.agents['summarization'].process(paper)
            summaries.append(summary)
        
        # Step 4: Synthesis
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=80.0,
            message="Synthesizing findings..."
        )
        
        synthesis_input = {
            'papers': papers,
            'classifications': classifications,
            'summaries': summaries
        }
        synthesis = await self.agents['synthesis'].process(synthesis_input)
        
        # Step 5: Audio generation
        self.workflow_manager.update_workflow(
            workflow_id,
            progress=90.0,
            message="Generating audio..."
        )
        
        audio_files = await self.agents['audio'].process(synthesis)
        
        return {
            'workflow_id': workflow_id,
            'papers': [paper.to_dict() for paper in papers],
            'classifications': classifications,
            'summaries': summaries,
            'synthesis': synthesis,
            'audio_files': audio_files
        }
    
    async def process_research_request_with_workflow(self, workflow_id: str, request: Dict) -> Dict:
        """
        Process a complete research request through the agent pipeline using an existing workflow.
        
        Args:
            workflow_id: Existing workflow ID to use for tracking
            request: Dictionary containing request parameters
            
        Returns:
            Dictionary containing processing results
        """
        try:
            # Determine request type and process accordingly
            if request.get('search_query'):
                result = await self._process_search_request(workflow_id, request)
            elif request.get('file_paths'):
                result = await self._process_upload_request(workflow_id, request)
            else:
                raise ValueError("Invalid request: must contain either 'search_query' or 'file_paths'")
            
            return result
            
        except Exception as e:
            # Update workflow as failed
            self.workflow_manager.update_workflow(
                workflow_id,
                status="failed",
                progress=0.0,
                message=f"Processing failed: {str(e)}"
            )
            raise

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get the status of a workflow"""
        return self.workflow_manager.get_workflow(workflow_id)
