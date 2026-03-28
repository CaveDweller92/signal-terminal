import { useState, useEffect } from 'react';
import type { ParameterSnapshot, MetaReview } from '../../types/adaptation';
import {
  fetchCurrentParameters,
  fetchParameterLog,
  fetchMetaReviews,
  triggerMetaReview,
} from '../../services/api';
import { CurrentParameters } from './CurrentParameters';
import { ParameterDriftChart } from './ParameterDriftChart';
import { MetaReviewCard } from './MetaReviewCard';

type TabId = 'parameters' | 'reviews';

export function AdaptationPanel() {
  const [tab, setTab] = useState<TabId>('parameters');
  const [current, setCurrent] = useState<ParameterSnapshot | null>(null);
  const [log, setLog] = useState<ParameterSnapshot[]>([]);
  const [reviews, setReviews] = useState<MetaReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [cur, lg, rv] = await Promise.all([
          fetchCurrentParameters(),
          fetchParameterLog(50),
          fetchMetaReviews(30),
        ]);
        if (!cancelled) {
          setCurrent(cur);
          setLog(lg);
          setReviews(rv);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  async function handleTriggerReview() {
    setTriggering(true);
    try {
      await triggerMetaReview();
      const updated = await fetchMetaReviews(30);
      setReviews(updated);
    } finally {
      setTriggering(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-zinc-500">
        Loading adaptation data...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Tab bar */}
      <div className="border-b border-zinc-800 px-4 flex items-center justify-between">
        <div className="flex gap-1">
          <TabButton id="parameters" active={tab === 'parameters'} onClick={setTab}>
            Parameters
            {log.length > 0 && (
              <span className="ml-1.5 text-[10px] bg-zinc-700 text-zinc-400 px-1.5 rounded-full">
                {log.length}
              </span>
            )}
          </TabButton>
          <TabButton id="reviews" active={tab === 'reviews'} onClick={setTab}>
            Meta-Reviews
            {reviews.length > 0 && (
              <span className="ml-1.5 text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded-full">
                {reviews.length}
              </span>
            )}
          </TabButton>
        </div>
        {tab === 'reviews' && (
          <button
            onClick={handleTriggerReview}
            disabled={triggering}
            className="text-[10px] text-zinc-400 hover:text-zinc-200 border border-zinc-700 hover:border-zinc-500 px-2.5 py-1 rounded transition-colors disabled:opacity-40"
          >
            {triggering ? 'Running...' : 'Run Review'}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === 'parameters' && current && (
          <div className="p-4 space-y-6">
            <CurrentParameters snapshot={current} />
            <div className="border-t border-zinc-800 pt-4">
              <ParameterDriftChart snapshots={log} />
            </div>
          </div>
        )}

        {tab === 'reviews' && (
          <div className="p-4 space-y-2">
            {reviews.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-2 text-zinc-600">
                <p className="text-xs">No meta-reviews yet.</p>
                <p className="text-[10px]">Reviews run automatically at 4:15 PM ET, or click "Run Review".</p>
              </div>
            ) : (
              reviews.map((review, i) => (
                <MetaReviewCard key={review.id} review={review} expanded={i === 0} />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface TabButtonProps {
  id: TabId;
  active: boolean;
  onClick: (id: TabId) => void;
  children: React.ReactNode;
}

function TabButton({ id, active, onClick, children }: TabButtonProps) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`flex items-center px-3 py-2 text-xs font-semibold transition-colors border-b-2 ${
        active
          ? 'text-blue-400 border-blue-400'
          : 'text-zinc-500 border-transparent hover:text-zinc-300'
      }`}
    >
      {children}
    </button>
  );
}
