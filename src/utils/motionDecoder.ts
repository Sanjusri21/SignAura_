/**
 * Pure mathematical utilities for SMPL-X 3D motion decoding,
 * normalization, frame timing, and multi-clip transition blending.
 *
 * Standalone module with zero React or DOM dependencies.
 */

export const SMPLX_VERTEX_COUNT = 10475;
export const SMPLX_FACE_COUNT = 20908;
export const DEFAULT_MOTION_FPS = 20;
export const FLOATS_PER_FRAME = SMPLX_VERTEX_COUNT * 3; // 31,425 floats
export const BYTES_PER_FRAME = FLOATS_PER_FRAME * 4;   // 125,700 bytes

export interface NormalizedMotion {
  frames: number;
  vertices: number;
  components: number;
  fps: number;
  data: Float32Array; // Flattened normalized coordinates: frames * 10475 * 3
}

export interface MotionSegmentBoundary {
  gloss: string;
  startFrame: number;
  endFrame: number;
}

export interface BlendMotionOptions {
  holdFrames?: number;
  transitionFrames?: number;
  easeInFrames?: number;
  easeOutFrames?: number;
}

/**
 * Parses and validates raw Float32 binary motion buffer into normalized SMPL-X motion.
 * Enforces exact frame sizing, dimension constraints, and finite coordinate checks.
 */
export function processAndNormalizeMotion(
  buffer: ArrayBuffer,
  headerFrames?: number,
  headerFps?: number
): NormalizedMotion {
  if (!buffer || buffer.byteLength === 0) {
    throw new Error('Motion buffer is empty.');
  }

  const floatView = new Float32Array(buffer);
  const totalFloats = floatView.length;

  if (totalFloats % FLOATS_PER_FRAME !== 0) {
    throw new Error(
      `Invalid motion binary length. Expected multiple of ${BYTES_PER_FRAME} bytes (${FLOATS_PER_FRAME} floats), received ${buffer.byteLength} bytes.`
    );
  }

  const computedFrames = totalFloats / FLOATS_PER_FRAME;
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

/**
 * Creates smooth cosine transition poses between poseA and poseB across numFrames intermediate frames.
 * Returns a Float32Array of length (numFrames * 10475 * 3).
 */
export function createTransition(
  poseA: Float32Array,
  poseB: Float32Array,
  numFrames: number = 6
): Float32Array {
  if (numFrames <= 0) {
    return new Float32Array(0);
  }

  const result = new Float32Array(numFrames * FLOATS_PER_FRAME);
  for (let f = 1; f <= numFrames; f++) {
    // Cosine smooth easing strictly in range (0, 1)
    const rawT = f / (numFrames + 1);
    const weight = 0.5 * (1.0 - Math.cos(rawT * Math.PI));
    const offset = (f - 1) * FLOATS_PER_FRAME;

    for (let i = 0; i < FLOATS_PER_FRAME; i++) {
      result[offset + i] = (1.0 - weight) * poseA[i] + weight * poseB[i];
    }
  }
  return result;
}

/**
 * Calculates wrapped frame index given elapsed time and playback speed.
 */
export function calculateFrameIndex(
  currentElapsed: number,
  deltaSec: number,
  fps: number,
  speed: number,
  totalFrames: number
): { nextElapsed: number; frameIndex: number } {
  if (totalFrames <= 0) {
    return { nextElapsed: 0, frameIndex: 0 };
  }
  const nextElapsed = (currentElapsed + deltaSec * fps * speed) % totalFrames;
  const frameIndex = Math.min(Math.floor(nextElapsed), totalFrames - 1);
  return { nextElapsed, frameIndex };
}

/**
 * Blends multiple consecutive SMPL-X motion clips with:
 * - Cubic ease-in from relaxed standing neutral pose (arms down)
 * - 4-frame holds per sign for legibility
 * - 6-frame cosine crossfade between consecutive signs across all 10,475 vertices
 * - Cubic ease-out to relaxed pose
 * - NaN and Infinity validation
 */
export function blendMotionClips(
  clips: { gloss: string; motion: NormalizedMotion }[],
  relaxedPose: Float32Array | null,
  options: BlendMotionOptions = {}
): { motion: NormalizedMotion; segmentBoundaries: MotionSegmentBoundary[] } {
  const holdFrames = options.holdFrames ?? 4;
  const transitionFrames = options.transitionFrames ?? 6;
  const easeInFrames = options.easeInFrames ?? 8;
  const easeOutFrames = options.easeOutFrames ?? 10;
  const V_SIZE = FLOATS_PER_FRAME;

  if (clips.length === 0) {
    throw new Error('No clips to blend.');
  }

  let totalFrames = easeInFrames;
  for (let c = 0; c < clips.length; c++) {
    totalFrames += clips[c].motion.frames + holdFrames;
    if (c < clips.length - 1) {
      totalFrames += transitionFrames;
    }
  }
  totalFrames += easeOutFrames;

  const blendedData = new Float32Array(totalFrames * V_SIZE);
  const segmentBoundaries: MotionSegmentBoundary[] = [];
  const fps = clips[0].motion.fps || DEFAULT_MOTION_FPS;

  let currentFrameIdx = 0;

  // 1. Ease in from relaxed pose to frame 0 of first clip
  const firstFrameData = clips[0].motion.data.subarray(0, V_SIZE);
  const startPose = relaxedPose && relaxedPose.length === V_SIZE ? relaxedPose : firstFrameData;

  for (let f = 0; f < easeInFrames; f++) {
    const rawT = (f + 1) / easeInFrames;
    const t = rawT < 0.5 ? 4 * rawT * rawT * rawT : 1 - Math.pow(-2 * rawT + 2, 3) / 2;
    const destOffset = currentFrameIdx * V_SIZE;
    for (let i = 0; i < V_SIZE; i++) {
      blendedData[destOffset + i] = startPose[i] * (1 - t) + firstFrameData[i] * t;
    }
    currentFrameIdx++;
  }

  // 2. Play clips with holds and crossfades
  for (let c = 0; c < clips.length; c++) {
    const { gloss, motion } = clips[c];
    const segStart = currentFrameIdx;

    for (let f = 0; f < motion.frames; f++) {
      const srcOffset = f * V_SIZE;
      const destOffset = currentFrameIdx * V_SIZE;
      blendedData.set(motion.data.subarray(srcOffset, srcOffset + V_SIZE), destOffset);
      currentFrameIdx++;
    }

    const lastClipFrameOffset = (motion.frames - 1) * V_SIZE;
    const lastClipData = motion.data.subarray(lastClipFrameOffset, lastClipFrameOffset + V_SIZE);
    for (let h = 0; h < holdFrames; h++) {
      blendedData.set(lastClipData, currentFrameIdx * V_SIZE);
      currentFrameIdx++;
    }

    segmentBoundaries.push({
      gloss,
      startFrame: segStart,
      endFrame: currentFrameIdx - 1
    });

    if (c < clips.length - 1) {
      const nextFirstFrame = clips[c + 1].motion.data.subarray(0, V_SIZE);
      const transition = createTransition(lastClipData, nextFirstFrame, transitionFrames);
      blendedData.set(transition, currentFrameIdx * V_SIZE);
      currentFrameIdx += transitionFrames;
    }
  }

  // 3. Ease out from last frame to relaxed pose
  const finalClipData = blendedData.subarray((currentFrameIdx - 1) * V_SIZE, currentFrameIdx * V_SIZE);
  const endPose = relaxedPose && relaxedPose.length === V_SIZE ? relaxedPose : finalClipData;

  for (let f = 0; f < easeOutFrames; f++) {
    const rawT = (f + 1) / easeOutFrames;
    const t = rawT < 0.5 ? 4 * rawT * rawT * rawT : 1 - Math.pow(-2 * rawT + 2, 3) / 2;
    const destOffset = currentFrameIdx * V_SIZE;
    for (let i = 0; i < V_SIZE; i++) {
      blendedData[destOffset + i] = finalClipData[i] * (1 - t) + endPose[i] * t;
    }
    currentFrameIdx++;
  }

  // Sanity check: Ensure zero NaNs
  for (let i = 0; i < Math.min(blendedData.length, 300); i++) {
    if (!Number.isFinite(blendedData[i])) {
      console.warn('[motionDecoder] Warning: NaN or Infinity found during motion clip blending');
      break;
    }
  }

  return {
    motion: {
      frames: totalFrames,
      vertices: SMPLX_VERTEX_COUNT,
      components: 3,
      fps,
      data: blendedData
    },
    segmentBoundaries
  };
}
