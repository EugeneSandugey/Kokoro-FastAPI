# HD Transfers Sales Training Interface - Complete Project Memory

**Last Updated:** October 29, 2025

This document contains EVERYTHING about this project so a new AI assistant session can understand the entire system by reading this file.

---

## What This Project Is

A **voice-based sales training interface** where users practice cold calling by talking to an AI that roleplays as a customer. The AI uses emotional tone, personality types, and difficulty levels to create realistic sales scenarios.

**Live URL:** https://training.eugenes.ai
**Purpose:** Train sales reps for HD Transfers (DTF printing company) in handling cold calls

---

## Technology Stack

**Core:**
- React 18 + Vite (dev server)
- TypeScript
- Google Gemini 2.5 Flash Native Audio API (Preview model: `gemini-2.5-flash-native-audio-preview-09-2025`)
- Real-time bidirectional audio streaming (WebSocket)

**State Management:**
- Zustand (with localStorage persistence)

**Audio:**
- Web Audio API
- AudioRecorder class (custom implementation)
- AudioStreamer class (handles output)
- Volume meter worklet

**Deployment:**
- Vite dev server (port 3000)
- Cloudflare tunnel: `hdtransfers-training` → training.eugenes.ai
- Systemd services (auto-start on boot)

---

## Project Structure

```
/home/echo/projects/hdtransfers/training/
├── components/
│   ├── Header.tsx                    # Settings panel (top-right options menu)
│   ├── SystemPromptEditor.tsx        # Modal for editing AI instructions
│   ├── audio-visualizer/             # 3D orb visualizer
│   │   ├── AudioVisualizer.tsx       # React wrapper
│   │   └── visual-3d.ts              # Lit Element custom component
│   ├── demo/
│   │   └── streaming-console/
│   │       └── StreamingConsole.tsx  # Main component - handles AI config
│   └── control-tray/
│       └── ControlTray.tsx           # Bottom buttons (mic, download, etc.)
├── contexts/
│   ├── LiveAPIContext.tsx            # Gemini API connection provider
│   └── AudioNodesContext.tsx         # Web Audio nodes provider
├── hooks/
│   └── media/
│       └── use-live-api.ts           # Custom hook for Gemini Live API
├── lib/
│   ├── genai-live-client.ts          # Gemini WebSocket client class
│   ├── audio-recorder.ts             # Microphone input handler
│   ├── audio-streamer.ts             # Speaker output handler
│   ├── state.ts                      # Zustand stores
│   ├── constants.ts                  # Model and voice defaults
│   └── worklets/
│       └── vol-meter.ts              # Volume meter worklet
├── sales_roleplay_system_prompt.md   # 25KB AI training instructions
├── index.css                         # All styling (22KB)
├── App.tsx                           # Root component
├── index.tsx                         # Entry point
├── vite.config.ts                    # Dev server config
├── tunnel-config.yml                 # Cloudflare tunnel routing
├── .env.local                        # API key (GEMINI_API_KEY)
├── PROJECT_MEMORY.md                 # This file
├── TRAINING_CONFIG.md                # API configuration reference
└── docs/archive/                     # Old/unused files
```

---

## How It Works

### 1. User Opens https://training.eugenes.ai

1. Cloudflare tunnel routes request to localhost:3000
2. Vite serves React app
3. React loads with default settings from localStorage

### 2. User Clicks Play Button

1. `LiveAPIContext` creates WebSocket connection to Gemini
2. Sends setup message with:
   - Model: `gemini-2.5-flash-native-audio-preview-09-2025`
   - System prompt (25KB with personality types, scenarios, difficulty)
   - Voice selection (one of 33 voices)
   - Response modality: AUDIO only
   - Thinking config (on/off with dynamic budget)
   - Turn coverage, affective dialogue, proactive audio settings
   - Audio transcription (input + output enabled)
3. Gemini responds with setup complete
4. Connection is live - bidirectional audio streaming begins

### 3. User Speaks (Microphone Active)

1. Browser captures microphone audio
2. `AudioRecorder` processes raw audio
3. Audio chunks sent to Gemini via `BidiGenerateContentRealtimeInput` messages
4. Gemini transcribes user speech (displayed in UI)
5. Gemini detects end-of-speech automatically (or manual activity signals if disabled)

### 4. AI Responds

1. Gemini generates audio response in real-time
2. Audio chunks streamed back via WebSocket
3. `AudioStreamer` plays audio through speakers
4. Gemini sends transcription of its own speech (displayed in UI)
5. If thinking mode enabled, thought processes shown in blue collapsible sections

### 5. User Clicks New Session (+)

1. Clears conversation history
2. Disconnects WebSocket
3. Picks new random voice (if random enabled)
4. Generates new random difficulty 1-10 (if random selected)
5. Reconnects after 500ms with fresh session

---

## Key Components Explained

### StreamingConsole.tsx (Main Brain)

**Location:** `/components/demo/streaming-console/StreamingConsole.tsx`

**What it does:**
- Pulls settings from Zustand store (voice, difficulty, thinking mode, etc.)
- Injects difficulty into system prompt with critical instruction
- Builds API config object with all settings
- Passes config to LiveAPIContext
- Handles incoming messages (content, transcription, tool calls, thoughts)
- Manages conversation state (turns array)
- Renders transcription view with thoughts

**Key code section (lines 93-143):**
```typescript
const config: any = {
  responseModalities: [Modality.AUDIO],
  speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice }}},
  inputAudioTranscription: {},
  outputAudioTranscription: {},
  systemInstruction: { parts: [{ text: finalSystemPrompt }]},
  tools: enabledTools,
  thinkingConfig: { thinkingBudget: thinkingMode ? -1 : 0 },
  realtimeInputConfig: { turnCoverage: turnCoverage },
  enable_affective_dialog: affectiveDialogue,
  proactivity: { proactiveAudio: proactiveAudio },
  // Context window compression would go here
};
setConfig(config);
```

### Header.tsx (Settings UI)

**Location:** `/components/Header.tsx`

**What it does:**
- Renders three-dot menu (top-right)
- Shows dropdowns and checkboxes for all settings
- Updates Zustand store on change (auto-saves to localStorage)
- Opens system prompt editor modal

**Controls:**
- Difficulty: Dropdown (Random or 1-10)
- Voice: Dropdown (33 options + RANDOM)
- Thinking: Dropdown (None / Thinking / Show Thoughts)
- Turn Coverage: Dropdown (Activity Only / All Input)
- Affective Dialogue: Checkbox
- Proactive Audio: Checkbox
- Edit System Prompt: Button

### state.ts (Zustand Stores)

**Location:** `/lib/state.ts`

**What it contains:**

**useSettings store:**
- systemPrompt (string)
- model (string)
- voice (string)
- randomVoice (boolean)
- thinkingMode (boolean)
- showThoughts (boolean)
- difficulty (string: "random" or "1"-"10")
- turnCoverage (string: enum)
- affectiveDialogue (boolean)
- proactiveAudio (boolean)
- Setters for all of the above

**useLogStore:**
- turns[] (ConversationTurn array)
- addTurn()
- updateLastTurn()
- clearTurns()

**useTools store:**
- tools[] (function calling definitions)
- Mostly unused in this project

### LiveAPIContext.tsx + use-live-api.ts

**What they do:**
- Create and manage Gemini WebSocket connection
- Handle audio streaming setup (Web Audio API nodes)
- Manage connection state (connected/disconnected/connecting)
- Provide `client` and `setConfig` to components

### genai-live-client.ts

**What it does:**
- Custom class wrapping Google's `@google/genai` SDK
- Extends EventEmitter for message handling
- Manages WebSocket connection lifecycle
- Parses server messages and emits typed events
- Handles reconnection and session management

### sales_roleplay_system_prompt.md

**Location:** `/sales_roleplay_system_prompt.md` (25KB)

**What it contains:**
- Instructions for AI: "You are the CUSTOMER being called, NOT the sales rep"
- 10 personality types (Friendly Skeptic, Budget-Conscious Buyer, Demanding Expert, etc.)
- 20 problem scenarios (quality issues, pricing concerns, shipping problems, etc.)
- Difficulty system 1-10:
  - 1-3: Friendly, open, easy to sell to
  - 4-6: Neutral, needs convincing
  - 7-10: Angry, hostile, extremely difficult
- Tone instructions tied to difficulty
- Order history simulation

**Auto-injected by code:**
```javascript
const actualDifficulty = difficulty === 'random'
  ? Math.floor(Math.random() * 10) + 1
  : parseInt(difficulty);

finalSystemPrompt += `\n\n🚨 CRITICAL INSTRUCTION: You MUST use difficulty ${actualDifficulty} for this session.`;
```

---

## Gemini API Configuration (COMPLETE)

### Model

`gemini-2.5-flash-native-audio-preview-09-2025`

**Why this model:**
- Preview model with native audio capabilities
- Supports bidirectional real-time audio streaming
- Supports affective dialogue (emotion-aware)
- Supports proactive audio (can choose not to respond)
- 33 built-in voices

### Response Modalities

- ✅ **AUDIO** (only - no text response)

### Audio Features

**Input Audio Transcription:**
- Enabled: `inputAudioTranscription: {}`
- Displays user speech as text in UI
- Sent independently of other server messages (no ordering guarantee)

**Output Audio Transcription:**
- Enabled: `outputAudioTranscription: {}`
- Displays AI speech as text in UI
- Sent independently (no ordering guarantee with serverContent)

**Voice Config:**
- 33 available voices (see `/lib/constants.ts`)
- Default: RANDOM (picks different voice each session)
- User selectable via dropdown
- Set in `speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName`

### Thinking Mode

**Parameter:** `thinkingConfig.thinkingBudget`

**Options:**
- `-1` = Dynamic thinking (auto-adjusts based on complexity) - AI generates visible reasoning
- `0` = Thinking disabled - AI responds directly

**When enabled:**
- AI sends thought content in separate parts
- UI displays in blue collapsible sections
- User can toggle "Show Thoughts" to auto-expand all

**Default:** OFF

### Turn Coverage (NEW)

**Parameter:** `realtimeInputConfig.turnCoverage`

**Options:**
- `TURN_INCLUDES_ONLY_ACTIVITY` (default) - User turn only includes activity since last turn, excluding silence
- `TURN_INCLUDES_ALL_INPUT` - User turn includes ALL input since last turn, including silence

**What it means:**
- Activity Only: AI only processes speech/text, ignores silence gaps
- All Input: AI processes everything including silence (useful for pauses, hesitation detection)

**UI Control:** Dropdown in settings
**Default:** Activity Only

### Affective Dialogue (NEW - v1alpha only)

**Parameter:** `enable_affective_dialog` (boolean)

**What it does:**
- Lets Gemini adapt response style to input expression and tone
- AI detects emotion in user's voice and responds appropriately
- Makes conversations feel more natural and human-like

**Requirements:**
- Must use v1alpha API (NOT CURRENTLY IMPLEMENTED IN CODE)
- Only works with native audio models

**Mutual Exclusivity:** User reported that Google's web UI doesn't allow both affective dialogue AND proactive audio enabled simultaneously. API docs suggest they're independent. NEEDS TESTING.

**UI Control:** Checkbox in settings
**Default:** FALSE

### Proactive Audio (NEW)

**Parameter:** `proactivity.proactiveAudio` (boolean)

**What it does:**
- Model can decide NOT to respond if content is irrelevant
- Ignores background noise, out-of-context speech, ambient conversations
- Stays silent if user didn't make a request

**Use case:** Prevents AI from responding to non-directed speech (e.g., user talking to someone else in the room)

**UI Control:** Checkbox in settings
**Default:** FALSE

### Session Context Compression (✅ ENABLED)

**Local API Docs:** `/docs/GEMINI_LIVE_API_REFERENCE.md` (Complete reference downloaded from Google)
**Official Docs:** https://ai.google.dev/gemini-api/docs/live-session

**Purpose:** Extend session beyond time limits by managing context window

**Without compression:**
- Audio-only sessions: 15 minute limit
- Audio-video sessions: 2 minute limit

**With compression:**
- Unlimited session time

**How it works:**

**Parameter:** `contextWindowCompression`

**Configuration:**
```typescript
contextWindowCompression: {
  slidingWindow: {
    targetTokens: 12800  // Number of tokens to keep after compression
  },
  triggerTokens: 25600   // Number of tokens that triggers compression
}
```

**Fields:**

1. **`triggerTokens`** (int64) - "Max Context Size" in Google's UI
   - Number of tokens (before running a turn) that triggers compression
   - Default: 80% of model's context window limit
   - When context reaches this size, compression is triggered
   - Should balance quality vs latency

2. **`slidingWindow.targetTokens`** (int64) - "Target Context Size" in Google's UI
   - Target number of tokens to keep after compression
   - Default: triggerTokens / 2
   - Context is reduced to this size when compression occurs
   - Should calibrate to avoid frequent compression (causes latency spike)

**Sliding Window Behavior:**
- Discards content at the BEGINNING of context window
- Resulting context ALWAYS begins at start of a USER role turn
- System instructions ALWAYS remain at the beginning
- Prefix turns ALWAYS remain at the beginning

**Example:**
```typescript
const config = {
  contextWindowCompression: {
    triggerTokens: 32000,  // Trigger compression at 32K tokens
    slidingWindow: {
      targetTokens: 16000  // Keep 16K tokens after compression
    }
  }
};
```

**When to use:**
- Long training sessions (30+ minutes)
- Therapist/friend AI (ongoing conversations)
- Scenarios where conversation history matters but needs management

**For current sales training project:**
- ✅ NOW ENABLED with Google's default values (25600 trigger / 12800 target)
- Enables sessions longer than 15 minutes without hitting limits
- No UI controls (set in code only)
- Compression triggers automatically if session exceeds ~25K tokens
- Most sessions still under 15 min, but this removes the hard limit

**For future projects (friend/therapist AI):**
- CRITICAL FEATURE - Enables unlimited conversation time
- Pair with memory injection system (save important facts to database, inject into system prompt on next session)

### Function Calling / Tools

**Status:** Supported but unused in current project

**How it works:**
- Define tools in `config.tools` array
- AI can request tool execution
- Client receives `BidiGenerateContentToolCall` message
- Client executes and responds with `BidiGenerateContentToolResponse`

**Future use case:**
- Save important user facts to database during conversation
- "Remember my name is John and I own a print shop in Austin"

### Session Resumption (NOT YET IMPLEMENTED)

**Purpose:** Prevent session termination when server resets WebSocket connection (happens every ~10 minutes)

**How it works:**
```typescript
config: {
  sessionResumption: {
    handle: previousSessionHandle || null  // null = new session
  }
}
```

Server sends `SessionResumptionUpdate` messages with `newHandle`.
Client stores handle and uses it to resume session on next connection.
Handles valid for 2 hours after session termination.

**Current behavior:** Connection drops after ~10 minutes, session lost.

---

## What's NOT Enabled

❌ Text response modality
❌ Video input/output
❌ Google Search / Grounding
❌ Code execution
❌ Multi-turn context limits (full history until cleared or compressed)
❌ Session resumption (connection drops after ~10 minutes)
❌ v1alpha API (needed for affective dialogue)

---

## User Flow

### First Time Visitor

1. Lands on https://training.eugenes.ai
2. Sees purple gradient orb visualizer (not animated yet)
3. Play button at bottom
4. Settings menu (three dots) top-right
5. Clicks Play → Gemini connects → Orb animates
6. Speaks into microphone
7. AI responds with voice + transcription
8. Conversation continues until user clicks Pause or New Session

### Returning Visitor

1. All settings persist from localStorage:
   - Last selected voice (or RANDOM)
   - Thinking mode preference
   - Show thoughts preference
   - Difficulty level
   - Turn coverage, affective dialogue, proactive audio
   - System prompt edits
2. Previous session conversation NOT saved (intentional)

### Typical Training Session

1. Open site → Click Play
2. AI says "Hello?" (as customer)
3. User delivers opening pitch
4. AI responds with personality + difficulty level behavior
5. User handles objections, questions, pushback
6. Conversation continues 5-15 minutes
7. User clicks New Session to practice with different customer
8. Repeat

---

## File Locations & Purposes

### Configuration Files

- `.env.local` - Contains GEMINI_API_KEY (not in git)
- `vite.config.ts` - Dev server settings (port 3000, allowed hosts)
- `tunnel-config.yml` - Cloudflare tunnel routing
- `package.json` - Dependencies and scripts
- `tsconfig.json` - TypeScript compiler options

### Source Code

- `index.tsx` - Entry point, renders `<App />`
- `App.tsx` - Root component, provides LiveAPI and AudioNodes contexts
- `index.css` - ALL styling (22KB, no CSS modules)

### Documentation

- `PROJECT_MEMORY.md` - This file (complete project knowledge)
- `TRAINING_CONFIG.md` - API configuration reference
- `LICENSE.md` - Apache 2.0 license
- `docs/archive/` - Old files (original README, backup code, shell scripts)

### Services

- `training-vite.service` - Systemd service for Vite dev server
  - Runs: `npm run dev` in `/home/echo/projects/hdtransfers/training/`
  - Port: 3000
  - Auto-starts on boot
  - Logs to systemd journal

- `training-tunnel.service` - Systemd service for Cloudflare tunnel
  - Runs: `cloudflared tunnel --config tunnel-config.yml run hdtransfers-training`
  - Routes training.eugenes.ai → localhost:3000
  - Auto-starts on boot
  - Depends on training-vite.service

---

## How to Start/Stop Services

### Manual Start
```bash
cd /home/echo/projects/hdtransfers/training

# Start Vite dev server (port 3000)
npm run dev

# Start Cloudflare tunnel (separate terminal)
cloudflared tunnel --config tunnel-config.yml run hdtransfers-training
```

### Systemd (Auto-start on boot)
```bash
# Check status
systemctl status training-vite.service training-tunnel.service

# Start
sudo systemctl start training-vite.service training-tunnel.service

# Stop
sudo systemctl stop training-vite.service training-tunnel.service

# Restart
sudo systemctl restart training-vite.service training-tunnel.service

# View logs
sudo journalctl -u training-vite.service -f
sudo journalctl -u training-tunnel.service -f
```

---

## Common Issues & Solutions

### "Blocked request. This host is not allowed"

**Problem:** Vite rejects requests from training.eugenes.ai

**Solution:** Add hostname to `vite.config.ts`:
```typescript
server: {
  allowedHosts: ['training.eugenes.ai', 'hdtransfers-training.eugenes.ai']
}
```

### Changes not appearing on mobile

**Problem:** CSS/JS changes don't show after edit

**Solutions:**
1. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
2. Incognito mode
3. Clear Vite cache: `rm -rf .vite`
4. Restart dev server

### Connection drops after 10 minutes

**Problem:** WebSocket connection terminates, session lost

**Solution:** Implement session resumption (see Session Resumption section)

### Audio doesn't work

**Problem:** No audio in/out

**Checklist:**
1. Browser microphone permissions granted?
2. Browser speaker permissions granted?
3. Check browser console for errors
4. Verify AudioRecorder and AudioStreamer initialized
5. Check Web Audio context state (suspended/running)

### Thinking mode not working

**Problem:** Thoughts not displayed

**Checklist:**
1. Thinking mode enabled in settings?
2. `thinkingBudget` set to `-1` in config?
3. Check browser console for thought content
4. Verify `showThoughts` toggle state

---

## Future Enhancements

### Short Term (Next Features)

1. **Test affective dialogue + proactive audio**
   - Determine if mutually exclusive
   - Add UI logic if needed

2. **v1alpha API support**
   - Modify LiveAPIContext to use v1alpha when affective dialogue enabled
   - Test with: `client = genai.Client(http_options={"api_version": "v1alpha"})`

3. **Session metrics**
   - Track session duration
   - Track number of turns
   - Display stats at end of session

### Medium Term

1. **Session context compression**
   - Enable unlimited session time
   - Add UI controls for trigger/target tokens
   - Default: trigger=25600, target=12800

2. **Session resumption**
   - Persist sessions across connection drops
   - Store resumption handles in localStorage
   - Auto-reconnect with previous handle

3. **Recording & playback**
   - Record entire training session
   - Play back conversation with annotations
   - Export to audio file

### Long Term (New Projects)

1. **Friend / Therapist AI**
   - Based on this exact project
   - Enable session context compression
   - Add memory system (save important facts to database)
   - Inject memories into system prompt on session start
   - Support for unlimited conversation time

2. **Sales coaching analysis**
   - AI analyzes user performance
   - Suggests improvements
   - Tracks progress over time
   - Generates reports

---

## Git Repository

**URL:** `git@github.com:EugeneSandugey/HD-Training.git`
**Type:** Private
**Branch:** main
**Commits:** Regular commits to track changes

**.gitignore includes:**
- node_modules/
- .vite/
- dist/
- .env.local
- venv/
- __pycache__/
- *.pyc
- docs/archive/temp_download/

---

## Dependencies

**Key packages:**
- `@google/genai` - Official Gemini SDK
- `react` / `react-dom` - UI framework
- `zustand` - State management
- `eventemitter3` - Event system
- `lodash` - Utility functions
- `vite` - Build tool / dev server
- `typescript` - Type safety

**All dependencies in `package.json`**

---

## Important Constants

**From `/lib/constants.ts`:**

```typescript
export const DEFAULT_LIVE_API_MODEL = 'gemini-2.5-flash-native-audio-preview-09-2025';

export const DEFAULT_VOICE = 'RANDOM';

export const AVAILABLE_VOICES = [
  'RANDOM', 'Zephyr', 'Puck', 'Charon', 'Luna', 'Nova', 'Kore', 'Fenrir',
  'Leda', 'Orus', 'Aoede', 'Callirrhoe', 'Autonoe', 'Enceladus', 'Iapetus',
  'Umbriel', 'Algieba', 'Despina', 'Erinome', 'Algenib', 'Rasalgethi',
  'Laomedeia', 'Achernar', 'Alnilam', 'Schedar', 'Gacrux', 'Pulcherrima',
  'Achird', 'Zubenelgenubi', 'Vindemiatrix', 'Sadachbia', 'Sadaltager', 'Sulafat'
];
```

**Voice names:** Greek mythology and star names

---

## CSS Architecture

**Single file:** `index.css` (22KB)

**Key sections:**
- Global resets and variables
- Streaming console (main container)
- Audio visualizer (purple orb)
- Transcription view (chat area)
- Control tray (bottom buttons)
- Header and options panel
- System prompt editor modal
- Sidebar (settings)

**Color scheme:**
- Background: Black with gradient
- Orb: Purple gradient (#d946ef, #9333ea, #7e22ce)
- Text: White
- Accents: Blue (#1f94ff)
- Buttons: Neutral grays

**Mobile responsive:**
- Uses `100dvh` for dynamic viewport height (accounts for mobile address bar)
- Transcription stops 125px from bottom (button clearance)
- Options panel adjusts for small screens

---

## Testing Checklist

When making changes, verify:

- [ ] Vite dev server starts without errors
- [ ] Site loads at training.eugenes.ai
- [ ] Play button connects to Gemini
- [ ] Microphone captures audio
- [ ] AI responds with audio
- [ ] Transcription displays for both user and AI
- [ ] Settings panel opens
- [ ] All settings persist after page refresh
- [ ] New Session button clears history and reconnects
- [ ] System prompt editor opens and saves
- [ ] Thinking mode displays thoughts (if enabled)
- [ ] Voice selection changes voice (not RANDOM)
- [ ] Random voice picks different voice each session
- [ ] Turn coverage setting changes API config
- [ ] Affective dialogue checkbox works
- [ ] Proactive audio checkbox works

---

## Known Limitations

1. **15 minute session limit** (without compression)
2. **Connection drops every ~10 minutes** (WebSocket reset, no resumption)
3. **No session history** (cleared on page refresh)
4. **No recording/playback**
5. **v1alpha API not implemented** (affective dialogue may not work)
6. **Mutual exclusivity unclear** (affective + proactive may conflict)

---

## Related Projects

**Parent project:** HD Transfers (DTF printing company)
**Location:** `/home/echo/projects/hdtransfers/`
**Purpose:** Cold calling training for sales team

**Sibling projects in HD Transfers:**
- CRM Dashboard (`/dashboard/`) - Customer management with Supabase
- Email campaigns (Shopify Email)
- Cold calling setup (Close.com CRM)

---

## Key Learnings (What Makes This Different)

### From Building This Project

1. **Native audio is special:** Gemini 2.5 Flash Native Audio is fundamentally different from text-to-speech. It's true end-to-end audio, not synthesized speech from text.

2. **Thinking mode is powerful:** When enabled with `-1` budget, the AI generates human-like reasoning that dramatically improves response quality.

3. **Random difficulty is critical:** Initially AI chose difficulty (always picked 6). JavaScript random number generation forces variety.

4. **System prompt clarification matters:** Had to explicitly state "You are the CUSTOMER" because AI kept acting as sales rep.

5. **Transcription is independent:** Audio transcription arrives separately from content, no ordering guarantees. UI must handle async updates.

6. **Turn coverage changes everything:** Activity-only vs all-input affects how AI interprets pauses and silence.

7. **Context compression enables new use cases:** Without it, sessions are limited. With it, unlimited conversation time unlocks friend/therapist AI applications.

8. **v1alpha features need explicit API version:** Affective dialogue requires switching to alpha API, not just setting a flag.

---

## Next Steps (If Continuing This Project)

1. Test affective dialogue and proactive audio (verify mutual exclusivity)
2. Implement session context compression (enable 30+ minute sessions)
3. Implement session resumption (handle 10 minute WebSocket resets)
4. Add v1alpha API support for affective dialogue
5. Add session metrics tracking
6. Consider adding recording/playback functionality

---

**END OF PROJECT MEMORY**

This document should contain everything needed for a new AI assistant to understand the entire project. If anything is missing or unclear, update this file.
