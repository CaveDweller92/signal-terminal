/**
 * Tests for SignalBadge — signal type display.
 *
 * Ensures BUY/SELL/HOLD display the correct color and conviction value.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SignalBadge } from './SignalBadge';

describe('SignalBadge', () => {
  it('renders BUY with green styling', () => {
    const { container } = render(<SignalBadge type="BUY" conviction={1.5} />);
    expect(screen.getByText('BUY')).toBeInTheDocument();
    expect(screen.getByText('1.5')).toBeInTheDocument();
    const badge = container.querySelector('.text-emerald-400');
    expect(badge).toBeInTheDocument();
  });

  it('renders SELL with red styling', () => {
    const { container } = render(<SignalBadge type="SELL" conviction={-1.3} />);
    expect(screen.getByText('SELL')).toBeInTheDocument();
    expect(screen.getByText('1.3')).toBeInTheDocument(); // absolute value
    const badge = container.querySelector('.text-red-400');
    expect(badge).toBeInTheDocument();
  });

  it('renders HOLD with neutral styling', () => {
    const { container } = render(<SignalBadge type="HOLD" conviction={0.5} />);
    expect(screen.getByText('HOLD')).toBeInTheDocument();
    expect(screen.getByText('0.5')).toBeInTheDocument();
    const badge = container.querySelector('.text-zinc-400');
    expect(badge).toBeInTheDocument();
  });

  it('shows absolute conviction for negative values', () => {
    render(<SignalBadge type="SELL" conviction={-2.7} />);
    expect(screen.getByText('2.7')).toBeInTheDocument(); // not -2.7
  });

  it('formats conviction to 1 decimal place', () => {
    render(<SignalBadge type="BUY" conviction={1.0} />);
    expect(screen.getByText('1.0')).toBeInTheDocument();
  });
});
