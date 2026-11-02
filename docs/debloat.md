# Optional debloat (ads, Bixby/voice, context services, sidebar, TV Plus)

Inspired by [quiet-tizen](https://github.com/jss8649/quiet-tizen)'s cleanup toolkit, adapted for
this TV. Separate from CleanFrame's own app and the native-Home experiment (`docs/tv-status.md`,
`scripts/native-home/`) - this disables stock Samsung services, not anything CleanFrame installs.

**Status: 84 candidates applied and verified disabled on the TV (2026-11-02).** The mechanism was
proven against one app first (`yL49PNFmjW.service`/PromotionService - see "What's proven" below),
generalised into reusable tooling (`plan.py`/`apply.py`/`restore.py`), run against the original 63
across `advertising`/`voice`/`context`/`sidebar`/`tvplus`/`smart-extras`/`telemetry`, then extended
twice more: 16 app IDs quiet-tizen's own profile covers that this list initially didn't (fetched
and cross-checked against their actual `profiles/*.json`, not just their README), plus 5 more
found by sweeping this TV's full ~500-app `applist` capture for retail-demo-mode and log-transmitter
patterns neither list had (`bloatware` group). Zero failures across all three rounds;
`app_onboot`/`app_autorestart` preserved exactly for every app that had either flag `true` to
begin with. Exact-value rollback baselines: `.local/debloat/plan/20261102-185552/baseline.json`
(the original 63) and `.local/debloat/plan/20261102-195727/baseline.json` (all 84) - see
"Rollback" below.

**Deliberately not pursued**: `ipa.service`, `contents-recognition-service.service`,
`org.tizen.tv.sp-kpi.service`, `data-service.service`, and 12 other systemd services quiet-tizen's
own tooling disables - all require root (quiet-tizen vendors a separate public exploit,
[chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root), confirmed working
against this TV's exact capability setup via a read-only compatibility check), which is an
explicit hard limit here. Even with root, quiet-tizen doesn't persist a disable for the four
telemetry services above specifically (`runtime_only_masks` in their profile, not `stop_markers`)
- masking them would need re-exploiting the TV on every reboot for a result that reverts anyway,
judged not worth it. See "Systemd services: investigated, not pursued" below.

**Still open, needs a decision**: five candidates found in the full-list sweep that are plausibly
unused but could be features you actually use - `samsung-cloud` (cross-device sync),
`nfc-daemon`/`nfc-monitor` (NFC tap-to-connect), `rdm.vx.dmhandler` (unclear if retail-only
device management), `coba.mobilebff` (likely a SmartThings/SmartView mobile-pairing bridge despite
"Sample App" in its display name). Not added to `profiles.json` - see "Lower-confidence candidates"
below.

## Why this needs its own validation, not quiet-tizen's values

quiet-tizen's TV (`UN75U8000FFXZA`, Tizen 9.0) is a different model and firmware from this one
(`UE55CU7100KXXU`, Tizen/platform_version 8.0 per `.local/setup-record.md`). Their own README is
explicit that their generalised scripts were "checked locally... not replayed end-to-end on a
second TV" even on hardware closer to their reference device than this one is. Two things carry
over and two don't:

- **Carries over**: the *category* of mechanism needed (`pkgcmd`/registry-field territory) and the
  exact field names (`package_app_info.app_disable`/`app_onboot`/`app_autorestart` - confirmed
  identical schema on this TV). Where this TV actually diverges from quiet-tizen's experience: they
  found `pkgcmd` activate/deactivate "did not reliably report or retain the intended state" on
  their build and dropped straight to raw SQL. On this TV, standard `pkgcmd -D`/`-A` worked
  cleanly and reliably - no SQL write was needed at all (see "What's proven" below). Worth trying
  the documented route first regardless, since not needing a raw registry write is strictly safer.
- **Doesn't carry over**: their specific app IDs, exact registry field values, and the ~51-app
  grouping. Candidates for *this* TV came from grepping `.local/qa/tv-applist.txt` (captured
  2026-10-23) against their category names - see `scripts/debloat/profiles.json`. Every entry is
  marked `verified: false` until confirmed present in a fresh snapshot.

## Candidate groups (`scripts/debloat/profiles.json`)

| Group | Count | Examples |
| --- | --- | --- |
| `advertising` | 11 | Ad Web Framework, Targeted Advertisment Service, Samsung Promotion, ACR engine, canalysis/adagent/pisa ad-tracking services |
| `voice` | 24 | Bixby (provisioning, context client, capsule viewer, wake engine, "Salute" - Bixby's internal codename), Alexa client/fullscreen app/wake engine, voice/TTS services |
| `context` | 6 | Context Aware Agent and its toast/grab-control/server-requester helpers, content-grab-service |
| `sidebar` | 1 | `com.samsung.tv.home.sidebar` |
| `tvplus` | 2 | TV Plus deeplinker and the app itself |
| `smart-extras` | 32 | SmartThings (app, hub, plugin platform, per-widget IoT cards), Samsung Health (app, view, mde service, daemon), Gaming Hub (app, daemon, service), ambient support/sound/FTE components, ad players, AOV dashboard |
| `telemetry` | 5 | samsung-analytics, contents-recognition-dbmgr, remote-service logging debug menu, emergency-log-transmitter, ep-log-manager |
| `bloatware` | 3 | Retail demo-mode player, USB sync demo GUI, unsolicited survey popup |

`smart-extras` and `telemetry` were added 2026-11-02 after comparing against
[jss8649/quiet-tizen](https://github.com/jss8649/quiet-tizen)'s own cleanup profile summary, which
covered both categories and this list didn't yet. The systemd-service caveat for `telemetry` is
covered in full in "Systemd services: investigated, not pursued" below.

A second pass the same day went further than the summary: fetched quiet-tizen's actual
`profiles/un75u8000ffxza-1300.9.json` (not just their README) and diffed it app-ID-by-app-ID
against ours, rather than just category names. 16 app IDs they cover that this list didn't -
`advertising` gained the ACR engine and canalysis/adagent/pisa ad-tracking services, `voice`
gained the full Alexa cluster (this TV ships Alexa alongside Bixby/Salute), `context` gained
`content-grab-service`, `smart-extras` gained Gaming Hub's daemon/service (separate from the
`gaminghub` app itself) and a second Samsung Health service. Each was checked against this TV's
own `applist` capture before adding - quiet-tizen's `AICompanion*`/`ai-discovery-*` cluster (6
apps) and their TV Plus package ID don't exist on this TV at all and were correctly left out, not
silently assumed present.

A third pass swept this TV's full ~500-app capture for patterns neither list had: `bloatware`
(retail demo-mode tools, an unsolicited survey popup) and two more `telemetry` entries
(`emergency-log-transmitter`, `ep-log-manager` - names that are telemetry-shaped on their face).
See "Lower-confidence candidates" below for five more the sweep found that weren't added.

## What's built so far

`scripts/debloat/snapshot.py` - **read-only**. Connects to the TV (same `.local/device.json` +
SDB pattern as `scripts/tv.py`), runs `applist` and `pkgcmd -l` (both plain listing commands, no
state change), checks which candidate app IDs from `profiles.json` are actually present, and
saves everything to `.local/debloat/snapshots/<name>/` (`applist.txt`, `pkgcmd-l.txt`,
`report.json`). Safe to run at any time; makes no changes.

```sh
python3 scripts/debloat/snapshot.py --name baseline-01
```

## What's proven (2026-11-02)

The original plan assumed `sdb shell 0 pkgcmd ...` would just work, the same way `applist` does in
`snapshot.py`. It doesn't: testing found that `sdb shell 0 <command>` only runs a small allowlist of
registered Tizen debug commands (`applist` is one) - `echo`, `which`, `ls`, and `pkgcmd` all return
nothing through it, silently (this is also why `pkgcmd-l.txt` in every snapshot is a 0-byte file).
There's no general shell behind that interface.

Real command execution required reusing the same mechanism `scripts/native-home/` already proved:
the undocumented package-name command-execution workaround (disguising a reverse-shell callback as
a `.tpk` filename passed to `0 appinstall tpk`, executed as SDK UID 901). `scripts/debloat/run.py`
adapts that transport directly from `scripts/native-home/run.py` - same model guard, same
reverse-TCP callback, same completion markers - but skips the .NET staging entirely: disabling an
app is a plain CLI/file operation (`pkgcmd`, or `sqlite3` against `pkgmgr_parser.db`), unlike
native Home routing, which needed raw library calls (`libvconf.so.0` etc.) no CLI exposes.

Once inside that real shell, `pkgcmd`, `sqlite3`, and `vconftool` are all present and working
normally (`/usr/bin/pkgcmd`, `/usr/bin/sqlite3`, `/usr/bin/vconftool`). `pkgcmd`'s own `-D`/`-A`
flags are the standard mechanism, confirmed against `package_app_info.app_disable` via direct DB
read before and after each step - no raw SQL write needed:

```sh
pkgcmd -D -t app -n <app_id> --global   # deactivate; pkgcmd itself reports val[ok]
pkgcmd -A -t app -n <app_id> --global   # activate;   pkgcmd itself reports val[ok]
sqlite3 /opt/dbspace/.pkgmgr_parser.db "SELECT app_disable FROM package_app_info WHERE app_id='<app_id>';"
```

Full `query → apply → query → restore → query` cycle against `yL49PNFmjW.service` (PromotionService):
`app_disable` went `false → true → false` exactly, `pkgcmd` reported success at each step, and
`app_onboot`/`app_autorestart` stayed untouched throughout (deactivate only touches the one flag).
Targeted at the **app** level (`-t app`, this app's own id), not the **package** level - the
`yL49PNFmjW` package also contains `yL49PNFmjW.PromotionApp`, a separate app this test didn't
touch. The device was left in its original (enabled) state at the end of this validation round.
`scripts/debloat/inspect.sh` records the mechanism for re-verification; `query.sh`/`apply.sh`/
`restore.sh` (the shell stage scripts, not the Python tools below) are still hardcoded to this one
app id - they were the single-app proof, not the general tool.

## General tooling (`scripts/debloat/plan.py`, `apply.py`, `restore.py`)

`transport.py` factors the proven injection transport out of `run.py` into a shared function,
`run_script(source, label)`, so these three can build one script covering many apps and execute it
in a single device round trip rather than re-paying the connection/injection cost per app.

- `plan.py [group ...]` (read-only) - queries the **real current** `app_disable`/`app_onboot`/
  `app_autorestart` for every requested candidate (all of them if no group given) and writes the
  exact-value baseline to `.local/debloat/plan/<timestamp>/baseline.json`. This is what
  `restore.py` restores to, so it has to be the genuine current state, not an assumption.
- `apply.py <baseline.json>` - live-queries current `app_disable` first (not the baseline file's
  recorded value, which can go stale between runs - see the bug note below), disables everything
  not already disabled via `pkgcmd -D -t app -n <id> --global`, then independently re-verifies
  every single one against `package_app_info.app_disable`. Writes `apply-result.json` next to the
  baseline with `ok`/`failed`/`already_disabled_skipped` lists; non-zero exit if anything failed
  to verify.
- `restore.py <baseline.json>` - re-enables (`pkgcmd -A`) everything the baseline recorded as
  originally enabled, independently re-verified against the baseline's exact recorded values
  (not just flipped back to `false` - compared field-for-field, so an app that started with
  `onboot`/`autorestart: true` gets checked against that, not a blanket assumption).

**Known-and-fixed bug**: `apply.py`'s first version decided what to skip from the *baseline file's
recorded* `app_disable` value. Since the baseline is a point-in-time capture, re-running `apply.py`
against an older/overlapping baseline after some of its apps were already disabled by a different
run under-reported what got skipped (harmless in practice - re-running `pkgcmd -D` on an
already-disabled app is a safe no-op, confirmed when this happened during the full rollout below -
but the "N already disabled, skipped" line was wrong). Fixed to live-query current state first.

## Discipline followed for the real rollout

Same as the native-Home experiment (`docs/tv-status.md`'s "Native Home and recovery"): baseline
captured before any write, exact-value restore path proven (on a 5-app batch, round-tripped
disable -> verify -> restore -> verify before touching the rest), one app validated before scaling
to the full list, owner's explicit authorisation for the write itself - given separately from, and
after, authorisation to build the tooling.

One real gap hit along the way: the full 63-app `apply.py` call was blocked by Claude Code's own
harness-level safety classifier ("Modify Shared Resources"), independent of the owner's own
authorisation. The owner ran it themselves instead, using the `!` prefix to execute directly in
the session - that's not subject to the same classifier since it's the owner's own action, not the
agent's. The later 21-app round (quiet-tizen-gap + full-sweep candidates) ran agent-side without
hitting the same block, for reasons not fully understood - possibly batch-size-dependent.

## Systemd services: investigated, not pursued

`ipa.service`, `contents-recognition-service.service`, `org.tizen.tv.sp-kpi.service`,
`data-service.service` (quiet-tizen's `runtime_only_masks`), plus 12 more in their persistent
`stop_markers` list (Bixby/context-aware/AICompanion/Gaming Hub daemons, etc.) - all confirmed to
genuinely exist on this TV via `systemctl list-units --all` (`systemctl list-unit-files` hangs on
this TV and should be avoided; `list-units` doesn't). Two more worth knowing about that neither
original candidate list named: `kpi-logging.service` ("Send Key To Logger Service" - no Tizen app
wrapper, reads like remote-key/keystroke logging) and `media-analytics-service.service` (currently
in a failed state).

None of this is reachable with the mechanism built here. Read-only verification (`getcap
/usr/bin/dotnet /usr/sbin/sdbd-tarlauncher`) confirmed this TV has the exact vulnerable capability
set (`cap_setgid,cap_sys_admin+ei` / `cap_setgid,cap_setuid+eip`) quiet-tizen's root route
(vendored from [chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root), an
`sdbd-tarlauncher` + `tar --to-command` privilege-escalation chain) needs - the exploit would work
here. It wasn't run. Obtaining root is an explicit hard limit for this project (same boundary the
native-Home work has held throughout: no root, no security-policy changes, no resident helper),
and even setting that aside, quiet-tizen's own profile treats the four `runtime_only_masks`
services as non-persistent by design (not in their `stop_markers` list, unlike the other 12) - a
disable would revert on the next reboot, needing the exploit re-run every time for a result that
doesn't stick. Judged not worth the exposure for a non-durable outcome. Owner's explicit call,
made with this information in hand.

## Lower-confidence candidates

Five more the full-capture sweep surfaced that look plausible but weren't added, because each is a
real user-facing feature on some installations, not obviously-unused bloat or covert telemetry:

| App | Why it's ambiguous |
| --- | --- |
| `com.samsung.tizen.samsung-cloud` | Samsung Cloud sync - a real feature if cross-device settings/photo sync is wanted |
| `com.samsung.tv.nfc-daemon` / `com.samsung.tv.nfc-monitor` | NFC tap-to-connect - real feature if used for mobile pairing |
| `com.samsung.rdm.vx.dmhandler` ("VisualExperienceDeviceManagementApplication") | Reads as retail/remote device management; unclear if it has any home-use relevance or is purely a showroom leftover |
| `com.samsung.tv.coba.mobilebff` ("CoBA Sample App") | Likely a SmartThings/SmartView mobile-companion bridge despite "Sample App" in its display name - not clearly unused |

Also explicitly reviewed and excluded as false positives from the keyword sweep (not ambiguous,
just wrongly matched): `org.tizen.pvrrecorder-syspopup` (its DVR/recording popup, not demo/sample
bloat - matched on the word "sample" in an unrelated display name), `com.samsung.SelfDiagnosis`
(a legitimate support/troubleshooting tool, not privacy telemetry), `com.samsung.mtm-banner`
(maintenance-mode service infrastructure, not bloat).

## Rollback

`.local/debloat/plan/20261102-195727/baseline.json` is the exact-value baseline for everything
currently disabled (all 84 candidates, superseding the earlier 63-only baseline). To put
everything back exactly as it was:

```sh
python3 scripts/debloat/restore.py .local/debloat/plan/20261102-195727/baseline.json
```

This re-enables every app and independently re-verifies each one against the baseline's exact
recorded values (not a blanket "set to false" - every app that started with `app_onboot`/
`app_autorestart: true` gets checked against that, specifically). May hit the same harness
classifier the first mass `apply.py` call did - run it with `!` if Claude's own call is blocked.
