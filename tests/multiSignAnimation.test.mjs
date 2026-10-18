/**
 * Unit regression tests exercising production SMPL-X motion decoding,
 * normalization, frame timing, and multi-clip transition blending.
 *
 * Directly imports and verifies production utilities from `src/utils/motionDecoder.ts`.
 * Run with: node --experimental-strip-types tests/multiSignAnimation.test.mjs
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  SMPLX_VERTEX_COUNT,
  SMPLX_FACE_COUNT,
  DEFAULT_MOTION_FPS,
  FLOATS_PER_FRAME,
  BYTES_PER_FRAME,
  processAndNormalizeMotion,
  createTransition,
  calculateFrameIndex,
  blendMotionClips,
} from '../src/utils/motionDecoder.ts';

/**
 * Helper to generate synthetic SMPL-X motion binary buffer matching production schema.
 */
function createSyntheticMotion(frames, baseOffset = 0.0) {
  const data = new Float32Array(frames * FLOATS_PER_FRAME);
  for (let f = 0; f < frames; f++) {
    const frameOffset = f * FLOATS_PER_FRAME;
    for (let v = 0; v < SMPLX_VERTEX_COUNT; v++) {
      const idx = frameOffset + v * 3;
      data[idx] = (v * 0.001) + baseOffset;          // x
      data[idx + 1] = 0.2 + (f * 0.005);             // y (upward animation)
      data[idx + 2] = -0.1 + Math.sin(f * 0.1);      // z
    }
  }
  return data.buffer;
}

test('Production Motion Decoder — Valid Float32 Payloads & Frame Stride', () => {
  assert.equal(SMPLX_VERTEX_COUNT, 10475);
  assert.equal(FLOATS_PER_FRAME, 31425);
  assert.equal(BYTES_PER_FRAME, 125700);

  // Test 1-frame, 5-frame, and 10-frame buffers using production decoder
  for (const numFrames of [1, 5, 10]) {
    const buf = createSyntheticMotion(numFrames, 0.25);
    const motion = processAndNormalizeMotion(buf, numFrames, 30);

    assert.equal(motion.frames, numFrames);
    assert.equal(motion.vertices, SMPLX_VERTEX_COUNT);
    assert.equal(motion.components, 3);
    assert.equal(motion.fps, 30);
    assert.equal(motion.data.length, numFrames * FLOATS_PER_FRAME);
    assert.equal(motion.data.byteLength, numFrames * BYTES_PER_FRAME);

    // Verify first coordinate reflects the base offset exactly
    assert.ok(Math.abs(motion.data[0] - 0.25) < 1e-6);
  }
});

test('Production Motion Decoder — Rejects Truncated, Non-Stride, and Malformed Payloads', () => {
  // 1. Empty buffer
  assert.throws(
    () => processAndNormalizeMotion(new ArrayBuffer(0)),
    /Motion buffer is empty/
  );

  // 2. Truncated buffer (arbitrary non-frame byte count)
  const nonFrameBuffer = new ArrayBuffer(50 * 4); // 200 bytes
  assert.throws(
    () => processAndNormalizeMotion(nonFrameBuffer),
    /Invalid motion binary length/
  );

  // 3. Off-by-one float buffer (1 frame + 1 float = 125,704 bytes)
  const offByOneFloat = new ArrayBuffer(BYTES_PER_FRAME + 4);
  assert.throws(
    () => processAndNormalizeMotion(offByOneFloat),
    /Invalid motion binary length/
  );

  // 4. Non-multiple of 4 bytes (e.g. 13 bytes) triggers Float32Array RangeError
  const oddBytes = new ArrayBuffer(13);
  assert.throws(
    () => processAndNormalizeMotion(oddBytes),
    /byte length of Float32Array should be a multiple of 4/
  );
});

test('Production Motion Decoder — Rejects NaN and Infinite Coordinates', () => {
  // Buffer containing NaN coordinate
  const bufNaN = createSyntheticMotion(2);
  const viewNaN = new Float32Array(bufNaN);
  viewNaN[100] = NaN;
  assert.throws(
    () => processAndNormalizeMotion(bufNaN),
    /Motion data contains NaN or infinite coordinates/
  );

  // Buffer containing Infinity coordinate
  const bufInf = createSyntheticMotion(2);
  const viewInf = new Float32Array(bufInf);
  viewInf[500] = Infinity;
  assert.throws(
    () => processAndNormalizeMotion(bufInf),
    /Motion data contains NaN or infinite coordinates/
  );

  // Buffer containing -Infinity coordinate
  const bufNegInf = createSyntheticMotion(2);
  const viewNegInf = new Float32Array(bufNegInf);
  viewNegInf[1000] = -Infinity;
  assert.throws(
    () => processAndNormalizeMotion(bufNegInf),
    /Motion data contains NaN or infinite coordinates/
  );
});

test('Production Motion Blending — Cosine Transition Between Clips', () => {
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

test('Production Multi-Clip Blending — Segment Boundaries & Hold Frames', () => {
  const motionA = processAndNormalizeMotion(createSyntheticMotion(10, 0.0), 10, 30);
  const motionB = processAndNormalizeMotion(createSyntheticMotion(15, 1.0), 15, 30);

  const blended = blendMotionClips(
    [
      { gloss: 'SIGN_A', motion: motionA },
      { gloss: 'SIGN_B', motion: motionB },
    ],
    null,
    { holdFrames: 4, transitionFrames: 6, easeInFrames: 8, easeOutFrames: 10 }
  );

  // Expected frame calculation:
  // easeIn(8) + clipA(10) + hold(4) + trans(6) + clipB(15) + hold(4) + easeOut(10) = 57 frames
  const expectedTotal = 8 + 10 + 4 + 6 + 15 + 4 + 10;
  assert.equal(blended.motion.frames, expectedTotal);
  assert.equal(blended.segmentBoundaries.length, 2);

  // Segment boundaries check
  assert.equal(blended.segmentBoundaries[0].gloss, 'SIGN_A');
  assert.equal(blended.segmentBoundaries[0].startFrame, 8);
  assert.equal(blended.segmentBoundaries[0].endFrame, 8 + 10 + 4 - 1); // 21

  assert.equal(blended.segmentBoundaries[1].gloss, 'SIGN_B');
  assert.equal(blended.segmentBoundaries[1].startFrame, 22 + 6); // 28
});

test('Production Playback Timing — calculateFrameIndex Modulo & Wrap-Around', () => {
  const totalFrames = 100;
  const fps = 30;
  const speed = 1.0;
  const deltaSec = 1.0 / fps;

  let currentElapsed = 0;
  const sampledIndices = [];

  for (let step = 0; step < 120; step++) {
    const { nextElapsed, frameIndex } = calculateFrameIndex(
      currentElapsed,
      deltaSec,
      fps,
      speed,
      totalFrames
    );
    currentElapsed = nextElapsed;
    sampledIndices.push(frameIndex);
    assert.ok(frameIndex >= 0 && frameIndex < totalFrames);
  }

  // Confirm wrap-around occurred cleanly across totalFrames
  assert.equal(sampledIndices[98], 99);
  assert.equal(sampledIndices[99], 0);
  assert.equal(sampledIndices[119], 20);
});

test('Production Decoder Stride Contract — Deliberate Stride Mutation Sensitivity', () => {
  // Verify that any payload that diverges from exact 10,475 * 3 floats/frame is rejected
  const validBuffer = createSyntheticMotion(1);
  assert.equal(validBuffer.byteLength, 125700);

  // If stride were 10474 or 10476 vertices instead of 10475:
  const brokenStrideBuffer = new ArrayBuffer(10474 * 3 * 4);
  assert.throws(
    () => processAndNormalizeMotion(brokenStrideBuffer),
    /Invalid motion binary length/
  );

  const brokenStrideBuffer2 = new ArrayBuffer(10476 * 3 * 4);
  assert.throws(
    () => processAndNormalizeMotion(brokenStrideBuffer2),
    /Invalid motion binary length/
  );
});
