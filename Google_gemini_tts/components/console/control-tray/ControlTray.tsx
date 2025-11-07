/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import cn from 'classnames';

import { memo, ReactNode, useEffect, useRef, useState } from 'react';
import { AudioRecorder } from '../../../lib/audio-recorder';
import { useSettings, useTools, useLogStore } from '@/lib/state';
import { AVAILABLE_VOICES } from '@/lib/constants';

import { useLiveAPIContext } from '../../../contexts/LiveAPIContext';
import { useAudioNodes } from '../../../contexts/AudioNodesContext';

export type ControlTrayProps = {
  children?: ReactNode;
};

function ControlTray({ children }: ControlTrayProps) {
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const connectButtonRef = useRef<HTMLButtonElement>(null);

  const { client, connected, connect, disconnect } = useLiveAPIContext();
  const { setAudioRecorder } = useAudioNodes();

  // Register audio recorder in context when it's created
  useEffect(() => {
    setAudioRecorder(audioRecorder);
    return () => setAudioRecorder(null);
  }, [audioRecorder, setAudioRecorder]);

  useEffect(() => {
    // FIX: Cannot find name 'connectButton'. Did you mean 'connectButtonRef'?
    if (!connected && connectButtonRef.current) {
      // FIX: Cannot find name 'connectButton'. Did you mean 'connectButtonRef'?
      connectButtonRef.current.focus();
    }
  }, [connected]);

  useEffect(() => {
    if (!connected) {
      setMuted(false);
    }
  }, [connected]);

  useEffect(() => {
    const onData = (base64: string) => {
      client.sendRealtimeInput([
        {
          mimeType: 'audio/pcm;rate=16000',
          data: base64,
        },
      ]);
    };
    if (connected && !muted && audioRecorder) {
      audioRecorder.on('data', onData);
      audioRecorder.start();
    } else {
      audioRecorder.stop();
    }
    return () => {
      audioRecorder.off('data', onData);
    };
  }, [connected, client, muted, audioRecorder]);

  const handleMicClick = () => {
    if (connected) {
      setMuted(!muted);
    } else {
      // If random voice is enabled, pick a random voice before connecting
      const { randomVoice, setVoice } = useSettings.getState();
      if (randomVoice) {
        const randomIndex = Math.floor(Math.random() * AVAILABLE_VOICES.length);
        setVoice(AVAILABLE_VOICES[randomIndex]);
      }
      connect();
    }
  };

  const handleExportLogs = () => {
    const { systemPrompt, model } = useSettings.getState();
    const { tools } = useTools.getState();
    const { turns } = useLogStore.getState();

    const logData = {
      configuration: {
        model,
        systemPrompt,
      },
      tools,
      conversation: turns.map(turn => ({
        ...turn,
        // Convert Date object to ISO string for JSON serialization
        timestamp: turn.timestamp.toISOString(),
      })),
    };

    const jsonString = JSON.stringify(logData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    a.href = url;
    a.download = `live-api-logs-${timestamp}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleNewSession = () => {
    // Clear chat history
    useLogStore.getState().clearTurns();

    // If connected, disconnect
    if (connected) {
      disconnect();
    }

    // If random voice is enabled, pick a new random voice
    const { randomVoice, setVoice } = useSettings.getState();
    if (randomVoice) {
      const randomIndex = Math.floor(Math.random() * AVAILABLE_VOICES.length);
      setVoice(AVAILABLE_VOICES[randomIndex]);
    }

    // Wait a moment then reconnect
    setTimeout(() => {
      connect();
    }, 500);
  };

  const micButtonTitle = connected
    ? muted
      ? 'Unmute microphone'
      : 'Mute microphone'
    : 'Connect and start microphone';

  const connectButtonTitle = connected ? 'Stop streaming' : 'Start streaming';

  return (
    <section className="control-tray">
      <nav className={cn('actions-nav')}>
        <button
          className={cn('action-button mic-button')}
          onClick={handleMicClick}
          title={micButtonTitle}
        >
          {!muted ? (
            <span className="material-symbols-outlined filled">mic</span>
          ) : (
            <span className="material-symbols-outlined filled">mic_off</span>
          )}
        </button>
        <button
          className={cn('action-button')}
          onClick={handleExportLogs}
          aria-label="Export Logs"
          title="Export session logs"
        >
          <span className="icon">download</span>
        </button>
        <button
          className={cn('action-button new-session-button')}
          onClick={handleNewSession}
          aria-label="New Session"
          title="Start new training session"
        >
          <span className="icon">add</span>
        </button>
        {children}
      </nav>

      <div className={cn('connection-container', { connected })}>
        <div className="connection-button-container">
          <button
            ref={connectButtonRef}
            className={cn('action-button connect-toggle', { connected })}
            onClick={() => {
              if (connected) {
                disconnect();
              } else {
                // If random voice is enabled, pick a random voice before connecting
                const { randomVoice, setVoice } = useSettings.getState();
                if (randomVoice) {
                  const randomIndex = Math.floor(Math.random() * AVAILABLE_VOICES.length);
                  setVoice(AVAILABLE_VOICES[randomIndex]);
                }
                connect();
              }
            }}
            title={connectButtonTitle}
          >
            <span className="material-symbols-outlined filled">
              {connected ? 'pause' : 'play_arrow'}
            </span>
          </button>
        </div>
        <span className="text-indicator">Streaming</span>
      </div>
    </section>
  );
}

export default memo(ControlTray);