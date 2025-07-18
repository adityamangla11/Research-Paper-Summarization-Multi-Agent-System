"""
Summarization Agent for generating paper summaries.
"""

import re
import ssl
import urllib.request
from typing import Dict, List

from .base_agent import BaseAgent
from ..models.data_models import ResearchPaper
from ..config.settings import settings


class SummarizationAgent(BaseAgent):
    """Agent responsible for generating summaries of research papers"""
    
    def __init__(self):
        super().__init__("Summarization")
        self._initialize_summarizer()
    
    def _initialize_summarizer(self):
        """Initialize the summarization model with lightweight approach"""
        # Import additional modules needed
        self.re = re
        
        # Check if we should use extractive summarization (much faster)
        if settings.use_extractive_summarization or getattr(settings, 'disable_heavy_models', True):
            print("🚀 Using extractive summarization (fast mode)")
            self.model_available = False  # Skip heavy models
            self._setup_nltk_data()
            return
        
        try:
            print("⚠️ Heavy AI models disabled for performance. Using extractive summarization only.")
            self.model_available = False
            
            # The following code is disabled to avoid loading heavy models:
            # from transformers import pipeline, AutoTokenizer
            # 
            # # Only try to load models if extractive is disabled
            # print("⏳ Loading AI summarization models (this may take a moment)...")
            # 
            # # Setup NLTK data first
            # self._setup_nltk_data()
            # 
            # # Try to load a simple model only if models are specified
            # if settings.summarization_models:
            #     for model_name in settings.summarization_models:
            #         try:
            #             print(f"🤖 Trying to load model: {model_name}")
            #             
            #             self.summarizer = pipeline(
            #                 "summarization",
            #                 model=model_name,
            #                 tokenizer=model_name,
            #                 device=-1,  # CPU only for simplicity
            #                 framework="pt"
            #             )
            #             
            #             # Test the model
            #             test_result = self.summarizer(
            #                 "This is a test sentence to verify the model works correctly.", 
            #                 max_length=30, 
            #                 min_length=10,
            #                 do_sample=False
            #             )
            #             
            #             if test_result:
            #                 self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            #                 print(f"✅ Successfully loaded model: {model_name}")
            #                 self.model_available = True
            #                 return
            #                 
            #         except Exception as e:
            #             print(f"⚠️ Failed to load {model_name}: {e}")
            #             continue
            # 
            # # If no models loaded, fall back to extractive
            # print("🔄 No models available, using extractive summarization")
            # self.model_available = False
            
        except ImportError as e:
            print(f"❌ Transformers not available ({e}), using extractive summarization")
            self.model_available = False
    
    def _setup_nltk_data(self):
        """Simple NLTK setup with fallbacks"""
        try:
            import nltk
            import ssl
            
            # Check if data is already available
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('corpora/stopwords')
                print("✅ NLTK data already available")
                return
            except LookupError:
                pass
            
            # Quick download attempt with SSL fix
            try:
                print("📥 Downloading NLTK data...")
                
                # Try with SSL context if available
                try:
                    _create_unverified_https_context = ssl._create_unverified_context
                    ssl._create_default_https_context = _create_unverified_https_context
                except AttributeError:
                    pass
                    
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                print("✅ NLTK data downloaded")
            except:
                print("⚠️ NLTK download failed, using simple fallbacks")
                
        except ImportError:
            print("⚠️ NLTK not available, using simple text processing")
    
    async def process(self, paper: ResearchPaper) -> Dict:
        """
        Generate structured summary of the research paper.
        
        Args:
            paper: ResearchPaper object to summarize
            
        Returns:
            Dictionary containing summary and metadata
        """
        try:
            if self.model_available and hasattr(self, 'summarizer'):
                return await self._generate_abstractive_summary(paper)
            else:
                return await self._generate_extractive_summary(paper)
        except Exception as e:
            print(f"❌ Error in summarization: {e}")
            return self._generate_fallback_summary(paper)
    
    async def _generate_abstractive_summary(self, paper: ResearchPaper) -> Dict:
        """Generate abstractive summary using transformer model"""
        text_to_summarize = self._prepare_text_for_summarization(paper)
        chunks = self._chunk_text(text_to_summarize, settings.max_chunk_length)
        
        summaries = []
        for chunk in chunks:
            try:
                result = self.summarizer(
                    chunk,
                    max_length=settings.max_summary_length,
                    min_length=settings.min_summary_length,
                    do_sample=False,
                    truncation=True
                )
                
                if result and len(result) > 0:
                    summaries.append(result[0]['summary_text'])
            except Exception as e:
                print(f"⚠️ Error summarizing chunk: {e}")
                continue
        
        final_summary = " ".join(summaries) if summaries else paper.abstract[:300]
        
        # Ensure abstractive summary is short for UI
        max_length = 150
        if len(final_summary) > max_length:
            # Find a good sentence break point
            truncated = final_summary[:max_length]
            last_period = truncated.rfind('.')
            last_space = truncated.rfind(' ')
            
            if last_period > max_length - 50:
                final_summary = truncated[:last_period + 1]
            elif last_space > max_length - 20:
                final_summary = truncated[:last_space] + "..."
            else:
                final_summary = truncated + "..."
        
        key_insights = self._extract_key_insights(paper, final_summary)
        
        return {
            'summary': final_summary,
            'paper_id': paper.id,
            'length': len(final_summary),
            'method': 'abstractive',
            'key_insights': key_insights,
            'topics': paper.topics,
            'title': paper.title
        }
    
    async def _generate_extractive_summary(self, paper: ResearchPaper) -> Dict:
        """Generate extractive summary using sentence ranking"""
        text_to_summarize = self._prepare_text_for_summarization(paper)
        
        # Ensure we have enough text to work with
        if len(text_to_summarize.strip()) < 100:
            return self._generate_fallback_summary(paper)
        
        sentences = self._tokenize_sentences(text_to_summarize)
        
        if len(sentences) == 0:
            return self._generate_fallback_summary(paper)
        elif len(sentences) <= 2:
            summary = " ".join(sentences)
        else:
            scored_sentences = self._score_sentences(sentences)
            
            # Select best sentences - adaptive based on total length
            total_sentences = len(sentences)
            if total_sentences <= 5:
                num_sentences = min(2, total_sentences)
            elif total_sentences <= 10:
                num_sentences = 3
            else:
                num_sentences = max(3, min(5, total_sentences // 4))
            
            # Get top sentences and maintain original order
            top_sentences = sorted(scored_sentences, key=lambda x: x[1], reverse=True)[:num_sentences]
            top_sentences.sort(key=lambda x: x[2])  # Sort by original index
            
            summary = " ".join([sent[0] for sent in top_sentences])
            
            # Ensure summary respects the configured max length (much shorter for UI)
            max_length = 150  # Even shorter than settings for better UI
            if len(summary) > max_length:
                # Find a good sentence break point
                truncated = summary[:max_length]
                last_period = truncated.rfind('.')
                last_space = truncated.rfind(' ')
                
                if last_period > max_length - 50:  # If period is reasonably close to end
                    summary = truncated[:last_period + 1]
                elif last_space > max_length - 20:  # If space is reasonably close
                    summary = truncated[:last_space] + "..."
                else:
                    summary = truncated + "..."
        
        # Extract key insights with improved patterns
        key_insights = self._extract_key_insights(paper, summary)
        
        # Debug output to see what we're generating
        print(f"📝 Generated summary (length {len(summary)}): {summary[:100]}...")
        
        return {
            'summary': summary,
            'paper_id': paper.id,
            'length': len(summary),
            'method': 'extractive',
            'key_insights': key_insights,
            'topics': paper.topics,
            'title': paper.title
        }
    
    def _prepare_text_for_summarization(self, paper: ResearchPaper) -> str:
        """Prepare and clean text for summarization"""
        # Prioritize abstract if it's meaningful
        if paper.abstract and len(paper.abstract.strip()) > 100:
            base_text = paper.abstract.strip()
        else:
            # If no good abstract, use beginning of content
            if paper.content:
                # Try to find meaningful paragraphs by skipping metadata/headers
                lines = paper.content.split('\n')
                meaningful_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Skip short lines, headers, references, etc.
                    if (len(line) > 50 and 
                        not line.isupper() and  # Skip all caps headers
                        not line.startswith(('http', 'doi:', 'DOI:', 'References', 'Bibliography')) and
                        not re.match(r'^[\d\.\s]+$', line)):  # Skip page numbers, etc.
                        meaningful_lines.append(line)
                    
                    # Take first few meaningful paragraphs
                    if len(' '.join(meaningful_lines)) > 1500:
                        break
                
                base_text = ' '.join(meaningful_lines[:5]) if meaningful_lines else paper.content[:1000]
            else:
                base_text = ""
        
        # Add title for context
        if paper.title:
            text = f"{paper.title}. {base_text}"
        else:
            text = base_text
        
        # Clean text more carefully
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[^\w\s.,;:!?\'-]', '', text)  # Remove special chars but keep punctuation
        text = text.strip()
        
        return text
    
    def _chunk_text(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _tokenize_sentences(self, text: str) -> List[str]:
        """Tokenize text into sentences"""
        try:
            import nltk
            from nltk.tokenize import sent_tokenize
            sentences = sent_tokenize(text)
        except:
            # Improved fallback regex-based sentence splitting
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for s in sentences:
            s = s.strip()
            # Filter out very short sentences and non-meaningful content
            if (len(s) > 20 and 
                not s.isupper() and  # Skip all caps
                not re.match(r'^[\d\s\.\-]+$', s) and  # Skip page numbers, etc.
                len(s.split()) > 3):  # At least 4 words
                cleaned_sentences.append(s)
        
        return cleaned_sentences
    
    def _score_sentences(self, sentences: List[str]) -> List[tuple]:
        """Score sentences for extractive summarization with improved algorithm"""
        from collections import Counter
        
        # Get stopwords with fallback
        try:
            from nltk.corpus import stopwords
            stop_words = set(stopwords.words('english'))
        except:
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                'for', 'of', 'with', 'by', 'as', 'is', 'are', 'was', 'were',
                'this', 'that', 'these', 'those', 'be', 'been', 'being', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
            }
        
        # Calculate word frequencies from all sentences
        word_freq = Counter()
        all_words = []
        
        for sentence in sentences:
            words = [word.lower() for word in re.findall(r'\b\w+\b', sentence) 
                    if word.lower() not in stop_words and len(word) > 2]
            word_freq.update(words)
            all_words.extend(words)
        
        # Important keywords that should be weighted higher
        important_keywords = {
            'research', 'study', 'finding', 'result', 'conclusion', 'analysis', 
            'method', 'approach', 'significant', 'important', 'novel', 'new',
            'propose', 'demonstrate', 'show', 'reveal', 'indicate', 'suggest',
            'improve', 'effective', 'performance', 'accuracy', 'model', 'algorithm'
        }
        
        scored_sentences = []
        for idx, sentence in enumerate(sentences):
            words = [word.lower() for word in re.findall(r'\b\w+\b', sentence) 
                    if word.lower() not in stop_words and len(word) > 2]
            
            if not words:
                scored_sentences.append((sentence, 0, idx))
                continue
            
            # Base score from word frequency
            base_score = sum(word_freq[word] for word in words) / len(words) if words else 0
            
            # Bonus for important keywords
            keyword_bonus = sum(2 for word in words if word in important_keywords)
            
            # Position bonus - favor earlier sentences but not too heavily
            position_bonus = 1.0 + (0.1 * max(0, (len(sentences) - idx) / len(sentences)))
            
            # Length bonus for reasonable length sentences
            length_bonus = 1.0
            sentence_length = len(sentence.split())
            if 10 <= sentence_length <= 30:  # Ideal length range
                length_bonus = 1.2
            elif sentence_length < 5 or sentence_length > 50:  # Too short or too long
                length_bonus = 0.5
            
            # Penalty for sentences with too many numbers/technical terms
            technical_ratio = len([w for w in words if re.match(r'\d', w)]) / len(words) if words else 0
            technical_penalty = 0.7 if technical_ratio > 0.3 else 1.0
            
            final_score = (base_score + keyword_bonus) * position_bonus * length_bonus * technical_penalty
            scored_sentences.append((sentence, final_score, idx))
        
        return scored_sentences
    
    def _extract_key_insights(self, paper: ResearchPaper, summary: str) -> List[str]:
        """Extract key insights from the paper and summary"""
        insights = []
        
        insight_patterns = [
            r'(?:we|the study|research|results?) (?:found|shows?|demonstrates?|reveals?|indicates?) (?:that )?([^.]+)',
            r'(?:the|our) (?:findings|results|conclusion) (?:suggest|indicate|show) (?:that )?([^.]+)',
        ]
        
        text_to_analyze = f"{summary} {paper.abstract}"
        
        for pattern in insight_patterns:
            matches = re.findall(pattern, text_to_analyze, re.IGNORECASE)
            for match in matches:
                insight = match.strip()
                if 20 < len(insight) < 200:
                    insights.append(insight)
        
        return insights[:3]
    
    def _generate_fallback_summary(self, paper: ResearchPaper) -> Dict:
        """Generate a more intelligent fallback summary"""
        summary_parts = []
        
        # Start with title context
        if paper.title:
            summary_parts.append(f"This research paper titled '{paper.title}'")
        else:
            summary_parts.append("This research paper")
        
        # Add topic context if available
        if paper.topics and len(paper.topics) > 0:
            topic_str = ", ".join(paper.topics[:3])  # Limit to first 3 topics
            summary_parts.append(f"focuses on {topic_str}")
        
        # Use abstract if available and meaningful
        if paper.abstract and len(paper.abstract.strip()) > 50:
            # Clean and truncate abstract
            clean_abstract = re.sub(r'\s+', ' ', paper.abstract.strip())
            if len(clean_abstract) > 300:
                clean_abstract = clean_abstract[:300] + "..."
            summary_parts.append(f"Abstract: {clean_abstract}")
        else:
            # Try to extract meaningful content from the beginning
            if paper.content:
                # Look for meaningful paragraphs
                lines = paper.content.split('\n')
                meaningful_content = []
                
                for line in lines[:10]:  # Check first 10 lines
                    line = line.strip()
                    if (len(line) > 30 and 
                        not line.isupper() and 
                        not line.startswith(('http', 'doi:', 'DOI:')) and
                        not re.match(r'^[\d\.\s\-]+$', line)):
                        meaningful_content.append(line)
                        if len(' '.join(meaningful_content)) > 200:
                            break
                
                if meaningful_content:
                    content_summary = ' '.join(meaningful_content)
                    if len(content_summary) > 250:
                        content_summary = content_summary[:250] + "..."
                    summary_parts.append(content_summary)
                else:
                    summary_parts.append("presents research findings and analysis")
            else:
                summary_parts.append("presents research findings and analysis")
        
        summary = ". ".join(summary_parts)
        if not summary.endswith('.'):
            summary += "."
        
        # Ensure fallback summary is short for UI
        max_length = 150
        if len(summary) > max_length:
            # Find a good sentence break point
            truncated = summary[:max_length]
            last_period = truncated.rfind('.')
            last_space = truncated.rfind(' ')
            
            if last_period > max_length - 50:
                summary = truncated[:last_period + 1]
            elif last_space > max_length - 20:
                summary = truncated[:last_space] + "..."
            else:
                summary = truncated + "..."
        
        return {
            'summary': summary,
            'paper_id': paper.id,
            'length': len(summary),
            'method': 'fallback',
            'key_insights': [],
            'topics': paper.topics,
            'title': paper.title
        }
