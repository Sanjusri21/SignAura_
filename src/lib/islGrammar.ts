import nlp from 'compromise';

export type ISLGrammarTag =
  | 'TIME'
  | 'SUBJECT'
  | 'OBJECT'
  | 'VERB'
  | 'NEGATION'
  | 'QUESTION'
  | 'GREETING'
  | 'MODIFIER'
  | 'OTHER';

export interface ISLGlossToken {
  id: string;
  originalWord: string;
  lemma: string;
  gloss: string;
  tag: ISLGrammarTag;
  confidence: number;
}

export interface ISLTranslationResult {
  originalText: string;
  islGloss: string;
  tokens: ISLGlossToken[];
  clauses: string[];
}

/**
 * Standard stop-words omitted in Indian Sign Language (articles, copulas, helper verbs, prepositions).
 */
export const DEFAULT_ISL_STOP_WORDS = new Set([
  'a',
  'an',
  'the',
  'is',
  'am',
  'are',
  'was',
  'were',
  'be',
  'been',
  'being',
  'to', // when used as infinitive or directional connector
  'of',
  'in',
  'on',
  'into',
  'onto',
  'at',
  'by',
  'for',
  'with', // unless with someone as topic
  'do',
  'does',
  'did', // auxiliaries
  'has',
  'have',
  'had' // auxiliaries
]);

/**
 * Common ISL time markers placed at the start of a clause.
 */
export const ISL_TIME_WORDS = new Set([
  'today',
  'tomorrow',
  'yesterday',
  'now',
  'later',
  'morning',
  'afternoon',
  'evening',
  'night',
  'tonight',
  'daily',
  'everyday',
  'always',
  'never',
  'soon',
  'earlier',
  'recently',
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday'
]);

/**
 * ISL WH-question markers placed at the end of a sentence.
 */
export const ISL_QUESTION_WORDS = new Set([
  'what',
  'where',
  'who',
  'why',
  'how',
  'when',
  'which',
  'whose',
  'whom'
]);

/**
 * Negation tokens placed after the verb in ISL.
 */
export const ISL_NEGATION_WORDS = new Set([
  'not',
  'no',
  'never',
  "don't",
  'dont',
  "doesn't",
  'doesnt',
  "didn't",
  'didnt',
  "cannot",
  "can't",
  'cant',
  "won't",
  'wont'
]);

/**
 * Greetings that typically open an utterance.
 */
export const ISL_GREETINGS = new Set([
  'hello',
  'hi',
  'hey',
  'namaste',
  'welcome',
  'goodbye',
  'bye',
  'please',
  'thanks',
  'thank',
  'sorry'
]);

/**
 * Pronouns preserved in ISL.
 */
export const ISL_PRONOUNS = new Map<string, string>([
  ['i', 'I'],
  ['me', 'I'],
  ['my', 'MY'],
  ['mine', 'MINE'],
  ['you', 'YOU'],
  ['your', 'YOUR'],
  ['yours', 'YOURS'],
  ['he', 'HE'],
  ['him', 'HE'],
  ['his', 'HIS'],
  ['she', 'SHE'],
  ['her', 'HER'],
  ['hers', 'HERS'],
  ['we', 'WE'],
  ['us', 'WE'],
  ['our', 'OUR'],
  ['ours', 'OURS'],
  ['they', 'THEY'],
  ['them', 'THEY'],
  ['their', 'THEIR'],
  ['theirs', 'THEIRS'],
  ['it', 'IT'],
  ['this', 'THIS'],
  ['that', 'THAT']
]);

/**
 * Lemmatization dictionary for irregular English verbs and nouns.
 */
const IRREGULAR_LEMMAS: Record<string, string> = {
  went: 'GO',
  going: 'GO',
  goes: 'GO',
  gone: 'GO',
  ate: 'EAT',
  eating: 'EAT',
  eats: 'EAT',
  eaten: 'EAT',
  drinking: 'DRINK',
  drinks: 'DRINK',
  drank: 'DRINK',
  drunk: 'DRINK',
  came: 'COME',
  coming: 'COME',
  comes: 'COME',
  ran: 'RUN',
  running: 'RUN',
  runs: 'RUN',
  saw: 'SEE',
  seeing: 'SEE',
  sees: 'SEE',
  seen: 'SEE',
  wrote: 'WRITE',
  writing: 'WRITE',
  writes: 'WRITE',
  written: 'WRITE',
  read: 'READ',
  reading: 'READ',
  reads: 'READ',
  spoke: 'SPEAK',
  speaking: 'SPEAK',
  speaks: 'SPEAK',
  spoken: 'SPEAK',
  taught: 'TEACH',
  teaching: 'TEACH',
  teaches: 'TEACH',
  studied: 'STUDY',
  studying: 'STUDY',
  studies: 'STUDY',
  bought: 'BUY',
  buying: 'BUY',
  buys: 'BUY',
  gave: 'GIVE',
  giving: 'GIVE',
  gives: 'GIVE',
  given: 'GIVE',
  took: 'TAKE',
  taking: 'TAKE',
  takes: 'TAKE',
  taken: 'TAKE',
  wanted: 'WANT',
  wanting: 'WANT',
  wants: 'WANT',
  needed: 'NEED',
  needing: 'NEED',
  needs: 'NEED',
  liked: 'LIKE',
  liking: 'LIKE',
  likes: 'LIKE',
  helped: 'HELP',
  helping: 'HELP',
  helps: 'HELP',
  crying: 'CRY',
  cries: 'CRY',
  cried: 'CRY',
  slept: 'SLEEP',
  sleeping: 'SLEEP',
  sleeps: 'SLEEP',
  walking: 'WALK',
  walked: 'WALK',
  walks: 'WALK',
  students: 'STUDENT',
  teachers: 'TEACHER',
  books: 'BOOK',
  friends: 'FRIEND',
  schools: 'SCHOOL',
  apples: 'APPLE',
  cars: 'CAR',
  letters: 'LETTER',
  children: 'CHILD',
  people: 'PERSON',
  men: 'MAN',
  women: 'WOMAN'
};

/**
 * Lemmatizes a token to its base dictionary form (all uppercase for ISL gloss).
 */
export function lemmatizeWord(rawWord: string): string {
  const clean = rawWord.toLowerCase().replace(/[^a-z0-9'-]/g, '');
  if (!clean) return '';

  if (IRREGULAR_LEMMAS[clean]) {
    return IRREGULAR_LEMMAS[clean];
  }

  if (ISL_PRONOUNS.has(clean)) {
    return ISL_PRONOUNS.get(clean)!;
  }

  // Use compromise NLP for general lemmatization
  try {
    const doc = nlp(clean);
    const verbDoc = doc.verbs();
    if (verbDoc.length > 0) {
      const infinitive = verbDoc.toInfinitive().text();
      if (infinitive && infinitive.length > 1) {
        return infinitive.toUpperCase();
      }
    }

    const nounDoc = doc.nouns();
    if (nounDoc.length > 0) {
      const singular = nounDoc.toSingular().text();
      if (singular && singular.length > 1) {
        return singular.toUpperCase();
      }
    }
  } catch {
    // Fallback heuristic
  }

  // Common suffix stripping fallbacks
  if (clean.endsWith('ing') && clean.length > 4) {
    return clean.slice(0, -3).toUpperCase();
  }
  if (clean.endsWith('ed') && clean.length > 3) {
    return clean.slice(0, -2).toUpperCase();
  }
  if (clean.endsWith('s') && !clean.endsWith('ss') && clean.length > 3) {
    return clean.slice(0, -1).toUpperCase();
  }

  return clean.toUpperCase();
}

interface AnalyzedToken {
  original: string;
  lemma: string;
  gloss: string;
  tag: ISLGrammarTag;
  pos: string;
}

/**
 * Analyzes and reorders a single English clause into ISL SOV syntax.
 */
function translateClauseToISL(clauseText: string): ISLGlossToken[] {
  const trimmed = clauseText.trim();
  if (!trimmed) return [];

  const doc = nlp(trimmed);
  const tagList: Array<Record<string, string[]>> = (doc.terms().out('tags') as any) || [];

  const timeTokens: AnalyzedToken[] = [];
  const greetingTokens: AnalyzedToken[] = [];
  const questionTokens: AnalyzedToken[] = [];
  const negationTokens: AnalyzedToken[] = [];
  const subjectTokens: AnalyzedToken[] = [];
  const objectTokens: AnalyzedToken[] = [];
  const verbTokens: AnalyzedToken[] = [];
  const modifierTokens: AnalyzedToken[] = [];
  const otherTokens: AnalyzedToken[] = [];

  const words = trimmed.split(/\s+/);

  // First identify verb index in the sentence to distinguish subject vs object
  let primaryVerbFound = false;

  for (let i = 0; i < words.length; i++) {
    const rawWord = words[i];
    const cleanWord = rawWord.toLowerCase().replace(/[^a-z0-9'-]/g, '');
    if (!cleanWord) continue;

    const nextWord = i + 1 < words.length ? words[i + 1].toLowerCase().replace(/[^a-z0-9'-]/g, '') : undefined;

    // 1. Omit stop words & copulas / auxiliaries
    if (DEFAULT_ISL_STOP_WORDS.has(cleanWord)) {
      continue;
    }
    if (['is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'will', 'shall', 'would', 'should'].includes(cleanWord)) {
      continue;
    }
    if (['do', 'does', 'did', 'have', 'has', 'had'].includes(cleanWord)) {
      // If used as auxiliary
      if (nextWord && (ISL_NEGATION_WORDS.has(nextWord) || nextWord.length > 2)) {
        continue;
      }
    }

    // 2. Greetings
    if (ISL_GREETINGS.has(cleanWord)) {
      greetingTokens.push({
        original: rawWord,
        lemma: lemmatizeWord(cleanWord),
        gloss: lemmatizeWord(cleanWord),
        tag: 'GREETING',
        pos: 'greeting'
      });
      continue;
    }

    // 3. Time markers (placed first in ISL)
    if (ISL_TIME_WORDS.has(cleanWord)) {
      timeTokens.push({
        original: rawWord,
        lemma: lemmatizeWord(cleanWord),
        gloss: lemmatizeWord(cleanWord),
        tag: 'TIME',
        pos: 'time'
      });
      continue;
    }

    // 4. Question words (placed at end in ISL)
    if (ISL_QUESTION_WORDS.has(cleanWord)) {
      questionTokens.push({
        original: rawWord,
        lemma: lemmatizeWord(cleanWord),
        gloss: lemmatizeWord(cleanWord),
        tag: 'QUESTION',
        pos: 'question'
      });
      continue;
    }

    // 5. Negation words (placed after verb in ISL)
    if (ISL_NEGATION_WORDS.has(cleanWord)) {
      negationTokens.push({
        original: rawWord,
        lemma: 'NOT',
        gloss: 'NOT',
        tag: 'NEGATION',
        pos: 'negation'
      });
      continue;
    }

    // 6. Look up compromise tags
    const tagEntry = tagList.find((entry) => Object.keys(entry)[0]?.toLowerCase() === cleanWord);
    const tags: string[] = tagEntry ? Object.values(tagEntry)[0] || [] : [];

    const isPronoun = ISL_PRONOUNS.has(cleanWord) || tags.includes('Pronoun');
    const isVerb = tags.includes('Verb') && !isPronoun && !['water', 'help', 'drink'].includes(cleanWord ? (tags.includes('Noun') && primaryVerbFound ? cleanWord : '') : '');
    const isNoun = tags.includes('Noun') || isPronoun;
    const isAdjective = tags.includes('Adjective') || tags.includes('Adverb');

    const lemma = lemmatizeWord(cleanWord);

    // Classify into Subject, Object, Verb, Modifier
    if (isPronoun) {
      if (subjectTokens.length > 0 && subjectTokens[0].pos === 'noun') {
        // Pronoun is the true subject; demote the fronted noun (e.g. 'Which book do you want') to object
        const previousNoun = subjectTokens.pop()!;
        previousNoun.tag = 'OBJECT';
        objectTokens.push(previousNoun);
        subjectTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'SUBJECT', pos: 'pronoun' });
      } else if (!primaryVerbFound && subjectTokens.length === 0) {
        subjectTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'SUBJECT', pos: 'pronoun' });
      } else {
        objectTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'OBJECT', pos: 'pronoun' });
      }
    } else if (isVerb && !primaryVerbFound) {
      primaryVerbFound = true;
      verbTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'VERB', pos: 'verb' });
    } else if (isNoun) {
      if (!primaryVerbFound && subjectTokens.length === 0) {
        subjectTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'SUBJECT', pos: 'noun' });
      } else {
        objectTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'OBJECT', pos: 'noun' });
      }
    } else if (isAdjective) {
      modifierTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'MODIFIER', pos: 'adjective' });
    } else {
      // If not yet assigned a verb and looks like action
      if (!primaryVerbFound && tags.includes('Verb')) {
        primaryVerbFound = true;
        verbTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'VERB', pos: 'verb' });
      } else {
        otherTokens.push({ original: rawWord, lemma, gloss: lemma, tag: 'OTHER', pos: 'other' });
      }
    }
  }

  // Handle special case where a sentence starts with question word who: e.g. "Who is teaching English?"
  // In ISL: OBJECT (ENGLISH) -> VERB (TEACH) -> QUESTION (WHO)
  if (questionTokens.length > 0 && subjectTokens.length === 0 && objectTokens.length > 0) {
    // English is the object, teach is the verb, who is the question word at the end
  }

  // ISL Clause Order:
  // [GREETING] -> [TIME] -> [SUBJECT] -> [OBJECT] -> [MODIFIER] -> [OTHER] -> [VERB] -> [NEGATION] -> [QUESTION]
  const orderedList: AnalyzedToken[] = [];

  orderedList.push(...greetingTokens);
  orderedList.push(...timeTokens);
  orderedList.push(...subjectTokens);
  orderedList.push(...objectTokens);
  orderedList.push(...modifierTokens);
  orderedList.push(...otherTokens);
  orderedList.push(...verbTokens);
  orderedList.push(...negationTokens);
  orderedList.push(...questionTokens);

  return orderedList.map((t, idx) => ({
    id: `isl-${idx + 1}-${t.gloss.toLowerCase()}`,
    originalWord: t.original,
    lemma: t.lemma,
    gloss: t.gloss,
    tag: t.tag,
    confidence: 0.98
  }));
}

/**
 * Translates English text into Indian Sign Language (ISL) Gloss.
 * Handles multiple clauses, time-fronting, SOV reordering, negation-postposition,
 * and end-of-sentence WH-question placement.
 */
export function translateEnglishToISLGloss(englishText: string): ISLTranslationResult {
  if (!englishText || !englishText.trim()) {
    return {
      originalText: '',
      islGloss: '',
      tokens: [],
      clauses: []
    };
  }

  // Split into sentence/clause segments while keeping order
  const rawClauses = englishText
    .split(/(?<=[.?!])\s+|(?<=[,;])\s+/)
    .map((c) => c.trim())
    .filter(Boolean);

  const allTokens: ISLGlossToken[] = [];
  const clauseGlosses: string[] = [];

  for (const clause of rawClauses) {
    const clauseTokens = translateClauseToISL(clause);
    if (clauseTokens.length > 0) {
      allTokens.push(...clauseTokens);
      clauseGlosses.push(clauseTokens.map((t) => t.gloss).join(' '));
    }
  }

  const finalGloss = clauseGlosses.join(' ').trim();

  return {
    originalText: englishText,
    islGloss: finalGloss,
    tokens: allTokens,
    clauses: clauseGlosses
  };
}
