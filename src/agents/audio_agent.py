"""
Audio Agent for generating audio summaries.
"""

import uuid
from typing import Dict, List

from .base_agent import BaseAgent
from ..config.settings import settings


class AudioAgent(BaseAgent):
    """Agent responsible for generating audio files from text synthesis"""
    
    def __init__(self):
        super().__init__("Audio")
        self.tts_available = self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize text-to-speech engine with fallback options"""
        try:
            # Try gTTS first (Google Text-to-Speech - free)
            from gtts import gTTS
            self.gtts = gTTS
            self.tts_method = "gtts"
            print("✅ gTTS (Google Text-to-Speech) initialized successfully!")
            return True
        except ImportError:
            try:
                # Try pyttsx3 as fallback
                import pyttsx3
                self.pyttsx3 = pyttsx3
                self.tts_method = "pyttsx3"
                print("✅ pyttsx3 initialized successfully!")
                return True
            except ImportError:
                print("⚠️ No TTS library available. Audio generation disabled.")
                return False
    
    async def process(self, synthesis: Dict) -> List[str]:
        """
        Generate audio files from synthesis.
        
        Args:
            synthesis: Dictionary containing synthesis text
            
        Returns:
            List of generated audio file paths
        """
        audio_files = []
        
        if not self.tts_available:
            # Create placeholder file if no TTS available
            filename = f"audio/synthesis_{uuid.uuid4()}.txt"
            with open(filename, "w") as f:
                f.write("Audio generation not available - TTS library not installed")
            return [filename]
        
        try:
            synthesis_text = synthesis.get('synthesis', '')
            if synthesis_text:
                filename = f"audio/synthesis_{uuid.uuid4()}.mp3"
                
                if self.tts_method == "gtts":
                    audio_files = await self._generate_gtts_audio(synthesis_text, filename)
                elif self.tts_method == "pyttsx3":
                    audio_files = await self._generate_pyttsx3_audio(synthesis_text, filename)
            
        except Exception as e:
            print(f"❌ Error generating audio: {e}")
            # Create error placeholder
            filename = f"audio/synthesis_{uuid.uuid4()}.txt"
            with open(filename, "w") as f:
                f.write(f"Audio generation failed: {e}")
            audio_files = [filename]
        
        return audio_files
    
    async def _generate_gtts_audio(self, text: str, filename: str) -> List[str]:
        """Generate audio using Google Text-to-Speech (gTTS)"""
        try:
            # Check text length and split if necessary
            if len(text) > 5000:  # gTTS has limits
                return await self._generate_chunked_gtts_audio(text, filename)
            
            tts = self.gtts(text=text, lang='en', slow=False)
            tts.save(filename)
            print(f"🔊 Generated audio file: {filename}")
            return [filename]
            
        except Exception as e:
            print(f"❌ Error with gTTS: {e}")
            return []
    
    async def _generate_chunked_gtts_audio(self, text: str, base_filename: str) -> List[str]:
        """Generate audio in chunks for long text using gTTS"""
        try:
            # Split text into chunks
            words = text.split()
            chunk_size = 100  # words per chunk
            chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            
            audio_files = []
            for i, chunk in enumerate(chunks):
                chunk_filename = base_filename.replace('.mp3', f'_part{i+1}.mp3')
                tts = self.gtts(text=chunk, lang='en', slow=False)
                tts.save(chunk_filename)
                audio_files.append(chunk_filename)
            
            print(f"🔊 Generated {len(audio_files)} audio chunks")
            return audio_files
            
        except Exception as e:
            print(f"❌ Error with chunked gTTS: {e}")
            return []
    
    async def _generate_pyttsx3_audio(self, text: str, filename: str) -> List[str]:
        """Generate audio using pyttsx3 (offline TTS)"""
        try:
            engine = self.pyttsx3.init()
            engine.save_to_file(text, filename)
            engine.runAndWait()
            print(f"🔊 Generated audio file: {filename}")
            return [filename]
            
        except Exception as e:
            print(f"❌ Error with pyttsx3: {e}")
            return []
