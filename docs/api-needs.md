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

Why: positions the warm↔cool slider in White mode. The UI assumes a
2200-6500K range (common for consumer bulbs) with no explicit bounds field
from the server yet - if real bulbs need a narrower/wider range, house-api
should also send `tiles.data[].color_temp_range: {min, max}`, not
implemented here since the fixtures didn't need it.

Compute: house-api, mirroring the light's actual colour temperature.

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

## Dropped: remote colour-key (F1-F4) mapping

The house-api-ui brief's Phase 1 item 6 ("map the colour keys to F1-F4 in
the preview, matching the TV's ColorF0Red..ColorF3Blue handling") didn't
correspond to anything in the codebase - no existing remote-color-key
handling in `app/device.js` or `app/main.js`, no `tizen:privilege` for it
in `config.xml`, and no feature in this house-api UI plan that would use
a remote's colour buttons. Raised at the end of Phase 1; confirmed out of
scope and dropped entirely, not implemented.
