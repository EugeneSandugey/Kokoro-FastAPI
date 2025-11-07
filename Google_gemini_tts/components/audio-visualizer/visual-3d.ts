/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

// tslint:disable:organize-imports
// tslint:disable:ban-malformed-import-paths
// tslint:disable:no-new-decorators

import {LitElement, css, html} from 'lit';
import {customElement, property} from 'lit/decorators.js';
import {Analyser} from './analyser';

import * as THREE from 'three';
import {EXRLoader} from 'three/addons/loaders/EXRLoader.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {FXAAShader} from 'three/addons/shaders/FXAAShader.js';
import {fs as backdropFS, vs as backdropVS} from './backdrop-shader';
import {vs as sphereVS} from './sphere-shader';

/**
 * 3D live audio visual.
 */
@customElement('gdm-live-audio-visuals-3d')
export class GdmLiveAudioVisuals3D extends LitElement {
  private inputAnalyser!: Analyser;
  private outputAnalyser!: Analyser;
  private camera!: THREE.PerspectiveCamera;
  private backdrop!: THREE.Mesh;
  private composer!: EffectComposer;
  private sphere!: THREE.Mesh;
  private prevTime = 0;
  private rotation = new THREE.Vector3(0, 0, 0);
  private frameCount = 0;
  private targetColor = new THREE.Color(0x000010); // Target color to lerp to
  private targetOpacity = 1.0; // Target opacity to lerp to

  private _outputNode!: AudioNode;

  @property()
  set outputNode(node: AudioNode) {
    console.log('🔵 visual-3d: outputNode setter called', node);
    this._outputNode = node;
    this.outputAnalyser = new Analyser(this._outputNode);
    console.log('🔵 visual-3d: outputAnalyser created', this.outputAnalyser);
  }

  get outputNode() {
    return this._outputNode;
  }

  private _inputNode!: AudioNode;

  @property()
  set inputNode(node: AudioNode | null) {
    console.log('⚪ visual-3d: inputNode setter called', node);
    this._inputNode = node!;
    this.inputAnalyser = new Analyser(this._inputNode);
    console.log('⚪ visual-3d: inputAnalyser created, hasData:', this.inputAnalyser?.data?.length > 0);
  }

  get inputNode() {
    return this._inputNode;
  }

  private canvas!: HTMLCanvasElement;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
    }

    canvas {
      display: block;
      width: 100% !important;
      height: 100% !important;
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      image-rendering: pixelated;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
  }

  private init() {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x100c14);

    const backdrop = new THREE.Mesh(
      new THREE.IcosahedronGeometry(10, 5),
      new THREE.RawShaderMaterial({
        uniforms: {
          resolution: {value: new THREE.Vector2(1, 1)},
          rand: {value: 0},
        },
        vertexShader: backdropVS,
        fragmentShader: backdropFS,
        glslVersion: THREE.GLSL3,
      }),
    );
    backdrop.material.side = THREE.BackSide;
    scene.add(backdrop);
    this.backdrop = backdrop;

    // Get actual canvas dimensions - ensure we have valid dimensions
    const rect = this.canvas.getBoundingClientRect();
    const parentRect = this.canvas.parentElement?.getBoundingClientRect();
    const width = rect.width > 0 ? rect.width : (parentRect?.width || window.innerWidth);
    const height = rect.height > 0 ? rect.height : (parentRect?.height || window.innerHeight);

    console.log('Canvas init dimensions:', { width, height, rect, parentRect });

    const camera = new THREE.PerspectiveCamera(
      75,
      width / height,
      0.1,
      1000,
    );
    camera.position.set(0, 0, 5); // Camera centered
    this.camera = camera;

    const renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: !true,
    });

    // Set canvas size WITHOUT devicePixelRatio multiplication
    this.canvas.width = width;
    this.canvas.height = height;

    // Set renderer size to match canvas exactly, don't let it modify styles
    renderer.setSize(width, height, false);
    // Don't use devicePixelRatio - it causes dimension mismatches
    renderer.setPixelRatio(1);

    const viewport = renderer.getViewport(new THREE.Vector4());
    console.log('Renderer setup:', {
      cssSize: { width, height },
      canvasAttrs: { width: this.canvas.width, height: this.canvas.height },
      rendererSize: renderer.getSize(new THREE.Vector2()),
      viewport: { x: viewport.x, y: viewport.y, z: viewport.z, w: viewport.w }
    });

    // Explicitly set viewport to full canvas
    renderer.setViewport(0, 0, width, height);
    console.log('Forced viewport to:', 0, 0, width, height);

    const geometry = new THREE.IcosahedronGeometry(1, 10);

    new EXRLoader().load('piz_compressed.exr', (texture: THREE.Texture) => {
      texture.mapping = THREE.EquirectangularReflectionMapping;
      const exrCubeRenderTarget = pmremGenerator.fromEquirectangular(texture);
      sphereMaterial.envMap = exrCubeRenderTarget.texture;
      sphere.visible = true;
    });

    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();

    const sphereMaterial = new THREE.MeshStandardMaterial({
      color: 0x000010, // Original dark blue
      metalness: 0.5, // Original medium metallic
      roughness: 0.1, // Original smoothness
      emissive: 0x000010, // Original dark blue emissive
      emissiveIntensity: 1.5,
      transparent: true, // Enable transparency for white color
      opacity: 1.0, // Default full opacity (will change to 0.2 for white)
    });

    // Enable smooth color transitions (1 second fade)
    sphereMaterial.needsUpdate = true;

    sphereMaterial.onBeforeCompile = (shader) => {
      shader.uniforms.time = {value: 0};
      shader.uniforms.inputData = {value: new THREE.Vector4()};
      shader.uniforms.outputData = {value: new THREE.Vector4()};

      sphereMaterial.userData.shader = shader;

      shader.vertexShader = sphereVS;
    };

    const sphere = new THREE.Mesh(geometry, sphereMaterial);
    sphere.position.set(0, 0, 0); // Sphere at center
    scene.add(sphere);
    sphere.visible = true; // Make visible immediately, don't wait for EXR

    this.sphere = sphere;

    // Point camera at sphere immediately
    camera.lookAt(sphere.position);

    const renderPass = new RenderPass(scene, camera);

    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight),
      5, // Original constant bloom strength
      0.5,
      0,
    );

    const fxaaPass = new ShaderPass(FXAAShader);

    const composer = new EffectComposer(renderer);
    composer.addPass(renderPass);
    // composer.addPass(fxaaPass);
    composer.addPass(bloomPass);

    this.composer = composer;

    const onWindowResize = () => {
      const rect = this.canvas.getBoundingClientRect();
      const w = rect.width || window.innerWidth;
      const h = rect.height || window.innerHeight;

      // Set canvas size WITHOUT devicePixelRatio multiplication
      this.canvas.width = w;
      this.canvas.height = h;

      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      backdrop.material.uniforms.resolution.value.set(w, h);
      renderer.setSize(w, h, false);
      renderer.setPixelRatio(1); // Keep it at 1 to avoid dimension issues
      composer.setSize(w, h);
      fxaaPass.material.uniforms['resolution'].value.set(1 / w, 1 / h);

      const vp = renderer.getViewport(new THREE.Vector4());
      console.log('Resized:', {
        cssSize: { w, h },
        canvasAttrs: { width: this.canvas.width, height: this.canvas.height },
        viewport: { x: vp.x, y: vp.y, z: vp.z, w: vp.w }
      });

      // Explicitly set viewport to full canvas
      renderer.setViewport(0, 0, w, h);
    };

    window.addEventListener('resize', onWindowResize);
    // Force initial resize multiple times to ensure proper sizing
    setTimeout(onWindowResize, 50);
    setTimeout(onWindowResize, 200);
    setTimeout(onWindowResize, 500);

    this.animation();
  }

  private animation() {
    requestAnimationFrame(() => this.animation());

    if (this.inputAnalyser) {
      this.inputAnalyser.update();
    }
    if (this.outputAnalyser) {
      this.outputAnalyser.update();
    }

    // Debug: log audio levels every 60 frames (~1 second)
    this.frameCount++;
    if (this.frameCount % 60 === 0 && this.inputAnalyser && this.outputAnalyser) {
      const inputAvg = (this.inputAnalyser.data[0] + this.inputAnalyser.data[1] + this.inputAnalyser.data[2]) / 3;
      const outputAvg = (this.outputAnalyser.data[0] + this.outputAnalyser.data[1] + this.outputAnalyser.data[2]) / 3;
      const activeSource = inputAvg > outputAvg && inputAvg > 10 ? '⚪ USER' : outputAvg > 10 ? '🔵 AI' : '🟣 IDLE';
      console.log(`${activeSource} - Input: ${Math.round(inputAvg)}, Output: ${Math.round(outputAvg)}, Analysers valid: ${!!this.inputAnalyser.data.length}, ${!!this.outputAnalyser.data.length}`);
    }

    const t = performance.now();
    const dt = (t - this.prevTime) / (1000 / 60);
    this.prevTime = t;
    const backdropMaterial = this.backdrop.material as THREE.RawShaderMaterial;
    const sphereMaterial = this.sphere.material as THREE.MeshStandardMaterial;

    backdropMaterial.uniforms.rand.value = Math.random() * 10000;

    if (sphereMaterial.userData.shader && this.outputAnalyser && this.inputAnalyser) {
      // Get average levels for input and output
      const inputLevel = (this.inputAnalyser.data[0] + this.inputAnalyser.data[1] + this.inputAnalyser.data[2]) / 3;
      const outputLevel = (this.outputAnalyser.data[0] + this.outputAnalyser.data[1] + this.outputAnalyser.data[2]) / 3;

      // Determine target color and opacity based on who's talking
      if (outputLevel > 10) {
        // AI is talking - Original dark blue
        this.targetColor.setHex(0x000010);
        this.targetOpacity = 1.0;
        sphereMaterial.emissive.setHex(0x000010);
        sphereMaterial.emissiveIntensity = 1.5;
        sphereMaterial.metalness = 0.5;
        sphereMaterial.roughness = 0.1;
        this.sphere.scale.setScalar(1 + (0.2 * outputLevel) / 255);
      } else if (inputLevel > 10) {
        // User is talking - WHITE with 20% opacity
        this.targetColor.setHex(0xffffff);
        this.targetOpacity = 0.2;
        sphereMaterial.emissive.setHex(0x000010);
        sphereMaterial.emissiveIntensity = 1.5;
        this.sphere.scale.setScalar(1 + (0.2 * inputLevel) / 255);
      } else {
        // Idle - Original dark blue
        this.targetColor.setHex(0x000010);
        this.targetOpacity = 1.0;
        sphereMaterial.emissive.setHex(0x000010);
        sphereMaterial.emissiveIntensity = 1.5;
        this.sphere.scale.setScalar(1);
      }

      // Smoothly interpolate color and opacity towards target (1 second = 60 frames)
      // Lerp factor of 0.05 means ~20 frames to reach 50%, ~60 frames to reach 95%
      const lerpFactor = 0.05;
      sphereMaterial.color.lerp(this.targetColor, lerpFactor);
      sphereMaterial.opacity += (this.targetOpacity - sphereMaterial.opacity) * lerpFactor;

      // Rotation speed based on active speaker
      const f = 0.001;
      const rotationMultiplier = inputLevel > outputLevel ? 1.5 : 1.0; // Faster rotation when user speaks

      this.rotation.x += (dt * f * rotationMultiplier * this.outputAnalyser.data[1]) / 255;
      this.rotation.z += (dt * f * rotationMultiplier * this.inputAnalyser.data[1]) / 255;
      this.rotation.y += (dt * f * 0.5 * this.inputAnalyser.data[2]) / 255;
      this.rotation.y += (dt * f * 0.5 * this.outputAnalyser.data[2]) / 255;

      const euler = new THREE.Euler(
        this.rotation.x,
        this.rotation.y,
        this.rotation.z,
      );
      const quaternion = new THREE.Quaternion().setFromEuler(euler);
      const vector = new THREE.Vector3(0, 0, 5);
      vector.applyQuaternion(quaternion);
      this.camera.position.copy(vector);
      this.camera.lookAt(this.sphere.position);

      if (this.outputAnalyser && this.inputAnalyser) {
        sphereMaterial.userData.shader.uniforms.time.value +=
          (dt * 0.1 * this.outputAnalyser.data[0]) / 255;
        sphereMaterial.userData.shader.uniforms.inputData.value.set(
          (1 * this.inputAnalyser.data[0]) / 255,
          (0.1 * this.inputAnalyser.data[1]) / 255,
          (10 * this.inputAnalyser.data[2]) / 255,
          0,
        );
        sphereMaterial.userData.shader.uniforms.outputData.value.set(
          (2 * this.outputAnalyser.data[0]) / 255,
          (0.1 * this.outputAnalyser.data[1]) / 255,
          (10 * this.outputAnalyser.data[2]) / 255,
          0,
        );
      }
    }

    this.composer.render();
  }

  protected firstUpdated() {
    this.canvas = this.shadowRoot!.querySelector('canvas') as HTMLCanvasElement;
    console.log('firstUpdated - canvas:', this.canvas, 'parent:', this.canvas.parentElement);
    console.log('Host element dimensions:', {
      width: this.offsetWidth,
      height: this.offsetHeight,
      clientWidth: this.clientWidth,
      clientHeight: this.clientHeight
    });
    // Wait for layout to complete before initializing
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this.init();
      });
    });
  }

  protected render() {
    return html`<canvas></canvas>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'gdm-live-audio-visuals-3d': GdmLiveAudioVisuals3D;
  }
}
