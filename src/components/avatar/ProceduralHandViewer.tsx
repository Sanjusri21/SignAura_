import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  ProceduralHandPoseData,
  FingerJointAngles,
  getNeutralHandPose,
} from '../../lib/experimentalHandPoseRegistry';

export interface ProceduralHandViewerProps {
  poseData?: ProceduralHandPoseData | null;
  isUnavailable?: boolean;
  unavailableReason?: string;
  className?: string;
}

interface FingerRig {
  mcpGroup: THREE.Group;
  pipGroup: THREE.Group;
  dipGroup: THREE.Group;
}

interface HandRig {
  rootGroup: THREE.Group;
  palmMesh: THREE.Mesh;
  thumb: FingerRig;
  index: FingerRig;
  middle: FingerRig;
  ring: FingerRig;
  pinky: FingerRig;
}

/**
 * Creates an articulated finger chain: MCP group -> Proximal -> PIP group -> Middle -> DIP group -> Distal
 */
function createFingerChain(
  fingerName: string,
  baseX: number,
  baseY: number,
  proximalLen: number,
  middleLen: number,
  distalLen: number,
  radius: number,
  materials: { bone: THREE.Material; joint: THREE.Material },
  disposables: { geometries: THREE.BufferGeometry[]; materials: THREE.Material[] }
): FingerRig {
  const mcpGroup = new THREE.Group();
  mcpGroup.name = `${fingerName}_mcp`;
  mcpGroup.position.set(baseX, baseY, 0);

  // MCP Joint Marker
  const jointGeom = new THREE.SphereGeometry(radius * 1.15, 12, 12);
  disposables.geometries.push(jointGeom);
  const mcpSphere = new THREE.Mesh(jointGeom, materials.joint);
  mcpGroup.add(mcpSphere);

  // Proximal phalanx (cylinder oriented along +Y)
  const proxGeom = new THREE.CylinderGeometry(radius * 0.9, radius, proximalLen, 12);
  disposables.geometries.push(proxGeom);
  const proxMesh = new THREE.Mesh(proxGeom, materials.bone);
  proxMesh.position.set(0, proximalLen / 2, 0);
  mcpGroup.add(proxMesh);

  // PIP Joint Group (at top of proximal phalanx)
  const pipGroup = new THREE.Group();
  pipGroup.name = `${fingerName}_pip`;
  pipGroup.position.set(0, proximalLen, 0);

  const pipSphere = new THREE.Mesh(jointGeom, materials.joint);
  pipGroup.add(pipSphere);

  // Middle phalanx
  const midGeom = new THREE.CylinderGeometry(radius * 0.8, radius * 0.9, middleLen, 12);
  disposables.geometries.push(midGeom);
  const midMesh = new THREE.Mesh(midGeom, materials.bone);
  midMesh.position.set(0, middleLen / 2, 0);
  pipGroup.add(midMesh);

  // DIP Joint Group (at top of middle phalanx)
  const dipGroup = new THREE.Group();
  dipGroup.name = `${fingerName}_dip`;
  dipGroup.position.set(0, middleLen, 0);

  const dipSphere = new THREE.Mesh(jointGeom, materials.joint);
  dipGroup.add(dipSphere);

  // Distal phalanx + rounded tip
  const distGeom = new THREE.CylinderGeometry(radius * 0.65, radius * 0.8, distalLen, 12);
  disposables.geometries.push(distGeom);
  const distMesh = new THREE.Mesh(distGeom, materials.bone);
  distMesh.position.set(0, distalLen / 2, 0);
  dipGroup.add(distMesh);

  const tipGeom = new THREE.SphereGeometry(radius * 0.65, 10, 10);
  disposables.geometries.push(tipGeom);
  const tipMesh = new THREE.Mesh(tipGeom, materials.bone);
  tipMesh.position.set(0, distalLen, 0);
  dipGroup.add(tipMesh);

  // Assemble hierarchy
  pipGroup.add(dipGroup);
  mcpGroup.add(pipGroup);

  return { mcpGroup, pipGroup, dipGroup };
}

/**
 * Creates full articulated hand rig with palm and 5 digits.
 */
function createHandRig(disposables: { geometries: THREE.BufferGeometry[]; materials: THREE.Material[] }): HandRig {
  const rootGroup = new THREE.Group();
  rootGroup.name = 'procedural_hand_root';

  const boneMat = new THREE.MeshStandardMaterial({
    color: 0x93c5fd,
    roughness: 0.35,
    metalness: 0.15,
  });
  const jointMat = new THREE.MeshStandardMaterial({
    color: 0x38bdf8,
    roughness: 0.25,
    metalness: 0.3,
  });
  const palmMat = new THREE.MeshStandardMaterial({
    color: 0x60a5fa,
    roughness: 0.4,
    metalness: 0.1,
  });
  disposables.materials.push(boneMat, jointMat, palmMat);

  // Palm geometry (box rounded slightly)
  const palmWidth = 0.082;
  const palmHeight = 0.085;
  const palmDepth = 0.022;
  const palmGeom = new THREE.BoxGeometry(palmWidth, palmHeight, palmDepth);
  disposables.geometries.push(palmGeom);
  const palmMesh = new THREE.Mesh(palmGeom, palmMat);
  palmMesh.position.set(0, palmHeight / 2, 0);
  rootGroup.add(palmMesh);

  const materials = { bone: boneMat, joint: jointMat };

  // Thumb
  const thumb = createFingerChain('thumb', -0.046, 0.022, 0.032, 0.026, 0.022, 0.009, materials, disposables);
  // Default thumb base orientation (naturally rotated outwards and forward)
  thumb.mcpGroup.rotation.set(0.2, 0.35, 0.7);
  rootGroup.add(thumb.mcpGroup);

  // Index
  const index = createFingerChain('index', -0.03, 0.085, 0.04, 0.028, 0.022, 0.0085, materials, disposables);
  rootGroup.add(index.mcpGroup);

  // Middle
  const middle = createFingerChain('middle', -0.01, 0.088, 0.045, 0.032, 0.024, 0.0088, materials, disposables);
  rootGroup.add(middle.mcpGroup);

  // Ring
  const ring = createFingerChain('ring', 0.011, 0.085, 0.041, 0.028, 0.022, 0.0083, materials, disposables);
  rootGroup.add(ring.mcpGroup);

  // Pinky
  const pinky = createFingerChain('pinky', 0.031, 0.076, 0.032, 0.022, 0.018, 0.0075, materials, disposables);
  rootGroup.add(pinky.mcpGroup);

  return { rootGroup, palmMesh, thumb, index, middle, ring, pinky };
}

/**
 * Applies clamped flexion/abduction to a finger rig.
 */
function applyFingerJoints(
  rig: FingerRig,
  angles: FingerJointAngles,
  baseEulerOffset: { x: number; y: number; z: number } = { x: 0, y: 0, z: 0 }
) {
  // Clamp joint ranges to avoid severe self-intersections
  const mcpFlex = Math.max(-0.2, Math.min(angles.mcpFlexion, 1.8));
  const mcpAbd = Math.max(-0.6, Math.min(angles.mcpAbduction ?? 0, 0.6));
  const pipFlex = Math.max(0.0, Math.min(angles.pipFlexion, 1.8));
  const dipFlex = Math.max(0.0, Math.min(angles.dipFlexion, 1.6));

  rig.mcpGroup.rotation.x = baseEulerOffset.x + mcpFlex;
  rig.mcpGroup.rotation.y = baseEulerOffset.y;
  rig.mcpGroup.rotation.z = baseEulerOffset.z + mcpAbd;

  rig.pipGroup.rotation.x = pipFlex;
  rig.dipGroup.rotation.x = dipFlex;
}

export const ProceduralHandViewer: React.FC<ProceduralHandViewerProps> = ({
  poseData,
  isUnavailable = false,
  unavailableReason,
  className = '',
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const rigRef = useRef<HandRig | null>(null);

  // Set up Three.js Scene, Camera, Lights, and OrbitControls
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 400;
    const height = container.clientHeight || 400;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a1026);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.01, 10);
    camera.position.set(0, 0.08, 0.42);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0.08, 0);
    controls.maxDistance = 1.0;
    controls.minDistance = 0.15;

    // Lighting
    const ambLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight1.position.set(0.3, 0.4, 0.5);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 0.6);
    dirLight2.position.set(-0.3, -0.1, 0.3);
    scene.add(dirLight2);

    // Track all disposables for clean unmount
    const disposables = {
      geometries: [] as THREE.BufferGeometry[],
      materials: [] as THREE.Material[],
    };

    const rig = createHandRig(disposables);
    scene.add(rig.rootGroup);
    rigRef.current = rig;

    // Subtle floor grid
    const grid = new THREE.GridHelper(0.5, 10, 0x1e293b, 0x0f172a);
    grid.position.y = -0.05;
    scene.add(grid);
    disposables.geometries.push(grid.geometry);

    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize observer
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      controls.dispose();

      disposables.geometries.forEach((g) => g.dispose());
      disposables.materials.forEach((m) => m.dispose());

      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      rigRef.current = null;
    };
  }, []);

  // Update Joint Rotations when poseData or isUnavailable changes
  useEffect(() => {
    const rig = rigRef.current;
    if (!rig) return;

    // If unavailable or poseData is absent, apply neutral resting pose
    const targetPose = isUnavailable || !poseData ? getNeutralHandPose() : poseData;

    // Thumb base resting Euler offset
    const thumbBaseOffset = { x: 0.15, y: 0.35, z: 0.65 };
    applyFingerJoints(rig.thumb, targetPose.thumb, thumbBaseOffset);

    // Digits 2-5
    applyFingerJoints(rig.index, targetPose.index);
    applyFingerJoints(rig.middle, targetPose.middle);
    applyFingerJoints(rig.ring, targetPose.ring);
    applyFingerJoints(rig.pinky, targetPose.pinky);

    // Wrist rotation if provided
    if (targetPose.wristRotation) {
      rig.rootGroup.rotation.set(
        targetPose.wristRotation[0],
        targetPose.wristRotation[1],
        targetPose.wristRotation[2]
      );
    } else {
      rig.rootGroup.rotation.set(0, 0, 0);
    }

    // Material tint adjustment for unavailable state
    const palmMat = rig.palmMesh.material as THREE.MeshStandardMaterial;
    if (isUnavailable) {
      palmMat.color.setHex(0x64748b);
      palmMat.wireframe = true;
    } else {
      palmMat.color.setHex(0x60a5fa);
      palmMat.wireframe = false;
    }
  }, [poseData, isUnavailable]);

  return (
    <div className={`relative w-full h-full min-h-[340px] rounded-2xl overflow-hidden bg-[#0A1026] border border-[#273154] ${className}`}>
      {/* Three.js Canvas Container */}
      <div ref={mountRef} className="w-full h-full" />

      {/* Unavailable State Overlay */}
      {isUnavailable && (
        <div className="absolute inset-0 bg-[#080D24]/75 backdrop-blur-[2px] flex flex-col items-center justify-center p-6 text-center z-10 pointer-events-none">
          <div className="p-3 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 mb-2">
            <span className="text-xl">⚠️</span>
          </div>
          <p className="text-sm font-bold text-amber-300">Pose Definition Unavailable</p>
          <p className="text-xs text-slate-300 max-w-sm mt-1 leading-relaxed">
            {unavailableReason || 'No verified single-hand procedural definition is available for this symbol.'}
          </p>
          <p className="text-[10px] text-slate-400 mt-2 font-mono">
            (Rendering neutral rest pose; not fabricating unsupported signs)
          </p>
        </div>
      )}

      {/* Viewport Overlay Controls Hint */}
      <div className="absolute bottom-2 right-2 text-[10px] text-slate-400 bg-slate-900/60 px-2 py-0.5 rounded backdrop-blur pointer-events-none">
        Drag to Rotate • Scroll to Zoom
      </div>
    </div>
  );
};
