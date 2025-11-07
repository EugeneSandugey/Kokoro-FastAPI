/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
/**
 * Analyser class for live audio visualisation.
 */
export class Analyser {
  private analyser: AnalyserNode | null = null;
  private bufferLength = 0;
  private dataArray: Uint8Array;

  constructor(node: AudioNode | null | undefined) {
    if (!node || !node.context) {
      // Create dummy data array for safety
      this.dataArray = new Uint8Array(16);
      return;
    }

    this.analyser = node.context.createAnalyser();
    this.analyser.fftSize = 32;
    this.bufferLength = this.analyser.frequencyBinCount;
    this.dataArray = new Uint8Array(this.bufferLength);
    node.connect(this.analyser);
  }

  update() {
    if (this.analyser) {
      this.analyser.getByteFrequencyData(this.dataArray);
    }
  }

  get data() {
    return this.dataArray;
  }
}
