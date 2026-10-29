# Optional debloat (ads, Bixby/voice, context services, sidebar, TV Plus)

Inspired by [quiet-tizen](https://github.com/jss8649/quiet-tizen)'s cleanup toolkit, adapted for
this TV. Separate from CleanFrame's own app and the native-Home experiment (`docs/tv-status.md`,
`scripts/native-home/`) - this disables stock Samsung services, not anything CleanFrame installs.

**Status: scaffold only. Nothing in this repo disables anything on the TV yet.** The candidate
list below is real (grepped from an actual `applist` capture of this TV), but the mechanism for
actually disabling an app - and whether it's reversible, and whether it affects anything else -
has not been tested here at all.

## Why this needs its own validation, not quiet-tizen's values

quiet-tizen's TV (`UN75U8000FFXZA`, Tizen 9.0) is a different model and firmware from this one
(`UE55CU7100KXXU`, Tizen/platform_version 8.0 per `.local/setup-record.md`). Their own README is
explicit that their generalised scripts were "checked locally... not replayed end-to-end on a
second TV" even on hardware closer to their reference device than this one is. Two things carry
over and two don't:

- **Carries over**: the *category* of mechanism needed. quiet-tizen found that standard `pkgcmd`
  activate/deactivate "did not reliably report or retain the intended state" on their build, and
  dropped to editing `pkgmgr_parser.db` registry fields (`app_disable`, `app_onboot`,
  `app_autorestart`) directly via SQL, plus `vconftool` for simple preference flags and systemd
  stop-markers for a couple of persistent services. That's a reasonable order of escalation to
  repeat here: try the standard, documented, easily-reversible route first, and only drop to
  direct registry edits if it proves unreliable on this TV too.
- **Doesn't carry over**: their specific app IDs, exact registry field values, and the ~51-app
  grouping. Candidates for *this* TV came from grepping `.local/qa/tv-applist.txt` (captured
  2026-10-23) against their category names - see `scripts/debloat/profiles.json`. Every entry is
  marked `verified: false` until confirmed present in a fresh snapshot.

## Candidate groups (`scripts/debloat/profiles.json`)

| Group | Count | Examples |
| --- | --- | --- |
| `advertising` | 5 | Ad Web Framework, Targeted Advertisment Service, Samsung Promotion |
| `voice` | 20 | Bixby (provisioning, context client, capsule viewer, wake engine, "Salute" - Bixby's internal codename), voice/TTS services |
| `context` | 5 | Context Aware Agent and its toast/grab-control/server-requester helpers |
| `sidebar` | 1 | `com.samsung.tv.home.sidebar` |
| `tvplus` | 2 | TV Plus deeplinker and the app itself |

## What's built so far

`scripts/debloat/snapshot.py` - **read-only**. Connects to the TV (same `.local/device.json` +
SDB pattern as `scripts/tv.py`), runs `applist` and `pkgcmd -l` (both plain listing commands, no
state change), checks which candidate app IDs from `profiles.json` are actually present, and
saves everything to `.local/debloat/snapshots/<name>/` (`applist.txt`, `pkgcmd-l.txt`,
`report.json`). Safe to run at any time; makes no changes.

```sh
python3 scripts/debloat/snapshot.py --name baseline-01
```

## Not built yet, on purpose

`plan.py`, `apply.py`, `restore.py` - generating and running the actual disable/restore commands.
Deferred until the mechanism itself is validated against a single low-risk app on the real device
(the PromotionService is the current candidate - a small, clearly-named, non-core service), the
same way `scripts/native-home/`'s helper was proven with query → apply → query → restore → query
before being trusted with the real target. Writing `apply.py` against guessed command syntax
risks a subtly wrong write to the TV's package registry; that's worse than not having the script
yet.

## Before any write to the device

Same discipline as the native-Home experiment (`docs/tv-status.md`'s "Native Home and recovery"):
snapshot before, exact-value restore path proven, one app validated before scaling to the full
list, owner's explicit authorisation for the write itself - not just for building the tooling.
