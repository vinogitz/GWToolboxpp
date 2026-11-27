# Pre-Searing küldetéskatalógus (pilot) — adatleírás

TaskSpec: `TOOLBOX-QUEST-CATALOG-CHAINS-01` · `catalogVersion` `0.3.0-pilot` · `schemaVersion` `1` · `DATA_CAPTURE_READY=NOT_READY`

Verziózott, offline használható, géppel olvasható katalógus. Hálózat és build nélkül, Python 3 standard könyvtárral validálható és köthető Contract v1 exporthoz. A producer, a Contract v1 és a Wayfarer változatlan: a katalógus külön adatréteg, nem Contract mező, és nem kerül az exportba.

| Fájl | Szerep |
| --- | --- |
| `presearing-quest-catalog.v1.json` | A katalógus (10 bejegyzés, 31 forrás) |
| `quest-catalog.schema.v1.json` | JSON Schema (draft 2020-12), ezt a validátor is betölti |
| `source-and-id-register.md` | Forrás- és ID-ellenőrzési jegyzék |
| `../../../scripts/quest_catalog.py` | `validate` és `link` parancs |
| `../../../tests/QuestCatalogTests/` | Célzott tesztek és fixture-ök |

## Verziózás

- `schemaVersion`: a séma szerkezete. Mező törlése, átnevezése vagy jelentésváltozása új sémaverziót és új `quest-catalog.schema.vN.json` fájlt jelent.
- `catalogVersion`: SemVer. Patch: forrás- vagy szövegjavítás. Minor: új bejegyzés vagy kapcsolat. Major: meglévő `key` vagy `gameQuestId` változása, vagy egy ID visszaminősítése.
- A `key` (pl. `presearing.monk_test`) a katalógus stabil azonosítója. A kapcsolatok `key`-re mutatnak, nem `gameQuestId`-ra, mert az ID lehet `null` vagy kétes.

## Bejegyzés mezői

| Mező | Jelentés |
| --- | --- |
| `name`, `campaign`, `region`, `questType`, `profession`, `reforgedModeOnly` | Megjelenítési és hatóköri metaadat. A `name` soha nem azonosító. |
| `gameQuestId` | A játék numerikus quest ID-ja (Contract v1 `gameQuestId`), vagy `null`. |
| `candidateGameQuestIds` | Csak `ambiguous` bejegyzésnél: a lehetséges ID-k. |
| `idVerification.status` | Lásd lent. |
| `idVerification.evidence[]` | `kind` + `sourceId` + `value`. Minden igazoló érték egyezzen a `gameQuestId`-val (ambiguous esetén a jelöltek közé essen). |
| `sourceIds` | A bejegyzés forrásai, a `sources[]` regiszterre hivatkozva (URL, `pageId`, `revisionId`, időbélyeg). |
| `objectives.model` | `single`, `sequential_same_id` (célváltás ugyanazzal az ID-val) vagy `unknown`. A `stages[].summary` saját megfogalmazású összefoglaló, nem wiki-idézet. |
| `completion.mode` | A lezárás módja: `reward_dialogue`, `automatic_on_objective` vagy `unknown`. Csak forrással lehet ismert. A `note` saját megfogalmazású összefoglaló. |
| `branching.kind` | `none_stated`, `profession_variant`, `mutually_exclusive`, `parallel_unlock` vagy `unknown`. Ha a forrás nem mondja ki a kizárólagosságot, akkor `unknown`. |
| `requires_completion_of[]` | **Igazolt előfeltétel.** `anyOf` csoport: legalább egy célpont teljesítése kell. Csak a forrás „Requirements” része alapján. |
| `related_follow_up[]` | **Kapcsolódó folytatás.** Informatív, nem előfeltétel (pl. „preceded by/followed by” infobox, kihagyható quest). |
| `outOfScopeFollowUps[]` | A pilot hatókörén kívüli, forrás szerinti folytatások név szerint. Nem kapcsolat, nem validált célpont. |
| `notes[]` | Forrással ellátott, saját megfogalmazású megjegyzés (pl. ismert bug, elérhetőségi feltétel). |

## ID-ellenőrzési státuszok és kötési szabály

| `status` | Feltétel (validátor kényszeríti) | Kötés exporthoz |
| --- | --- | --- |
| `verified_in_game` | `gameQuestId` + `in_game_game_link` vagy `producer_name_id_pair` bizonyíték, amely ugyanabból a megfigyelésből köti a nevet és az ID-t (lásd lent) | automatikus (`linked`) |
| `corroborated` | wiki ID-forrás **és** nem-wiki ID-forrás (`toolbox_live_observation`, `repo_code_reference`, `gwca_constant`), legalább 2 különböző forrás | csak `candidate`, nem kötődik |
| `source_claimed` | legalább egy azonosító erejű forrás (pl. csak wiki) | csak `candidate` |
| `ambiguous` | `gameQuestId = null`, legalább 2 jelölt ID | soha (`ambiguous_candidate`) |
| `unknown` | `gameQuestId = null`, nincs jelölt | soha |

A `verified_in_game` bizonyíték kötelező mezői: `observedName` (egyezik a bejegyzés `name` mezőjével), `campaignContext` (egyezik a `campaign` mezővel), `professionContext` (nem `unknown`), és `in_game_game_link` esetén `preRedirect: true`. Részletes szabály: [source-and-id-register.md](source-and-id-register.md).

A `wiki_page_id` és a `name_match` bizonyíték rögzíthető, de egyik státuszt sem támasztja alá. A `linkPolicy.autoLinkStatuses` nem tartalmazhat ellenőrizetlen státuszt, ezt a validátor hibának veszi. A `verified_in_game` forrás `url` mezőjében, ha van `rdfrom` és abból kiolvasható a `Game link:Quest N` azonosító, a validátor ellenőrzi, hogy az N egyezik a bizonyíték `value` mezőjével. A pilotban két bejegyzés `verified_in_game`: `presearing.getting_started_in_guild_wars` (`1462`) és `presearing.monk_test` (`84`), mindkettő 2026-11-27-i F10 Help panel rögzítés alapján (Toolbox nélkül; az átirányítás előtti `Game_link:Quest_1462` illetve `Game_link:Quest_84` cím az `rdfrom` paraméterből). A többi bejegyzés nem automatikus kapcsolású.

## Idézetek

A katalógus, a fixture-ök és a dokumentáció nem tartalmaz szó szerinti wiki-idézetet. Nincs `quote` mező, a séma (`additionalProperties: false`) elutasítja, a teszt pedig ellenőrzi. A leírások saját megfogalmazású összefoglalók, a forrást az URL és a `revisionId` azonosítja.

## Két pilot eset

1. **Célváltás ugyanazzal a `gameQuestId`-val:** `presearing.getting_started_in_guild_wars` (`1462`, `sequential_same_id`, 5 forrásolt szakasz). A helyi exportban ugyanazon az ID-n 1 → 2 célt és az első cél teljesülését láttuk. Ugyanez a minta a profession testeknél (`84`, `81`) is.
2. **Külön ID-jű küldetések lánca:** `presearing.war_preparations` (`ambiguous`, `null`) → `presearing.monk_test` (`84`, `verified_in_game`) → `presearing.further_adventures` (`54`, `corroborated`). A War Preparations kihagyható, ezért csak `related_follow_up`. A Further Adventures `requires_completion_of` mezője a hat profession test `anyOf` csoportja a `Standard prerequisites` sablon alapján.

## Offline kötés exporthoz

```text
python scripts/quest_catalog.py validate docs/quest-tracker/catalog/presearing-quest-catalog.v1.json
python scripts/quest_catalog.py link <catalog.json> <export.json | export-mappa> [...] [--summary]
```

A `link` csak olvas. Exportonként, karakterenként és questenként `linkState`-et ad: `linked`, `candidate`, `ambiguous_candidate`, `not_linked` vagy `unmatched`. Az előfeltétel-elemzés csak `linked` B-re fut:

- A-nak akkor van lezárási bizonyítéka (`evidenced`), ha az exportban A jelenlegi vagy history állapota `completed_observed` vagy `completed_manual`. A `source` és a `confidence` változatlanul kerül a riportba, a `probable` `probable` marad.
- Különben `uncertain`, és mellé kerül az ok: `prerequisite_observed_without_closure_evidence`, `prerequisite_absent_from_export` vagy `prerequisite_not_linkable`. B megjelenéséből A-ra soha nem következtetünk lezárást.
- Az ismeretlen ID `unmatched` lesz, a hibás quest rekord, a nem Contract v1 fájl és az olvashatatlan fájl pedig `issues[]` bejegyzést kap. A feldolgozás egyik esetben sem áll le.
