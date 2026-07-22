/*
 * theme-init.js — pre-paint theme resolver (Editorial Revamp)
 *
 * Origin-local, synchronous <head> script. Must be loaded in the document
 * <head> BEFORE first paint (not deferred/async) so the correct theme is
 * applied before the page renders, preventing a flash of the wrong theme.
 * CSP-safe: served from {% static %} (origin 'self'), no inline script.
 *
 * Resolution order (Requirements 2.4, 14.2):
 *   1. A valid persisted `theme` cookie ("light" or "dark").
 *   2. The operating-system / browser `prefers-color-scheme` preference.
 *   3. Light theme as the default when no preference is available.
 *
 * A malformed or unrecognized cookie value is treated as "no preference"
 * and resolution falls through to prefers-color-scheme, then light.
 */
(function () {
  'use strict';

  var VALID_THEMES = ['light', 'dark'];
  var DEFAULT_THEME = 'light';

  // Read the persisted theme from the `theme` cookie, if present.
  // Returns a valid theme string, or null when absent/malformed.
  function readThemeCookie() {
    try {
      var cookies = document.cookie ? document.cookie.split(';') : [];
      for (var i = 0; i < cookies.length; i++) {
        var parts = cookies[i].split('=');
        var name = parts.shift().trim();
        if (name === 'theme') {
          var value = decodeURIComponent(parts.join('=').trim());
          // Treat any unrecognized value as "no preference".
          return VALID_THEMES.indexOf(value) !== -1 ? value : null;
        }
      }
    } catch (e) {
      // Any failure reading cookies is treated as "no preference".
    }
    return null;
  }

  // Read the OS/browser color-scheme preference.
  // Returns "dark" or "light", or null when matchMedia is unavailable.
  function readSystemPreference() {
    try {
      if (typeof window.matchMedia === 'function') {
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          return 'dark';
        }
        if (window.matchMedia('(prefers-color-scheme: light)').matches) {
          return 'light';
        }
      }
    } catch (e) {
      // matchMedia unsupported or threw — treat as no preference.
    }
    return null;
  }

  function resolveTheme() {
    var cookieTheme = readThemeCookie();
    if (cookieTheme) {
      return cookieTheme;
    }
    var systemTheme = readSystemPreference();
    if (systemTheme) {
      return systemTheme;
    }
    return DEFAULT_THEME;
  }

  document.documentElement.dataset.theme = resolveTheme();
})();
