import { useState } from 'react';
import type { Signal } from '../../types/market';
import { SignalBadge } from '../common/SignalBadge';
import { StatBox } from '../common/StatBox';

interface DetailPanelProps {
  signal: Signal;
}

type TabId = 'technical' | 'sentiment' | 'fundamental';

interface TabDef {
  id: TabId;
  label: string;
}

const TABS: TabDef[] = [
  { id: 'technical', label: 'Technical' },
  { id: 'sentiment', label: 'Sentiment' },
  { id: 'fundamental', label: 'Fundamental' },
];

export function DetailPanel({ signal }: DetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>('technical');

  return (
    <div className="flex-1 flex flex-col bg-zinc-950 overflow-y-auto">
      {/* Stock header */}
      <div className="px-6 py-4 border-b border-zinc-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-mono font-bold text-zinc-100">
              {signal.symbol}
            </h2>
            <SignalBadge type={signal.signal_type} conviction={signal.conviction} />
          </div>
          <div className="text-right">
            <div className="text-lg font-mono font-semibold text-zinc-100">
              ${signal.price_at_signal.toFixed(2)}
            </div>
          </div>
        </div>

        {/* Conviction breakdown */}
        <ConvictionBreakdown signal={signal} />

        {/* Quick stats row */}
        <div className="grid grid-cols-3 gap-2 mt-2">
          <StatBox
            label="Stop Loss"
            value={`$${signal.suggested_stop_loss.toFixed(2)}`}
            subValue={`${((1 - signal.suggested_stop_loss / signal.price_at_signal) * 100).toFixed(1)}% risk`}
          />
          <StatBox
            label="Target"
            value={`$${signal.suggested_profit_target.toFixed(2)}`}
            subValue={`${((signal.suggested_profit_target / signal.price_at_signal - 1) * 100).toFixed(1)}% reward`}
          />
          <StatBox
            label="ATR"
            value={signal.atr_at_signal.toFixed(2)}
            subValue={`${((signal.atr_at_signal / signal.price_at_signal) * 100).toFixed(1)}% of price`}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-zinc-800 px-6">
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 text-xs font-semibold transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'text-blue-400 border-blue-400'
                  : 'text-zinc-500 border-transparent hover:text-zinc-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 px-6 py-4">
        {activeTab === 'technical' && <TechnicalContent signal={signal} />}
        {activeTab === 'sentiment' && <SentimentContent signal={signal} />}
        {activeTab === 'fundamental' && <FundamentalContent signal={signal} />}
      </div>
    </div>
  );
}

function TechnicalContent({ signal }: { signal: Signal }) {
  const { indicators, reasons } = signal;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <StatBox
          label="RSI (14)"
          value={indicators.rsi.toFixed(1)}
          positive={indicators.rsi < 50}
        />
        <StatBox
          label="MACD Histogram"
          value={indicators.macd_histogram.toFixed(4)}
          positive={indicators.macd_histogram > 0}
        />
        <StatBox
          label="Volume Ratio"
          value={`${indicators.volume_ratio.toFixed(1)}x`}
          positive={indicators.volume_ratio > 1.5}
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        <StatBox
          label="EMA Crossover"
          value={indicators.ema_crossover}
          subValue={indicators.ema_just_crossed ? 'Just crossed!' : undefined}
          positive={indicators.ema_crossover === 'bullish'}
        />
        <StatBox
          label="Tech Score"
          value={signal.tech_score.toFixed(2)}
          subValue="Range: -5 to +5"
          positive={signal.tech_score > 0}
        />
        <StatBox
          label="ADX"
          value={indicators.adx != null ? indicators.adx.toFixed(1) : '—'}
          subValue={indicators.adx != null ? (indicators.adx > 40 ? 'Strong trend' : indicators.adx < 20 ? 'Weak trend' : 'Moderate') : undefined}
          positive={indicators.adx != null ? indicators.adx > 25 : undefined}
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        <StatBox
          label="Bollinger %B"
          value={indicators.bollinger_pct_b != null ? indicators.bollinger_pct_b.toFixed(3) : '—'}
          subValue={indicators.bollinger_pct_b != null ? (indicators.bollinger_pct_b < 0.2 ? 'Near lower band' : indicators.bollinger_pct_b > 0.8 ? 'Near upper band' : 'Mid-range') : undefined}
          positive={indicators.bollinger_pct_b != null ? indicators.bollinger_pct_b < 0.5 : undefined}
        />
        <StatBox
          label="Stochastic %K"
          value={indicators.stochastic_k != null ? indicators.stochastic_k.toFixed(1) : '—'}
          subValue={indicators.stochastic_k != null ? (indicators.stochastic_k < 20 ? 'Oversold' : indicators.stochastic_k > 80 ? 'Overbought' : 'Neutral') : undefined}
          positive={indicators.stochastic_k != null ? indicators.stochastic_k < 50 : undefined}
        />
        <StatBox
          label="Divergence"
          value={indicators.divergence?.type ?? 'none'}
          subValue={indicators.divergence?.type !== 'none' && indicators.divergence?.confidence != null ? `${(indicators.divergence.confidence * 100).toFixed(0)}% conf` : undefined}
          positive={indicators.divergence?.type === 'bullish' ? true : indicators.divergence?.type === 'bearish' ? false : undefined}
        />
      </div>

      <ReasonsList title="Technical Signals" reasons={reasons.technical} />
    </div>
  );
}

function SentimentContent({ signal }: { signal: Signal }) {
  return (
    <div className="space-y-4">
      <StatBox
        label="Sentiment Score"
        value={signal.sentiment_score.toFixed(2)}
        subValue="Range: -3 to +3"
        positive={signal.sentiment_score > 0}
      />
      <ReasonsList title="Sentiment Analysis" reasons={signal.reasons.sentiment} />
    </div>
  );
}

function FundamentalContent({ signal }: { signal: Signal }) {
  return (
    <div className="space-y-4">
      <StatBox
        label="Fundamental Score"
        value={signal.fundamental_score.toFixed(2)}
        subValue="Range: -2 to +2"
        positive={signal.fundamental_score > 0}
      />
      <ReasonsList title="Fundamental Analysis" reasons={signal.reasons.fundamental} />
    </div>
  );
}

function ConvictionBreakdown({ signal }: { signal: Signal }) {
  // Default weights — these match the backend's current config
  // TODO: fetch actual weights from /api/adaptation/parameters if needed
  const tw = 0.55;
  const sw = 0.30;
  const fw = 0.15;

  const techContrib = signal.tech_score * tw;
  const sentContrib = signal.sentiment_score * sw;
  const fundContrib = signal.fundamental_score * fw;

  const riskPct = ((1 - signal.suggested_stop_loss / signal.price_at_signal) * 100);
  const rewardPct = ((signal.suggested_profit_target / signal.price_at_signal - 1) * 100);
  const rr = riskPct > 0 ? rewardPct / riskPct : 0;

  return (
    <div className="bg-zinc-800/50 rounded-lg px-4 py-3 border border-zinc-700/50">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          Conviction Breakdown
        </span>
        <span className={`text-lg font-mono font-bold ${signal.conviction > 0 ? 'text-emerald-400' : signal.conviction < 0 ? 'text-red-400' : 'text-zinc-300'}`}>
          {signal.conviction > 0 ? '+' : ''}{signal.conviction.toFixed(2)}
        </span>
      </div>

      {/* Score bars */}
      <div className="space-y-1.5">
        <ScoreRow label="Technical" score={signal.tech_score} weight={tw} contrib={techContrib} range={5} />
        <ScoreRow label="Sentiment" score={signal.sentiment_score} weight={sw} contrib={sentContrib} range={3} />
        <ScoreRow label="Fundamental" score={signal.fundamental_score} weight={fw} contrib={fundContrib} range={2} />
      </div>

      {/* Formula */}
      <div className="mt-2 pt-2 border-t border-zinc-700/50 text-[10px] font-mono text-zinc-500">
        <span>{techContrib >= 0 ? '+' : ''}{techContrib.toFixed(2)}</span>
        <span className="text-zinc-600"> + </span>
        <span>{sentContrib >= 0 ? '+' : ''}{sentContrib.toFixed(2)}</span>
        <span className="text-zinc-600"> + </span>
        <span>{fundContrib >= 0 ? '+' : ''}{fundContrib.toFixed(2)}</span>
        <span className="text-zinc-600"> = </span>
        <span className={signal.conviction > 0 ? 'text-emerald-400' : signal.conviction < 0 ? 'text-red-400' : 'text-zinc-300'}>
          {signal.conviction > 0 ? '+' : ''}{signal.conviction.toFixed(2)}
        </span>
        <span className="ml-3 text-zinc-600">R:R {rr.toFixed(1)}:1</span>
      </div>
    </div>
  );
}

function ScoreRow({ label, score, weight, contrib, range }: {
  label: string; score: number; weight: number; contrib: number; range: number;
}) {
  // Bar width: score / range mapped to 0-100%
  const pct = Math.min(100, Math.abs(score) / range * 100);
  const positive = score >= 0;

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-zinc-400 w-20 shrink-0">{label}</span>
      <div className="flex-1 h-3 bg-zinc-900 rounded-sm overflow-hidden relative">
        <div
          className={`h-full rounded-sm ${positive ? 'bg-emerald-500/60' : 'bg-red-500/60'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-[10px] font-mono w-10 text-right ${positive ? 'text-emerald-400' : 'text-red-400'}`}>
        {score >= 0 ? '+' : ''}{score.toFixed(1)}
      </span>
      <span className="text-[10px] font-mono text-zinc-600 w-8 text-right">
        ×{(weight * 100).toFixed(0)}%
      </span>
      <span className={`text-[10px] font-mono w-12 text-right ${contrib >= 0 ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
        = {contrib >= 0 ? '+' : ''}{contrib.toFixed(2)}
      </span>
    </div>
  );
}

function ReasonsList({ title, reasons }: { title: string; reasons: string[] }) {
  return (
    <div>
      <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 mb-2 font-semibold">
        {title}
      </h3>
      <ul className="space-y-1">
        {reasons.map((reason, i) => (
          <li
            key={i}
            className="text-xs text-zinc-300 font-mono pl-3 border-l-2 border-zinc-700 py-0.5"
          >
            {reason}
          </li>
        ))}
      </ul>
    </div>
  );
}
