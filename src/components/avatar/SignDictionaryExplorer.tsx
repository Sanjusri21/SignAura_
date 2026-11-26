import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  BookOpen,
  Play,
  RotateCw,
  Hand,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Filter,
  Folder
} from 'lucide-react';
import { GlassButton } from '../ui/GlassButton';

interface SignRecord {
  sample_key: string;
  gloss: string;
  normalized_gloss: string;
  shard: string;
  frame_count: number;
  fps: number;
  has_left_hand: number;
  has_right_hand: number;
  hand_category: string;
  smplx_cache_path?: string | null;
  conversion_status?: string;
  animation_url?: string;
}

interface SignDictionaryExplorerProps {
  onSelectSign: (gloss: string, motionUrl: string, sign: SignRecord) => void;
  currentSignName?: string;
}

const BACKEND_API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8002';
const SIGNAVATAR_API = 'http://127.0.0.1:8001';

const DATASET_TABS = [
  { id: 'all', label: 'All Datasets', match: '' },
  { id: 'isl_dictionary', label: 'ISL Dictionary', match: 'ISL Dictionary' },
  { id: 'cislr', label: 'CISLR', match: 'CISLR' },
  { id: 'drive_a', label: 'Drive Group A', match: 'Drive Group A' },
  { id: 'drive_b', label: 'Drive Group B', match: 'Drive Group B' },
  { id: 'drive_c', label: 'Drive Group C', match: 'Drive Group C' },
  { id: 'drive_d', label: 'Drive Group D', match: 'Drive Group D' },
  { id: 'drive_e', label: 'Drive Group E', match: 'Drive Group E' },
  { id: 'drive_f', label: 'Drive Group F', match: 'Drive Group F' },
  { id: 'drive_g', label: 'Drive Group G', match: 'Drive Group G' },
  { id: 'drive_h', label: 'Drive Group H', match: 'Drive Group H' },
  { id: 'drive_i', label: 'Drive Group I', match: 'Drive Group I' },
  { id: 'drive_j', label: 'Drive Group J', match: 'Drive Group J' },
  { id: 'drive_k', label: 'Drive Group K', match: 'Drive Group K' },
  { id: 'drive_l', label: 'Drive Group L', match: 'Drive Group L' },
  { id: 'drive_m', label: 'Drive Group M', match: 'Drive Group M' },
  { id: 'drive_n', label: 'Drive Group N', match: 'Drive Group N' },
  { id: 'part1', label: 'Part 1', match: 'Part 1' },
  { id: 'part2', label: 'Part 2', match: 'Part 2' },
  { id: 'part3', label: 'Part 3', match: 'Part 3' },
  { id: 'include', label: 'INCLUDE', match: 'INCLUDE' },
  { id: 'sign15', label: 'Sign 15', match: 'Sign 15' },
  { id: 'isl50', label: 'ISL 50', match: 'ISL 50' },
  { id: 'archive5', label: 'Archive 5', match: 'Archive 5' },
];

const shortShard = (shard?: string) => {
  if (!shard) return '';
  if (shard.includes('ISL Dictionary')) return 'ISL Dict';
  if (shard.includes('CISLR')) return 'CISLR';
  if (shard.includes('Group A')) return 'Drive A';
  if (shard.includes('Group B')) return 'Drive B';
  if (shard.includes('Group C')) return 'Drive C';
  if (shard.includes('Group D')) return 'Drive D';
  if (shard.includes('Group E')) return 'Drive E';
  if (shard.includes('Group F')) return 'Drive F';
  if (shard.includes('Group G')) return 'Drive G';
  if (shard.includes('Group H')) return 'Drive H';
  if (shard.includes('Group I')) return 'Drive I';
  if (shard.includes('Group J')) return 'Drive J';
  if (shard.includes('Group K')) return 'Drive K';
  if (shard.includes('Group L')) return 'Drive L';
  if (shard.includes('Group M')) return 'Drive M';
  if (shard.includes('Group N')) return 'Drive N';
  if (shard.includes('Part 1')) return 'Part 1';
  if (shard.includes('Part 2')) return 'Part 2';
  if (shard.includes('Part 3')) return 'Part 3';
  if (shard.includes('INCLUDE')) return 'INCLUDE';
  if (shard.includes('Sign 15')) return 'Sign 15';
  if (shard.includes('50')) return 'ISL 50';
  if (shard.includes('archive5') || shard.includes('Archive 5')) return 'Arch 5';
  return shard.split(' ')[0];
};

export const SignDictionaryExplorer: React.FC<SignDictionaryExplorerProps> = ({
  onSelectSign,
  currentSignName
}) => {
  const [signs, setSigns] = useState<SignRecord[]>([]);
  const [totalSigns, setTotalSigns] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(18);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [handFilter, setHandFilter] = useState<string>('');
  const [selectedDataset, setSelectedDataset] = useState<string>('all');
  const [datasetCounts, setDatasetCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [convertingKey, setConvertingKey] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');

  const fetchSigns = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('page', currentPage.toString());
      params.set('page_size', pageSize.toString());
      if (searchQuery.trim()) {
        params.set('search', searchQuery.trim());
      }
      if (handFilter) {
        params.set('hand_filter', handFilter);
      }
      if (selectedDataset && selectedDataset !== 'all') {
        const tab = DATASET_TABS.find((t) => t.id === selectedDataset);
        if (tab?.match) {
          params.set('dataset', tab.match);
        }
      }

      const res = await fetch(`${BACKEND_API}/api/signavatar/motions?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setSigns(data.signs || data.motions || []);
        setTotalSigns(data.total || data.count || 0);
        setTotalPages(data.total_pages || Math.ceil((data.total || 0) / pageSize) || 1);
        if (data.by_shard) {
          setDatasetCounts(data.by_shard);
        }
      }
    } catch (err) {
      console.warn('Error fetching sign dictionary:', err);
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, searchQuery, handFilter, selectedDataset]);

  useEffect(() => {
    fetchSigns();
  }, [fetchSigns]);

  const getDatasetCount = (matchStr: string) => {
    if (!matchStr) return 0;
    let sum = 0;
    for (const [k, v] of Object.entries(datasetCounts)) {
      if (k.toLowerCase().includes(matchStr.toLowerCase())) {
        sum += v;
      }
    }
    return sum;
  };

  const allDatasetsCount =
    Object.values(datasetCounts).reduce((a, b) => a + b, 0) || (selectedDataset === 'all' ? totalSigns : 8218);

  const handlePlaySign = async (sign: SignRecord) => {
    setConvertingKey(sign.sample_key);
    setStatusMessage(`Loading sign "${sign.gloss}"...`);

    const glossTarget = sign.normalized_gloss || sign.gloss;
    const motionUrl = `${SIGNAVATAR_API}/motion/${encodeURIComponent(glossTarget)}`;

    try {
      // Test motion availability / trigger lazy retargeting
      const checkRes = await fetch(motionUrl, { method: 'HEAD' });
      if (checkRes.ok || checkRes.status === 200) {
        onSelectSign(sign.gloss, motionUrl, sign);
        setStatusMessage(`Playing "${sign.gloss}"`);
      } else {
        // Fallback: pass motionUrl anyway, SignAvatar3D handles streaming
        onSelectSign(sign.gloss, motionUrl, sign);
      }
    } catch (e) {
      // Still attempt streaming
      onSelectSign(sign.gloss, motionUrl, sign);
    } finally {
      setConvertingKey(null);
      setTimeout(() => setStatusMessage(''), 3000);
    }
  };

  return (
    <div className="bg-[#151D40] rounded-2xl border border-[#273154] p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#273154] pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-[#22D3EE]/10 border border-[#22D3EE]/30 text-[#22D3EE]">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">SignAura Master ISL Dictionary</h2>
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#101735] text-[#22D3EE] border border-[#273154] font-mono">
                {allDatasetsCount > 0 ? `${allDatasetsCount.toLocaleString()} signs` : 'Loading...'}
              </span>
            </div>
            <p className="text-xs text-[#A8B2D1]">
              Comprehensive Indian Sign Language vocabulary with on-demand SMPL-X kinematics
            </p>
          </div>
        </div>

        {/* Quick status message */}
        {statusMessage && (
          <div className="text-xs font-mono px-3 py-1 rounded-lg bg-[#101735] text-[#22D3EE] border border-[#273154] animate-pulse">
            {statusMessage}
          </div>
        )}
      </div>

      {/* Dataset Folder Dividing Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
        <div className="flex items-center gap-1.5 text-xs text-[#6B7A99] mr-1 shrink-0 font-medium">
          <Folder className="w-3.5 h-3.5 text-[#22D3EE]" />
          <span>Datasets:</span>
        </div>
        {DATASET_TABS.map((tab) => {
          const isSelected = selectedDataset === tab.id;
          const count = tab.id === 'all'
            ? allDatasetsCount
            : getDatasetCount(tab.match);

          return (
            <button
              key={tab.id}
              onClick={() => {
                setSelectedDataset(tab.id);
                setCurrentPage(1);
              }}
              className={`shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-all border ${
                isSelected
                  ? 'bg-[#22D3EE]/20 border-[#22D3EE] text-[#22D3EE] font-semibold shadow-[0_0_12px_rgba(34,211,238,0.25)]'
                  : 'bg-[#101735] hover:bg-[#1A244D] border-[#273154] text-[#A8B2D1] hover:text-white'
              }`}
            >
              <span>{tab.label}</span>
              {count > 0 && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-md font-mono ${
                    isSelected ? 'bg-[#22D3EE] text-[#0A0E24] font-bold' : 'bg-[#151D40] text-white'
                  }`}
                >
                  {count.toLocaleString()}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Search Bar & Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-[#6B7A99] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search over 8,200+ signs (e.g. good, water, drink, teacher)..."
            className="w-full bg-[#101735] text-xs py-2.5 pl-10 pr-4 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white placeholder-[#6B7A99] outline-none transition-colors"
          />
        </div>

        {/* Hand Filter Tabs */}
        <div className="flex items-center gap-1 bg-[#101735] p-1 rounded-xl border border-[#273154]">
          {[
            { id: '', label: 'All Signs' },
            { id: 'both', label: 'Both Hands' },
            { id: 'right_only', label: 'Right Hand' },
            { id: 'left_only', label: 'Left Hand' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setHandFilter(tab.id);
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                handFilter === tab.id
                  ? 'bg-[#22D3EE] text-[#0A0E24] font-semibold shadow'
                  : 'text-[#A8B2D1] hover:text-white hover:bg-[#151D40]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sign Grid */}
      <div className="min-h-[280px]">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-48 space-y-2 text-[#A8B2D1]">
            <RotateCw className="w-6 h-6 animate-spin text-[#22D3EE]" />
            <p className="text-xs">Searching vocabulary...</p>
          </div>
        ) : signs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 space-y-2 text-[#A8B2D1] bg-[#101735]/40 rounded-xl border border-[#273154]/50 p-6">
            <AlertCircle className="w-8 h-8 text-amber-400/80" />
            <p className="text-xs font-semibold text-white">No signs found matching "{searchQuery}"</p>
            <p className="text-[11px] text-[#A8B2D1]">
              Try a different word or clear the filter to browse the complete dictionary.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {signs.map((sign) => {
              const isSelected =
                currentSignName?.toLowerCase() === sign.gloss.toLowerCase() ||
                currentSignName?.toLowerCase() === sign.normalized_gloss.toLowerCase();
              const isConverting = convertingKey === sign.sample_key;
              const isCached = sign.smplx_cache_path != null || sign.conversion_status === 'cached';

              return (
                <div
                  key={sign.sample_key}
                  onClick={() => handlePlaySign(sign)}
                  className={`group relative p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between h-28 ${
                    isSelected
                      ? 'bg-[#22D3EE]/10 border-[#22D3EE] shadow-[0_0_15px_rgba(34,211,238,0.15)]'
                      : 'bg-[#101735] hover:bg-[#1A244D] border-[#273154] hover:border-[#3B4874]'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span className="text-[9px] font-mono text-[#6B7A99] truncate" title={sign.shard || sign.sample_key}>
                        {shortShard(sign.shard) || `#${sign.sample_key}`}
                      </span>
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded font-mono uppercase ${
                          isCached
                            ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                            : 'bg-[#22D3EE]/10 text-[#22D3EE] border border-[#22D3EE]/20'
                        }`}
                      >
                        {isCached ? 'CACHED' : 'AVAILABLE'}
                      </span>
                    </div>

                    <p className="text-xs font-bold text-white group-hover:text-[#22D3EE] transition-colors truncate">
                      {sign.gloss}
                    </p>
                  </div>

                  <div className="space-y-1 pt-1 border-t border-[#273154]/50">
                    <div className="flex items-center justify-between text-[10px] text-[#A8B2D1]">
                      <span className="flex items-center gap-1 font-mono">
                        <Hand className="w-3 h-3 text-[#22D3EE]" />
                        {sign.hand_category === 'both'
                          ? '2 Hands'
                          : sign.hand_category === 'right_only'
                          ? 'R Hand'
                          : sign.hand_category === 'left_only'
                          ? 'L Hand'
                          : 'Body'}
                      </span>
                      <span className="font-mono text-[9px] text-[#6B7A99]">
                        {sign.frame_count}f
                      </span>
                    </div>

                    <button
                      type="button"
                      className={`w-full py-1 rounded text-[10px] font-bold flex items-center justify-center gap-1 transition-colors ${
                        isSelected
                          ? 'bg-[#22D3EE] text-[#0A0E24]'
                          : 'bg-[#151D40] text-[#A8B2D1] group-hover:bg-[#22D3EE] group-hover:text-[#0A0E24]'
                      }`}
                    >
                      {isConverting ? (
                        <>
                          <RotateCw className="w-3 h-3 animate-spin" />
                          <span>CONVERTING</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-2.5 h-2.5 fill-current" />
                          <span>PLAY</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2 border-t border-[#273154] text-xs text-[#A8B2D1]">
          <span>
            Page <strong className="text-white font-mono">{currentPage}</strong> of{' '}
            <strong className="text-white font-mono">{totalPages}</strong> ({totalSigns} signs)
          </span>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1 || loading}
              className="p-1.5 rounded-lg bg-[#101735] border border-[#273154] hover:bg-[#1A244D] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages || loading}
              className="p-1.5 rounded-lg bg-[#101735] border border-[#273154] hover:bg-[#1A244D] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
