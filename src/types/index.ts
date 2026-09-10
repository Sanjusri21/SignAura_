export type NavigationTab = 
  | 'landing' 
  | 'signin'
  | 'signup'
  | 'forgot-password'
  | 'dashboard' 
  | 'convert' 
  | 'translator'
  | 'avatar' 
  | 'assistant' 
  | 'library' 
  | 'settings';

export type ISLDialect = 'standard' | 'north' | 'south';

export interface GlossToken {
  id: string;
  word: string;
  gloss: string;
  startTime: number;
  endTime: number;
  confidence: number;
  category?: string;
  grammarTag?: string;
}

export interface VideoProject {
  id: string;
  title: string;
  originalFileName?: string;
  videoUrl?: string;
  duration: number; // in seconds
  createdAt: string;
  status: 'completed' | 'processing' | 'queued' | 'failed';
  accuracy: number;
  transcript: string;
  glossTokens: GlossToken[];
  thumbnailUrl?: string;
  language: string;
  dialect: ISLDialect;
}

export interface AvatarPose {
  name: string;
  leftArm: { shoulder: [number, number, number]; elbow: [number, number, number]; wrist: [number, number, number]; fingers: number };
  rightArm: { shoulder: [number, number, number]; elbow: [number, number, number]; wrist: [number, number, number]; fingers: number };
  head: [number, number, number];
  expression: 'neutral' | 'question' | 'smile' | 'focused' | 'nod';
}

export interface ISLDictionaryItem {
  id: string;
  word: string;
  gloss: string;
  category: 'Greetings' | 'Emergency' | 'Education' | 'Conversational' | 'Technology' | 'Medical';
  definition: string;
  exampleSentence: string;
  difficulty: 'Beginner' | 'Intermediate' | 'Advanced';
}

export interface ChatMessage {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  timestamp: string;
  glossSequence?: string[];
  recommendedSigns?: string[];
  isStreaming?: boolean;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role?: 'Student' | 'Educator' | 'General User' | 'Researcher';
  created_at?: string;
  is_active?: boolean;
}

export interface AccessibilitySettings {
  highContrast: boolean;
  reducedMotion: boolean;
  largeText: boolean;
  screenReaderHints: boolean;
  avatarSpeed: number;
  glassOpacity: 'subtle' | 'medium' | 'prominent';
}
