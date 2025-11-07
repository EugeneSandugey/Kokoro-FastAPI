/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { createContext, FC, ReactNode, useContext, useState } from 'react';
import { AudioRecorder } from '../lib/audio-recorder';

export type AudioNodesContextType = {
  outputGainNode: GainNode | null;
  setOutputGainNode: (node: GainNode | null) => void;
  audioRecorder: AudioRecorder | null;
  setAudioRecorder: (recorder: AudioRecorder | null) => void;
};

const AudioNodesContext = createContext<AudioNodesContextType | undefined>(undefined);

export type AudioNodesProviderProps = {
  children: ReactNode;
};

export const AudioNodesProvider: FC<AudioNodesProviderProps> = ({ children }) => {
  const [outputGainNode, setOutputGainNode] = useState<GainNode | null>(null);
  const [audioRecorder, setAudioRecorder] = useState<AudioRecorder | null>(null);

  return (
    <AudioNodesContext.Provider value={{
      outputGainNode,
      setOutputGainNode,
      audioRecorder,
      setAudioRecorder,
    }}>
      {children}
    </AudioNodesContext.Provider>
  );
};

export const useAudioNodes = () => {
  const context = useContext(AudioNodesContext);
  if (!context) {
    throw new Error('useAudioNodes must be used within an AudioNodesProvider');
  }
  return context;
};
