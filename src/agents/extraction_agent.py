"""
Extraction Agent for processing uploaded documents.
"""

import os
import re
import uuid
from typing import Dict, List, Optional, Any

from .base_agent import BaseAgent
from ..models.data_models import ResearchPaper


class ExtractionAgent(BaseAgent):
    """Agent responsible for extracting content from uploaded PDF and text files"""
    
    def __init__(self):
        super().__init__("Extraction")
        # Import PDF processing libraries
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
            self.pdf_available = True
        except ImportError:
            print("Warning: PyMuPDF not available, using fallback extraction")
            self.pdf_available = False
    
    async def process(self, paper_input: Dict) -> List[ResearchPaper]:
        """
        Extract content from PDF/text files.
        
        Args:
            paper_input: Dictionary containing file paths and topics
            
        Returns:
            List of ResearchPaper objects
        """
        papers = []
        
        for file_path in paper_input.get('file_paths', []):
            try:
                if self.pdf_available and file_path.lower().endswith('.pdf'):
                    paper = await self._extract_from_pdf(file_path, paper_input.get('topics', []))
                elif file_path.lower().endswith('.txt'):
                    # Handle text files with our metadata extraction
                    paper = await self._extract_from_text_file(file_path, paper_input.get('topics', []))
                else:
                    # Fallback for other file types
                    paper = self._create_fallback_paper(file_path, paper_input.get('topics', []))
                
                if paper:
                    papers.append(paper)
                    print(f"✅ Extracted content from: {os.path.basename(file_path)}")
                    
            except Exception as e:
                print(f"❌ Error extracting from {file_path}: {e}")
                # Create fallback paper even on error
                fallback_paper = self._create_fallback_paper(file_path, paper_input.get('topics', []))
                papers.append(fallback_paper)
        
        return papers
    
    async def _extract_from_pdf(self, file_path: str, topics: List[str]) -> Optional[ResearchPaper]:
        """Extract text and metadata from PDF using PyMuPDF"""
        try:
            doc = self.fitz.open(file_path)
            
            # Extract text from all pages
            full_text = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                full_text += text + "\\n"
            
            doc.close()
            
            # Extract metadata
            metadata = self._extract_metadata_from_text(full_text)
            
            paper = ResearchPaper(
                id=str(uuid.uuid4()),
                title=metadata['title'],
                authors=metadata['authors'],
                abstract=metadata['abstract'],
                content=full_text,
                doi=metadata['doi'],
                url="",
                topics=topics
            )
            
            return paper
            
        except Exception as e:
            print(f"Error processing PDF {file_path}: {e}")
            return None
    
    async def _extract_from_text_file(self, file_path: str, topics: List[str]) -> Optional[ResearchPaper]:
        """Extract text and metadata from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
            
            # Extract metadata
            metadata = self._extract_metadata_from_text(full_text)
            
            paper = ResearchPaper(
                id=str(uuid.uuid4()),
                title=metadata['title'],
                authors=metadata['authors'],
                abstract=metadata['abstract'],
                content=full_text,
                doi=metadata['doi'],
                url="",
                topics=topics
            )
            
            return paper
            
        except Exception as e:
            print(f"Error processing text file {file_path}: {e}")
            return None
    
    def _extract_metadata_from_text(self, text: str) -> Dict[str, Any]:
        """Extract title, authors, abstract, and DOI from text using simple parsing"""
        
        lines = text.split('\\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # Initialize metadata
        metadata = {
            'title': '',
            'authors': [],
            'abstract': '',
            'doi': ''
        }
        
        # Extract title (first non-empty line, or longest line in first few lines)
        title_candidates = []
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            if len(line) > 10 and not line.lower().startswith(('abstract', 'introduction', 'keywords', 'author')):
                # Score: prefer first lines, but also consider length
                score = (len(line) * 2) - (i * 10)  # Heavy preference for first lines
                title_candidates.append((score, line, i))
        
        if title_candidates:
            title_candidates.sort(reverse=True)
            # Take the first line if it's reasonable, otherwise the highest scoring
            first_line_candidate = [tc for tc in title_candidates if tc[2] == 0]
            if first_line_candidate and len(first_line_candidate[0][1]) > 15:
                metadata['title'] = first_line_candidate[0][1]
            else:
                metadata['title'] = title_candidates[0][1]
        else:
            # Fallback: use filename
            metadata['title'] = "Extracted Document"
        
        # Extract DOI using regex
        doi_pattern = r'(?:doi:|DOI:|https?://(?:dx\\.)?doi\\.org/)?\\s*(10\\.\\d+/[^\\s]+)'
        doi_match = re.search(doi_pattern, text, re.IGNORECASE)
        if doi_match:
            metadata['doi'] = doi_match.group(1)
        
        # Extract abstract
        abstract_start = -1
        abstract_end = -1
        
        for i, line in enumerate(lines):
            if line.lower().startswith('abstract'):
                abstract_start = i
                break
        
        if abstract_start != -1:
            # Find end of abstract (usually before "Introduction", "Keywords", or empty line)
            end_markers = ['introduction', 'keywords', 'key words', '1.', 'i.', 'background']
            for i in range(abstract_start + 1, min(abstract_start + 20, len(lines))):
                if any(lines[i].lower().startswith(marker) for marker in end_markers):
                    abstract_end = i
                    break
                elif not lines[i]:  # Empty line
                    abstract_end = i
                    break
            
            if abstract_end == -1:
                abstract_end = min(abstract_start + 15, len(lines))
            
            abstract_lines = lines[abstract_start:abstract_end]
            # Remove the "Abstract" header
            if abstract_lines and abstract_lines[0].lower().startswith('abstract'):
                abstract_lines = abstract_lines[1:]
            
            abstract_text = ' '.join(abstract_lines).strip()
            
            # HARD LIMIT: Ensure abstract is never longer than 500 characters
            if len(abstract_text) > 100:
                # Find a good break point (sentence end)
                sentences = abstract_text.split('. ')
                if len(sentences) > 1:
                    # Take sentences until we hit ~400 characters
                    truncated = ""
                    for sentence in sentences:
                        if len(truncated + sentence + '. ') <= 100:
                            truncated += sentence + '. '
                        else:
                            break
                    abstract_text = truncated.strip()
                else:
                    # No sentence breaks, just hard truncate
                    abstract_text = abstract_text[:100] + "..."
            
            metadata['abstract'] = abstract_text
        
        # Extract authors (heuristic: look for lines with names, usually after title)
        author_patterns = [
            r'^([A-Z][a-z]+ [A-Z][a-z]+(?:,?\\s+[A-Z][a-z]+ [A-Z][a-z]+)*)',  # Name patterns
            r'^([A-Z]\\. [A-Z][a-z]+(?:,?\\s+[A-Z]\\. [A-Z][a-z]+)*)',  # Initials + surname
        ]
        
        for i, line in enumerate(lines[1:6]):  # Check lines after title
            for pattern in author_patterns:
                match = re.match(pattern, line)
                if match:
                    # Split by common separators
                    authors_text = match.group(1)
                    authors = re.split(r',|\\sand\\s|\\s&\\s', authors_text)
                    metadata['authors'] = [author.strip() for author in authors if author.strip()]
                    break
            if metadata['authors']:
                break
        
        # If no abstract found, use first few paragraphs
        if not metadata['abstract'] and len(lines) > 10:
            # Skip title and author lines, take next few lines as abstract
            start_idx = 3
            end_idx = min(start_idx + 10, len(lines))
            potential_abstract = ' '.join(lines[start_idx:end_idx])
            if len(potential_abstract) > 100:
                # HARD LIMIT: Never exceed 100 characters for fallback abstract
                if len(potential_abstract) > 100:
                    potential_abstract = potential_abstract[:100] + "..."
                metadata['abstract'] = potential_abstract
        
        # Ensure we have at least some content
        if not metadata['title']:
            metadata['title'] = "Extracted PDF Document"
        if not metadata['authors']:
            metadata['authors'] = ["Unknown Author"]
        if not metadata['abstract']:
            metadata['abstract'] = "No abstract extracted"
        
        return metadata
    
    def _create_fallback_paper(self, file_path: str, topics: List[str]) -> ResearchPaper:
        """Create a fallback paper when extraction fails"""
        return ResearchPaper(
            id=str(uuid.uuid4()),
            title=f"Document: {os.path.basename(file_path)}",
            authors=["Unknown Author"],
            abstract="Content extraction failed or unsupported file format",
            content="Content extraction failed",
            doi="",
            url="",
            topics=topics
        )
