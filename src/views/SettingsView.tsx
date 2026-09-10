import React, { useState } from 'react';
import { 
  Settings, 
  Accessibility, 
  BookOpen, 
  Check, 
  Play, 
  Search, 
  User, 
  Palette,
  LogOut,
  Bell
} from 'lucide-react';
import { AccessibilitySettings, ISLDictionaryItem, NavigationTab } from '../types';
import { ISL_DICTIONARY } from '../data/mockData';
import { GlassToggle } from '../components/ui/GlassToggle';
import { GlassButton } from '../components/ui/GlassButton';
import { useAuth } from '../context/AuthContext';

interface SettingsViewProps {
  settings: AccessibilitySettings;
  onUpdateSettings: (settings: Partial<AccessibilitySettings>) => void;
  onTestSign?: (sign: string) => void;
  onNavigate?: (tab: NavigationTab) => void;
}

type SettingsSection = 'accessibility' | 'profile' | 'appearance' | 'language' | 'notifications';

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onUpdateSettings,
  onTestSign,
  onNavigate
}) => {
  const { user, logout, updateUser } = useAuth();
  const [activeSection, setActiveSection] = useState<SettingsSection>('accessibility');
  const [dictSearch, setDictSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  // Editable profile state
  const [nameInput, setNameInput] = useState(user?.full_name || 'Dr. Sanju');
  const [roleInput, setRoleInput] = useState(user?.role || 'Educator');
  const [savedNotice, setSavedNotice] = useState(false);

  const categories = ['All', 'Greetings', 'Emergency', 'Education', 'Conversational', 'Technology', 'Medical'];

  const filteredDict = ISL_DICTIONARY.filter((item) => {
    const matchesSearch = item.word.toLowerCase().includes(dictSearch.toLowerCase()) ||
      item.gloss.toLowerCase().includes(dictSearch.toLowerCase()) ||
      item.definition.toLowerCase().includes(dictSearch.toLowerCase());
    const matchesCat = selectedCategory === 'All' || item.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const navCategories = [
    { id: 'accessibility', label: 'Accessibility (WCAG)', icon: Accessibility, desc: 'High contrast & motion limits' },
    { id: 'profile', label: 'Profile & Account', icon: User, desc: 'Identity, role & security' },
    { id: 'appearance', label: 'Appearance & UI Theme', icon: Palette, desc: 'Dark solid surface settings' },
    { id: 'language', label: 'Certified ISL Lexicon', icon: BookOpen, desc: 'Sign vocabulary & dictionary' },
    { id: 'notifications', label: 'Notifications', icon: Bell, desc: 'Pipeline updates and alerts' }
  ];

  const handleSaveProfile = () => {
    updateUser({
      full_name: nameInput,
      role: roleInput as any
    });
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2000);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      {/* Top Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
          <Settings className="w-6 h-6 text-[#22D3EE]" />
          Settings & Preferences
        </h1>
        <p className="text-xs sm:text-sm text-[#A8B2D1] mt-1">
          Customize WCAG accessibility standards, manage your SignAura profile, and explore the certified ISL dictionary.
        </p>
      </div>

      {/* 2-COLUMN SETTINGS LAYOUT */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: NAVIGATION LIST */}
        <aside className="md:col-span-4 bg-[#151D40] p-3 rounded-2xl border border-[#273154] space-y-1 shadow-md">
          {navCategories.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeSection === cat.id;

            return (
              <button
                key={cat.id}
                onClick={() => setActiveSection(cat.id as SettingsSection)}
                className={`w-full p-3 rounded-xl text-left transition-colors flex items-center gap-3 ${
                  isActive
                    ? 'bg-[#101735] border border-[#22D3EE]/40 text-white shadow-sm'
                    : 'text-[#A8B2D1] hover:text-white hover:bg-[#1A244D] border border-transparent'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  isActive ? 'bg-[#151D40] text-[#22D3EE]' : 'bg-[#101735] text-[#A8B2D1]'
                }`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-bold truncate">{cat.label}</p>
                  <p className="text-[10px] text-[#A8B2D1] truncate">{cat.desc}</p>
                </div>
              </button>
            );
          })}

          <div className="pt-3 mt-2 border-t border-[#273154]">
            <button
              onClick={() => {
                logout();
                if (onNavigate) onNavigate('landing');
              }}
              className="w-full p-2.5 rounded-xl text-left text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 flex items-center gap-3 transition-colors text-xs font-semibold"
            >
              <LogOut className="w-4 h-4 ml-1" />
              <span>Log Out</span>
            </button>
          </div>
        </aside>

        {/* RIGHT COLUMN: DETAIL PANELS */}
        <main className="md:col-span-8 space-y-6">
          {/* 1. ACCESSIBILITY SETTINGS (WCAG 2.1 AA) */}
          {activeSection === 'accessibility' && (
            <div className="bg-[#151D40] p-6 sm:p-8 rounded-2xl border border-[#273154] shadow-md space-y-6">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Accessibility className="w-5 h-5 text-[#22D3EE]" />
                  <h2 className="text-lg font-bold text-white">WCAG 2.1 AA Accessibility Features</h2>
                </div>
                <p className="text-xs text-[#A8B2D1]">
                  Tailor the visual presentation and motion dynamics for universal ease-of-use.
                </p>
              </div>

              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between p-4 rounded-xl bg-[#101735] border border-[#273154]">
                  <div className="space-y-0.5 max-w-sm">
                    <p className="text-sm font-semibold text-white">High Contrast Mode</p>
                    <p className="text-xs text-[#A8B2D1]">Increases border contrast and reinforces background saturation.</p>
                  </div>
                  <GlassToggle
                    checked={settings.highContrast}
                    onChange={(val) => onUpdateSettings({ highContrast: val })}
                  />
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl bg-[#101735] border border-[#273154]">
                  <div className="space-y-0.5 max-w-sm">
                    <p className="text-sm font-semibold text-white">Reduce Motion</p>
                    <p className="text-xs text-[#A8B2D1]">Disables ambient background shifts and animations.</p>
                  </div>
                  <GlassToggle
                    checked={settings.reducedMotion}
                    onChange={(val) => onUpdateSettings({ reducedMotion: val })}
                  />
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl bg-[#101735] border border-[#273154]">
                  <div className="space-y-0.5 max-w-sm">
                    <p className="text-sm font-semibold text-white">Larger Typography</p>
                    <p className="text-xs text-[#A8B2D1]">Enlarges UI font scale for enhanced legibility.</p>
                  </div>
                  <GlassToggle
                    checked={settings.largeText}
                    onChange={(val) => onUpdateSettings({ largeText: val })}
                  />
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl bg-[#101735] border border-[#273154]">
                  <div className="space-y-0.5 max-w-sm">
                    <p className="text-sm font-semibold text-white">Screen Reader Guidance Hints</p>
                    <p className="text-xs text-[#A8B2D1]">Exposes explicit ARIA descriptors on 3D avatar keyframes.</p>
                  </div>
                  <GlassToggle
                    checked={settings.screenReaderHints}
                    onChange={(val) => onUpdateSettings({ screenReaderHints: val })}
                  />
                </div>
              </div>
            </div>
          )}

          {/* 2. PROFILE & ACCOUNT */}
          {activeSection === 'profile' && (
            <div className="bg-[#151D40] p-6 sm:p-8 rounded-2xl border border-[#273154] shadow-md space-y-6">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <User className="w-5 h-5 text-[#22D3EE]" />
                  <h2 className="text-lg font-bold text-white">Profile Information</h2>
                </div>
                <p className="text-xs text-[#A8B2D1]">
                  Manage your identity, role privileges, and authentication credentials.
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 rounded-xl bg-[#101735] border border-[#273154]">
                  <div className="w-12 h-12 rounded-xl bg-[#6366F1]/20 border border-[#273154] flex items-center justify-center text-lg font-bold text-white">
                    {user?.full_name?.charAt(0) || 'U'}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">{user?.full_name || 'Dr. Sanju'}</h3>
                    <p className="text-xs text-[#A8B2D1]">{user?.email || 'sanju@signaura.ai'}</p>
                    <span className="inline-block mt-1 text-[10px] font-mono px-2 py-0.5 rounded bg-[#151D40] text-[#22D3EE] border border-[#273154]">
                      {user?.role || 'Educator'}
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-[#A8B2D1]">Display Name</label>
                  <input
                    type="text"
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    className="w-full bg-[#101735] text-xs py-2.5 px-3 rounded-xl border border-[#273154] text-white focus:border-[#22D3EE] outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-[#A8B2D1]">Role</label>
                  <select
                    value={roleInput}
                    onChange={(e) => setRoleInput(e.target.value as any)}
                    className="w-full bg-[#101735] text-xs py-2.5 px-3 rounded-xl border border-[#273154] text-white outline-none"
                  >
                    <option value="Educator">Educator</option>
                    <option value="Student">Student</option>
                    <option value="General User">General User</option>
                    <option value="Researcher">Researcher</option>
                  </select>
                </div>

                <div className="pt-2 flex items-center justify-between">
                  {savedNotice && (
                    <span className="text-xs text-[#10B981] font-semibold flex items-center gap-1">
                      <Check className="w-3.5 h-3.5" />
                      Changes saved!
                    </span>
                  )}
                  <GlassButton
                    variant="primary"
                    size="sm"
                    onClick={handleSaveProfile}
                    className="ml-auto"
                  >
                    Save Changes
                  </GlassButton>
                </div>
              </div>
            </div>
          )}

          {/* 3. APPEARANCE & THEMES */}
          {activeSection === 'appearance' && (
            <div className="bg-[#151D40] p-6 sm:p-8 rounded-2xl border border-[#273154] shadow-md space-y-6">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Palette className="w-5 h-5 text-[#22D3EE]" />
                  <h2 className="text-lg font-bold text-white">Appearance & UI Theme</h2>
                </div>
                <p className="text-xs text-[#A8B2D1]">
                  SignAura operates with a clean modern solid dark SaaS interface.
                </p>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-[#101735] border border-[#273154] space-y-2">
                  <p className="text-sm font-semibold text-white">Active Theme: Solid Dark Navy SaaS</p>
                  <p className="text-xs text-[#A8B2D1]">
                    Deep Navy base (#080D24), solid surface (#151D40), subtle borders (#273154), and cyan accents (#22D3EE).
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 4. CERTIFIED ISL DICTIONARY */}
          {activeSection === 'language' && (
            <div className="bg-[#151D40] p-6 sm:p-8 rounded-2xl border border-[#273154] shadow-md space-y-5">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-[#22D3EE]" />
                  <h2 className="text-lg font-bold text-white">Certified Indian Sign Language Dictionary</h2>
                </div>
                <p className="text-xs text-[#A8B2D1]">
                  Explore verified ISL vocabulary tokens with definitions and direct 3D avatar testing.
                </p>
              </div>

              {/* Search & Category Pills */}
              <div className="space-y-3">
                <div className="relative">
                  <Search className="w-4 h-4 text-[#6B7A99] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={dictSearch}
                    onChange={(e) => setDictSearch(e.target.value)}
                    placeholder="Search ISL signs (e.g. Welcome, Doctor, Help)..."
                    className="w-full bg-[#101735] text-xs pl-10 pr-4 py-2.5 rounded-xl border border-[#273154] text-white focus:border-[#22D3EE] outline-none"
                  />
                </div>

                <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setSelectedCategory(cat)}
                      className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-colors whitespace-nowrap ${
                        selectedCategory === cat
                          ? 'bg-[#101735] text-[#22D3EE] border border-[#22D3EE]/50'
                          : 'bg-[#101735] text-[#A8B2D1] hover:text-white border border-[#273154]'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dictionary List */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[360px] overflow-y-auto pr-1">
                {filteredDict.map((item) => (
                  <div
                    key={item.id}
                    className="p-3.5 rounded-xl bg-[#101735] border border-[#273154] hover:border-[#3B4975] transition-colors flex flex-col justify-between space-y-2 group"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-xs font-bold text-white group-hover:text-[#22D3EE] transition-colors">
                          {item.word}
                        </h4>
                        <span className="text-[10px] font-mono text-[#22D3EE] font-bold">
                          {item.gloss}
                        </span>
                      </div>
                      <span className="text-[9px] px-2 py-0.5 rounded bg-[#151D40] text-[#A8B2D1] border border-[#273154]">
                        {item.category}
                      </span>
                    </div>

                    <p className="text-[11px] text-[#A8B2D1] line-clamp-2">
                      {item.definition}
                    </p>

                    {onTestSign && (
                      <div className="pt-2 border-t border-[#273154] flex justify-end">
                        <button
                          onClick={() => {
                            onTestSign(item.gloss);
                            if (onNavigate) onNavigate('avatar');
                          }}
                          className="text-[10px] font-bold text-[#22D3EE] hover:text-white flex items-center gap-1"
                        >
                          <Play className="w-3 h-3" />
                          <span>Test in 3D Avatar</span>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5. NOTIFICATIONS */}
          {activeSection === 'notifications' && (
            <div className="bg-[#151D40] p-6 sm:p-8 rounded-2xl border border-[#273154] shadow-md space-y-6">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-[#22D3EE]" />
                  <h2 className="text-lg font-bold text-white">Notification Preferences</h2>
                </div>
                <p className="text-xs text-[#A8B2D1]">
                  Control real-time updates and pipeline completion notifications.
                </p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between p-4 rounded-xl bg-[#101735] border border-[#273154]">
                  <div className="space-y-0.5">
                    <p className="text-sm font-semibold text-white">Video Processing Alerts</p>
                    <p className="text-xs text-[#A8B2D1]">Notify when 3D avatar keyframes finish generating.</p>
                  </div>
                  <GlassToggle checked={true} onChange={() => {}} />
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl bg-[#101735] border border-[#273154]">
                  <div className="space-y-0.5">
                    <p className="text-sm font-semibold text-white">ISL Lexicon Updates</p>
                    <p className="text-xs text-[#A8B2D1]">Alerts when new certified signs are added to the library.</p>
                  </div>
                  <GlassToggle checked={true} onChange={() => {}} />
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
