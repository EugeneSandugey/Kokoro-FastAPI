/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { useState } from 'react';
import { useSettings } from '@/lib/state';
import './SystemPromptEditor.css';

interface SystemPromptEditorProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SystemPromptEditor({ isOpen, onClose }: SystemPromptEditorProps) {
  const { systemPrompt, setSystemPrompt } = useSettings();
  const [editedPrompt, setEditedPrompt] = useState(systemPrompt);

  if (!isOpen) return null;

  const handleSave = () => {
    setSystemPrompt(editedPrompt);
    onClose();
  };

  const handleCancel = () => {
    setEditedPrompt(systemPrompt); // Reset to original
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit System Prompt</h2>
          <button onClick={handleCancel} className="close-button">
            <span className="icon">close</span>
          </button>
        </div>
        <div className="modal-body">
          <textarea
            value={editedPrompt}
            onChange={(e) => setEditedPrompt(e.target.value)}
            className="system-prompt-textarea"
            placeholder="Enter system prompt..."
          />
        </div>
        <div className="modal-footer">
          <button onClick={handleCancel} className="button-secondary">
            Cancel
          </button>
          <button onClick={handleSave} className="button-primary">
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
