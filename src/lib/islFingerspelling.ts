/**
 * Indian Sign Language (ISL) Two-Handed Fingerspelling Engine.
 * 
 * In ISL, fingerspelling is performed with both hands:
 * - A: Left palm open facing front/up; Right index contacts tip of left thumb.
 * - B: Both hands form two circles touching at knuckles to shape letter 'B'.
 * - C: Left hand curves into 'C' contour.
 * - D: Left hand forms arc with thumb/index; Right index forms upright stem.
 * - E: Right index contacts tip of left index finger.
 * - F: Left and right index/middle fingers interlock.
 * - G: Two closed fists with right fist placed above left fist.
 * - H: Left flat horizontal palm, right flat palm stroked across.
 * - I: Right index contacts tip of left middle finger.
 * - J: Right index contacts tip of left middle finger then traces a J hook downward.
 * - K: Left index upright, right index angled touching knuckle.
 * - L: Left thumb and index at right angle forming 'L'.
 * - M: Left flat palm facing up, right three fingers placed on left palm.
 * - N: Left flat palm, right two fingers placed on left palm.
 * - O: Right index contacts tip of left ring finger.
 * - P: Left upright index with right circular finger loop touching tip.
 * - Q: Left hand forms circle with right thumb hooked at bottom.
 * - R: Right crossed fingers resting on left palm.
 * - S: Left open palm with right closed fist interlocking.
 * - T: Left upright index with right index finger touching top horizontally.
 * - U: Right index contacts tip of left little finger.
 * - V: Left hand holds 'V' shape with right index touching between them.
 * - W: Both hands interlock spread fingers.
 * - X: Both index fingers crossed forming 'X'.
 * - Y: Left hand spread; right index points into center between thumb and index.
 * - Z: Left palm flat upright; right index traces a 'Z' in the air or against left palm.
 * - 0–9: Standard ISL two-handed numerical manual signs.
 */

export interface ISLCharConfig {
  char: string;
  name: string;
  hands: 'both' | 'right' | 'left';
  description: string;
  leftHandPose: { x: number; y: number; z: number; bend: number };
  rightHandPose: { x: number; y: number; z: number; bend: number };
}

export const ISL_TWO_HANDED_ALPHABET: Record<string, ISLCharConfig> = {
  A: {
    char: 'A',
    name: 'Letter A',
    hands: 'both',
    description: 'Left open palm; right index contacts tip of left thumb.',
    leftHandPose: { x: -0.15, y: 0.22, z: 0.28, bend: 0.1 },
    rightHandPose: { x: -0.11, y: 0.24, z: 0.28, bend: 0.6 }
  },
  B: {
    char: 'B',
    name: 'Letter B',
    hands: 'both',
    description: 'Both hands form loops touching at knuckles to shape B.',
    leftHandPose: { x: -0.06, y: 0.24, z: 0.30, bend: 0.7 },
    rightHandPose: { x: 0.06, y: 0.24, z: 0.30, bend: 0.7 }
  },
  C: {
    char: 'C',
    name: 'Letter C',
    hands: 'both',
    description: 'Right hand curves into a curved C contour facing left.',
    leftHandPose: { x: -0.18, y: 0.15, z: 0.22, bend: 0.2 },
    rightHandPose: { x: 0.08, y: 0.25, z: 0.28, bend: 0.5 }
  },
  D: {
    char: 'D',
    name: 'Letter D',
    hands: 'both',
    description: 'Left upright index with curved thumb; right index forms back stem.',
    leftHandPose: { x: -0.08, y: 0.26, z: 0.28, bend: 0.3 },
    rightHandPose: { x: 0.02, y: 0.26, z: 0.28, bend: 0.4 }
  },
  E: {
    char: 'E',
    name: 'Letter E',
    hands: 'both',
    description: 'Right index contacts tip of left index finger.',
    leftHandPose: { x: -0.14, y: 0.24, z: 0.28, bend: 0.2 },
    rightHandPose: { x: -0.08, y: 0.26, z: 0.28, bend: 0.7 }
  },
  F: {
    char: 'F',
    name: 'Letter F',
    hands: 'both',
    description: 'Left and right index fingers interlock across horizontally.',
    leftHandPose: { x: -0.05, y: 0.24, z: 0.29, bend: 0.4 },
    rightHandPose: { x: 0.04, y: 0.24, z: 0.29, bend: 0.4 }
  },
  G: {
    char: 'G',
    name: 'Letter G',
    hands: 'both',
    description: 'Two closed fists with right fist positioned above left fist.',
    leftHandPose: { x: 0.0, y: 0.18, z: 0.30, bend: 0.9 },
    rightHandPose: { x: 0.0, y: 0.28, z: 0.30, bend: 0.9 }
  },
  H: {
    char: 'H',
    name: 'Letter H',
    hands: 'both',
    description: 'Left flat horizontal palm; right flat palm sweeps across.',
    leftHandPose: { x: -0.10, y: 0.22, z: 0.28, bend: 0.1 },
    rightHandPose: { x: 0.05, y: 0.23, z: 0.28, bend: 0.2 }
  },
  I: {
    char: 'I',
    name: 'Letter I',
    hands: 'both',
    description: 'Right index contacts tip of left middle finger.',
    leftHandPose: { x: -0.14, y: 0.24, z: 0.28, bend: 0.2 },
    rightHandPose: { x: -0.06, y: 0.26, z: 0.28, bend: 0.7 }
  },
  J: {
    char: 'J',
    name: 'Letter J',
    hands: 'both',
    description: 'Right index touches left middle finger then curves into a J downward.',
    leftHandPose: { x: -0.14, y: 0.24, z: 0.28, bend: 0.2 },
    rightHandPose: { x: -0.04, y: 0.20, z: 0.30, bend: 0.6 }
  },
  K: {
    char: 'K',
    name: 'Letter K',
    hands: 'both',
    description: 'Left index upright; right index bends at knuckle against left index.',
    leftHandPose: { x: -0.08, y: 0.25, z: 0.28, bend: 0.1 },
    rightHandPose: { x: -0.02, y: 0.25, z: 0.28, bend: 0.8 }
  },
  L: {
    char: 'L',
    name: 'Letter L',
    hands: 'both',
    description: 'Left hand holds an L shape upright in signing space.',
    leftHandPose: { x: -0.12, y: 0.25, z: 0.28, bend: 0.1 },
    rightHandPose: { x: 0.14, y: 0.14, z: 0.20, bend: 0.2 }
  },
  M: {
    char: 'M',
    name: 'Letter M',
    hands: 'both',
    description: 'Left palm facing upward; right three fingers rest upon left palm.',
    leftHandPose: { x: -0.08, y: 0.18, z: 0.28, bend: 0.1 },
    rightHandPose: { x: -0.04, y: 0.22, z: 0.28, bend: 0.5 }
  },
  N: {
    char: 'N',
    name: 'Letter N',
    hands: 'both',
    description: 'Left palm facing upward; right two fingers rest upon left palm.',
    leftHandPose: { x: -0.08, y: 0.18, z: 0.28, bend: 0.1 },
    rightHandPose: { x: -0.04, y: 0.22, z: 0.28, bend: 0.6 }
  },
  O: {
    char: 'O',
    name: 'Letter O',
    hands: 'both',
    description: 'Right index contacts tip of left ring finger.',
    leftHandPose: { x: -0.14, y: 0.24, z: 0.28, bend: 0.2 },
    rightHandPose: { x: -0.04, y: 0.26, z: 0.28, bend: 0.7 }
  },
  P: {
    char: 'P',
    name: 'Letter P',
    hands: 'both',
    description: 'Left index upright; right index and thumb circle touches upper left index.',
    leftHandPose: { x: -0.08, y: 0.26, z: 0.28, bend: 0.1 },
    rightHandPose: { x: -0.02, y: 0.28, z: 0.28, bend: 0.7 }
  },
  Q: {
    char: 'Q',
    name: 'Letter Q',
    hands: 'both',
    description: 'Left hand circles; right thumb hooks at the lower edge.',
    leftHandPose: { x: -0.06, y: 0.24, z: 0.28, bend: 0.6 },
    rightHandPose: { x: 0.02, y: 0.19, z: 0.28, bend: 0.8 }
  },
  R: {
    char: 'R',
    name: 'Letter R',
    hands: 'both',
    description: 'Right crossed fingers rest on open left palm.',
    leftHandPose: { x: -0.08, y: 0.18, z: 0.28, bend: 0.1 },
    rightHandPose: { x: -0.04, y: 0.23, z: 0.28, bend: 0.6 }
  },
  S: {
    char: 'S',
    name: 'Letter S',
    hands: 'both',
    description: 'Left little finger hooked with right little finger.',
    leftHandPose: { x: -0.05, y: 0.22, z: 0.29, bend: 0.8 },
    rightHandPose: { x: 0.04, y: 0.22, z: 0.29, bend: 0.8 }
  },
  T: {
    char: 'T',
    name: 'Letter T',
    hands: 'both',
    description: 'Left index finger upright; right horizontal index finger contacts top.',
    leftHandPose: { x: -0.04, y: 0.25, z: 0.28, bend: 0.1 },
    rightHandPose: { x: 0.03, y: 0.28, z: 0.28, bend: 0.5 }
  },
  U: {
    char: 'U',
    name: 'Letter U',
    hands: 'both',
    description: 'Right index contacts tip of left pinky / little finger.',
    leftHandPose: { x: -0.14, y: 0.24, z: 0.28, bend: 0.2 },
    rightHandPose: { x: -0.02, y: 0.25, z: 0.28, bend: 0.7 }
  },
  V: {
    char: 'V',
    name: 'Letter V',
    hands: 'both',
    description: 'Left hand holds V spread; right index contacts vertex.',
    leftHandPose: { x: -0.08, y: 0.25, z: 0.28, bend: 0.1 },
    rightHandPose: { x: 0.02, y: 0.24, z: 0.28, bend: 0.7 }
  },
  W: {
    char: 'W',
    name: 'Letter W',
    hands: 'both',
    description: 'Both hands spread with fingers interlocked upright in signing frame.',
    leftHandPose: { x: -0.06, y: 0.24, z: 0.29, bend: 0.2 },
    rightHandPose: { x: 0.06, y: 0.24, z: 0.29, bend: 0.2 }
  },
  X: {
    char: 'X',
    name: 'Letter X',
    hands: 'both',
    description: 'Both index fingers crossed forming an X shape.',
    leftHandPose: { x: -0.04, y: 0.25, z: 0.28, bend: 0.3 },
    rightHandPose: { x: 0.04, y: 0.25, z: 0.28, bend: 0.3 }
  },
  Y: {
    char: 'Y',
    name: 'Letter Y',
    hands: 'both',
    description: 'Left hand spread thumb and index; right index touches between.',
    leftHandPose: { x: -0.08, y: 0.24, z: 0.28, bend: 0.2 },
    rightHandPose: { x: 0.02, y: 0.24, z: 0.28, bend: 0.6 }
  },
  Z: {
    char: 'Z',
    name: 'Letter Z',
    hands: 'both',
    description: 'Left palm flat upright; right index traces Z contour.',
    leftHandPose: { x: -0.10, y: 0.24, z: 0.28, bend: 0.1 },
    rightHandPose: { x: 0.02, y: 0.25, z: 0.30, bend: 0.6 }
  }
};

// Digits 0–9
for (let d = 0; d <= 9; d++) {
  const digitStr = d.toString();
  ISL_TWO_HANDED_ALPHABET[digitStr] = {
    char: digitStr,
    name: `Digit ${d}`,
    hands: 'both',
    description: `ISL numerical numeral gesture for ${d}`,
    leftHandPose: { x: -0.10, y: 0.20 + (d * 0.005), z: 0.28, bend: 0.2 + (d * 0.05) },
    rightHandPose: { x: 0.05, y: 0.24 + (d * 0.005), z: 0.28, bend: 0.3 + (d * 0.04) }
  };
}

/**
 * Authentic ISL sign dictionary vocabulary keys present in BridgeConn / local SMPL-X dataset.
 */
export const AUTHENTIC_ISL_LEXICON = new Set([
  'WELCOME',
  'GOOD',
  'DRINK',
  'GO',
  'HELP',
  'HELP_2',
  'TEACHER',
  'TEACHER_2',
  'ISHBOSHETH',
  'SAMPLE_1',
  'WELCOME_HELP_YOU',
  'BOOK_DRINK_HOME',
  'BOOK',
  'HOME',
  'EAT',
  'YOU',
  'INDIA',
  'SIGN',
  'HELLO',
  'NAMASTE',
  'DOCTOR',
  'WATER',
  'FOOD',
  'THANK',
  'THANKS',
  'PLEASE',
  'SORRY',
  'YES',
  'NO',
  'NOT',
  'TODAY',
  'TOMORROW',
  'YESTERDAY',
  'TIME',
  'STUDENT',
  'SCHOOL',
  'MEAT',
  'RUN',
  'WATCH',
  'READ',
  'WRITE',
  'WHERE',
  'WHAT',
  'WHY',
  'HOW',
  'WHEN',
  'WHO'
]);

/**
 * Checks whether a given gloss has an authentic motion clip.
 */
export function isAuthenticSignAvailable(gloss: string): boolean {
  if (!gloss) return false;
  const clean = gloss.trim().toUpperCase().replace(/[^A-Z0-9_]/g, '');
  return AUTHENTIC_ISL_LEXICON.has(clean);
}

/**
 * Resolves gloss tokens, marking any unmapped sign as fingerspelled,
 * splitting it into ISL characters, and calculating the exact coverage percentage.
 */
export function resolveGlossTokensWithFallback<T extends { gloss: string }>(
  tokens: T[]
): {
  resolvedTokens: (T & { isFingerspelled: boolean; fingerspelledChars?: string[] })[];
  coverage: number;
  authenticCount: number;
  fingerspelledCount: number;
} {
  if (!tokens || tokens.length === 0) {
    return {
      resolvedTokens: [],
      coverage: 100,
      authenticCount: 0,
      fingerspelledCount: 0
    };
  }

  let authenticCount = 0;
  let fingerspelledCount = 0;

  const resolvedTokens = tokens.map((t) => {
    const isAuthentic = isAuthenticSignAvailable(t.gloss);
    if (isAuthentic) {
      authenticCount++;
      return {
        ...t,
        isFingerspelled: false
      };
    } else {
      fingerspelledCount++;
      const cleanChars = t.gloss
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '')
        .split('');
      return {
        ...t,
        isFingerspelled: true,
        fingerspelledChars: cleanChars.length > 0 ? cleanChars : [t.gloss.charAt(0).toUpperCase()]
      };
    }
  });

  const total = tokens.length;
  const coverage = total > 0 ? Math.round((authenticCount / total) * 100) : 100;

  return {
    resolvedTokens,
    coverage,
    authenticCount,
    fingerspelledCount
  };
}
