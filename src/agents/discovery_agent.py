"""
Discovery Agent for searching academic databases.
"""

import uuid
import datetime
from typing import Dict, List
import httpx
import xml.etree.ElementTree as ET

from .base_agent import BaseAgent
from ..models.data_models import ResearchPaper
from ..config.settings import settings


class DiscoveryAgent(BaseAgent):
    """Agent responsible for discovering and searching research papers from academic databases"""
    
    def __init__(self):
        super().__init__("Discovery")
        self.arxiv_base_url = settings.arxiv_base_url
        self.search_apis = {
            'arxiv': settings.arxiv_base_url,
            'pubmed': settings.pubmed_base_url,
            'semantic_scholar': settings.semantic_scholar_base_url
        }
    
    async def process(self, query: Dict) -> List[ResearchPaper]:
        """
        Search multiple academic databases for research papers.
        
        Args:
            query: Dictionary containing search parameters
            
        Returns:
            List of ResearchPaper objects
        """
        search_query = query.get('search_query', '')
        max_papers = query.get('max_papers', settings.max_papers_default)
        
        # Extract advanced filtering parameters
        from_year = query.get('from_year')
        to_year = query.get('to_year')
        publication_type = query.get('publication_type')
        min_citations = query.get('min_citations')
        must_include = query.get('must_include', [])
        must_exclude = query.get('must_exclude', [])
        
        if not search_query:
            print("Warning: No search query provided")
            return []
        
        # Use real ArXiv search with advanced filters
        try:
            papers = await self.search_arxiv(
                search_query, 
                max_papers,
                from_year=from_year,
                to_year=to_year,
                publication_type=publication_type,
                min_citations=min_citations,
                must_include=must_include,
                must_exclude=must_exclude
            )
            print(f"✅ Found {len(papers)} papers from ArXiv for query: '{search_query}'")
            return papers
        except Exception as e:
            print(f"❌ Error in ArXiv search: {e}")
            # Fallback to mock data in case of error
            return [
                ResearchPaper(
                    id=str(uuid.uuid4()),
                    title=f"Fallback: Research Paper on {search_query}",
                    authors=["Dr. Fallback"],
                    abstract=f"Fallback paper about {search_query} (ArXiv search failed)...",
                    content="Fallback content...",
                    doi="fallback",
                    url="",
                    topics=query.get('topics', ['AI'])
                )
            ]
    
    async def search_arxiv(self, query: str, max_results: int = 10, 
                          from_year: int = None, to_year: int = None,
                          publication_type: str = None, min_citations: int = None,
                          must_include: List[str] = None, must_exclude: List[str] = None) -> List[ResearchPaper]:
        """
        Search ArXiv for papers with advanced filtering options.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            from_year: Start year for date filtering
            to_year: End year for date filtering
            publication_type: Type of publication to filter by
            min_citations: Minimum citation count (not supported by ArXiv)
            must_include: Terms that must be included
            must_exclude: Terms that must be excluded
            
        Returns:
            List of ResearchPaper objects
        """
        # Build the search query with filters
        search_terms = []
        
        # Base query
        search_terms.append(f'all:{query}')
        
        # Add must_include terms (AND operation)
        if must_include:
            for term in must_include:
                search_terms.append(f'all:{term}')
        
        # Add must_exclude terms (NOT operation)
        if must_exclude:
            for term in must_exclude:
                search_terms.append(f'ANDNOT all:{term}')
        
        # Combine search terms
        search_query = ' AND '.join(search_terms)
        
        # Add date filtering using submittedDate
        if from_year or to_year:
            date_filter = []
            if from_year:
                date_filter.append(f'submittedDate:[{from_year}0101000000 TO ')
                if to_year:
                    date_filter.append(f'{to_year}1231235959]')
                else:
                    # If only from_year specified, use current year as upper bound
                    current_year = datetime.datetime.now().year
                    date_filter.append(f'{current_year}1231235959]')
            elif to_year:
                # If only to_year specified, use 1990 as lower bound (ArXiv started in 1991)
                date_filter.append(f'submittedDate:[19900101000000 TO {to_year}1231235959]')
            
            if date_filter:
                search_query += f' AND {"".join(date_filter)}'
        
        # Add publication type filter (map to ArXiv categories if needed)
        if publication_type:
            # Map common publication types to ArXiv categories
            type_mapping = {
                'cs': 'cat:cs.*',  # Computer Science
                'physics': 'cat:physics.*',
                'math': 'cat:math.*',
                'stat': 'cat:stat.*',
                'econ': 'cat:econ.*',
                'bio': 'cat:q-bio.*',
                'finance': 'cat:q-fin.*'
            }
            arxiv_category = type_mapping.get(publication_type.lower(), f'cat:{publication_type}*')
            search_query += f' AND {arxiv_category}'
        
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        try:
            # Use httpx with SSL verification disabled and follow redirects
            async with httpx.AsyncClient(verify=False, timeout=30.0, follow_redirects=True) as client:
                response = await client.get(self.arxiv_base_url, params=params)
                if response.status_code == 200:
                    xml_content = response.text
                    papers = self._parse_arxiv_response(xml_content)
                    
                    # Apply post-processing filters that ArXiv doesn't support directly
                    if min_citations is not None:
                        # Note: ArXiv doesn't provide citation data, so we'll log this limitation
                        print(f"Warning: Citation filtering (min_citations={min_citations}) not supported by ArXiv API")
                    
                    return papers
                else:
                    print(f"ArXiv API error: {response.status_code}")
                    return []
        except httpx.TimeoutException:
            print("ArXiv API timeout - using fallback")
            return []
        except Exception as e:
            print(f"Error searching ArXiv: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_content: str) -> List[ResearchPaper]:
        """
        Parse ArXiv XML response into ResearchPaper objects.
        
        Args:
            xml_content: XML response from ArXiv API
            
        Returns:
            List of ResearchPaper objects
        """
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Define namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            for entry in root.findall('atom:entry', namespaces):
                # Extract title
                title_elem = entry.find('atom:title', namespaces)
                title = title_elem.text.strip() if title_elem is not None else "No title"
                
                # Extract authors
                authors = []
                for author in entry.findall('atom:author', namespaces):
                    name_elem = author.find('atom:name', namespaces)
                    if name_elem is not None:
                        authors.append(name_elem.text)
                
                # Extract abstract
                summary_elem = entry.find('atom:summary', namespaces)
                abstract = summary_elem.text.strip() if summary_elem is not None else "No abstract"
                
                # Extract DOI and URL
                doi = ""
                url = ""
                for link in entry.findall('atom:link', namespaces):
                    href = link.get('href', '')
                    if 'arxiv.org/abs/' in href:
                        url = href
                        # Extract arXiv ID which can serve as DOI
                        arxiv_id = href.split('/')[-1]
                        doi = f"arXiv:{arxiv_id}"
                
                # Create paper object
                paper = ResearchPaper(
                    id=str(uuid.uuid4()),
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    content=abstract,  # For now, use abstract as content
                    doi=doi,
                    url=url,
                    topics=[]  # Will be filled by classification agent
                )
                
                papers.append(paper)
                
        except ET.ParseError as e:
            print(f"Error parsing ArXiv XML: {e}")
        
        return papers
