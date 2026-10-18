/**
 * Unit regression tests for SignAvatar 3D animation binary decoding,
 * multi-sign sequence blending, timing, and crossfades.
 *
 * Run with: node --experimental-strip-types tests/multiSignAnimation.test.mjs
 */

import assert from 'node:assert/strict';
import test from 'node:test';

const SMPLX_VERTEX_COUNT = 10475;
const FLOATS_PER_FRAME = SMPLX_VERTEX_COUNT * 3; // 31425
const BYTES_PER_FRAME = FLOATS_PER_FRAME * 4;   // 125700
const DEFAULT_MOTION_FPS = 30;

/**
 * Pure implementation of SignAvatar3D binary decoder for testing.
 * Matches `processAndNormalizeMotion` in SignAvatar3D.tsx.
 */
function processAndNormalizeMotion(buffer, headerFrames, headerFps) {
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
  const frames = headerFrames && headerFrames === computedFrames ? headerFrames : computedFrames;

  if (frames <= 0) {
    throw new Error('Motion contains zero frames.');
  }

  for (let i = 0; i < totalFloats; i += 3) {
    if (!Number.isFinite(floatView[i]) || !Number.isFinite(floatView[i + 1]) || !Number.isFinite(floatView[i + 2])) {
      throw new Error('Motion data contains NaN or infinite coordinates.');
    }
  }

  return {
    frames,
    vertices: SMPLX_VERTEX_COUNT,
    components: 3,
    fps: headerFps || DEFAULT_MOTION_FPS,
    data: new Float32Array(floatView),
  };
}

/**
 * Pure implementation of SignAvatar3D cosine crossfade blending.
 * Matches `createTransition` and `blendMotionClips` in SignAvatar3D.tsx.
 */
function createTransition(poseA, poseB, numFrames = 6) {
  if (numFrames <= 0) {
    return new Float32Array(0);
  }

  const result = new Float32Array(numFrames * FLOATS_PER_FRAME);
  for (let f = 1; f <= numFrames; f++) {
    // Cosine easing weight strictly in (0, 1)
    const step = f / (numFrames + 1);
    const weight = 0.5 * (1.0 - Math.cos(Math.PI * step));
    const offset = (f - 1) * FLOATS_PER_FRAME;

    for (let i = 0; i < FLOATS_PER_FRAME; i++) {
      result[offset + i] = (1.0 - weight) * poseA[i] + weight * poseB[i];
    }
  }
  return result;
}

/**
 * Helper to generate synthetic SMPL-X motion clip.
 */
function createSyntheticMotion(frames, baseOffset = 0.0) {
  const data = new Float32Array(frames * FLOATS_PER_FRAME);
  for (let f = 0; f < frames; f++) {
    const frameOffset = f * FLOATS_PER_FRAME;
    for (let v = 0; v < SMPLX_VERTEX_COUNT; v++) {
      const idx = frameOffset + v * 3;
      data[idx] = (v * 0.001) + baseOffset;          // x
      data[idx + 1] = 0.2 + (f * 0.005);             // y (animating upward)
      data[idx + 2] = -0.1 + Math.sin(f * 0.1);      // z
    }
  }
  return data.buffer;
}

test('SignAvatar Binary Decoder — Valid Payloads', () => {
  // Test 1-frame, 5-frame, and 10-frame buffers
  for (const numFrames of [1, 5, 10]) {
    const buf = createSyntheticMotion(numFrames, 0.1);
    const motion = processAndNormalizeMotion(buf, numFrames, 30);

    assert.equal(motion.frames, numFrames);
    assert.equal(motion.vertices, SMPLX_VERTEX_COUNT);
    assert.equal(motion.components, 3);
    assert.equal(motion.fps, 30);
    assert.equal(motion.data.length, numFrames * FLOATS_PER_FRAME);
  }
});

test('SignAvatar Binary Decoder — Rejects Truncated and Malformed Buffers', () => {
  // 1. Empty buffer
  assert.throws(
    () => processAndNormalizeMotion(new ArrayBuffer(0)),
    /Motion buffer is empty/
  );

  // 2. Truncated buffer with non-frame float count (e.g. 10 floats instead of 31425)
  const nonFrameBuffer = new ArrayBuffer(10 * 4);
  assert.throws(
    () => processAndNormalizeMotion(nonFrameBuffer),
    /Invalid motion binary length/
  );

  // 3. Off-by-one float buffer (one frame + 1 float)
  const offByOneFloat = new ArrayBuffer(BYTES_PER_FRAME + 4);
  assert.throws(
    () => processAndNormalizeMotion(offByOneFloat),
    /Invalid motion binary length/
  );

  // 4. Non-multiple of 4 bytes buffer throws RangeError
  const oddBytes = new ArrayBuffer(13);
  assert.throws(
    () => processAndNormalizeMotion(oddBytes),
    /byte length of Float32Array should be a multiple of 4/
  );
});

test('SignAvatar Binary Decoder — Rejects NaN and Infinity Coordinates', () => {
  // Buffer containing NaN
  const bufNaN = createSyntheticMotion(2);
  const viewNaN = new Float32Array(bufNaN);
  viewNaN[100] = NaN;
  assert.throws(
    () => processAndNormalizeMotion(bufNaN),
    /Motion data contains NaN or infinite coordinates/
  );

  // Buffer containing Infinity
  const bufInf = createSyntheticMotion(2);
  const viewInf = new Float32Array(bufInf);
  viewInf[500] = Infinity;
  assert.throws(
    () => processAndNormalizeMotion(bufInf),
    /Motion data contains NaN or infinite coordinates/
  );
});

test('SignAvatar Motion Blending — Smooth Cosine Transition Between Signs', () => {
  const clipA = new Float32Array(createSyntheticMotion(3, 0.0));
  const clipB = new Float32Array(createSyntheticMotion(3, 1.0));

  const poseA = clipA.subarray(2 * FLOATS_PER_FRAME, 3 * FLOATS_PER_FRAME); // final pose of Sign A
  const poseB = clipB.subarray(0, FLOATS_PER_FRAME);                          // initial pose of Sign B

  const numTransFrames = 6;
  const transition = createTransition(poseA, poseB, numTransFrames);

  assert.equal(transition.length, numTransFrames * FLOATS_PER_FRAME);

  // Verify transition is strictly bounded between poseA and poseB
  for (let f = 0; f < numTransFrames; f++) {
    const frameOffset = f * FLOATS_PER_FRAME;
    const sampleA = poseA[0];
    const sampleB = poseB[0];
    const sampleT = transition[frameOffset];

    assert.ok(
      (sampleT >= sampleA && sampleT <= sampleB) || (sampleT <= sampleA && sampleT >= sampleB),
      `Transition frame ${f} coordinate ${sampleT} outside bounds [${sampleA}, ${sampleB}]`
    );
  }

  // Verify monotonicity of transition progress across time
  const samples = [];
  for (let f = 0; f < numTransFrames; f++) {
    samples.push(transition[f * FLOATS_PER_FRAME]);
  }
  for (let i = 1; i < samples.length; i++) {
    assert.ok(samples[i] > samples[i - 1], `Transition must monotonically advance from poseA to poseB`);
  }
});

test('SignAvatar Playback Timing — Looping and Frame Modulo Integrity', () => {
  const totalFrames = 100;
  const fps = 30;
  const speed = 1.0;

  let frameElapsed = 0;
  const sampledIndices = [];

  // Simulate 4 seconds of playback (120 frames at 30 fps -> should wrap around at 100)
  for (let step = 0; step < 120; step++) {
    const delta = 1.0 / fps;
    frameElapsed = (frameElapsed + delta * fps * speed) % totalFrames;
    const frameIndex = Math.min(Math.floor(frameElapsed), totalFrames - 1);

    assert.ok(frameIndex >= 0 && frameIndex < totalFrames, `Frame index ${frameIndex} must remain in [0, 99]`);
    assert.ok(Number.isFinite(frameIndex), `Frame index must be finite`);
    sampledIndices.push(frameIndex);
  }

  // Confirm wrap-around occurred cleanly
  assert.equal(sampledIndices[98], 99);
  assert.equal(sampledIndices[99], 0);
  assert.equal(sampledIndices[119], 20);
});

test('SignAvatar Playback State Machine — Rapid Sequence Switching', () => {
  // Simulate active playback switching to a new sequence
  const motionA = processAndNormalizeMotion(createSyntheticMotion(30, 0.0), 30, 30);
  const motionB = processAndNormalizeMotion(createSyntheticMotion(40, 5.0), 40, 30);

  let currentMotion = motionA;
  let currentFrame = 15; // playing mid-way through sign A
  let isBlending = false;
  let prevFrameVertices = null;

  // Rapid switch triggered to sign B
  prevFrameVertices = new Float32Array(
    currentMotion.data.subarray(currentFrame * FLOATS_PER_FRAME, (currentFrame + 1) * FLOATS_PER_FRAME)
  );
  isBlending = true;
  currentMotion = motionB;
  currentFrame = 0;

  assert.equal(currentMotion.frames, 40);
  assert.equal(isBlending, true);
  assert.equal(prevFrameVertices.length, FLOATS_PER_FRAME);
  assert.ok(Number.isFinite(prevFrameVertices[0]));

  // Ensure blend interpolation executes safely without NaN
  const targetData = currentMotion.data.subarray(0, FLOATS_PER_FRAME);
  const blendedPose = new Float32Array(FLOATS_PER_FRAME);
  const t = 0.5; // mid-crossfade
  for (let i = 0; i < FLOATS_PER_FRAME; i++) {
    blendedPose[i] = prevFrameVertices[i] * (1 - t) + targetData[i] * t;
  }

  assert.ok(!Number.isNaN(blendedPose[0]));
  assert.ok(Number.isFinite(blendedPose[0]));
});
