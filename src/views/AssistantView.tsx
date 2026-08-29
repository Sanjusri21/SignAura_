import React, { useState, useRef, useEffect } from 'react';
import { 
  BotMessageSquare, 
  Send, 
  Mic, 
  MicOff, 
  Sparkles, 
  RotateCcw, 
  User, 
  Play, 
  Layers
} from 'lucide-react';
import { ChatMessage, NavigationTab } from '../types';
import { INITIAL_CHAT_MESSAGES } from '../data/mockData';
import { GlassButton } from '../components/ui/GlassButton';
import { signAuraApi } from '../services/api';

interface AssistantViewProps {
  onTestSign?: (sign: string) => void;
  onNavigate?: (tab: NavigationTab) => void;
}

export const AssistantView: React.FC<AssistantViewProps> = ({
  onTestSign,
  onNavigate
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isAiTyping, setIsAiTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const promptSuggestions = [
    "Translate 'Where is the nearest hospital?' into ISL",
    "Explain non-manual facial markers in Indian Sign Language",
    "How does Subject-Object-Verb (SOV) order work in ISL?",
    "Generate sign sequence for: 'Welcome to India friend'"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isAiTyping]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputValue;
    if (!text.trim()) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text.trim(),
      timestamp: 'Just now'
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputValue('');
    setIsAiTyping(true);

    try {
      // Call backend FastAPI endpoint
      const response = await signAuraApi.sendChatMessage(text.trim());
      const aiMsg: ChatMessage = {
        id: response.id || `ai-${Date.now()}`,
        sender: 'ai',
        text: response.text,
        timestamp: response.timestamp || 'Just now',
        glossSequence: response.glossSequence || [],
        recommendedSigns: response.recommendedSigns || []
      };
      setIsAiTyping(false);
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      // Graceful offline fallback
      let aiText = '';
      let glosses: string[] = [];
      let signs: string[] = [];

      const lower = text.toLowerCase();
      if (lower.includes('hospital') || lower.includes('medical') || lower.includes('doctor')) {
        aiText = "In Indian Sign Language, medical questions place the location and question marker at the end. Here is the canonical ISL grammar breakdown:";
        glosses = ['HOSPITAL', 'NEARBY', 'WHERE', '[EYEBROW-RAISE]'];
        signs = ['DOCTOR', 'HELP', 'HOW_ARE_YOU'];
      } else if (lower.includes('non-manual') || lower.includes('facial') || lower.includes('marker')) {
        aiText = "Non-manual markers (NMMs) in ISL include eyebrow raises for yes/no questions, head tilts for spatial relationships, and mouthing for lexical disambiguation.";
        glosses = ['FACIAL-EXPRESSION', 'HEAD-TILT', 'GRAMMAR-IMPORTANT'];
        signs = ['SIGN_LANGUAGE', 'ACCESSIBLE', 'WELCOME'];
      } else if (lower.includes('welcome') || lower.includes('india') || lower.includes('friend')) {
        aiText = "Here is the natural ISL translation for welcoming someone to India with polite respect:";
        glosses = ['INDIA', 'FRIEND', 'WELCOME', '[SMILE]'];
        signs = ['INDIA', 'WELCOME', 'HELLO', 'THANK_YOU'];
      } else {
        aiText = `Here is the Indian Sign Language (ISL) syntactic gloss translation for "${text}":`;
        glosses = text.toUpperCase().replace(/[^A-Z ]/g, '').split(' ').filter(Boolean);
        if (glosses.length > 5) glosses = glosses.slice(0, 5);
        signs = ['WELCOME', 'ACCESSIBLE', 'THANK_YOU'];
      }

      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: aiText,
        timestamp: 'Just now',
        glossSequence: glosses,
        recommendedSigns: signs
      };

      setIsAiTyping(false);
      setMessages((prev) => [...prev, aiMsg]);
    }
  };

  const toggleRecording = () => {
    if (!isRecording) {
      setIsRecording(true);
      setTimeout(() => {
        setIsRecording(false);
        setInputValue("Translate 'Please help me learn Indian Sign Language' to ISL");
      }, 2500);
    } else {
      setIsRecording(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-140px)] min-h-[580px] pb-4 space-y-4">
      {/* Header */}
      <div className="glass-card p-4 rounded-[28px] border border-white/14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-white/10 flex items-center justify-center text-white border border-white/14">
            <BotMessageSquare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-white">SignAura AI Copilot</h1>
              <span className="glass-badge text-[10px]">ISL Grammar Engine</span>
            </div>
            <p className="text-xs text-slate-400">Ask any sign language translation or syntax question</p>
          </div>
        </div>

        <GlassButton
          variant="ghost"
          size="sm"
          onClick={() => setMessages(INITIAL_CHAT_MESSAGES)}
          icon={<RotateCcw className="w-3.5 h-3.5 text-slate-400" />}
        >
          Clear
        </GlassButton>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 glass-card rounded-[32px] p-4 sm:p-6 border border-white/14 overflow-y-auto space-y-4 backdrop-blur-2xl scrollbar-thin">
        {messages.map((msg) => {
          const isAi = msg.sender === 'ai';
          return (
            <div
              key={msg.id}
              className={`flex items-start gap-3 ${isAi ? '' : 'flex-row-reverse'}`}
            >
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                isAi 
                  ? 'bg-white/14 text-white border border-white/20' 
                  : 'bg-white/25 text-white border border-white/30'
              }`}>
                {isAi ? <Sparkles className="w-4 h-4" /> : <User className="w-4 h-4" />}
              </div>

              <div className={`max-w-xl rounded-3xl p-4 border transition-all ${
                isAi
                  ? 'glass-subtle text-slate-200 border-white/14 shadow-lg'
                  : 'bg-white/18 text-white border-white/28 shadow-md'
              }`}>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.text}
                </p>

                {/* Embedded ISL Gloss Sequence */}
                {msg.glossSequence && msg.glossSequence.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
                    <span className="text-[11px] font-bold text-white flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5" />
                      Syntactic ISL Gloss Sequence:
                    </span>

                    <div className="flex flex-wrap gap-1.5 font-mono text-xs">
                      {msg.glossSequence.map((g, i) => (
                        <span 
                          key={i} 
                          className="px-2.5 py-1 rounded-xl bg-black/40 text-white border border-white/14"
                        >
                          {g}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommended Signs to test */}
                {msg.recommendedSigns && msg.recommendedSigns.length > 0 && (
                  <div className="mt-3 pt-2 flex flex-wrap items-center gap-2">
                    <span className="text-[10px] text-slate-400">Launch 3D Gesture:</span>
                    {msg.recommendedSigns.map((s) => (
                      <button
                        key={s}
                        onClick={() => {
                          onTestSign?.(s);
                          onNavigate?.('avatar');
                        }}
                        className="glass-subtle hover:bg-white/12 text-[11px] font-semibold py-1 px-2.5 rounded-xl border border-white/14 text-white flex items-center gap-1 transition-all"
                      >
                        <Play className="w-2.5 h-2.5" />
                        <span>{s}</span>
                      </button>
                    ))}
                  </div>
                )}

                <span className="text-[10px] text-slate-400 block mt-2 text-right">
                  {msg.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {isAiTyping && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-white/14 flex items-center justify-center text-white">
              <Sparkles className="w-4 h-4 animate-spin" />
            </div>
            <div className="glass-subtle px-4 py-2.5 rounded-2xl border border-white/14 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-white animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestion Chips */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-none select-none">
        {promptSuggestions.map((prompt, i) => (
          <button
            key={i}
            onClick={() => handleSendMessage(prompt)}
            className="flex-shrink-0 glass-subtle hover:bg-white/10 px-3 py-1.5 rounded-xl text-xs text-slate-300 hover:text-white border border-white/10 transition-all truncate max-w-xs"
          >
            "{prompt}"
          </button>
        ))}
      </div>

      {/* Input Glass Bar */}
      <div className="glass-card rounded-[28px] p-2 border border-white/18 shadow-xl flex items-center gap-2 backdrop-blur-3xl">
        <button
          onClick={toggleRecording}
          className={`p-3 rounded-2xl transition-all ${
            isRecording
              ? 'bg-rose-500 text-white animate-pulse shadow-lg shadow-rose-500/40'
              : 'glass-subtle hover:bg-white/10 text-slate-300 hover:text-white border border-white/10'
          }`}
          title={isRecording ? 'Listening... click to stop' : 'Record voice query'}
        >
          {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </button>

        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSendMessage();
          }}
          placeholder={isRecording ? 'Listening to speech...' : 'Ask SignAura AI or type a sentence to translate...'}
          className="flex-1 glass-input text-sm py-2 px-3 rounded-2xl border-none shadow-none focus:ring-0 bg-transparent"
        />

        <GlassButton
          variant="primary"
          size="icon"
          onClick={() => handleSendMessage()}
          disabled={!inputValue.trim()}
          icon={<Send className="w-4 h-4 text-slate-900" />}
        />
      </div>
    </div>
  );
};
