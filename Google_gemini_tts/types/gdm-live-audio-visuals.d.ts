/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
declare namespace JSX {
  interface IntrinsicElements {
    'gdm-live-audio-visuals-3d': React.DetailedHTMLProps<
      React.HTMLAttributes<HTMLElement> & {
        inputNode?: AudioNode;
        outputNode?: AudioNode;
      },
      HTMLElement
    >;
  }
}
