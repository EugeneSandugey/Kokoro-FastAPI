/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { useEffect, useRef, useState } from 'react';
import PopUp from '../popup/PopUp';
import WelcomeScreen from '../welcome-screen/WelcomeScreen';
// FIX: Import LiveServerContent to correctly type the content handler.
import { LiveConnectConfig, Modality, LiveServerContent } from '@google/genai';

import { useLiveAPIContext } from '../../../contexts/LiveAPIContext';
import {
  useSettings,
  useLogStore,
  useTools,
  ConversationTurn,
} from '@/lib/state';
import { AudioVisualizer } from '../../audio-visualizer/AudioVisualizer';

const formatTimestamp = (date: Date) => {
  const pad = (num: number, size = 2) => num.toString().padStart(size, '0');
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());
  const milliseconds = pad(date.getMilliseconds(), 3);
  return `${hours}:${minutes}:${seconds}.${milliseconds}`;
};

const renderContent = (text: string) => {
  // Split by ```json...``` code blocks
  const parts = text.split(/(`{3}json\n[\s\S]*?\n`{3})/g);

  return parts.map((part, index) => {
    if (part.startsWith('```json')) {
      const jsonContent = part.replace(/^`{3}json\n|`{3}$/g, '');
      return (
        <pre key={index}>
          <code>{jsonContent}</code>
        </pre>
      );
    }

    // Split by **bold** text
    const boldParts = part.split(/(\*\*.*?\*\*)/g);
    return boldParts.map((boldPart, boldIndex) => {
      if (boldPart.startsWith('**') && boldPart.endsWith('**')) {
        return <strong key={boldIndex}>{boldPart.slice(2, -2)}</strong>;
      }
      return boldPart;
    });
  });
};


export default function StreamingConsole() {
  const { client, setConfig } = useLiveAPIContext();
  const { systemPrompt, voice, thinkingMode, showThoughts, difficulty, turnCoverage, affectiveDialogue, proactiveAudio } = useSettings();
  const { tools } = useTools();
  const turns = useLogStore(state => state.turns);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showPopUp, setShowPopUp] = useState(false);
  const [expandedThoughts, setExpandedThoughts] = useState<Set<number>>(new Set());

  const handleClosePopUp = () => {
    setShowPopUp(false);
  };

  // Set the configuration for the Live API
  useEffect(() => {
    const enabledTools = tools
      .filter(tool => tool.isEnabled)
      .map(tool => ({
        functionDeclarations: [
          {
            name: tool.name,
            description: tool.description,
            parameters: tool.parameters,
          },
        ],
      }));

    // Always inject difficulty - use random number generator if "random" selected
    const actualDifficulty = difficulty === 'random'
      ? Math.floor(Math.random() * 10) + 1 // Random number 1-10
      : parseInt(difficulty);

    let finalSystemPrompt = systemPrompt;
    finalSystemPrompt += `\n\n🚨 CRITICAL INSTRUCTION: You MUST use difficulty ${actualDifficulty} for this session. The difficulty level is ${actualDifficulty}.`;


    // Using `any` for config to accommodate `speechConfig`, which is not in the
    // current TS definitions but is used in the working reference example.
    const config: any = {
      responseModalities: [Modality.AUDIO],
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: {
            voiceName: voice,
          },
        },
      },
      inputAudioTranscription: {},
      outputAudioTranscription: {},
      systemInstruction: {
        parts: [
          {
            text: finalSystemPrompt,
          },
        ],
      },
      tools: enabledTools,
    };

    // Add thinking config based on thinking mode
    if (thinkingMode) {
      config.thinkingConfig = {
        thinkingBudget: -1, // -1 = dynamic thinking (auto-adjusts based on complexity)
      };
    } else {
      config.thinkingConfig = {
        thinkingBudget: 0, // 0 = thinking disabled
      };
    }

    // Add turn coverage config
    config.realtimeInputConfig = {
      turnCoverage: turnCoverage,
    };

    // Add affective dialogue (requires v1alpha API - handled in LiveAPIContext)
    if (affectiveDialogue) {
      config.enable_affective_dialog = true;
    }

    // Add proactive audio config
    if (proactiveAudio) {
      config.proactivity = {
        proactiveAudio: true,
      };
    }

    // Enable session context compression (unlimited session time)
    // Default values from Google: trigger at 25,600 tokens, keep 12,800 after compression
    // This extends audio-only sessions beyond the 15-minute limit
    config.contextWindowCompression = {
      triggerTokens: 25600,      // Compress when context reaches 25.6K tokens
      slidingWindow: {
        targetTokens: 12800       // Keep 12.8K tokens after compression
      }
    };

    setConfig(config);
  }, [setConfig, systemPrompt, tools, voice, thinkingMode, difficulty, turnCoverage, affectiveDialogue, proactiveAudio]);

  useEffect(() => {
    const { addTurn, updateLastTurn } = useLogStore.getState();

    const handleInputTranscription = (text: string, isFinal: boolean) => {
      const turns = useLogStore.getState().turns;
      const last = turns[turns.length - 1];
      if (last && last.role === 'user' && !last.isFinal) {
        updateLastTurn({
          text: last.text + text,
          isFinal,
        });
      } else {
        addTurn({ role: 'user', text, isFinal });
      }
    };

    const handleOutputTranscription = (text: string, isFinal: boolean) => {
      const turns = useLogStore.getState().turns;
      const last = turns[turns.length - 1];
      if (last && last.role === 'agent' && !last.isFinal) {
        updateLastTurn({
          text: last.text + text,
          isFinal,
        });
      } else {
        addTurn({ role: 'agent', text, isFinal });
      }
    };

    // FIX: The 'content' event provides a single LiveServerContent object.
    // The function signature is updated to accept one argument, and groundingMetadata is extracted from it.
    const handleContent = (serverContent: LiveServerContent) => {
      const parts = serverContent.modelTurn?.parts || [];

      // Separate thoughts from regular text
      const thoughts = parts
        ?.filter((p: any) => p.thought)
        ?.map((p: any) => p.text)
        .filter(Boolean)
        .join(' ') ?? '';

      const text = parts
        ?.filter((p: any) => !p.thought)
        ?.map((p: any) => p.text)
        .filter(Boolean)
        .join(' ') ?? '';

      const groundingChunks = serverContent.groundingMetadata?.groundingChunks;

      if (!text && !groundingChunks && !thoughts) return;

      const turns = useLogStore.getState().turns;
      const last = turns.at(-1);

      if (last?.role === 'agent' && !last.isFinal) {
        const updatedTurn: Partial<ConversationTurn> = {
          text: last.text + text,
        };
        if (thoughts) {
          updatedTurn.thoughts = (last.thoughts || '') + thoughts;
        }
        if (groundingChunks) {
          updatedTurn.groundingChunks = [
            ...(last.groundingChunks || []),
            ...groundingChunks,
          ];
        }
        updateLastTurn(updatedTurn);
      } else {
        addTurn({ role: 'agent', text, isFinal: false, thoughts, groundingChunks });
      }
    };

    const handleTurnComplete = () => {
      const last = useLogStore.getState().turns.at(-1);
      if (last && !last.isFinal) {
        updateLastTurn({ isFinal: true });
      }
    };

    client.on('inputTranscription', handleInputTranscription);
    client.on('outputTranscription', handleOutputTranscription);
    client.on('content', handleContent);
    client.on('turncomplete', handleTurnComplete);

    return () => {
      client.off('inputTranscription', handleInputTranscription);
      client.off('outputTranscription', handleOutputTranscription);
      client.off('content', handleContent);
      client.off('turncomplete', handleTurnComplete);
    };
  }, [client]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [turns]);

  return (
    <div className="transcription-container">
      <AudioVisualizer />
      {showPopUp && <PopUp onClose={handleClosePopUp} />}
      {turns.length === 0 ? (
        <WelcomeScreen />
      ) : (
        <div className="transcription-view" ref={scrollRef}>
          {turns.map((t, i) => (
            <div
              key={i}
              className={`transcription-entry ${t.role} ${!t.isFinal ? 'interim' : ''
                }`}
            >
              <div className="transcription-header">
                <div className="transcription-source">
                  {t.role === 'user'
                    ? 'You'
                    : t.role === 'agent'
                      ? 'Agent'
                      : 'System'}
                </div>
              </div>
              <div className="transcription-text-content">
                {renderContent(t.text)}
              </div>
              {t.thoughts && thinkingMode && (
                <div className="thoughts-section">
                  <div
                    className="thoughts-header"
                    onClick={() => {
                      const newExpanded = new Set(expandedThoughts);
                      if (newExpanded.has(i)) {
                        newExpanded.delete(i);
                      } else {
                        newExpanded.add(i);
                      }
                      setExpandedThoughts(newExpanded);
                    }}
                  >
                    <span className="thoughts-icon">
                      {expandedThoughts.has(i) ? '▼' : '▶'}
                    </span>
                    <span className="thoughts-label">Thinking...</span>
                  </div>
                  {(showThoughts || expandedThoughts.has(i)) && (
                    <div className="thoughts-content">
                      {t.thoughts}
                    </div>
                  )}
                </div>
              )}
              {t.groundingChunks && t.groundingChunks.length > 0 && (
                <div className="grounding-chunks">
                  <strong>Sources:</strong>
                  <ul>
                    {t.groundingChunks
                      .filter(chunk => chunk.web)
                      .map((chunk, index) => (
                        <li key={index}>
                          <a
                            href={chunk.web!.uri}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {chunk.web!.title || chunk.web!.uri}
                          </a>
                        </li>
                      ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}