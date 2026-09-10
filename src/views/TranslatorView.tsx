import React, { useState } from 'react';
import { 
  Languages, 
  Sparkles, 
  ArrowRight, 
  UserSquare2, 
  Copy, 
  Check, 
  Play
} from 'lucide-react';
import { ISLDialect, VideoProject, GlossToken, NavigationTab } from '../types';
import { GlassButton } from '../components/ui/GlassButton';
import { signAuraApi } from '../services/api';

interface TranslatorViewProps {
  currentDialect: ISLDialect;
  onDialectChange: (dialect: ISLDialect) => void;
  onSendToAvatar: (project: VideoProject) => void;
  onNavigate: (tab: NavigationTab) => void;
}

export const TranslatorView: React.FC<TranslatorViewProps> = ({
  currentDialect,
  onDialectChange,
  onSendToAvatar,
  onNavigate,
}) => {
  const [inputText, setInputText] = useState('Where is the nearest medical clinic?');
  const [isTranslating, setIsTranslating] = useState(false);
  const [translatedGloss, setTranslatedGloss] = useState<string[]>(['CLINIC', 'MEDICAL', 'NEARBY', 'WHERE', '[EYEBROW-RAISE]']);
  const [copied, setCopied] = useState(false);

  const samplePhrases = [
    'Where is the nearest medical clinic?',
    'Welcome to our digital accessibility studio.',
    'Please help me find the train platform.',
    'Thank you for joining the meeting today.',
    'I need an Indian Sign Language interpreter.'
  ];

  const handleTranslate = async () => {
    if (!inputText.trim()) return;
    setIsTranslating(true);

    try {
      const response = await signAuraApi.translateISL(inputText.trim(), currentDialect);
      if (response && response.gloss && response.gloss.length > 0) {
        setTranslatedGloss(response.gloss);
      } else {
        const words = inputText.toUpperCase().replace(/[^A-Z ]/g, '').split(' ').filter(Boolean);
        setTranslatedGloss(words);
      }
    } catch (err) {
      const words = inputText.toUpperCase().replace(/[^A-Z ]/g, '').split(' ').filter(Boolean);
      setTranslatedGloss(words.length > 0 ? words : ['WELCOME', 'ACCESSIBLE', 'INDIA']);
    } finally {
      setIsTranslating(false);
    }
  };

  const handleCopyGloss = () => {
    navigator.clipboard.writeText(translatedGloss.join(' '));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePreviewInAvatar = () => {
    const tokens: GlossToken[] = translatedGloss.map((g, idx) => ({
      id: `gloss-${idx}-${Date.now()}`,
      word: g.toLowerCase().replace(/\[.*?\]/g, ''),
      gloss: g,
      startTime: idx * 2.0,
      endTime: (idx + 1) * 2.0,
      confidence: 0.98,
      grammarTag: idx === 0 ? 'SUBJECT' : idx === translatedGloss.length - 1 ? 'QUESTION_MARKER' : 'OBJECT'
    }));

    const project: VideoProject = {
      id: `trans-${Date.now()}`,
      title: inputText.slice(0, 32) || 'Text Translation',
      duration: Math.max(tokens.length * 2.0, 4.0),
      createdAt: new Date().toISOString(),
      status: 'completed',
      accuracy: 98.5,
      transcript: inputText,
      glossTokens: tokens,
      language: 'English/Hindi',
      dialect: currentDialect
    };

    onSendToAvatar(project);
    onNavigate('avatar');
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-20">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">ISL Syntactic Translator</h1>
          <p className="text-xs sm:text-sm text-[#A8B2D1] mt-0.5">
            Convert English and Hindi into grammatically ordered Indian Sign Language tokens (SOV).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-[#A8B2D1]">Dialect:</span>
          <select
            value={currentDialect}
            onChange={(e) => onDialectChange(e.target.value as ISLDialect)}
            className="bg-[#151D40] text-xs font-semibold text-[#22D3EE] py-1.5 px-3 rounded-lg border border-[#273154] outline-none"
          >
            <option value="standard">Standard ISL</option>
            <option value="north">Northern Dialect</option>
            <option value="south">Southern Dialect</option>
          </select>
        </div>
      </div>

      {/* Main Dual Panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Left: Input Text Panel */}
        <div className="bg-[#151D40] rounded-2xl p-5 sm:p-6 border border-[#273154] shadow-md flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                Source Spoken/Written Text
              </span>
              <span className="text-[11px] text-[#A8B2D1]">English / Hindi</span>
            </div>

            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type or paste sentences to translate into ISL..."
              rows={6}
              className="w-full bg-[#101735] text-sm p-4 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white placeholder-[#6B7A99] outline-none resize-none leading-relaxed"
            />
          </div>

          <div className="space-y-3">
            <div>
              <p className="text-[11px] font-semibold text-[#A8B2D1] mb-1.5">Try sample phrases:</p>
              <div className="flex flex-wrap gap-1.5">
                {samplePhrases.map((phrase, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInputText(phrase)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-[#101735] text-[#A8B2D1] hover:text-white hover:bg-[#1A244D] border border-[#273154] transition-colors"
                  >
                    {phrase.slice(0, 24)}...
                  </button>
                ))}
              </div>
            </div>

            <GlassButton
              variant="primary"
              size="md"
              onClick={handleTranslate}
              disabled={isTranslating || !inputText.trim()}
              className="w-full justify-center font-bold"
              icon={<Languages className="w-4 h-4 text-[#080D24]" />}
            >
              {isTranslating ? 'Translating Syntax...' : 'Translate to ISL Gloss'}
            </GlassButton>
          </div>
        </div>

        {/* Right: Output Gloss Panel */}
        <div className="bg-[#151D40] rounded-2xl p-5 sm:p-6 border border-[#273154] shadow-md flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#22D3EE] uppercase tracking-wider">
                ISL Syntactic Representation (SOV)
              </span>

              {translatedGloss.length > 0 && (
                <button
                  onClick={handleCopyGloss}
                  className="text-xs text-[#A8B2D1] hover:text-white flex items-center gap-1.5 transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              )}
            </div>

            {/* Gloss Tokens Container */}
            <div className="bg-[#101735] rounded-xl p-4 min-h-[160px] border border-[#273154] flex flex-wrap content-start gap-2">
              {translatedGloss.length > 0 ? (
                translatedGloss.map((token, idx) => {
                  const isMarker = token.startsWith('[');
                  return (
                    <span
                      key={idx}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition-transform shadow-sm ${
                        isMarker
                          ? 'bg-[#8B5CF6]/15 text-[#A78BFA] border-[#8B5CF6]/30'
                          : 'bg-[#151D40] text-[#22D3EE] border-[#273154]'
                      }`}
                    >
                      {token}
                    </span>
                  );
                })
              ) : (
                <p className="text-xs text-[#6B7A99] italic">Click Translate to generate ISL tokens.</p>
              )}
            </div>

            <div className="bg-[#101735] p-3 rounded-xl border border-[#273154] text-xs text-[#A8B2D1] space-y-1">
              <p className="font-semibold text-white">Grammar Transformation:</p>
              <p className="text-[11px] text-[#A8B2D1]">
                Subject-Object-Verb syntactic ordering with non-manual facial markers applied for authentic ISL semantics.
              </p>
            </div>
          </div>

          <GlassButton
            variant="secondary"
            size="md"
            onClick={handlePreviewInAvatar}
            disabled={translatedGloss.length === 0}
            className="w-full justify-center"
            icon={<UserSquare2 className="w-4 h-4 text-[#22D3EE]" />}
          >
            Animate in 3D Avatar
          </GlassButton>
        </div>

      </div>
    </div>
  );
};
