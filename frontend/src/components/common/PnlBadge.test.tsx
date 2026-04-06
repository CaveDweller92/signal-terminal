/**
 * Tests for PnlBadge — P&L display formatting.
 *
 * This component shows profit/loss numbers to the user.
 * Wrong sign, missing dollar sign, or incorrect formatting
 * could cause the user to misread their position.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PnlBadge } from './PnlBadge';

describe('PnlBadge', () => {
  it('shows dash for null P&L', () => {
    render(<PnlBadge pct={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('shows positive P&L with + sign and green color', () => {
    const { container } = render(<PnlBadge pct={5.25} />);
    expect(screen.getByText('+5.25%')).toBeInTheDocument();
    const span = container.querySelector('.text-emerald-400');
    expect(span).toBeInTheDocument();
  });

  it('shows negative P&L without + sign and red color', () => {
    const { container } = render(<PnlBadge pct={-3.14} />);
    expect(screen.getByText('-3.14%')).toBeInTheDocument();
    const span = container.querySelector('.text-red-400');
    expect(span).toBeInTheDocument();
  });

  it('shows zero as positive (green, +0.00%)', () => {
    const { container } = render(<PnlBadge pct={0} />);
    expect(screen.getByText('+0.00%')).toBeInTheDocument();
    const span = container.querySelector('.text-emerald-400');
    expect(span).toBeInTheDocument();
  });

  it('shows dollar amount when provided', () => {
    render(<PnlBadge pct={5.0} dollar={500} />);
    expect(screen.getByText('+5.00%')).toBeInTheDocument();
    expect(screen.getByText('(+$500.00)')).toBeInTheDocument();
  });

  it('shows absolute dollar for negative P&L', () => {
    render(<PnlBadge pct={-2.5} dollar={-250} />);
    expect(screen.getByText('-2.50%')).toBeInTheDocument();
    // Dollar shows as absolute value with sign from pct
    expect(screen.getByText('($250.00)')).toBeInTheDocument();
  });

  it('formats to exactly 2 decimal places', () => {
    render(<PnlBadge pct={1.1} />);
    expect(screen.getByText('+1.10%')).toBeInTheDocument();
  });

  it('handles very small fractions', () => {
    render(<PnlBadge pct={0.003} />);
    expect(screen.getByText('+0.00%')).toBeInTheDocument();
  });
});
