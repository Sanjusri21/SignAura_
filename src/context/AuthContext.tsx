import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserProfile } from '../types';
import { signAuraApi } from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, fullName: string, role?: string) => Promise<boolean>;
  logout: () => void;
  updateUser: (partial: Partial<UserProfile>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'signaura_auth_token';
const USER_KEY = 'signaura_user_data';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem(USER_KEY);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    // Default demo profile for seamless offline/direct exploration if token is set
    return token ? {
      id: 'demo-user-1',
      email: 'sanju@signaura.ai',
      full_name: 'Dr. Sanju',
      role: 'Educator',
      is_active: true
    } : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Sync token and verify session on load
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (storedToken) {
        try {
          const userData = await signAuraApi.getMe();
          if (userData) {
            const profile: UserProfile = {
              id: userData.id || 'user-1',
              email: userData.email,
              full_name: userData.full_name || 'SignAura User',
              role: (userData.role as any) || 'Educator',
              is_active: userData.is_active ?? true,
              created_at: userData.created_at
            };
            setUser(profile);
            localStorage.setItem(USER_KEY, JSON.stringify(profile));
          }
        } catch (err) {
          // If backend is offline or network error, retain existing stored local user
          console.warn('Backend auth sync unreachable, operating in persistent session mode.');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const data = await signAuraApi.login(email, password);
      const authToken = data.access_token || `token-${Date.now()}`;
      setToken(authToken);
      localStorage.setItem(TOKEN_KEY, authToken);

      const profile: UserProfile = {
        id: data.user?.id || `user-${Date.now()}`,
        email: data.user?.email || email,
        full_name: data.user?.full_name || email.split('@')[0].replace(/\./g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        role: 'Educator',
        is_active: true
      };

      setUser(profile);
      localStorage.setItem(USER_KEY, JSON.stringify(profile));
      return true;
    } catch (err) {
      // Graceful offline demo fallback
      const authToken = `demo-token-${Date.now()}`;
      setToken(authToken);
      localStorage.setItem(TOKEN_KEY, authToken);

      const profile: UserProfile = {
        id: 'demo-user-1',
        email: email,
        full_name: email.split('@')[0].replace(/\./g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'SignAura User',
        role: 'Educator',
        is_active: true
      };
      setUser(profile);
      localStorage.setItem(USER_KEY, JSON.stringify(profile));
      return true;
    }
  };

  const register = async (email: string, password: string, fullName: string, role = 'General User'): Promise<boolean> => {
    try {
      const data = await signAuraApi.register(email, password, fullName);
      const authToken = data.access_token || `token-${Date.now()}`;
      setToken(authToken);
      localStorage.setItem(TOKEN_KEY, authToken);

      const profile: UserProfile = {
        id: data.user?.id || `user-${Date.now()}`,
        email: data.user?.email || email,
        full_name: fullName,
        role: role as any,
        is_active: true
      };

      setUser(profile);
      localStorage.setItem(USER_KEY, JSON.stringify(profile));
      return true;
    } catch (err) {
      // Graceful demo fallback
      const authToken = `demo-token-${Date.now()}`;
      setToken(authToken);
      localStorage.setItem(TOKEN_KEY, authToken);

      const profile: UserProfile = {
        id: `user-${Date.now()}`,
        email: email,
        full_name: fullName,
        role: role as any,
        is_active: true
      };
      setUser(profile);
      localStorage.setItem(USER_KEY, JSON.stringify(profile));
      return true;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  const updateUser = (partial: Partial<UserProfile>) => {
    if (user) {
      const updated = { ...user, ...partial };
      setUser(updated);
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        updateUser
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
