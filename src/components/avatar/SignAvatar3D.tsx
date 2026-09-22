import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  Play,
  Pause,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Palette,
  Sparkles,
  Maximize2,
  Minimize2,
  Loader2,
  AlertCircle,
  Shirt,
  Compass,
  Eye
} from 'lucide-react';

export type CameraPreset = 'front' | 'perspective' | 'hands' | 'top';
export type LightingPreset = 'neon' | 'studio' | 'cyber' | 'sunset';

const VALID_CAMERA_PRESETS: readonly CameraPreset[] = ['front', 'perspective', 'hands', 'top'] as const;
const VALID_LIGHTING_PRESETS: readonly LightingPreset[] = ['studio', 'neon', 'cyber', 'sunset'] as const;

function normalizeCameraPreset(preset?: string | null): CameraPreset {
  if (preset && (VALID_CAMERA_PRESETS as readonly string[]).includes(preset)) {
    return preset as CameraPreset;
  }
  return 'front';
}

function normalizeLightingPreset(preset?: string | null): LightingPreset {
  if (preset && (VALID_LIGHTING_PRESETS as readonly string[]).includes(preset)) {
    return preset as LightingPreset;
  }
  return 'studio';
}

interface LightingColors {
  ambient: number;
  dir: number;
  leftFill: number;
  rightFill: number;
}

const LIGHTING_PRESET_COLORS: Record<LightingPreset, LightingColors> = {
  studio: {
    ambient: 0xffffff,
    dir: 0xffffff,
    leftFill: 0xe2e8f0,
    rightFill: 0xffffff
  },
  neon: {
    ambient: 0xffffff,
    dir: 0xffffff,
    leftFill: 0x38bdf8,
    rightFill: 0x818cf8
  },
  cyber: {
    ambient: 0x06b6d4,
    dir: 0xffffff,
    leftFill: 0xec4899,
    rightFill: 0x10b981
  },
  sunset: {
    ambient: 0xf59e0b,
    dir: 0xffffff,
    leftFill: 0xf43f5e,
    rightFill: 0x8b5cf6
  }
};

export const SMPLX_VERTEX_COUNT = 10475;
export const SMPLX_FACE_COUNT = 20908;
export const DEFAULT_MOTION_FPS = 20;
const SIGNAVATAR_API_URL = 'http://127.0.0.1:8001';

interface TopologyGroup {
  start: number;
  count: number;
  materialIndex: number;
  name?: string;
}

interface TopologyData {
  vertexCount?: number;
  vertices?: number;
  faceCount?: number;
  faces: number[][] | number[];
  groups?: TopologyGroup[];
}

interface NormalizedMotion {
  frames: number;
  vertices: number;
  components: number;
  fps: number;
  data: Float32Array; // Flattened normalized coordinates: frames * 10475 * 3
}

// Map verified ISL signs to authentic BridgeConn motion keys
const SIGN_TO_MOTION_MAP: Record<string, string> = {
  WELCOME: 'welcome',
  GOOD: 'good',
  DRINK: 'drink',
  GO: 'go',
  HELP: 'help_2',
  HELP_2: 'help_2',
  TEACHER: 'teacher_2',
  TEACHER_2: 'teacher_2',
  ISHBOSHETH: 'ishbosheth',
  SAMPLE_1: 'sample_1',
  WELCOME_HELP_YOU: 'welcome_help_you',
  BOOK_DRINK_HOME: 'book_drink_home',
};

// Known authentic motion keys in inventory
const AUTHENTIC_MOTION_KEYS = new Set([
  'good',
  'drink',
  'go',
  'help',
  'help_2',
  'teacher',
  'teacher_2',
  'ishbosheth',
  'sample_1',
  'welcome_help_you',
  'book_drink_home',
]);

/** Parses the backend's globally converted and normalized Float32 motion binary. */
function processAndNormalizeMotion(
  buffer: ArrayBuffer,
  headerFrames?: number,
  headerFps?: number
): NormalizedMotion {
  if (!buffer || buffer.byteLength === 0) {
    throw new Error('Motion buffer is empty.');
  }

  const floatView = new Float32Array(buffer);
  const totalFloats = floatView.length;
  const floatsPerFrame = SMPLX_VERTEX_COUNT * 3;

  if (totalFloats % floatsPerFrame !== 0) {
    throw new Error(
      `Invalid motion binary length. Expected multiple of ${floatsPerFrame * 4} bytes (${floatsPerFrame} floats), received ${buffer.byteLength} bytes.`
    );
  }

  const computedFrames = totalFloats / floatsPerFrame;
  const frames = (headerFrames && headerFrames === computedFrames) ? headerFrames : computedFrames;

  if (frames <= 0) {
    throw new Error('Motion contains zero frames.');
  }

  for (let i = 0; i < totalFloats; i += 3) {
    if (!Number.isFinite(floatView[i]) || !Number.isFinite(floatView[i + 1]) || !Number.isFinite(floatView[i + 2])) {
      throw new Error('Motion data contains NaN or infinite coordinates.');
    }
  }

  const normalizedData = new Float32Array(floatView);

  return {
    frames,
    vertices: SMPLX_VERTEX_COUNT,
    components: 3,
    fps: headerFps || DEFAULT_MOTION_FPS,
    data: normalizedData,
  };
}

export interface SignAvatar3DProps {
  currentSign?: string;
  playbackSpeed?: number;
  isPlaying?: boolean;
  onTogglePlay?: () => void;
  onSpeedChange?: (speed: number) => void;
  onSignChange?: (sign: string) => void;
  onPreviousSign?: () => void;
  onNextSign?: () => void;
  showISLControls?: boolean;
  availableSigns?: { label: string; sign: string }[];
  generatedGifUrl?: string;
  generatedGifStatus?: 'idle' | 'loading' | 'loaded' | 'error';
  onGeneratedGifLoad?: () => void;
  onGeneratedGifError?: () => void;
  motionUrl?: string;
  motionSegments?: { word: string; frames: number }[];
  motionFps?: number;
  cameraPreset?: CameraPreset;
  onCameraPresetChange?: (preset: CameraPreset) => void;
  lightingPreset?: LightingPreset;
  onLightingPresetChange?: (preset: LightingPreset) => void;
  height?: string;
  className?: string;
}

export const SignAvatar3D: React.FC<SignAvatar3DProps> = ({
  currentSign = 'GOOD',
  playbackSpeed = 1,
  isPlaying = true,
  onTogglePlay,
  onSpeedChange,
  onSignChange,
  onPreviousSign,
  onNextSign,
  showISLControls = true,
  generatedGifUrl = '',
  generatedGifStatus = 'idle',
  onGeneratedGifLoad,
  onGeneratedGifError,
  motionUrl = '',
  motionSegments = [],
  motionFps = DEFAULT_MOTION_FPS,
  cameraPreset: propCameraPreset,
  onCameraPresetChange,
  lightingPreset: propLightingPreset,
  onLightingPresetChange,
  availableSigns = [
    { label: 'Welcome', sign: 'WELCOME' },
    { label: 'Good', sign: 'GOOD' },
    { label: 'Drink', sign: 'DRINK' },
    { label: 'Go', sign: 'GO' },
    { label: 'Help', sign: 'HELP' },
    { label: 'Teacher', sign: 'TEACHER' },
    { label: 'Ishbosheth', sign: 'ISHBOSHETH' },
    { label: 'Sample 1', sign: 'SAMPLE_1' },
    { label: 'Welcome Help You', sign: 'WELCOME_HELP_YOU' },
    { label: 'Book Drink Home', sign: 'BOOK_DRINK_HOME' },
  ],
  height = '480px',
  className = ''
}) => {
  // Dedicated mount container for Three.js canvas only (no React children inside)
  const mountRef = useRef<HTMLDivElement>(null);
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>(normalizeCameraPreset(propCameraPreset));
  const [lightingPreset, setLightingPreset] = useState<LightingPreset>(normalizeLightingPreset(propLightingPreset));
  const cameraPresetRef = useRef<CameraPreset>(normalizeCameraPreset(propCameraPreset));
  const lightingPresetRef = useRef<LightingPreset>(normalizeLightingPreset(propLightingPreset));
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [internalSpeed, setInternalSpeed] = useState(playbackSpeed);
  const [selectedSign, setSelectedSign] = useState(currentSign);

  // Status & Error state (pure React state, no direct DOM mutations)
  const [modelStatus, setModelStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [modelError, setModelError] = useState<string>('');
  const [motionInfo, setMotionInfo] = useState<{ frames: number; fps: number } | null>(null);

  // Three.js Scene References
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const avatarGroupRef = useRef<THREE.Group | null>(null);
  const avatarMeshRef = useRef<THREE.Mesh | null>(null);
  const geometryRef = useRef<THREE.BufferGeometry | null>(null);
  const lightsRef = useRef<{ [key: string]: THREE.Light }>({});

  // Animation & Motion State Refs (avoids scene recreation when props change)
  const motionDataRef = useRef<NormalizedMotion | null>(null);
  const topologyReadyRef = useRef<boolean>(false);
  const isPlayingRef = useRef<boolean>(isPlaying);
  const playbackSpeedRef = useRef<number>(playbackSpeed);
  const currentSignRef = useRef<string>(currentSign);
  const frameElapsedRef = useRef<number>(0);
  const currentFrameRef = useRef<number>(-1);

  // OrbitControls & Visual Customization
  const controlsRef = useRef<OrbitControls | null>(null);
  const [currentDisplayFrame, setCurrentDisplayFrame] = useState<number>(0);
  const [outfit, setOutfit] = useState<'blue_shirt' | 'white_shirt'>('blue_shirt');
  const shirtMaterialRef = useRef<THREE.MeshStandardMaterial | null>(null);

  const frameAvatarFromFront = useCallback(() => {
    const camera = cameraRef.current;
    const avatar = avatarGroupRef.current;
    const controls = controlsRef.current;
    if (!camera || !avatar) return;

    // SMPL-X Avatar centered at (0,0,0). Upper body signing space centered at Y ~ 0.18.
    camera.position.set(0, 0.22, 1.85);
    if (controls) {
      controls.target.set(0, 0.18, 0);
      controls.update();
    } else {
      camera.lookAt(0, 0.18, 0);
    }
    camera.updateProjectionMatrix();
  }, []);

  const handleResetCamera = useCallback(() => {
    frameAvatarFromFront();
    setCameraPreset('front');
    onCameraPresetChange?.('front');
  }, [frameAvatarFromFront, onCameraPresetChange]);

  /**
   * CAMERA PRESETS (Front, Perspective, Hands, Top) with OrbitControls target sync
   */
  const applyCameraPreset = useCallback((presetInput?: CameraPreset | string | null) => {
    const preset = normalizeCameraPreset(presetInput);
    cameraPresetRef.current = preset;
    setCameraPreset(preset);
    onCameraPresetChange?.(preset);
    const camera = cameraRef.current;
    const avatar = avatarGroupRef.current;
    const controls = controlsRef.current;
    if (!camera || !avatar) return;

    if (preset === 'front') {
      camera.position.set(0, 0.22, 1.85);
      if (controls) controls.target.set(0, 0.18, 0);
      else camera.lookAt(0, 0.18, 0);
      avatar.rotation.set(0, 0, 0);
    } else if (preset === 'perspective') {
      camera.position.set(0.48, 0.24, 1.80);
      if (controls) controls.target.set(0, 0.18, 0);
      else camera.lookAt(0, 0.18, 0);
      avatar.rotation.set(0, 0, 0);
    } else if (preset === 'hands') {
      // Zoomed in directly on upper torso, face, and hands
      camera.position.set(0, 0.20, 1.30);
      if (controls) controls.target.set(0, 0.18, 0);
      else camera.lookAt(0, 0.18, 0);
      avatar.rotation.set(0, 0, 0);
    } else if (preset === 'top') {
      camera.position.set(0, 0.55, 1.75);
      if (controls) controls.target.set(0, 0.18, 0);
      else camera.lookAt(0, 0.18, 0);
      avatar.rotation.set(0, 0, 0);
    }
    if (controls) controls.update();
    camera.updateProjectionMatrix();
  }, [onCameraPresetChange]);

  /**
   * LIGHTING PRESETS
   */
  const applyLightingPreset = useCallback((presetInput?: LightingPreset | string | null) => {
    const preset = normalizeLightingPreset(presetInput);
    lightingPresetRef.current = preset;
    setLightingPreset(preset);
    onLightingPresetChange?.(preset);

    const lights = lightsRef.current;
    if (!lights) return;

    const ambient = lights.ambient as THREE.AmbientLight | undefined;
    const dir = lights.dir as THREE.DirectionalLight | undefined;
    const leftFill = lights.leftFill as THREE.PointLight | undefined;
    const rightFill = lights.rightFill as THREE.PointLight | undefined;

    // Strict defensive check: verify all light instances and their .color property exist before accessing
    if (!ambient?.color || !dir?.color || !leftFill?.color || !rightFill?.color) {
      return;
    }

    const colors = LIGHTING_PRESET_COLORS[preset] ?? LIGHTING_PRESET_COLORS.studio;
    ambient.color.setHex(colors.ambient);
    dir.color.setHex(colors.dir);
    leftFill.color.setHex(colors.leftFill);
    rightFill.color.setHex(colors.rightFill);
  }, [onLightingPresetChange]);

  // Synchronize incoming camera & lighting preset props defensively
  useEffect(() => {
    if (propCameraPreset !== undefined) {
      applyCameraPreset(propCameraPreset);
    }
  }, [propCameraPreset, applyCameraPreset]);

  useEffect(() => {
    if (propLightingPreset !== undefined) {
      applyLightingPreset(propLightingPreset);
    }
  }, [propLightingPreset, applyLightingPreset]);

  // Synchronize playback & sign props to refs without re-rendering Three scene
  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  useEffect(() => {
    playbackSpeedRef.current = playbackSpeed;
    setInternalSpeed(playbackSpeed);
  }, [playbackSpeed]);

  useEffect(() => {
    currentSignRef.current = currentSign;
    setSelectedSign(currentSign);
  }, [currentSign]);

  // Synchronize outfit changes to shirt material in real-time
  useEffect(() => {
    if (shirtMaterialRef.current) {
      if (outfit === 'white_shirt') {
        shirtMaterialRef.current.color.setHex(0xf8fafc);
        shirtMaterialRef.current.roughness = 0.70;
      } else {
        shirtMaterialRef.current.color.setHex(0x2563eb);
        shirtMaterialRef.current.roughness = 0.76;
      }
      shirtMaterialRef.current.needsUpdate = true;
    }
  }, [outfit]);

  // Scrubbable frame seek handler for interactive timeline
  const handleSeekFrame = useCallback((frameTarget: number) => {
    const motion = motionDataRef.current;
    const geom = geometryRef.current;
    if (!motion || !geom) return;

    const validFrame = Math.max(0, Math.min(frameTarget, motion.frames - 1));
    frameElapsedRef.current = validFrame;
    currentFrameRef.current = validFrame;
    setCurrentDisplayFrame(validFrame);

    const offset = validFrame * SMPLX_VERTEX_COUNT * 3;
    const posAttr = geom.getAttribute('position') as THREE.BufferAttribute;
    if (posAttr) {
      (posAttr.array as Float32Array).set(
        motion.data.subarray(offset, offset + SMPLX_VERTEX_COUNT * 3)
      );
      posAttr.needsUpdate = true;
      geom.computeVertexNormals();
    }
  }, []);

  const handleRestartAnimation = useCallback(() => {
    handleSeekFrame(0);
  }, [handleSeekFrame]);

  /**
   * 1. LOAD TOPOLOGY (SMPL-X 10475 Vertices & 20908 Triangular Faces)
   */
  useEffect(() => {
    let cancelled = false;

    fetch('/models/smplx_neutral_topology.json')
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load SMPL-X topology: HTTP ${response.status}`);
        }
        return (await response.json()) as TopologyData;
      })
      .then((topology) => {
        if (cancelled) return;

        const vertexCount = topology.vertexCount || topology.vertices || SMPLX_VERTEX_COUNT;
        let facesArray: number[] = [];

        if (Array.isArray(topology.faces)) {
          if (topology.faces.length > 0 && Array.isArray(topology.faces[0])) {
            facesArray = (topology.faces as number[][]).flat();
          } else {
            facesArray = topology.faces as number[];
          }
        }

        const faceCount = topology.faceCount || Math.floor(facesArray.length / 3);

        if (vertexCount !== SMPLX_VERTEX_COUNT || faceCount !== SMPLX_FACE_COUNT) {
          throw new Error(
            `Invalid SMPL-X topology. Expected ${SMPLX_VERTEX_COUNT} vertices and ${SMPLX_FACE_COUNT} faces, received ${vertexCount} vertices and ${faceCount} faces.`
          );
        }

        const geom = geometryRef.current;
        if (geom) {
          geom.setIndex(new THREE.BufferAttribute(new Uint32Array(facesArray), 1));
          geom.clearGroups();
          if (topology.groups && Array.isArray(topology.groups)) {
            for (const g of topology.groups) {
              geom.addGroup(g.start, g.count, g.materialIndex);
            }
          }
          geom.computeVertexNormals();
        }

        topologyReadyRef.current = true;

        // If motion was already loaded before topology finished, render initial frame
        const motion = motionDataRef.current;
        if (motion && geom) {
          const posAttr = geom.getAttribute('position') as THREE.BufferAttribute;
          if (posAttr) {
            (posAttr.array as Float32Array).set(motion.data.subarray(0, SMPLX_VERTEX_COUNT * 3));
            posAttr.needsUpdate = true;
            geom.computeVertexNormals();
          }
          if (avatarMeshRef.current) avatarMeshRef.current.visible = true;
          frameAvatarFromFront();
          setModelStatus('ready');
          setModelError('');
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('[SignAvatar3D] Topology loading failed:', err);
          setModelError(err instanceof Error ? err.message : 'SMPL-X topology could not be loaded.');
          setModelStatus('error');
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  /**
   * 2. LOAD MOTION DATA (Dynamic Float32 Binary from GET /motion/{motion_name})
   */
  useEffect(() => {
    let cancelled = false;

    // Resolve motion URL
    const rawSign = (selectedSign || '').trim();
    const upperSign = rawSign.toUpperCase();
    const mapped = SIGN_TO_MOTION_MAP[upperSign] || (rawSign ? rawSign.toLowerCase() : '');

    let targetUrl = motionUrl;

    if (!targetUrl) {
      if (!mapped) return;
      targetUrl = `${SIGNAVATAR_API_URL}/motion/${mapped}`;
    }

    if (targetUrl.startsWith('/motion/')) {
      targetUrl = `${SIGNAVATAR_API_URL}${targetUrl}`;
    } else if (targetUrl.startsWith('/api/')) {
      targetUrl = `http://127.0.0.1:8000${targetUrl}`;
    }

    console.log('[SignAvatar3D] Selected sign:', upperSign || rawSign);
    console.log('[SignAvatar3D] Target Motion URL:', targetUrl);

    setModelStatus('loading');
    setModelError('');

    fetch(targetUrl)
      .then(async (res) => {
        if (!res.ok) {
          if (res.status === 404) {
            let errorMsg = `No matching BridgeConn motion available for: "${rawSign || selectedSign}"`;
            try {
              const errJson = await res.json();
              if (errJson?.detail?.error) errorMsg = errJson.detail.error;
              else if (errJson?.detail?.reason) errorMsg = errJson.detail.reason;
              else if (errJson?.error) errorMsg = errJson.error;
            } catch {
              // fallback
            }
            throw new Error(errorMsg);
          }
          throw new Error(`HTTP ${res.status}: Unable to fetch motion from ${targetUrl}`);
        }

        const headerFrames = Number(res.headers.get('X-Frames')) || undefined;
        const headerVertices = Number(res.headers.get('X-Vertices')) || undefined;
        const headerComponents = Number(res.headers.get('X-Components')) || undefined;
        const headerFpsVal = Number(res.headers.get('X-FPS')) || motionFps;

        if (headerVertices && headerVertices !== SMPLX_VERTEX_COUNT) {
          throw new Error(`Expected ${SMPLX_VERTEX_COUNT} vertices, received ${headerVertices}`);
        }
        if (headerComponents && headerComponents !== 3) {
          throw new Error(`Expected 3 coordinates per vertex, received ${headerComponents}`);
        }

        const buffer = await res.arrayBuffer();
        return { buffer, headerFrames, headerFpsVal };
      })
      .then(({ buffer, headerFrames, headerFpsVal }) => {
        if (cancelled) return;

        const motion = processAndNormalizeMotion(buffer, headerFrames, headerFpsVal);
        motionDataRef.current = motion;
        setMotionInfo({ frames: motion.frames, fps: motion.fps });
        frameElapsedRef.current = 0;
        currentFrameRef.current = -1;

        console.log(
          `[SignAvatar3D] Motion loaded successfully: ${motion.frames} frames × ${motion.vertices} vertices @ ${motion.fps} FPS (${buffer.byteLength} bytes)`
        );
        console.log('[SignAvatar3D] Frames:', motion.frames);
        console.log('[SignAvatar3D] MOTION', {
          frames: motion.frames,
          vertices: motion.vertices,
          fps: motion.fps,
        });

        const geom = geometryRef.current;
        if (geom) {
          const posAttr = geom.getAttribute('position') as THREE.BufferAttribute;
          if (posAttr) {
            (posAttr.array as Float32Array).set(motion.data.subarray(0, SMPLX_VERTEX_COUNT * 3));
            posAttr.needsUpdate = true;
            geom.computeVertexNormals();
          }
        }

        if (topologyReadyRef.current) {
          if (avatarMeshRef.current) avatarMeshRef.current.visible = true;
          frameAvatarFromFront();
          setModelStatus('ready');
          setModelError('');
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('[SignAvatar3D] Motion loading failed:', err);
          setModelError(err instanceof Error ? err.message : 'Unable to load SignAvatar motion.');
          setModelStatus('error');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [motionUrl, selectedSign, motionFps]);

  /**
   * 3. INITIALIZE THREE.JS SCENE (FRONT-FACING SIGNING STAGE)
   */
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // A. Scene setup
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.fog = new THREE.FogExp2(0x060918, 0.025);

    // B. Fixed face-to-face FRONT camera positioned to frame upper-body signing space.
    const camera = new THREE.PerspectiveCamera(
      36,
      container.clientWidth / (container.clientHeight || 1),
      0.1,
      100
    );
    camera.position.set(0, 0.22, 1.85);
    camera.lookAt(0, 0.18, 0);
    cameraRef.current = camera;

    // C. WebGL Renderer with High-Fidelity Tone Mapping & PCF Shadows
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;

    // Append ONLY renderer.domElement to dedicated empty mount container
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Interactive OrbitControls for 3D gesture inspection
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0.18, 0); // Center rotation around upper-body signing space
    controls.minDistance = 0.9;
    controls.maxDistance = 3.5;
    controls.maxPolarAngle = Math.PI / 2 + 0.15; // Prevent flipping under floor
    controlsRef.current = controls;

    // D. ACCESSIBLE SIGNING LIGHTING RIG (Crisp illumination on face, torso, and hands)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
    scene.add(ambientLight);

    // Direct front key light illuminating face and hand gestures
    const frontKeyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    frontKeyLight.position.set(0, 1.6, 3.2);
    frontKeyLight.castShadow = true;
    frontKeyLight.shadow.mapSize.width = 1024;
    frontKeyLight.shadow.mapSize.height = 1024;
    scene.add(frontKeyLight);

    // Left fill light for clear hand silhouette
    const leftFillLight = new THREE.PointLight(0x38bdf8, 1.8, 8);
    leftFillLight.position.set(-2.0, 0.6, 1.6);
    scene.add(leftFillLight);

    // Right fill light
    const rightFillLight = new THREE.PointLight(0xf8fafc, 1.8, 8);
    rightFillLight.position.set(2.0, 0.6, 1.6);
    scene.add(rightFillLight);

    // Subtle front chest light for hands
    const handFillLight = new THREE.PointLight(0xffffff, 1.2, 4);
    handFillLight.position.set(0, 0.18, 1.4);
    scene.add(handFillLight);

    // Floor glow
    const floorLight = new THREE.PointLight(0x06b6d4, 1.4, 6);
    floorLight.position.set(0, -1.0, 1.5);
    scene.add(floorLight);

    lightsRef.current = {
      ambient: ambientLight,
      dir: frontKeyLight,
      leftFill: leftFillLight,
      rightFill: rightFillLight,
      floor: floorLight
    };

    // Apply active lighting and camera presets now that Three.js objects are mounted
    applyLightingPreset(lightingPresetRef.current);
    applyCameraPreset(cameraPresetRef.current);

    // E. Holographic Stage Base at Ground Level (Feet at Y ~ -0.88)
    const stageGroup = new THREE.Group();
    stageGroup.position.set(0, -0.92, 0);

    const floorGeo = new THREE.CylinderGeometry(1.6, 1.65, 0.04, 64);
    const floorMat = new THREE.MeshPhysicalMaterial({
      color: 0x0a0f24,
      metalness: 0.85,
      roughness: 0.15,
      transmission: 0.6,
      transparent: true,
      opacity: 0.85,
      reflectivity: 0.9,
      clearcoat: 1.0,
      clearcoatRoughness: 0.08
    });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.receiveShadow = true;
    stageGroup.add(floorMesh);

    scene.add(stageGroup);

    // F. SMPL-X Avatar Mesh & Multi-Material Dressed Setup (Upright & Front-Facing)
    const avatarGroup = new THREE.Group();
    avatarGroupRef.current = avatarGroup;
    avatarGroup.position.set(0, 0, 0);
    avatarGroup.rotation.set(0, 0, 0);
    scene.add(avatarGroup);

    const geometry = new THREE.BufferGeometry();
    const initialPositions = new Float32Array(SMPLX_VERTEX_COUNT * 3);
    geometry.setAttribute('position', new THREE.BufferAttribute(initialPositions, 3));
    geometryRef.current = geometry;

    // Professional Dressed Outfit:
    // Material 0: Natural Human Skin Tone (Head, Neck, Forearms, Wrists, Hands, Fingers)
    const skinMaterial = new THREE.MeshStandardMaterial({
      color: 0xdec0a8, // Warm natural human skin tone
      roughness: 0.52,
      metalness: 0.04,
      side: THREE.FrontSide,
      flatShading: false
    });

    // Material 1: Professional Fitted Shirt (Chest, Torso, Shoulders, Upper Arms)
    const shirtColor = outfit === 'white_shirt' ? 0xf8fafc : 0x2563eb;
    const shirtMaterial = new THREE.MeshStandardMaterial({
      color: shirtColor,
      roughness: 0.76,
      metalness: 0.08,
      side: THREE.FrontSide,
      flatShading: false
    });
    shirtMaterialRef.current = shirtMaterial;

    // Material 2: Tailored Dark Charcoal Trousers (Pelvis, Hips, Legs, Shoes)
    const trousersMaterial = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.85,
      metalness: 0.04,
      side: THREE.FrontSide,
      flatShading: false
    });

    const avatarMesh = new THREE.Mesh(geometry, [skinMaterial, shirtMaterial, trousersMaterial]);
    avatarMesh.castShadow = true;
    avatarMesh.receiveShadow = true;
    avatarMesh.visible = false; // Becomes visible once topology & motion are loaded
    avatarGroup.add(avatarMesh);
    avatarMeshRef.current = avatarMesh;

    // H. Stable Animation Loop (Only vertices update, camera/controls handled smoothly)
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = Math.min(clock.getDelta(), 0.1);

      if (controlsRef.current) {
        controlsRef.current.update();
      }

      // Animate SMPL-X Mesh
      const motion = motionDataRef.current;
      const geom = geometryRef.current;

      if (motion && geom && topologyReadyRef.current) {
        if (isPlayingRef.current) {
          frameElapsedRef.current = (frameElapsedRef.current + delta * motion.fps * playbackSpeedRef.current) % motion.frames;
        }

        const frameIndex = Math.min(Math.floor(frameElapsedRef.current), motion.frames - 1);

        if (frameIndex !== currentFrameRef.current) {
          currentFrameRef.current = frameIndex;
          setCurrentDisplayFrame(frameIndex);
          const offset = frameIndex * SMPLX_VERTEX_COUNT * 3;
          const posAttr = geom.getAttribute('position') as THREE.BufferAttribute;

          if (posAttr) {
            (posAttr.array as Float32Array).set(
              motion.data.subarray(offset, offset + SMPLX_VERTEX_COUNT * 3)
            );
            posAttr.needsUpdate = true;
          }
        }
      }

      renderer.render(scene, camera);
    };

    animate();

    // I. Responsive Resize Observer
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      camera.aspect = container.clientWidth / (container.clientHeight || 1);
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // J. Cleanup on unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();

      if (controlsRef.current) {
        controlsRef.current.dispose();
        controlsRef.current = null;
      }

      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }

      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry?.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material?.dispose();
          }
        }
      });
      lightsRef.current = {};
      cameraRef.current = null;
      renderer.dispose();
    };
  }, []);

  const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];

  const handlePrevSign = () => {
    if (onPreviousSign) {
      onPreviousSign();
      return;
    }
    const idx = availableSigns.findIndex((s) => s.sign.toUpperCase() === selectedSign.toUpperCase());
    const prevIdx = idx > 0 ? idx - 1 : availableSigns.length - 1;
    onSignChange?.(availableSigns[prevIdx].sign);
  };

  const handleNextSign = () => {
    if (onNextSign) {
      onNextSign();
      return;
    }
    const idx = availableSigns.findIndex((s) => s.sign.toUpperCase() === selectedSign.toUpperCase());
    const nextIdx = idx < availableSigns.length - 1 ? idx + 1 : 0;
    onSignChange?.(availableSigns[nextIdx].sign);
  };

  return (
    <div
      className={`w-full rounded-[32px] glass-card border border-white/16 shadow-2xl flex flex-col select-none overflow-hidden ${
        isFullscreen ? 'fixed inset-4 z-50 h-[calc(100vh-32px)] max-w-none' : ''
      } ${className}`}
    >
      {/* 1. DEDICATED HEADER ROW */}
      <header className="px-6 py-4 border-b border-white/10 flex flex-wrap items-center justify-between gap-3 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-cyan-500/15 border border-cyan-400/30 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-cyan-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white tracking-tight uppercase">
                SignAvatar SMPL-X Stage
              </h2>
              <span className="text-[11px] font-mono text-cyan-300 font-semibold bg-white/8 px-2 py-0.5 rounded-md border border-white/10">
                {(motionUrl ? currentSign : selectedSign || currentSign || 'READY').toUpperCase()}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {motionInfo ? `10,475 Vertices • ${motionInfo.frames} Frames @ ${motionInfo.fps} FPS` : 'SMPL-X 10,475 Vertex Neutral Mesh'}
            </p>
          </div>
        </div>

        {/* Header Right: Controls & Status */}
        <div className="flex items-center gap-2">
          {/* Reset Camera Button */}
          <button
            onClick={handleResetCamera}
            className="px-2.5 py-1 rounded-xl glass-subtle hover:bg-white/10 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 transition-all"
            title="Reset Camera to Jury View"
          >
            <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Reset Camera</span>
          </button>

          {/* Outfit Toggle */}
          <button
            onClick={() => setOutfit((prev) => (prev === 'blue_shirt' ? 'white_shirt' : 'blue_shirt'))}
            className="px-2.5 py-1 rounded-xl glass-subtle hover:bg-white/10 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 transition-all"
            title="Toggle Outfit (Fitted Shirt & Dark Trousers)"
          >
            <Shirt className="w-3.5 h-3.5 text-blue-400" />
            <span className="hidden sm:inline">{outfit === 'blue_shirt' ? 'Blue Shirt' : 'White Shirt'}</span>
          </button>

          {/* Camera Angles */}
          <div className="hidden sm:flex items-center gap-1 p-1 rounded-xl glass-subtle border border-white/10">
            {(['front', 'hands', 'perspective'] as CameraPreset[]).map((p) => (
              <button
                key={p}
                onClick={() => applyCameraPreset(p)}
                className={`px-2 py-0.5 rounded-lg text-[11px] font-medium capitalize transition-all ${
                  cameraPreset === p
                    ? 'bg-white/20 text-white border border-white/25 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title={`Camera View: ${p}`}
              >
                {p === 'front' ? 'Default' : p === 'hands' ? 'Hands' : 'Angle'}
              </button>
            ))}
          </div>

          {/* Status Indicator */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
              modelStatus === 'error'
                ? 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
                : modelStatus === 'loading'
                ? 'bg-amber-500/10 border border-amber-500/30 text-amber-300'
                : 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                modelStatus === 'error'
                  ? 'bg-rose-400'
                  : modelStatus === 'loading'
                  ? 'bg-amber-300 animate-pulse'
                  : 'bg-emerald-400 animate-pulse'
              }`}
            />
            <span>{modelStatus === 'error' ? 'Unavailable' : modelStatus === 'loading' ? 'Loading' : 'Ready'}</span>
          </div>
        </div>
      </header>

      {/* 2. DEDICATED AVATAR CANVAS VIEWPORT */}
      <div
        style={{ height, minHeight: height, flex: '0 0 auto' }}
        className="w-full flex-1 cursor-grab active:cursor-grabbing overflow-hidden relative bg-black/20"
      >
        {/* Dedicated mount container for Three.js canvas ONLY (No React children) */}
        <div ref={mountRef} className="w-full h-full absolute inset-0" />

        {/* Floating Loading Indicator */}
        {modelStatus === 'loading' && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 bg-[#101735]/95 border border-cyan-500/40 px-4 py-2 rounded-full backdrop-blur-md shadow-lg pointer-events-none">
            <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
            <span className="text-xs font-semibold text-cyan-200">
              {!topologyReadyRef.current ? 'Loading SignAvatar...' : 'Preparing sign animation...'}
            </span>
          </div>
        )}

        {/* Floating Error Indicator */}
        {modelStatus === 'error' && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 bg-rose-950/85 border border-rose-500/40 px-4 py-2 rounded-full backdrop-blur-md shadow-lg pointer-events-none max-w-md text-center">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span className="text-xs font-semibold text-rose-200 truncate">
              {modelError || 'No sign animation available.'}
            </span>
          </div>
        )}

        {/* Orbit instruction subtle hint */}
        <div className="absolute bottom-3 right-3 z-10 hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-black/40 backdrop-blur-sm border border-white/5 pointer-events-none text-[10px] text-slate-400">
          <Compass className="w-3 h-3 text-cyan-400" />
          <span>Drag to orbit • Scroll to zoom</span>
        </div>
      </div>

      {/* 3. DEDICATED PLAYBACK TRANSPORT ROW */}
      <section className="px-6 py-3.5 border-t border-white/10 bg-[#0c122b]/80 backdrop-blur-sm flex flex-col gap-3">
        {/* Scrubbable Timeline Slider */}
        {motionInfo && motionInfo.frames > 0 && (
          <div className="w-full flex items-center gap-3">
            <span className="text-[11px] font-mono text-slate-400 min-w-[45px]">
              {((currentDisplayFrame) / (motionInfo.fps || DEFAULT_MOTION_FPS)).toFixed(1)}s
            </span>
            <input
              type="range"
              min={0}
              max={Math.max(0, motionInfo.frames - 1)}
              value={currentDisplayFrame}
              onChange={(e) => handleSeekFrame(Number(e.target.value))}
              className="flex-1 h-1.5 bg-slate-700/80 rounded-lg appearance-none cursor-pointer accent-cyan-400 hover:bg-slate-600 transition-colors"
              aria-label="Timeline scrubber"
            />
            <span className="text-[11px] font-mono text-slate-400 min-w-[45px] text-right">
              {((motionInfo.frames - 1) / (motionInfo.fps || DEFAULT_MOTION_FPS)).toFixed(1)}s
            </span>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {/* Play/Pause Button */}
            <button
              onClick={onTogglePlay}
              className="px-4 py-2 rounded-xl bg-white hover:bg-slate-100 text-black font-semibold text-xs flex items-center gap-1.5 shadow-md transition-transform active:scale-95"
              title={isPlaying ? 'Pause Gesture' : 'Play Gesture'}
            >
              {isPlaying ? <Pause className="w-4 h-4 fill-black" /> : <Play className="w-4 h-4 fill-black ml-0.5" />}
              <span>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>

            {/* Restart Button */}
            <button
              onClick={handleRestartAnimation}
              className="p-2 rounded-xl glass-subtle hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 transition-all active:scale-95"
              title="Restart Animation from Beginning"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Frame Indicator */}
            {motionInfo && motionInfo.frames > 0 && (
              <span className="text-[11px] font-mono text-slate-300 px-2.5 py-1 rounded-lg bg-white/5 border border-white/10">
                Frame {currentDisplayFrame + 1} / {motionInfo.frames}
              </span>
            )}
          </div>

          {/* Speed Controls */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-semibold">Speed:</span>
            <div className="flex items-center gap-1">
              {speeds.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setInternalSpeed(s);
                    onSpeedChange?.(s);
                  }}
                  className={`px-2 py-1 rounded-lg text-xs font-semibold font-mono transition-all ${
                    internalSpeed === s
                      ? 'bg-white/20 text-white border border-white/35 shadow-sm'
                      : 'glass-subtle text-slate-400 hover:text-white border border-white/8'
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 5. ISL TEST BUTTONS ROW */}
      {showISLControls && (
        <section className="px-6 py-4 border-t border-white/10 bg-white/[0.015] flex flex-col sm:flex-row sm:items-center gap-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex-shrink-0">
            Try Live ISL:
          </span>

          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-thin flex-1">
            {availableSigns.map((item) => {
              const isCurrent = !motionUrl && (selectedSign || currentSign).toUpperCase() === item.sign.toUpperCase();
              return (
                <button
                  key={item.sign}
                  onClick={() => {
                    setSelectedSign(item.sign);
                    onSignChange?.(item.sign);
                  }}
                  className={`flex-shrink-0 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                      isCurrent
                      ? 'bg-white/20 text-white border border-white/35 shadow-[0_0_12px_rgba(255,255,255,0.25)] scale-105'
                      : 'glass-subtle text-slate-300 hover:text-white hover:bg-white/10 border border-white/10'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
};
