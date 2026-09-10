import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
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
  AlertCircle
} from 'lucide-react';

export type CameraPreset = 'front' | 'perspective' | 'hands' | 'top';
export type LightingPreset = 'neon' | 'studio' | 'cyber' | 'sunset';

export const SMPLX_VERTEX_COUNT = 10475;
export const SMPLX_FACE_COUNT = 20908;
export const DEFAULT_MOTION_FPS = 20;
const SIGNAVATAR_API_URL = 'http://127.0.0.1:8001';

interface TopologyData {
  vertexCount?: number;
  vertices?: number;
  faceCount?: number;
  faces: number[][] | number[];
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
  GOOD: 'good',
  DRINK: 'drink',
  GO: 'go',
  HELP: 'help_2',
  TEACHER: 'teacher_2',
  ISHBOSHETH: 'ishbosheth',
  SAMPLE_1: 'sample_1',
  WELCOME_HELP_YOU: 'welcome_help_you',
  BOOK_DRINK_HOME: 'book_drink_home',
};

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
  availableSigns = [
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
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>('front');
  const [lightingPreset, setLightingPreset] = useState<LightingPreset>('studio');
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

  const frameAvatarFromFront = () => {
    const camera = cameraRef.current;
    const avatar = avatarGroupRef.current;
    if (!camera || !avatar) return;

    const box = new THREE.Box3().setFromObject(avatar);
    console.log('AVATAR BOUNDS', box.min, box.max);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const verticalExtent = Math.max(size.y, 0.1);
    const horizontalExtent = Math.max(size.x, 0.1);
    const verticalDistance = verticalExtent / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    const horizontalDistance = horizontalExtent / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * Math.max(camera.aspect, 0.1));
    const distance = Math.max(verticalDistance, horizontalDistance) * 1.2;
    camera.position.set(0, 1.55, Math.max(distance, 4.5));
    camera.lookAt(0, center.y, 0);
    camera.updateProjectionMatrix();
    console.log('[SignAvatar3D] CAMERA', {
      position: camera.position.toArray(),
      target: [0, center.y, 0],
      fov: camera.fov,
    });
    console.log('[SignAvatar3D] AVATAR', {
      position: avatar.position.toArray(),
      rotation: avatar.rotation.toArray(),
      scale: avatar.scale.toArray(),
    });
    console.log('[SignAvatar3D] BOUNDS', {
      min: box.min.toArray(),
      max: box.max.toArray(),
      center: center.toArray(),
      size: size.toArray(),
    });
  };

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
    const mapped = SIGN_TO_MOTION_MAP[selectedSign.toUpperCase()];
    if (!motionUrl && !mapped) {
      console.warn(`[SignAvatar3D] No real animation available for sign: ${selectedSign}`);
      setModelStatus('error');
      setModelError(`Sign animation unavailable for: ${selectedSign.toUpperCase()}`);
      return;
    }

    let targetUrl = motionUrl || `${SIGNAVATAR_API_URL}/motion/${mapped}`;
    if (targetUrl.startsWith('/motion/')) {
      targetUrl = `${SIGNAVATAR_API_URL}${targetUrl}`;
    } else if (targetUrl.startsWith('/api/')) {
      targetUrl = `http://127.0.0.1:8000${targetUrl}`;
    }

    console.log('[SignAvatar3D] Selected sign:', selectedSign.toUpperCase());
    console.log('[SignAvatar3D] Motion URL:', targetUrl);

    setModelStatus('loading');
    setModelError('');

    fetch(targetUrl)
      .then(async (res) => {
        if (!res.ok) {
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

    // B. Fixed face-to-face FRONT camera. The viewer stays on the front Z axis.
    const camera = new THREE.PerspectiveCamera(
      40,
      container.clientWidth / (container.clientHeight || 1),
      0.1,
      100
    );
    camera.position.set(0, 1.55, 4.5);
    camera.lookAt(0, 0, 0);
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

    // D. ACCESSIBLE SIGNING LIGHTING RIG (Crisp illumination on face, torso, and hands)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
    scene.add(ambientLight);

    // Direct front key light illuminating face and hand gestures
    const frontKeyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    frontKeyLight.position.set(0, 1.8, 4.0);
    frontKeyLight.castShadow = true;
    frontKeyLight.shadow.mapSize.width = 1024;
    frontKeyLight.shadow.mapSize.height = 1024;
    scene.add(frontKeyLight);

    // Left fill light for clear hand silhouette
    const leftFillLight = new THREE.PointLight(0x38bdf8, 1.8, 10);
    leftFillLight.position.set(-2.5, 1.2, 2.5);
    scene.add(leftFillLight);

    // Right fill light
    const rightFillLight = new THREE.PointLight(0x818cf8, 1.8, 10);
    rightFillLight.position.set(2.5, 1.2, 2.5);
    scene.add(rightFillLight);

    // Floor glow
    const floorLight = new THREE.PointLight(0x06b6d4, 1.6, 6);
    floorLight.position.set(0, -1.5, 1.5);
    scene.add(floorLight);

    lightsRef.current = {
      ambient: ambientLight,
      dir: frontKeyLight,
      leftFill: leftFillLight,
      rightFill: rightFillLight,
      floor: floorLight
    };

    // E. Holographic Stage Base at Ground Level
    const stageGroup = new THREE.Group();
    stageGroup.position.set(0, -1.62, 0);

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

    // F. SMPL-X Avatar Mesh & Geometry Creation (Upright & Front-Facing)
    const avatarGroup = new THREE.Group();
    avatarGroupRef.current = avatarGroup;
    avatarGroup.position.set(0, 0, 0); // Positioned stably in world coordinates
    avatarGroup.rotation.set(0, 0, 0); // Directly facing viewer
    scene.add(avatarGroup);

    const geometry = new THREE.BufferGeometry();
    const initialPositions = new Float32Array(SMPLX_VERTEX_COUNT * 3);
    geometry.setAttribute('position', new THREE.BufferAttribute(initialPositions, 3));
    geometryRef.current = geometry;

    // High-visibility human signer material with distinct hand/finger definition
    const avatarMaterial = new THREE.MeshStandardMaterial({
      color: 0x4fa8e8,
      roughness: 0.55,
      metalness: 0.08,
      side: THREE.DoubleSide,
      flatShading: false
    });

    const avatarMesh = new THREE.Mesh(geometry, avatarMaterial);
    avatarMesh.castShadow = true;
    avatarMesh.receiveShadow = true;
    avatarMesh.visible = false; // Becomes visible once topology & motion are loaded
    avatarGroup.add(avatarMesh);
    avatarMeshRef.current = avatarMesh;

    const domElem = renderer.domElement;

    // H. Stable Animation Loop (Only vertices update, camera/avatar stay fixed)
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = Math.min(clock.getDelta(), 0.1);

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
          const offset = frameIndex * SMPLX_VERTEX_COUNT * 3;
          const posAttr = geom.getAttribute('position') as THREE.BufferAttribute;

          if (frameIndex % 20 === 0 || frameIndex === motion.frames - 1) {
            console.log(`[SignAvatar3D] playback frame: ${frameIndex}`);
          }

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

      // Remove renderer element safely if still child of container
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
      renderer.dispose();
    };
  }, []);

  /**
   * CAMERA PRESETS (All Front/Face-to-Face focused, no overhead or distorted angles)
   */
  const applyCameraPreset = useCallback((preset: CameraPreset) => {
    setCameraPreset(preset);
    const camera = cameraRef.current;
    const avatar = avatarGroupRef.current;
    if (!camera || !avatar) return;

    if (preset === 'front') {
      camera.position.set(0, 1.55, 4.5);
      camera.lookAt(0, 0, 0);
      avatar.rotation.set(0, 0, 0);
    } else if (preset === 'perspective') {
      // Mild natural perspective angle
      camera.position.set(0.6, 0.5, 4.3);
      camera.lookAt(0, 0.35, 0);
      avatar.rotation.set(0, 0, 0);
    } else if (preset === 'hands') {
      camera.position.set(0, 1.55, 3.2);
      camera.lookAt(0, 1.45, 0);
      avatar.rotation.set(0, 0, 0);
    } else if (preset === 'top') {
      // Gentle high angle
      camera.position.set(0, 2.0, 3.9);
      camera.lookAt(0, 0.25, 0);
      avatar.rotation.set(0, 0, 0);
    }
  }, []);

  /**
   * LIGHTING PRESETS
   */
  const applyLightingPreset = useCallback((preset: LightingPreset) => {
    setLightingPreset(preset);
    const lights = lightsRef.current;
    if (!lights) return;

    if (preset === 'studio') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0xffffff);
      (lights.dir as THREE.DirectionalLight).color.setHex(0xffffff);
      (lights.leftFill as THREE.PointLight).color.setHex(0xe2e8f0);
      (lights.rightFill as THREE.PointLight).color.setHex(0xffffff);
    } else if (preset === 'neon') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0xffffff);
      (lights.dir as THREE.DirectionalLight).color.setHex(0xffffff);
      (lights.leftFill as THREE.PointLight).color.setHex(0x38bdf8);
      (lights.rightFill as THREE.PointLight).color.setHex(0x818cf8);
    } else if (preset === 'cyber') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0x06b6d4);
      (lights.dir as THREE.DirectionalLight).color.setHex(0xffffff);
      (lights.leftFill as THREE.PointLight).color.setHex(0xec4899);
      (lights.rightFill as THREE.PointLight).color.setHex(0x10b981);
    } else if (preset === 'sunset') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0xf59e0b);
      (lights.dir as THREE.DirectionalLight).color.setHex(0xffffff);
      (lights.leftFill as THREE.PointLight).color.setHex(0xf43f5e);
      (lights.rightFill as THREE.PointLight).color.setHex(0x8b5cf6);
    }
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
                {selectedSign.toUpperCase()}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {motionInfo ? `10,475 Vertices • ${motionInfo.frames} Frames @ ${motionInfo.fps} FPS` : 'SMPL-X 10,475 Vertex Neutral Mesh'}
            </p>
          </div>
        </div>

        {/* Header Right: Controls & Status */}
        <div className="flex items-center gap-2.5">
          {/* Camera Angles */}
          <div className="hidden sm:flex items-center gap-1 p-1 rounded-xl glass-subtle border border-white/10">
            {(['front', 'perspective', 'hands', 'top'] as CameraPreset[]).map((p) => (
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
                {p}
              </button>
            ))}
          </div>

          {/* Lighting Preset Picker */}
          <button
            onClick={() => {
              const presets: LightingPreset[] = ['studio', 'neon', 'cyber', 'sunset'];
              const next = presets[(presets.indexOf(lightingPreset) + 1) % presets.length];
              applyLightingPreset(next);
            }}
            className="p-1.5 rounded-xl glass-subtle hover:bg-white/10 text-slate-400 hover:text-white border border-white/10 transition-all"
            title={`Lighting Theme: ${lightingPreset}`}
          >
            <Palette className="w-4 h-4" />
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-xl glass-subtle hover:bg-white/10 text-slate-400 hover:text-white border border-white/10 transition-all"
            title="Toggle Stage Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

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
            <span>{modelStatus === 'error' ? 'Error' : modelStatus === 'loading' ? 'Loading' : 'Ready'}</span>
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

        {/* Loading Overlay (React-managed sibling) */}
        {modelStatus === 'loading' && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[2px] px-6 text-center pointer-events-none space-y-2">
            <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
            <p className="text-sm font-semibold text-cyan-200">
              Loading SignAvatar...
            </p>
            <p className="text-xs text-slate-400 font-mono">
              Fetching SMPL-X Mesh & Motion Stream
            </p>
          </div>
        )}

        {/* Error Overlay (React-managed sibling) */}
        {modelStatus === 'error' && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/60 backdrop-blur-[2px] px-6 text-center pointer-events-none space-y-2">
            <AlertCircle className="w-7 h-7 text-rose-400" />
            <p className="text-sm font-semibold text-rose-300">
              {modelError || 'Unable to load SignAvatar motion.'}
            </p>
            <p className="text-xs text-slate-400">
              Please check backend API at {SIGNAVATAR_API_URL}
            </p>
          </div>
        )}

        {/* Optional GIF Overlay if explicitly provided and loaded */}
        {generatedGifUrl && generatedGifStatus !== 'error' && (
          <div className="absolute inset-4 z-10 hidden items-center justify-center rounded-2xl overflow-hidden bg-black/40 pointer-events-none">
            <img
              src={generatedGifUrl}
              alt={`Generated sign language animation for ${currentSign}`}
              className="max-w-full max-h-full object-contain"
              onLoad={onGeneratedGifLoad}
              onError={onGeneratedGifError}
            />
          </div>
        )}
      </div>

      {/* 3. DEDICATED PLAYBACK TRANSPORT ROW */}
      <section className="px-6 py-3.5 border-t border-white/10 bg-white/[0.02] flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {/* Previous Sign */}
          <button
            onClick={handlePrevSign}
            className="px-3 py-2 rounded-xl glass-subtle hover:bg-white/10 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1 transition-all active:scale-95"
            title="Previous Sign"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Previous</span>
          </button>

          {/* Reset Orientation */}
          <button
            onClick={() => {
              if (avatarGroupRef.current) avatarGroupRef.current.rotation.set(0, 0, 0);
              applyCameraPreset('front');
            }}
            className="p-2 rounded-xl glass-subtle hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 transition-all"
            title="Reset Avatar Front Orientation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Play/Pause Button */}
          <button
            onClick={onTogglePlay}
            className="px-4 py-2 rounded-xl bg-white hover:bg-slate-100 text-black font-semibold text-xs flex items-center gap-1.5 shadow-md transition-transform active:scale-95"
            title={isPlaying ? 'Pause Gesture' : 'Play Gesture'}
          >
            {isPlaying ? <Pause className="w-4 h-4 fill-black" /> : <Play className="w-4 h-4 fill-black ml-0.5" />}
            <span>{isPlaying ? 'Pause' : 'Play'}</span>
          </button>

          {/* Next Sign */}
          <button
            onClick={handleNextSign}
            className="px-3 py-2 rounded-xl glass-subtle hover:bg-white/10 text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1 transition-all active:scale-95"
            title="Next Sign"
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* 4. SPEED CONTROLS ROW */}
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
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold font-mono transition-all ${
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
      </section>

      {/* 5. ISL TEST BUTTONS ROW */}
      {showISLControls && (
        <section className="px-6 py-4 border-t border-white/10 bg-white/[0.015] flex flex-col sm:flex-row sm:items-center gap-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex-shrink-0">
            Try Live ISL:
          </span>

          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-thin flex-1">
            {availableSigns.map((item) => {
              const isCurrent = currentSign.toUpperCase() === item.sign.toUpperCase();
              return (
                <button
                  key={item.sign}
                  onClick={() => {
                    setSelectedSign(item.sign);
                    onSignChange?.(item.sign);
                  }}
                  className={`flex-shrink-0 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                      selectedSign.toUpperCase() === item.sign.toUpperCase()
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
