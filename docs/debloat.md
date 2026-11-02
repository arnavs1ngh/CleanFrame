# Optional debloat (ads, Bixby/voice, context services, sidebar, TV Plus)

Inspired by [quiet-tizen](https://github.com/jss8649/quiet-tizen)'s cleanup toolkit, adapted for
this TV. Separate from CleanFrame's own app and the native-Home experiment (`docs/tv-status.md`,
`scripts/native-home/`) - this disables stock Samsung services, not anything CleanFrame installs.

**Status: mechanism validated against one app (2026-11-02), nothing scaled up yet.** The candidate
list below is real (grepped from an actual `applist` capture of this TV). The disable/restore
mechanism has now been proven end to end against `yL49PNFmjW.service` (PromotionService, in
`advertising`) - see "What's proven" below - but nothing beyond that one app has been touched, and
the reusable multi-app tooling (`plan.py`/`apply.py`/`restore.py`) still doesn't exist.

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
| `advertising` | 5 | Ad Web Framework, Targeted Advertisment Service, Samsung Promotion |
| `voice` | 21 | Bixby (provisioning, context client, capsule viewer, wake engine, "Salute" - Bixby's internal codename), voice/TTS services |
| `context` | 5 | Context Aware Agent and its toast/grab-control/server-requester helpers |
| `sidebar` | 1 | `com.samsung.tv.home.sidebar` |
| `tvplus` | 2 | TV Plus deeplinker and the app itself |
| `smart-extras` | 26 | SmartThings (app, hub, plugin platform, per-widget IoT cards), Samsung Health/workout tracker, Gaming Hub, ambient support/sound/FTE components |
| `telemetry` | 3 | samsung-analytics, contents-recognition-dbmgr, the remote-service logging debug menu |

Added 2026-11-02 after comparing against [jss8649/quiet-tizen](https://github.com/jss8649/quiet-tizen)'s
own cleanup profile, which covers both of these categories and this list didn't yet. One caveat
specific to `telemetry`: quiet-tizen's own telemetry group is mostly systemd **service** units
(`ipa.service`, `contents-recognition-service.service`, `org.tizen.tv.sp-kpi.service`,
`data-service.service`), not Tizen app packages - those don't appear in `applist`/`pkgcmd -l` at
all, so `snapshot.py` can't check them as it exists today, and quiet-tizen itself could only
runtime-mask them (`systemctl mask --runtime --now`), never persist the disable across reboot.
The three entries actually in `telemetry` above are the app-package-level candidates that showed
up in this TV's own capture; the service-unit layer remains unbuilt tooling, not just unverified
candidates.

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
touch. The device was left in its original (enabled) state. `scripts/debloat/inspect.sh` records
the mechanism for re-verification; `query.sh`/`apply.sh`/`restore.sh` are still hardcoded to this
one app id, not yet a general tool.

## Not built yet, on purpose

`plan.py`, `apply.py`, `restore.py` - a **generalised, reusable** version of the proven mechanism
above, parameterised over all 63 candidates instead of one hardcoded app id, plus a real
`original.json`-style baseline file (`scripts/native-home/`'s pattern) instead of a single ad hoc
JSON note. Deferred on purpose until explicitly requested: proving the mechanism on one low-risk
app is a different authorisation than disabling 63 apps across 7 groups, several of which
(`smart-extras`'s SmartThings/Health/Gaming Hub, in particular) are plausibly apps the owner
actually wants working, not just bloat.

## Before any write to the device

Same discipline as the native-Home experiment (`docs/tv-status.md`'s "Native Home and recovery"):
snapshot before, exact-value restore path proven, one app validated before scaling to the full
list, owner's explicit authorisation for the write itself - not just for building the tooling.
