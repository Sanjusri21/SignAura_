/**
 * Experimental Procedural Hand-Pose Registry
 *
 * Provides structured metadata and joint transform configurations for an experimental
 * Three.js procedural articulated hand prototype (Alphabet A–Z and Digits 0–9).
 *
 * CRITICAL SAFEGUARDS:
 * - This is an engineering visualization and technical feasibility prototype,
 *   NOT a validated Indian Sign Language (ISL) fingerspelling implementation.
 * - NO pose in this registry is marked 'expert-validated' because no authoritative
 *   ISL linguistic review has been conducted on procedural finger joint heuristics.
 * - This registry is strictly isolated from production SMPL-X sequence synthesis,
 *   lexical sign resolution, and motion caching.
 */

export type PoseCategory = 'alphabet' | 'digit';

export type PoseStatus = 'experimental' | 'unavailable' | 'expert-validated';

export interface FingerJointAngles {
  /** Metacarpophalangeal (base knuckle) flexion in radians (0 = fully extended, >0 = flexed towards palm) */
  mcpFlexion: number;
  /** Metacarpophalangeal lateral spread / yaw in radians (negative = adducted/inward, positive = abducted/outward) */
  mcpAbduction?: number;
  /** Proximal interphalangeal (middle knuckle) flexion in radians */
  pipFlexion: number;
  /** Distal interphalangeal (fingertip joint) flexion in radians */
  dipFlexion: number;
}

export interface ProceduralHandPoseData {
  /** Optional wrist rotation in radians [x, y, z] */
  wristRotation?: [number, number, number];
  thumb: FingerJointAngles;
  index: FingerJointAngles;
  middle: FingerJointAngles;
  ring: FingerJointAngles;
  pinky: FingerJointAngles;
}

export interface ExperimentalHandPoseEntry {
  /** Stable unique identifier (e.g., 'alpha_A', 'digit_1') */
  id: string;
  category: PoseCategory;
  symbol: string;
  status: PoseStatus;
  sourceDescription: string;
  validationReference?: string;
  validationNotes: string;
  poseData?: ProceduralHandPoseData;
}

/**
 * Neutral resting hand pose (relaxed open hand, slight natural finger curvature).
 */
export function getNeutralHandPose(): ProceduralHandPoseData {
  return {
    wristRotation: [0, 0, 0],
    thumb: { mcpFlexion: 0.15, mcpAbduction: 0.25, pipFlexion: 0.1, dipFlexion: 0.05 },
    index: { mcpFlexion: 0.08, mcpAbduction: 0.02, pipFlexion: 0.1, dipFlexion: 0.05 },
    middle: { mcpFlexion: 0.08, mcpAbduction: 0.0, pipFlexion: 0.1, dipFlexion: 0.05 },
    ring: { mcpFlexion: 0.08, mcpAbduction: -0.02, pipFlexion: 0.1, dipFlexion: 0.05 },
    pinky: { mcpFlexion: 0.1, mcpAbduction: -0.05, pipFlexion: 0.12, dipFlexion: 0.08 },
  };
}

/**
 * Closed fist joint parameters helper.
 */
function makeFistAngles(abduction = 0.0): FingerJointAngles {
  return { mcpFlexion: 1.5, mcpAbduction: abduction, pipFlexion: 1.5, dipFlexion: 1.2 };
}

/**
 * Extended straight finger joint parameters helper.
 */
function makeExtendedAngles(abduction = 0.0): FingerJointAngles {
  return { mcpFlexion: 0.05, mcpAbduction: abduction, pipFlexion: 0.05, dipFlexion: 0.02 };
}

/**
 * Curled (hook/arc) finger joint parameters helper.
 */
function makeCurledAngles(abduction = 0.0): FingerJointAngles {
  return { mcpFlexion: 0.8, mcpAbduction: abduction, pipFlexion: 0.9, dipFlexion: 0.7 };
}

/**
 * Explicit registry entries for Alphabet (A–Z).
 * Each letter has a distinct ID ('alpha_A' through 'alpha_Z').
 * Entries without verifiable single-hand procedural definitions are explicitly marked 'unavailable'.
 */
const ALPHABET_REGISTRY: Record<string, ExperimentalHandPoseEntry> = {
  A: {
    id: 'alpha_A',
    category: 'alphabet',
    symbol: 'A',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: closed fist with upright thumb alongside index finger.',
    validationNotes: 'Experimental procedural approximation. In authentic ISL, letter A is typically a two-handed contact sign. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.2, mcpAbduction: 0.05, pipFlexion: 0.1, dipFlexion: 0.05 },
      index: makeFistAngles(0.0),
      middle: makeFistAngles(0.0),
      ring: makeFistAngles(-0.02),
      pinky: makeFistAngles(-0.04),
    },
  },
  B: {
    id: 'alpha_B',
    category: 'alphabet',
    symbol: 'B',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: four extended upright fingers with thumb tucked across palm.',
    validationNotes: 'Experimental procedural approximation. In authentic ISL, letter B is a two-handed circle-touch sign. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.3, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.02),
      middle: makeExtendedAngles(0.0),
      ring: makeExtendedAngles(-0.02),
      pinky: makeExtendedAngles(-0.04),
    },
  },
  C: {
    id: 'alpha_C',
    category: 'alphabet',
    symbol: 'C',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: all fingers and thumb curved into an open C contour.',
    validationNotes: 'Experimental procedural approximation. Visual geometric C shape. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.7, mcpAbduction: 0.4, pipFlexion: 0.6, dipFlexion: 0.5 },
      index: makeCurledAngles(0.02),
      middle: makeCurledAngles(0.0),
      ring: makeCurledAngles(-0.02),
      pinky: makeCurledAngles(-0.04),
    },
  },
  D: {
    id: 'alpha_D',
    category: 'alphabet',
    symbol: 'D',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: upright index finger with thumb and remaining fingers curved into loop.',
    validationNotes: 'Experimental procedural approximation. Authentic ISL letter D requires two-handed contact (left arc, right stem). Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.1, mcpAbduction: 0.1, pipFlexion: 0.8, dipFlexion: 0.6 },
      index: makeExtendedAngles(0.0),
      middle: makeFistAngles(0.0),
      ring: makeFistAngles(-0.02),
      pinky: makeFistAngles(-0.04),
    },
  },
  E: {
    id: 'alpha_E',
    category: 'alphabet',
    symbol: 'E',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: all four fingers tightly curled with thumb tucked below.',
    validationNotes: 'Experimental procedural approximation. Authentic ISL letter E is two-handed index-touch. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.4, mcpAbduction: -0.2, pipFlexion: 1.0, dipFlexion: 0.8 },
      index: { mcpFlexion: 1.4, mcpAbduction: 0.0, pipFlexion: 1.4, dipFlexion: 1.0 },
      middle: { mcpFlexion: 1.4, mcpAbduction: 0.0, pipFlexion: 1.4, dipFlexion: 1.0 },
      ring: { mcpFlexion: 1.4, mcpAbduction: -0.02, pipFlexion: 1.4, dipFlexion: 1.0 },
      pinky: { mcpFlexion: 1.4, mcpAbduction: -0.04, pipFlexion: 1.4, dipFlexion: 1.0 },
    },
  },
  F: {
    id: 'alpha_F',
    category: 'alphabet',
    symbol: 'F',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: thumb and index tips touching, remaining three fingers extended upright.',
    validationNotes: 'Experimental procedural approximation. Authentic ISL letter F is two-handed interlock. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.9, mcpAbduction: 0.3, pipFlexion: 0.7, dipFlexion: 0.5 },
      index: { mcpFlexion: 0.9, mcpAbduction: 0.0, pipFlexion: 1.0, dipFlexion: 0.7 },
      middle: makeExtendedAngles(0.05),
      ring: makeExtendedAngles(0.0),
      pinky: makeExtendedAngles(-0.05),
    },
  },
  G: {
    id: 'alpha_G',
    category: 'alphabet',
    symbol: 'G',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter G is two closed fists stacked vertically (two-handed gesture).',
    validationNotes: 'Unavailable on single-hand procedural rig. No authentic single-hand representation exists in standard two-handed ISL. Not fabricated.',
  },
  H: {
    id: 'alpha_H',
    category: 'alphabet',
    symbol: 'H',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter H is a two-handed horizontal palm sweep gesture.',
    validationNotes: 'Unavailable on single-hand procedural rig. Authentic ISL letter H requires two hands in contact. Not fabricated.',
  },
  I: {
    id: 'alpha_I',
    category: 'alphabet',
    symbol: 'I',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: pinky finger extended upright, thumb folded over closed fist.',
    validationNotes: 'Experimental procedural approximation. Authentic ISL letter I is right index contacting left middle fingertip. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.2, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeFistAngles(0.0),
      middle: makeFistAngles(0.0),
      ring: makeFistAngles(-0.02),
      pinky: makeExtendedAngles(0.0),
    },
  },
  J: {
    id: 'alpha_J',
    category: 'alphabet',
    symbol: 'J',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter J is a dynamic traced motion gesture.',
    validationNotes: 'Unavailable as a static hand shape. Requires dynamic path tracing. Not fabricated.',
  },
  K: {
    id: 'alpha_K',
    category: 'alphabet',
    symbol: 'K',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter K requires two hands (left upright index, right bent index).',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  L: {
    id: 'alpha_L',
    category: 'alphabet',
    symbol: 'L',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: thumb and index finger extended at right angle forming L, other fingers folded.',
    validationNotes: 'Experimental procedural approximation. Geometric L configuration. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.05, mcpAbduction: 0.7, pipFlexion: 0.05, dipFlexion: 0.02 },
      index: makeExtendedAngles(0.0),
      middle: makeFistAngles(0.0),
      ring: makeFistAngles(-0.02),
      pinky: makeFistAngles(-0.04),
    },
  },
  M: {
    id: 'alpha_M',
    category: 'alphabet',
    symbol: 'M',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter M requires right three fingers placed upon flat left palm (two-handed).',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  N: {
    id: 'alpha_N',
    category: 'alphabet',
    symbol: 'N',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter N requires right two fingers placed upon flat left palm (two-handed).',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  O: {
    id: 'alpha_O',
    category: 'alphabet',
    symbol: 'O',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: all four fingertips curve to touch thumb tip forming O circle.',
    validationNotes: 'Experimental procedural approximation. Geometric O circle. In authentic ISL, letter O is index contact on left ring fingertip. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.8, mcpAbduction: 0.35, pipFlexion: 0.8, dipFlexion: 0.6 },
      index: { mcpFlexion: 0.9, mcpAbduction: 0.05, pipFlexion: 0.9, dipFlexion: 0.7 },
      middle: { mcpFlexion: 0.95, mcpAbduction: 0.0, pipFlexion: 0.95, dipFlexion: 0.7 },
      ring: { mcpFlexion: 0.95, mcpAbduction: -0.05, pipFlexion: 0.95, dipFlexion: 0.7 },
      pinky: { mcpFlexion: 0.95, mcpAbduction: -0.08, pipFlexion: 0.95, dipFlexion: 0.7 },
    },
  },
  P: {
    id: 'alpha_P',
    category: 'alphabet',
    symbol: 'P',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter P is a two-handed contact sign (left index upright, right circular loop).',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  Q: {
    id: 'alpha_Q',
    category: 'alphabet',
    symbol: 'Q',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter Q is a two-handed circle and hook sign.',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  R: {
    id: 'alpha_R',
    category: 'alphabet',
    symbol: 'R',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter R requires crossed fingers resting on open opposite palm (two-handed).',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  S: {
    id: 'alpha_S',
    category: 'alphabet',
    symbol: 'S',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter S is two little fingers hooked together (two-handed).',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  T: {
    id: 'alpha_T',
    category: 'alphabet',
    symbol: 'T',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter T is left upright index with right horizontal index touching top.',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  U: {
    id: 'alpha_U',
    category: 'alphabet',
    symbol: 'U',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: index and middle fingers extended upright together, other fingers folded.',
    validationNotes: 'Experimental procedural approximation. Authentic ISL letter U is contact on left pinky tip. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.2, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.0),
      middle: makeExtendedAngles(0.0),
      ring: makeFistAngles(-0.02),
      pinky: makeFistAngles(-0.04),
    },
  },
  V: {
    id: 'alpha_V',
    category: 'alphabet',
    symbol: 'V',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: index and middle fingers extended and spread in V shape.',
    validationNotes: 'Experimental procedural approximation. Geometric V shape. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.2, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.12),
      middle: makeExtendedAngles(-0.12),
      ring: makeFistAngles(-0.02),
      pinky: makeFistAngles(-0.04),
    },
  },
  W: {
    id: 'alpha_W',
    category: 'alphabet',
    symbol: 'W',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: index, middle, and ring fingers extended and spread in W shape.',
    validationNotes: 'Experimental procedural approximation. Geometric W shape. In authentic ISL, letter W is dual-hand interlocked upright fingers. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.2, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.14),
      middle: makeExtendedAngles(0.0),
      ring: makeExtendedAngles(-0.14),
      pinky: makeFistAngles(-0.04),
    },
  },
  X: {
    id: 'alpha_X',
    category: 'alphabet',
    symbol: 'X',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter X is two index fingers crossed forming an X shape (two-handed).',
    validationNotes: 'Unavailable on single-hand procedural rig. Requires dual-hand contact. Not fabricated.',
  },
  Y: {
    id: 'alpha_Y',
    category: 'alphabet',
    symbol: 'Y',
    status: 'experimental',
    sourceDescription: 'Procedural single-hand approximation: thumb and pinky extended, middle three fingers folded.',
    validationNotes: 'Experimental procedural approximation. Geometric Y shape. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.1, mcpAbduction: 0.65, pipFlexion: 0.1, dipFlexion: 0.05 },
      index: makeFistAngles(0.0),
      middle: makeFistAngles(0.0),
      ring: makeFistAngles(-0.02),
      pinky: makeExtendedAngles(-0.2),
    },
  },
  Z: {
    id: 'alpha_Z',
    category: 'alphabet',
    symbol: 'Z',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL letter Z is a dynamic tracing gesture against open palm.',
    validationNotes: 'Unavailable as a static single-hand pose. Requires dynamic motion path and dual-hand reference. Not fabricated.',
  },
};

/**
 * Explicit registry entries for Digits (0–9).
 * Each digit has a distinct ID ('digit_0' through 'digit_9').
 */
const DIGIT_REGISTRY: Record<string, ExperimentalHandPoseEntry> = {
  '0': {
    id: 'digit_0',
    category: 'digit',
    symbol: '0',
    status: 'experimental',
    sourceDescription: 'Procedural numeral approximation: closed circle formation (similar to O shape).',
    validationNotes: 'Experimental procedural numeral approximation. Authentic ISL numerical signs vary regionally. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.8, mcpAbduction: 0.35, pipFlexion: 0.8, dipFlexion: 0.6 },
      index: { mcpFlexion: 0.9, mcpAbduction: 0.05, pipFlexion: 0.9, dipFlexion: 0.7 },
      middle: { mcpFlexion: 0.95, mcpAbduction: 0.0, pipFlexion: 0.95, dipFlexion: 0.7 },
      ring: { mcpFlexion: 0.95, mcpAbduction: -0.05, pipFlexion: 0.95, dipFlexion: 0.7 },
      pinky: { mcpFlexion: 0.95, mcpAbduction: -0.08, pipFlexion: 0.95, dipFlexion: 0.7 },
    },
  },
  '1': {
    id: 'digit_1',
    category: 'digit',
    symbol: '1',
    status: 'experimental',
    sourceDescription: 'Procedural numeral approximation: upright index finger with remaining fingers closed.',
    validationNotes: 'Experimental procedural numeral approximation. Counting gesture. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.2, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.0),
      middle: makeFistAngles(0.0),
      ring: makeFistAngles(-0.02),
      pinky: makeFistAngles(-0.04),
    },
  },
  '2': {
    id: 'digit_2',
    category: 'digit',
    symbol: '2',
    status: 'experimental',
    sourceDescription: 'Procedural numeral approximation: upright index and middle fingers extended.',
    validationNotes: 'Experimental procedural numeral approximation. Counting gesture. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.2, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.05),
      middle: makeExtendedAngles(-0.05),
      ring: makeFistAngles(-0.02),
      pinky: makeFistAngles(-0.04),
    },
  },
  '3': {
    id: 'digit_3',
    category: 'digit',
    symbol: '3',
    status: 'experimental',
    sourceDescription: 'Procedural numeral approximation: upright index, middle, and ring fingers extended.',
    validationNotes: 'Experimental procedural numeral approximation. Counting gesture. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.3, mcpAbduction: -0.2, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.08),
      middle: makeExtendedAngles(0.0),
      ring: makeExtendedAngles(-0.08),
      pinky: makeFistAngles(-0.04),
    },
  },
  '4': {
    id: 'digit_4',
    category: 'digit',
    symbol: '4',
    status: 'experimental',
    sourceDescription: 'Procedural numeral approximation: four fingers extended upright with thumb folded across palm.',
    validationNotes: 'Experimental procedural numeral approximation. Counting gesture. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 1.4, mcpAbduction: -0.3, pipFlexion: 0.9, dipFlexion: 0.7 },
      index: makeExtendedAngles(0.06),
      middle: makeExtendedAngles(0.02),
      ring: makeExtendedAngles(-0.02),
      pinky: makeExtendedAngles(-0.06),
    },
  },
  '5': {
    id: 'digit_5',
    category: 'digit',
    symbol: '5',
    status: 'experimental',
    sourceDescription: 'Procedural numeral approximation: all five fingers fully extended open hand.',
    validationNotes: 'Experimental procedural numeral approximation. Counting gesture. Not validated by Deaf ISL linguistic authorities.',
    poseData: {
      thumb: { mcpFlexion: 0.05, mcpAbduction: 0.5, pipFlexion: 0.05, dipFlexion: 0.02 },
      index: makeExtendedAngles(0.08),
      middle: makeExtendedAngles(0.02),
      ring: makeExtendedAngles(-0.02),
      pinky: makeExtendedAngles(-0.08),
    },
  },
  '6': {
    id: 'digit_6',
    category: 'digit',
    symbol: '6',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL numeral 6 is typically a two-handed gesture or complex base-5 combination.',
    validationNotes: 'Unavailable on single-hand procedural rig without authoritative two-handed kinematic reference. Not fabricated.',
  },
  '7': {
    id: 'digit_7',
    category: 'digit',
    symbol: '7',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL numeral 7 is a compound or two-handed gesture.',
    validationNotes: 'Unavailable on single-hand procedural rig. Not fabricated.',
  },
  '8': {
    id: 'digit_8',
    category: 'digit',
    symbol: '8',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL numeral 8 is a compound or two-handed gesture.',
    validationNotes: 'Unavailable on single-hand procedural rig. Not fabricated.',
  },
  '9': {
    id: 'digit_9',
    category: 'digit',
    symbol: '9',
    status: 'unavailable',
    sourceDescription: 'Authentic ISL numeral 9 is a compound or two-handed gesture.',
    validationNotes: 'Unavailable on single-hand procedural rig. Not fabricated.',
  },
};

/**
 * Returns an entry by ID (e.g. 'alpha_A', 'digit_0').
 */
export function getExperimentalPoseById(id: string): ExperimentalHandPoseEntry | undefined {
  if (id.startsWith('alpha_')) {
    const symbol = id.replace('alpha_', '');
    return ALPHABET_REGISTRY[symbol];
  }
  if (id.startsWith('digit_')) {
    const symbol = id.replace('digit_', '');
    return DIGIT_REGISTRY[symbol];
  }
  return undefined;
}

/**
 * Returns all entries for a specific category ('alphabet' | 'digit') in canonical order.
 */
export function getPosesByCategory(category: PoseCategory): ExperimentalHandPoseEntry[] {
  if (category === 'alphabet') {
    return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map((c) => ALPHABET_REGISTRY[c]);
  }
  return '0123456789'.split('').map((d) => DIGIT_REGISTRY[d]);
}

/**
 * Returns all entries in the registry (36 entries total: 26 alphabet + 10 digits).
 */
export function getAllExperimentalPoses(): ExperimentalHandPoseEntry[] {
  return [
    ...getPosesByCategory('alphabet'),
    ...getPosesByCategory('digit'),
  ];
}
