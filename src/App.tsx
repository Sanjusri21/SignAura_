import React, { useState, useEffect } from 'react';
import { AmbientBackground } from './components/layout/AmbientBackground';
import { DashboardSidebar } from './components/layout/DashboardSidebar';
import { DashboardHeader } from './components/layout/DashboardHeader';
import { LandingView } from './views/LandingView';
import { SignInView } from './views/SignInView';
import { SignUpView } from './views/SignUpView';
import { ForgotPasswordView } from './views/ForgotPasswordView';
import { DashboardView } from './views/DashboardView';
import { ConvertView } from './views/ConvertView';
import { ProcessingView } from './views/ProcessingView';
import { TranslatorView } from './views/TranslatorView';
import { SignAvatarStudioView } from './views/SignAvatarStudioView';
import { AssistantView } from './views/AssistantView';
import { LibraryView } from './views/LibraryView';
import { SettingsView } from './views/SettingsView';
import { NavigationTab, ISLDialect, VideoProject, AccessibilitySettings } from './types';
import { SAMPLE_PROJECTS } from './data/mockData';
import { signAuraApi } from './services/api';
import { AuthProvider, useAuth } from './context/AuthContext';

// Route path to tab mapping
const PATH_TO_TAB: Record<string, NavigationTab> = {
  '/': 'landing',
  '/signin': 'signin',
  '/signup': 'signup',
  '/forgot-password': 'forgot-password',
  '/dashboard': 'dashboard',
  '/video-to-isl': 'convert',
  '/translator': 'translator',
  '/avatar': 'avatar',
  '/chat': 'assistant',
  '/history': 'library',
  '/settings': 'settings',
};

const TAB_TO_PATH: Record<NavigationTab, string> = {
  landing: '/',
  signin: '/signin',
  signup: '/signup',
  'forgot-password': '/forgot-password',
  dashboard: '/dashboard',
  convert: '/video-to-isl',
  translator: '/translator',
  avatar: '/avatar',
  assistant: '/chat',
  library: '/history',
  settings: '/settings',
};

const PROTECTED_TABS: NavigationTab[] = [
  'dashboard',
  'convert',
  'translator',
  'avatar',
  'assistant',
  'library',
  'settings'
];

const MainAppContent: React.FC = () => {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();

  // Route state initialized from window.location.pathname
  const [activeTab, setActiveTab] = useState<NavigationTab>(() => {
    const path = window.location.pathname.toLowerCase();
    return PATH_TO_TAB[path] || 'landing';
  });

  const [currentDialect, setCurrentDialect] = useState<ISLDialect>('standard');
  const [projects, setProjects] = useState<VideoProject[]>(SAMPLE_PROJECTS);
  const [currentProject, setCurrentProject] = useState<VideoProject>(SAMPLE_PROJECTS[0]);
  
  // Processing Pipeline State
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingTitle, setProcessingTitle] = useState<string>('');
  const [processingPayload, setProcessingPayload] = useState<any>(null);

  // Sync with browser history popstate
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname.toLowerCase();
      const tab = PATH_TO_TAB[path] || 'landing';
      setActiveTab(tab);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Safe navigation helper with pushState
  const navigateTo = (tab: NavigationTab) => {
    setIsProcessing(false);

    // Protected route check
    if (PROTECTED_TABS.includes(tab) && !isAuthenticated) {
      const targetPath = TAB_TO_PATH['signin'];
      window.history.pushState(null, '', targetPath);
      setActiveTab('signin');
      return;
    }

    const targetPath = TAB_TO_PATH[tab] || '/';
    if (window.location.pathname !== targetPath) {
      window.history.pushState(null, '', targetPath);
    }
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Initial load from backend API
  useEffect(() => {
    signAuraApi.getHistory()
      .then((history) => {
        if (history && history.length > 0) {
          setProjects(history);
          setCurrentProject(history[0]);
        }
      })
      .catch(() => {
        // Fallback to SAMPLE_PROJECTS on initial offline run
      });
  }, []);

  // Accessibility & Visual Preferences
  const [accessibilitySettings, setAccessibilitySettings] = useState<AccessibilitySettings>(() => {
    const saved = localStorage.getItem('signaura_accessibility');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        // Fallback
      }
    }
    return {
      highContrast: false,
      reducedMotion: false,
      largeText: false,
      screenReaderHints: true,
      avatarSpeed: 1,
      glassOpacity: 'medium'
    };
  });

  const handleUpdateSettings = (partial: Partial<AccessibilitySettings>) => {
    setAccessibilitySettings((prev) => {
      const updated = { ...prev, ...partial };
      localStorage.setItem('signaura_accessibility', JSON.stringify(updated));
      return updated;
    });
  };

  const handleStartProcessing = (payload: any) => {
    setProcessingPayload(payload);
    setProcessingTitle(payload?.title || 'Video Conversion');
    setIsProcessing(true);
  };

  const handleProcessingComplete = (completedProject: VideoProject) => {
    setProjects((prev) => [completedProject, ...prev]);
    setCurrentProject(completedProject);
    setIsProcessing(false);
    navigateTo('avatar');
  };

  const handleTestSign = (sign: string) => {
    const updated: VideoProject = {
      ...currentProject,
      glossTokens: [
        {
          id: `custom-${Date.now()}`,
          word: sign.toLowerCase(),
          gloss: sign,
          startTime: 0,
          endTime: 3.5,
          confidence: 0.99,
          grammarTag: 'ISL_GESTURE'
        },
        ...currentProject.glossTokens
      ]
    };
    setCurrentProject(updated);
  };

  const isPublicPage = activeTab === 'landing' || activeTab === 'signin' || activeTab === 'signup' || activeTab === 'forgot-password';

  return (
    <div className={`min-h-screen bg-[#080D24] text-white relative font-sans ${
      accessibilitySettings.highContrast ? 'high-contrast' : ''
    } ${accessibilitySettings.largeText ? 'text-lg' : ''}`}>
      
      {/* Reusable Spatial Ambient Background */}
      {!accessibilitySettings.reducedMotion && <AmbientBackground />}

      {/* Conditional Dashboard Sidebar (Only on authenticated dashboard views) */}
      {!isPublicPage && (
        <DashboardSidebar
          activeTab={activeTab}
          onSelectTab={navigateTo}
        />
      )}

      {/* Main Content Layout Container */}
      <div className={`min-h-screen flex flex-col transition-all duration-300 ${
        !isPublicPage ? 'md:pl-20 lg:pl-64' : ''
      }`}>
        <main className={`flex-1 w-full mx-auto px-4 sm:px-6 lg:px-8 relative z-10 ${
          isPublicPage ? 'max-w-7xl pt-4 pb-12' : 'max-w-7xl pt-6 pb-20'
        }`}>
          
          {/* Top Contextual Dashboard Header (Only on dashboard views) */}
          {!isPublicPage && !isProcessing && (
            <DashboardHeader
              currentTab={activeTab}
              currentDialect={currentDialect}
              onDialectChange={setCurrentDialect}
              onNavigate={navigateTo}
            />
          )}

          {/* Dynamic View Switcher */}
          {isProcessing ? (
            <ProcessingView
              title={processingTitle}
              payload={processingPayload}
              currentDialect={currentDialect}
              onComplete={handleProcessingComplete}
            />
          ) : (
            <>
              {/* Public Views */}
              {activeTab === 'landing' && (
                <LandingView onNavigate={navigateTo} />
              )}

              {activeTab === 'signin' && (
                <SignInView
                  onNavigate={navigateTo}
                  onSuccess={() => navigateTo('dashboard')}
                />
              )}

              {activeTab === 'signup' && (
                <SignUpView
                  onNavigate={navigateTo}
                  onSuccess={() => navigateTo('dashboard')}
                />
              )}

              {activeTab === 'forgot-password' && (
                <ForgotPasswordView onNavigate={navigateTo} />
              )}

              {/* Protected Dashboard Views */}
              {activeTab === 'dashboard' && (
                <DashboardView
                  projects={projects}
                  onNavigate={navigateTo}
                  onSelectProject={(proj) => setCurrentProject(proj)}
                />
              )}

              {activeTab === 'convert' && (
                <ConvertView
                  currentDialect={currentDialect}
                  onDialectChange={setCurrentDialect}
                  onStartProcessing={handleStartProcessing}
                />
              )}

              {activeTab === 'translator' && (
                <TranslatorView
                  currentDialect={currentDialect}
                  onDialectChange={setCurrentDialect}
                  onSendToAvatar={(proj) => setCurrentProject(proj)}
                  onNavigate={navigateTo}
                />
              )}

              {activeTab === 'avatar' && (
                <SignAvatarStudioView
                  project={currentProject}
                  onOpenDictionary={() => navigateTo('settings')}
                />
              )}

              {activeTab === 'assistant' && (
                <AssistantView
                  onTestSign={handleTestSign}
                  onNavigate={navigateTo}
                />
              )}

              {activeTab === 'library' && (
                <LibraryView
                  projects={projects}
                  onSelectProject={(proj) => setCurrentProject(proj)}
                  onNavigate={navigateTo}
                />
              )}

              {activeTab === 'settings' && (
                <SettingsView
                  settings={accessibilitySettings}
                  onUpdateSettings={handleUpdateSettings}
                  onTestSign={handleTestSign}
                  onNavigate={navigateTo}
                />
              )}
            </>
          )}

        </main>
      </div>

    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainAppContent />
    </AuthProvider>
  );
};
