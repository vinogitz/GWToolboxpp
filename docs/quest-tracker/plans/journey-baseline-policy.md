# Journey baseline policy

Date: 2026-09-11  
Status: **design only** (no production C++ in this change)  
Base tip: `7b8d93d72dfc3eca87e46c8fccde77c3d698d089` (`feature/quest-tracker-phase-2-persistence`)  
Review amendments: C1–C3, W4–W6 (2026-09-11)

## Problem

On a long-lived character’s **first** Toolbox observation, several journey builders treat an empty prior as “never seen” and emit catch-up milestones for every currently unlocked map/skill/hero/profession/threshold. Those events share one `observedAt` (sample time). Wayfarer’s dossier Life journey shows only the first **40** timeline entries (`character_timeline_section.dart`), so unlock noise can crowd out quest and session history. `observedAt` is observation time, but the UI reads like milestone time.

## Preferred direction

1. First **complete** live snapshot **seals** a persisted baseline **per flood family** for unlock/threshold state.
2. Baseline alone does **not** become timed `journeyEvents[]` milestones.
3. Only later **newly observed deltas** append journey events.
4. Current lifetime state remains exportable via Contract **snapshot** fields where they already exist (`level`, `skillPointsEarned`, `factionTotals`, `hallOfMonuments`, `missions`, titles projection).
5. Missing world/account context must not seal an empty baseline or clear existing data.
6. Uncertain/incomplete samples must not create confirmed-looking catch-up floods (**must not seal**).
7. No quest/combat/movement automation.

This matches title/level’s existing first-sample suppress pattern and extends it to unlock/threshold kinds that currently catch up via `BuildNewlySeenIdEvents` / absolute thresholds / HoM-from-zero.

### C1 — Unlock visibility tradeoff (accepted)

**Decision (a):** Accept the visibility tradeoff for this phase.

After seal, Contract v1 still has **no** unlock inventory snapshot arrays for map / character skill / hero / profession / vanquish. Those families are therefore visible in Life journey **only as deltas observed since tracking began** (plus any pre-policy catch-up noise already on disk). Permanent mission bits remain in `missions[]`; lifetime totals remain in existing snapshot fields.

**Not in this phase:** Contract unlock-inventory enrichment (exporting sealed unlock sets as snapshot arrays). That requires a **separate future Contract sync** with Wayfarer before producer work. Until then, “what was already unlocked before Toolbox” is intentionally not reconstructible from Contract journey milestones alone.

---

## 1. Current data flow

```
QuestTrackerWindow::Update (Persistent + world_ready)
  → SampleLiveJourneySnapshot(previous titles/level/map, existing journey_events)
       → MergeJourneySnapshot (title_tier / level_up)
       → BuildMapEnterEvents
       → BuildVanquishAreaEvents / BuildNewlySeenIdEvents / BuildHardModeUnlockEvents
       → BuildCartographyThresholdEvents / BuildAbsoluteThresholdEvents
  → IngestJourneySnapshot (store titles/level/map/xp/sp/faction + append events)

UI callbacks (dungeon/mission/vanquish complete)
  → PushJourneyMilestoneHint → BuildTimedMapClearEvents → IngestJourneyEvents

Async HoM fetch
  → IngestHomSnapshot → BuildHomPointsEvents

Export
  → Contract character.journeyEvents[] + snapshot fields
```

Wiring hub is `QuestTrackerWindow` + `QuestProgressLive` / `QuestProgressService`, not the Obs→Reducer path in `proposed-architecture.md`. `QuestProgressReducer` has no journey logic. Journey records have **no** `source` / `confidence` fields today.

Priors for unlocks/thresholds are reconstructed from **already emitted** `journey_events` (`PriorIdsFromJourneyEvents`, `MaxAmountFromJourneyEvents`, `MaxCartographyPercentFromEvents`, `HasJourneyKind`). There is **no** separate unlock bitset baseline in the store (`storeFormat` `gwtoolbox-quest-progress` **1.1**).

---

## 2. Kind table

| Kind | Source | Scope | First snapshot today | Desired | Required baseline |
|------|--------|-------|----------------------|---------|-------------------|
| `title_tier` | Snapshot `world->titles` | Character | No event until tier rises vs persisted `titles` | Keep suppress-until-delta | `titles` map (exists) |
| `level_up` | Snapshot level | Character | No event until level rises vs `last_known_level` | Keep | `last_known_level` (exists) |
| `map_enter` | Snapshot `GetMapID` | Character | Emits when prior map missing or changed | Keep visit emit (one event, not flood) | `last_map_id` (exists) |
| `map_unlock` | Snapshot `unlocked_map` bits | Character | Emit-all vs empty prior from events | Per-family seal; emit only new bits | Map-unlock id set + family sealed flag |
| `skill_unlock` | Snapshot `unlocked_character_skills` | Character | Emit-all catch-up | Per-family seal; emit only new | Skill-unlock id set + family sealed flag |
| `account_skill_unlock` | Snapshot account skill list | Account semantic, stored under active character | Emit-all under that character | **Account-family** seal; emit delta under observing character only | Account skill id set + account-family sealed flag |
| `hero_unlock` | Snapshot `hero_info` | Character | Emit-all catch-up | Per-family seal; emit only new | Hero id set + family sealed flag |
| `profession_unlock` | Snapshot profession bits | Character | Emit-all catch-up | Per-family seal; emit only new | Profession id set + family sealed flag |
| `hard_mode_unlock` | Snapshot flag | Character | Emit if unlocked and kind absent | Per-family seal; emit only false→true after seal | HM unlocked bool + family sealed flag |
| `vanquish_area` | Snapshot vanquish bits | Character | Emit-all catch-up | Per-family seal; emit only new bits | Vanquish map id set + family sealed flag |
| `cartography_threshold` | Snapshot fog % | Character | Catch-up all thresholds from 0 | Per-family seal; emit only newly crossed thresholds | Use sealed flag + live/snapshot-derived prior % (no dual amount field) |
| `skill_point_threshold` | Snapshot earned SP | Character | Catch-up from 0 via events | Per-family seal; emit only new crossings | **Single-source:** sealed flag + existing `skill_points_earned` snapshot as prior |
| `faction_threshold` | Snapshot earned factions | Character | Catch-up from 0 | Per-family seal; emit only new crossings | **Single-source:** sealed flag + existing `faction_totals` snapshot as prior |
| `hom_points` | Async HoM snapshot | Character envelope | First sample treats previous as 0 → emit all non-zero | **HoM-family** seal; emit only increases after seal | Sealed flag + existing `hall_of_monuments` snapshot as prior |
| `mission_complete` | UI game message | Character | Event-only (no snapshot catch-up) | Keep | None (timed) |
| `dungeon_complete` | UI game message | Character | Event-only | Keep | None |
| `vanquish_complete` | UI game message | Character | Event-only (distinct from permanent `vanquish_area`) | Keep | None |

**Massive baseline risk today:** `map_unlock`, `skill_unlock`, `account_skill_unlock`, `hero_unlock`, `profession_unlock`, `vanquish_area`, `cartography_threshold`, `skill_point_threshold`, `faction_threshold`, `hom_points`, and (single-event) `hard_mode_unlock`.

**Timed / low flood risk:** `mission_complete`, `dungeon_complete`, `vanquish_complete`, `map_enter`, `title_tier`, `level_up`.

---

## 3. Proposed domain / store model

### 3.1 Concepts

Per **flood family** (not one global character seal), distinguish:

| State | Meaning |
|-------|---------|
| `Unset` | This family never sealed; missing context, incomplete sample, or never sampled |
| `Sealed` | Baseline captured for this family; may have zero unlocks; **no** milestone implied |
| `DeltaObserved` | After seal, a new id/threshold/flag appeared → append journey event and advance that family’s baseline set / snapshot prior |

Do **not** encode Sealed as a journey event.

### 3.2 Flood families (C2)

Seal independently (each `Unset` | `Sealed`, optional audit timestamp for debugging only):

| Family | Scope | Covers kinds / priors |
|--------|-------|------------------------|
| `maps` | Character | `map_unlock` |
| `character_skills` | Character | `skill_unlock` |
| `heroes` | Character | `hero_unlock` |
| `professions` | Character | `profession_unlock` |
| `hard_mode` | Character | `hard_mode_unlock` |
| `vanquish` | Character | `vanquish_area` |
| `cartography` | Character | `cartography_threshold` |
| `skill_points` | Character | `skill_point_threshold` |
| `faction` | Character | `faction_threshold` |
| `hom` | Character envelope | `hom_points` |
| `account_skills` | Account | `account_skill_unlock` |

Title / level / map_enter / timed clears are **not** flood-baseline families (existing suppress or event-only behavior).

**Rejected:** a single sticky `journeyBaselineSealedAt` that seals all families together.

### 3.3 Suggested persisted fields (additive)

On `StoredCharacter` (illustrative names):

- Per character flood family: `*BaselineState` = `Unset` | `Sealed` (+ optional `*BaselineSealedAt` audit only)
- Unlock id sets / bit encodings for families that need them: maps, character skills, heroes, professions, vanquish
- `hardModeBaseline` bool meaningful only when `hard_mode` family is `Sealed`
- Threshold / HoM families: **no duplicate amount fields** (W5) — when `Sealed`, builders use existing snapshot fields as prior (`skill_points_earned`, `faction_totals`, `hall_of_monuments`, and cartography prior derived from last sealed observation policy below)

On `AccountProgressStore`:

- `accountSkillsBaselineState` = `Unset` | `Sealed` (+ optional audit ts)
- `baselineAccountSkills` — account skill ids (needed; no existing account snapshot array on Contract/store today)

Existing fields keep their roles: `titles`, `last_known_level`, `last_map_id`, `hall_of_monuments`, `skill_points_earned`, `faction_totals`, `journey_events` (append-only milestones only).

### 3.4 Incomplete first-tick gating (C3) — C++ merge blocker

Bitset / list **completeness on first Persistent tick remains empirically unknown**. Implementation must still ship an explicit conservative policy; **C++ merge is blocked** until this is coded and tested:

1. **Do not seal** a family when world/account context for that family is missing.
2. **Do not seal** on empty-or-suspicious unlock samples when the character is not expected to be blank (conservative default: if a previously observed non-empty working set for that family would shrink to empty/near-empty without an explicit “new character” signal, **no seal-on-shrink** — leave `Unset`, emit nothing).
3. Prefer seal only after a **stable sample** for that family (e.g. same id-set / bit pattern across consecutive eligible polls, or equivalent documented stability check). Exact N and equality rule are implementation detail; default must be conservative.
4. While `Unset`, builders must **not** fall back to emit-all against empty event priors.
5. Partial/uncertain → stay `Unset`; never invent confirmed catch-up milestones.

In-game verification still required to validate the stability heuristic against real GWCA behavior.

### 3.5 Sealing and delta rules

Seal a family only when §3.4 gates pass and identity is bound.

If context missing or unstable: leave that family `Unset`; do not clear a prior `Sealed`; do not emit catch-up.

After `Sealed`, reuse builders with:

- unlock families → persisted baseline id sets as `previous_*`
- threshold / HoM families → **existing snapshot fields** as prior amounts (W5)
- continue fingerprint dedupe via `AppendUniqueJourneyEvents`

### 3.6 W5 — Threshold / HoM single-source

Do **not** dual-write `baselineSkillPointsEarned` / `baselineFactionTotals` / mirrored HoM point fields alongside snapshots.

| Family | Prior after seal |
|--------|------------------|
| `skill_points` | `StoredCharacter::skill_points_earned` |
| `faction` | `StoredCharacter::faction_totals` |
| `hom` | `StoredCharacter::hall_of_monuments` |
| `cartography` | Prior max % from last sealed observation stored as the family’s sealed prior **or** derived only from a single cartography baseline field if no snapshot field exists today — still one source, not snapshot+mirror pair |

For cartography, Contract/store today has no dedicated lifetime cartography snapshot field; a **single** sealed prior percent for that family is allowed. Do not also reconstruct threshold catch-up from journey events once sealed.

---

## 4. JSON codec and version compatibility

| Item | Decision |
|------|----------|
| Format id | Keep `gwtoolbox-quest-progress` |
| Version | **Minor bump** `1.1 → 1.2` (additive optional per-family baseline fields). Major bump not required if old readers ignore unknown fields and new readers tolerate absence |
| Old `1.0` / `1.1` files | Load via existing migrate-to-current path; family states absent → `Unset` |
| Reject | Newer major still rejected |
| Journey event schema | Unchanged (Contract v1 payload shape unchanged) |
| Do not | Rewrite or delete existing `journey_events` during migration |

### W4 — Upgrade atomicity (same ingest)

Codec migrate `1.1 → 1.2` may only add empty/`Unset` family fields. Catch-up prevention is enforced on **first post-upgrade ingest**, atomically:

1. Enter ingest with family state `Unset`.
2. **Before** unlock/threshold builders run: if that family has existing unlock/threshold `journey_events`, **reconstruct baseline id set / use snapshot prior, mark `Sealed`, emit nothing**.
3. Only then run builders for that family (delta-only vs sealed prior).
4. **Emit-all against empty prior is forbidden** for flood families on this path.
5. If no prior events and sample fails §3.4 gates → remain `Unset`, still no emit-all.
6. Never invent quest completions or delete history.

Reconstruction and seal for a family must not be deferred to a later poll after builders have already run once with empty priors.

---

## 5. Reducer / service / live integration points

| Component | Change (planned) |
|-----------|------------------|
| `QuestCharacterJourney.*` | Seal-aware priors per family; keep pure builders testable; forbid empty-prior emit-all when family policy active |
| `QuestProgressLive::SampleLiveJourneySnapshot` | Per-family stability/seal gates; return seal updates + delta events only |
| `QuestProgressService::IngestJourneySnapshot` / `IngestHomSnapshot` | **W4 atomic** reconstruct/seal-before-build; persist per-family state; append only deltas; threshold priors from snapshots (W5) |
| `QuestProgressStore` merge | Per-family: `Sealed` sticky once set; union unlock id sets; do not drop events |
| `QuestProgressJsonCodec` | 1.2 per-family fields + migrate stub to `Unset` |
| `QuestProgressContractExporter` | No Contract schema change; fewer false milestones; **no new unlock inventory arrays** (C1) |
| `QuestProgressReducer` | No journey work |
| `QuestTrackerWindow` | No automation; may only call updated ingest APIs |

---

## 6. Contract export consequences

- Contract **v1 document unchanged** (this plan forbids editing Contract docs/meaning/version).
- Producer emits fewer `journeyEvents` on first track of veteran characters.
- Snapshot fields still carry current lifetime state where they already exist.
- **C1:** no map/skill/hero/profession/vanquish unlock inventory snapshot arrays in this phase.
- `account_skill_unlock` remains under the character envelope when a **true delta** is observed while that character is active; account-family baseline prevents per-character re-flood.
- Fingerprint / canonical JSON rules unchanged.
- Existing noisy events already written to disk remain exportable; display handling is consumer-side (W6).

---

## 7. Wayfarer UX consequences (W6)

**Toolbox plan non-goal:** no Wayfarer / Codex code in this repository or PR.

Observed today: dossier timeline `entries.take(40)`.

**Follow-up (Codex repo, separate work):** for **already imported** baseline noise, implement **display collapse** only:

- Collapse same-`observedAt` unlock bursts into a summary such as “Already unlocked when tracking began”.
- Prefer quest/session-meaningful kinds when truncating.
- Treat `observedAt` as observation time in copy.
- **DB delete / rewrite of imported rows is forbidden** (append-only evidence).

Toolbox stops creating new floods; it does not clean Codex databases.

---

## 8. Migration and backward compatibility

| Scenario | Behavior |
|----------|----------|
| New character, empty store | Per-family seal on first gated-complete sample; few or no unlock events; `map_enter` / later deltas / timed clears as today |
| Veteran character, first Toolbox session | Per-family seal without unlock catch-up flood; Life journey shows tracking-start deltas only (C1) |
| Store wipe / new folder | Same as first session (intentional re-seal; pre-Toolbox unlock inventory not in Contract — C1) |
| Upgrade 1.1 → 1.2 with existing unlock flood events | Keep events; **W4** reconstruct+seal in same ingest before builders; stop further catch-up |
| Character switch | Per-character families; account_skills family shared |
| Account switch | Different `account_key` store file; no cross-account merge |
| Missing / unstable context | Family stays `Unset`; no empty seal; no emit-all (C3) |
| Play without Toolbox, return later | Deltas vs sealed families |
| Already-exported Contract / already-imported Codex noise | Immutable evidence; **W6** Codex display collapse follow-up only |

**History policy for existing noise:** do not erase; do not auto-rewrite evidence; Codex display collapse only.

---

## 9. Scenario matrix (required answers)

| Scenario | Expected |
|----------|----------|
| New character first session | Per-family seal when gated; emit real deltas; title/level as today |
| Old character first Toolbox session | Per-family seal; **no** mass milestones |
| Restart with store | Load per-family state; quiet unless delta |
| Restart without store | Re-seal per family; observational gap accepted (C1) |
| Old store upgrade | §4 W4 atomic reconstruct |
| Character switch | No cross-character contamination; account_skills shared |
| Account switch | Separate store |
| Partial/missing/unstable context | Family `Unset`; no seal; no flood (C3) |
| Return after offline play | Delta vs sealed families |

---

## 10. Test matrix

Pure logic (`QuestProgressTests`):

1. Per unlock family: first gated sample seals that family, **zero** events; second sample with +1 id → one event.
2. Families seal independently (e.g. maps sealed, skills still `Unset` when skills context missing).
3. Account skills: account-family seal; character A no flood; new account skill on A → one event; character B does not re-emit.
4. Thresholds: sealed + snapshot prior only (no dual baseline amount); no catch-up from 0; crossing emits.
5. HoM family: first gated fetch seals without `hom_points` flood; later increase emits.
6. C3: shrink/empty/unstable sample → no seal, no emit-all.
7. W4: 1.1 store with unlock events → single ingest reconstructs+seals before build → zero new catch-up events.
8. Title/level/map_enter + timed clears regressions stay green.
9. Codec 1.1 → 1.2 round-trip preserves `journey_events`; per-family state optional/`Unset`.
10. Missing account pointer → account_skills `Unset`, no flood.
11. Merge: per-family `Sealed` sticky; unlock id sets unioned; events kept.

**Not unit-testable here:** real GWCA first-tick completeness — remains **unknown**; in-game checklist still required after C3 policy is implemented.

Regression: exporter valid Contract v1; no unlock inventory arrays added (C1).

---

## 11. Implementation slices (order)

1. **Domain + codec 1.2** — per-family state enums, unlock id sets, migrate to `Unset`, tests.
2. **W4 ingest atomicity** — reconstruct/seal-before-build helper + tests (merge blocker with C3).
3. **C3 gating** — stability / no-seal-on-shrink / no emit-all while `Unset` (merge blocker).
4. **Unlock family priors** — Live/Service wiring; seal/delta tests.
5. **Thresholds + cartography + hard mode** — W5 single-source priors.
6. **Account skill family** on `AccountProgressStore`.
7. **HoM family** seal-on-first-gated-fetch.
8. **Store merge** per-family rules.
9. **In-game verification** checklist (Pre-Searing + unlock-heavy post-Searing).
10. **Wayfarer/Codex display collapse** — separate repo/PR (W6); not Toolbox.

Do not combine with unlock-array Contract expansions (C1 future sync) or automation.

---

## 12. Risks and open questions

### Decided

- Unlock/threshold first sample today is emit-all vs empty event-derived prior.
- Title/level already suppress-until-delta; timed clears are game-message driven.
- Store minor is 1.1; journey has no source/confidence.
- Account skills are sampled from account context but stored under the active character’s `journey_events`.
- Wayfarer UI truncates timeline to 40 entries.
- **C1:** accept no unlock inventory snapshot arrays for now; Life journey = since tracking; enrichment = future Contract sync.
- **C2:** per-family `Unset` \| `Sealed` (not one global sticky seal).
- **C3:** conservative no-seal-on-partial/empty/shrink policy is required; C++ merge blocker until implemented.
- **W4:** upgrade reconstruct+seal runs in the same ingest before builders; emit-all forbidden.
- **W5:** threshold/HoM priors are sealed flag + existing snapshot (no dual amount write).
- **W6:** already-imported noise → Codex display collapse follow-up; no DB delete; Wayfarer code is Toolbox non-goal.
- Contaminated-store hygiene doc is about quest identity contamination, not journey baseline.

### Unknown (not invent)

- Whether unlock bitsets/lists can be incomplete on the first Persistent tick after map load (policy in C3 still required).
- Whether `hero_info` / profession masks can temporarily omit owned entries.
- Ordering races between HoM async fetch and live unlock sampling.
- Exact stability-check parameters (N polls / equality) — implement conservatively, tune with in-game evidence.
- Exact compact encoding for large bitsets on disk (implementation detail).
- Whether `map_enter` on very first sample should change (recommended keep; not the flood problem).

### Risks

- Over-conservative C3 gating delays seal and therefore delays legitimate delta emission until stability is met (accepted vs false catch-up).
- Reconstructing baseline from noisy events keeps bad timestamps in history (accepted; W6 display-only mitigation).
- Account baseline in store is a new persistence surface; must not break accountKey validation.
- C1 tradeoff: users cannot see full pre-Toolbox unlock inventory via Contract until a future synced enrichment.

---

## 13. Explicit non-goals

- Production C++ in this documentation PR
- Contract v1 schema / meaning / version changes (including unlock inventory arrays — C1 future sync)
- Automatic deletion or rewrite of existing journey evidence
- Codex/Wayfarer code changes in this Toolbox plan (W6 follow-up is separate)
- DB delete of already-imported journey rows
- Quest acceptance / movement / combat / reward automation
- Festival hats, deaths, gold-as-progress, PvP W/L journey kinds
- Unlock-baseline implementation merge without senior architecture approval and without C3/W4 gates satisfied

---

## 14. Answers to posed questions (summary)

1. **Snapshot-derived:** title, level, map_enter, vanquish_area, map/skill/account_skill/hero/profession unlock, hard_mode, cartography, SP/faction thresholds, hom_points. **Timed game messages:** mission/dungeon/vanquish_complete.
2. **Mass baseline:** unlock + vanquish_area + threshold + hom_points families above.
3. **Character vs account:** account skills are account-family; other flood families are character (HoM character-envelope).
4. **Store today:** cannot distinguish never-observed vs baseline-without-milestone vs new-since-baseline for unlocks; events double as prior.
5. **Needed baseline:** per-family sealed state + unlock id sets; thresholds use sealed + existing snapshots (W5).
6. **Version:** store **minor** 1.2; major not required for additive fields.
7. **Old files:** load, migrate minor, W4 reconstruct/seal on first ingest; keep all events.
8. **Existing noise:** retain; no auto-rewrite; **W6** Codex display collapse only.
9. **Account unlocks:** account-family baseline; Contract still nests delta events under the observing character.
10. **Append-only:** seal without appending; deltas append; history never erased.
11. **Scenarios:** see §9.
12. **Tests:** see §10.
