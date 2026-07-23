/*
 * Test helpers for the Editorial Revamp theme-script behavior tests.
 *
 * The scripts under test (theme-init.js, theme-toggle.js) are origin-local,
 * non-module IIFEs that operate directly on `window`/`document`. To exercise
 * them we read the real source files and evaluate them in the jsdom global
 * scope via `window.eval`, so they mutate the same document/window the test
 * observes and (for theme-toggle.js) expose `window.EditorialTheme`.
 */
const fs = require('fs');
const path = require('path');

// The scripts live one directory up from this __tests__ folder.
const JS_DIR = path.resolve(__dirname, '..');

// Read and execute a theme script in the jsdom global scope.
function loadScript(filename) {
  const code = fs.readFileSync(path.join(JS_DIR, filename), 'utf8');
  // Indirect eval via window.eval runs the code in the window's global scope.
  window.eval(code);
}

// Expire every cookie currently set on the document.
function clearCookies() {
  const existing = document.cookie ? document.cookie.split(';') : [];
  existing.forEach((entry) => {
    const name = entry.split('=')[0].trim();
    if (name) {
      document.cookie = name + '=; Max-Age=0; Path=/';
    }
  });
}

// Install a matchMedia mock reflecting the given OS/browser color scheme.
//   scheme = 'dark'  -> prefers-color-scheme: dark matches
//   scheme = 'light' -> prefers-color-scheme: light matches
//   scheme = null    -> matchMedia is unsupported (removed from window)
function mockMatchMedia(scheme) {
  if (scheme === null) {
    delete window.matchMedia;
    return;
  }
  window.matchMedia = (query) => ({
    matches: query.indexOf('prefers-color-scheme: ' + scheme) !== -1,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

// Install a CSS.supports mock reporting whether transitions are supported.
function mockCSSSupports(supported) {
  window.CSS = { supports: () => supported };
}

// Reset the shared document/window state between tests.
function resetEnvironment() {
  clearCookies();
  document.documentElement.removeAttribute('data-theme');
  document.body.innerHTML = '';
  delete window.matchMedia;
  delete window.CSS;
  delete window.EditorialTheme;
}

module.exports = {
  JS_DIR,
  loadScript,
  clearCookies,
  mockMatchMedia,
  mockCSSSupports,
  resetEnvironment,
};
