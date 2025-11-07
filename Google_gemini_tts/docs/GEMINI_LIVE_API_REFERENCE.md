# Gemini Live API - Complete WebSockets API Reference

**Source:** https://ai.google.dev/api/live (Downloaded October 29, 2025)

---

## Session Context Compression - Complete Documentation

**From:** https://ai.google.dev/gemini-api/docs/live-session#context-window-compression

### ContextWindowCompressionConfig

Enables context window compression — a mechanism for managing the model's context window so that it does not exceed a given length.

**Fields:**

**Union field `compressionMechanism`** - The context window compression mechanism used. Can be only one of the following:

- **`slidingWindow`** - `SlidingWindow` - A sliding-window mechanism
- **`triggerTokens`** - `int64` - The number of tokens (before running a turn) required to trigger a context window compression

**What this means:**
- This can be used to balance quality against latency
- Shorter context windows may result in faster model responses
- However, any compression operation will cause a temporary latency increase
- So they should not be triggered frequently
- **If not set, the default is 80% of the model's context window limit**
- This leaves 20% for the next user request/model response

### SlidingWindow

The SlidingWindow method operates by discarding content at the beginning of the context window.

**Important behavior:**
- The resulting context will always begin at the start of a USER role turn
- System instructions and any `BidiGenerateContentSetup.prefixTurns` will always remain at the beginning of the result

**Fields:**

- **`targetTokens`** - `int64` - The target number of tokens to keep
  - **Default value:** `trigger_tokens/2`
  - Discarding parts of the context window causes a temporary latency increase
  - This value should be calibrated to avoid frequent compression operations

### Session Lifetime Without Compression

**Audio-only sessions:** Limited to 15 minutes
**Audio-video sessions:** Limited to 2 minutes

**With context window compression:** Sessions can extend to an unlimited amount of time

### Configuration Example (Python)

```python
from google.genai import types

config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    context_window_compression=(
        # Configures compression with default parameters
        types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        )
    ),
)
```

### Configuration Example (JavaScript)

```javascript
const config = {
  responseModalities: [Modality.AUDIO],
  contextWindowCompression: {
    slidingWindow: {}
  }
};
```

### Configuration Example with Custom Values

```javascript
const config = {
  responseModalities: [Modality.AUDIO],
  contextWindowCompression: {
    triggerTokens: 25600,     // Trigger compression at 25,600 tokens
    slidingWindow: {
      targetTokens: 12800     // Keep 12,800 tokens after compression
    }
  }
};
```

---

## Turn Coverage

**From:** `RealtimeInputConfig.turnCoverage`

Options about which input is included in the user's turn.

**Enums:**

- **`TURN_COVERAGE_UNSPECIFIED`** - If unspecified, the default behavior is `TURN_INCLUDES_ONLY_ACTIVITY`

- **`TURN_INCLUDES_ONLY_ACTIVITY`** - The users turn only includes activity since the last turn, excluding inactivity (e.g. silence on the audio stream). This is the default behavior.

- **`TURN_INCLUDES_ALL_INPUT`** - The users turn includes all realtime input since the last turn, including inactivity (e.g. silence on the audio stream)

---

## Proactivity Config

**From:** `ProactivityConfig`

Config for proactivity features.

**Fields:**

- **`proactiveAudio`** - `bool` - Optional. If enabled, the model can reject responding to the last prompt. For example, this allows the model to ignore out of context speech or to stay silent if the user did not make a request, yet.

---

## Affective Dialogue

**From:** Live API capabilities guide

**Parameter:** `enable_affective_dialog` (boolean, v1alpha API only)

**Description:** This feature lets Gemini adapt its response style to the input expression and tone

**Requirements:**
- Must use v1alpha API version
- Currently supported only by native audio output models

**How to enable (Python):**
```python
client = genai.Client(http_options={"api_version": "v1alpha"})
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    enable_affective_dialog=True
)
```

**Mutual Exclusivity:** Documentation indicates no mutual exclusivity between affective dialogue and proactive audio—both can theoretically be enabled simultaneously on native audio models.

---

## Complete Message Types Reference

### BidiGenerateContentSetup

Message to be sent in the first (and only in the first) `BidiGenerateContentClientMessage`. Contains configuration that will apply for the duration of the streaming RPC.

**Fields:**

- **`model`** - `string` - Required. The model's resource name. Format: `models/{model}`

- **`generationConfig`** - `GenerationConfig` - Optional. Generation config. Not supported: responseLogprobs, responseMimeType, logprobs, responseSchema, stopSequence, routingConfig, audioTimestamp

- **`systemInstruction`** - `Content` - Optional. The user provided system instructions for the model

- **`tools[]`** - `Tool` - Optional. A list of `Tools` the model may use to generate the next response

- **`realtimeInputConfig`** - `RealtimeInputConfig` - Optional. Configures the handling of realtime input

- **`sessionResumption`** - `SessionResumptionConfig` - Optional. Configures session resumption mechanism

- **`contextWindowCompression`** - `ContextWindowCompressionConfig` - Optional. Configures a context window compression mechanism

- **`inputAudioTranscription`** - `AudioTranscriptionConfig` - Optional. If set, enables transcription of voice input

- **`outputAudioTranscription`** - `AudioTranscriptionConfig` - Optional. If set, enables transcription of the model's audio output

- **`proactivity`** - `ProactivityConfig` - Optional. Configures the proactivity of the model

---

## RealtimeInputConfig

Configures the realtime input behavior in `BidiGenerateContent`

**Fields:**

- **`automaticActivityDetection`** - `AutomaticActivityDetection` - Optional. If not set, automatic activity detection is enabled by default

- **`activityHandling`** - `ActivityHandling` - Optional. Defines what effect activity has

- **`turnCoverage`** - `TurnCoverage` - Optional. Defines which input is included in the user's turn

---

## AutomaticActivityDetection

Configures automatic detection of activity.

**Fields:**

- **`disabled`** - `bool` - Optional. If enabled (the default), detected voice and text input count as activity. If disabled, the client must send activity signals

- **`startOfSpeechSensitivity`** - `StartSensitivity` - Optional. Determines how likely speech is to be detected

- **`prefixPaddingMs`** - `int32` - Optional. The required duration of detected speech before start-of-speech is committed. The lower this value, the more sensitive the start-of-speech detection is and shorter speech can be recognized. However, this also increases the probability of false positives

- **`endOfSpeechSensitivity`** - `EndSensitivity` - Optional. Determines how likely detected speech is ended

- **`silenceDurationMs`** - `int32` - Optional. The required duration of detected non-speech (e.g. silence) before end-of-speech is committed. The larger this value, the longer speech gaps can be without interrupting the user's activity but this will increase the model's latency

---

## Audio Transcription Config

The audio transcription configuration.

**This type has no fields** - Just enable by including it in config:

```typescript
inputAudioTranscription: {},   // Enables input transcription
outputAudioTranscription: {},  // Enables output transcription
```

---

## Thinking Config

**From:** `GenerationConfig`

**Field:** `thinkingConfig.thinkingBudget`

**Options:**
- `-1` - Dynamic thinking (auto-adjusts based on complexity)
- `0` - Thinking disabled

**When enabled:**
- AI generates visible "thought" sections before responding
- Thoughts displayed separately in server content
- Can be shown/hidden in UI

---

## Important Model Limits

**Model:** `gemini-2.5-flash-native-audio-preview-09-2025`

**Session Time Limits (WITHOUT compression):**
- Audio-only sessions: **15 minutes**
- Audio-video sessions: **2 minutes**

**Session Time Limits (WITH compression):**
- **Unlimited**

**Connection Lifetime:**
- Approximately 10 minutes
- GoAway message sent before connection terminates
- Use session resumption to maintain session across connections

---

## Session Resumption

To prevent session termination when the server periodically resets the WebSocket connection, configure the `sessionResumption` field within the setup configuration.

**Configuration:**
```typescript
config: {
  sessionResumption: {
    handle: previousSessionHandle || null  // null = new session
  }
}
```

**Behavior:**
- Server sends `SessionResumptionUpdate` messages
- Contains `newHandle` field (string)
- Client stores handle and uses it on next connection
- Handles valid for 2 hours after session termination

---

## GoAway Message

The server sends a `GoAway` message that signals that the current connection will soon be terminated.

**Fields:**
- **`timeLeft`** - `Duration` - The remaining time before the connection will be terminated as ABORTED

**Example (Python):**
```python
async for response in session.receive():
    if response.go_away is not None:
        # The connection will soon be terminated
        print(response.go_away.time_left)
```

---

## Generation Complete

The server sends a `generationComplete` message that signals that the model finished generating the response.

**Example:**
```javascript
if (turn.serverContent && turn.serverContent.generationComplete) {
  // The generation is complete
}
```

---

## What I Learned From Google's Official Docs

### Session Context Compression

**The problem:** Without compression, audio sessions are limited to 15 minutes (audio-video: 2 minutes)

**The solution:** Sliding window compression enables unlimited session time

**How it works:**
1. Conversation grows until it hits `triggerTokens` (default: 80% of max context)
2. Compression is triggered (causes temporary latency spike)
3. System discards oldest conversation from the BEGINNING
4. Keeps `targetTokens` worth of recent conversation (default: triggerTokens/2)
5. System instructions ALWAYS remain at the top (never discarded)
6. Context always starts at beginning of a USER turn (never mid-conversation)

**Key insight:** Google defaults to 80% trigger specifically to leave 20% headroom for the next user request and model response

**For sales training:**
- Default 25,600 trigger / 12,800 target is appropriate
- Most sessions under 15 minutes anyway
- But compression enables occasional longer sessions without hitting limits

**For therapist/friend AI:**
- Compression is CRITICAL (enables hour+ sessions)
- Pair with memory injection system:
  - Use function calls to save important facts to database during conversation
  - Load saved facts into system prompt on session start
  - This gives "memory" without using context tokens

### Affective Dialogue vs Proactive Audio

**What Google docs actually say:**
- "The documentation indicates no mutual exclusivity"
- Both can be enabled simultaneously on native audio models
- However, user reports suggest Google's web UI doesn't allow both at once

**Conclusion:** May be UI limitation, not API limitation. Needs testing.

### Turn Coverage - Subtle But Important

**Activity Only (default):**
- AI processes speech/text
- Ignores silence gaps
- More efficient token usage

**All Input:**
- AI processes EVERYTHING including silence
- Useful for detecting hesitation, pauses, emotion
- Uses more tokens

**For sales training:** Activity Only is correct (don't waste tokens on silence)

**For therapist AI:** All Input might be valuable (pauses/hesitation have meaning)

### Transcription is Independent

**Critical discovery:** Input and output transcription arrive as separate messages with NO ordering guarantees

**What this means:**
- Can't rely on transcription arriving before/after content
- UI must handle async updates
- Transcription might arrive late or out of order

**Implementation impact:**
- Store transcription separately in state
- Display asynchronously as it arrives
- Don't wait for transcription to update UI

---

## Default Values Summary

**Google's recommended defaults (if not specified):**

- **triggerTokens:** 80% of model's max context window
- **targetTokens:** triggerTokens / 2
- **turnCoverage:** TURN_INCLUDES_ONLY_ACTIVITY
- **thinkingBudget:** 0 (disabled)
- **affectiveDialogue:** false
- **proactiveAudio:** false
- **automaticActivityDetection:** enabled
- **activityHandling:** START_OF_ACTIVITY_INTERRUPTS

---

## Common Patterns

### Minimal Config (Google's example)

```typescript
const config = {
  responseModalities: [Modality.AUDIO],
  contextWindowCompression: {
    slidingWindow: {}  // Uses all defaults
  }
};
```

### Custom Config (Explicit values)

```typescript
const config = {
  responseModalities: [Modality.AUDIO],
  contextWindowCompression: {
    triggerTokens: 25600,
    slidingWindow: {
      targetTokens: 12800
    }
  },
  realtimeInputConfig: {
    turnCoverage: "TURN_INCLUDES_ONLY_ACTIVITY"
  },
  proactivity: {
    proactiveAudio: true
  },
  thinkingConfig: {
    thinkingBudget: -1
  }
};
```

---

**END OF API REFERENCE**

This document was extracted from Google's official documentation and represents their current (October 2025) API specification for the Gemini 2.5 Flash Native Audio Live API.
