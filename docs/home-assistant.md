# Home Assistant integration status

Read this before finishing the wiring. It records what's built, what's been
verified, and what the next stage (device install) still needs to add.

## What's done

- `app/ha.js`: fire-and-forget webhook POSTs via `XMLHttpRequest`, ES5-only,
  4s client-side timeout. No body, no custom headers, no live state read back.
- A "Lights" toggle control sits next to All apps/Settings on Home (reuses
  the existing `.u` control styling). Each press fires the opposite of its
  locally tracked on/off state; feedback (sending/done/the error message)
  shows inline on the control and reverts after ~2s. Repeat presses on an
  in-flight action are ignored.
- A "Jellyfin light sync" On/Off panel lives under Settings, reusing the
  panel/sheet system (`V.ha`/`FRAMES.ha`/`FILLS.ha` in `app/main.js`).
- Both the control and the Settings row are fully hidden when
  `HomeAssistant.configured()` is false - no broken buttons without config.
- `app/ha-config.example.js` documents the required shape (`base` plus four
  webhook IDs: `lightsOn`, `lightsOff`, `jellyfinSyncOn`, `jellyfinSyncOff`).
  The real `app/ha-config.js` is gitignored and not present in this repo.
- Browser coverage: `npm run check` and `CLEANFRAME_PUBLIC_FONTS=1 npm run
  check:browser` both pass, including a "Home Assistant control" section
  covering hidden-without-config, focus, the toggle firing the right webhook
  per press, the in-flight guard, and sending/failed/timeout feedback. This
  mocks `XMLHttpRequest` at the Playwright-harness level (see `ha` option on
  `installHarness` in `scripts/check-browser.mjs`) - it never touches a real
  network and proves nothing about reachability from the actual TV.

## What still needs real-HA testing

Nothing here has been exercised against a real Home Assistant instance or on
the TV itself - only against a browser-based mock. Before relying on it:

- Confirm the four webhooks actually exist in Home Assistant and do what
  their names say.
- Confirm the TV can reach Home Assistant's address at all from its own
  network context (not just this Mac's).
- Confirm actual request latency/behaviour against the real server - the 4s
  client timeout was tuned for responsiveness, not measured against a real
  HA response time.

## What the TV-install round must add

These were explicitly deferred from this round and are not done:

1. **`config.xml` privileges**: add `http://tizen.org/privilege/internet`
   and an `<access>` entry scoped to Home Assistant's own origin (its LAN
   `http://<HA_LAN_IP>:8123`, not a wildcard). Don't add these until the real
   `ha-config.js` base URL is known.
2. **Packaging check for `ha-config.js`**: `scripts/check.py` currently lets
   `ha-config.js` be missing (`continue` on that reference) because it's
   optional pre-wiring. Once a real `ha-config.js` is supplied for an actual
   device install, tighten this so packaging fails loudly if it's absent
   instead of silently shipping a widget with Home Assistant hidden.
3. **CORS testing on the TV**: the widget's own origin
   (`https://local.mayton-home/app`, from `config.xml`'s widget `id`) will
   make real cross-origin requests to Home Assistant from the TV's WebKit/
   Chromium engine, not a desktop browser. Confirm Home Assistant accepts
   that origin (or whatever CORS/trusted-network configuration is needed)
   and that the request actually succeeds on-device, not just in preview.
4. Copy the real `app/ha-config.js` from `app/ha-config.example.js`'s shape
   before packaging - it's gitignored, so each machine needs its own copy.

## Where things stand

Branch `ha-controls` (now merged to `main`) has the full commit history of
this work, including the design iteration. `docs/agent-tv-setup-guide.md`
and `docs/for-agents.md` cover the install round itself once the above is
ready; `.local/setup-record.md` (gitignored, local to this Mac) has the
identity/certificate/device details from the install already completed for
this TV.
