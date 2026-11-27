import argparse
import json
import os
import re
import sys
import urllib.parse

CATALOG_ID = "gwtoolbox-quest-catalog"
REPORT_ID = "gwtoolbox-quest-catalog-link-report"
CONTRACT_ID = "guild-wars-quest-progress"
SYNTHETIC_ID_FLOOR = 900000
DEFAULT_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "quest-tracker", "catalog", "quest-catalog.schema.v1.json")

GAME_ID_KINDS = {"in_game_game_link", "producer_name_id_pair"}
WIKI_ID_KINDS = {"wiki_infobox_id", "wiki_game_link", "wiki_game_integration_table"}
NON_WIKI_ID_KINDS = {"toolbox_live_observation", "repo_code_reference", "gwca_constant"}
NON_IDENTIFYING_KINDS = {"wiki_page_id", "name_match"}
UNVERIFIED_STATUSES = {"corroborated", "source_claimed", "ambiguous", "unknown"}
CLOSURE_STATES = {"completed_observed", "completed_manual"}


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def type_matches(value, expected):
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": is_int,
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    return checks[expected](value)


def resolve_ref(root, ref):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def schema_errors(value, schema, root, path="$"):
    if "$ref" in schema:
        return schema_errors(value, resolve_ref(root, schema["$ref"]), root, path)
    errors = []
    if "type" in schema:
        expected = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(type_matches(value, t) for t in expected):
            return [(path, "type", f"expected {'|'.join(expected)}")]
    if "const" in schema and value != schema["const"]:
        errors.append((path, "const", f"expected {schema['const']!r}"))
    if "enum" in schema and value not in schema["enum"]:
        errors.append((path, "enum", f"{value!r} not in {schema['enum']}"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append((path, "minLength", "too short"))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append((path, "pattern", f"{value!r} !~ {schema['pattern']}"))
    if is_int(value) and "minimum" in schema and value < schema["minimum"]:
        errors.append((path, "minimum", f"{value} < {schema['minimum']}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append((path, "minItems", f"fewer than {schema['minItems']} items"))
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(seen) != len(set(seen)):
                errors.append((path, "uniqueItems", "duplicate items"))
        if "items" in schema:
            for index, item in enumerate(value):
                errors += schema_errors(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append((path, "required", f"missing {name}"))
        props = schema.get("properties", {})
        for name, item in value.items():
            if name in props:
                errors += schema_errors(item, props[name], root, f"{path}.{name}")
            elif schema.get("additionalProperties") is False:
                errors.append((path, "additionalProperties", f"unexpected {name}"))
    return errors


def find_required_cycles(quests_by_key):
    graph = {key: sorted({t for req in q.get("requires_completion_of", []) for t in req.get("anyOf", []) if t in quests_by_key}) for key, q in quests_by_key.items()}
    state = {}
    cycles = []

    def visit(node, stack):
        state[node] = "open"
        stack.append(node)
        for nxt in graph[node]:
            if state.get(nxt) == "open":
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif nxt not in state:
                visit(nxt, stack)
        stack.pop()
        state[node] = "done"

    for key in sorted(graph):
        if key not in state:
            visit(key, [])
    return cycles


GAME_LINK_TITLE_RE = re.compile(r"Game[_ ]link:Quest[_ ](\d+)", re.IGNORECASE)


def game_link_id_from_rdfrom(url):
    if not isinstance(url, str):
        return None
    rdfrom_vals = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("rdfrom")
    if not rdfrom_vals:
        return None
    raw = rdfrom_vals[0]
    inner = urllib.parse.urlparse(raw)
    titles = urllib.parse.parse_qs(inner.query).get("title")
    haystack = titles[0] if titles else urllib.parse.unquote(inner.path or "")
    match = GAME_LINK_TITLE_RE.search(haystack) or GAME_LINK_TITLE_RE.search(raw)
    return int(match.group(1)) if match else None


def in_game_observation_binds(evidence, quest):
    if evidence.get("observedName") != quest["name"] or evidence.get("campaignContext") != quest["campaign"]:
        return False
    if evidence.get("professionContext") in (None, "unknown"):
        return False
    return evidence["kind"] != "in_game_game_link" or evidence.get("preRedirect") is True


def validate_catalog(catalog, schema):
    errors = [{"code": "schema", "path": p, "rule": r, "message": m} for p, r, m in schema_errors(catalog, schema, schema)]
    if errors:
        return errors

    def err(code, path, message):
        errors.append({"code": code, "path": path, "message": message})

    source_ids = [s["id"] for s in catalog["sources"]]
    for sid in sorted({s for s in source_ids if source_ids.count(s) > 1}):
        err("duplicate_source_id", "$.sources", sid)
    known_sources = set(source_ids)
    sources_by_id = {s["id"]: s for s in catalog["sources"]}

    policy = catalog["linkPolicy"]
    buckets = [set(policy["autoLinkStatuses"]), set(policy["candidateStatuses"]), set(policy["neverLinkStatuses"])]
    if buckets[0] & buckets[1] or buckets[0] & buckets[2] or buckets[1] & buckets[2]:
        err("link_policy_overlap", "$.linkPolicy", "a status appears in more than one bucket")
    if buckets[0] & UNVERIFIED_STATUSES:
        err("link_policy_autolinks_unverified", "$.linkPolicy.autoLinkStatuses", ",".join(sorted(buckets[0] & UNVERIFIED_STATUSES)))

    synthetic = catalog["scope"]["synthetic"]
    quests = catalog["quests"]
    keys = [q["key"] for q in quests]
    for key in sorted({k for k in keys if keys.count(k) > 1}):
        err("duplicate_key", "$.quests", key)
    quests_by_key = {q["key"]: q for q in quests}

    id_owner = {}
    for q in quests:
        if q["gameQuestId"] is not None:
            if q["gameQuestId"] in id_owner:
                err("duplicate_game_quest_id", f"$.quests[{q['key']}]", f"{q['gameQuestId']} also on {id_owner[q['gameQuestId']]}")
            else:
                id_owner[q["gameQuestId"]] = q["key"]
    for q in quests:
        for cid in q["candidateGameQuestIds"]:
            if cid in id_owner and id_owner[cid] != q["key"]:
                err("candidate_id_collision", f"$.quests[{q['key']}].candidateGameQuestIds", f"{cid} is gameQuestId of {id_owner[cid]}")

    for evidence in catalog.get("numberingEvidence", []):
        for sid in evidence["sourceIds"]:
            if sid not in known_sources:
                err("unknown_source_ref", "$.numberingEvidence", sid)

    for q in quests:
        path = f"$.quests[{q['key']}]"
        refs = list(q["sourceIds"])
        refs += [e["sourceId"] for e in q["idVerification"]["evidence"]]
        refs += [r["sourceId"] for r in q["requires_completion_of"]]
        refs += [f["sourceId"] for f in q["related_follow_up"]]
        refs += [f["sourceId"] for f in q.get("outOfScopeFollowUps", [])]
        refs += [n["sourceId"] for n in q.get("notes", [])]
        refs += [block["sourceId"] for block in (q["objectives"], q["completion"], q["branching"]) if "sourceId" in block]
        for sid in sorted(set(refs)):
            if sid not in known_sources:
                err("unknown_source_ref", path, sid)

        game_id = q["gameQuestId"]
        if game_id is not None:
            if synthetic and game_id < SYNTHETIC_ID_FLOOR:
                err("synthetic_id_range", path, f"synthetic catalog id {game_id} < {SYNTHETIC_ID_FLOOR}")
            if not synthetic and game_id >= SYNTHETIC_ID_FLOOR:
                err("synthetic_id_range", path, f"real catalog id {game_id} >= {SYNTHETIC_ID_FLOOR}")

        status = q["idVerification"]["status"]
        evidence = q["idVerification"]["evidence"]
        kinds = {e["kind"] for e in evidence}
        identifying = [e for e in evidence if e["kind"] not in NON_IDENTIFYING_KINDS]
        for e in evidence:
            if e.get("kind") != "in_game_game_link":
                continue
            source = sources_by_id.get(e.get("sourceId"))
            parsed = game_link_id_from_rdfrom((source or {}).get("url"))
            if parsed is not None and parsed != e.get("value"):
                err("in_game_rdfrom_id_mismatch", path, f"rdfrom Game link:Quest {parsed} != value {e.get('value')}")
        if status in ("ambiguous", "unknown"):
            if game_id is not None:
                err("status_requires_null_id", path, f"{status} entries must not carry gameQuestId")
            if status == "ambiguous" and len(q["candidateGameQuestIds"]) < 2:
                err("ambiguous_needs_candidates", path, "ambiguous requires >= 2 candidateGameQuestIds")
            if status == "unknown" and q["candidateGameQuestIds"]:
                err("unknown_has_candidates", path, "unknown must not list candidates; use ambiguous")
            for e in identifying:
                if e["value"] not in q["candidateGameQuestIds"]:
                    err("evidence_value_not_candidate", path, f"{e['kind']}={e['value']}")
        else:
            if game_id is None:
                err("status_requires_id", path, f"{status} requires gameQuestId")
            if q["candidateGameQuestIds"]:
                err("resolved_entry_has_candidates", path, "candidates are only for ambiguous entries")
            for e in identifying:
                if e["value"] != game_id:
                    err("evidence_value_conflict", path, f"{e['kind']}={e['value']} != gameQuestId {game_id}")
            if not identifying:
                err("status_without_identifying_evidence", path, f"{status} rests only on {sorted(kinds) or 'nothing'}")
            if status == "verified_in_game":
                in_game = [e for e in identifying if e["kind"] in GAME_ID_KINDS]
                if not in_game:
                    err("verified_without_in_game_evidence", path, "verified_in_game needs in_game_game_link or producer_name_id_pair evidence")
                if in_game and not any(in_game_observation_binds(e, q) for e in in_game):
                    err("verified_observation_incomplete", path, "in-game evidence must carry observedName equal to name, campaignContext equal to campaign, professionContext, and preRedirect=true for in_game_game_link")
            if status == "corroborated" and not (kinds & WIKI_ID_KINDS and kinds & NON_WIKI_ID_KINDS):
                err("corroborated_without_independent_evidence", path, "corroborated needs a wiki id source and a non-wiki id source")
            if status == "corroborated" and len({e["sourceId"] for e in identifying}) < 2:
                err("corroborated_single_source", path, "corroborated needs >= 2 distinct sources")

        for index, req in enumerate(q["requires_completion_of"]):
            for target in req["anyOf"]:
                if target == q["key"]:
                    err("self_reference", f"{path}.requires_completion_of[{index}]", target)
                elif target not in quests_by_key:
                    err("unknown_target", f"{path}.requires_completion_of[{index}]", target)
        for index, follow in enumerate(q["related_follow_up"]):
            target = follow["target"]
            if target == q["key"]:
                err("self_reference", f"{path}.related_follow_up[{index}]", target)
            elif target not in quests_by_key:
                err("unknown_target", f"{path}.related_follow_up[{index}]", target)
        if q["objectives"]["model"] == "sequential_same_id" and len(q["objectives"]["stages"]) < 2:
            err("sequential_needs_stages", f"{path}.objectives", "sequential_same_id needs >= 2 stages")
        stage_indexes = [s["index"] for s in q["objectives"]["stages"]]
        if stage_indexes != sorted(set(stage_indexes)):
            err("stage_index_order", f"{path}.objectives", "stage indexes must be unique and ascending")
        if q["objectives"]["stages"] and "sourceId" not in q["objectives"]:
            err("unsourced_objectives", f"{path}.objectives", "stages require sourceId")
        if q["completion"]["mode"] != "unknown" and "sourceId" not in q["completion"]:
            err("unsourced_completion", f"{path}.completion", "known completion mode requires sourceId")
        if q["branching"]["kind"] not in ("unknown", "none_stated") and "sourceId" not in q["branching"]:
            err("unsourced_branching", f"{path}.branching", "known branching kind requires sourceId")

    for cycle in find_required_cycles(quests_by_key):
        err("required_cycle", "$.quests", " -> ".join(cycle))
    return errors


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def iter_export_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for folder, _, files in sorted(os.walk(path)):
                for name in sorted(files):
                    if name.endswith(".json") and (name.startswith("quest_progress_contract_v1") or name.endswith(".contract-v1.json")):
                        yield os.path.join(folder, name)
        else:
            yield path


def closure_evidence(observation):
    found = []
    if observation["state"] in CLOSURE_STATES:
        found.append({"state": observation["state"], "source": observation.get("source"), "confidence": observation.get("confidence"), "observedAt": observation.get("observedAt"), "from": "current"})
    for event in observation.get("history") or []:
        if isinstance(event, dict) and event.get("state") in CLOSURE_STATES:
            found.append({"state": event["state"], "source": event.get("source"), "confidence": event.get("confidence"), "observedAt": event.get("observedAt"), "from": "history"})
    return found


def link_character(character, catalog, issues, file_label):
    policy = catalog["linkPolicy"]
    by_id = {q["gameQuestId"]: q for q in catalog["quests"] if q["gameQuestId"] is not None}
    by_candidate = {cid: q for q in catalog["quests"] for cid in q["candidateGameQuestIds"]}
    by_key = {q["key"]: q for q in catalog["quests"]}
    observations = {}
    rows = []
    for index, quest in enumerate(character.get("quests") or []):
        game_id = quest.get("gameQuestId") if isinstance(quest, dict) else None
        if not is_int(game_id) or game_id <= 0:
            issues.append({"code": "invalid_quest_record", "file": file_label, "characterKey": character.get("characterKey"), "index": index})
            continue
        row = {"gameQuestId": game_id, "state": quest.get("state"), "source": quest.get("source"), "confidence": quest.get("confidence")}
        entry = by_id.get(game_id)
        if entry is None and game_id in by_candidate:
            row.update({"linkState": "ambiguous_candidate", "catalogKey": by_candidate[game_id]["key"], "idStatus": by_candidate[game_id]["idVerification"]["status"]})
        elif entry is None:
            row.update({"linkState": "unmatched"})
        else:
            status = entry["idVerification"]["status"]
            if status in policy["autoLinkStatuses"]:
                link_state = "linked"
                observations[entry["key"]] = quest
            elif status in policy["candidateStatuses"]:
                link_state = "candidate"
            else:
                link_state = "not_linked"
            row.update({"linkState": link_state, "catalogKey": entry["key"], "idStatus": status})
        rows.append(row)

    prerequisites = []
    for key in sorted(observations):
        entry = by_key[key]
        for req in entry["requires_completion_of"]:
            evidence = []
            for target in req["anyOf"]:
                target_obs = observations.get(target)
                if target_obs is not None:
                    evidence += [dict(e, catalogKey=target) for e in closure_evidence(target_obs)]
            if evidence:
                closure, reason = "evidenced", "closure_evidence_in_export"
            else:
                linkable = [t for t in req["anyOf"] if by_key[t]["idVerification"]["status"] in policy["autoLinkStatuses"]]
                observed = [t for t in req["anyOf"] if t in observations]
                if not linkable:
                    reason = "prerequisite_not_linkable"
                elif observed:
                    reason = "prerequisite_observed_without_closure_evidence"
                else:
                    reason = "prerequisite_absent_from_export"
                closure = "uncertain"
            prerequisites.append({"followUp": key, "followUpState": observations[key].get("state"), "requiresAnyOf": req["anyOf"], "closure": closure, "reason": reason, "evidence": evidence})
    rows.sort(key=lambda r: r["gameQuestId"])
    return {"characterKey": character.get("characterKey"), "quests": rows, "prerequisites": prerequisites}


def link_exports(catalog, export_paths):
    issues = []
    files = []
    for path in iter_export_files(export_paths):
        label = os.path.basename(path)
        try:
            document = load_json(path)
        except (OSError, ValueError) as exc:
            issues.append({"code": "unreadable_export", "file": label, "message": type(exc).__name__})
            continue
        if not isinstance(document, dict) or document.get("contract") != CONTRACT_ID or document.get("contractVersion") != 1:
            issues.append({"code": "not_contract_v1", "file": label})
            continue
        characters = [link_character(c, catalog, issues, label) for c in document.get("characters") or [] if isinstance(c, dict)]
        files.append({"file": label, "characters": characters})
    counts = {}
    for f in files:
        for c in f["characters"]:
            for row in c["quests"]:
                counts[row["linkState"]] = counts.get(row["linkState"], 0) + 1
    return {"report": REPORT_ID, "reportVersion": 1, "catalogVersion": catalog["catalogVersion"], "linkPolicy": catalog["linkPolicy"], "counts": dict(sorted(counts.items())), "files": files, "issues": issues}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="quest_catalog.py")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("catalogs", nargs="+")
    validate.add_argument("--schema", default=DEFAULT_SCHEMA)
    link = sub.add_parser("link")
    link.add_argument("catalog")
    link.add_argument("exports", nargs="+")
    link.add_argument("--schema", default=DEFAULT_SCHEMA)
    link.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    schema = load_json(args.schema)
    if args.command == "validate":
        failed = False
        for path in args.catalogs:
            errors = validate_catalog(load_json(path), schema)
            print(json.dumps({"catalog": os.path.basename(path), "valid": not errors, "errors": errors}, ensure_ascii=False))
            failed = failed or bool(errors)
        return 1 if failed else 0
    catalog = load_json(args.catalog)
    errors = validate_catalog(catalog, schema)
    if errors:
        print(json.dumps({"catalog": os.path.basename(args.catalog), "valid": False, "errors": errors}, ensure_ascii=False))
        return 1
    report = link_exports(catalog, args.exports)
    if args.summary:
        report = {k: report[k] for k in ("report", "reportVersion", "catalogVersion", "counts", "issues")} | {
            "linkStates": [{"gameQuestId": i, "linkState": s, "catalogKey": k} for i, s, k in sorted({(r["gameQuestId"], r["linkState"], r.get("catalogKey")) for f in report["files"] for c in f["characters"] for r in c["quests"]}, key=lambda t: (t[0], t[1]))],
            "prerequisites": [p for f in report["files"] for c in f["characters"] for p in c["prerequisites"]]}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
