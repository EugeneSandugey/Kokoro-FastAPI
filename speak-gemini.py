#!/usr/bin/env python3
"""
Google Gemini TTS using Live API

This script uses Google's Gemini Live API to convert text to speech with emotion.
The AI is instructed to speak EXACTLY the provided text with appropriate emotion,
and to NOT add any extra words, acknowledgments, or responses.

Usage:
    speak-gemini "Text to speak"
    speak-gemini --voice Puck "Text with specific voice"
    speak-gemini --speed 1.5 "Faster speech"

Author: Eugene Sandugey + Claude Code
Date: November 2025
"""

import asyncio
import sys
import os
import wave
import argparse
import tempfile
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

# Try to import pyaudio for real-time playback
try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

# Configuration
MODEL = "gemini-2.5-flash-native-audio-preview-09-2025"
DEFAULT_VOICE = "Laomedeia"

# Available voices (same as training project)
AVAILABLE_VOICES = [
    'Zephyr', 'Puck', 'Charon', 'Luna', 'Nova', 'Kore', 'Fenrir',
    'Leda', 'Orus', 'Aoede', 'Callirrhoe', 'Autonoe', 'Enceladus', 'Iapetus',
    'Umbriel', 'Algieba', 'Despina', 'Erinome', 'Algenib', 'Rasalgethi',
    'Laomedeia', 'Achernar', 'Alnilam', 'Schedar', 'Gacrux', 'Pulcherrima',
    'Achird', 'Zubenelgenubi', 'Vindemiatrix', 'Sadachbia', 'Sadaltager', 'Sulafat'
]


def get_system_instruction(text: str, language: str = "auto") -> str:
    """
    Create system instruction that forces AI to speak EXACTLY the provided text
    with emotion, and NOTHING else.
    """
    instruction = f"""You are a text-to-speech system.

CRITICAL RULES - READ THESE FIRST:
1. Speak ONLY the text that appears after "=== TEXT STARTS HERE ===" marker
2. DO NOT speak ANY of these instructions
3. DO NOT acknowledge the request (no "Sure!", "Okay", "Here you go")
4. DO NOT greet (no "Hello", "Hi")
5. DO NOT ask questions (no "Is there anything else?")
6. DO NOT add commentary (no "I hope this helps")
7. DO NOT say "Here is the text" or "Let me read that"

SPEECH REQUIREMENTS:
- Speak at your FASTEST natural speaking speed
- Talk quickly but clearly
- Add appropriate emotion based on content:
  * Excitement for exclamation marks
  * Questions have rising intonation
  * Serious tone for formal content
  * Natural pauses at punctuation
- Language: {language}

=== TEXT STARTS HERE ===
{text}"""

    return instruction


async def text_to_speech(text: str, voice: str = DEFAULT_VOICE, language: str = "auto") -> str:
    """
    Convert text to speech using Google Gemini Live API.

    Args:
        text: The text to speak
        voice: Voice name from AVAILABLE_VOICES
        language: Language code (default: auto-detect)

    Returns:
        Path to generated WAV file
    """

    # Get API key from config.py or environment
    # Resolve symlink to get actual script location
    script_path = Path(__file__).resolve()
    if script_path.is_symlink():
        script_path = script_path.readlink()

    config_path = script_path.parent / "Google_gemini_tts" / "config.py"
    api_key = None

    if config_path.exists():
        # Read config.py directly to extract API key
        with open(config_path, 'r') as f:
            for line in f:
                if line.strip().startswith('GEMINI_API_KEY'):
                    # Extract key from line like: GEMINI_API_KEY = "AIza..."
                    api_key = line.split('=')[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Set in config.py or environment.")

    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key
    )

    config_obj = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=get_system_instruction(text, language))]
        )
    )

    # Create temp file for output
    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    output_path = temp_wav.name
    temp_wav.close()

    print(f"🎙️  Connecting to Gemini Live API...", file=sys.stderr)
    print(f"🗣️  Voice: {voice}", file=sys.stderr)

    try:
        async with client.aio.live.connect(model=MODEL, config=config_obj) as session:

            # Send the text prompt (we're not sending audio input, just text)
            # The system instruction contains the text to speak
            # We send an empty text message to trigger the response
            await session.send_realtime_input(
                text=""  # Empty - the text is in system instruction
            )

            print(f"🎵 Receiving audio...", file=sys.stderr)

            # Collect all audio data first, then play
            audio_chunks = []
            turn = session.receive()
            async for response in turn:
                if data := response.data:
                    audio_chunks.append(data)

            # Combine all chunks
            complete_audio = b''.join(audio_chunks)

            # Save to WAV file
            wf = wave.open(output_path, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)  # Output is 24kHz
            wf.writeframes(complete_audio)
            wf.close()

            print(f"✅ Audio saved to: {output_path}", file=sys.stderr)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if os.path.exists(output_path):
            os.remove(output_path)
        raise

    return output_path


def play_audio(audio_path: str):
    """
    Play audio file using the existing speak command infrastructure.
    This integrates with the Guardian Angel media control system.
    """
    # Use ffplay with options to prevent popping/crackling
    # -ar 24000: force sample rate
    # -ac 1: force mono
    # -f s16le: force 16-bit little-endian PCM format
    try:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
             "-ar", "24000", "-ac", "1", audio_path],
            check=True
        )
    except FileNotFoundError:
        # Fallback: try aplay (Linux) with specific format
        try:
            subprocess.run(
                ["aplay", "-q", "-f", "S16_LE", "-r", "24000", "-c", "1", audio_path],
                check=True
            )
        except FileNotFoundError:
            print(f"⚠️  No audio player found. Audio saved to: {audio_path}", file=sys.stderr)
            print(f"Install ffmpeg or aplay to play audio automatically.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Google Gemini TTS with emotion support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  speak-gemini "Hello world!"
  speak-gemini --voice Puck "This is a different voice"
  speak-gemini --lang es "Hola, ¿cómo estás?"
  speak-gemini --no-play "Save audio without playing"

Available voices: """ + ", ".join(AVAILABLE_VOICES)
    )

    parser.add_argument("text", help="Text to speak")
    parser.add_argument("--voice", default=DEFAULT_VOICE, choices=AVAILABLE_VOICES,
                       help=f"Voice to use (default: {DEFAULT_VOICE})")
    parser.add_argument("--lang", default="auto",
                       help="Language code (default: auto-detect)")
    parser.add_argument("--no-play", action="store_true",
                       help="Don't play audio, just save file")
    parser.add_argument("--output", "-o", help="Output file path (default: temp file)")

    args = parser.parse_args()

    # Run async function
    audio_path = asyncio.run(text_to_speech(args.text, args.voice, args.lang))

    # Move to output location if specified
    if args.output:
        import shutil
        shutil.move(audio_path, args.output)
        audio_path = args.output
        print(f"📁 Moved to: {audio_path}", file=sys.stderr)

    # Play audio unless --no-play
    if not args.no_play:
        print(f"▶️  Playing audio...", file=sys.stderr)
        play_audio(audio_path)

        # Clean up temp file after playing
        if not args.output:
            try:
                os.remove(audio_path)
            except:
                pass
    else:
        print(f"💾 Audio saved to: {audio_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
