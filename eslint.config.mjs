// Dev tooling only. Enforces ES5 syntax (parse errors on let/const, arrow
// functions, template literals, classes, etc.) for the TV runtime sources.
// See CLAUDE.md and docs/development.md for why app/ stays ES5.
import js from '@eslint/js';

export default [
  js.configs.recommended,
  {
    files: ['app/**/*.js'],
    languageOptions: {
      ecmaVersion: 5,
      sourceType: 'script',
      globals: {
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        XMLHttpRequest: 'readonly',
        DOMException: 'readonly',
        Image: 'readonly',
        console: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        requestAnimationFrame: 'readonly',
        cancelAnimationFrame: 'readonly',
        tizen: 'readonly',
        Promise: 'readonly',
        // Globals shared across separate <script> tags loaded by app/index.html, not modules.
        // HOUSE_API_BASE is declared with `var` in its own config file and read via window.*
        // elsewhere, so it doesn't need (and must not have) a global entry here.
        FrameDevice: 'readonly',
        HouseAPI: 'readonly'
      }
    },
    rules: {
      'no-unused-vars': 'warn'
    }
  }
];
