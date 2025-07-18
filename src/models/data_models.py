"""
Data models for the Research Paper Summarization System.
"""

import uuid
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class ResearchPaper:
    """Data class representing a research paper"""
    id: str
    title: str
    authors: List[str]
    abstract: str
    content: str
    doi: str
    url: str
    topics: List[str]
    
    def to_dict(self, truncate_for_api: bool = True) -> Dict[str, Any]:
        """Convert to dictionary with optional truncation for API responses"""
        
        def truncate_by_words(text: str, max_words: int) -> str:
            """Truncates text to a specified number of words."""
            if not text:
                return ""
            words = text.split()
            if len(words) > max_words:
                return " ".join(words[:max_words]) + "..."
            return text
        
        # Apply same truncation logic as routes.py for consistency
        if truncate_for_api:
            abstract_preview = truncate_by_words(self.abstract, 100)
            content_preview = self.content[:100] + "..." if len(self.content) > 150 else self.content
        else:
            abstract_preview = self.abstract
            content_preview = self.content
        
        return {
            'id': self.id,
            'title': self.title,
            'authors': self.authors,
            'abstract': abstract_preview,
            'content': content_preview,
            'doi': self.doi,
            'url': self.url,
            'topics': self.topics
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with full content (for internal use only)"""
        return self.to_dict(truncate_for_api=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchPaper':
        """Create from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            authors=data.get('authors', []),
            abstract=data.get('abstract', ''),
            content=data.get('content', ''),
            doi=data.get('doi', ''),
            url=data.get('url', ''),
            topics=data.get('topics', [])
        )

@dataclass
class ProcessingRequest:
    """Data class representing a processing request"""
    workflow_id: str
    request_type: str  # 'search' or 'upload'
    parameters: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workflow_id': self.workflow_id,
            'request_type': self.request_type,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class ProcessingResult:
    """Data class representing processing results"""
    workflow_id: str
    status: str
    progress: float
    message: str
    papers: List[ResearchPaper]
    classifications: List[List[str]]
    summaries: List[Dict[str, Any]]
    synthesis: Dict[str, Any]
    audio_files: List[str]
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workflow_id': self.workflow_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'papers': [paper.to_dict() for paper in self.papers],
            'classifications': self.classifications,
            'summaries': self.summaries,
            'synthesis': self.synthesis,
            'audio_files': self.audio_files,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
