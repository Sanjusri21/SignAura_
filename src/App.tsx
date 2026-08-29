import React, { useState } from 'react';
import { AmbientBackground } from './components/layout/AmbientBackground';
import { GlassNavigationRail } from './components/layout/GlassNavigationRail';
import { GlassHeader } from './components/layout/GlassHeader';
import { LandingView } from './views/LandingView';
import { DashboardView } from './views/DashboardView';
import { ConvertView } from './views/ConvertView';
import { ProcessingView } from './views/ProcessingView';
import { SignAvatarStudioView } from './views/SignAvatarStudioView';
import { AssistantView } from './views/AssistantView';
import { LibraryView } from './views/LibraryView';
import { SettingsView } from './views/SettingsView';
import { NavigationTab, ISLDialect, VideoProject, AccessibilitySettings } from './types';
import { SAMPLE_PROJECTS } from './data/mockData';

import { signAuraApi } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavigationTab>('landing');
  const [currentDialect, setCurrentDialect] = useState<ISLDialect>('standard');
  const [projects, setProjects] = useState<VideoProject[]>(SAMPLE_PROJECTS);
  const [currentProject, setCurrentProject] = useState<VideoProject>(SAMPLE_PROJECTS[0]);
  
  // Processing Pipeline State
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingTitle, setProcessingTitle] = useState<string>('');
  const [processingPayload, setProcessingPayload] = useState<any>(null);

  // Initial load from backend API
  React.useEffect(() => {
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
  const [accessibilitySettings, setAccessibilitySettings] = useState<AccessibilitySettings>({
    highContrast: false,
    reducedMotion: false,
    largeText: false,
    screenReaderHints: true,
    avatarSpeed: 1,
    glassOpacity: 'medium'
  });

  const handleStartProcessing = (payload: any) => {
    setProcessingPayload(payload);
    setProcessingTitle(payload?.title || 'Video Conversion');
    setIsProcessing(true);
  };

  const handleProcessingComplete = (completedProject: VideoProject) => {
    setProjects((prev) => [completedProject, ...prev]);
    setCurrentProject(completedProject);
    setIsProcessing(false);
    setActiveTab('avatar');
  };

  const handleTestSign = (sign: string) => {
    const updated: VideoProject = {
      ...currentProject,
      glossTokens: [
        { id: `custom-${Date.now()}`, word: sign.toLowerCase(), gloss: sign, startTime: 0, endTime: 3.5, confidence: 0.99, grammarTag: 'ISL_GESTURE' },
        ...currentProject.glossTokens
      ]
    };
    setCurrentProject(updated);
  };

  const handleUpdateSettings = (partial: Partial<AccessibilitySettings>) => {
    setAccessibilitySettings((prev) => ({ ...prev, ...partial }));
  };

  return (
    <div className={`min-h-screen bg-[#04060a] text-slate-100 relative font-sans ${
      accessibilitySettings.highContrast ? 'high-contrast' : ''
    } ${accessibilitySettings.largeText ? 'text-lg' : ''}`}>
      
      {/* Spatial Ambient Background Emitters */}
      {!accessibilitySettings.reducedMotion && <AmbientBackground />}

      {/* Compact Floating Navigation Rail (Desktop Rail & Mobile Bottom Nav) */}
      <GlassNavigationRail
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setIsProcessing(false);
          setActiveTab(tab);
        }}
      />

      {/* Main Content Layout Container */}
      <div className="min-h-screen flex flex-col md:pl-24 lg:pl-28 transition-all duration-300">
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-24 md:pb-12 relative z-10">
          
          {/* Top Minimal Floating Glass Header */}
          <GlassHeader
            currentDialect={currentDialect}
            onDialectChange={setCurrentDialect}
            onNavigate={(tab) => {
              setIsProcessing(false);
              setActiveTab(tab);
            }}
            onOpenSettings={() => setActiveTab('settings')}
          />

          {/* Dynamic View Router */}
          {isProcessing ? (
            <ProcessingView
              title={processingTitle}
              payload={processingPayload}
              currentDialect={currentDialect}
              onComplete={handleProcessingComplete}
            />
          ) : (
            <>
              {activeTab === 'landing' && (
                <LandingView onNavigate={setActiveTab} />
              )}

              {activeTab === 'dashboard' && (
                <DashboardView
                  projects={projects}
                  onNavigate={setActiveTab}
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

              {activeTab === 'avatar' && (
                <SignAvatarStudioView
                  project={currentProject}
                  onOpenDictionary={() => setActiveTab('settings')}
                />
              )}

              {activeTab === 'assistant' && (
                <AssistantView
                  onTestSign={handleTestSign}
                  onNavigate={setActiveTab}
                />
              )}

              {activeTab === 'library' && (
                <LibraryView
                  projects={projects}
                  onSelectProject={(proj) => setCurrentProject(proj)}
                  onNavigate={setActiveTab}
                />
              )}

              {activeTab === 'settings' && (
                <SettingsView
                  settings={accessibilitySettings}
                  onUpdateSettings={handleUpdateSettings}
                  onTestSign={handleTestSign}
                  onNavigate={setActiveTab}
                />
              )}
            </>
          )}

        </main>
      </div>

    </div>
  );
};
