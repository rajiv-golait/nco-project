#!/usr/bin/env python3
"""
voice_handler.py

Handles voice input processing for multilingual speech-to-text.
Supports Hindi, Bengali, Marathi, and English.
"""

import io
import json
import base64
from typing import Optional, Dict, Any
from pathlib import Path
import logging

# Speech recognition libraries (optional dependencies)
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel


class VoiceInputRequest(BaseModel):
    """Request model for voice input."""
    audio_data: str  # Base64 encoded audio
    format: str = "webm"  # Audio format (webm, wav, mp3)
    language: Optional[str] = None  # Expected language (hi, bn, mr, en)


class VoiceInputResponse(BaseModel):
    """Response model for voice transcription."""
    text: str
    language: str
    confidence: float
    alternatives: Optional[list] = None


class VoiceHandler:
    """
    Handles voice input processing and speech-to-text conversion.
    """
    
    def __init__(self, use_whisper: bool = False, model_size: str = "base"):
        """
        Initialize voice handler.
        
        Args:
            use_whisper: Whether to use OpenAI Whisper model
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.use_whisper = use_whisper and WHISPER_AVAILABLE
        
        if self.use_whisper:
            try:
                self.whisper_model = whisper.load_model(model_size)
                logging.info(f"Loaded Whisper model: {model_size}")
            except Exception as e:
                logging.error(f"Failed to load Whisper model: {e}")
                self.use_whisper = False
        
        # Initialize speech recognition
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            # Adjust for ambient noise
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
        else:
            self.recognizer = None
    
    def decode_audio(self, audio_data: str, format: str = "webm") -> bytes:
        """
        Decode base64 audio data.
        
        Args:
            audio_data: Base64 encoded audio
            format: Audio format
        
        Returns:
            Raw audio bytes
        """
        try:
            # Remove data URL prefix if present
            if "," in audio_data:
                audio_data = audio_data.split(",")[1]
            
            return base64.b64decode(audio_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid audio data: {e}")
    
    def transcribe_with_whisper(self, audio_bytes: bytes, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper model.
        
        Args:
            audio_bytes: Raw audio bytes
            language: Expected language code
        
        Returns:
            Transcription result
        """
        if not self.use_whisper:
            raise HTTPException(status_code=501, detail="Whisper not available")
        
        try:
            # Save temporary audio file (Whisper requires file input)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            # Map language codes
            lang_map = {
                "hi": "hindi",
                "bn": "bengali",
                "mr": "marathi",
                "en": "english"
            }
            
            whisper_lang = lang_map.get(language, None)
            
            # Transcribe
            result = self.whisper_model.transcribe(
                tmp_path,
                language=whisper_lang,
                task="transcribe"
            )
            
            # Clean up
            Path(tmp_path).unlink()
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", language or "en"),
                "confidence": 0.95  # Whisper doesn't provide confidence scores
            }
            
        except Exception as e:
            logging.error(f"Whisper transcription failed: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    
    def transcribe_with_google(self, audio_bytes: bytes, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio using Google Speech Recognition.
        
        Args:
            audio_bytes: Raw audio bytes
            language: Expected language code
        
        Returns:
            Transcription result
        """
        if not self.recognizer:
            raise HTTPException(status_code=501, detail="Speech recognition not available")
        
        try:
            # Convert bytes to AudioData
            audio_data = sr.AudioData(audio_bytes, sample_rate=16000, sample_width=2)
            
            # Map language codes to Google Speech Recognition format
            lang_map = {
                "hi": "hi-IN",
                "bn": "bn-IN",
                "mr": "mr-IN",
                "en": "en-IN"  # Indian English
            }
            
            recognition_lang = lang_map.get(language, "en-IN")
            
            # Recognize speech
            text = self.recognizer.recognize_google(
                audio_data,
                language=recognition_lang,
                show_all=False
            )
            
            return {
                "text": text,
                "language": language or "en",
                "confidence": 0.85  # Default confidence for Google
            }
            
        except sr.UnknownValueError:
            raise HTTPException(status_code=400, detail="Could not understand audio")
        except sr.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Speech recognition service error: {e}")
        except Exception as e:
            logging.error(f"Google transcription failed: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    
    def transcribe(self, audio_data: str, format: str = "webm", language: Optional[str] = None) -> VoiceInputResponse:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Base64 encoded audio
            format: Audio format
            language: Expected language
        
        Returns:
            Transcription response
        """
        # Decode audio
        audio_bytes = self.decode_audio(audio_data, format)
        
        # Try Whisper first if available
        if self.use_whisper:
            result = self.transcribe_with_whisper(audio_bytes, language)
        elif self.recognizer:
            result = self.transcribe_with_google(audio_bytes, language)
        else:
            raise HTTPException(
                status_code=501,
                detail="No speech recognition backend available. Install speech_recognition or whisper."
            )
        
        return VoiceInputResponse(
            text=result["text"],
            language=result["language"],
            confidence=result["confidence"]
        )
    
    async def process_audio_file(self, file: UploadFile, language: Optional[str] = None) -> VoiceInputResponse:
        """
        Process uploaded audio file.
        
        Args:
            file: Uploaded audio file
            language: Expected language
        
        Returns:
            Transcription response
        """
        # Read file content
        content = await file.read()
        
        # Convert to base64 for uniform processing
        audio_b64 = base64.b64encode(content).decode('utf-8')
        
        # Get format from filename
        format = file.filename.split('.')[-1].lower() if file.filename else "wav"
        
        return self.transcribe(audio_b64, format, language)


# Singleton instance
_voice_handler = None


def get_voice_handler() -> VoiceHandler:
    """Get or create voice handler instance."""
    global _voice_handler
    if _voice_handler is None:
        # Use Whisper if available for better accuracy
        _voice_handler = VoiceHandler(use_whisper=WHISPER_AVAILABLE)
    return _voice_handler


if __name__ == "__main__":
    # Test voice handler
    handler = get_voice_handler()
    print(f"Voice Handler initialized")
    print(f"  Whisper available: {WHISPER_AVAILABLE}")
    print(f"  Speech Recognition available: {SPEECH_RECOGNITION_AVAILABLE}")
    
    if not WHISPER_AVAILABLE and not SPEECH_RECOGNITION_AVAILABLE:
        print("\nNote: Install 'openai-whisper' or 'SpeechRecognition' for voice input support")
        print("  pip install openai-whisper")
        print("  pip install SpeechRecognition")
