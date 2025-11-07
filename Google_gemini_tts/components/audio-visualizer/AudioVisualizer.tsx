/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { useEffect, useRef, memo } from 'react';
import { useAudioNodes } from '../../contexts/AudioNodesContext';
import './visual-3d';

/**
 * React wrapper for the Lit Element 3D audio visualizer
 */
export const AudioVisualizer = memo(() => {
  const { audioRecorder, outputGainNode } = useAudioNodes();
  const elementRef = useRef<any>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    // Wait for the element to be fully initialized
    const setNodes = () => {
      // Set output node first (required)
      if (outputGainNode) {
        console.log('Setting output node:', outputGainNode);
        element.outputNode = outputGainNode;
      }

      // Set input node if available
      if (audioRecorder?.inputGainNode) {
        console.log('Setting input node:', audioRecorder.inputGainNode);
        element.inputNode = audioRecorder.inputGainNode;
      }
    };

    // Small delay to ensure Lit element is fully initialized
    setTimeout(setNodes, 100);

    // Also check periodically for input node changes (it's created when recording starts)
    const interval = setInterval(() => {
      if (element && audioRecorder) {
        if (audioRecorder.inputGainNode && element.inputNode !== audioRecorder.inputGainNode) {
          console.log('Setting/updating input node:', audioRecorder.inputGainNode);
          element.inputNode = audioRecorder.inputGainNode;
        } else if (!audioRecorder.inputGainNode && element.inputNode) {
          console.log('Clearing input node (recorder stopped)');
          element.inputNode = null;
        }
      }
    }, 500);

    return () => clearInterval(interval);
  }, [audioRecorder, outputGainNode]);

  return (
    <div style={{
      position: 'fixed',
      top: '-370px', // Move up 450px total (80px - 450px = -370px)
      left: '0',
      right: '0',
      bottom: '0',
      pointerEvents: 'none',
      zIndex: 1,
    }}>
      <gdm-live-audio-visuals-3d
        ref={elementRef}
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
        }}
      />
    </div>
  );
});

AudioVisualizer.displayName = 'AudioVisualizer';
