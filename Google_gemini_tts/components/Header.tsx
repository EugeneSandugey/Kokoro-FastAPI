/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { useState } from 'react';
import { useSettings } from '@/lib/state';
import { AVAILABLE_VOICES } from '@/lib/constants';
import SystemPromptEditor from './SystemPromptEditor';
import './Header.css';

export default function Header() {
  const { voice, thinkingMode, showThoughts, difficulty, turnCoverage, affectiveDialogue, proactiveAudio, setVoice, setRandomVoice, setThinkingMode, setShowThoughts, setDifficulty, setTurnCoverage, setAffectiveDialogue, setProactiveAudio } = useSettings();
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [showOptionsPanel, setShowOptionsPanel] = useState(false);

  return (
    <header>
      <div className="header-left">
      </div>
      <div className="header-right">
        <button
          className="options-button"
          onClick={() => setShowOptionsPanel(!showOptionsPanel)}
          aria-label="Options"
          title="Options"
        >
          <span className="icon">more_vert</span>
        </button>

        {showOptionsPanel && (
          <div className="options-panel">
            <div className="option-item">
              <label className="option-label">Difficulty:</label>
              <select
                className="option-select"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
              >
                <option value="random">RANDOM</option>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                  <option key={n} value={n.toString()}>
                    {n}
                  </option>
                ))}
              </select>
            </div>

            <div className="option-item">
              <label className="option-label">Voice:</label>
              <select
                className="option-select"
                value={voice}
                onChange={(e) => {
                  setVoice(e.target.value);
                  // Update randomVoice flag based on selection
                  setRandomVoice(e.target.value === 'RANDOM');
                }}
              >
                {AVAILABLE_VOICES.map(v => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </div>

            <div className="option-item">
              <label className="option-label">Thinking:</label>
              <select
                className="option-select"
                value={thinkingMode ? (showThoughts ? 'show' : 'thinking') : 'none'}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === 'none') {
                    setThinkingMode(false);
                    setShowThoughts(false);
                  } else if (val === 'thinking') {
                    setThinkingMode(true);
                    setShowThoughts(false);
                  } else if (val === 'show') {
                    setThinkingMode(true);
                    setShowThoughts(true);
                  }
                }}
              >
                <option value="none">No Thinking</option>
                <option value="thinking">Thinking</option>
                <option value="show">Show Thoughts</option>
              </select>
            </div>

            <div className="option-item">
              <label className="option-label">Turn Coverage:</label>
              <select
                className="option-select"
                value={turnCoverage}
                onChange={(e) => setTurnCoverage(e.target.value)}
              >
                <option value="TURN_INCLUDES_ONLY_ACTIVITY">Activity Only</option>
                <option value="TURN_INCLUDES_ALL_INPUT">All Input</option>
              </select>
            </div>

            <div className="option-item">
              <label className="option-label">
                <input
                  type="checkbox"
                  checked={affectiveDialogue}
                  onChange={(e) => setAffectiveDialogue(e.target.checked)}
                />
                <span style={{ marginLeft: '8px' }}>Affective Dialogue</span>
              </label>
            </div>

            <div className="option-item">
              <label className="option-label">
                <input
                  type="checkbox"
                  checked={proactiveAudio}
                  onChange={(e) => setProactiveAudio(e.target.checked)}
                />
                <span style={{ marginLeft: '8px' }}>Proactive Audio</span>
              </label>
            </div>

            <div className="option-item">
              <button
                className="option-button"
                onClick={() => {
                  setShowPromptEditor(true);
                  setShowOptionsPanel(false);
                }}
              >
                Edit System Prompt
              </button>
            </div>
          </div>
        )}
      </div>
      <SystemPromptEditor
        isOpen={showPromptEditor}
        onClose={() => setShowPromptEditor(false)}
      />
    </header>
  );
}