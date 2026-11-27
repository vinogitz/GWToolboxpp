import contextlib
import copy
import io
import json
import os
import sys
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import quest_catalog as qc

FIXTURES = os.path.join(HERE, "fixtures")
CATALOG_DIR = os.path.join(ROOT, "docs", "quest-tracker", "catalog")
REAL_CATALOG = os.path.join(CATALOG_DIR, "presearing-quest-catalog.v1.json")
SCHEMA = qc.load_json(os.path.join(CATALOG_DIR, "quest-catalog.schema.v1.json"))


def fixture(name):
    return os.path.join(FIXTURES, name)


def real_catalog():
    return qc.load_json(REAL_CATALOG)


def synthetic_catalog():
    return qc.load_json(fixture("synthetic-chain-catalog.v1.json"))


def quest(catalog, key):
    return next(q for q in catalog["quests"] if q["key"] == key)


def codes(catalog):
    return {e["code"] for e in qc.validate_catalog(catalog, SCHEMA)}


def characters(report):
    return {c["characterKey"]: c for f in report["files"] for c in f["characters"]}


def row(character, game_id):
    return next(r for r in character["quests"] if r["gameQuestId"] == game_id)


class CatalogValidity(unittest.TestCase):
    def test_real_catalog_is_valid(self):
        self.assertEqual(qc.validate_catalog(real_catalog(), SCHEMA), [])

    def test_synthetic_catalog_is_valid(self):
        self.assertEqual(qc.validate_catalog(synthetic_catalog(), SCHEMA), [])

    def test_pilot_metadata(self):
        catalog = real_catalog()
        self.assertEqual(catalog["dataCaptureReady"], "NOT_READY")
        self.assertFalse(catalog["scope"]["synthetic"])
        self.assertEqual(catalog["linkPolicy"]["autoLinkStatuses"], ["verified_in_game"])
        self.assertEqual([q["key"] for q in catalog["quests"] if q["idVerification"]["status"] == "verified_in_game"], ["presearing.getting_started_in_guild_wars"])

    def test_war_preparations_unchanged_ambiguous(self):
        catalog = real_catalog()
        war = quest(catalog, "presearing.war_preparations")
        self.assertIsNone(war["gameQuestId"])
        self.assertEqual(war["idVerification"]["status"], "ambiguous")
        self.assertEqual(war["candidateGameQuestIds"], [35, 217, 218, 219, 220, 221, 222])
        self.assertEqual(war["requires_completion_of"], [])
        self.assertEqual(war["profession"], "unknown")
        self.assertEqual(len(war["related_follow_up"]), 5)

    def test_no_verbatim_quote_fields_anywhere(self):
        def keys(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield key
                    yield from keys(value)
            elif isinstance(node, list):
                for item in node:
                    yield from keys(item)
        for name in os.listdir(FIXTURES):
            if name.endswith(".json"):
                with self.subTest(name):
                    try:
                        document = qc.load_json(fixture(name))
                    except ValueError:
                        continue
                    self.assertNotIn("quote", set(keys(document)))
        self.assertNotIn("quote", set(keys(real_catalog())))
        self.assertNotIn("quote", set(keys(SCHEMA)))

    def test_documentation_links_to_catalog_readme(self):
        doc = os.path.join(ROOT, "docs", "quest-tracker", "data-availability.md")
        with open(doc, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("(catalog/README.md)", text)
        self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(doc), "catalog", "README.md")))

    def test_case_same_id_objective_change(self):
        entry = quest(real_catalog(), "presearing.getting_started_in_guild_wars")
        self.assertEqual(entry["gameQuestId"], 1462)
        self.assertEqual(entry["objectives"]["model"], "sequential_same_id")
        self.assertGreaterEqual(len(entry["objectives"]["stages"]), 2)
        self.assertEqual(entry["region"], "ascalon_pre_searing")
        self.assertEqual(entry["idVerification"]["status"], "verified_in_game")
        in_game = [e for e in entry["idVerification"]["evidence"] if e["kind"] == "in_game_game_link"]
        self.assertEqual(len(in_game), 1)
        evidence = in_game[0]
        self.assertEqual(evidence["sourceId"], "in-game-f10-help-quest-1462-2026-11-27")
        self.assertEqual(evidence["value"], 1462)
        self.assertEqual(evidence["observedName"], "Getting Started in Guild Wars")
        self.assertEqual(evidence["campaignContext"], "prophecies")
        self.assertEqual(evidence["professionContext"], "monk")
        self.assertIs(evidence["preRedirect"], True)
        source = next(s for s in real_catalog()["sources"] if s["id"] == evidence["sourceId"])
        self.assertIn("rdfrom=", source["url"])
        self.assertIn("Game_link:Quest_1462", urllib.parse.unquote(source["url"]))
        self.assertIn("403", evidence["note"])
        self.assertIn("rdfrom", evidence["note"])
        self.assertIn("F10 Help panel", evidence["note"])
        self.assertIn("Toolbox not loaded", evidence["note"])

    def test_case_separate_id_chain(self):
        catalog = real_catalog()
        tests = {"presearing.%s_test" % p for p in ("warrior", "ranger", "monk", "necromancer", "mesmer", "elementalist")}
        further = quest(catalog, "presearing.further_adventures")
        self.assertEqual(set(further["requires_completion_of"][0]["anyOf"]), tests)
        monk = quest(catalog, "presearing.monk_test")
        self.assertEqual(monk["requires_completion_of"], [])
        self.assertIn("presearing.further_adventures", {f["target"] for f in monk["related_follow_up"]})
        war = quest(catalog, "presearing.war_preparations")
        self.assertIn("presearing.monk_test", {f["target"] for f in war["related_follow_up"]})
        required_anywhere = {t for q in catalog["quests"] for r in q["requires_completion_of"] for t in r["anyOf"]}
        self.assertNotIn("presearing.war_preparations", required_anywhere)
        self.assertIsNone(war["gameQuestId"])
        self.assertEqual(war["idVerification"]["status"], "ambiguous")
        self.assertEqual(len({monk["gameQuestId"], further["gameQuestId"]}), 2)


class CatalogRejections(unittest.TestCase):
    def mutate(self, change):
        catalog = synthetic_catalog()
        change(catalog)
        return codes(catalog)

    def test_schema_bad_enum(self):
        self.assertIn("schema", self.mutate(lambda c: quest(c, "synthetic.quest_a")["completion"].update(mode="finished")))

    def test_schema_unknown_field(self):
        self.assertIn("schema", self.mutate(lambda c: quest(c, "synthetic.quest_a").update(questName="x")))

    def test_schema_missing_required(self):
        self.assertIn("schema", self.mutate(lambda c: quest(c, "synthetic.quest_a").pop("related_follow_up")))

    def test_schema_bool_is_not_integer(self):
        self.assertIn("schema", self.mutate(lambda c: quest(c, "synthetic.quest_a").update(gameQuestId=True)))

    def test_duplicate_key(self):
        self.assertIn("duplicate_key", self.mutate(lambda c: quest(c, "synthetic.quest_c").update(key="synthetic.quest_a")))

    def test_duplicate_game_quest_id(self):
        def change(c):
            entry = quest(c, "synthetic.quest_b")
            entry["gameQuestId"] = 900101
            entry["idVerification"]["evidence"][0]["value"] = 900101
        self.assertIn("duplicate_game_quest_id", self.mutate(change))

    def test_unknown_required_target(self):
        self.assertIn("unknown_target", self.mutate(lambda c: quest(c, "synthetic.quest_b")["requires_completion_of"][0]["anyOf"].append("synthetic.missing")))

    def test_unknown_follow_up_target(self):
        self.assertIn("unknown_target", self.mutate(lambda c: quest(c, "synthetic.quest_a")["related_follow_up"][0].update(target="synthetic.missing")))

    def test_self_reference_required(self):
        self.assertIn("self_reference", self.mutate(lambda c: quest(c, "synthetic.quest_b")["requires_completion_of"][0]["anyOf"].append("synthetic.quest_b")))

    def test_self_reference_follow_up(self):
        self.assertIn("self_reference", self.mutate(lambda c: quest(c, "synthetic.quest_a")["related_follow_up"][0].update(target="synthetic.quest_a")))

    def test_required_cycle(self):
        found = self.mutate(lambda c: quest(c, "synthetic.quest_a")["requires_completion_of"].append({"anyOf": ["synthetic.quest_b"], "sourceId": "synthetic-fixture", "basis": "cycle"}))
        self.assertIn("required_cycle", found)

    def test_follow_up_loop_is_not_a_required_cycle(self):
        found = self.mutate(lambda c: quest(c, "synthetic.quest_b")["related_follow_up"].append({"target": "synthetic.quest_a", "sourceId": "synthetic-fixture"}))
        self.assertEqual(found, set())

    def test_policy_cannot_autolink_unverified(self):
        self.assertIn("link_policy_autolinks_unverified", self.mutate(lambda c: c["linkPolicy"].update(autoLinkStatuses=["verified_in_game", "corroborated"], candidateStatuses=["source_claimed"])))

    def test_verified_needs_in_game_evidence(self):
        self.assertIn("verified_without_in_game_evidence", self.mutate(lambda c: quest(c, "synthetic.quest_c")["idVerification"].update(status="verified_in_game")))

    def test_name_match_or_page_id_alone_is_not_identifying(self):
        def change(c):
            quest(c, "synthetic.quest_c")["idVerification"]["evidence"] = [qc_e("name_match", 900103), qc_e("wiki_page_id", 900103)]
        self.assertIn("status_without_identifying_evidence", self.mutate(change))

    def test_wiki_only_is_not_corroborated(self):
        def change(c):
            quest(c, "synthetic.quest_c")["idVerification"]["evidence"] = [qc_e("wiki_game_link", 900103), qc_e("wiki_infobox_id", 900103)]
        self.assertIn("corroborated_without_independent_evidence", self.mutate(change))

    def test_evidence_value_conflict(self):
        self.assertIn("evidence_value_conflict", self.mutate(lambda c: quest(c, "synthetic.quest_c")["idVerification"]["evidence"][0].update(value=900199)))

    def test_candidate_collision(self):
        def change(c):
            entry = quest(c, "synthetic.quest_d")
            entry["idVerification"]["status"] = "ambiguous"
            entry["candidateGameQuestIds"] = [900101, 900198]
        self.assertIn("candidate_id_collision", self.mutate(change))

    def test_unknown_entry_cannot_carry_id(self):
        self.assertIn("status_requires_null_id", self.mutate(lambda c: quest(c, "synthetic.quest_d").update(gameQuestId=900105)))

    def test_synthetic_id_range(self):
        def change(c):
            entry = quest(c, "synthetic.quest_c")
            entry["gameQuestId"] = 84
            for e in entry["idVerification"]["evidence"]:
                e["value"] = 84
        self.assertIn("synthetic_id_range", self.mutate(change))

    def test_unknown_source_ref(self):
        self.assertIn("unknown_source_ref", self.mutate(lambda c: quest(c, "synthetic.quest_a")["sourceIds"].append("missing-source")))

    def test_verified_needs_name_bound_to_id(self):
        def change(c):
            quest(c, "synthetic.quest_a")["idVerification"]["evidence"][0].pop("observedName")
        self.assertIn("verified_observation_incomplete", self.mutate(change))

    def test_verified_name_must_match_entry(self):
        self.assertIn("verified_observation_incomplete", self.mutate(lambda c: quest(c, "synthetic.quest_a")["idVerification"]["evidence"][0].update(observedName="Synthetic Quest Z")))

    def test_verified_needs_campaign_and_profession_context(self):
        self.assertIn("verified_observation_incomplete", self.mutate(lambda c: quest(c, "synthetic.quest_a")["idVerification"]["evidence"][0].update(professionContext="unknown")))
        self.assertIn("verified_observation_incomplete", self.mutate(lambda c: quest(c, "synthetic.quest_a")["idVerification"]["evidence"][0].update(campaignContext="nightfall")))

    def test_game_link_must_be_pre_redirect(self):
        self.assertIn("verified_observation_incomplete", self.mutate(lambda c: quest(c, "synthetic.quest_a")["idVerification"]["evidence"][0].update(preRedirect=False)))

    def test_verified_rejects_name_taken_from_a_different_evidence_record(self):
        def change(c):
            evidence = quest(c, "synthetic.quest_a")["idVerification"]["evidence"]
            link = evidence[0]
            name = link.pop("observedName")
            evidence.append({"kind": "name_match", "sourceId": "synthetic-wiki", "value": link["value"], "observedName": name})
        self.assertIn("verified_observation_incomplete", self.mutate(change))

    def test_verified_rejects_binding_fields_moved_onto_wiki_id_evidence(self):
        def change(c):
            entry = quest(c, "synthetic.quest_a")
            link = entry["idVerification"]["evidence"][0]
            wiki = {"kind": "wiki_infobox_id", "sourceId": "synthetic-wiki", "value": link["value"]}
            for key in ("observedName", "campaignContext", "professionContext", "preRedirect"):
                wiki[key] = link.pop(key)
            entry["idVerification"]["evidence"].append(wiki)
        self.assertIn("verified_observation_incomplete", self.mutate(change))

    def test_hand_looked_up_wiki_link_cannot_verify(self):
        def change(c):
            entry = quest(c, "synthetic.quest_c")
            entry["idVerification"]["status"] = "verified_in_game"
            entry["idVerification"]["evidence"].append(qc_e("wiki_game_link", 900103))
        self.assertIn("verified_without_in_game_evidence", self.mutate(change))

    def test_quote_field_is_rejected(self):
        self.assertIn("schema", self.mutate(lambda c: quest(c, "synthetic.quest_a")["completion"].update(quote="x")))
        self.assertIn("schema", self.mutate(lambda c: quest(c, "synthetic.quest_a")["notes"].append({"sourceId": "synthetic-fixture", "quote": "x"}) if "notes" in quest(c, "synthetic.quest_a") else quest(c, "synthetic.quest_a").update(notes=[{"sourceId": "synthetic-fixture", "quote": "x"}])))

    def test_old_stage_text_field_is_rejected(self):
        self.assertIn("schema", self.mutate(lambda c: quest(c, "synthetic.quest_a")["objectives"]["stages"][0].update(text="x")))

    def test_sequential_needs_two_stages(self):
        self.assertIn("sequential_needs_stages", self.mutate(lambda c: quest(c, "synthetic.quest_b")["objectives"].update(model="sequential_same_id")))


def in_game_evidence(entry, source_id, **override):
    evidence = {"kind": "in_game_game_link", "sourceId": source_id, "value": entry["gameQuestId"], "observedName": entry["name"], "campaignContext": entry["campaign"], "professionContext": "any", "preRedirect": True}
    evidence.update(override)
    return evidence


def qc_e(kind, value):
    return {"kind": kind, "sourceId": "synthetic-fixture", "value": value}


class Linking(unittest.TestCase):
    def link(self, catalog, *names):
        return qc.link_exports(catalog, [fixture(n) for n in names])

    def test_b_present_a_without_closure_stays_uncertain(self):
        report = self.link(synthetic_catalog(), "export-b-without-a-closure.contract-v1.json")
        character = characters(report)["synthetic-char-1"]
        prereq = next(p for p in character["prerequisites"] if p["followUp"] == "synthetic.quest_b")
        self.assertEqual(prereq["closure"], "uncertain")
        self.assertEqual(prereq["reason"], "prerequisite_observed_without_closure_evidence")
        self.assertEqual(prereq["evidence"], [])
        self.assertEqual(row(character, 900101)["state"], "objective_progress")

    def test_b_present_a_absent_stays_uncertain(self):
        report = self.link(synthetic_catalog(), "export-b-a-absent.contract-v1.json")
        prereq = characters(report)["synthetic-char-3"]["prerequisites"][0]
        self.assertEqual((prereq["closure"], prereq["reason"]), ("uncertain", "prerequisite_absent_from_export"))

    def test_a_closure_evidence_keeps_its_confidence(self):
        report = self.link(synthetic_catalog(), "export-b-with-a-closure.contract-v1.json")
        prereq = characters(report)["synthetic-char-2"]["prerequisites"][0]
        self.assertEqual(prereq["closure"], "evidenced")
        self.assertEqual({(e["state"], e["source"], e["confidence"]) for e in prereq["evidence"]}, {("completed_observed", "game_event", "probable")})

    def test_unverified_prerequisite_is_not_linkable(self):
        report = self.link(synthetic_catalog(), "export-b-without-a-closure.contract-v1.json")
        character = characters(report)["synthetic-char-1"]
        prereq = next(p for p in character["prerequisites"] if p["followUp"] == "synthetic.quest_e")
        self.assertEqual((prereq["closure"], prereq["reason"]), ("uncertain", "prerequisite_not_linkable"))
        self.assertEqual(row(character, 900103)["linkState"], "candidate")

    def test_unknown_id_does_not_break_processing(self):
        report = self.link(synthetic_catalog(), "export-b-without-a-closure.contract-v1.json")
        character = characters(report)["synthetic-char-1"]
        self.assertEqual(row(character, 900999)["linkState"], "unmatched")
        self.assertEqual(row(character, 900102)["linkState"], "linked")
        self.assertEqual(report["issues"], [])

    def test_malformed_and_unreadable_inputs_are_reported_not_fatal(self):
        report = self.link(synthetic_catalog(), "export-malformed-records.contract-v1.json", "not-a-contract.json", "unreadable.json", "export-b-a-absent.contract-v1.json")
        issue_codes = [i["code"] for i in report["issues"]]
        self.assertEqual(issue_codes.count("invalid_quest_record"), 4)
        self.assertIn("not_contract_v1", issue_codes)
        self.assertIn("unreadable_export", issue_codes)
        found = characters(report)
        self.assertEqual(row(found["synthetic-char-4"], 900102)["linkState"], "linked")
        self.assertIn("synthetic-char-3", found)

    def test_real_catalog_autolinks_only_verified_getting_started(self):
        report = self.link(real_catalog(), "export-presearing-derived.contract-v1.json")
        self.assertEqual(report["counts"], {"ambiguous_candidate": 1, "candidate": 6, "linked": 4})
        found = characters(report)
        for key in ("derived-monk-a", "derived-monk-b", "derived-mesmer-c", "hypothetical-monk-d"):
            self.assertEqual(row(found[key], 1462)["linkState"], "linked")
        self.assertEqual(row(found["derived-monk-b"], 220)["linkState"], "ambiguous_candidate")
        self.assertEqual(row(found["derived-monk-a"], 84)["linkState"], "candidate")
        self.assertTrue(all(not c["prerequisites"] for c in found.values()))

    def test_real_catalog_links_1462_while_unverified_84_stays_candidate(self):
        catalog = real_catalog()
        self.assertEqual(quest(catalog, "presearing.getting_started_in_guild_wars")["idVerification"]["status"], "verified_in_game")
        self.assertEqual(quest(catalog, "presearing.monk_test")["idVerification"]["status"], "corroborated")
        report = self.link(catalog, "export-presearing-derived.contract-v1.json")
        character = characters(report)["derived-monk-a"]
        self.assertEqual(row(character, 1462)["linkState"], "linked")
        self.assertEqual(row(character, 84)["linkState"], "candidate")
        linked_ids = {r["gameQuestId"] for c in characters(report).values() for r in c["quests"] if r["linkState"] == "linked"}
        self.assertEqual(linked_ids, {1462})

    def test_real_ids_after_hypothetical_promotion(self):
        catalog = copy.deepcopy(real_catalog())
        catalog["sources"].append({"id": "what-if-in-game-check", "kind": "synthetic_fixture", "title": "Test-only promotion", "retrievedAt": "2026-11-26"})
        for key in ("presearing.monk_test", "presearing.further_adventures"):
            entry = quest(catalog, key)
            entry["idVerification"]["status"] = "verified_in_game"
            entry["idVerification"]["evidence"].append(in_game_evidence(entry, "what-if-in-game-check"))
        self.assertEqual(qc.validate_catalog(catalog, SCHEMA), [])
        found = characters(self.link(catalog, "export-presearing-derived.contract-v1.json"))
        evidenced = found["derived-monk-a"]["prerequisites"][0]
        self.assertEqual(evidenced["closure"], "evidenced")
        self.assertEqual(evidenced["evidence"][0]["confidence"], "probable")
        hypothetical = found["hypothetical-monk-d"]["prerequisites"][0]
        self.assertEqual((hypothetical["closure"], hypothetical["reason"]), ("uncertain", "prerequisite_absent_from_export"))
        self.assertEqual(row(found["hypothetical-monk-d"], 1462)["linkState"], "linked")


class CommandLine(unittest.TestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = qc.main(argv)
        return code, out.getvalue()

    def test_validate_exit_codes(self):
        self.assertEqual(self.run_main(["validate", REAL_CATALOG, fixture("synthetic-chain-catalog.v1.json")])[0], 0)
        self.assertEqual(self.run_main(["validate", fixture("not-a-contract.json")])[0], 1)

    def test_link_summary_runs_on_directory(self):
        code, text = self.run_main(["link", fixture("synthetic-chain-catalog.v1.json"), FIXTURES, "--summary"])
        self.assertEqual(code, 0)
        report = json.loads(text)
        self.assertEqual(report["report"], "gwtoolbox-quest-catalog-link-report")
        self.assertEqual(report["counts"], {"candidate": 1, "linked": 7, "unmatched": 12})
        self.assertEqual([i["code"] for i in report["issues"]], ["invalid_quest_record"] * 4)


if __name__ == "__main__":
    unittest.main()
