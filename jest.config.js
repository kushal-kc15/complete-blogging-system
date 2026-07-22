// Jest configuration for the Editorial Revamp front-end behavior tests.
//
// These tests exercise the origin-local theme scripts (theme-init.js and
// theme-toggle.js) in a jsdom environment, mocking matchMedia, cookies, and
// CSS.supports as needed (spec task 11.3, Requirements 2.2, 2.3, 2.4, 2.5).
module.exports = {
  testEnvironment: 'jsdom',
  // A concrete origin is required so document.cookie round-trips work.
  testEnvironmentOptions: { url: 'http://localhost/' },
  // Only run the front-end behavior tests; keep Python venv packages out.
  roots: ['<rootDir>/blog_main/static/js'],
  testMatch: ['**/__tests__/**/*.test.js'],
  modulePathIgnorePatterns: ['<rootDir>/venv/'],
  clearMocks: true,
};
