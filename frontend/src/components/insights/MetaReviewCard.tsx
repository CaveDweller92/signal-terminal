import { useState } from 'react';
import type { MetaReview } from '../../types/adaptation';

function renderJsonField(value: string[] | Record<string, unknown> | null): React.ReactNode {
  if (!value) return null;
  if (Array.isArray(value)) {
    return value.map((item, i) => (
      <div key={i} className="text-xs text-zinc-300">• {String(item)}</div>
    ));
  }
  return Object.entries(value).map(([k, v]) => (
    <div key={k} className="flex gap-2 text-xs font-mono">
      <span className="text-zinc-500 shrink-0">{k}:</span>
      <span className="text-zinc-300">{String(v)}</span>
    </div>
  ));
}

interface MetaReviewCardProps {
  review: MetaReview;
  expanded?: boolean;
}

export function MetaReviewCard({ review, expanded: defaultExpanded = false }: MetaReviewCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const date = new Date(review.review_date).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
  });

  const winRate = review.signals_generated > 0
    ? ((review.signals_correct / review.signals_generated) * 100).toFixed(1)
    : null;

  return (
    <div className="border border-zinc-800 rounded-lg overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-zinc-800/40 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-semibold text-zinc-100">{date}</span>
          {review.regime_at_review && (
            <span className="text-[10px] text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">
              {review.regime_at_review}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 text-[10px] font-mono">
          {winRate !== null && (
            <span className={parseFloat(winRate) >= 50 ? 'text-emerald-400' : 'text-red-400'}>
              {winRate}% win
            </span>
          )}
          {review.avg_return !== null && (
            <span className={review.avg_return >= 0 ? 'text-emerald-400' : 'text-red-400'}>
              {review.avg_return >= 0 ? '+' : ''}{review.avg_return.toFixed(2)}% avg
            </span>
          )}
          <span className="text-zinc-600">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-zinc-800/60">
          {/* Summary */}
          <div className="pt-3">
            <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1.5 font-semibold">
              Claude's Assessment
            </p>
            <p className="text-xs text-zinc-300 leading-relaxed">{review.summary}</p>
          </div>

          {/* Recommendations */}
          {review.recommendations && (Array.isArray(review.recommendations) ? review.recommendations.length > 0 : Object.keys(review.recommendations).length > 0) && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1.5 font-semibold">
                Recommendations
              </p>
              <div className="space-y-1">{renderJsonField(review.recommendations)}</div>
            </div>
          )}

          {/* Parameter adjustments */}
          {review.parameter_adjustments && (Array.isArray(review.parameter_adjustments) ? review.parameter_adjustments.length > 0 : Object.keys(review.parameter_adjustments).length > 0) && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1.5 font-semibold">
                Parameter Adjustments
              </p>
              <div className="space-y-1">{renderJsonField(review.parameter_adjustments)}</div>
            </div>
          )}

          {/* Stats footer */}
          <div className="flex gap-4 text-[10px] font-mono text-zinc-600 pt-1 border-t border-zinc-800/60">
            <span>{review.signals_generated} signals</span>
            <span>{review.signals_correct} correct</span>
            {review.regime_accuracy !== null && (
              <span>regime acc: {(review.regime_accuracy * 100).toFixed(0)}%</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
