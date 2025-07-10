#!/usr/bin/env python3
"""
Chatterbox TTS Server - OpenAI-compatible API
Provides the same endpoints as Kokoro for easy drop-in replacement
"""

from flask import Flask, request, jsonify, Response
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import io
import base64
import tempfile
import os
import logging
import soundfile as sf
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global model instance
model = None

def load_model():
    """Load Chatterbox model on startup"""
    global model
    logger.info("Loading Chatterbox TTS model on CUDA...")
    try:
        model = ChatterboxTTS.from_pretrained(device="cuda")
        logger.info("✅ Model loaded successfully on CUDA!")
        logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        # Try CPU fallback
        logger.info("Falling back to CPU...")
        model = ChatterboxTTS.from_pretrained(device="cpu")
        logger.info("✅ Model loaded successfully on CPU")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "model": "chatterbox",
        "cuda_available": torch.cuda.is_available(),
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    })

@app.route('/v1/audio/speech', methods=['POST'])
def generate_speech():
    """OpenAI-compatible TTS endpoint"""
    try:
        data = request.json
        
        # Extract parameters
        text = data.get('input', '')
        voice = data.get('voice', 'default')  # Can be 'default' or path to WAV file
        response_format = data.get('response_format', 'mp3')
        speed = data.get('speed', 1.0)
        
        # Emotion/exaggeration control (unique to Chatterbox)
        exaggeration = data.get('exaggeration', 0.5)  # Default from Chatterbox docs
        cfg_weight = data.get('cfg_weight', 0.5)  # Default from Chatterbox docs
        
        if not text:
            return jsonify({"error": "No input text provided"}), 400
        
        # Check if voice is a path to a WAV file for cloning
        audio_prompt_path = None
        logger.info(f"Voice parameter received: {voice}")
        if voice != 'default' and voice.endswith('.wav'):
            if os.path.exists(voice):
                audio_prompt_path = voice
                logger.info(f"✅ Using voice clone from: {voice}")
            else:
                logger.warning(f"❌ Voice file not found: {voice}, using default")
                logger.info(f"Current directory: {os.getcwd()}")
                logger.info(f"Files in /voice-samples: {os.listdir('/voice-samples') if os.path.exists('/voice-samples') else 'Directory not found'}")
        
        logger.info(f"Generating speech for: {text[:100]}...")
        
        # Generate audio
        if audio_prompt_path:
            wav = model.generate(
                text, 
                audio_prompt_path=audio_prompt_path,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight
            )
        else:
            wav = model.generate(
                text, 
                exaggeration=exaggeration,
                cfg_weight=cfg_weight
            )
        
        # Convert to numpy array
        audio_np = wav.cpu().numpy()
        
        # Handle speed adjustment if needed
        if speed != 1.0:
            # Simple speed adjustment by resampling
            new_length = int(len(audio_np[0]) / speed)
            indices = np.linspace(0, len(audio_np[0])-1, new_length).astype(int)
            audio_np = audio_np[:, indices]
        
        # Convert to desired format
        if response_format == 'mp3':
            # Save to temporary file and convert
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                ta.save(tmp_wav.name, torch.from_numpy(audio_np), model.sr)
                
                # Convert to MP3 using ffmpeg
                mp3_path = tmp_wav.name.replace('.wav', '.mp3')
                os.system(f"ffmpeg -i {tmp_wav.name} -acodec libmp3lame -b:a 192k {mp3_path} -y -loglevel error")
                
                # Read MP3 data
                with open(mp3_path, 'rb') as f:
                    mp3_data = f.read()
                
                # Cleanup
                os.remove(tmp_wav.name)
                os.remove(mp3_path)
                
                return Response(mp3_data, mimetype='audio/mpeg')
        
        elif response_format == 'wav':
            # Return WAV directly
            buffer = io.BytesIO()
            sf.write(buffer, audio_np.T, model.sr, format='WAV')
            buffer.seek(0)
            return Response(buffer.read(), mimetype='audio/wav')
        
        elif response_format == 'opus':
            # Convert to Opus
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                ta.save(tmp_wav.name, torch.from_numpy(audio_np), model.sr)
                
                opus_path = tmp_wav.name.replace('.wav', '.opus')
                os.system(f"ffmpeg -i {tmp_wav.name} -c:a libopus -b:a 128k {opus_path} -y -loglevel error")
                
                with open(opus_path, 'rb') as f:
                    opus_data = f.read()
                
                os.remove(tmp_wav.name)
                os.remove(opus_path)
                
                return Response(opus_data, mimetype='audio/opus')
        
        else:
            return jsonify({"error": f"Unsupported format: {response_format}"}), 400
            
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models"""
    return jsonify({
        "data": [
            {
                "id": "chatterbox",
                "object": "model",
                "created": 1736096400,
                "owned_by": "resemble-ai"
            }
        ]
    })

@app.route('/v1/voices', methods=['GET'])
def list_voices():
    """List available voices"""
    # Chatterbox uses default voices or audio prompts, not named voices
    return jsonify({
        "voices": [
            {
                "voice_id": "default",
                "name": "Default",
                "description": "Chatterbox default voice with emotion control"
            }
        ]
    })

if __name__ == '__main__':
    # Load model on startup
    load_model()
    
    # Run server
    logger.info("Starting Chatterbox TTS server on port 8881...")
    app.run(host='0.0.0.0', port=8881, debug=False)