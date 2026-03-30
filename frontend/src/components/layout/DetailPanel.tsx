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

        {/* Quick stats row */}
        <div className="grid grid-cols-4 gap-2">
          <StatBox
            label="Conviction"
            value={signal.conviction.toFixed(2)}
            positive={signal.conviction > 0}
          />
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

      <div className="grid grid-cols-2 gap-2">
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
