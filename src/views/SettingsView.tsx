import React, { useState } from 'react';
import { 
  Settings, 
  Eye, 
  Accessibility, 
  Cpu, 
  BookOpen, 
  Sparkles, 
  Check, 
  Play, 
  Search, 
  Sliders, 
  ShieldCheck, 
  User, 
  Globe, 
  Palette,
  Layers,
  Lock
} from 'lucide-react';
import { AccessibilitySettings, ISLDictionaryItem, NavigationTab } from '../types';
import { ISL_DICTIONARY } from '../data/mockData';
import { GlassToggle } from '../components/ui/GlassToggle';
import { GlassButton } from '../components/ui/GlassButton';
import { GlassCard } from '../components/ui/GlassCard';

interface SettingsViewProps {
  settings: AccessibilitySettings;
  onUpdateSettings: (settings: Partial<AccessibilitySettings>) => void;
  onTestSign?: (sign: string) => void;
  onNavigate?: (tab: NavigationTab) => void;
}

type SettingsSection = 'accessibility' | 'appearance' | 'language' | 'account';

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onUpdateSettings,
  onTestSign,
  onNavigate
}) => {
  const [activeSection, setActiveSection] = useState<SettingsSection>('accessibility');
  const [dictSearch, setDictSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedDictItem, setSelectedDictItem] = useState<ISLDictionaryItem | null>(ISL_DICTIONARY[0]);

  const categories = ['All', 'Greetings', 'Emergency', 'Education', 'Conversational', 'Technology', 'Medical'];

  const filteredDict = ISL_DICTIONARY.filter((item) => {
    const matchesSearch = item.word.toLowerCase().includes(dictSearch.toLowerCase()) ||
      item.gloss.toLowerCase().includes(dictSearch.toLowerCase()) ||
      item.definition.toLowerCase().includes(dictSearch.toLowerCase());
    const matchesCat = selectedCategory === 'All' || item.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const navCategories = [
    { id: 'accessibility', label: 'Accessibility', icon: Accessibility, desc: 'WCAG high contrast & motion' },
    { id: 'appearance', label: 'Appearance', icon: Palette, desc: 'Liquid Glass & themes' },
    { id: 'language', label: 'Language & Lexicon', icon: BookOpen, desc: 'ISL grammar & dictionary' },
    { id: 'account', label: 'Account & Security', icon: User, desc: 'Profile & API access' }
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      {/* Top Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
          <Settings className="w-6 h-6 text-white" />
          Settings & Preferences
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Customize Liquid Glass material parameters, WCAG accessibility, and explore the certified ISL lexicon.
        </p>
      </div>

      {/* 2-COLUMN CLEAN SETTINGS LAYOUT */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: NAVIGATION CATEGORY LIST (4 COLS) */}
        <aside className="md:col-span-4 glass-card p-3 rounded-[28px] border border-white/14 space-y-1">
          {navCategories.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeSection === cat.id;

            return (
              <button
                key={cat.id}
                onClick={() => setActiveSection(cat.id as SettingsSection)}
                className={`w-full p-3 rounded-2xl text-left transition-all flex items-center gap-3 ${
                  isActive
                    ? 'bg-white/15 border border-white/25 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-white/6 border border-transparent'
                }`}
              >
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  isActive ? 'bg-white/20 text-white' : 'bg-white/6 text-slate-400'
                }`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-white tracking-tight">{cat.label}</p>
                  <p className="text-[10px] text-slate-400 truncate">{cat.desc}</p>
                </div>
              </button>
            );
          })}
        </aside>

        {/* RIGHT COLUMN: SETTINGS CONTENT SECTIONS (8 COLS) */}
        <div className="md:col-span-8 space-y-6">
          
          {/* 1. ACCESSIBILITY SECTION */}
          {activeSection === 'accessibility' && (
            <div className="glass-card p-6 sm:p-7 rounded-[32px] border border-white/14 space-y-6">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Accessibility className="w-4 h-4 text-white" />
                  WCAG Accessibility & Visual Comfort
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Adjust contrast, motion, and typography sizing for maximum readability.
                </p>
              </div>

              <div className="space-y-4">
                {/* High Contrast Glass Mode */}
                <div className="p-4 rounded-2xl glass-subtle border border-white/10">
                  <GlassToggle
                    checked={settings.highContrast}
                    onChange={(val) => onUpdateSettings({ highContrast: val })}
                    label="High Contrast Glass Mode"
                    description="Increases background opacity to 94% with crisp white borders for WCAG AA compliance."
                  />
                </div>

                {/* Reduced Motion */}
                <div className="p-4 rounded-2xl glass-subtle border border-white/10">
                  <GlassToggle
                    checked={settings.reducedMotion}
                    onChange={(val) => onUpdateSettings({ reducedMotion: val })}
                    label="Reduced Motion & Dimmed Ambient Lighting"
                    description="Disables floating background lighting emitters and smooths layout transitions for motion sensitivity."
                  />
                </div>

                {/* Large Typography Scaling */}
                <div className="p-4 rounded-2xl glass-subtle border border-white/10">
                  <GlassToggle
                    checked={settings.largeText}
                    onChange={(val) => onUpdateSettings({ largeText: val })}
                    label="Enhanced Typography Scaling (+15%)"
                    description="Enlarges captions, transcripts, and interactive button labels for easier scanning."
                  />
                </div>

                {/* Screen Reader Hints */}
                <div className="p-4 rounded-2xl glass-subtle border border-white/10">
                  <GlassToggle
                    checked={settings.screenReaderHints}
                    onChange={(val) => onUpdateSettings({ screenReaderHints: val })}
                    label="Screen Reader & Live Landmark Audio Hints"
                    description="Emits ARIA live region updates when 3D gesture keyframes change in real-time."
                  />
                </div>
              </div>
            </div>
          )}

          {/* 2. APPEARANCE & LIQUID GLASS FIDELITY */}
          {activeSection === 'appearance' && (
            <div className="glass-card p-6 sm:p-7 rounded-[32px] border border-white/14 space-y-6">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Palette className="w-4 h-4 text-white" />
                  Liquid Glass & Spatial Rendering Fidelity
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Configure material blur depth, specular reflections, and ambient lighting colors.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl glass-subtle border border-white/10 space-y-1.5">
                  <span className="text-xs font-bold text-white">Liquid Glass Blur Intensity</span>
                  <select 
                    value={settings.glassOpacity}
                    onChange={(e) => onUpdateSettings({ glassOpacity: e.target.value as any })}
                    className="w-full glass-input text-xs p-2.5 rounded-xl bg-black/40 text-white"
                  >
                    <option value="high">Liquid Ultra Glass (36px Blur)</option>
                    <option value="medium">Balanced Glass (24px Blur)</option>
                    <option value="low">Crisp Performance (12px Blur)</option>
                  </select>
                </div>

                <div className="p-4 rounded-2xl glass-subtle border border-white/10 space-y-1.5">
                  <span className="text-xs font-bold text-white">SignAvatar Rendering FPS</span>
                  <select className="w-full glass-input text-xs p-2.5 rounded-xl bg-black/40 text-white">
                    <option>60 FPS (Ultra Smooth Spatial)</option>
                    <option>30 FPS (Energy Saver Mode)</option>
                  </select>
                </div>

                <div className="p-4 rounded-2xl glass-subtle border border-white/10 space-y-1.5">
                  <span className="text-xs font-bold text-white">Holographic Stage Reflection</span>
                  <select className="w-full glass-input text-xs p-2.5 rounded-xl bg-black/40 text-white">
                    <option>Full Translucent Floor Specular</option>
                    <option>Minimal Floor Glow</option>
                  </select>
                </div>

                <div className="p-4 rounded-2xl glass-subtle border border-white/10 space-y-1.5">
                  <span className="text-xs font-bold text-white">Floating Spatial Motes</span>
                  <select className="w-full glass-input text-xs p-2.5 rounded-xl bg-black/40 text-white">
                    <option>Active (100 Particles)</option>
                    <option>Disabled</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* 3. LANGUAGE & ISL DICTIONARY LEXICON */}
          {activeSection === 'language' && (
            <div className="glass-card p-6 sm:p-7 rounded-[32px] border border-white/14 space-y-6">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-white" />
                  ISL Certified Dictionary & Lexicon Explorer
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Search 15,000+ certified Indian Sign Language gestures and test them in 3D.
                </p>
              </div>

              {/* Search & Categories */}
              <div className="space-y-3">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={dictSearch}
                    onChange={(e) => setDictSearch(e.target.value)}
                    placeholder="Search ISL vocabulary by English word or gloss..."
                    className="w-full glass-input text-xs pl-10 pr-3 py-2.5 rounded-2xl bg-black/30"
                  />
                </div>

                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                  {categories.map((c) => (
                    <button
                      key={c}
                      onClick={() => setSelectedCategory(c)}
                      className={`px-3 py-1 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                        selectedCategory === c
                          ? 'bg-white/20 text-white border border-white/30'
                          : 'glass-subtle text-slate-400 hover:text-white'
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dictionary Explorer Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-4">
                {/* List (7 Cols) */}
                <div className="sm:col-span-7 space-y-2 max-h-[340px] overflow-y-auto pr-1 scrollbar-thin">
                  {filteredDict.map((item) => {
                    const isSelected = selectedDictItem?.id === item.id;
                    return (
                      <div
                        key={item.id}
                        onClick={() => setSelectedDictItem(item)}
                        className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                          isSelected
                            ? 'bg-white/18 border-white/35 text-white shadow-md'
                            : 'glass-subtle hover:bg-white/8 border-white/10 text-slate-300'
                        }`}
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-white">{item.word}</span>
                            <span className="font-mono text-xs text-slate-300 font-semibold">[{item.gloss}]</span>
                          </div>
                          <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{item.definition}</p>
                        </div>

                        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-white/8 text-slate-300 border border-white/10">
                          {item.category}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Details Card (5 Cols) */}
                <div className="sm:col-span-5">
                  {selectedDictItem && (
                    <div className="p-4 rounded-2xl glass-subtle border border-white/12 space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-white/10">
                        <span className="glass-badge text-[10px]">{selectedDictItem.difficulty}</span>
                        <span className="text-xs text-slate-300 font-bold">{selectedDictItem.category}</span>
                      </div>

                      <div>
                        <h3 className="text-lg font-extrabold text-white">{selectedDictItem.word}</h3>
                        <p className="text-xs font-mono text-white font-bold">GLOSS: {selectedDictItem.gloss}</p>
                      </div>

                      <div className="space-y-2 text-xs">
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {selectedDictItem.definition}
                        </p>
                        <p className="text-slate-400 text-[10px] italic">
                          "{selectedDictItem.exampleSentence}"
                        </p>
                      </div>

                      <GlassButton
                        variant="primary"
                        size="sm"
                        onClick={() => {
                          onTestSign?.(selectedDictItem.gloss);
                          onNavigate?.('avatar');
                        }}
                        icon={<Play className="w-3 h-3" />}
                        className="w-full justify-center"
                      >
                        Launch 3D Gesture
                      </GlassButton>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 4. ACCOUNT & SECURITY SECTION */}
          {activeSection === 'account' && (
            <div className="glass-card p-6 sm:p-7 rounded-[32px] border border-white/14 space-y-6">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <User className="w-4 h-4 text-white" />
                  Account Profile & API Keys
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Manage your authenticated user credentials and API access keys.
                </p>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-2xl glass-subtle border border-white/10 flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-slate-700 to-slate-500 flex items-center justify-center font-bold text-base text-white shadow-md flex-shrink-0">
                    SA
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-white">Dr. Sanju</p>
                    <p className="text-xs text-slate-400">sanju@signaura.ai • ISL Professional License</p>
                  </div>
                  <span className="glass-badge text-[10px]">Active</span>
                </div>

                <div className="p-4 rounded-2xl glass-subtle border border-white/10 space-y-2">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-slate-400" /> SignAura Neural API Token
                  </span>
                  <div className="flex items-center gap-2">
                    <input
                      type="password"
                      value="sa_live_948f93e82190fecd5f244d528fd4fe32"
                      readOnly
                      className="flex-1 glass-input text-xs py-2 px-3 rounded-xl bg-black/40 font-mono text-slate-400"
                    />
                    <GlassButton variant="secondary" size="sm">
                      Copy Key
                    </GlassButton>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
