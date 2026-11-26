/**
 * Client for the SignAvatars (port 8001) word endpoints: the playable-word list,
 * per-word availability for a sentence, and word-by-word sentence generation.
 */

export const SIGNAVATAR_API_URL = 'http://127.0.0.1:8001';

export interface PlayableWord {
  word: string;
  type: 'word' | 'alias' | 'synonym';
  source: string;
  label?: string;
  target?: string;
  variants?: number;
}

export interface PlayableWordsResponse {
  count: number;
  /** Words with their own clip, per source (aliases and synonyms are not counted here) */
  by_source: Record<string, number>;
  excluded_failed: number;
  words: PlayableWord[];
}

export interface WordCheckToken {
  input: string;
  key: string;
  status: 'available' | 'synonym' | 'missing';
  source?: string;
  label?: string;
  synonym_of?: string;
  reason?: string;
}

export interface WordCheckResponse {
  tokens: WordCheckToken[];
  available: number;
  total: number;
}

export interface WordSequenceSegment {
  word: string;
  motion_id: string;
  synonym_of?: string | null;
  frames: number;
  source_fps: number;
  source: string;
}

export interface WordSequenceResponse {
  status: string;
  sentence: string;
  motion: string;
  segments: WordSequenceSegment[];
  skipped_words: string[];
  total_frames: number;
  fps: number;
}

const postJson = async <T,>(path: string, body: unknown): Promise<T> => {
  const res = await fetch(`${SIGNAVATAR_API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail?.error || detail?.detail || `HTTP ${res.status} from ${path}`);
  }
  return res.json();
};

export const fetchPlayableWords = async (): Promise<PlayableWordsResponse> => {
  const res = await fetch(`${SIGNAVATAR_API_URL}/words`);
  if (!res.ok) throw new Error(`HTTP ${res.status} from /words`);
  return res.json();
};

export const checkSentenceWords = (sentence: string) =>
  postJson<WordCheckResponse>('/resolve', { sentence });

/** Signs every available word of the sentence; missing words are skipped (see skipped_words). */
export const generateWordSequence = (sentence: string) =>
  postJson<WordSequenceResponse>('/generate', { sentence });
