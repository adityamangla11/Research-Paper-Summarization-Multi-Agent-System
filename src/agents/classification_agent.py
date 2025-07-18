"""
Classification Agent for categorizing research papers into topics.
"""

import re
from typing import Dict, List
from collections import Counter

from .base_agent import BaseAgent
from ..models.data_models import ResearchPaper
from ..config.settings import settings


class ClassificationAgent(BaseAgent):
    """Agent responsible for classifying research papers into relevant topics"""
    
    def __init__(self):
        super().__init__("Classification")
        
        # Check if we should use lightweight classification
        if settings.use_extractive_summarization or getattr(settings, 'disable_heavy_models', True):
            print("🚀 Using lightweight classification (keyword-based)")
            self.model_available = False
        else:
            self._initialize_ml_classification()
        
        # Define research topics and their keywords (always available)
        self.topic_definitions = {
                'Artificial Intelligence': [
                    'artificial intelligence', 'AI', 'machine intelligence', 'cognitive computing',
                    'intelligent systems', 'AI algorithms', 'artificial neural networks'
                ],
                'Machine Learning': [
                    'machine learning', 'ML', 'deep learning', 'neural networks', 'supervised learning',
                    'unsupervised learning', 'reinforcement learning', 'gradient descent', 'backpropagation',
                    'random forest', 'support vector machine', 'clustering', 'classification algorithms'
                ],
                'Natural Language Processing': [
                    'natural language processing', 'NLP', 'text mining', 'language models',
                    'text classification', 'sentiment analysis', 'named entity recognition',
                    'machine translation', 'text generation', 'language understanding'
                ],
                'Computer Vision': [
                    'computer vision', 'image processing', 'image recognition', 'object detection',
                    'image classification', 'convolutional neural networks', 'CNN', 'visual recognition',
                    'image segmentation', 'face recognition'
                ],
                'Data Science': [
                    'data science', 'data analysis', 'data mining', 'big data', 'analytics',
                    'statistical analysis', 'data visualization', 'predictive modeling',
                    'business intelligence', 'data engineering'
                ],
                'Robotics': [
                    'robotics', 'autonomous systems', 'robot control', 'robot navigation',
                    'robotic systems', 'automation', 'mechatronics', 'robot learning'
                ],
                'Cybersecurity': [
                    'cybersecurity', 'information security', 'network security', 'encryption',
                    'malware detection', 'intrusion detection', 'security protocols', 'cyber threats'
                ],
                'Blockchain': [
                    'blockchain', 'cryptocurrency', 'distributed ledger', 'smart contracts',
                    'bitcoin', 'ethereum', 'decentralized systems', 'consensus algorithms'
                ],
                'Quantum Computing': [
                    'quantum computing', 'quantum algorithms', 'quantum mechanics', 'qubits',
                    'quantum entanglement', 'quantum cryptography', 'quantum simulation'
                ],
                'Software Engineering': [
                    'software engineering', 'software development', 'programming', 'software architecture',
                    'code quality', 'software testing', 'agile development', 'DevOps'
                ],
                'Human-Computer Interaction': [
                    'human-computer interaction', 'HCI', 'user interface', 'user experience',
                    'usability', 'interface design', 'interaction design', 'UX research'
                ],
                'Bioinformatics': [
                    'bioinformatics', 'computational biology', 'genomics', 'proteomics',
                    'biological data analysis', 'sequence analysis', 'molecular biology'
                ]
            }
    
    def _initialize_ml_classification(self):
        """Initialize ML-based classification (optional, heavy) - DISABLED for performance"""
        print("⚠️ Heavy ML classification disabled for performance. Using keyword-based classification.")
        self.model_available = False
        self.embeddings_model = None
    
    def _initialize_topic_embeddings(self):
        """Pre-compute embeddings for all topic definitions"""
        if not self.model_available:
            return
            
        self.topic_embeddings = {}
        
        for topic, keywords in self.topic_definitions.items():
            # Create a comprehensive description for each topic
            topic_description = f"{topic}: " + ", ".join(keywords)
            embedding = self.embeddings_model.encode([topic_description])[0]
            self.topic_embeddings[topic] = embedding
    
    async def process(self, paper: ResearchPaper) -> List[str]:
        """
        Classify paper into topics using semantic similarity and keyword matching.
        
        Args:
            paper: ResearchPaper object to classify
            
        Returns:
            List of topic strings
        """
        if not self.model_available:
            return self._fallback_classification(paper)
        
        try:
            # Combine title, abstract, and beginning of content for classification
            text_for_classification = f"{paper.title} {paper.abstract}"
            if paper.content and len(paper.content) > len(paper.abstract):
                # Add first 1000 characters of content if available
                content_preview = paper.content[:1000]
                text_for_classification += f" {content_preview}"
            
            # Get text embedding
            text_embedding = self.embeddings_model.encode([text_for_classification])[0]
            
            # Calculate similarity with each topic
            topic_scores = {}
            for topic, topic_embedding in self.topic_embeddings.items():
                similarity = self.cosine_similarity(
                    [text_embedding], [topic_embedding]
                )[0][0]
                topic_scores[topic] = similarity
            
            # Keyword-based scoring (boost for exact matches)
            keyword_scores = self._calculate_keyword_scores(text_for_classification.lower())
            
            # Combine semantic and keyword scores
            final_scores = {}
            for topic in self.topic_definitions.keys():
                semantic_score = topic_scores.get(topic, 0)
                keyword_score = keyword_scores.get(topic, 0)
                # Weight semantic similarity more heavily, but boost for keyword matches
                final_scores[topic] = (semantic_score * 0.7) + (keyword_score * 0.3)
            
            # Select top topics (threshold-based selection)
            selected_topics = []
            sorted_topics = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Always include the top topic if it has reasonable confidence
            if sorted_topics[0][1] > 0.3:
                selected_topics.append(sorted_topics[0][0])
            
            # Add additional topics if they have good scores
            for topic, score in sorted_topics[1:]:
                if score > 0.5:  # High confidence threshold for additional topics
                    selected_topics.append(topic)
                elif score > 0.4 and len(selected_topics) < 3:  # Medium confidence, limit to 3 total
                    selected_topics.append(topic)
            
            # Fallback to ensure we always return at least one topic
            if not selected_topics:
                selected_topics = [sorted_topics[0][0]]
            
            # Limit to maximum 4 topics
            selected_topics = selected_topics[:4]
            
            print(f"📊 Classified '{paper.title[:50]}...' into topics: {selected_topics}")
            return selected_topics
            
        except Exception as e:
            print(f"❌ Error in classification: {e}")
            return self._fallback_classification(paper)
    
    def _calculate_keyword_scores(self, text: str) -> Dict[str, float]:
        """Calculate keyword-based scores for topics"""
        keyword_scores = {}
        
        for topic, keywords in self.topic_definitions.items():
            score = 0
            for keyword in keywords:
                # Count occurrences (case-insensitive)
                count = text.count(keyword.lower())
                if count > 0:
                    # Score based on keyword importance and frequency
                    keyword_weight = 1.0
                    if len(keyword.split()) > 1:  # Multi-word keywords get higher weight
                        keyword_weight = 1.5
                    score += count * keyword_weight
            
            # Normalize by number of keywords in the topic
            if keywords:
                keyword_scores[topic] = score / len(keywords)
        
        return keyword_scores
    
    def _fallback_classification(self, paper: ResearchPaper) -> List[str]:
        """Simple fallback classification using keyword matching only"""
        text = f"{paper.title} {paper.abstract}".lower()
        
        # Simple keyword-based classification
        topic_matches = {}
        for topic, keywords in self.topic_definitions.items():
            matches = sum(1 for keyword in keywords if keyword.lower() in text)
            if matches > 0:
                topic_matches[topic] = matches
        
        if topic_matches:
            # Return top 2 matching topics
            sorted_matches = sorted(topic_matches.items(), key=lambda x: x[1], reverse=True)
            return [topic for topic, _ in sorted_matches[:2]]
        else:
            # Ultimate fallback
            return ['Computer Science', 'Research']
