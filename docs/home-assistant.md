# Home Assistant integration status

This file used to document a direct webhook integration
(`app/ha.js`/`app/ha-config.js`, a "Lights" toggle firing Home Assistant
webhooks, and a "Jellyfin light sync" panel under Settings). That approach
was removed on the `house-api-ui` branch and replaced with the design
below. If you're looking for the old webhook history, it's in this branch's
git log up to the "Phase 3, piece 2" commits.

## What's done

Home Assistant (or any house backend) is now reached only through house-api
- see `docs/api-needs.md` and `dev/fixtures/v1/*.json` for the `/v1/home`
and `/v1/actions/{id}` shape. There is no direct webhook/XHR call to Home
Assistant from the TV anywhere in `app/`.

- A "Lights" quick-access control sits next to All apps/Settings on Home,
  same `.u` styling as before. It represents whichever tile in
  `tiles.data[]` has `quick: true` (exactly one, by convention) - its label
  and icon come from that tile, not a hardcoded string. Hidden entirely
  when `HouseAPI.configured()` is false, or shown generically ("Lights")
  if configured but no quick tile exists yet.
- Short press: toggles the tile (`POST /v1/actions/{id}` with no body),
  immediately, same feel as before - sending/done/failed feedback shows
  inline and reverts after ~2s. Repeat presses while in flight are ignored.
- Holding OK past ~500ms *additionally* opens a brightness/colour popup
  (`app/main.js`'s `V.light`/`FRAMES.light`/`FILLS.light`) - it does not
  replace or delay the short-press toggle. Only opens for a tile that
  actually has `brightness` and/or `color_mode` in its data.
- The popup: a brightness slider, a Colour/White mode toggle, and either a
  10-swatch colour grid or a warm↔cool temperature slider depending on
  mode. Adjustments preview locally and debounce into a single
  `POST /v1/actions/{id}` call ~700ms after the last change (not one call
  per keypress), carrying whatever changed since the popup opened. Back
  flushes any pending change immediately rather than waiting out the
  debounce.
- Browser coverage: `npm run check` and `CLEANFRAME_PUBLIC_FONTS=1 npm run
  check:browser` both pass, including a "Lights control" section covering
  hidden-without-config, the tile-driven label, short-press toggle and its
  in-flight guard, long-press opening the popup, and the debounce/flush
  behaviour. This mocks house-api at the Playwright route level (the
  `houseApi` option on `page()` in `scripts/check-browser.mjs`) - it never
  touches a real network and proves nothing about reachability from the
  actual TV, or about a real house-api backend's behaviour.

## What still needs real-backend testing

Nothing here has been exercised against a real house-api backend or on the
TV itself - only against the dev mock and the Playwright route-level mock.
house-api itself doesn't exist yet. Before relying on this:

- house-api needs to be built to the shape in `docs/api-needs.md` and
  `dev/fixtures/v1/*.json`, including the `quick`, `brightness`,
  `color_mode`, `rgb` and `color_temp_k` tile fields and the
  `POST /v1/actions/{id}` request body this round added.
- Confirm real device latency for brightness/colour pushes - the debounce
  window (~700ms) and the 4s action timeout were tuned for responsiveness
  against the dev mock, not a real backend or a real light's response time.
- Confirm the TV can reach house-api's address from its own network
  context (not just this Mac's).

## What the TV-install round must add

These were explicitly deferred from this round and are not done - see the
house-api-ui hand-off summary for the full list:

1. **`config.xml` privileges**: an `<access>` entry scoped to house-api's
   own origin (not a wildcard) plus `http://tizen.org/privilege/internet`.
   Don't add these until the real `house-api-config.js` base URL is known.
   (The old Home Assistant webhook's `<access>`/`internet` entries were
   removed along with `app/ha.js` - they're not reused for house-api.)
2. **Packaging check for `house-api-config.js`**: `scripts/check.py`
   currently lets it be missing, because it's optional pre-wiring. Once a
   real one is supplied for an actual device install, tighten this so
   packaging fails loudly if it's absent instead of silently shipping a
   widget with house features hidden.
3. **CORS testing on the TV**: confirm house-api accepts the widget's own
   origin and that requests actually succeed from the TV's WebKit/Chromium
   engine, not just in desktop preview.
4. Real-device tests for polling cadence, visibility pause/resume (another
   app taking the foreground), and the action debounce under real network
   conditions.

## Where things stand

The webhook approach (branch `ha-controls`, merged to `main`) is fully
retired. The house-api-backed replacement was built on `house-api-ui`;
see that branch's commit history for the design iteration, including the
mid-build redirects (control+panel → always-visible calendar; swatch-grid
colour picker; debounced auto-commit instead of explicit OK).
`docs/agent-tv-setup-guide.md` and `docs/for-agents.md` cover the install
round itself once house-api exists and the above is ready;
`.local/setup-record.md` (gitignored, local to this Mac) has the
identity/certificate/device details from the install already completed for
this TV.
