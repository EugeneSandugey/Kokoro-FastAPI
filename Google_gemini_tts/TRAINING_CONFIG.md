# HD Transfers Sales Training Interface - Complete Configuration

**Live URL:** https://training.eugenes.ai
**Tech Stack:** React + Vite + TypeScript + Google Gemini 2.5 Flash Native Audio API
**Purpose:** Voice-based sales training with AI customer roleplay

---

## Gemini API Configuration

### Core Settings

**Model:** `gemini-2.5-flash-native-audio-preview-09-2025`

**Response Modality:**
- ✅ AUDIO ONLY (no text response)

**Voice Settings:**
- 33 available voices (see `/lib/constants.ts`)
- Default: RANDOM (picks random voice each session)
- User configurable via dropdown
- Persists in localStorage

### Audio Features

**Transcription:**
- ✅ Input audio transcription ENABLED (`inputAudioTranscription: {}`)
- ✅ Output audio transcription ENABLED (`outputAudioTranscription: {}`)
- Both displayed in real-time in UI

### Advanced Audio Settings (User Toggleable)

#### 1. Turn Coverage
**Parameter:** `realtimeInputConfig.turnCoverage`
**Options:**
- `TURN_INCLUDES_ONLY_ACTIVITY` (default) - User turn only includes activity since last turn, excluding silence
- `TURN_INCLUDES_ALL_INPUT` - User turn includes all input since last turn, including silence

**UI Control:** Dropdown in settings (to be added)
**Default:** `TURN_INCLUDES_ONLY_ACTIVITY`

#### 2. Affective Dialogue
**Parameter:** `enable_affective_dialog` (boolean, v1alpha API only)
**Description:** Lets Gemini adapt response style to input expression and tone (emotion-aware)
**Requirement:** Must use v1alpha API version
**Mutual Exclusivity:** May be mutually exclusive with proactive audio (user reported, needs testing)

**UI Control:** Checkbox in settings (to be added)
**Default:** FALSE

#### 3. Proactive Audio
**Parameter:** `proactivity.proactiveAudio` (boolean)
**Description:** Model can decide NOT to respond if content is not relevant (ignores background noise, out-of-context speech)
**Mutual Exclusivity:** May be mutually exclusive with affective dialogue (user reported, needs testing)

**UI Control:** Checkbox in settings (to be added)
**Default:** FALSE

### Thinking Mode (User Toggleable)

**Parameter:** `thinkingConfig.thinkingBudget`
**Options:**
- `-1` = Dynamic thinking (auto-adjusts based on complexity)
- `0` = Thinking disabled

**When enabled:**
- AI generates visible "thought" sections before responding
- Thoughts displayed in collapsible blue sections
- "Show Thoughts" toggle auto-expands all thought sections

**UI Controls:**
- "Thinking Mode" checkbox (enables/disables thinking)
- "Show Thoughts" checkbox (auto-expands thought sections)
- Both persist in localStorage

**Default:** OFF (disabled)

### System Prompt

**Source:** `/sales_roleplay_system_prompt.md` (~25KB)
**Editable:** Yes, via gear icon (persists in localStorage)
**Contains:**
- 10 personality types
- 20 problem scenarios
- Difficulty system (1-10)
- Tone-of-voice instructions

**Auto-injection:**
- Difficulty level (1-10 or random) injected automatically
- Random difficulty uses `Math.random()` to generate 1-10 each session
- Critical instruction added: "You are the CUSTOMER being called, not the sales rep"

### Function Calling / Tools

**Status:** ✅ Supported (disabled by default)
**Config:** `tools: enabledTools`
**Default:** Empty array (no tools enabled)

### Session Context Compression (✅ ENABLED)

**Purpose:** Extend session beyond time limits by managing context window size

**Without compression:**
- Audio-only sessions: **15 minute limit**
- Audio-video sessions: **2 minute limit**

**With compression:**
- **Unlimited session time**

**How it works:**

Context window compression uses a sliding-window mechanism that discards content at the beginning of the context window when it exceeds a configured length.

**Configuration:**
```typescript
contextWindowCompression: {
  triggerTokens: 25600,      // "Max Context Size" - triggers compression
  slidingWindow: {
    targetTokens: 12800       // "Target Context Size" - size after compression
  }
}
```

**Parameters:**

1. **`triggerTokens`** (int64) - When to compress
   - Number of tokens (before running a turn) that triggers compression
   - Default: 80% of model's context window limit (if not set)
   - Example: 25,600 tokens or 32,000 tokens
   - Should balance quality vs latency

2. **`slidingWindow.targetTokens`** (int64) - What to keep
   - Target number of tokens to keep after compression
   - Default: `triggerTokens / 2` (if not set)
   - Example: 12,800 tokens (half of 25,600)
   - Calibrate to avoid frequent compression (causes latency spikes)

**What gets kept:**
- ✅ System instructions (always at beginning)
- ✅ Prefix turns (always at beginning)
- ✅ Recent conversation (from target_tokens point to present)
- ❌ Old conversation history (discarded from beginning)

**Important:** Resulting context ALWAYS begins at the start of a USER role turn

**When to use:**
- Long training sessions (30+ minutes)
- Therapist/friend AI (ongoing conversations)
- Any scenario where unlimited session time is needed

**Current implementation:**
- ✅ Enabled in code with Google's default values
- triggerTokens: 25,600
- slidingWindow.targetTokens: 12,800
- No UI controls (automatically triggers when needed)
- Extends sessions beyond 15-minute limit

**Example config:**
```typescript
const config = {
  // ... other settings ...
  contextWindowCompression: {
    triggerTokens: 32000,  // Compress at 32K tokens
    slidingWindow: {
      targetTokens: 16000  // Keep 16K tokens after compression
    }
  }
};
```

**API Reference:** https://ai.google.dev/gemini-api/docs/live-session#context-window-compression

---

## UI Configuration

### Settings Panel Controls

**Current:**
- Difficulty (Random or 1-10)
- Voice selector (33 voices)
- Random Voice checkbox
- Thinking Mode checkbox
- Show Thoughts checkbox
- System Prompt editor (gear icon)

**To Add:**
- Turn Coverage dropdown (ACTIVITY_ONLY / ALL_INPUT)
- Affective Dialogue checkbox
- Proactive Audio checkbox

### Session Controls

**New Session (+ button):**
1. Clears chat history
2. Disconnects current session
3. Picks new random voice (if Random Voice enabled)
4. Generates new random difficulty 1-10 (if Random selected)
5. Reconnects after 500ms

**Other Controls:**
- Microphone mute/unmute
- Download logs (conversation transcript)
- Play/Pause (main connection)

### Persistence (localStorage)

All settings survive page refresh:
- `voice` - Selected voice
- `randomVoice` - Random voice toggle
- `thinkingMode` - Thinking on/off
- `showThoughts` - Auto-expand thoughts
- `difficulty` - Difficulty level (random or 1-10)
- `systemPrompt` - Edited system prompt
- Session state (current customer profile, conversation history)

---

## API Config Structure

```typescript
const config: any = {
  responseModalities: [Modality.AUDIO],

  speechConfig: {
    voiceConfig: {
      prebuiltVoiceConfig: {
        voiceName: voice  // One of 33 available voices
      }
    }
  },

  inputAudioTranscription: {},   // enabled
  outputAudioTranscription: {},  // enabled

  systemInstruction: {
    parts: [{ text: finalSystemPrompt }]  // With difficulty injected
  },

  tools: enabledTools,  // Empty by default

  thinkingConfig: {
    thinkingBudget: thinkingMode ? -1 : 0  // Dynamic or disabled
  },

  // TO ADD:
  realtimeInputConfig: {
    turnCoverage: "TURN_INCLUDES_ONLY_ACTIVITY"  // or TURN_INCLUDES_ALL_INPUT
  },

  enable_affective_dialog: false,  // Requires v1alpha API

  proactivity: {
    proactiveAudio: false
  }
};
```

---

## File Locations

**Key Files:**
- `/components/demo/streaming-console/StreamingConsole.tsx` - Main config setup (lines 93-125)
- `/lib/state.ts` - Zustand state management with localStorage
- `/lib/constants.ts` - Model and voice defaults
- `/contexts/LiveAPIContext.tsx` - API connection management
- `/components/Header.tsx` - Settings controls UI
- `/sales_roleplay_system_prompt.md` - AI training instructions
- `/index.css` - All styling
- `/vite.config.ts` - Dev server config
- `/tunnel-config.yml` - Cloudflare tunnel config

**Services:**
- Training Vite: `training-vite.service` (port 3000)
- Training Tunnel: `training-tunnel.service` (training.eugenes.ai)

---

## What's NOT Enabled

❌ Text response modality
❌ Video input/output
❌ Google Search / Grounding
❌ Code execution
❌ Multi-turn context limits (full history maintained)

---

## Technical Notes

**API Version:**
- Default: stable (no version specified)
- For affective dialogue: Must use v1alpha (`http_options={"api_version": "v1alpha"}`)

**Mutual Exclusivity (Reported but Unverified):**
- User reports affective dialogue and proactive audio can't both be enabled in Google's web UI
- API documentation suggests they're independent
- Needs testing to confirm

**Vite Dev Server:**
- Runs on port 3000
- Allowed hosts: `training.eugenes.ai`, `hdtransfers-training.eugenes.ai`
- Hot module replacement (HMR) enabled

**Cloudflare Tunnel:**
- Tunnel name: `hdtransfers-training`
- Routes to localhost:3000
- 4 edge connections
- Auto-starts on boot via systemd
