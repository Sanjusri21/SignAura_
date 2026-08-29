import React, { useEffect, useRef, useState } from 'react';
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
  Sliders,
  CheckCircle2
} from 'lucide-react';

export type CameraPreset = 'front' | 'perspective' | 'hands' | 'top';
export type LightingPreset = 'neon' | 'studio' | 'cyber' | 'sunset';

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
  height?: string;
  className?: string;
}

export const SignAvatar3D: React.FC<SignAvatar3DProps> = ({
  currentSign = 'HELLO',
  playbackSpeed = 1,
  isPlaying = true,
  onTogglePlay,
  onSpeedChange,
  onSignChange,
  onPreviousSign,
  onNextSign,
  showISLControls = true,
  availableSigns = [
    { label: 'Hello', sign: 'HELLO' },
    { label: 'Welcome', sign: 'WELCOME' },
    { label: 'Thank You', sign: 'THANK_YOU' },
    { label: 'How Are You', sign: 'HOW_ARE_YOU' },
    { label: 'Sign Language', sign: 'SIGN_LANGUAGE' },
    { label: 'Accessible', sign: 'ACCESSIBLE' },
    { label: 'India', sign: 'INDIA' },
    { label: 'Help', sign: 'HELP' },
    { label: 'Doctor', sign: 'DOCTOR' }
  ],
  height = '440px',
  className = ''
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>('front');
  const [lightingPreset, setLightingPreset] = useState<LightingPreset>('neon');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [internalSpeed, setInternalSpeed] = useState(playbackSpeed);

  // References for Three.js state
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const avatarGroupRef = useRef<THREE.Group | null>(null);
  const jointsRef = useRef<{ [key: string]: THREE.Object3D }>({});
  const particlesRef = useRef<THREE.Points | null>(null);
  const lightsRef = useRef<{ [key: string]: THREE.Light }>({});
  const animTimeRef = useRef<number>(0);
  const activeSignRef = useRef<string>(currentSign);

  useEffect(() => {
    activeSignRef.current = currentSign;
  }, [currentSign]);

  useEffect(() => {
    setInternalSpeed(playbackSpeed);
  }, [playbackSpeed]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. SCENE SETUP
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.fog = new THREE.FogExp2(0x04060a, 0.038);

    // 2. CAMERA SETUP
    const camera = new THREE.PerspectiveCamera(
      42,
      container.clientWidth / (container.clientHeight || 1),
      0.1,
      100
    );
    camera.position.set(0, 1.35, 2.7);
    cameraRef.current = camera;

    // 3. HIGH FIDELITY WEBGL RENDERER
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
    renderer.toneMappingExposure = 1.3;
    container.replaceChildren(renderer.domElement);
    rendererRef.current = renderer;

    // 4. LIGHTING RIG
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.9);
    dirLight.position.set(2.5, 4.5, 3.5);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    scene.add(dirLight);

    const purpleRimLight = new THREE.PointLight(0x8b5cf6, 3.2, 10);
    purpleRimLight.position.set(-2.5, 2.2, -1.5);
    scene.add(purpleRimLight);

    const cyanRimLight = new THREE.PointLight(0x38bdf8, 3.2, 10);
    cyanRimLight.position.set(2.5, 2.2, -1.5);
    scene.add(cyanRimLight);

    const floorLight = new THREE.PointLight(0x06b6d4, 2.2, 6);
    floorLight.position.set(0, 0.1, 0);
    scene.add(floorLight);

    lightsRef.current = {
      ambient: ambientLight,
      dir: dirLight,
      purple: purpleRimLight,
      cyan: cyanRimLight,
      floor: floorLight
    };

    // 5. HOLOGRAPHIC PRESENTATION PLATFORM & GLASS STAGE
    const stageGroup = new THREE.Group();

    // Circular translucent glass stage base
    const floorGeo = new THREE.CylinderGeometry(1.65, 1.7, 0.05, 64);
    const floorMat = new THREE.MeshPhysicalMaterial({
      color: 0x0a0f24,
      metalness: 0.85,
      roughness: 0.12,
      transmission: 0.65,
      transparent: true,
      opacity: 0.9,
      reflectivity: 0.95,
      clearcoat: 1.0,
      clearcoatRoughness: 0.08
    });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.position.y = -0.025;
    floorMesh.receiveShadow = true;
    stageGroup.add(floorMesh);

    // Glowing concentric holographic rings
    const ringGeo1 = new THREE.RingGeometry(1.58, 1.62, 64);
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85
    });
    const ringMesh1 = new THREE.Mesh(ringGeo1, ringMat1);
    ringMesh1.rotation.x = Math.PI / 2;
    ringMesh1.position.y = 0.005;
    stageGroup.add(ringMesh1);

    const ringGeo2 = new THREE.RingGeometry(1.15, 1.18, 64);
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x818cf8,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.55
    });
    const ringMesh2 = new THREE.Mesh(ringGeo2, ringMat2);
    ringMesh2.rotation.x = Math.PI / 2;
    ringMesh2.position.y = 0.006;
    stageGroup.add(ringMesh2);

    scene.add(stageGroup);

    // 6. FLOATING SPATIAL PARTICLES
    const particleCount = 100;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      particlePositions[i * 3] = (Math.random() - 0.5) * 3.6;
      particlePositions[i * 3 + 1] = Math.random() * 2.8;
      particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 3.6;

      const isCyan = Math.random() > 0.4;
      particleColors[i * 3] = isCyan ? 0.3 : 0.6;
      particleColors[i * 3 + 1] = isCyan ? 0.75 : 0.4;
      particleColors[i * 3 + 2] = isCyan ? 0.98 : 0.95;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);
    particlesRef.current = particles;

    // 7. ARTICULATED 3D HUMANOID SIGNAVATAR RIG
    const avatar = new THREE.Group();
    avatarGroupRef.current = avatar;
    const joints: { [key: string]: THREE.Object3D } = {};

    const skinMat = new THREE.MeshPhysicalMaterial({
      color: 0x1e293b,
      metalness: 0.2,
      roughness: 0.35,
      clearcoat: 0.7,
      clearcoatRoughness: 0.15
    });

    const suitMat = new THREE.MeshPhysicalMaterial({
      color: 0x0f172a,
      metalness: 0.65,
      roughness: 0.28,
      clearcoat: 0.9,
      clearcoatRoughness: 0.1
    });

    const glowAccentMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8
    });

    const visorMat = new THREE.MeshPhysicalMaterial({
      color: 0x22d3ee,
      emissive: 0x0284c7,
      emissiveIntensity: 0.7,
      roughness: 0.08,
      metalness: 0.95,
      clearcoat: 1.0
    });

    // Root Pelvis
    const pelvis = new THREE.Group();
    pelvis.position.y = 0.85;
    avatar.add(pelvis);
    joints['pelvis'] = pelvis;

    // Spine & Torso
    const spine = new THREE.Group();
    pelvis.add(spine);
    joints['spine'] = spine;

    const chestGeo = new THREE.CylinderGeometry(0.24, 0.18, 0.44, 20);
    const chestMesh = new THREE.Mesh(chestGeo, suitMat);
    chestMesh.position.y = 0.25;
    chestMesh.castShadow = true;
    spine.add(chestMesh);

    // Glowing Chest Core Indicator
    const coreGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.02, 16);
    const coreMesh = new THREE.Mesh(coreGeo, glowAccentMat);
    coreMesh.rotation.x = Math.PI / 2;
    coreMesh.position.set(0, 0.28, 0.18);
    spine.add(coreMesh);

    // Neck
    const neck = new THREE.Group();
    neck.position.y = 0.5;
    spine.add(neck);
    joints['neck'] = neck;

    const neckGeo = new THREE.CylinderGeometry(0.07, 0.08, 0.1, 16);
    const neckMesh = new THREE.Mesh(neckGeo, skinMat);
    neckMesh.position.y = 0.05;
    neck.add(neckMesh);

    // Head
    const head = new THREE.Group();
    head.position.y = 0.12;
    neck.add(head);
    joints['head'] = head;

    const headGeo = new THREE.SphereGeometry(0.14, 28, 28);
    const headMesh = new THREE.Mesh(headGeo, skinMat);
    headMesh.position.y = 0.1;
    headMesh.castShadow = true;
    head.add(headMesh);

    // Visor / Spatial Optical Sensor
    const visorGeo = new THREE.BoxGeometry(0.18, 0.05, 0.08);
    const visorMesh = new THREE.Mesh(visorGeo, visorMat);
    visorMesh.position.set(0, 0.11, 0.11);
    head.add(visorMesh);

    // 5-Finger Articulated Arm Generator
    const createArm = (isRight: boolean) => {
      const sideMult = isRight ? 1 : -1;
      
      const shoulder = new THREE.Group();
      shoulder.position.set(0.24 * sideMult, 0.42, 0);
      spine.add(shoulder);
      joints[isRight ? 'rightShoulder' : 'leftShoulder'] = shoulder;

      const shoulderArmorGeo = new THREE.SphereGeometry(0.09, 16, 16);
      const shoulderArmor = new THREE.Mesh(shoulderArmorGeo, suitMat);
      shoulderArmor.position.set(0.04 * sideMult, 0, 0);
      shoulder.add(shoulderArmor);

      const upperArm = new THREE.Group();
      shoulder.add(upperArm);
      joints[isRight ? 'rightUpperArm' : 'leftUpperArm'] = upperArm;

      const upperArmGeo = new THREE.CylinderGeometry(0.055, 0.05, 0.28, 16);
      const upperArmMesh = new THREE.Mesh(upperArmGeo, suitMat);
      upperArmMesh.position.y = -0.14;
      upperArmMesh.castShadow = true;
      upperArm.add(upperArmMesh);

      const elbow = new THREE.Group();
      elbow.position.y = -0.28;
      upperArm.add(elbow);
      joints[isRight ? 'rightElbow' : 'leftElbow'] = elbow;

      const forearmGeo = new THREE.CylinderGeometry(0.05, 0.042, 0.26, 16);
      const forearmMesh = new THREE.Mesh(forearmGeo, skinMat);
      forearmMesh.position.y = -0.13;
      forearmMesh.castShadow = true;
      elbow.add(forearmMesh);

      const wrist = new THREE.Group();
      wrist.position.y = -0.26;
      elbow.add(wrist);
      joints[isRight ? 'rightWrist' : 'leftWrist'] = wrist;

      const palmGeo = new THREE.BoxGeometry(0.06, 0.08, 0.025);
      const palmMesh = new THREE.Mesh(palmGeo, skinMat);
      palmMesh.position.y = -0.04;
      palmMesh.castShadow = true;
      wrist.add(palmMesh);

      const fingers: THREE.Group[] = [];
      for (let f = 0; f < 5; f++) {
        const finger = new THREE.Group();
        if (f === 0) {
          finger.position.set(0.035 * sideMult, -0.02, 0.01);
        } else {
          finger.position.set((-0.025 + (f - 1) * 0.016) * sideMult, -0.08, 0);
        }
        wrist.add(finger);

        const fingerGeo = new THREE.CylinderGeometry(0.009, 0.008, f === 0 ? 0.04 : 0.05, 8);
        const fingerMesh = new THREE.Mesh(fingerGeo, skinMat);
        fingerMesh.position.y = -0.025;
        finger.add(fingerMesh);
        fingers.push(finger);
      }
      joints[isRight ? 'rightFingers' : 'leftFingers'] = fingers[1];
    };

    createArm(false);
    createArm(true);

    const hipsGeo = new THREE.CylinderGeometry(0.18, 0.14, 0.16, 16);
    const hipsMesh = new THREE.Mesh(hipsGeo, suitMat);
    hipsMesh.position.y = -0.08;
    pelvis.add(hipsMesh);

    scene.add(avatar);
    jointsRef.current = joints;

    // 8. INTERACTIVE ORBIT
    let isDragging = false;
    let prevMouseX = 0;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging || !avatarGroupRef.current) return;
      const deltaX = e.clientX - prevMouseX;
      avatarGroupRef.current.rotation.y += deltaX * 0.01;
      prevMouseX = e.clientX;
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const domElem = renderer.domElement;
    domElem.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // 9. ANIMATION LOOP
    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (isPlaying) {
        animTimeRef.current += 0.035 * internalSpeed;
      }

      const t = animTimeRef.current;
      const sign = activeSignRef.current.toUpperCase();
      const j = jointsRef.current;

      if (particlesRef.current) {
        particlesRef.current.rotation.y = t * 0.04;
        const positions = particlesRef.current.geometry.attributes.position.array as Float32Array;
        for (let i = 1; i < positions.length; i += 3) {
          positions[i] += Math.sin(t + i) * 0.0008;
        }
        particlesRef.current.geometry.attributes.position.needsUpdate = true;
      }

      if (j.spine && j.neck && j.head) {
        j.spine.position.y = Math.sin(t * 1.5) * 0.008;
        j.neck.rotation.x = Math.sin(t * 1.2) * 0.015;
        j.head.rotation.y = Math.sin(t * 0.8) * 0.03;
      }

      let rUpperRot = new THREE.Vector3(0.1, 0, -0.2);
      let rElbowRot = new THREE.Vector3(-0.3, 0, -0.1);
      let rWristRot = new THREE.Vector3(0, 0, 0);

      let lUpperRot = new THREE.Vector3(0.1, 0, 0.2);
      let lElbowRot = new THREE.Vector3(-0.3, 0, 0.1);
      let lWristRot = new THREE.Vector3(0, 0, 0);

      let headRot = new THREE.Vector3(0, 0, 0);

      if (sign === 'HELLO' || sign.includes('GREET')) {
        const wave = Math.sin(t * 5) * 0.25;
        rUpperRot = new THREE.Vector3(-1.2, 0.3, 0.8);
        rElbowRot = new THREE.Vector3(-1.4, 0.2, 0.4 + wave);
        rWristRot = new THREE.Vector3(0.2, wave, 0.3);
        headRot = new THREE.Vector3(-0.05, 0.1, 0.05);
      } else if (sign === 'WELCOME') {
        const sweep = Math.sin(t * 3) * 0.2;
        rUpperRot = new THREE.Vector3(-0.8, -0.4, 0.6 + sweep);
        rElbowRot = new THREE.Vector3(-1.2, -0.6, 0.2);
        lUpperRot = new THREE.Vector3(-0.8, 0.4, -0.6 - sweep);
        lElbowRot = new THREE.Vector3(-1.2, 0.6, -0.2);
        headRot = new THREE.Vector3(-0.08, 0, 0);
      } else if (sign === 'THANK_YOU' || sign === 'THANKS') {
        const nod = Math.sin(t * 3.5);
        const forward = (Math.sin(t * 3.5) + 1) * 0.5;
        rUpperRot = new THREE.Vector3(-0.6 - forward * 0.6, 0.2, 0.3);
        rElbowRot = new THREE.Vector3(-1.8 + forward * 0.8, 0, 0.2);
        rWristRot = new THREE.Vector3(0.4, 0, 0);
        headRot = new THREE.Vector3(nod * 0.08, 0, 0);
      } else if (sign === 'HOW_ARE_YOU' || sign.includes('QUESTION')) {
        const qPulse = Math.sin(t * 2.5) * 0.15;
        rUpperRot = new THREE.Vector3(-0.7, -0.3, 0.5 + qPulse);
        rElbowRot = new THREE.Vector3(-1.3, 0.2, 0.3);
        lUpperRot = new THREE.Vector3(-0.7, 0.3, -0.5 - qPulse);
        lElbowRot = new THREE.Vector3(-1.3, -0.2, -0.3);
        headRot = new THREE.Vector3(-0.15, Math.sin(t * 2) * 0.08, 0);
      } else if (sign === 'SIGN_LANGUAGE' || sign.includes('SIGN')) {
        const rotR = Math.sin(t * 4);
        const rotL = Math.cos(t * 4);
        rUpperRot = new THREE.Vector3(-0.9, rotR * 0.4, 0.5);
        rElbowRot = new THREE.Vector3(-1.5, rotL * 0.4, 0.2);
        lUpperRot = new THREE.Vector3(-0.9, rotL * 0.4, -0.5);
        lElbowRot = new THREE.Vector3(-1.5, rotR * 0.4, -0.2);
      } else if (sign === 'ACCESSIBLE' || sign.includes('FUTURE')) {
        const expand = (Math.sin(t * 3) + 1) * 0.5;
        rUpperRot = new THREE.Vector3(-0.8, -0.2, 0.3 + expand * 0.6);
        rElbowRot = new THREE.Vector3(-1.6 + expand * 0.5, 0, 0.3);
        lUpperRot = new THREE.Vector3(-0.8, 0.2, -0.3 - expand * 0.6);
        lElbowRot = new THREE.Vector3(-1.6 + expand * 0.5, 0, -0.3);
      } else if (sign === 'INDIA' || sign === 'NAMASTE') {
        rUpperRot = new THREE.Vector3(-1.4, 0.4, 0.4);
        rElbowRot = new THREE.Vector3(-2.2, 0.2, 0.3);
        rWristRot = new THREE.Vector3(0.5, 0.2, 0);
        headRot = new THREE.Vector3(0.08, 0, 0);
      } else if (sign === 'HELP') {
        const lift = (Math.sin(t * 3) + 1) * 0.15;
        rUpperRot = new THREE.Vector3(-0.8 - lift, 0.2, 0.2);
        rElbowRot = new THREE.Vector3(-1.6, 0.4, 0.2);
        lUpperRot = new THREE.Vector3(-0.8 - lift, -0.2, -0.2);
        lElbowRot = new THREE.Vector3(-1.6, -0.4, -0.2);
      } else if (sign === 'DOCTOR' || sign.includes('MEDICAL')) {
        const tap = Math.sin(t * 6) * 0.1;
        lUpperRot = new THREE.Vector3(-0.6, -0.2, -0.3);
        lElbowRot = new THREE.Vector3(-1.4, 0.3, 0);
        rUpperRot = new THREE.Vector3(-0.7, 0.3, 0.4 + tap);
        rElbowRot = new THREE.Vector3(-1.5, 0.2, 0);
      }

      const lerpFactor = 0.12;
      const rightUpper = j.rightUpperArm;
      const rightElbow = j.rightElbow;
      const rightWrist = j.rightWrist;
      const leftUpper = j.leftUpperArm;
      const leftElbow = j.leftElbow;
      const headJ = j.head;

      if (rightUpper) {
        rightUpper.rotation.x = THREE.MathUtils.lerp(rightUpper.rotation.x, rUpperRot.x, lerpFactor);
        rightUpper.rotation.y = THREE.MathUtils.lerp(rightUpper.rotation.y, rUpperRot.y, lerpFactor);
        rightUpper.rotation.z = THREE.MathUtils.lerp(rightUpper.rotation.z, rUpperRot.z, lerpFactor);
      }
      if (rightElbow) {
        rightElbow.rotation.x = THREE.MathUtils.lerp(rightElbow.rotation.x, rElbowRot.x, lerpFactor);
        rightElbow.rotation.y = THREE.MathUtils.lerp(rightElbow.rotation.y, rElbowRot.y, lerpFactor);
        rightElbow.rotation.z = THREE.MathUtils.lerp(rightElbow.rotation.z, rElbowRot.z, lerpFactor);
      }
      if (rightWrist) {
        rightWrist.rotation.x = THREE.MathUtils.lerp(rightWrist.rotation.x, rWristRot.x, lerpFactor);
        rightWrist.rotation.y = THREE.MathUtils.lerp(rightWrist.rotation.y, rWristRot.y, lerpFactor);
        rightWrist.rotation.z = THREE.MathUtils.lerp(rightWrist.rotation.z, rWristRot.z, lerpFactor);
      }
      if (leftUpper) {
        leftUpper.rotation.x = THREE.MathUtils.lerp(leftUpper.rotation.x, lUpperRot.x, lerpFactor);
        leftUpper.rotation.y = THREE.MathUtils.lerp(leftUpper.rotation.y, lUpperRot.y, lerpFactor);
        leftUpper.rotation.z = THREE.MathUtils.lerp(leftUpper.rotation.z, lUpperRot.z, lerpFactor);
      }
      if (leftElbow) {
        leftElbow.rotation.x = THREE.MathUtils.lerp(leftElbow.rotation.x, lElbowRot.x, lerpFactor);
        leftElbow.rotation.y = THREE.MathUtils.lerp(leftElbow.rotation.y, lElbowRot.y, lerpFactor);
        leftElbow.rotation.z = THREE.MathUtils.lerp(leftElbow.rotation.z, lElbowRot.z, lerpFactor);
      }
      if (headJ) {
        headJ.rotation.x = THREE.MathUtils.lerp(headJ.rotation.x, headRot.x, lerpFactor);
        headJ.rotation.y = THREE.MathUtils.lerp(headJ.rotation.y, headRot.y, lerpFactor);
      }

      renderer.render(scene, camera);
    };

    animate();

    // 10. RESIZE HANDLER
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      camera.aspect = container.clientWidth / (container.clientHeight || 1);
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      domElem.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      renderer.dispose();
    };
  }, [internalSpeed, isPlaying]);

  const applyCameraPreset = (preset: CameraPreset) => {
    setCameraPreset(preset);
    if (!cameraRef.current || !avatarGroupRef.current) return;

    if (preset === 'front') {
      cameraRef.current.position.set(0, 1.35, 2.7);
      avatarGroupRef.current.rotation.y = 0;
    } else if (preset === 'perspective') {
      cameraRef.current.position.set(1.1, 1.4, 2.3);
      avatarGroupRef.current.rotation.y = -0.28;
    } else if (preset === 'hands') {
      cameraRef.current.position.set(0, 1.15, 1.6);
      avatarGroupRef.current.rotation.y = 0;
    } else if (preset === 'top') {
      cameraRef.current.position.set(0, 2.3, 2.2);
      avatarGroupRef.current.rotation.y = 0;
    }
  };

  const applyLightingPreset = (preset: LightingPreset) => {
    setLightingPreset(preset);
    const lights = lightsRef.current;
    if (!lights) return;

    if (preset === 'neon') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0xffffff);
      (lights.purple as THREE.PointLight).color.setHex(0x8b5cf6);
      (lights.cyan as THREE.PointLight).color.setHex(0x38bdf8);
    } else if (preset === 'studio') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0xffffff);
      (lights.purple as THREE.PointLight).color.setHex(0xe2e8f0);
      (lights.cyan as THREE.PointLight).color.setHex(0xffffff);
    } else if (preset === 'cyber') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0x06b6d4);
      (lights.purple as THREE.PointLight).color.setHex(0xec4899);
      (lights.cyan as THREE.PointLight).color.setHex(0x10b981);
    } else if (preset === 'sunset') {
      (lights.ambient as THREE.AmbientLight).color.setHex(0xf59e0b);
      (lights.purple as THREE.PointLight).color.setHex(0xf43f5e);
      (lights.cyan as THREE.PointLight).color.setHex(0x8b5cf6);
    }
  };

  const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];

  // Handler for previous / next sign cycling
  const handlePrevSign = () => {
    if (onPreviousSign) {
      onPreviousSign();
      return;
    }
    const idx = availableSigns.findIndex(s => s.sign.toUpperCase() === currentSign.toUpperCase());
    const prevIdx = idx > 0 ? idx - 1 : availableSigns.length - 1;
    onSignChange?.(availableSigns[prevIdx].sign);
  };

  const handleNextSign = () => {
    if (onNextSign) {
      onNextSign();
      return;
    }
    const idx = availableSigns.findIndex(s => s.sign.toUpperCase() === currentSign.toUpperCase());
    const nextIdx = idx < availableSigns.length - 1 ? idx + 1 : 0;
    onSignChange?.(availableSigns[nextIdx].sign);
  };

  return (
    <div className={`w-full rounded-[32px] glass-card border border-white/16 shadow-2xl flex flex-col select-none overflow-hidden ${
      isFullscreen ? 'fixed inset-4 z-50 h-[calc(100vh-32px)] max-w-none' : ''
    } ${className}`}>
      
      {/* 1. DEDICATED HEADER ROW */}
      <header className="px-6 py-4 border-b border-white/10 flex flex-wrap items-center justify-between gap-3 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white tracking-tight uppercase">
                SignAvatar Stage
              </h2>
              <span className="text-[11px] font-mono text-cyan-300 font-semibold bg-white/8 px-2 py-0.5 rounded-md border border-white/10">
                {currentSign}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">ISL 60 FPS Keyframe Rig</p>
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
              const presets: LightingPreset[] = ['neon', 'studio', 'cyber', 'sunset'];
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
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[11px] font-semibold text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Ready</span>
          </div>
        </div>
      </header>

      {/* 2. DEDICATED AVATAR CANVAS VIEWPORT (NO OVERLAPPING TEXT OR BUTTONS) */}
      <main 
        ref={mountRef} 
        style={{ height }}
        className="w-full flex-1 cursor-grab active:cursor-grabbing overflow-hidden relative bg-black/20"
      />

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
              if (avatarGroupRef.current) avatarGroupRef.current.rotation.y = 0;
            }}
            className="p-2 rounded-xl glass-subtle hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 transition-all"
            title="Reset Avatar Orientation"
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

        {/* 4. DEDICATED SPEED CONTROLS ROW IN TRANSPORT */}
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

      {/* 5. DEDICATED ISL TEST BUTTONS ROW */}
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
                  onClick={() => onSignChange?.(item.sign)}
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
