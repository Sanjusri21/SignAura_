/**
 * Regression test suite for Experimental Procedural Hand-Pose Registry & Safeguards.
 *
 * Verifies:
 * 1. Registry Integrity (A-Z and 0-9 count, uniqueness, explicit unavailable states, no false validation)
 * 2. Joint Data Sanity (Finite angles, physical bounds, neutral pose guarantees)
 * 3. Production Isolation (Strict namespace separation, no collision with authentic lexicon, unavailable state safety)
 *
 * Run with: node --experimental-strip-types tests/experimentalHandPose.test.mjs
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getAllExperimentalPoses,
  getPosesByCategory,
  getExperimentalPoseById,
  getNeutralHandPose,
} from '../src/lib/experimentalHandPoseRegistry.ts';

import {
  AUTHENTIC_ISL_LEXICON,
  isAuthenticSignAvailable,
} from '../src/lib/islFingerspelling.ts';

test('Registry Integrity — Alphabet entries (A–Z)', () => {
  const alphabetPoses = getPosesByCategory('alphabet');
  assert.equal(alphabetPoses.length, 26, 'Alphabet must contain exactly 26 entries');

  const symbols = alphabetPoses.map((p) => p.symbol).join('');
  assert.equal(symbols, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'Alphabet symbols must be A through Z in canonical order');

  alphabetPoses.forEach((p) => {
    assert.equal(p.category, 'alphabet', `Entry ${p.id} must have category 'alphabet'`);
    assert.match(p.id, /^alpha_[A-Z]$/, `ID ${p.id} must follow 'alpha_<letter>' schema`);
  });
});

test('Registry Integrity — Digit entries (0–9)', () => {
  const digitPoses = getPosesByCategory('digit');
  assert.equal(digitPoses.length, 10, 'Digits must contain exactly 10 entries');

  const symbols = digitPoses.map((p) => p.symbol).join('');
  assert.equal(symbols, '0123456789', 'Digit symbols must be 0 through 9 in canonical order');

  digitPoses.forEach((p) => {
    assert.equal(p.category, 'digit', `Entry ${p.id} must have category 'digit'`);
    assert.match(p.id, /^digit_[0-9]$/, `ID ${p.id} must follow 'digit_<number>' schema`);
  });
});

test('Registry Integrity — Unique IDs and Distinguishable Namespaces', () => {
  const allPoses = getAllExperimentalPoses();
  assert.equal(allPoses.length, 36, 'Total registry size must be exactly 36 (26 letters + 10 digits)');

  const ids = new Set(allPoses.map((p) => p.id));
  assert.equal(ids.size, 36, 'All 36 pose IDs must be strictly unique');

  // Verify lookup by ID
  const poseA = getExperimentalPoseById('alpha_A');
  assert.ok(poseA, 'alpha_A must be retrievable by ID');
  assert.equal(poseA?.symbol, 'A');

  const pose0 = getExperimentalPoseById('digit_0');
  assert.ok(pose0, 'digit_0 must be retrievable by ID');
  assert.equal(pose0?.symbol, '0');

  const nonExistent = getExperimentalPoseById('invalid_id');
  assert.equal(nonExistent, undefined, 'Invalid ID must return undefined');
});

test('Registry Integrity — Truthful Validation Status (No False Claims)', () => {
  const allPoses = getAllExperimentalPoses();

  // Safeguard: Zero entries may be marked 'expert-validated' without formal ISL expert review
  const validatedCount = allPoses.filter((p) => p.status === 'expert-validated').length;
  assert.equal(
    validatedCount,
    0,
    'CRITICAL: No experimental pose may be marked "expert-validated" without documented linguistic review'
  );

  // Safeguard: Poses requiring complex two-handed interlock gestures are explicitly marked 'unavailable'
  const unavailablePoses = allPoses.filter((p) => p.status === 'unavailable');
  assert.ok(unavailablePoses.length > 0, 'Unavailable gestures must be explicitly acknowledged, not fabricated');

  const unavailableSymbols = unavailablePoses.map((p) => p.symbol);
  // Letters G, H, J, K, M, N, P, Q, R, S, T, X, Z cannot be articulated on a single procedural hand
  assert.ok(unavailableSymbols.includes('G'), 'Letter G must be marked unavailable on single-hand rig');
  assert.ok(unavailableSymbols.includes('H'), 'Letter H must be marked unavailable on single-hand rig');
  assert.ok(unavailableSymbols.includes('Z'), 'Letter Z (dynamic trace) must be marked unavailable');

  // Ensure every unavailable entry contains explicit validation notes explaining why it is unavailable
  unavailablePoses.forEach((p) => {
    assert.ok(p.validationNotes && p.validationNotes.length > 10, `Entry ${p.id} must document why it is unavailable`);
    assert.equal(p.poseData, undefined, `Unavailable entry ${p.id} must not contain fabricated poseData`);
  });
});

test('Joint Data Sanity — Supported Experimental Poses', () => {
  const experimentalPoses = getAllExperimentalPoses().filter((p) => p.status === 'experimental');
  assert.ok(experimentalPoses.length > 0, 'There must be valid experimental poses for evaluation');

  experimentalPoses.forEach((p) => {
    assert.ok(p.poseData, `Experimental entry ${p.id} must have poseData`);
    const { thumb, index, middle, ring, pinky } = p.poseData;

    [thumb, index, middle, ring, pinky].forEach((digit) => {
      // Assert finite numbers
      assert.ok(Number.isFinite(digit.mcpFlexion), `mcpFlexion in ${p.id} must be finite`);
      assert.ok(Number.isFinite(digit.pipFlexion), `pipFlexion in ${p.id} must be finite`);
      assert.ok(Number.isFinite(digit.dipFlexion), `dipFlexion in ${p.id} must be finite`);

      // Assert physical joint angle bounds (within -0.2 to 2.2 rad flexion)
      assert.ok(digit.mcpFlexion >= -0.2 && digit.mcpFlexion <= 2.2, `mcpFlexion in ${p.id} out of bounds: ${digit.mcpFlexion}`);
      assert.ok(digit.pipFlexion >= 0.0 && digit.pipFlexion <= 2.2, `pipFlexion in ${p.id} out of bounds: ${digit.pipFlexion}`);
      assert.ok(digit.dipFlexion >= 0.0 && digit.dipFlexion <= 2.0, `dipFlexion in ${p.id} out of bounds: ${digit.dipFlexion}`);
    });
  });
});

test('Joint Data Sanity — Neutral Resting Pose', () => {
  const neutral = getNeutralHandPose();
  assert.ok(neutral, 'Neutral pose must be defined');

  const digits = [neutral.thumb, neutral.index, neutral.middle, neutral.ring, neutral.pinky];
  digits.forEach((digit) => {
    assert.ok(digit.mcpFlexion >= 0 && digit.mcpFlexion < 0.3, 'Neutral pose must have relaxed, near-zero flexion');
    assert.ok(digit.pipFlexion >= 0 && digit.pipFlexion < 0.3, 'Neutral pose must have relaxed PIP');
    assert.ok(digit.dipFlexion >= 0 && digit.dipFlexion < 0.2, 'Neutral pose must have relaxed DIP');
  });
});

test('Production Isolation — Namespace Separation & Lexicon Non-Collision', () => {
  const initialLexiconSize = AUTHENTIC_ISL_LEXICON.size;

  getAllExperimentalPoses().forEach((pose) => {
    // 1. Enforce strict namespace prefix separation:
    // Production sequences use 'sequence_*' or canonical vocabulary names.
    // Experimental IDs must strictly start with 'alpha_' or 'digit_'.
    assert.match(
      pose.id,
      /^(alpha_[A-Z]|digit_[0-9])$/,
      `Experimental ID ${pose.id} must use dedicated prefix namespace`
    );

    // 2. Assert no experimental ID exists in or collides with the authentic lexicon
    assert.equal(
      AUTHENTIC_ISL_LEXICON.has(pose.id.toUpperCase()),
      false,
      `Experimental ID ${pose.id} must NOT collide with authentic lexical signs`
    );

    // 3. Verify that authentic sign resolver reports false for experimental IDs
    assert.equal(
      isAuthenticSignAvailable(pose.id),
      false,
      `isAuthenticSignAvailable must return false for experimental ID ${pose.id}`
    );

    // 4. Verify that isolated alphabet/digit symbols are not recognized as authentic signs
    assert.equal(
      isAuthenticSignAvailable(pose.symbol),
      false,
      `Individual alphabet letter/digit ${pose.symbol} must not be marked authentic sign`
    );
  });

  // Verify authentic lexicon remains immutable
  assert.equal(AUTHENTIC_ISL_LEXICON.size, initialLexiconSize, 'AUTHENTIC_ISL_LEXICON size must remain constant');
});

test('Production Isolation — Unavailable State Safety (No Silent Fallback to Motion Assets)', () => {
  const unavailablePoses = getAllExperimentalPoses().filter((p) => p.status === 'unavailable');
  assert.equal(unavailablePoses.length, 17, 'Exactly 17 gestures must be explicitly marked unavailable');

  unavailablePoses.forEach((p) => {
    // Ensure poseData is undefined so no renderer can accidentally treat it as an available pose
    assert.equal(
      p.poseData,
      undefined,
      `Unavailable pose ${p.id} must have undefined poseData`
    );

    // Ensure metadata does not reference unrelated motion files or fallbacks
    const notesLower = (p.validationNotes + ' ' + p.sourceDescription).toLowerCase();
    assert.equal(
      notesLower.includes('welcome_help_you'),
      false,
      `Unavailable pose ${p.id} must NOT reference unrelated fallback 'welcome_help_you'`
    );
    assert.equal(
      notesLower.includes('.npy'),
      false,
      `Unavailable pose ${p.id} must NOT reference .npy motion files`
    );
  });
});
