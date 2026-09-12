#include <Modules/QuestCharacterJourney.h>
#include <Modules/QuestProgressService.h>
#include <Modules/QuestSessionIdentity.h>

#include "test_assert.h"

#include <chrono>
#include <filesystem>
#include <string>

#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <Windows.h>

using namespace QuestProgress;

namespace {

std::filesystem::path MakeTempDir()
{
    wchar_t tmp[MAX_PATH]{};
    GetTempPathW(MAX_PATH, tmp);
    const auto base = std::filesystem::path(tmp) / L"gwtb_quest_progress_s2_raw_tests";
    std::error_code ec;
    std::filesystem::create_directories(base, ec);
    static uint32_t seq = 0;
    const auto dir = base / std::to_string(GetCurrentProcessId())
        / (std::to_string(GetTickCount64()) + "_" + std::to_string(seq++));
    std::filesystem::create_directories(dir, ec);
    return dir;
}

SessionIdentity PersistentId()
{
    return MakeSessionIdentity(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "11111111-2222-3333-4444-555555555555",
        "Hero",
        "W",
        false);
}

bool FamilyUnavailableDefault(const RawIdSetFamilyObservation& family)
{
    return !family.context_available && !family.sample_usable && family.value.empty();
}

bool FamilyUnavailableDefault(const RawFlagFamilyObservation& family)
{
    return !family.context_available && !family.sample_usable && !family.value;
}

bool FamilyUnavailableDefault(const RawFamilyObservation<uint32_t>& family)
{
    return !family.context_available && !family.sample_usable && family.value == 0;
}

bool FamilyUnavailableDefault(const RawFactionFamilyObservation& family)
{
    return !family.context_available
        && !family.sample_usable
        && family.value == FactionTotalsRecord{};
}

bool AllCharacterBaselinesUnset(const CharacterJourneyBaselines& baselines)
{
    return baselines.maps.state == JourneyBaselineSealState::Unset
        && baselines.character_skills.state == JourneyBaselineSealState::Unset
        && baselines.heroes.state == JourneyBaselineSealState::Unset
        && baselines.professions.state == JourneyBaselineSealState::Unset
        && baselines.vanquish_areas.state == JourneyBaselineSealState::Unset
        && baselines.hard_mode.state == JourneyBaselineSealState::Unset
        && baselines.skill_points.state == JourneyBaselineSealState::Unset
        && baselines.factions.state == JourneyBaselineSealState::Unset
        && baselines.hall_of_monuments.state == JourneyBaselineSealState::Unset
        && baselines.cartography.state == JourneyBaselineSealState::Unset;
}

void TestDefaultRawObservationUnavailable()
{
    const RawJourneyFloodObservation observation{};
    Expect(observation.observed_at.empty(), "raw_default_observed_at_empty");
    Expect(FamilyUnavailableDefault(observation.maps), "raw_default_maps");
    Expect(FamilyUnavailableDefault(observation.character_skills), "raw_default_character_skills");
    Expect(FamilyUnavailableDefault(observation.account_skills), "raw_default_account_skills");
    Expect(FamilyUnavailableDefault(observation.heroes), "raw_default_heroes");
    Expect(FamilyUnavailableDefault(observation.professions), "raw_default_professions");
    Expect(FamilyUnavailableDefault(observation.hard_mode), "raw_default_hard_mode");
    Expect(FamilyUnavailableDefault(observation.vanquish_areas), "raw_default_vanquish");
    Expect(FamilyUnavailableDefault(observation.cartography), "raw_default_cartography");
    Expect(FamilyUnavailableDefault(observation.skill_points), "raw_default_skill_points");
    Expect(FamilyUnavailableDefault(observation.factions), "raw_default_factions");
}

void TestContextUnavailableClearsUsable()
{
    auto ids = MakeRawIdSetFamilyObservation(false, true, {9, 1, 9});
    Expect(!ids.context_available, "raw_ctx_false_ids_ctx");
    Expect(!ids.sample_usable, "raw_ctx_false_ids_usable");
    Expect(ids.value.empty(), "raw_ctx_false_ids_value");

    auto flag = MakeRawFlagFamilyObservation(false, true, true);
    Expect(!flag.sample_usable && !flag.value, "raw_ctx_false_flag");

    auto percent = MakeRawPercentFamilyObservation(false, true, 55);
    Expect(!percent.sample_usable && percent.value == 0, "raw_ctx_false_percent");

    auto amount = MakeRawAmountFamilyObservation(false, true, 12);
    Expect(!amount.sample_usable && amount.value == 0, "raw_ctx_false_amount");

    FactionTotalsRecord totals;
    totals.kurzick = 100;
    auto factions = MakeRawFactionFamilyObservation(false, true, totals);
    Expect(!factions.sample_usable && factions.value == FactionTotalsRecord{}, "raw_ctx_false_factions");
}

void TestIdSetCanonicalization()
{
    auto family = MakeRawIdSetFamilyObservation(true, true, {5, 1, 5, 3, 1});
    Expect(family.sample_usable, "raw_id_canon_usable");
    Expect(family.value.size() == 3, "raw_id_canon_size");
    Expect(family.value[0] == 1 && family.value[1] == 3 && family.value[2] == 5, "raw_id_canon_order");

    auto unusable = MakeRawIdSetFamilyObservation(true, false, {4, 2});
    Expect(unusable.context_available, "raw_id_unusable_ctx");
    Expect(!unusable.sample_usable, "raw_id_unusable_flag");
    Expect(unusable.value.empty(), "raw_id_unusable_cleared");
}

void TestAccountIndependentOfCharacter()
{
    RawJourneyFloodObservation observation;
    observation.observed_at = "2026-09-12T10:00:00.000Z";
    observation.maps = MakeRawIdSetFamilyObservation(true, true, {73});
    observation.character_skills = MakeRawIdSetFamilyObservation(true, true, {42});
    observation.account_skills = MakeRawIdSetFamilyObservation(false, false, {7});
    NormalizeRawJourneyFloodObservation(observation);

    Expect(observation.maps.context_available && observation.maps.sample_usable, "raw_char_maps_ok");
    Expect(
        observation.character_skills.context_available && observation.character_skills.sample_usable,
        "raw_char_skills_ok");
    Expect(
        !observation.account_skills.context_available && !observation.account_skills.sample_usable,
        "raw_account_independent_unavailable");
    Expect(observation.account_skills.value.empty(), "raw_account_independent_empty");
}

void TestMissingProfessionOnly()
{
    RawJourneyFloodObservation observation;
    observation.observed_at = "2026-09-12T10:00:00.000Z";
    observation.maps = MakeRawIdSetFamilyObservation(true, true, {1});
    observation.heroes = MakeRawIdSetFamilyObservation(true, true, {2});
    observation.hard_mode = MakeRawFlagFamilyObservation(true, true, true);
    observation.professions = MakeRawIdSetFamilyObservation(false, false, {5});
    NormalizeRawJourneyFloodObservation(observation);

    Expect(observation.maps.sample_usable, "raw_prof_missing_maps_ok");
    Expect(observation.heroes.sample_usable, "raw_prof_missing_heroes_ok");
    Expect(observation.hard_mode.sample_usable && observation.hard_mode.value, "raw_prof_missing_hm_ok");
    Expect(!observation.professions.context_available, "raw_prof_missing_ctx");
    Expect(!observation.professions.sample_usable, "raw_prof_missing_usable");
    Expect(observation.professions.value.empty(), "raw_prof_missing_value");
}

JourneySnapshotResult MakeRawOnlySnapshot(RawJourneyFloodObservation raw)
{
    JourneySnapshotResult snapshot;
    snapshot.raw_flood = std::move(raw);
    NormalizeRawJourneyFloodObservation(snapshot.raw_flood);
    return snapshot;
}

void TestRawFloodIngestCreatesNoEventsAndLeavesBaselinesUnset()
{
    const auto dir = MakeTempDir();
    QuestProgressService svc;
    svc.Initialize();
    svc.SetStoreDirectory(dir);
    svc.BindIdentity(PersistentId());

    RawJourneyFloodObservation raw;
    raw.observed_at = "2026-09-12T10:00:00.000Z";
    raw.maps = MakeRawIdSetFamilyObservation(true, true, {73, 12});
    raw.character_skills = MakeRawIdSetFamilyObservation(true, true, {42});
    raw.account_skills = MakeRawIdSetFamilyObservation(true, true, {7});
    raw.heroes = MakeRawIdSetFamilyObservation(true, true, {1, 9});
    raw.professions = MakeRawIdSetFamilyObservation(true, true, {5});
    raw.vanquish_areas = MakeRawIdSetFamilyObservation(true, true, {22});
    raw.hard_mode = MakeRawFlagFamilyObservation(true, true, true);
    raw.cartography = MakeRawPercentFamilyObservation(true, true, 50);
    raw.skill_points = MakeRawAmountFamilyObservation(true, true, 50);
    FactionTotalsRecord factions;
    factions.kurzick = 10000;
    factions.luxon = 5000;
    raw.factions = MakeRawFactionFamilyObservation(true, true, factions);

    auto snapshot = MakeRawOnlySnapshot(std::move(raw));
    snapshot.experience_total = 12345;
    snapshot.skill_points_earned = 50;
    snapshot.faction_totals = factions;

    Expect(IsCanonicalUtcTimestamp(snapshot.raw_flood.observed_at), "raw_ingest_observed_at_utc");
    svc.IngestJourneySnapshot(std::move(snapshot));

    const auto& store = svc.account_store();
    Expect(store.characters.size() == 1, "raw_ingest_character_present");
    const auto& character = store.characters.begin()->second;
    Expect(character.journey_events.empty(), "raw_ingest_no_flood_events");
    Expect(AllCharacterBaselinesUnset(character.journey_baselines), "raw_ingest_baselines_unset");
    Expect(
        store.account_skill_baseline.state == JourneyBaselineSealState::Unset,
        "raw_ingest_account_baseline_unset");
    Expect(character.experience_total == 12345u, "raw_ingest_experience");
    Expect(character.skill_points_earned == 50u, "raw_ingest_skill_points");
    Expect(character.faction_totals.has_value(), "raw_ingest_factions_present");
    Expect(character.faction_totals->kurzick == 10000u, "raw_ingest_faction_kurzick");
    Expect(character.faction_totals->luxon == 5000u, "raw_ingest_faction_luxon");
}

void TestNonFloodEventsStillIngest()
{
    const auto dir = MakeTempDir();
    QuestProgressService svc;
    svc.Initialize();
    svc.SetStoreDirectory(dir);
    svc.BindIdentity(PersistentId());

    JourneySnapshotResult snapshot;
    snapshot.level = 5;
    snapshot.observed_map_id = 73;
    snapshot.experience_total = 99;
    snapshot.raw_flood.observed_at = "2026-09-12T11:00:00.000Z";
    snapshot.raw_flood.maps = MakeRawIdSetFamilyObservation(true, true, {73});
    NormalizeRawJourneyFloodObservation(snapshot.raw_flood);

    JourneyEventRecord level_up;
    level_up.kind = "level_up";
    level_up.subject_key = BuildLevelSubjectKey(5);
    level_up.observed_at = "2026-09-12T11:00:00.000Z";
    level_up.level = 5;
    snapshot.new_events.push_back(level_up);

    JourneyEventRecord map_enter;
    map_enter.kind = "map_enter";
    map_enter.subject_key = BuildMapSubjectKey(73);
    map_enter.observed_at = "2026-09-12T11:00:00.000Z";
    map_enter.map_id = 73;
    snapshot.new_events.push_back(map_enter);

    svc.IngestJourneySnapshot(std::move(snapshot));
    const auto& character = svc.account_store().characters.begin()->second;
    Expect(character.journey_events.size() == 2, "raw_nonflood_event_count");
    Expect(character.journey_events[0].kind == "level_up", "raw_nonflood_level");
    Expect(character.journey_events[1].kind == "map_enter", "raw_nonflood_map_enter");
    Expect(AllCharacterBaselinesUnset(character.journey_baselines), "raw_nonflood_baselines_unset");
    Expect(IsCanonicalUtcTimestamp(character.journey_events[0].observed_at), "raw_nonflood_utc");
}

void TestCartographyUsabilityHelper()
{
    const uint32_t bits[1] = {0xFFu};
    Expect(IsCartographyBufferUsable(bits, 1, 8, 1), "carto_usable_ok");
    Expect(!IsCartographyBufferUsable(nullptr, 1, 8, 1), "carto_usable_null");
    Expect(!IsCartographyBufferUsable(bits, 0, 8, 1), "carto_usable_empty");
    Expect(!IsCartographyBufferUsable(bits, 1, 0, 1), "carto_usable_width");
    Expect(!IsCartographyBufferUsable(bits, 1, 8, 0), "carto_usable_height");
}

} // namespace

void RunJourneyRawObservationTests()
{
    TestDefaultRawObservationUnavailable();
    TestContextUnavailableClearsUsable();
    TestIdSetCanonicalization();
    TestAccountIndependentOfCharacter();
    TestMissingProfessionOnly();
    TestRawFloodIngestCreatesNoEventsAndLeavesBaselinesUnset();
    TestNonFloodEventsStillIngest();
    TestCartographyUsabilityHelper();
}
