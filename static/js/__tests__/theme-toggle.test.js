/*
 * Behavior tests for theme-toggle.js — toggle, persistence, and transition guard.
 *
 * Covers:
 *   - toggle-without-navigation (Requirement 2.2)
 *   - persistence round-trip: toggle writes a cookie that theme-init.js later
 *     honors on a subsequent load (Requirement 2.3)
 *   - transition-unsupported fallback: the change is declined rather than
 *     applied instantaneously (Requirement 2.5)
 *
 * Spec task 11.3 — Requirements 2.2, 2.3, 2.5.
 */
const {
  loadScript,
  mockCSSSupports,
  resetEnvironment,
} = require('./helpers');

describe('theme-toggle.js behavior', () => {
  beforeEach(() => {
    resetEnvironment();
  });

  describe('toggle without navigation (Req 2.2)', () => {
    test('activating a [data-theme-toggle] control flips the theme in place', () => {
      document.documentElement.dataset.theme = 'light';
      document.body.innerHTML =
        '<button type="button" data-theme-toggle>Toggle theme</button>';
      mockCSSSupports(true);

      loadScript('theme-toggle.js');

      const hrefBefore = window.location.href;
      const button = document.querySelector('[data-theme-toggle]');
      button.click();

      // Theme flipped light -> dark.
      expect(document.documentElement.dataset.theme).toBe('dark');
      // No navigation occurred.
      expect(window.location.href).toBe(hrefBefore);
    });

    test('EditorialTheme.toggle() flips dark -> light without navigation', () => {
      document.documentElement.dataset.theme = 'dark';
      mockCSSSupports(true);

      loadScript('theme-toggle.js');

      const hrefBefore = window.location.href;
      const completed = window.EditorialTheme.toggle();

      expect(completed).toBe(true);
      expect(document.documentElement.dataset.theme).toBe('light');
      expect(window.location.href).toBe(hrefBefore);
    });
  });

  describe('persistence round-trip (Req 2.3)', () => {
    test('a toggled theme is written to a cookie that theme-init.js honors on reload', () => {
      document.documentElement.dataset.theme = 'light';
      mockCSSSupports(true);

      loadScript('theme-toggle.js');
      const completed = window.EditorialTheme.apply('dark');

      expect(completed).toBe(true);
      expect(document.cookie).toContain('theme=dark');

      // Simulate a fresh page load: clear the applied attribute (but keep the
      // cookie) and re-run the pre-paint resolver. It must honor the cookie.
      document.documentElement.removeAttribute('data-theme');
      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('dark');
    });
  });

  describe('transition-unsupported fallback (Req 2.5)', () => {
    test('applyTheme declines the change when transitions are unsupported', () => {
      document.documentElement.dataset.theme = 'light';
      mockCSSSupports(false);

      loadScript('theme-toggle.js');
      const completed = window.EditorialTheme.apply('dark');

      // Change is declined rather than applied instantaneously.
      expect(completed).toBe(false);
      expect(document.documentElement.dataset.theme).toBe('light');
      // Nothing persisted because the change was not completed.
      expect(document.cookie).not.toContain('theme=dark');
    });

    test('toggle() is a no-op flash when transitions are unsupported', () => {
      document.documentElement.dataset.theme = 'dark';
      document.body.innerHTML =
        '<button type="button" data-theme-toggle>Toggle theme</button>';
      mockCSSSupports(false);

      loadScript('theme-toggle.js');
      document.querySelector('[data-theme-toggle]').click();

      // Theme unchanged: the toggle refused to switch instantaneously.
      expect(document.documentElement.dataset.theme).toBe('dark');
    });

    test('transitionsSupported() reflects the CSS.supports result', () => {
      mockCSSSupports(true);
      loadScript('theme-toggle.js');
      expect(window.EditorialTheme.transitionsSupported()).toBe(true);

      mockCSSSupports(false);
      loadScript('theme-toggle.js');
      expect(window.EditorialTheme.transitionsSupported()).toBe(false);
    });
  });
});
