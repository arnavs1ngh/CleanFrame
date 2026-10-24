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
polling/backoff/cache/actions), the weather strip, and the always-visible
calendar panel - all exercising `weather` and `calendar` from the shape
below. **Not reached:** the `tiles` section has no consuming UI yet (the
old webhook-based Home Assistant control/panel in `app/ha.js` and
`app/main.js` is still in place, untouched) and the real bundled-icon
pipeline was never built - weather icons are still the inline placeholder
set from Phase 3 piece 1. See the hand-off summary for what's left.

## Fields added beyond the starting shape

### `calendar.data.days[].events[].redacted` (boolean)

Example: `{ "time": "19:30", "end": "21:00", "all_day": false, "title": "Busy", "calendar": "House", "redacted": true }`

Why: the calendar visibility policy is undecided, and the UI must handle both
full event titles and redacted ones (see `dev/fixtures/v1/redacted.json`).
Detecting "redacted" by matching `title === "Busy"` would be fragile (a real
event could legitimately be titled "Busy") and would silently break if the
redaction placeholder text ever changes. An explicit flag lets the UI style a
redacted event distinctly (e.g. muted/italic) without guessing from text.

Compute: house-api. It's the one that knows which calendar's events are
being redacted and why; the TV only needs to know whether to render the
muted treatment.

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

## Dropped: remote colour-key (F1-F4) mapping

The house-api-ui brief's Phase 1 item 6 ("map the colour keys to F1-F4 in
the preview, matching the TV's ColorF0Red..ColorF3Blue handling") didn't
correspond to anything in the codebase - no existing remote-color-key
handling in `app/device.js` or `app/main.js`, no `tizen:privilege` for it
in `config.xml`, and no feature in this house-api UI plan that would use
a remote's colour buttons. Raised at the end of Phase 1; confirmed out of
scope and dropped entirely, not implemented.
