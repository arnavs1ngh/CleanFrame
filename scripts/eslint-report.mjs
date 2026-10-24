// Wired into `npm run check`. ESLint parses app/**/*.js as ES5 script code
// (see eslint.config.mjs), so an ES6+ syntax regression (let/const, arrow
// functions, classes, template literals, ...) shows up as a fatal parse
// error and fails the check - that's the actual TV-compatibility gate.
//
// Everything else ESLint reports (eslint:recommended findings against the
// existing source) is printed as a non-blocking report: this task is not
// here to fix unrelated pre-existing issues in app/, only to surface them.
import { ESLint } from 'eslint';

const eslint = new ESLint();
const results = await eslint.lintFiles(['app/**/*.js']);
const formatter = await eslint.loadFormatter('stylish');
const output = await formatter.format(results);
if (output.trim()) console.log(output);

const fatal = results.reduce((n, r) => n + r.messages.filter(m => m.fatal).length, 0);
const problems = results.reduce((n, r) => n + r.messages.length, 0);

if (fatal > 0) {
  console.error(fatal + ' fatal parse error(s): app/**/*.js is not ES5-compatible.');
  process.exit(1);
}
if (problems > 0) {
  console.log(problems + ' ESLint finding(s) against existing app/ source (non-blocking; see docs/api-needs.md).');
} else {
  console.log('ESLint: app/**/*.js parses as ES5 with no findings.');
}
