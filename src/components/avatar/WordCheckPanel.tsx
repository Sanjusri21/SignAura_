import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, XCircle, ListChecks, Search, ArrowRight, Loader2 } from 'lucide-react';
import { fetchPlayableWords, PlayableWord, WordCheckResponse } from '../../services/signAvatarWords';
import { registerPlayableWords } from './SignAvatar3D';

const MAX_LISTED_WORDS = 400;

interface WordCheckPanelProps {
  /** Result of the last Generate; null until the first check */
  check: WordCheckResponse | null;
  isChecking?: boolean;
  /** Plays a single word from the searchable list */
  onSelectWord?: (word: string) => void;
}

const displayWord = (key: string) => key.replace(/_/g, ' ');

export const WordCheckPanel: React.FC<WordCheckPanelProps> = ({ check, isChecking, onSelectWord }) => {
  const [words, setWords] = useState<PlayableWord[]>([]);
  const [excludedFailed, setExcludedFailed] = useState(0);
  const [listError, setListError] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetchPlayableWords()
      .then((res) => {
        if (cancelled) return;
        setWords(res.words);
        setExcludedFailed(res.excluded_failed);
        registerPlayableWords(res.words.map((w) => w.word));
      })
      .catch((err) => !cancelled && setListError(err instanceof Error ? err.message : 'Could not load word list'));
    return () => {
      cancelled = true;
    };
  }, []);

  // Prefix matches first, then words containing the query
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase().replace(/[\s-]+/g, '_');
    if (!q) return words;
    const prefix = words.filter((w) => w.word.startsWith(q));
    const inner = words.filter((w) => !w.word.startsWith(q) && w.word.includes(q));
    return [...prefix, ...inner];
  }, [words, query]);

  const availablePct = check && check.total > 0 ? Math.round((100 * check.available) / check.total) : 0;

  return (
    <div className="bg-[#151D40] rounded-2xl p-4 border border-[#273154] shadow-md space-y-4">
      {/* Word check for the last generated sentence */}
      <div className="space-y-2.5">
        <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
          <ListChecks className="w-4 h-4 text-[#22D3EE]" />
          <span>Word Check</span>
          {isChecking && <Loader2 className="w-3.5 h-3.5 text-[#A8B2D1] animate-spin ml-auto" />}
        </div>

        {check ? (
          <>
            <div>
              <p className="text-sm font-bold text-white">
                {check.available} of {check.total} words available
              </p>
              <div className="h-1.5 mt-1.5 rounded-full bg-[#101735] overflow-hidden">
                <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${availablePct}%` }} />
              </div>
            </div>
            <ul className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-1.5">
              {check.tokens.map((t, idx) => (
                <li
                  key={`${idx}-${t.input}`}
                  className="flex items-start gap-2 px-2 py-1.5 rounded-lg bg-[#101735] border border-[#273154] text-xs"
                >
                  {t.status === 'missing' ? (
                    <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-px" aria-label="missing" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-px" aria-label="available" />
                  )}
                  <div className="min-w-0">
                    <p className={`font-mono font-semibold ${t.status === 'missing' ? 'text-red-300' : 'text-white'}`}>
                      {t.input}
                    </p>
                    {t.status === 'synonym' && (
                      <p className="text-[10px] text-[#A8B2D1] flex items-center gap-1">
                        <ArrowRight className="w-3 h-3" /> signed as "{displayWord(t.synonym_of || t.key)}"
                      </p>
                    )}
                    {t.status === 'missing' && (
                      <p className="text-[10px] text-red-300/70">{t.reason || 'not in dataset'} · skipped</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-[11px] text-[#A8B2D1] leading-relaxed">
            Type text and click <span className="text-white font-semibold">Generate 3D Signs</span> to see which
            words the avatar can sign.
          </p>
        )}
      </div>

      {/* Searchable list of every playable word */}
      <div className="pt-3 border-t border-[#273154] space-y-2">
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-[11px] font-bold text-white uppercase tracking-wider">Available Words</p>
          <p className="text-[10px] text-[#A8B2D1] font-mono">
            {query.trim() ? `${filtered.length.toLocaleString()} of ` : ''}
            {words.length.toLocaleString()}
          </p>
        </div>
        <div className="relative sm:max-w-sm">
          <Search className="w-3.5 h-3.5 text-[#6B7A99] absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search words..."
            className="w-full bg-[#101735] text-xs py-2 pl-8 pr-3 rounded-xl border border-[#273154] focus:border-[#22D3EE] text-white placeholder-[#6B7A99] outline-none"
          />
        </div>

        {listError ? (
          <p className="text-[11px] text-amber-300">{listError}</p>
        ) : (
          <div className="h-56 overflow-y-auto pr-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-2 gap-y-0.5 content-start">
            {filtered.slice(0, MAX_LISTED_WORDS).map((w) => (
              <button
                key={w.word}
                onClick={() => onSelectWord?.(w.target || w.word)}
                title={w.target ? `Signed as "${displayWord(w.target)}"` : w.label || w.word}
                className="w-full text-left flex items-center justify-between gap-2 px-2 py-1 rounded-md text-xs text-[#A8B2D1] hover:bg-[#1A244D] hover:text-white transition-colors"
              >
                <span className="font-mono truncate">{displayWord(w.word)}</span>
                {w.target ? (
                  <span className="text-[9px] text-[#6B7A99] shrink-0">→ {displayWord(w.target)}</span>
                ) : w.source === 'SignMotionDB' ? (
                  <span className="text-[9px] text-emerald-400/80 shrink-0">verified</span>
                ) : null}
              </button>
            ))}
            {filtered.length > MAX_LISTED_WORDS && (
              <p className="col-span-full text-[10px] text-[#6B7A99] px-2 pt-1">
                +{(filtered.length - MAX_LISTED_WORDS).toLocaleString()} more, refine the search
              </p>
            )}
            {words.length > 0 && filtered.length === 0 && (
              <p className="col-span-full text-[11px] text-[#6B7A99] px-2">No playable word matches "{query}".</p>
            )}
          </div>
        )}
        {excludedFailed > 0 && (
          <p className="text-[10px] text-[#6B7A99]">{excludedFailed} words hidden: their clips failed the quality check.</p>
        )}
      </div>
    </div>
  );
};
