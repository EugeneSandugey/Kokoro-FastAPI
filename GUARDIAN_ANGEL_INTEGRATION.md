# Guardian Angel TTS Integration Guide

## Overview

Guardian Angel is the central voice interface system that manages TTS playback across all Claude Code agents. It provides:

- Unified voice output through web interface at https://eugene.tail1d96a2.ts.net/
- Smart media control (pause/resume) for Windows applications
- Queue management for multiple simultaneous TTS requests
- Support for both Kokoro and Chatterbox TTS engines

## Architecture

```
Claude Code Agent → speak command → Guardian Angel wrapper → TTS Engine → Web Interface
                                         ↓
                                  Media Control (if needed)
```

## For Claude Code Agents

### Basic Usage

```bash
# Simple message (uses Kokoro with af_heart voice at 1.25x)
/usr/local/bin/speak "Task completed successfully"

# Or using the speak command directly
speak "Processing file analysis"

# Include project name for clarity
speak "Kokoro: Documentation updated successfully"
```

### Using Custom Commands

The `/user:speak` slash command is for human users only. Agents should use the bash command directly:

```bash
# CORRECT - For agents
speak "Your message here"

# INCORRECT - This is for humans only
/user:speak "Your message"
```

### Terminal Status Integration

Always update terminal status when working:

```bash
# When starting a task
claude-working "Analyzing codebase"

# When completing a task (includes audio notification)
claude-done "Analysis complete"

# These commands also update the Guardian Angel multi-agent panel
```

## How Guardian Angel Works

### 1. Audio Generation Flow

1. **Agent calls speak**: `speak "Hello world"`
2. **Wrapper script determines TTS engine**: Kokoro (default) or Chatterbox
3. **TTS generates MP3**: Saved to `/home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/`
4. **Guardian Angel detects new file**: Monitors directory for new audio
5. **Web interface plays audio**: Through browser at https://eugene.tail1d96a2.ts.net/

### 2. Smart Media Control

The system intelligently handles Windows media playback:

```bash
# What happens when you speak:
1. Detect if media is playing (Spotify, YouTube, etc.)
2. If playing → Pause media
3. Play TTS audio
4. If media was paused → Resume after TTS completes
5. If no media was playing → Do nothing after TTS
```

### 3. Queue Management

Multiple agents can speak simultaneously:

```bash
# Agent 1
speak "Starting database migration"

# Agent 2 (at same time)
speak "Frontend build complete"

# Result: Both generate audio in parallel, playback is sequential (FIFO)
```

## File Locations

### Audio Files
```bash
# TTS output directory (auto-cleaned after playback)
/home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/

# File naming pattern
wsl_speak_YYYYMMDD_HHMMSS_mmm.mp3

# Control markers
*.skip_media_control  # Prevents double pause/resume
*.paused_media       # Tracks if we paused media
```

### Scripts
```bash
# Main wrapper (symlinked to /usr/local/bin/speak)
/home/echo/.local/bin/kokoro-speak

# Universal TTS handler
/home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_smart_pause_universal.py

# Media control scripts
/home/echo/bin/windows-media-control.ps1
/home/echo/bin/windows-detect-media.ps1
```

## Advanced Usage

### Using Chatterbox (Voice Cloning)

```bash
# If Chatterbox is deployed, you can use voice cloning
python3 /home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_smart_pause_universal.py \
  --model chatterbox \
  --voice-file /path/to/voice.wav \
  "This is a cloned voice speaking"
```

### Custom Voice and Speed

```bash
# While the wrapper doesn't directly support parameters,
# you can call the Python script directly:
python3 /home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_smart_pause_universal.py \
  --voice af_bella \
  --speed 1.5 \
  "Speaking with custom voice"
```

## Inter-Agent Communication

### Sending Messages to Other Agents

```bash
# Check available agents
/home/echo/bin/msg-list

# Send message to another agent
/home/echo/bin/msg-send frontend "API endpoints are ready at port 3000"

# The receiving agent will see:
# [kokoro]: API endpoints are ready at port 3000
```

### Message Priority

- User tasks ALWAYS come first
- Inter-agent messages are lower priority
- If busy, acknowledge and respond later

## Troubleshooting

### Audio Not Playing

1. **Check Guardian Angel web interface**
   ```bash
   # Open browser to:
   # https://eugene.tail1d96a2.ts.net/
   ```

2. **Verify TTS container is running**
   ```bash
   docker ps | grep kokoro-tts
   curl http://localhost:8880/health
   ```

3. **Check audio files are being created**
   ```bash
   ls -la /home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/
   ```

4. **View Guardian Angel logs**
   ```bash
   # Check for errors in audio detection
   tail -f /tmp/speak_resume.log
   ```

### Media Control Issues

1. **Media not pausing/resuming**
   - Ensure PowerShell scripts have execute permission
   - Check if Windows media control APIs are accessible
   - Verify no other apps are controlling media

2. **Double pause/resume**
   - Check for `.skip_media_control` markers
   - Ensure only one instance is managing media

### Queue Problems

1. **Audio playing out of order**
   ```bash
   # Check queue status
   ls -la /home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/*.lock
   ```

2. **Stale locks**
   - Queue system auto-cleans locks older than 5 minutes
   - Manual cleanup: Remove old .lock files

## Best Practices for Agents

### 1. Project Identification
Always prefix messages with your project name:
```bash
speak "Kokoro: Documentation complete"
speak "Frontend: Build successful"
speak "Database: Migration finished"
```

### 2. Status Updates
Use appropriate status commands:
```bash
# Starting work
claude-working "Installing dependencies"

# Completed task
claude-done "All tests passing"

# Quick notification
speak "Found 3 critical issues"
```

### 3. Error Reporting
Report errors clearly:
```bash
speak "Error: Database connection failed on port 5432"
speak "Warning: Found deprecated API usage in 5 files"
```

### 4. Progress Updates
For long-running tasks:
```bash
speak "Processing 1 of 10 files"
# ... work ...
speak "Processing 5 of 10 files"
# ... work ...
speak "Processing complete: 10 files analyzed"
```

## Integration with VS Code

If using VS Code with Guardian Angel:
1. Terminal titles update automatically with agent status
2. Audio plays through the web interface
3. Media control works even when VS Code is not in focus

## Security Notes

- Audio files are automatically deleted after playback
- No audio content is logged or stored permanently  
- Media control only affects local Windows session
- All communication is local (localhost only)

## Performance Considerations

- TTS generation: ~100-500ms depending on text length
- Audio playback: Instant once generated
- Media control: ~50-100ms overhead
- Queue processing: Negligible overhead
- Multiple agents: No performance impact (parallel generation)

## Future Enhancements

- Direct parameter support in speak command
- Voice preset configurations
- Emotion presets for quick access
- Cross-agent audio priority system
- Audio history and replay features