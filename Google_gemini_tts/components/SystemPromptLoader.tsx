/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { useEffect } from 'react';
import { useSettings } from '@/lib/state';

const PROMPT_VERSION = '7'; // Increment this when prompt changes to force reload

// This component loads the system prompt from the markdown file on mount
export default function SystemPromptLoader() {
  const { setSystemPrompt } = useSettings();

  useEffect(() => {
    // Check the version of stored prompt
    const storedVersion = localStorage.getItem('systemPromptVersion');

    // If version doesn't match, force reload from file
    if (storedVersion !== PROMPT_VERSION) {
      console.log('System prompt version mismatch, reloading from file...');
      localStorage.removeItem('systemPrompt'); // Clear old prompt
      localStorage.setItem('systemPromptVersion', PROMPT_VERSION); // Update version
    }

    // Check if we already have the current version
    const stored = localStorage.getItem('systemPrompt');
    if (stored && storedVersion === PROMPT_VERSION) {
      // Already have current version
      return;
    }

    // Load the system prompt from the file
    fetch('/sales_roleplay_system_prompt.md')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to load system prompt');
        }
        return response.text();
      })
      .then(text => {
        setSystemPrompt(text);
        console.log('System prompt loaded from file');
      })
      .catch(error => {
        console.warn('Failed to load system prompt from file:', error);
      });
  }, [setSystemPrompt]);

  return null; // This component doesn't render anything
}
