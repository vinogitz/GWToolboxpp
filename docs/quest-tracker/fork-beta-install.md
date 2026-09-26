# Fork Quest Tracker beta — local install (English)

**This is not an official GWToolbox++ release.**  
Official Toolbox downloads and docs remain at [gwtoolbox.com](https://gwtoolbox.com) / [gwdevhub/GWToolboxpp](https://github.com/gwdevhub/GWToolboxpp).  
This page is only for testers of the **vinogitz/GWToolboxpp** fork build that includes Quest Tracker → Tyrian Wayfarer Contract v1 export.

Build label used for the 2026-09-26 gate: RelWithDebInfo **`8.34_Beta2+quest`**.  
In Settings you should see `8.34`, `+quest`, and `Beta2` as separate labels. Contract JSON `producer.version` will be `8.34` only.

## Install the fork DLL locally

1. Build or obtain RelWithDebInfo `GWToolboxdll.dll` from this fork (see root `README.md` build steps, or a prerelease asset when published).
2. Place that DLL next to `GWToolbox.exe` (for example under `bin\RelWithDebInfo\` after a local build).
3. Optional but recommended: record the DLL SHA256 before first inject so you can detect replacements later.

## Launch with `/localdll`

Inject using the launcher next to your fork DLL:

```text
GWToolbox.exe /localdll /noupdate /noinstall
```

Or, with Guild Wars already running:

```text
GWToolbox.exe /pid <GwPid> /localdll /noupdate /noinstall
```

Do not use `/noexecheck` as a default launch flag.

`/localdll` loads the DLL beside the launcher and implies `/noupdate` / `/noinstall` for the **launcher**. See also `site` launch-options docs if present in your tree.

## DLL updater setting (separate from the launcher)

`/noupdate` only stops the **launcher** from updating at startup.  
Inside Toolbox: **Settings → Updater → Update mode → Do not check for updates**.

On this fork, installing an official GitHub DLL is an explicit **Official DLL…** confirm path. Do not use that button if you want to keep Quest Tracker.

## Export Contract v1 JSON

1. Log in on a character (Pre-Searing is fine for smoke).
2. Open **Quest Tracker** → **Export Contract v1**.
3. Files land under `Documents/GWToolboxpp/<PC>/QuestProgress/` (`exports/` plus latest `quest_progress_contract_v1.json`). Unchanged content may skip creating a new dated file.
4. Details and honesty rules: [`toolbox-wayfarer-export-guide.md`](toolbox-wayfarer-export-guide.md).

Do not publish raw exports, character names, or character keys.

## Optional: import in Tyrian Wayfarer

1. Wayfarer → **Settings → GWToolbox quest progress**.
2. Select the Contract JSON → **explicitly** link to a local character → Review and import → **Open dossier**.
3. Expect Life journey / history for linked progress. Re-importing the **same** file should report already imported and insert **0** new events.
4. Quest disappearance is **not** confirmed completion.

## Return to official Toolbox

1. Quit Guild Wars / unload Toolbox completely.
2. Install or reinstall a **clean official Toolbox** from [gwtoolbox.com](https://gwtoolbox.com) into its normal install location (do not treat “rename the fork DLL and keep launching from the same RelWithDebInfo folder” as a verified return path).
3. Start Guild Wars, then launch the **official** installer/launcher **without** `/localdll`, so it injects the official installed DLL.
4. Optionally keep or delete fork settings under `Documents/GWToolboxpp\` — progress JSON is observational data and is not required for official Toolbox to run.

## Where to report problems

Open issues on **`vinogitz/GWToolboxpp`** (the Wayfarer consumer repo is private for now).

- Quest Tracker / Contract **export**: title prefix or label `quest-tracker` / `contract-export`; describe steps and redacted diagnostics only.
- Wayfarer **import / dossier / Life journey**: title prefix or label `wayfarer-import` (or `wayfarer-dossier`); say which Wayfarer build/platform you used, without private repo access assumptions.
- Do **not** attach raw Contract JSON exports, character names, or character keys. Prefer counts, `producer.version`, outcome text (e.g. already imported / insert counts), and redacted error messages.
- Official Toolbox bugs unrelated to this fork: upstream channels only — do not expect upstream to support this fork build.
