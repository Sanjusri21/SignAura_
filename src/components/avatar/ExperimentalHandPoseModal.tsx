import React, { useState, useMemo } from 'react';
import {
  AlertTriangle,
  RotateCcw,
  X,
  Info,
  Layers,
  Cpu,
  ShieldAlert,
  Sliders,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { GlassButton } from '../ui/GlassButton';
import { ProceduralHandViewer } from './ProceduralHandViewer';
import {
  PoseCategory,
  ExperimentalHandPoseEntry,
  getPosesByCategory,
  getNeutralHandPose,
  ProceduralHandPoseData,
} from '../../lib/experimentalHandPoseRegistry';

export interface ExperimentalHandPoseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExperimentalHandPoseModal: React.FC<ExperimentalHandPoseModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<PoseCategory>('alphabet');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('A');
  const [isNeutralActive, setIsNeutralActive] = useState<boolean>(false);

  // Available poses for the currently selected category
  const categoryPoses = useMemo(() => {
    return getPosesByCategory(selectedCategory);
  }, [selectedCategory]);

  // Current active entry
  const activeEntry: ExperimentalHandPoseEntry | undefined = useMemo(() => {
    return categoryPoses.find((p) => p.symbol === selectedSymbol) || categoryPoses[0];
  }, [categoryPoses, selectedSymbol]);

  // Hand pose data to pass to viewer
  const displayedPoseData: ProceduralHandPoseData | null = useMemo(() => {
    if (isNeutralActive) {
      return getNeutralHandPose();
    }
    if (activeEntry?.status === 'unavailable' || !activeEntry?.poseData) {
      return null;
    }
    return activeEntry.poseData;
  }, [isNeutralActive, activeEntry]);

  if (!isOpen) return null;

  const handleCategorySwitch = (cat: PoseCategory) => {
    setSelectedCategory(cat);
    setSelectedSymbol(cat === 'alphabet' ? 'A' : '0');
    setIsNeutralActive(false);
  };

  const handleSymbolSelect = (sym: string) => {
    setSelectedSymbol(sym);
    setIsNeutralActive(false);
  };

  const handleResetToNeutral = () => {
    setIsNeutralActive(true);
  };

  const isUnavailable = !isNeutralActive && activeEntry?.status === 'unavailable';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="experimental-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md overflow-y-auto"
    >
      <div className="relative w-full max-w-5xl bg-[#0D1433] border border-[#273154] rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[94vh]">

        {/* MANDATORY SAFEGUARD BANNER */}
        <div className="bg-amber-950/80 border-b border-amber-500/30 px-5 py-3 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="font-extrabold uppercase tracking-wider text-amber-300">
              EXPERIMENTAL — NOT VALIDATED ISL
            </span>
            <p className="text-amber-200/90 text-[11px] leading-relaxed mt-0.5">
              Procedural hand poses are for visualization and engineering evaluation. They have not been verified
              as Indian Sign Language signs. Do not use this prototype as a language-learning or communication reference.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close prototype viewer"
            className="ml-auto text-amber-300/70 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-[#273154] flex flex-wrap items-center justify-between gap-4 bg-[#101735]">
          <div>
            <h2 id="experimental-modal-title" className="text-base font-bold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#38BDF8]" />
              <span>Procedural Hand-Pose Feasibility Prototype</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                A–Z & 0–9
              </span>
            </h2>
            <p className="text-xs text-[#A8B2D1] mt-0.5">
              Isolated Three.js articulated joint kinematics viewer (15-DOF procedural hand).
            </p>
          </div>

          {/* Category Selector Tabs */}
          <div className="flex items-center gap-1.5 p-1 bg-[#0A1026] rounded-xl border border-[#273154]">
            <button
              onClick={() => handleCategorySwitch('alphabet')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                selectedCategory === 'alphabet'
                  ? 'bg-[#38BDF8] text-[#080D24] shadow-sm'
                  : 'text-[#A8B2D1] hover:text-white'
              }`}
            >
              Alphabet (A–Z)
            </button>
            <button
              onClick={() => handleCategorySwitch('digit')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                selectedCategory === 'digit'
                  ? 'bg-[#38BDF8] text-[#080D24] shadow-sm'
                  : 'text-[#A8B2D1] hover:text-white'
              }`}
            >
              Digits (0–9)
            </button>
          </div>
        </div>

        {/* Modal Body: Left Canvas, Right Controls & Diagnostics */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-5 p-5">

          {/* 3D Hand Canvas Column (7 cols) */}
          <div className="lg:col-span-7 flex flex-col space-y-3">
            <div className="relative flex-1 min-h-[380px] rounded-2xl overflow-hidden border border-[#273154] shadow-inner bg-[#080D24]">
              <ProceduralHandViewer
                poseData={displayedPoseData}
                isUnavailable={isUnavailable}
                unavailableReason={activeEntry?.validationNotes}
              />
            </div>

            {/* Viewport Action Bar */}
            <div className="flex items-center justify-between text-xs px-2">
              <div className="flex items-center gap-2">
                <span className="text-[#A8B2D1]">Current Mode:</span>
                {isNeutralActive ? (
                  <span className="font-semibold text-cyan-300">Neutral Rest Pose</span>
                ) : (
                  <span className="font-semibold text-white">
                    {selectedCategory === 'alphabet' ? `Letter ${activeEntry?.symbol}` : `Digit ${activeEntry?.symbol}`}
                  </span>
                )}
              </div>

              <GlassButton
                variant="secondary"
                size="sm"
                onClick={handleResetToNeutral}
                className="text-xs gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
                <span>Reset to Neutral</span>
              </GlassButton>
            </div>
          </div>

          {/* Right Controls & Inspector Column (5 cols) */}
          <div className="lg:col-span-5 flex flex-col space-y-4">

            {/* Symbol Grid Selector */}
            <div className="bg-[#101735] p-4 rounded-2xl border border-[#273154] space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-white uppercase tracking-wider">
                  Select {selectedCategory === 'alphabet' ? 'Letter' : 'Numeral'}
                </span>
                <span className="text-[11px] text-[#A8B2D1]">
                  {categoryPoses.filter((p) => p.status === 'experimental').length} Experimental / {categoryPoses.length} Total
                </span>
              </div>

              <div className={`grid ${selectedCategory === 'alphabet' ? 'grid-cols-7 sm:grid-cols-9' : 'grid-cols-5'} gap-1.5 max-h-[160px] overflow-y-auto p-1`}>
                {categoryPoses.map((entry) => {
                  const isSelected = !isNeutralActive && entry.symbol === selectedSymbol;
                  const isUnavail = entry.status === 'unavailable';

                  return (
                    <button
                      key={entry.id}
                      onClick={() => handleSymbolSelect(entry.symbol)}
                      aria-label={`${entry.category} ${entry.symbol} (${entry.status})`}
                      className={`relative py-1.5 px-2 rounded-lg text-xs font-bold transition-all text-center border ${
                        isSelected
                          ? 'bg-[#38BDF8] text-[#080D24] border-[#38BDF8] shadow-md scale-105'
                          : isUnavail
                          ? 'bg-[#151D40]/60 text-slate-400 border-dashed border-[#273154] hover:border-slate-500'
                          : 'bg-[#151D40] text-slate-200 border-[#273154] hover:border-[#38BDF8] hover:text-white'
                      }`}
                    >
                      {entry.symbol}
                      {/* Sub-dot indicator for availability */}
                      <span
                        className={`absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full ${
                          entry.status === 'experimental'
                            ? 'bg-amber-400'
                            : entry.status === 'expert-validated'
                            ? 'bg-emerald-400'
                            : 'bg-zinc-600'
                        }`}
                      />
                    </button>
                  );
                })}
              </div>

              {/* Status Legend */}
              <div className="flex items-center gap-3 text-[10px] text-[#A8B2D1] pt-1 border-t border-[#273154]">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  <span>Experimental Pose</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-zinc-600" />
                  <span>Unavailable</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>Expert-Validated (0)</span>
                </div>
              </div>
            </div>

            {/* Diagnostic Details Panel */}
            <div className="bg-[#101735] p-4 rounded-2xl border border-[#273154] space-y-3 flex-1">
              <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                <Sliders className="w-3.5 h-3.5 text-[#38BDF8]" />
                <span>Pose Metadata & Diagnostics</span>
              </div>

              {activeEntry && (
                <div className="space-y-2 text-xs">
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="bg-[#151D40] p-2 rounded-xl border border-[#273154]">
                      <span className="text-slate-400 block text-[10px]">Pose ID</span>
                      <span className="font-mono text-cyan-300 font-semibold">{activeEntry.id}</span>
                    </div>

                    <div className="bg-[#151D40] p-2 rounded-xl border border-[#273154]">
                      <span className="text-slate-400 block text-[10px]">Verification Status</span>
                      <span
                        className={`font-semibold inline-flex items-center gap-1 ${
                          activeEntry.status === 'experimental'
                            ? 'text-amber-400'
                            : activeEntry.status === 'expert-validated'
                            ? 'text-emerald-400'
                            : 'text-zinc-400'
                        }`}
                      >
                        {activeEntry.status === 'experimental' && <AlertTriangle className="w-3 h-3" />}
                        {activeEntry.status === 'unavailable' && <XCircle className="w-3 h-3" />}
                        <span className="uppercase text-[10px]">{activeEntry.status}</span>
                      </span>
                    </div>
                  </div>

                  {/* Provenance and notes */}
                  <div className="bg-[#151D40] p-2.5 rounded-xl border border-[#273154] space-y-1">
                    <span className="text-[10px] text-slate-400 font-semibold block uppercase">Source Description</span>
                    <p className="text-[11px] text-slate-200 leading-relaxed">
                      {activeEntry.sourceDescription}
                    </p>
                  </div>

                  <div className="bg-[#151D40] p-2.5 rounded-xl border border-[#273154] space-y-1">
                    <span className="text-[10px] text-slate-400 font-semibold block uppercase">Linguistic Limitations</span>
                    <p className="text-[11px] text-amber-200/90 leading-relaxed">
                      {activeEntry.validationNotes}
                    </p>
                  </div>

                  {/* Joint transforms telemetry */}
                  {activeEntry.poseData && (
                    <div className="bg-[#151D40] p-2.5 rounded-xl border border-[#273154] space-y-1">
                      <span className="text-[10px] text-slate-400 font-semibold block uppercase">Flexion Telemetry (rad)</span>
                      <div className="grid grid-cols-5 gap-1 text-[10px] font-mono text-center pt-0.5">
                        <div className="p-1 bg-[#0A1026] rounded">
                          <span className="text-slate-400 block text-[8px]">THUMB</span>
                          {activeEntry.poseData.thumb.mcpFlexion.toFixed(2)}
                        </div>
                        <div className="p-1 bg-[#0A1026] rounded">
                          <span className="text-slate-400 block text-[8px]">INDEX</span>
                          {activeEntry.poseData.index.mcpFlexion.toFixed(2)}
                        </div>
                        <div className="p-1 bg-[#0A1026] rounded">
                          <span className="text-slate-400 block text-[8px]">MID</span>
                          {activeEntry.poseData.middle.mcpFlexion.toFixed(2)}
                        </div>
                        <div className="p-1 bg-[#0A1026] rounded">
                          <span className="text-slate-400 block text-[8px]">RING</span>
                          {activeEntry.poseData.ring.mcpFlexion.toFixed(2)}
                        </div>
                        <div className="p-1 bg-[#0A1026] rounded">
                          <span className="text-slate-400 block text-[8px]">PINKY</span>
                          {activeEntry.poseData.pinky.mcpFlexion.toFixed(2)}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-[#273154] flex items-center justify-between bg-[#101735] text-xs">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>Isolated from production translation pipeline. No SMPL-X cache or sequences are altered.</span>
          </div>

          <GlassButton
            variant="secondary"
            size="sm"
            onClick={onClose}
            className="text-xs"
          >
            Close Viewer
          </GlassButton>
        </div>

      </div>
    </div>
  );
};
