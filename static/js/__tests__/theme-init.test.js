/*
 * Behavior tests for theme-init.js — pre-paint theme resolution.
 *
 * Covers the init branches with mocked matchMedia (dark / light / unsupported)
 * and cookie precedence / malformed-cookie fallthrough.
 *
 * Spec task 11.3 — Requirement 2.4 (initial theme from OS/browser preference,
 * defaulting to light when none is available) and the cookie precedence that
 * underpins persistence (Requirement 2.3).
 */
const {
  loadScript,
  mockMatchMedia,
  resetEnvironment,
} = require('./helpers');

describe('theme-init.js pre-paint theme resolution', () => {
  beforeEach(() => {
    resetEnvironment();
  });

  describe('system-preference branches (no stored cookie)', () => {
    test('resolves to dark when the OS/browser prefers dark (Req 2.4)', () => {
      mockMatchMedia('dark');

      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('dark');
    });

    test('resolves to light when the OS/browser prefers light (Req 2.4)', () => {
      mockMatchMedia('light');

      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('light');
    });

    test('defaults to light when matchMedia is unsupported (Req 2.4)', () => {
      mockMatchMedia(null);

      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('light');
    });
  });

  describe('cookie precedence', () => {
    test('a valid stored theme cookie overrides system preference (Req 2.3)', () => {
      document.cookie = 'theme=dark; Path=/';
      mockMatchMedia('light');

      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('dark');
    });

    test('a valid light cookie is honored even when system prefers dark (Req 2.3)', () => {
      document.cookie = 'theme=light; Path=/';
      mockMatchMedia('dark');

      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('light');
    });

    test('a malformed cookie is ignored and falls through to system preference (Req 2.4)', () => {
      document.cookie = 'theme=chartreuse; Path=/';
      mockMatchMedia('dark');

      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('dark');
    });

    test('a malformed cookie with no system preference falls through to the light default (Req 2.4)', () => {
      document.cookie = 'theme=not-a-theme; Path=/';
      mockMatchMedia(null);

      loadScript('theme-init.js');

      expect(document.documentElement.dataset.theme).toBe('light');
    });
  });
});
