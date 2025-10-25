"""
Audio Handler Module - Microphone recording and audio capture
"""
import pyaudio
import wave
import base64
import threading
import io
from typing import Optional, List, Dict
from datetime import datetime
import time


class AudioHandler:
    """Handles audio recording operations for remote access"""

    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.is_recording: bool = False
        self.recording_thread: Optional[threading.Thread] = None
        self.frames: List[bytes] = []
        self.sample_rate: int = 44100
        self.channels: int = 2
        self.chunk_size: int = 1024
        self.format = pyaudio.paInt16
        self.stream: Optional[pyaudio.Stream] = None
        self.recording_start_time: Optional[float] = None
        self.max_duration: int = 30  # Default max duration in seconds
        self._lock = threading.Lock()

    def list_microphones(self) -> List[Dict[str, any]]:
        """
        List all available audio input devices

        Returns:
            List of microphone info dictionaries
        """
        microphones = []

        # Get device count
        device_count = self.audio.get_device_count()

        for index in range(device_count):
            try:
                device_info = self.audio.get_device_info_by_index(index)

                # Only include input devices
                if device_info.get('maxInputChannels', 0) > 0:
                    microphones.append({
                        "index": index,
                        "name": device_info.get('name', f'Device {index}'),
                        "channels": int(device_info.get('maxInputChannels', 0)),
                        "sample_rate": int(device_info.get('defaultSampleRate', 44100)),
                        "available": True
                    })
            except Exception as e:
                # Skip devices that can't be accessed
                continue

        return microphones

    def start_recording(self, duration: int = 30, device_index: Optional[int] = None,
                       sample_rate: int = 44100, channels: int = 2) -> Dict[str, any]:
        """
        Start audio recording

        Args:
            duration: Maximum recording duration in seconds (default: 30)
            device_index: Microphone device index (None for default)
            sample_rate: Sample rate in Hz (default: 44100)
            channels: Number of channels (default: 2 for stereo)

        Returns:
            Status dictionary
        """
        with self._lock:
            if self.is_recording:
                return {
                    "success": False,
                    "error": "Recording already in progress"
                }

            # Reset recording data
            self.frames = []
            self.sample_rate = sample_rate
            self.channels = channels
            self.max_duration = duration
            self.recording_start_time = time.time()

            try:
                # Open audio stream
                self.stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=self.chunk_size
                )

                self.is_recording = True

                # Start recording in background thread
                self.recording_thread = threading.Thread(target=self._record_audio)
                self.recording_thread.daemon = True
                self.recording_thread.start()

                return {
                    "success": True,
                    "message": f"Recording started (max duration: {duration}s)",
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "device_index": device_index,
                    "max_duration": duration
                }

            except Exception as e:
                self.is_recording = False
                self.stream = None
                return {
                    "success": False,
                    "error": f"Failed to start recording: {str(e)}"
                }

    def _record_audio(self):
        """Internal method to record audio in background thread"""
        try:
            while self.is_recording:
                # Check if max duration reached
                if time.time() - self.recording_start_time >= self.max_duration:
                    break

                # Read audio data
                try:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    self.frames.append(data)
                except Exception as e:
                    print(f"Error reading audio: {e}")
                    break

        finally:
            # Auto-stop when done
            with self._lock:
                if self.stream is not None:
                    self.stream.stop_stream()
                    self.stream.close()
                    self.stream = None
                self.is_recording = False

    def stop_recording(self) -> Dict[str, any]:
        """
        Stop recording and return audio data

        Returns:
            Dictionary with base64 encoded WAV file and metadata
        """
        with self._lock:
            if not self.is_recording and len(self.frames) == 0:
                return {
                    "success": False,
                    "error": "No recording in progress or no data recorded"
                }

            # Stop recording
            self.is_recording = False

        # Wait for recording thread to finish
        if self.recording_thread is not None:
            self.recording_thread.join(timeout=2.0)
            self.recording_thread = None

        with self._lock:
            # Close stream if still open
            if self.stream is not None:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
                self.stream = None

            if len(self.frames) == 0:
                return {
                    "success": False,
                    "error": "No audio data captured"
                }

            try:
                # Create WAV file in memory
                wav_buffer = io.BytesIO()

                with wave.open(wav_buffer, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.format))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(self.frames))

                # Get WAV data
                wav_bytes = wav_buffer.getvalue()
                wav_base64 = base64.b64encode(wav_bytes).decode('utf-8')

                # Calculate duration
                duration = len(self.frames) * self.chunk_size / self.sample_rate

                # Clear frames
                frames_count = len(self.frames)
                self.frames = []

                return {
                    "success": True,
                    "audio": wav_base64,
                    "format": "wav",
                    "sample_rate": self.sample_rate,
                    "channels": self.channels,
                    "duration": round(duration, 2),
                    "size": len(wav_bytes),
                    "frames": frames_count,
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to encode audio: {str(e)}"
                }

    def is_recording_active(self) -> bool:
        """Check if recording is currently active"""
        return self.is_recording

    def __del__(self):
        """Cleanup on deletion"""
        if self.is_recording:
            self.is_recording = False

        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass

        if hasattr(self, 'audio') and self.audio is not None:
            try:
                self.audio.terminate()
            except:
                pass


# Global audio handler instance
_audio_handler = None


def get_audio_handler() -> AudioHandler:
    """Get or create global audio handler instance"""
    global _audio_handler
    if _audio_handler is None:
        _audio_handler = AudioHandler()
    return _audio_handler


def list_microphones() -> List[Dict[str, any]]:
    """List available microphones"""
    handler = get_audio_handler()
    return handler.list_microphones()


def start_recording(duration: int = 30, device_index: Optional[int] = None,
                   sample_rate: int = 44100, channels: int = 2) -> Dict[str, any]:
    """Start microphone recording"""
    handler = get_audio_handler()
    return handler.start_recording(duration, device_index, sample_rate, channels)


def stop_recording() -> Dict[str, any]:
    """Stop recording and get audio data"""
    handler = get_audio_handler()
    return handler.stop_recording()
