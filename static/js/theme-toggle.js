/*
 * theme-toggle.js — theme toggle, persistence, and transition guard (Editorial Revamp)
 *
 * Deferred, origin-local script. Loaded with `defer` from {% static %}
 * (origin 'self'), CSP-safe with no inline script. Runs after the DOM is
 * parsed and after theme-init.js has already resolved the pre-paint theme.
 *
 * Responsibilities:
 *   - Wire the Theme_Toggle control(s) so activating one flips the active
 *     theme between "light" and "dark" WITHOUT a full page navigation
 *     (Requirement 2.2).
 *   - Persist the chosen theme in a long-lived, JS-readable `theme` cookie
 *     (Max-Age ~1 year, SameSite=Lax, not HttpOnly) so the preference is
 *     honored on subsequent loads without authentication
 *     (Requirements 2.3, 14.2). The cookie name/values match theme-init.js.
 *   - Feature-detect smooth-transition support. If transitions cannot be
 *     applied due to a browser limitation, DECLINE to complete the theme
 *     change rather than switching instantaneously with a visible flash
 *     (Requirement 2.5).
 *
 * A Theme_Toggle control is any element carrying the `[data-theme-toggle]`
 * attribute.
 */
(function () {
  'use strict';

  var VALID_THEMES = ['light', 'dark'];
  var COOKIE_NAME = 'theme';
  // ~1 year in seconds (365 days). Long-lived so the preference survives
  // across sessions without an account (Requirements 2.3, 14.2).
  var COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
  var TOGGLE_SELECTOR = '[data-theme-toggle]';

  var docEl = document.documentElement;

  // Return the currently applied theme, defaulting to "light" when the
  // attribute is missing or holds an unrecognized value.
  function currentTheme() {
    var theme = docEl.dataset.theme;
    return VALID_THEMES.indexOf(theme) !== -1 ? theme : 'light';
  }

  function nextTheme(theme) {
    return theme === 'dark' ? 'light' : 'dark';
  }

  // Persist the chosen theme in a long-lived, JS-readable cookie.
  // Not HttpOnly (JS must read it in theme-init.js); SameSite=Lax; the
  // Secure attribute is added on HTTPS origins so the cookie is only sent
  // over secure transport where available.
  function persistTheme(theme) {
    try {
      var cookie =
        COOKIE_NAME +
        '=' +
        encodeURIComponent(theme) +
        '; Max-Age=' +
        COOKIE_MAX_AGE +
        '; Path=/; SameSite=Lax';
      if (window.location && window.location.protocol === 'https:') {
        cookie += '; Secure';
      }
      document.cookie = cookie;
      return true;
    } catch (e) {
      // If the cookie cannot be written, persistence is unavailable.
      return false;
    }
  }

  // Feature-detect whether CSS color transitions can be applied. When
  // transitions are unsupported, the theme change is declined rather than
  // completed instantaneously (Requirement 2.5).
  function transitionsSupported() {
    try {
      if (
        typeof window.CSS === 'object' &&
        window.CSS &&
        typeof window.CSS.supports === 'function'
      ) {
        return window.CSS.supports('transition', 'color 200ms');
      }
    } catch (e) {
      // Fall through to the style-property probe below.
    }
    // Fallback probe: check for the `transition` property on an element's
    // inline style object.
    try {
      return 'transition' in docEl.style;
    } catch (e2) {
      return false;
    }
  }

  // Apply and persist a theme change. Returns true when the change was
  // completed, false when it was declined (e.g., transitions unsupported).
  function applyTheme(theme) {
    if (VALID_THEMES.indexOf(theme) === -1) {
      return false;
    }
    // Requirement 2.5: if smooth transitions are unavailable, do not
    // complete the change rather than flashing instantaneously.
    if (!transitionsSupported()) {
      return false;
    }
    docEl.dataset.theme = theme;
    persistTheme(theme);
    return true;
  }

  function toggleTheme() {
    return applyTheme(nextTheme(currentTheme()));
  }

  function onToggleActivated(event) {
    if (event) {
      event.preventDefault();
    }
    // Flip the theme in place — no navigation (Requirement 2.2).
    toggleTheme();
  }

  function wireToggles() {
    var toggles = document.querySelectorAll(TOGGLE_SELECTOR);
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener('click', onToggleActivated);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireToggles);
  } else {
    wireToggles();
  }

  // Expose a minimal API for other scripts and behavior tests (task 11.3).
  window.EditorialTheme = {
    current: currentTheme,
    toggle: toggleTheme,
    apply: applyTheme,
    transitionsSupported: transitionsSupported
  };
})();
