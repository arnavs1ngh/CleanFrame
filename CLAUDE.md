# CLAUDE.md

Project-wide instructions live in `AGENTS.md` - read that first. This file
covers the house-api-ui dev tooling added on the `house-api-ui` branch.

## ES5 rule

`app/**/*.js` must stay ES5-compatible (the TV's engine; see
`docs/development.md`). `eslint.config.mjs` parses those files with
`ecmaVersion: 5, sourceType: 'script'`, wired into `npm run check` via
`scripts/eslint-report.mjs`. An ES6+ syntax regression (let/const, arrow
functions, classes, template literals, ...) is a fatal parse error and
fails the check. Everything else ESLint reports against the existing
source is printed as a non-blocking finding - fixing pre-existing issues
is out of scope for unrelated work; see `docs/api-needs.md` for the one
worth following up (`app/main.js`'s undefined `live(...)` call).

## house-api is local-only mock data right now

house-api doesn't exist yet. `app/house-api-config.js` (gitignored) will
hold `HOUSE_API_BASE`, with `app/house-api-config.example.js` as the
committed template - same pattern as `ha-config.js`. If that file is
missing, the house features stay hidden and the app works exactly as it
does today.

### Fixtures

`dev/fixtures/v1/*.json` holds one `/v1/home` response per scenario:
`normal`, `quiet-day`, `busy-week`, `long-titles`, `all-day-and-multiday`,
`ha-down`, `weather-missing`, `many-tiles`, `night`,
`stale-everything`. These are the house-api spec in progress - when the
UI needs a field, behaviour or limit not in the starting shape, add it to
the fixtures and log it in `docs/api-needs.md`.

### Mock server

`dev/mock.py` is DEV-ONLY: it's imported only by `scripts/preview.py`,
never by anything under `app/`. Routes, served by `npm run dev`:

- `GET /mock/v1/home?scenario=<name>&delay=<ms>&fail=<0|1>` - serves a
  fixture, supports `ETag`/`If-None-Match` -> 304, and `fail=1` returns a
  500.
- `POST /mock/v1/actions/{tile-id}?scenario=<name>&delay=<ms>&fail=<0|1>`
  - with no body: flips a toggle tile's in-memory state (reset on preview
    restart). With a JSON body (`brightness`/`color_mode`/`rgb`/
    `color_temp_k`): merges those fields onto the tile instead of toggling.
    Returns `{ ok, tile }`. `fail=1` returns `{ ok: false, tile }` without
    applying anything.

When no real `app/house-api-config.js` is present, `npm run dev` serves a
dev-only default `house-api-config.js` pointing `HOUSE_API_BASE` at
`/mock`, so the preview works against mock data with zero setup.

### Live reload

`npm run dev` injects a small poller into the served `index.html` (the
file on disk is never touched) that reloads the page when anything under
`app/` or `dev/fixtures/` changes. Automated Playwright tooling
(`check-browser.mjs`, `shots.mjs`, `build-icon-metrics.mjs`, all via
`scripts/browser.mjs`) sets `CLEANFRAME_NO_LIVE_RELOAD=1` so the long-poll
doesn't block `networkidle` waits - don't remove that env var without
checking those still pass.

### `npm run shots`

Screenshots every fixture scenario in List and Dock, at 1920x1080 and
1280x720, plus a handful of named focus states, into gitignored
`.local/shots/`, plus a single composited `contact-sheet.png`. It
intercepts `**/v1/home*` at the Playwright level with the raw fixture
body, so it doesn't depend on how `app/house-api.js` ends up building its
request URL. Run it after any change to the weather strip, calendar panel or the
Lights control/popup and review the contact sheet before calling a UI
piece done - see the workflow in the house-api-ui task description
(`normal.json` first, then every scenario, especially `long-titles`,
`busy-week`, `ha-down` and `night`).

## Lights control (replaces the old webhook integration)

The old direct-webhook Home Assistant integration (`app/ha.js`,
`app/ha-config.js`, the Settings-housed "Jellyfin light sync" panel) is
gone - fully removed, including its `config.xml` `<access>`/`internet`
entries. Everything now goes through house-api's `tiles` data; see
`docs/home-assistant.md` for the full history/status.

- The Home-row control represents whichever tile has `quick: true` (see
  `docs/api-needs.md`) - on-off state and icon colour come from that tile.
  The label itself is static ("Light", `UTIL.light[0]`) - it used to show
  the tile name and a Sending/Done/failed status, but a changing label
  shifted the button's own width, which read as the whole row jittering.
- Short press toggles immediately, same as before. Holding OK past
  `LIGHT_LONGPRESS_MS` (~500ms, see the keydown handler near the bottom of
  `app/main.js`) *additionally* opens a small brightness/colour popup
  directly on the live Home scene, not a full sheet screen (see
  `app/style.css`'s `.at-light` overrides) - it never delays or cancels
  the short-press toggle underneath it. Only opens for a tile with
  `brightness` and/or `color_mode` present. In List it's positioned
  dynamically (`syncLightPopupGeometry`) directly left of the control,
  vertically centred on it, with no card background - legibility matches
  the caption's own ink treatment for that zone.
- No auto-commit: adjustments only touch local state (`t.dirty` drives a
  subtle opacity cue, nothing else) until OK explicitly sends the
  accumulated change as a single `POST /v1/actions/{id}` call and closes
  the popup. Back cancels and closes without sending anything - same
  apply-on-OK/cancel-on-Back pairing Settings already uses.
- `scripts/check-browser.mjs`'s `page()` has a `houseApi` option (a tile
  object, or an array of tiles) that mocks `house-api-config.js` +
  `/v1/home` + `/v1/actions/*` at the Playwright route level - see the
  "Lights control" test section for the pattern (`current.__houseApi.
  actionCalls` records every call, matched to the right tile by id).

## Automation settings row

A second, independent tile slot: whichever tile has `settings: true` (see
`docs/api-needs.md`) shows as a plain on/off row under Settings, between
"Apps on Home" and "Samsung" (`settingsRows()`/`automationTile()` in
`app/main.js`). Replaces the old hardcoded "Jellyfin light sync" webhook
toggle - the row's name and on/off value both come from the tile now, so
it actually reflects whether the automation is on, instead of firing
blind. OK toggles it in place (`automationToggle()`, same
`POST /v1/actions/{id}` with no body as the Lights control's short
press) and stays on the Settings list - no separate panel, since it's
just one boolean.

## Never package dev code

`dev/` (the mock server and fixtures) must never end up in a built
widget, and neither must `app/house-api-config.example.js`. `npm run
check` builds a real (unsigned, no credentials) dry-run widget via
`write_widget_archive` and asserts neither is in it - see `scripts/check.py`.

## API needs log

`docs/api-needs.md` is the running list of fields/behaviours/limits the
UI needs beyond the starting `/v1/home` shape, why, and whether house-api
or the TV should compute them. It and the final `dev/fixtures/v1/*.json`
are the house-api spec handed off at the end of this task.
