/*
 * reading-progress.js — reading-progress indicator (Editorial Revamp)
 *
 * Origin-local, CSP-safe script (no inline code). Provides the SOLE
 * scroll-driven visual update permitted by this feature (Requirement 4.4):
 * a thin accent bar whose width tracks how far the reader has scrolled
 * through the article body.
 *
 * The module is split into two clearly separated parts:
 *
 *   1. A PURE function `computeReadingProgress(scrollTop, maxScroll)` that
 *      maps a scroll offset to a clamped 0-100 progress value. It has no
 *      dependency on the DOM, timers, or globals, so it can be property-tested
 *      in isolation (spec task 11.4, Property 2).
 *
 *   2. A thin DOM wiring layer that reads the real scroll position on scroll
 *      and writes the computed value into the `--reading-progress` CSS custom
 *      property (as a percentage) on the `.reading-progress` element. The
 *      wiring is GUARDED so the module no-ops when the progress element is
 *      absent or when it runs outside a browser (e.g., under a bare test
 *      runner without jsdom).
 *
 * The file is authored in a small UMD wrapper so it can be:
 *   - loaded directly in the browser from {% static %} (exposing
 *     `window.ReadingProgress`), and
 *   - `require()`d from a CommonJS test (exposing `module.exports`).
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) {
    // CommonJS (Jest / Node)
    module.exports = api;
  }
  if (root) {
    // Browser global
    root.ReadingProgress = api;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Map a scroll offset to a reading-progress percentage.
   *
   * Pure function — no side effects, no globals.
   *
   * Contract (Property 2, Requirement 4.4):
   *   - The result is always within [0, 100].
   *   - It is 0 at the top of the scrollable range (scrollTop <= 0).
   *   - It is 100 at the bottom of the scrollable range (scrollTop >= maxScroll).
   *   - It is monotonically non-decreasing as scrollTop increases.
   *   - When there is nothing to scroll (maxScroll <= 0) the article fits on
   *     screen and is fully "read", so progress is 0 at the top; we treat a
   *     non-scrollable article as 0 progress until scrolled, and because
   *     scrollTop cannot exceed a non-positive max, it stays 0.
   *
   * @param {number} scrollTop  Current scroll offset within the article body.
   * @param {number} maxScroll  Maximum scrollable offset (>= 0).
   * @returns {number} Progress in the inclusive range [0, 100].
   */
  function computeReadingProgress(scrollTop, maxScroll) {
    // Coerce non-finite inputs to a safe 0 so the function never returns NaN.
    if (!isFinite(scrollTop)) {
      scrollTop = 0;
    }
    if (!isFinite(maxScroll) || maxScroll <= 0) {
      // Nothing to scroll: there is no meaningful progress range, so report 0.
      return 0;
    }

    // Clamp the offset into [0, maxScroll] before scaling so the result can
    // never fall outside [0, 100], even for out-of-range inputs.
    var clamped = scrollTop;
    if (clamped < 0) {
      clamped = 0;
    } else if (clamped > maxScroll) {
      clamped = maxScroll;
    }

    return (clamped / maxScroll) * 100;
  }

  /**
   * Wire the pure function to the DOM: update the `--reading-progress` CSS
   * custom property on scroll. Guarded so it safely no-ops when there is no
   * document, no progress element, or no window to listen on.
   *
   * @param {Document} [doc]  Document to operate on (defaults to the global).
   * @param {Window} [win]    Window to listen on (defaults to the global).
   * @returns {boolean} true when wiring was installed, false when it no-oped.
   */
  function init(doc, win) {
    doc = doc || (typeof document !== 'undefined' ? document : null);
    win = win || (typeof window !== 'undefined' ? window : null);

    if (!doc || !win) {
      return false;
    }

    var bar = doc.querySelector('.reading-progress');
    if (!bar) {
      // No progress indicator on this page (e.g., non-article page): no-op.
      return false;
    }

    var article =
      doc.querySelector('[data-reading-progress-target]') ||
      doc.querySelector('article') ||
      doc.documentElement;

    function update() {
      var scrollTop =
        win.scrollY != null
          ? win.scrollY
          : doc.documentElement
          ? doc.documentElement.scrollTop
          : 0;

      // The scrollable range for the whole document/article: how far past the
      // viewport the content extends.
      var contentHeight = article
        ? article.scrollHeight || article.offsetHeight || 0
        : 0;
      var viewportHeight =
        win.innerHeight ||
        (doc.documentElement ? doc.documentElement.clientHeight : 0) ||
        0;
      var maxScroll = contentHeight - viewportHeight;

      var progress = computeReadingProgress(scrollTop, maxScroll);
      bar.style.setProperty('--reading-progress', progress + '%');
    }

    win.addEventListener('scroll', update, { passive: true });
    win.addEventListener('resize', update, { passive: true });
    // Set the initial value for the current scroll position.
    update();
    return true;
  }

  // Auto-wire in the browser once the DOM is ready. This is skipped under the
  // CommonJS test runner (where `module.exports` is present) so the pure
  // function can be imported without side effects.
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        init();
      });
    } else {
      init();
    }
  }

  return {
    computeReadingProgress: computeReadingProgress,
    init: init
  };
});
