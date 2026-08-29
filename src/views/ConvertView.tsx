import React, { useState, useRef } from 'react';
import { 
  Upload, 
  Link2, 
  Sparkles, 
  CheckCircle2, 
  ArrowRight, 
  Settings, 
  PlaySquare,
  Volume2,
  Radio,
  Layers,
  UserSquare2,
  FileVideo
} from 'lucide-react';
import { ISLDialect } from '../types';
import { GlassButton } from '../components/ui/GlassButton';
import { GlassCard } from '../components/ui/GlassCard';

export interface ConvertPayload {
  file?: File;
  url?: string;
  presetText?: string;
  title: string;
  duration?: number;
}

interface ConvertViewProps {
  currentDialect: ISLDialect;
  onDialectChange: (dialect: ISLDialect) => void;
  onStartProcessing: (payload: ConvertPayload) => void;
}

export const ConvertView: React.FC<ConvertViewProps> = ({
  currentDialect,
  onDialectChange,
  onStartProcessing
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [isUrlValid, setIsUrlValid] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const workflowSteps = [
    { title: 'Video Ingest', desc: 'Audio Extraction', icon: FileVideo },
    { title: 'Acoustics', desc: 'Noise Filtration', icon: Volume2 },
    { title: 'Whisper AI', desc: 'Speech to Text', icon: Radio },
    { title: 'ISL SOV', desc: 'Syntactic Gloss', icon: Layers },
    { title: 'SignAvatar', desc: '3D Articulation', icon: UserSquare2 }
  ];

  const samplePresets = [
    {
      id: 'p1',
      title: 'Accessibility Keynote & Welcome Address',
      duration: 34.5,
      type: 'Conference Lecture',
      desc: 'English speech welcoming attendees and explaining ISL accessibility mission.'
    },
    {
      id: 'p2',
      title: 'Emergency Medical Triage Guideline',
      duration: 48.0,
      type: 'Healthcare Instruction',
      desc: 'First responder dialog asking symptoms and coordinating immediate assistance.'
    },
    {
      id: 'p3',
      title: 'Computer Science: Algorithms Intro',
      duration: 120.0,
      type: 'Educational STEM',
      desc: 'Classroom explanation on data structures and step-by-step problem solving.'
    },
    {
      id: 'p4',
      title: 'Metro Transit Public Announcement',
      duration: 18.0,
      type: 'Public Transport',
      desc: 'Train arrival notification and safety instructions for passengers.'
    }
  ];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setSelectedPreset(null);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setSelectedPreset(null);
    }
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setVideoUrl(val);
    setIsUrlValid(val.trim().length > 10 && (val.includes('http') || val.includes('youtu') || val.includes('vimeo')));
    if (val.trim()) {
      setSelectedFile(null);
      setSelectedPreset(null);
    }
  };

  const handleSelectPreset = (preset: typeof samplePresets[0]) => {
    setSelectedPreset(preset.id);
    setSelectedFile(null);
    setVideoUrl('');
  };

  const handleSubmit = () => {
    if (selectedFile) {
      onStartProcessing({
        file: selectedFile,
        title: selectedFile.name.replace(/\.[^/.]+$/, ''),
        duration: 30
      });
    } else if (selectedPreset) {
      const p = samplePresets.find(x => x.id === selectedPreset);
      if (p) {
        onStartProcessing({
          presetText: p.desc,
          title: p.title,
          duration: p.duration
        });
      }
    } else if (videoUrl) {
      onStartProcessing({
        url: videoUrl,
        title: 'Web Video Conversion',
        duration: 45
      });
    }
  };

  const isReady = !!selectedFile || !!selectedPreset || (videoUrl.trim().length > 0 && isUrlValid);

  return (
    <div className="max-w-4xl mx-auto space-y-10 pb-20">
      
      {/* 1. HEADER */}
      <div className="text-center space-y-3">
        <div className="glass-subtle px-3.5 py-1.5 rounded-full inline-flex items-center gap-2 border border-white/14 mb-1">
          <Sparkles className="w-3.5 h-3.5 text-white" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Multi-Modal Ingestion
          </span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
          Convert Media to Sign Language
        </h1>
        <p className="text-sm sm:text-base text-slate-400 max-w-xl mx-auto leading-relaxed">
          Upload any media file or paste a video URL. Our neural pipeline will transcribe speech, extract syntactic ISL gloss, and synthesize 3D SignAvatar gestures.
        </p>
      </div>

      {/* 2. SPATIAL WORKFLOW PIPELINE VISUALIZER */}
      <div className="glass-card p-5 sm:p-6 rounded-[28px] border border-white/14">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3 text-center">
          Multimodal Conversion Pipeline
        </p>
        <div className="flex items-center justify-between gap-1 sm:gap-2 overflow-x-auto pb-1">
          {workflowSteps.map((step, i) => {
            const Icon = step.icon;
            return (
              <React.Fragment key={i}>
                <div className="flex flex-col items-center text-center p-2 rounded-2xl glass-subtle flex-1 min-w-[90px]">
                  <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center text-white mb-1.5">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-xs font-bold text-white tracking-tight">{step.title}</span>
                  <span className="text-[10px] text-slate-400">{step.desc}</span>
                </div>

                {i < workflowSteps.length - 1 && (
                  <div className="text-slate-600 px-0.5">→</div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* 3. MINIMAL LIQUID GLASS DROP ZONE */}
      <div 
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`glass-card p-10 sm:p-14 rounded-[36px] border-2 border-dashed text-center cursor-pointer transition-all duration-300 relative overflow-hidden select-none group ${
          isDragOver 
            ? 'border-white bg-white/12 scale-[1.01] shadow-[0_0_40px_rgba(255,255,255,0.25)]' 
            : selectedFile 
              ? 'border-white/40 bg-white/8' 
              : 'border-white/18 hover:border-white/35 hover:bg-white/7'
        }`}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          accept="video/mp4,video/quicktime,video/webm,audio/mp3,audio/wav" 
          className="hidden" 
          onChange={handleFileInput}
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
            <Upload className="w-7 h-7 text-white" />
          </div>

          <div className="space-y-1">
            <h2 className="text-lg sm:text-xl font-bold text-white">
              {selectedFile ? selectedFile.name : 'Drop video or audio file here'}
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              {selectedFile 
                ? `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB • Ready for neural conversion` 
                : 'or click to browse files from your device'}
            </p>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <span className="glass-badge text-[10px]">MP4</span>
            <span className="glass-badge text-[10px]">MOV</span>
            <span className="glass-badge text-[10px]">WEBM</span>
            <span className="glass-badge text-[10px]">WAV</span>
          </div>
        </div>
      </div>

      {/* 4. INGEST FROM VIDEO URL */}
      <div className="glass-card p-6 rounded-[28px] border border-white/14 space-y-3">
        <div className="flex items-center gap-2">
          <Link2 className="w-4 h-4 text-white" />
          <h2 className="text-sm font-bold text-white">Or Ingest from Video URL</h2>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-2.5">
          <input
            type="url"
            value={videoUrl}
            onChange={handleUrlChange}
            placeholder="Paste YouTube, Loom, Vimeo, or MP4 link..."
            className="w-full glass-input text-sm py-2.5 px-4 rounded-2xl flex-1"
          />

          <GlassButton
            variant="secondary"
            size="md"
            onClick={handleSubmit}
            disabled={!isUrlValid}
            className="w-full sm:w-auto"
          >
            Fetch Video
          </GlassButton>
        </div>
      </div>

      {/* 5. PRE-LOADED TEST CLIPS */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <PlaySquare className="w-4 h-4 text-slate-300" />
            Pre-Loaded Test Clips
          </h2>
          <span className="text-xs text-slate-400">1-Click Instant Demo</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {samplePresets.map((p) => {
            const isSelected = selectedPreset === p.id;
            return (
              <div
                key={p.id}
                onClick={() => handleSelectPreset(p)}
                className={`p-4 rounded-2xl glass-subtle hover:bg-white/10 border transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                  isSelected
                    ? 'border-white/40 bg-white/15 shadow-[0_0_20px_rgba(255,255,255,0.18)]'
                    : 'border-white/10 hover:border-white/20'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-300 bg-white/8 px-2 py-0.5 rounded-full border border-white/10">
                      {p.type}
                    </span>
                    <span className="text-xs font-mono text-slate-400">{p.duration}s</span>
                  </div>
                  <h3 className="text-sm font-bold text-white">{p.title}</h3>
                  <p className="text-xs text-slate-400 line-clamp-2 mt-1">{p.desc}</p>
                </div>

                {isSelected && (
                  <div className="text-[11px] text-white font-semibold flex items-center gap-1 mt-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Selected for Conversion
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 6. CONVERSION PARAMETERS */}
      <div className="glass-card p-6 rounded-[28px] border border-white/14 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Settings className="w-4 h-4 text-slate-300" />
          Synthesis Preferences
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 rounded-2xl glass-subtle border border-white/10 space-y-1">
            <span className="text-xs font-semibold text-slate-300">Target Dialect</span>
            <select
              value={currentDialect}
              onChange={(e) => onDialectChange(e.target.value as ISLDialect)}
              className="w-full glass-input text-xs p-2 rounded-xl bg-black/40 text-white"
            >
              <option value="standard">ISL Standard (National)</option>
              <option value="north">ISL Northern Variant</option>
              <option value="south">ISL Southern Variant</option>
            </select>
          </div>

          <div className="p-3 rounded-2xl glass-subtle border border-white/10 space-y-1">
            <span className="text-xs font-semibold text-slate-300">Avatar Motion Engine</span>
            <select className="w-full glass-input text-xs p-2 rounded-xl bg-black/40 text-white">
              <option>Spatial 3D Articulated Rig (60 FPS)</option>
              <option>Expressive Facial Non-Manual Markers</option>
            </select>
          </div>

          <div className="p-3 rounded-2xl glass-subtle border border-white/10 space-y-1">
            <span className="text-xs font-semibold text-slate-300">Gloss Overlay Style</span>
            <select className="w-full glass-input text-xs p-2 rounded-xl bg-black/40 text-white">
              <option>Liquid Glass Subtitle Stream</option>
              <option>Dual Spoken + ISL Timeline</option>
            </select>
          </div>
        </div>
      </div>

      {/* 7. START CONVERTING BUTTON */}
      <div className="pt-2 flex justify-center">
        <GlassButton
          variant="primary"
          size="lg"
          onClick={handleSubmit}
          disabled={!isReady}
          icon={<Sparkles className="w-4 h-4 text-slate-900" />}
        >
          Start Neural Conversion
        </GlassButton>
      </div>

    </div>
  );
};
