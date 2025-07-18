"""
Synthesis Agent for combining insights across multiple papers.
"""

from typing import Dict, List
from collections import Counter

from .base_agent import BaseAgent


class SynthesisAgent(BaseAgent):
    """Agent responsible for synthesizing findings across multiple research papers"""
    
    def __init__(self):
        super().__init__("Synthesis")
    
    async def process(self, classified_papers: Dict) -> Dict:
        """
        Synthesize findings across papers with improved analysis.
        
        Args:
            classified_papers: Dictionary containing papers, classifications, and summaries
            
        Returns:
            Dictionary containing synthesis results
        """
        papers = classified_papers.get('papers', [])
        classifications = classified_papers.get('classifications', [])
        summaries = classified_papers.get('summaries', [])
        
        if not papers:
            return {
                'synthesis': 'No papers available for synthesis.',
                'topic_analysis': {},
                'paper_count': 0
            }
        
        # Analyze topics across papers
        topic_analysis = self._analyze_topics(papers, classifications)
        
        # Generate comprehensive synthesis
        synthesis_text = self._generate_synthesis(papers, summaries, topic_analysis)
        
        return {
            'synthesis': synthesis_text,
            'topic_analysis': topic_analysis,
            'paper_count': len(papers),
            'methodology': 'enhanced_synthesis'
        }
    
    def _analyze_topics(self, papers: List, classifications: List) -> Dict:
        """Analyze topic distribution and relationships"""
        # Count topic frequencies
        all_topics = []
        for classification in classifications:
            if isinstance(classification, list):
                all_topics.extend(classification)
        
        topic_counts = Counter(all_topics)
        
        # Calculate topic co-occurrence
        topic_cooccurrence = {}
        for classification in classifications:
            if isinstance(classification, list) and len(classification) > 1:
                for i, topic1 in enumerate(classification):
                    for topic2 in classification[i+1:]:
                        pair_key = f"{topic1}_{topic2}"
                        topic_cooccurrence[pair_key] = topic_cooccurrence.get(pair_key, 0) + 1
        
        return {
            'topic_distribution': dict(topic_counts),
            'total_unique_topics': len(topic_counts),
            'most_common_topics': list(topic_counts.most_common(5)),
            'topic_cooccurrence': topic_cooccurrence
        }
    
    def _generate_synthesis(self, papers: List, summaries: List, topic_analysis: Dict) -> str:
        """Generate a comprehensive synthesis of research findings"""
        
        paper_count = len(papers)
        topic_count = topic_analysis.get('total_unique_topics', 0)
        most_common_topics = topic_analysis.get('most_common_topics', [])
        
        # Start with overview
        synthesis_parts = []
        
        # Overview section
        overview = f"This synthesis analyzes {paper_count} research papers covering {topic_count} distinct research areas. "
        
        if most_common_topics:
            top_topics = [topic for topic, count in most_common_topics[:3]]
            overview += f"The most prevalent research areas include {', '.join(top_topics[:-1])}"
            if len(top_topics) > 1:
                overview += f" and {top_topics[-1]}. "
            else:
                overview += ". "
        
        synthesis_parts.append(overview)
        
        # Key findings section
        if summaries:
            findings_section = "Key findings across the analyzed papers reveal several important insights: "
            
            # Extract common findings patterns
            findings = []
            for summary in summaries:
                if isinstance(summary, dict):
                    insights = summary.get('key_insights', [])
                    findings.extend(insights[:2])  # Take top 2 insights per paper
            
            if findings:
                # Take top unique findings
                unique_findings = []
                for finding in findings[:5]:
                    # Simple deduplication
                    if not any(finding.lower() in existing.lower() for existing in unique_findings):
                        unique_findings.append(finding)
                
                findings_section += " ".join([f"({i+1}) {finding.capitalize()}." 
                                            for i, finding in enumerate(unique_findings[:3])])
            else:
                findings_section += "The papers collectively advance our understanding in their respective domains."
            
            synthesis_parts.append(findings_section)
        
        # Conclusion
        conclusion = "The collective findings underscore the rapid advancement in these research areas and point toward significant potential for real-world applications and continued innovation."
        synthesis_parts.append(conclusion)
        
        return " ".join(synthesis_parts)
