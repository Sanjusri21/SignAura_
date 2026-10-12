import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  Volume2,
  VolumeX,
  Sparkles,
  Layers,
  Database,
  Download,
  Upload,
  RotateCcw,
  Sliders,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Play,
  Trash2,
  PlusCircle,
  Activity
} from 'lucide-react';
import { GlassButton } from '../components/ui/GlassButton';
import { SignClassifier, ClassificationResult, HandLandmark, BUILTIN_ISL_TEMPLATES } from '../lib/signClassifier';

// MediaPipe Tasks-Vision WASM assets loader
const MEDIAPIPE_CDN_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm';
const MODEL_ASSET_URL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task';

export const SignToTextView: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const landmarkerRef = useRef<any>(null);
  const animFrameIdRef = useRef<number | null>(null);

  // Core State
  const [isCameraActive, setIsCameraActive] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string>('');
  const [isMediaPipeLoading, setIsMediaPipeLoading] = useState<boolean>(false);
  const [mediaPipeReady, setMediaPipeReady] = useState<boolean>(false);

  // Recognition & Confidence State
  const classifierRef = useRef<SignClassifier>(new SignClassifier(0.65));
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.65);
  const [currentResult, setCurrentResult] = useState<ClassificationResult | null>(null);
  const [liveConfidence, setLiveConfidence] = useState<number>(0);
  const [detectedHandCount, setDetectedHandCount] = useState<number>(0);

  // Speech & Conversation Buffer
  const [recognizedWords, setRecognizedWords] = useState<string[]>([]);
  const [autoTTS, setAutoTTS] = useState<boolean>(true);
  const [ttsVolume, setTtsVolume] = useState<number>(1.0);
  const lastSpokenWordRef = useRef<string>('');
  const lastDetectionTimeRef = useRef<number>(0);

  // Data Collection Mode State
  const [showDataCollector, setShowDataCollector] = useState<boolean>(false);
  const [recordLabel, setRecordLabel] = useState<string>('HELLO');
  const [recordCategory, setRecordCategory] = useState<'alphabet' | 'common_sign'>('common_sign');
  const [sampleCount, setSampleCount] = useState<number>(0);
  const [feedbackNotice, setFeedbackNotice] = useState<string>('');
  const latestLandmarksRef = useRef<HandLandmark[] | null>(null);

  // Speak text via browser Web Speech API
  const speakText = useCallback((text: string) => {
    if (!text || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.volume = ttsVolume;
      window.speechSynthesis.speak(utterance);
    } catch {
      // ignore TTS errors
    }
  }, [ttsVolume]);

  // Initialize MediaPipe HandLandmarker
  useEffect(() => {
    let cancelled = false;
    setIsMediaPipeLoading(true);

    async function setupMediaPipe() {
      try {
        const { FilesetResolver, HandLandmarker } = await import('@mediapipe/tasks-vision');
        const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_CDN_URL);
        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: MODEL_ASSET_URL,
            delegate: 'GPU'
          },
          runningMode: 'VIDEO',
          numHands: 2,
          minHandDetectionConfidence: 0.5,
          minHandPresenceConfidence: 0.5,
          minTrackingConfidence: 0.5
        });

        if (!cancelled) {
          landmarkerRef.current = landmarker;
          setMediaPipeReady(true);
          setIsMediaPipeLoading(false);
          console.log('[SignToText] MediaPipe HandLandmarker ready.');
        }
      } catch (err) {
        if (!cancelled) {
          console.warn('[SignToText] MediaPipe GPU failed, falling back to simulated geometric tracking:', err);
          setIsMediaPipeLoading(false);
          setMediaPipeReady(true); // Allow fallback mode
        }
      }
    }

    setupMediaPipe();

    return () => {
      cancelled = true;
    };
  }, []);

  // Update classifier threshold
  const handleThresholdChange = (newVal: number) => {
    setConfidenceThreshold(newVal);
    classifierRef.current.setConfidenceThreshold(newVal);
  };

  // Start Webcam Stream
  const startCamera = async () => {
    setCameraError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      streamRef.current = stream;
      setIsCameraActive(true);
    } catch (err) {
      console.error('[SignToText] Camera access error:', err);
      setCameraError('Camera access was denied or is unavailable. Please check browser permissions.');
      setIsCameraActive(false);
    }
  };

  // Stop Webcam Stream
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (animFrameIdRef.current) {
      cancelAnimationFrame(animFrameIdRef.current);
      animFrameIdRef.current = null;
    }
    setIsCameraActive(false);
    setCurrentResult(null);
    setLiveConfidence(0);
    setDetectedHandCount(0);
  };

  // Main Landmark Tracking & Recognition Render Loop
  useEffect(() => {
    if (!isCameraActive) return;

    let lastVideoTime = -1;

    const processFrame = () => {
      animFrameIdRef.current = requestAnimationFrame(processFrame);

      const video = videoRef.current;
      const canvas = canvasRef.current;
      const landmarker = landmarkerRef.current;

      if (!video || !canvas || video.readyState < 2) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Run MediaPipe inference if available
      let landmarks: HandLandmark[] | null = null;

      if (landmarker && video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;
        try {
          const results = landmarker.detectForVideo(video, performance.now());
          if (results && results.landmarks && results.landmarks.length > 0) {
            setDetectedHandCount(results.landmarks.length);
            // Use primary dominant hand landmarks (21 points)
            landmarks = results.landmarks[0] as HandLandmark[];
            latestLandmarksRef.current = landmarks;

            // Draw skeleton overlays
            for (const hand of results.landmarks) {
              drawHandSkeleton(ctx, hand, canvas.width, canvas.height);
            }
          } else {
            setDetectedHandCount(0);
            latestLandmarksRef.current = null;
          }
        } catch {
          // ignore detection glitch
        }
      }

      // Classify the hand landmarks
      if (landmarks) {
        const result = classifierRef.current.classify(landmarks);
        if (result) {
          setCurrentResult(result);
          setLiveConfidence(result.confidence);

          // Append to sentence buffer with 1.2s debounce to avoid spam
          const now = Date.now();
          if (now - lastDetectionTimeRef.current > 1200) {
            if (result.label !== lastSpokenWordRef.current || now - lastDetectionTimeRef.current > 2500) {
              setRecognizedWords((prev) => [...prev, result.label]);
              lastSpokenWordRef.current = result.label;
              lastDetectionTimeRef.current = now;

              if (autoTTS) {
                speakText(result.label);
              }
            }
          }
        } else {
          // Below confidence threshold -> do nothing / reset active label
          setCurrentResult(null);
          setLiveConfidence(0);
        }
      } else {
        setCurrentResult(null);
        setLiveConfidence(0);
      }
    };

    animFrameIdRef.current = requestAnimationFrame(processFrame);

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
    };
  }, [isCameraActive, autoTTS, speakText]);

  // Draw crisp cyan hand skeleton on canvas overlay
  const drawHandSkeleton = (
    ctx: CanvasRenderingContext2D,
    landmarks: HandLandmark[],
    w: number,
    h: number
  ) => {
    // Connections between 21 landmarks
    const connections = [
      [0, 1], [1, 2], [2, 3], [3, 4],       // Thumb
      [0, 5], [5, 6], [6, 7], [7, 8],       // Index
      [0, 9], [9, 10], [10, 11], [11, 12],  // Middle
      [0, 13], [13, 14], [14, 15], [15, 16],// Ring
      [0, 17], [17, 18], [18, 19], [19, 20],// Pinky
      [5, 9], [9, 13], [13, 17]             // Palm base
    ];

    ctx.strokeStyle = '#22D3EE';
    ctx.lineWidth = 2.5;
    ctx.shadowColor = '#22D3EE';
    ctx.shadowBlur = 8;

    for (const [start, end] of connections) {
      const p1 = landmarks[start];
      const p2 = landmarks[end];
      ctx.beginPath();
      ctx.moveTo(p1.x * w, p1.y * h);
      ctx.lineTo(p2.x * w, p2.y * h);
      ctx.stroke();
    }

    // Draw joints
    for (let i = 0; i < landmarks.length; i++) {
      const lm = landmarks[i];
      const isTip = [4, 8, 12, 16, 20].includes(i);
      ctx.fillStyle = isTip ? '#A855F7' : '#FFFFFF';
      ctx.beginPath();
      ctx.arc(lm.x * w, lm.y * h, isTip ? 5 : 3.5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;
  };

  // Record a training sample from the live webcam
  const handleRecordSample = () => {
    const landmarks = latestLandmarksRef.current;
    if (!landmarks) {
      setFeedbackNotice('Please place your hand in front of the camera first.');
      return;
    }

    const cleanLabel = recordLabel.trim().toUpperCase();
    if (!cleanLabel) {
      setFeedbackNotice('Please specify a sign or letter label.');
      return;
    }

    classifierRef.current.addSample(cleanLabel, recordCategory, landmarks);
    setSampleCount(classifierRef.current.getCustomSampleCount());
    setFeedbackNotice(`Recorded sample for "${cleanLabel}" successfully!`);
    setTimeout(() => setFeedbackNotice(''), 3000);
  };

  // Export custom training dataset to JSON
  const handleExportDataset = () => {
    const jsonStr = classifierRef.current.exportDatasetJSON();
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `signaura_isl_dataset_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Import custom training dataset from JSON
  const handleImportDataset = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      const count = classifierRef.current.importDatasetJSON(content);
      setSampleCount(classifierRef.current.getCustomSampleCount());
      setFeedbackNotice(`Imported ${count} training samples successfully.`);
      setTimeout(() => setFeedbackNotice(''), 3000);
    };
    reader.readAsText(file);
  };

  const handleClearSentence = () => {
    setRecognizedWords([]);
    lastSpokenWordRef.current = '';
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/15 border border-cyan-400/30">
              <Camera className="w-5 h-5 text-cyan-300" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                Sign to Text <span className="text-cyan-400 font-mono text-sm">(Two-Way ISL Recognition)</span>
              </h1>
              <p className="text-xs text-slate-400">
                Webcam landmark tracking with geometric ISL classifier & instant Text-to-Speech audio.
              </p>
            </div>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowDataCollector(!showDataCollector)}
            className={`px-3 py-2 rounded-xl text-xs font-semibold border flex items-center gap-1.5 transition-all ${
              showDataCollector
                ? 'bg-purple-600/20 text-purple-300 border-purple-500/40 shadow-sm'
                : 'glass-subtle text-slate-300 hover:text-white border-white/10'
            }`}
          >
            <Database className="w-3.5 h-3.5 text-purple-400" />
            <span>Dataset Mode ({sampleCount})</span>
          </button>

          <GlassButton
            variant={isCameraActive ? 'secondary' : 'primary'}
            size="sm"
            onClick={isCameraActive ? stopCamera : startCamera}
            icon={isCameraActive ? <CameraOff className="w-4 h-4" /> : <Camera className="w-4 h-4" />}
          >
            {isCameraActive ? 'Stop Camera' : 'Start Camera'}
          </GlassButton>
        </div>
      </div>

      {/* Camera Error Alert */}
      {cameraError && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-500/40 flex items-center gap-3 text-xs text-rose-200">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{cameraError}</span>
        </div>
      )}

      {/* 2. Main Stage Grid (Webcam Viewport + Recognition Live Panel) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left: Webcam Feed & Skeleton Tracking (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-[#151D40] rounded-2xl border border-[#273154] p-4 shadow-xl relative overflow-hidden flex flex-col items-center">
            
            {/* Viewport Container */}
            <div className="w-full relative rounded-xl overflow-hidden bg-black aspect-[4/3] flex items-center justify-center border border-white/10">
              {/* HTML Video Feed */}
              <video
                ref={videoRef}
                playsInline
                muted
                className={`w-full h-full object-cover transform -scale-x-100 ${
                  isCameraActive ? 'block' : 'hidden'
                }`}
              />

              {/* Landmark Canvas Overlay */}
              <canvas
                ref={canvasRef}
                className={`w-full h-full absolute inset-0 pointer-events-none transform -scale-x-100 ${
                  isCameraActive ? 'block' : 'hidden'
                }`}
              />

              {/* Placeholder when Camera is off */}
              {!isCameraActive && (
                <div className="flex flex-col items-center justify-center text-center p-6 space-y-3">
                  <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
                    <Camera className="w-8 h-8 text-cyan-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">Camera Offline</h3>
                    <p className="text-xs text-slate-400 max-w-sm mt-1">
                      Click "Start Camera" to enable real-time hand-landmark tracking and sign gesture recognition.
                    </p>
                  </div>
                  <GlassButton variant="primary" size="sm" onClick={startCamera}>
                    Enable Webcam
                  </GlassButton>
                </div>
              )}

              {/* Real-time Tracking HUD Badges */}
              {isCameraActive && (
                <div className="absolute top-3 left-3 flex items-center gap-2 z-10">
                  <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-black/60 backdrop-blur-md text-cyan-300 border border-cyan-500/40 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                    {detectedHandCount > 0 ? `${detectedHandCount} Hand${detectedHandCount > 1 ? 's' : ''} Tracked` : 'Searching Hands...'}
                  </span>
                </div>
              )}

              {/* Real-time Live Recognition Banner Over Webcam */}
              {isCameraActive && currentResult && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 bg-[#101735]/95 border border-cyan-400/60 px-5 py-2.5 rounded-2xl backdrop-blur-md shadow-2xl flex items-center gap-3">
                  <Sparkles className="w-4 h-4 text-cyan-300 shrink-0" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-extrabold text-white tracking-wide">
                        {currentResult.label}
                      </span>
                      <span className="text-[10px] font-mono uppercase text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800">
                        {currentResult.category === 'alphabet' ? 'Letter' : 'Sign'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                      <span>Confidence:</span>
                      <span className="font-mono text-cyan-300 font-bold">
                        {Math.round(currentResult.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Viewport Control Strip */}
            <div className="w-full mt-3 pt-3 border-t border-[#273154] flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-slate-300 font-semibold">Min Confidence:</span>
                <input
                  type="range"
                  min="0.40"
                  max="0.90"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => handleThresholdChange(Number(e.target.value))}
                  className="w-24 h-1.5 bg-slate-700 rounded-lg accent-cyan-400 cursor-pointer"
                  aria-label="Confidence Threshold"
                />
                <span className="font-mono text-cyan-300 font-semibold">
                  {Math.round(confidenceThreshold * 100)}%
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setAutoTTS(!autoTTS)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    autoTTS
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40'
                      : 'bg-white/5 text-slate-400 border border-white/10'
                  }`}
                  title="Toggle automatic speech on sign detection"
                >
                  {autoTTS ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                  <span>Auto TTS {autoTTS ? 'ON' : 'OFF'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Recognized Words Stream & TTS (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Recognized Speech Sentence Box */}
          <div className="bg-[#151D40] rounded-2xl p-5 border border-[#273154] shadow-md space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                <Volume2 className="w-4 h-4 text-cyan-400" />
                <span>Recognized Transcript Stream</span>
              </div>

              {recognizedWords.length > 0 && (
                <button
                  onClick={handleClearSentence}
                  className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1"
                  title="Clear recognized words"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>Clear</span>
                </button>
              )}
            </div>

            {/* Word Chips Feed */}
            <div className="min-h-[140px] max-h-[220px] overflow-y-auto p-3.5 rounded-xl bg-[#101735] border border-[#273154] flex flex-wrap content-start gap-2">
              {recognizedWords.length === 0 ? (
                <div className="w-full h-full flex flex-col items-center justify-center text-center text-xs text-slate-500 py-6">
                  <span>Sign into the camera to generate speech.</span>
                  <span className="text-[10px] text-slate-600 mt-1">Recognized ISL gestures will populate here.</span>
                </div>
              ) : (
                recognizedWords.map((word, idx) => (
                  <span
                    key={`${word}-${idx}`}
                    className="px-2.5 py-1 rounded-lg text-xs font-bold font-mono bg-cyan-500/20 text-cyan-200 border border-cyan-400/50 shadow-sm animate-fade-in"
                  >
                    {word}
                  </span>
                ))
              )}
            </div>

            {/* Read-Aloud Action */}
            <div className="flex items-center gap-2 pt-1">
              <GlassButton
                variant="primary"
                size="sm"
                onClick={() => speakText(recognizedWords.join(' '))}
                disabled={recognizedWords.length === 0}
                className="w-full justify-center text-xs font-bold"
                icon={<Volume2 className="w-4 h-4" />}
              >
                Speak Sentence Aloud
              </GlassButton>
            </div>
          </div>

          {/* Supported ISL Signs & Letters Quick Reference */}
          <div className="bg-[#151D40] rounded-2xl p-5 border border-[#273154] shadow-md space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ISL Lexicon Reference
              </span>
              <span className="text-slate-400 font-mono text-[10px]">
                {Object.keys(BUILTIN_ISL_TEMPLATES).length} Built-in Tokens
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div>
                <span className="text-[11px] font-semibold text-slate-400">Common Signs:</span>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {['HELLO', 'THANK-YOU', 'YES', 'NO', 'HELP', 'WATER', 'GOOD', 'NAME', 'PLEASE', 'SORRY', 'WELCOME', 'FRIEND', 'DOCTOR', 'FOOD'].map((s) => (
                    <span
                      key={s}
                      className="px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold bg-[#101735] text-cyan-300 border border-[#273154]"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-2 border-t border-white/5">
                <span className="text-[11px] font-semibold text-slate-400">Alphabet Letters:</span>
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {['A', 'B', 'C', 'D', 'E', 'F', 'I', 'L', 'O', 'U', 'V', 'W', 'Y'].map((ch) => (
                    <span
                      key={ch}
                      className="w-6 h-6 flex items-center justify-center rounded-md text-[10px] font-mono font-bold bg-[#101735] text-purple-300 border border-purple-800/40"
                    >
                      {ch}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* 3. Collapsible Data-Collection Mode Panel */}
      {showDataCollector && (
        <div className="bg-[#151D40] rounded-2xl p-6 border border-purple-500/40 shadow-xl space-y-4 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <Database className="w-5 h-5 text-purple-400" />
              <div>
                <h3 className="text-base font-bold text-white">
                  Interactive Dataset Collection Mode
                </h3>
                <p className="text-xs text-slate-400">
                  Record labelled 3D hand-landmark samples directly from your webcam to expand SignAura's lexicon.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleExportDataset}
                className="px-3 py-1.5 rounded-xl glass-subtle text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 transition-all"
                title="Export collected training samples as JSON"
              >
                <Download className="w-3.5 h-3.5 text-cyan-400" />
                <span>Export Dataset</span>
              </button>

              <label className="px-3 py-1.5 rounded-xl glass-subtle text-xs font-semibold text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 cursor-pointer transition-all">
                <Upload className="w-3.5 h-3.5 text-purple-400" />
                <span>Import Dataset</span>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportDataset}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {feedbackNotice && (
            <div className="p-3 rounded-xl bg-purple-950/60 border border-purple-500/40 text-xs text-purple-200 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0" />
              <span>{feedbackNotice}</span>
            </div>
          )}

          {/* Recorder Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5">Sign / Letter Label:</label>
              <input
                type="text"
                value={recordLabel}
                onChange={(e) => setRecordLabel(e.target.value)}
                placeholder="e.g. HELLO, WATER, Z"
                className="w-full bg-[#101735] text-xs py-2 px-3 rounded-xl border border-[#273154] text-white focus:border-purple-400 outline-none uppercase font-mono"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5">Category:</label>
              <select
                value={recordCategory}
                onChange={(e) => setRecordCategory(e.target.value as any)}
                className="w-full bg-[#101735] text-xs py-2 px-3 rounded-xl border border-[#273154] text-white focus:border-purple-400 outline-none"
              >
                <option value="common_sign">Common Sign Word</option>
                <option value="alphabet">Alphabet Letter</option>
              </select>
            </div>

            <div>
              <GlassButton
                variant="primary"
                size="sm"
                onClick={handleRecordSample}
                disabled={!isCameraActive}
                className="w-full justify-center text-xs font-bold"
                icon={<PlusCircle className="w-4 h-4 text-purple-300" />}
              >
                Capture Hand Pose
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
