import React, { useState, useRef, useEffect } from 'react';
import { 
  BotMessageSquare, 
  Send, 
  Mic, 
  MicOff, 
  Sparkles, 
  User, 
  Play, 
  Copy, 
  Check 
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
  const [copiedId, setCopiedId] = useState<string | null>(null);
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
      // Offline fallback
      let aiText = '';
      let glosses: string[] = [];
      let signs: string[] = [];

      const lower = text.toLowerCase();
      if (lower.includes('hospital') || lower.includes('medical') || lower.includes('doctor')) {
        aiText = "In Indian Sign Language, medical questions place the location and question marker at the end:";
        glosses = ['HOSPITAL', 'NEARBY', 'WHERE', '[EYEBROW-RAISE]'];
        signs = ['DOCTOR', 'HELP', 'HOW_ARE_YOU'];
      } else if (lower.includes('non-manual') || lower.includes('facial') || lower.includes('marker')) {
        aiText = "Non-manual markers (NMMs) in ISL include eyebrow raises for questions and head tilts for spatial references.";
        glosses = ['FACIAL-EXPRESSION', 'HEAD-TILT', 'GRAMMAR-IMPORTANT'];
        signs = ['SIGN_LANGUAGE', 'ACCESSIBLE', 'WELCOME'];
      } else if (lower.includes('welcome') || lower.includes('india') || lower.includes('friend')) {
        aiText = "Here is the natural ISL translation for welcoming someone to India:";
        glosses = ['INDIA', 'FRIEND', 'WELCOME', '[SMILE]'];
        signs = ['INDIA', 'WELCOME', 'HELLO', 'THANK_YOU'];
      } else {
        aiText = `Here is the Indian Sign Language (ISL) Subject-Object-Verb syntactic translation for "${text}":`;
        glosses = text.toUpperCase().replace(/[^A-Z ]/g, '').split(' ').filter(Boolean);
        if (glosses.length > 5) glosses = glosses.slice(0, 5);
        signs = ['WELCOME', 'ACCESSIBLE', 'THANK_YOU'];
      }

      setIsAiTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: aiText,
          timestamp: 'Just now',
          glossSequence: glosses,
          recommendedSigns: signs
        }
      ]);
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
    } else {
      setIsRecording(true);
      setTimeout(() => {
        setIsRecording(false);
        setInputValue('How do I sign emergency assistance in ISL?');
      }, 2000);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-5 pb-20">
      {/* 1. HEADER */}
      <div className="bg-[#151D40] p-4 sm:p-5 rounded-2xl border border-[#273154] flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#101735] border border-[#273154] flex items-center justify-center text-[#22D3EE]">
            <BotMessageSquare className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">SignAura AI</h1>
            <p className="text-xs text-[#A8B2D1]">Multimodal Indian Sign Language Accessibility Copilot</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-[#10B981] bg-[#101735] px-2.5 py-1 rounded-lg border border-[#273154]">
          <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
          <span>Active</span>
        </div>
      </div>

      {/* 2. CHAT CONTAINER & MESSAGES */}
      <div className="bg-[#151D40] rounded-2xl border border-[#273154] flex flex-col h-[560px] shadow-xl overflow-hidden">
        
        {/* Messages List Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';

            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
              >
                {/* Avatar Icon */}
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold border ${
                    isUser
                      ? 'bg-[#6366F1] text-white border-[#6366F1]'
                      : 'bg-[#101735] text-[#22D3EE] border-[#273154]'
                  }`}
                >
                  {isUser ? <User className="w-4 h-4" /> : <BotMessageSquare className="w-4 h-4" />}
                </div>

                {/* Message Bubble (Solid surfaces) */}
                <div className="space-y-2">
                  <div
                    className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed border shadow-sm ${
                      isUser
                        ? 'bg-[#6366F1] text-white border-[#6366F1] rounded-tr-none'
                        : 'bg-[#101735] text-slate-100 border-[#273154] rounded-tl-none'
                    }`}
                  >
                    <p>{msg.text}</p>

                    {/* Syntactic ISL Gloss Chips */}
                    {msg.glossSequence && msg.glossSequence.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-[#273154] space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-[#22D3EE]">
                            ISL Subject-Object-Verb Gloss:
                          </span>
                          <button
                            onClick={() => copyToClipboard(msg.glossSequence!.join(' '), msg.id)}
                            className="text-[10px] text-[#A8B2D1] hover:text-white flex items-center gap-1 transition-colors"
                          >
                            {copiedId === msg.id ? <Check className="w-3 h-3 text-[#10B981]" /> : <Copy className="w-3 h-3" />}
                            <span>{copiedId === msg.id ? 'Copied' : 'Copy'}</span>
                          </button>
                        </div>

                        <div className="flex flex-wrap gap-1.5">
                          {msg.glossSequence.map((g, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-[#151D40] text-white text-[11px] font-mono font-bold border border-[#273154]"
                            >
                              {g}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Recommended Interactive Signs */}
                    {msg.recommendedSigns && msg.recommendedSigns.length > 0 && (
                      <div className="mt-2.5 pt-2.5 border-t border-[#273154] flex flex-wrap items-center gap-1.5">
                        <span className="text-[10px] font-semibold text-[#A8B2D1]">Test in 3D Avatar:</span>
                        {msg.recommendedSigns.map((s, i) => (
                          <button
                            key={i}
                            onClick={() => {
                              if (onTestSign) onTestSign(s);
                              if (onNavigate) onNavigate('avatar');
                            }}
                            className="px-2 py-0.5 rounded bg-[#151D40] text-[#22D3EE] text-[10px] font-bold hover:bg-[#1A244D] border border-[#273154] flex items-center gap-1 transition-colors"
                          >
                            <Play className="w-2.5 h-2.5" />
                            <span>{s}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <span className="text-[10px] text-[#6B7A99] px-1">{msg.timestamp}</span>
                </div>
              </div>
            );
          })}

          {/* Typing Indicator */}
          {isAiTyping && (
            <div className="flex gap-3 max-w-[80%] mr-auto">
              <div className="w-8 h-8 rounded-lg bg-[#101735] text-[#22D3EE] border border-[#273154] flex items-center justify-center flex-shrink-0">
                <BotMessageSquare className="w-4 h-4" />
              </div>
              <div className="bg-[#101735] p-3 rounded-2xl rounded-tl-none border border-[#273154] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-[#22D3EE] animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Prompt Suggestions */}
        <div className="p-3 bg-[#101735] border-t border-[#273154] flex gap-2 overflow-x-auto select-none">
          {promptSuggestions.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              className="flex-shrink-0 text-left px-3 py-1.5 rounded-lg bg-[#151D40] text-[#A8B2D1] hover:text-white hover:bg-[#1A244D] border border-[#273154] text-xs transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Box & Mic Button */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="p-3.5 bg-[#151D40] border-t border-[#273154] flex items-center gap-2"
        >
          <button
            type="button"
            onClick={toggleRecording}
            className={`p-2.5 rounded-xl border transition-colors ${
              isRecording
                ? 'bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse'
                : 'bg-[#101735] text-[#A8B2D1] hover:text-white border-[#273154] hover:bg-[#1A244D]'
            }`}
            title={isRecording ? 'Stop voice recording' : 'Speak into microphone'}
            aria-label={isRecording ? 'Stop voice recording' : 'Speak into microphone'}
          >
            {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={isRecording ? 'Listening for speech...' : 'Type a question or sentence for ISL translation...'}
            className="flex-1 bg-[#101735] text-xs sm:text-sm py-2.5 px-3.5 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white placeholder-[#6B7A99] outline-none"
          />

          <GlassButton
            type="submit"
            variant="primary"
            size="md"
            disabled={!inputValue.trim()}
            icon={<Send className="w-4 h-4 text-[#080D24]" />}
          >
            Send
          </GlassButton>
        </form>

      </div>
    </div>
  );
};
