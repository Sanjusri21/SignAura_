import React, { useState, useRef } from 'react';
import { 
  Upload, 
  Link2, 
  Sparkles, 
  FileVideo,
  Radio,
  Volume2,
  Layers,
  UserSquare2,
  ArrowRight,
  Clock,
  Play,
  ArrowDown
} from 'lucide-react';
import { ISLDialect } from '../types';
import { GlassButton } from '../components/ui/GlassButton';

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
  const [activeMode, setActiveMode] = useState<'upload' | 'url'>('upload');
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [isUrlValid, setIsUrlValid] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const pipelineSteps = [
    { title: 'VIDEO', desc: 'Media Ingest', icon: FileVideo },
    { title: 'SPEECH RECOGNITION', desc: 'Whisper ASR', icon: Radio },
    { title: 'TEXT', desc: 'NLP Parser', icon: Volume2 },
    { title: 'ISL TRANSLATION', desc: 'SOV Grammar', icon: Layers },
    { title: 'SIGN MOTION', desc: 'SMPL-X Kinematics', icon: Sparkles },
    { title: '3D AVATAR', desc: 'Interactive Rig', icon: UserSquare2 }
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
    setIsUrlValid(val.trim().length > 8);
    if (val.trim()) {
      setSelectedFile(null);
      setSelectedPreset(null);
    }
  };

  const handleSelectPreset = (preset: typeof samplePresets[0]) => {
    setSelectedPreset(preset.id);
    setSelectedFile(null);
    setVideoUrl('');
    setIsUrlValid(false);
  };

  const handleLaunchPipeline = () => {
    if (selectedFile) {
      onStartProcessing({
        file: selectedFile,
        title: selectedFile.name.replace(/\.[^/.]+$/, ''),
        duration: 25.0
      });
    } else if (isUrlValid && videoUrl) {
      onStartProcessing({
        url: videoUrl,
        title: 'Web Stream Video',
        duration: 30.0
      });
    } else if (selectedPreset) {
      const found = samplePresets.find((p) => p.id === selectedPreset);
      if (found) {
        onStartProcessing({
          title: found.title,
          presetText: found.desc,
          duration: found.duration
        });
      }
    }
  };

  const canLaunch = !!selectedFile || isUrlValid || !!selectedPreset;

  return (
    <div className="space-y-8 pb-20 max-w-6xl mx-auto">
      {/* 1. PIPELINE STEP FLOW INDICATOR */}
      <section className="bg-[#151D40] rounded-2xl p-6 border border-[#273154] shadow-md">
        <div className="text-center mb-5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#22D3EE]">
            Multi-Modal Neural Pipeline
          </span>
          <h2 className="text-lg font-bold text-white mt-0.5">
            Automated Video to Sign Language Architecture
          </h2>
        </div>

        {/* Desktop Pipeline Steps (Horizontal) */}
        <div className="hidden lg:grid grid-cols-6 gap-2 items-center">
          {pipelineSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <React.Fragment key={idx}>
                <div className="bg-[#101735] p-3 rounded-xl border border-[#273154] text-center flex flex-col items-center justify-between min-h-[96px] shadow-sm">
                  <div className="w-7 h-7 rounded-lg bg-[#151D40] text-[#22D3EE] flex items-center justify-center mb-1">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="text-[11px] font-extrabold text-white tracking-wide">{step.title}</p>
                    <p className="text-[9px] text-[#A8B2D1]">{step.desc}</p>
                  </div>
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* Mobile / Tablet Step Flow (Vertical List) */}
        <div className="lg:hidden grid grid-cols-2 sm:grid-cols-3 gap-2">
          {pipelineSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div key={idx} className="bg-[#101735] p-2.5 rounded-xl border border-[#273154] flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-[#151D40] text-[#22D3EE] flex items-center justify-center flex-shrink-0">
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-bold text-white truncate">{step.title}</p>
                  <p className="text-[9px] text-[#A8B2D1] truncate">{step.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. MAIN UPLOAD / INPUT PANEL */}
      <section className="bg-[#151D40] rounded-2xl p-6 sm:p-8 border border-[#273154] shadow-xl space-y-6">
        {/* Toggle Mode: Upload vs URL */}
        <div className="flex items-center justify-between border-b border-[#273154] pb-4 flex-wrap gap-3">
          <div className="flex items-center gap-2 bg-[#101735] p-1 rounded-xl border border-[#273154]">
            <button
              onClick={() => setActiveMode('upload')}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 ${
                activeMode === 'upload'
                  ? 'bg-[#151D40] text-white border border-[#273154] shadow-sm'
                  : 'text-[#A8B2D1] hover:text-white'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Video</span>
            </button>

            <button
              onClick={() => setActiveMode('url')}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 ${
                activeMode === 'url'
                  ? 'bg-[#151D40] text-white border border-[#273154] shadow-sm'
                  : 'text-[#A8B2D1] hover:text-white'
              }`}
            >
              <Link2 className="w-3.5 h-3.5" />
              <span>Paste Video URL</span>
            </button>
          </div>

          <span className="text-xs text-[#A8B2D1]">
            Dialect: <span className="text-[#22D3EE] font-bold capitalize">{currentDialect} ISL</span>
          </span>
        </div>

        {/* Active Mode Input Area */}
        {activeMode === 'upload' ? (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-colors bg-[#101735] ${
              isDragOver ? 'border-[#22D3EE] bg-[#151D40]' : 'border-[#273154] hover:border-[#3B4975]'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/webm,video/ogg,video/quicktime,video/avi"
              className="hidden"
              onChange={handleFileInput}
            />

            <div className="w-14 h-14 rounded-2xl bg-[#151D40] border border-[#273154] flex items-center justify-center mx-auto text-[#22D3EE] mb-4">
              <Upload className="w-7 h-7" />
            </div>

            {selectedFile ? (
              <div className="space-y-1">
                <p className="text-base font-bold text-white">{selectedFile.name}</p>
                <p className="text-xs text-[#22D3EE]">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for processing
                </p>
                <p className="text-[11px] text-[#A8B2D1] pt-1">Click to select a different video</p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-base font-bold text-white">Upload Video</p>
                <p className="text-xs text-[#A8B2D1] max-w-sm mx-auto leading-relaxed">
                  Drag and drop your video file here, or click to browse.
                </p>
                <p className="text-[11px] text-[#6B7A99]">Supports MP4, WEBM, MOV, AVI up to 500MB</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4 bg-[#101735] p-6 rounded-2xl border border-[#273154]">
            <label className="block text-xs font-semibold text-[#A8B2D1]">
              Video Stream or Media URL
            </label>
            <div className="relative flex items-center">
              <Link2 className="w-4 h-4 text-[#6B7A99] absolute left-3.5 pointer-events-none" />
              <input
                type="url"
                value={videoUrl}
                onChange={handleUrlChange}
                placeholder="https://example.com/lecture.mp4 or YouTube video link"
                className="w-full bg-[#151D40] text-sm py-3 pl-10 pr-4 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white placeholder-[#6B7A99] outline-none"
              />
            </div>
            <p className="text-xs text-[#6B7A99]">
              Enter a direct video URL or supported streaming link to extract speech and translate to ISL.
            </p>
          </div>
        )}

        {/* 3. SAMPLE DATASET PRESETS */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white">
              Or Choose a Verified Benchmark Sample
            </span>
            <span className="text-[11px] text-[#A8B2D1]">Certified ISL Recordings</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {samplePresets.map((p) => (
              <div
                key={p.id}
                onClick={() => handleSelectPreset(p)}
                className={`p-3.5 rounded-xl border transition-colors cursor-pointer text-left ${
                  selectedPreset === p.id
                    ? 'bg-[#101735] border-[#22D3EE] shadow-sm'
                    : 'bg-[#101735] border-[#273154] hover:border-[#3B4975]'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-semibold text-[#22D3EE] bg-[#151D40] px-2 py-0.5 rounded border border-[#273154]">
                    {p.type}
                  </span>
                  <div className="flex items-center gap-1 text-[10px] text-[#A8B2D1]">
                    <Clock className="w-3 h-3" />
                    <span>{p.duration}s</span>
                  </div>
                </div>

                <p className="text-xs font-bold text-white line-clamp-1">{p.title}</p>
                <p className="text-[10px] text-[#A8B2D1] line-clamp-2 mt-1 leading-relaxed">
                  {p.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Launch Pipeline Action */}
        <div className="pt-4 border-t border-[#273154] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="text-xs text-[#A8B2D1]">
            {selectedFile && <span>Selected: <strong className="text-white">{selectedFile.name}</strong></span>}
            {isUrlValid && <span>Stream URL configured for conversion</span>}
            {selectedPreset && <span>Selected benchmark dataset sample</span>}
            {!canLaunch && <span>Please upload a video, enter a URL, or choose a benchmark sample.</span>}
          </div>

          <GlassButton
            variant="primary"
            size="lg"
            disabled={!canLaunch}
            onClick={handleLaunchPipeline}
            icon={<ArrowRight className="w-4 h-4 text-[#080D24]" />}
            iconPosition="right"
          >
            Start Conversion
          </GlassButton>
        </div>
      </section>
    </div>
  );
};
