import axios from 'axios';
import { VideoProject, GlossToken, ChatMessage, ISLDictionaryItem, ISLDialect } from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor for JWT token injection
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('signaura_auth_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  demo_mode: boolean;
  database_connected: boolean;
}

export interface ISLTranslateResponse {
  text: string;
  gloss: string[];
  animations: string[];
  status: string;
  tokens?: GlossToken[];
  dialect?: string;
  disclaimer?: string;
}

export interface ChatResponse {
  id: string;
  text: string;
  timestamp: string;
  glossSequence: string[];
  recommendedSigns: string[];
  sender: 'ai' | 'user';
}

export interface TranslateToSignAvatarResponse {
  available: boolean;
  text: string;
  glosses: string[];
  animation?: {
    sequence_id: string;
    animation_url: string;
    metadata_url: string;
    frames: number;
    fps: number;
    vertex_count: number;
  };
  unavailable?: { gloss: string; reason: string }[];
  source?: string;
  error?: string;
}

export interface SignAvatarResponse {
  status: string;
  sentence: string;
  gif?: string;
  motion?: string;
  npy?: string;
  animation_url?: string;
  segments?: { word: string; motion_id: number; frames: number }[];
  total_frames?: number;
  fps?: number;
  vertices?: number;
  components?: number;
}

export const signAuraApi = {
  // Health
  checkHealth: async (): Promise<HealthResponse> => {
    const res = await apiClient.get<HealthResponse>('/health');
    return res.data;
  },

  // Auth
  register: async (email: string, password: string, fullName?: string) => {
    const res = await apiClient.post('/api/auth/register', { email, password, full_name: fullName });
    if (res.data.access_token) {
      localStorage.setItem('signaura_auth_token', res.data.access_token);
    }
    return res.data;
  },

  login: async (email: string, password: string) => {
    const res = await apiClient.post('/api/auth/login', { email, password });
    if (res.data.access_token) {
      localStorage.setItem('signaura_auth_token', res.data.access_token);
    }
    return res.data;
  },

  getMe: async () => {
    const res = await apiClient.get('/api/auth/me');
    return res.data;
  },

  // Video Conversion Pipeline
  uploadVideo: async (file: File, dialect: ISLDialect = 'standard') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dialect', dialect);

    const res = await apiClient.post('/api/video/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  processVideoUrl: async (url: string, title?: string, dialect: ISLDialect = 'standard') => {
    const res = await apiClient.post('/api/video/process-url', {
      url,
      title: title || 'Web Media Stream',
      dialect,
    });
    return res.data;
  },

  getJobStatus: async (jobId: string) => {
    const res = await apiClient.get(`/api/jobs/${jobId}`);
    return res.data;
  },

  // ISL Translation & Dictionary
  translateISL: async (text: string, dialect: ISLDialect = 'standard'): Promise<ISLTranslateResponse> => {
    const res = await apiClient.post<ISLTranslateResponse>('/api/isl/translate', {
      text,
      dialect,
    });
    return res.data;
  },

  getDictionary: async (): Promise<ISLDictionaryItem[]> => {
    const res = await apiClient.get<ISLDictionaryItem[]>('/api/isl/dictionary');
    return res.data;
  },

  // Chat & AI Assistant
  sendChatMessage: async (message: string, sessionId = 'default-session', dialect: ISLDialect = 'standard'): Promise<ChatResponse> => {
    const res = await apiClient.post<ChatResponse>('/api/chat', {
      message,
      session_id: sessionId,
      dialect,
    });
    return res.data;
  },

  getChatHistory: async (sessionId = 'default-session'): Promise<{ session_id: string; messages: ChatMessage[] }> => {
    const res = await apiClient.get(`/api/chat/history?session_id=${sessionId}`);
    return res.data;
  },

  // Project History
  getHistory: async (): Promise<VideoProject[]> => {
    const res = await apiClient.get<VideoProject[]>('/api/history');
    return res.data;
  },

  // Avatar Poser
  getAvatarPoses: async () => {
    const res = await apiClient.get('/api/avatar/poses');
    return res.data;
  },
    // SignAvatar Animation Generation
  generateSignAvatar: async (sentence: string): Promise<SignAvatarResponse> => {
    const res = await apiClient.post<SignAvatarResponse>('/api/avatar/signavatar', {
      sentence,
    });

    return res.data;
  },

  // Translate to SignAvatar Real Sequence Pipeline
  translateToSignAvatar: async (text: string, dialect: ISLDialect = 'standard'): Promise<TranslateToSignAvatarResponse> => {
    const res = await apiClient.post<TranslateToSignAvatarResponse>('/api/translate-to-signavatar', {
      text,
      dialect,
    });
    return res.data;
  },
};
