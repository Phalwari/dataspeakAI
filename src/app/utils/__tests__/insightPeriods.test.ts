import { describe, expect, it } from 'vitest';
import { selectPeriodChart } from '../insightPeriods';

describe('period comparison source', () => {
  it('does not turn city rankings into historical zero growth', () => {
    expect(selectPeriodChart([
      { type: 'bar', data: [{ name: 'East', val: 30 }, { name: 'West', val: 40 }] },
      { type: 'area', status: 'unavailable', data: [] },
    ])).toBeUndefined();
  });

  it('uses actual observed numeric periods, preserving zero', () => {
    const trend = { type: 'area', data: [{ period: '2026-09', value: 30 }, { period: '2026-10', value: 0 }] };
    expect(selectPeriodChart([{ type: 'bar', data: [1, 2] }, trend])).toBe(trend);
  });

  it('rejects failed, incomplete and missing-value time series', () => {
    expect(selectPeriodChart([
      { type: 'line', status: 'error', data: [{ value: 1 }, { value: 2 }] },
      { type: 'line', data: [{ value: 1 }] },
      { type: 'area', data: [{ value: null }, { value: 2 }] },
    ])).toBeUndefined();
  });
});
