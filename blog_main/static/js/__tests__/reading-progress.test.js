/*
 * Property + unit tests for reading-progress.js.
 *
 * # Feature: editorial-revamp, Property 2: Reading-progress reflects scroll position
 *
 * Property 2 (design.md): For any scroll offset within the article body's
 * scrollable range [0, max], the computed reading-progress value is within
 * [0, 100], equals 0 at the top and 100 at the bottom, and is monotonically
 * non-decreasing as the scroll offset increases.
 *
 * Validates: Requirements 4.4
 */
const fc = require('fast-check');
const { computeReadingProgress } = require('../reading-progress');

describe('reading-progress.js — computeReadingProgress', () => {
  // ---- Property 2: Reading-progress reflects scroll position ----------------

  // # Feature: editorial-revamp, Property 2: value stays within [0, 100]
  test('Property 2: progress is always within [0, 100] for offsets in [0, max]', () => {
    fc.assert(
      fc.property(
        // A positive scrollable range, and an offset constrained to [0, max].
        fc.double({ min: 1, max: 1e7, noNaN: true }),
        fc.double({ min: 0, max: 1, noNaN: true }),
        (max, fraction) => {
          const scrollTop = fraction * max;
          const progress = computeReadingProgress(scrollTop, max);
          expect(progress).toBeGreaterThanOrEqual(0);
          expect(progress).toBeLessThanOrEqual(100);
        }
      ),
      { numRuns: 300 }
    );
  });

  // # Feature: editorial-revamp, Property 2: 0 at the top of the range
  test('Property 2: progress is 0 at the top (scrollTop = 0)', () => {
    fc.assert(
      fc.property(fc.double({ min: 1, max: 1e7, noNaN: true }), (max) => {
        expect(computeReadingProgress(0, max)).toBe(0);
      }),
      { numRuns: 300 }
    );
  });

  // # Feature: editorial-revamp, Property 2: 100 at the bottom of the range
  test('Property 2: progress is 100 at the bottom (scrollTop = max)', () => {
    fc.assert(
      fc.property(fc.double({ min: 1, max: 1e7, noNaN: true }), (max) => {
        expect(computeReadingProgress(max, max)).toBe(100);
      }),
      { numRuns: 300 }
    );
  });

  // # Feature: editorial-revamp, Property 2: monotonic non-decreasing
  test('Property 2: progress is monotonically non-decreasing across sorted offsets', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 1, max: 1e7, noNaN: true }),
        // A set of random offsets within [0, max], expressed as fractions.
        fc.array(fc.double({ min: 0, max: 1, noNaN: true }), {
          minLength: 2,
          maxLength: 50,
        }),
        (max, fractions) => {
          const offsets = fractions.map((f) => f * max).sort((a, b) => a - b);
          const progresses = offsets.map((o) => computeReadingProgress(o, max));
          for (let i = 1; i < progresses.length; i++) {
            // Pairwise on sorted offsets: later offset never yields less progress.
            expect(progresses[i]).toBeGreaterThanOrEqual(progresses[i - 1]);
          }
        }
      ),
      { numRuns: 300 }
    );
  });

  // # Feature: editorial-revamp, Property 2: clamped for out-of-range offsets
  test('Property 2: out-of-range offsets stay clamped within [0, 100]', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 1, max: 1e7, noNaN: true }),
        fc.double({ min: -1e7, max: 2e7, noNaN: true }),
        (max, scrollTop) => {
          const progress = computeReadingProgress(scrollTop, max);
          expect(progress).toBeGreaterThanOrEqual(0);
          expect(progress).toBeLessThanOrEqual(100);
          if (scrollTop <= 0) {
            expect(progress).toBe(0);
          }
          if (scrollTop >= max) {
            expect(progress).toBe(100);
          }
        }
      ),
      { numRuns: 300 }
    );
  });

  // ---- Unit tests: specific examples and edge cases -------------------------

  test('midpoint offset yields 50%', () => {
    expect(computeReadingProgress(500, 1000)).toBe(50);
  });

  test('non-scrollable article (maxScroll <= 0) reports 0', () => {
    expect(computeReadingProgress(0, 0)).toBe(0);
    expect(computeReadingProgress(100, 0)).toBe(0);
    expect(computeReadingProgress(0, -50)).toBe(0);
  });

  test('non-finite inputs are handled without returning NaN', () => {
    expect(computeReadingProgress(NaN, 1000)).toBe(0);
    expect(computeReadingProgress(Infinity, 1000)).toBe(100);
    expect(computeReadingProgress(500, NaN)).toBe(0);
  });
});
