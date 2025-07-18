"""
Base agent class for the Research Paper Summarization System.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all agents in the system"""
    
    def __init__(self, name: str):
        self.name = name
        self.status = "idle"
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """
        Process input data and return results.
        
        Args:
            input_data: Input data to process (type varies by agent)
            
        Returns:
            Processed results (type varies by agent)
        """
        pass
    
    def get_status(self) -> str:
        """Get current agent status"""
        return self.status
    
    def set_status(self, status: str):
        """Set agent status"""
        self.status = status
