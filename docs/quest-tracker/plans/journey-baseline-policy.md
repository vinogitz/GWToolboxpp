# Journey baseline policy

Date: 2026-09-11  
Status: **design only** (no production C++ in this change)  
Base tip: `7b8d93d72dfc3eca87e46c8fccde77c3d698d089` (`feature/quest-tracker-phase-2-persistence`)

## Problem

On a long-lived character’s **first** Toolbox observation, several journey builders treat an empty prior as “never seen” and emit catch-up milestones for every currently unlocked map/skill/hero/profession/threshold. Those events share one `observedAt` (sample time). Wayfarer’s dossier Life journey shows only the first **40** timeline entries (`character_timeline_section.dart`), so unlock noise can crowd out quest and session history. `observedAt` is observation time, but the UI reads like milestone time.

## Preferred direction

1. First **complete** live snapshot **seals** a persisted baseline for unlock/threshold state.
2. Baseline alone does **not** become timed `journeyEvents[]` milestones.
3. Only later **newly observed deltas** append journey events.
4. Current lifetime/unlock state remains exportable via Contract **snapshot** fields where they already exist (`level`, `skillPointsEarned`, `factionTotals`, `hallOfMonuments`, `missions`, titles projection).
5. Missing world/account context must not seal an empty baseline or clear existing data.
6. Uncertain/incomplete samples must not create confirmed-looking catch-up floods.
7. No quest/combat/movement automation.

This matches title/level’s existing first-sample suppress pattern and extends it to unlock/threshold kinds that currently catch up via `BuildNewlySeenIdEvents` / absolute thresholds / HoM-from-zero.

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
| `map_enter` | Snapshot `GetMapID` | Character | Emits when prior map missing or changed | Keep visit emit (one event, not flood); optional: still require prior map optional seal without changing unlock policy | `last_map_id` (exists) |
| `map_unlock` | Snapshot `unlocked_map` bits | Character | Emit-all vs empty prior from events | Seal baseline; emit only new bits | Persisted map-unlock id set / bitset |
| `skill_unlock` | Snapshot `unlocked_character_skills` | Character | Emit-all catch-up | Seal; emit only new | Persisted skill-unlock id set |
| `account_skill_unlock` | Snapshot account skill list | Account semantic, stored under active character | Emit-all under that character | Seal at **account** baseline; emit delta under observing character only | Account-level skill id set |
| `hero_unlock` | Snapshot `hero_info` | Character | Emit-all catch-up | Seal; emit only new | Persisted hero id set |
| `profession_unlock` | Snapshot profession bits | Character | Emit-all catch-up | Seal; emit only new | Persisted profession id set |
| `hard_mode_unlock` | Snapshot flag | Character | Emit if unlocked and kind absent | Seal boolean; emit only false→true after seal | Persisted HM unlocked bool |
| `vanquish_area` | Snapshot vanquish bits | Character | Emit-all catch-up | Seal; emit only new bits | Persisted vanquish map id set |
| `cartography_threshold` | Snapshot fog % | Character | Catch-up all thresholds from 0 | Seal max %; emit only newly crossed thresholds after seal | Persisted max cartography % |
| `skill_point_threshold` | Snapshot earned SP | Character | Catch-up from 0 via events | Seal max amount; emit only new crossings | Prefer seal from `skill_points_earned` snapshot + baseline amount |
| `faction_threshold` | Snapshot earned factions | Character | Catch-up from 0 | Seal per-faction amounts; emit only new crossings | Prefer seal from `faction_totals` + baseline amounts |
| `hom_points` | Async HoM snapshot | Character envelope | First sample treats previous as 0 → emit all non-zero | Seal HoM points (and dedications already stored); emit only increases after seal | `hall_of_monuments` + explicit “HoM baseline sealed” flag if first fetch must not emit |
| `mission_complete` | UI game message | Character | Event-only (no snapshot catch-up) | Keep | None (timed) |
| `dungeon_complete` | UI game message | Character | Event-only | Keep | None |
| `vanquish_complete` | UI game message | Character | Event-only (distinct from permanent `vanquish_area`) | Keep | None |

**Massive baseline risk today:** `map_unlock`, `skill_unlock`, `account_skill_unlock`, `hero_unlock`, `profession_unlock`, `vanquish_area`, `cartography_threshold`, `skill_point_threshold`, `faction_threshold`, `hom_points`, and (single-event) `hard_mode_unlock`.

**Timed / low flood risk:** `mission_complete`, `dungeon_complete`, `vanquish_complete`, `map_enter`, `title_tier`, `level_up`.

---

## 3. Proposed domain / store model

### 3.1 Concepts

Per tracked identity, distinguish:

| State | Meaning |
|-------|---------|
| `Unset` | Never sealed for this kind family; missing context or never sampled |
| `Sealed` | Baseline captured; may have zero unlocks; **no** milestone implied |
| `DeltaObserved` | After seal, a new id/threshold/flag appeared → append journey event and advance baseline |

Do **not** encode Sealed as a journey event.

### 3.2 Suggested persisted fields (additive)

On `StoredCharacter` (illustrative names):

- `journeyBaselineSealedAt` (UTC optional) — character unlock/threshold families sealed together when first complete sample succeeds
- `baselineUnlockedMaps` / `baselineUnlockedSkills` / `baselineHeroes` / `baselineProfessions` / `baselineVanquishedMaps` — id sets or compact bit encodings
- `baselineHardModeUnlocked` — optional bool
- `baselineCartographyPercent` — optional uint
- `baselineSkillPointsEarned` / `baselineFactionTotals` — optional mirrors for threshold priors (may overlap existing snapshot fields; baseline seal time still needed so first sample does not emit)

On `AccountProgressStore`:

- `accountJourneyBaselineSealedAt`
- `baselineAccountSkills` — account skill ids

Existing fields keep their roles: `titles`, `last_known_level`, `last_map_id`, `hall_of_monuments`, `journey_events` (append-only milestones only).

### 3.3 Sealing rules

Seal a family only when:

- character identity is bound;
- world context is ready for that family’s source;
- for account skills: `game->account` present;
- sample is non-partial (**unknown** until Live proves partial-bitset behavior — if incomplete lists are possible, do not seal).

If context missing: leave `Unset`; do not clear prior seal; do not emit catch-up.

### 3.4 Delta rules

After seal, reuse existing builders with **baseline maps/amounts** as `previous_*` instead of `PriorIdsFromJourneyEvents` for unlock/threshold kinds. Continue fingerprint dedupe via `AppendUniqueJourneyEvents`.

---

## 4. JSON codec and version compatibility

| Item | Decision |
|------|----------|
| Format id | Keep `gwtoolbox-quest-progress` |
| Version | **Minor bump** `1.1 → 1.2` (additive optional baseline fields). Major bump not required if old readers ignore unknown fields and new readers tolerate absence |
| Old `1.0` / `1.1` files | Load via existing migrate-to-current path; then baseline fields absent → `Unset` |
| Reject | Newer major still rejected |
| Journey event schema | Unchanged (Contract v1 payload shape unchanged) |
| Do not | Rewrite or delete existing `journey_events` during migration |

Migration step for 1.2:

1. Canonicalize as today.
2. Leave baseline fields empty.
3. On **next successful complete sample** after upgrade:
   - If unlock/threshold journey events already exist for a family, **reconstruct baseline from those event ids/amounts** (and current snapshot), mark sealed, emit **no** new catch-up.
   - If no such events and complete sample available, seal from snapshot only (preferred for clean/new characters).
4. Never invent quest completions or delete history.

---

## 5. Reducer / service / live integration points

| Component | Change (planned) |
|-----------|------------------|
| `QuestCharacterJourney.*` | Add seal-aware wrappers or prior-from-baseline helpers; keep pure builders testable; stop using empty event-derived prior as “emit all” for unlocks when baseline policy active |
| `QuestProgressLive::SampleLiveJourneySnapshot` | Pass baseline priors; return seal updates + delta events only |
| `QuestProgressService::IngestJourneySnapshot` / `IngestHomSnapshot` | Persist baseline seal + snapshot fields; append only delta events |
| `QuestProgressStore` merge | Merge baseline sets by union; sealed flag sticky true once set; do not drop events |
| `QuestProgressJsonCodec` | 1.2 fields + migrate |
| `QuestProgressContractExporter` | No Contract schema change; export fewer false milestones; snapshots unchanged |
| `QuestProgressReducer` | No journey work |
| `QuestTrackerWindow` | No automation; may only call updated ingest APIs |

---

## 6. Contract export consequences

- Contract **v1 document unchanged** (this plan forbids editing Contract docs/meaning/version).
- Producer emits fewer `journeyEvents` on first track of veteran characters.
- Snapshot fields still carry current lifetime state for Wayfarer.
- `account_skill_unlock` remains under the character envelope when a **true delta** is observed while that character is active; account baseline prevents per-character re-flood.
- Fingerprint / canonical JSON rules unchanged.
- Existing noisy events already written to disk remain exportable until consumer strategy filters them (see §7–8).

---

## 7. Wayfarer UX consequences (no Wayfarer implementation here)

Observed today: dossier timeline `entries.take(40)`.

Recommended consumer-only strategies (future Wayfarer work, out of Toolbox scope):

- Prefer quest-progress / session-meaningful kinds when truncating.
- Collapse same-`observedAt` unlock bursts into a single “Already unlocked when tracking began” summary **for display**, without deleting imported rows.
- Treat `observedAt` as observation time in copy (avoid “earned at” wording for unlock floods).
- Do **not** auto-delete or rewrite imported history (append-only / evidence rules).

---

## 8. Migration and backward compatibility

| Scenario | Behavior |
|----------|----------|
| New character, empty store | Seal on first complete sample; few or no unlock events; `map_enter` / later deltas / timed clears as today |
| Veteran character, first Toolbox session | Seal without unlock catch-up flood |
| Store wipe / new folder | Same as first session (intentional re-seal; may miss pre-Toolbox history — observational limit) |
| Upgrade 1.1 → 1.2 with existing unlock flood events | Keep events; reconstruct baseline from them; stop further catch-up |
| Character switch | Per-character baseline; account skill baseline shared |
| Account switch | Different `account_key` store file; no cross-account merge |
| Missing world/account context | No seal; no empty baseline write; no event flood |
| Play without Toolbox, return later | Next complete sample deltas vs sealed baseline (new unlocks since last seal) |
| Already-exported Contract files with noise | Immutable producer artifacts; consumer display strategy only |

**History policy for existing noise:** do not erase; do not auto-rewrite evidence; optional consumer display filter only.

---

## 9. Scenario matrix (required answers)

| Scenario | Expected |
|----------|----------|
| New character first session | Seal near-empty unlock sets; emit real deltas as they happen; title/level as today |
| Old character first Toolbox session | Seal large unlock sets; **no** mass milestones |
| Restart with store | Load baseline; quiet unless delta |
| Restart without store | Re-seal; observational gap accepted |
| Old store upgrade | §4 + §8 |
| Character switch | No cross-character quest/journey contamination; account baseline shared |
| Account switch | Separate store |
| Partial/missing context | Hold seal; unknown completeness → do not seal |
| Return after offline play | Delta vs last seal |

---

## 10. Test matrix

Pure logic (`QuestProgressTests`):

1. Unlock family: first sample seals, **zero** events; second sample with +1 id → one event.
2. Same for skills, heroes, professions, vanquish, hard mode.
3. Account skills: seal on account store; character A first sample no flood; new account skill while on A → one `account_skill_unlock`; character B first sample does not re-emit A’s sealed skills.
4. Cartography / SP / faction thresholds: seal current max; no catch-up from 0; crossing next threshold emits.
5. HoM: first successful fetch seals without `hom_points` flood; later point increase emits.
6. Title/level/map_enter regression: existing tests stay green.
7. Timed clears unchanged.
8. Codec 1.1 → 1.2 round-trip preserves journey_events; baseline optional.
9. Upgrade path: store with pre-existing unlock events → reconstruct baseline → second sample quiet.
10. Missing account pointer → account skills unset, no empty seal, no flood.
11. Merge of two memory/disk characters unions baseline ids and keeps sealed.

Service-level (if harness allows): `IngestJourneySnapshot` does not append catch-up when sealing.

**Not unit-testable here:** GWCA bitset completeness on first tick — mark **unknown**; gate with in-game verification checklist.

Regression: exporter still emits valid Contract v1; fixture-style export tests remain green.

---

## 11. Implementation slices (order)

1. **Domain + codec 1.2** — baseline structs, serialize/parse, migrate stub, tests.
2. **Journey priors from baseline** — change Live/Service wiring for unlock kinds; pure tests for seal/delta.
3. **Thresholds + cartography + hard mode** — same pattern.
4. **Account skill baseline** on `AccountProgressStore`.
5. **HoM seal-on-first-fetch** without point flood.
6. **Upgrade reconstruction** from existing journey_events.
7. **Store merge** rules for baseline.
8. **In-game verification** checklist (Pre-Searing + veteran post-Searing unlock-heavy character).
9. **Wayfarer display follow-up** (separate repo/PR; not this plan’s code).

Do not combine with unlock-array Contract expansions or automation.

---

## 12. Risks and open questions

### Decided (from code)

- Unlock/threshold first sample is emit-all vs empty event-derived prior.
- Title/level already suppress-until-delta.
- Timed clears are game-message driven.
- Store minor is 1.1; journey has no source/confidence.
- Account skills are sampled from account context but stored under the active character’s `journey_events`.
- Wayfarer UI truncates timeline to 40 entries.
- Contaminated-store hygiene doc is about quest identity contamination, not journey baseline.

### Unknown (not invent)

- Whether unlock bitsets/lists can be incomplete on the first Persistent tick after map load.
- Whether `hero_info` / profession masks can temporarily omit owned entries.
- Ordering races between HoM async fetch and live unlock sampling.
- Whether Codex should ever soft-hide historical producer noise beyond UX truncation (product decision).
- Exact compact encoding for large bitsets on disk (implementation detail).
- Whether `map_enter` on very first sample should remain (recommended keep; not the flood problem).

### Risks

- Sealing on incomplete bitsets could suppress later “new” unlocks that were only late-loaded (**unknown** completeness).
- Reconstructing baseline from noisy events keeps bad timestamps in history (accepted; display-only mitigation).
- Account baseline in store is a new persistence surface; must not break accountKey validation.

---

## 13. Explicit non-goals

- Production C++ in this documentation PR
- Contract v1 schema / meaning / version changes
- Automatic deletion or rewrite of existing journey evidence
- Quest acceptance / movement / combat / reward automation
- Wayfarer code changes in this task
- Festival hats, deaths, gold-as-progress, PvP W/L journey kinds
- Exporting full unlock snapshot arrays (previously deferred enrichment)
- Unlock-baseline implementation merge without senior architecture approval

---

## 14. Answers to posed questions (summary)

1. **Snapshot-derived:** title, level, map_enter, vanquish_area, map/skill/account_skill/hero/profession unlock, hard_mode, cartography, SP/faction thresholds, hom_points. **Timed game messages:** mission/dungeon/vanquish_complete.
2. **Mass baseline:** unlock + vanquish_area + threshold + hom_points families above.
3. **Character vs account:** account skills are account-semantic; everything else listed is character (or character-envelope HoM).
4. **Store today:** cannot distinguish never-observed vs baseline-without-milestone vs new-since-baseline for unlocks; events double as prior.
5. **Needed baseline:** explicit sealed id sets / flags / max amounts (+ account skill set), separate from milestones.
6. **Version:** store **minor** 1.2; major not required for additive fields.
7. **Old files:** load, migrate minor, reconstruct or seal on next sample; keep all events.
8. **Existing noise:** retain; no auto-rewrite; consumer display strategy only.
9. **Account unlocks:** account-level baseline; Contract still nests delta events under the observing character.
10. **Append-only:** seal without appending; deltas append; history never erased.
11. **Scenarios:** see §9.
12. **Tests:** see §10.
