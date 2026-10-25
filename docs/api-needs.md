# house-api needs log

house-api doesn't exist yet; this UI build defines what it must return. The
starting `/v1/home` shape lives in the house-api-ui task description and in
`dev/fixtures/v1/normal.json`. Whenever the UI needs a field, behaviour or
limit beyond that starting shape, it gets added to the fixtures *and* logged
here: field, example, why the UI needs it, and whether house-api or the TV
should compute it. This file plus the final `dev/fixtures/v1/*.json` are the
house-api spec at the end of this round.

## Status at the end of this round

Built and verified against the mock: client plumbing (`app/house-api.js`,
polling/backoff/cache/actions, now with a request body on
`POST /v1/actions/{id}`), the weather strip, the always-visible calendar
panel, and a Lights quick-access control with a brightness/colour popup -
exercising `weather`, `calendar` and now `tiles` from the shape below. The
old webhook-based Home Assistant integration (`app/ha.js`,
`app/ha-config.js`) was fully removed, including its `config.xml`
`<access>`/`internet` entries - see `docs/home-assistant.md`. **Not
reached:** the real bundled-icon pipeline - weather and tile icons are
still the inline placeholder set from Phase 3 piece 1.

## Fields added beyond the starting shape

### `calendar.data.days[].events[].span` (object, optional)

Example: `{ "start_date": "2026-10-24", "end_date": "2026-11-02" }`

Why: an all-day event that runs across several days (see
`dev/fixtures/v1/all-day-and-multiday.json`) needs to look like one
continuing event, not like unrelated single-day all-day events repeated on
each day. The UI needs the real start/end dates to know whether a given
day is the start, a middle day, or the end of the span, so it can render a
continuation treatment (e.g. no leading/trailing rounding on middle days)
instead of a duplicate pill per day.

Compute: house-api. It already resolves the source calendar's multi-day
event boundaries; the TV just needs the two dates.

### `tiles.data[].quick` (boolean, optional)

Example: `{ "id": "living-lights", "label": "Living room", ..., "quick": true }`

Why: the Home-row "Lights" control is a single quick-access item, not the
full tile list - it needs to know *which* tile to represent without the UI
guessing ("first toggle tile" breaks the moment there's more than one
light; see `dev/fixtures/v1/many-tiles.json`, which has six). Set on
exactly one tile. If none is flagged, the control still shows (when
house-api is configured) but generically, with no tile behind it.

Compute: house-api. It (or whoever configures it) decides which single
device deserves one-press access from Home; the TV just renders whichever
tile has the flag.

### `tiles.data[].settings` (boolean, optional)

Example: `{ "id": "movie-time-lights", "label": "Movie time lights", "icon": "bulb", "kind": "toggle", "state": "on", "settings": true }`

Why: same idea as `quick`, for a second slot - a single on/off automation
shown as a row under Settings (replaces the old hardcoded "Jellyfin light
sync" webhook toggle, which fired blind with no idea whether the
automation was actually on). The label shown is the tile's own `label`,
not a hardcoded string - name it to match the automation as it's actually
named in house-api/Home Assistant. Set on at most one tile for now (the
UI only renders one settings-housed automation row); pressing OK toggles
it immediately and the row's value updates from the real `state` the
server returns, same `POST /v1/actions/{id}` with no body as any other
toggle - no separate endpoint or panel needed.

Compute: house-api. The TV just renders whichever tile has the flag,
exactly like `quick`.

### `tiles.data[].home` (boolean, optional)

Example: `{ "id": "fireplace", "label": "Fireplace", "icon": "scene", "kind": "button", "state": null, "home": true }`

Why: a third slot, independent of `quick` and `settings` (a tile has at
most one of the three) - gives any number of one-shot automations their
own icon directly on the Home row, next to the Lights control, rather
than needing a dedicated flag per automation. Unlike `quick`/`settings`,
more than one tile may have it; the TV renders one icon per flagged tile,
in whatever order they appear in `tiles.data`. No icon shows at all when
no tile has the flag. The label shown is the tile's own `label`, not a
hardcoded string, same reasoning as `settings`. A `home` tile's `state`
is expected to be `null` (a one-shot press, not a toggle) - the TV never
renders on/off for it regardless of `kind`. Pressing it sends
`POST /v1/actions/{id}` with no body, same as any other plain press;
repeat presses are ignored while the request is in flight, and for about
15 seconds after a successful one (house-api itself has no further state
to report back for a fireplace press - `ok: true` only means Home
Assistant accepted it, not that anything downstream, like the YouTube
video it starts, has actually happened yet).

Compute: house-api. The TV just renders whichever tiles have the flag,
same pattern as `quick`/`settings`.

### `tiles.data[].brightness` (number 0-100, optional)

Example: `{ "brightness": 72 }`

Why: the Lights control's long-press popup needs a dimmable tile's current
level to show a meaningful slider position, and to know a tile *is*
dimmable at all (its absence means no brightness row).

Compute: TV renders the slider; house-api supplies the current value and
must accept it back in the `POST /v1/actions/{id}` body (see below).

### `tiles.data[].color_mode` (`"color"` | `"white"`, optional)

Example: `{ "color_mode": "white" }`

Why: a colour-capable light is in exactly one of two states at a time -
showing a set RGB colour, or a white colour-temperature. The popup needs
to know which to default to, and which of `rgb`/`color_temp_k` is
currently "live", rather than guessing from which field happens to be
present. Its absence means the tile has no colour control at all (only
`brightness`, or neither - a plain toggle).

Compute: house-api. It reflects whatever mode the light is actually in.

### `tiles.data[].rgb` (`{r,g,b}`, 0-255 each, optional)

Example: `{ "rgb": { "r": 255, "g": 196, "b": 120 } }`

Why: lets the popup highlight the current colour among its swatch presets
(and carries the last-set colour through a mode switch, so flipping back
to Colour from White doesn't lose it).

Compute: house-api, mirroring the light's actual last-set colour.

### `tiles.data[].color_temp_k` (number, Kelvin, optional)

Example: `{ "color_temp_k": 4000 }`

Why: positions the warm↔cool slider in White mode.

Compute: house-api, mirroring the light's actual colour temperature.

### `tiles.data[].color_temp_range` (`{min, max}`, Kelvin, optional)

Example: `{ "color_temp_range": { "min": 1801, "max": 6535 } }`

Why: real bulbs vary - the living room bulb is 1801-6535K, not the
2200-6500K this UI originally assumed as a generic default. The slider's
bounds and the value sent back both need to match the specific tile's
actual range, or an adjustment could ask for a colour temperature the
bulb can't produce. Absent on a tile, the UI falls back to its generic
2200-6500K default.

Compute: house-api, from whatever the light reports as its own capability.

### Two behaviours worth stating explicitly (no new fields, just confirming)

- An off light still reports its last brightness/colour in its tile, never
  `brightness: 0` or a cleared `rgb`/`color_temp_k` - the popup needs real
  values to show even when the light is off, so a press-to-adjust doesn't
  start from a meaningless zero.
- An entity Home Assistant can't currently see (unavailable, automation
  missing, etc.) is simply omitted from `tiles.data` rather than included
  with some "unavailable" state. The UI's two reactions to an omitted tile
  differ and both are intentional, not a bug: a missing `settings` tile
  hides that Settings row entirely; a missing `quick` tile leaves the
  Home-row Light control visible (since it's gated on house-api being
  configured at all, not on a specific tile existing) but inert - pressing
  it does nothing, since `quickTile()` returns null. No new state value is
  needed for either case.

### `POST /v1/actions/{id}` now takes an optional JSON body

Example: `{ "brightness": 72, "color_mode": "color", "rgb": { "r": 255, "g": 196, "b": 120 } }`

Why: the original shape was "run an allowlisted action, no params" (fire,
like the old webhooks). Brightness/colour adjustment needs to carry the
new value. The UI accumulates brightness/colour/temperature adjustments
locally and sends them as a single request only when the user presses OK
(which also closes the popup) - not one request per slider tick, and not
on a timer either; Back cancels and sends nothing. A plain toggle/scene/
button press still sends no body at all, same as before. The mock
(`dev/mock.py`) merges whichever of `brightness`/`color_mode`/`rgb`/
`color_temp_k` are present onto the tile and returns it; a tile with no
body sent still toggles its `state` as before.

Compute: house-api must accept a partial update (only the fields that
changed) and return the tile's full resulting state in `{ ok, tile }`, not
require every field on every call.

A `kind: "button"` tile (e.g. `home`-flagged automations like Fireplace)
is the opposite case: it takes no body at all, and house-api is expected
to reject one with `400` rather than silently ignore it, since there's
nothing for it to mean. The TV never sends one for these. The mock
replicates this: a `kind: "button"` tile's action 400s if a body is
present, regardless of its contents.

## Icon vocabulary (provisional, not locked)

The fixtures currently use this icon-name vocabulary. The weather half is
live (rendered by the weather strip, as inline placeholder SVGs, not the
bundled-file pipeline). The tiles half is unconsumed - logged here as the
working vocabulary for whoever builds the Home Assistant panel next, not
a finalised contract. Whatever ships, house-api must only send names the
TV recognises, and unknown names must fall back gracefully rather than
breaking the tile/weather row.

- Weather: `clear-day`, `clear-night`, `partly-cloudy-day`,
  `partly-cloudy-night`, `cloudy`, `cloudy-rain`, `rain`, `thunderstorm`,
  `snow`, `fog`, `wind`
- Tiles: `bulb`, `lock`, `thermostat`, `blinds`, `fan`, `plug`, `tv`,
  `speaker`, `camera`, `scene`

## Dropped: redacted calendar events

Earlier drafts had `calendar.data.days[].events[].redacted` (boolean) and a
`redacted.json` fixture scenario, for a calendar-visibility policy that
doesn't exist yet - no decision has been made about whether or how personal
events get hidden from a shared screen. Speculative complexity for a
problem that isn't real yet: dropped from the UI, the fixtures and this
spec. If that policy gets decided later, house-api can just send whatever
`title` it wants the TV to show (including a placeholder like "Busy") -
the UI renders event titles as plain text regardless of their source, so
no client-side redaction awareness is needed either way.

## Remote colour-key (Red/Green/Yellow/Blue) shortcut

Originally raised in the house-api-ui brief's Phase 1 and dropped as out
of scope - no feature used the remote's colour buttons yet. Implemented
later once the Lights control existed to use them: from Home (not inside
the long-press popup), Red/Green/Yellow/Blue set the quick-access light
tile directly to one of the swatch presets (`LIGHT_SWATCHES` indices 0/4/
3/6 - the closest hue to each button's own colour) and commit immediately,
same `state:'on'`/`color_mode:'color'`/`rgb` body shape as any other
colour commit, preserving the tile's current `brightness`. A tile with no
`color_mode` at all (no colour capability) makes these a no-op, same as
the popup's own guard.

`FrameDevice.registerColorKeys()` (`app/device.js`) calls
`tizen.tvinputdevice.registerKey('ColorF0Red' | 'ColorF1Green' |
'ColorF2Yellow' | 'ColorF3Blue')` once at startup - undocumented in this
repo until now, but these are Tizen's standard registerable key names,
delivered as keyCodes 403/404/405/406 (`KEYS` in `app/main.js`). Not
verified on the real TV yet - register against the actual `tv.inputdevice`
privilege grant and confirm the physical buttons actually deliver these
codes.
