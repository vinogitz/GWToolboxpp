# Forrás- és ID-ellenőrzési jegyzék — Pre-Searing pilot

TaskSpec: `TOOLBOX-QUEST-CATALOG-CHAINS-01` · katalógus `0.2.0-pilot` · wiki-lekérés: 2026-11-26 · első játékbeli rögzítés: 2026-11-27 · `DATA_CAPTURE_READY=NOT_READY`

## Szabály

- A wiki oldalazonosító (`pageId`) és a névegyezés önmagában nem igazol játékbeli ID-t. A `pageId` csak a forrásverzió rögzítésére szolgál.
- A `Game link:Quest N` oldalak a játék beépített súgólinkjeinek céljai, amelyeket wiki-szerkesztők irányítanak át. Ha valaki kézzel keresi meg őket, wiki ID-forrásnak számítanak, nem játékbeli rögzítésnek. Csak a játékból indított, átirányítás előtti link számít játékbeli megfigyelésnek (lásd lent).
- A helyi Toolbox exportokban a `questName` és a célszöveg üres, így azok csak azt mutatják, hogy egy ID milyen kontextusban (Pre-Searing, profession) jelent meg. Nevet nem kötnek ID-hoz.
- `verified_in_game` státuszhoz a lenti szabály szerinti játékbeli megfigyelés kell. A pilotban egy ilyen megfigyelés van: Getting Started in Guild Wars (`1462`), lásd a rögzítési jegyzőkönyvet lent.

## Számozási tér keresztellenőrzése

- Állítás: GWCA QuestID numbering equals the wiki Game link:Quest numbering.
- Eredmény: 241 GWCA QuestID values: 226 same name, 14 same quest with abbreviated/variant spelling, 1 (1181) absent from the wiki table, 0 contradictions. Supports the numbering space only; binds no Pre-Searing quest.
- Az eltérő 14 név csak rövidítés vagy írásváltozat, pl. `UW_Wastes=102` → Servants of Grenth, `Fow_Tos=211` → Tower of Strength, `ZaishenVanquish_Respendent_Makuun=1290` → Resplendent Makuun. Ellentmondás nincs.
- Ez a GWCA `QuestID` számozás és a wiki game-link számozás egyezését támasztja alá. Pre-Searing questet nem köt, mert a GWCA-ban nincs Pre-Searing bejegyzés.

## Játékbeli ID-igazolás szabálya (`verified_in_game`)

- `verified_in_game` státuszhoz **ugyanaz a játékbeli megfigyelés** kösse össze a küldetés nevét és `gameQuestId`-ját.
- Elfogadott: a játékban kiválasztott quest neve és a játékból indított, **átirányítás előtti** `Game link:Quest N` együtt, rögzített kampány- és szakmakontextussal (`in_game_game_link`: `observedName`, `value`, `campaignContext`, `professionContext`, `preRedirect: true`).
- Később elfogadott: a producer ugyanabból a mintából rögzített név–ID párja (`producer_name_id_pair`, ugyanazokkal a mezőkkel). Ehhez külön producer-szelet kell, ebben a körben nincs.
- Nem elég: kézzel megkeresett wiki-link vagy `Game link:Quest N` oldal, névegyezés, wiki oldalazonosító, név nélküli export (a mostani helyi exportok ilyenek), upstream kódmegjegyzés vagy GWCA konstans.
- `corroborated` és `source_claimed` marad jelölt (`candidate`). Automatikus kapcsolás (`linked`) kizárólag `verified_in_game` esetén van.
- A validátor kényszeríti: a bizonyíték `observedName`-je egyezzen a bejegyzés nevével, a `campaignContext` a kampánnyal, a `professionContext` ne legyen `unknown`, és `in_game_game_link` esetén `preRedirect` legyen igaz.
- A validátor nem tárolja strukturáltan, honnan származik az átirányítás előtti cím (címsor, `rdfrom` vagy „Redirected from” sor): ezt a forrás `url` mezője és a bizonyíték `note` mezője rögzíti. A `preRedirect: true` azt jelenti, hogy a `Game link:Quest N` érték az átirányítás előtti cím, akkor is, ha azt az `rdfrom` paraméterből olvastuk ki.

## Bejegyzések

| key | név | `gameQuestId` | státusz | ID-bizonyíték | megjegyzés |
| --- | --- | --- | --- | --- | --- |
| `presearing.getting_started_in_guild_wars` | Getting Started in Guild Wars | 1462 | `verified_in_game` | `in_game_game_link`=1462 (in-game-f10-help-quest-1462-2026-11-27); `wiki_infobox_id`=1462 (gww-getting-started-in-guild-wars); `wiki_game_link`=1462 (gww-game-link-quest-1462); `wiki_game_integration_table`=1462 (gww-game-integration-quests-1000-1499); `toolbox_live_observation`=1462 (toolbox-live-exports-2026-11) | 2026-11-27 F10 Help panel, Toolbox nélkül, Pre-Searing Monk. A böngésző 403-at adott; az átirányítás előtti cím az `rdfrom` paraméterből: `Game_link:Quest_1462`. Automatikusan kapcsolható. |
| `presearing.war_preparations` | War Preparations | null (jelöltek: 35, 217, 218, 219, 220, 221, 222) | `ambiguous` | `wiki_infobox_id`=219 (gww-war-preparations); `wiki_game_link`=35 (gww-game-link-quest-35); `wiki_game_link`=220 (gww-game-link-quest-220); `wiki_game_integration_table`=35 (gww-game-integration-quests-0-499); `toolbox_live_observation`=220 (toolbox-live-exports-2026-11) | Name match cannot select an id: seven ids redirect to the same article and the disambiguation page describes six Pre-Searing variants. Never auto-linked. |
| `presearing.warrior_test` | Warrior Test | 85 | `source_claimed` | `wiki_infobox_id`=85 (gww-warrior-test); `wiki_game_link`=85 (gww-game-link-quest-85); `wiki_game_integration_table`=85 (gww-game-integration-quests-0-499) | Wiki sources only; not observed in local exports. |
| `presearing.ranger_test` | Ranger Test | 86 | `source_claimed` | `wiki_infobox_id`=86 (gww-ranger-test); `wiki_game_link`=86 (gww-game-link-quest-86); `wiki_game_integration_table`=86 (gww-game-integration-quests-0-499) | Wiki sources only; not observed in local exports. |
| `presearing.monk_test` | Monk Test | 84 | `corroborated` | `wiki_infobox_id`=84 (gww-monk-test); `wiki_game_link`=84 (gww-game-link-quest-84); `wiki_game_integration_table`=84 (gww-game-integration-quests-0-499); `toolbox_live_observation`=84 (toolbox-live-exports-2026-11) | Wiki id sources plus profession-consistent live observation; no in-game name/text capture yet. |
| `presearing.necromancer_test` | Necromancer Test | 82 | `source_claimed` | `wiki_infobox_id`=82 (gww-necromancer-test); `wiki_game_link`=82 (gww-game-link-quest-82); `wiki_game_integration_table`=82 (gww-game-integration-quests-0-499) | Wiki sources only; not observed in local exports. |
| `presearing.mesmer_test` | Mesmer Test | 81 | `corroborated` | `wiki_infobox_id`=81 (gww-mesmer-test); `wiki_game_link`=81 (gww-game-link-quest-81); `wiki_game_integration_table`=81 (gww-game-integration-quests-0-499); `toolbox_live_observation`=81 (toolbox-live-exports-2026-11) | Wiki id sources plus profession-consistent live observation; no in-game name/text capture yet. |
| `presearing.elementalist_test` | Elementalist Test | 83 | `source_claimed` | `wiki_infobox_id`=83 (gww-elementalist-test); `wiki_game_link`=83 (gww-game-link-quest-83); `wiki_game_integration_table`=83 (gww-game-integration-quests-0-499) | Wiki sources only; not observed in local exports. |
| `presearing.further_adventures` | Further Adventures | 54 | `corroborated` | `wiki_infobox_id`=54 (gww-further-adventures); `wiki_game_link`=54 (gww-game-link-quest-54); `wiki_game_integration_table`=54 (gww-game-integration-quests-0-499); `toolbox_live_observation`=54 (toolbox-live-exports-2026-11) | No in-game name/text capture yet. |
| `presearing.adventure_with_an_ally` | Adventure with an Ally | 56 | `corroborated` | `wiki_infobox_id`=56 (gww-adventure-with-an-ally); `wiki_game_link`=56 (gww-game-link-quest-56); `wiki_game_integration_table`=56 (gww-game-integration-quests-0-499); `repo_code_reference`=56 (repo-hintsmodule-quest-56); `toolbox_live_observation`=56 (toolbox-live-exports-2026-11) | Upstream code annotation is a developer claim, not a capture; no in-game name/text capture yet. |

## Helyi élő megfigyelések (`toolbox-live-exports-2026-11`)

Forrás: a fork helyi Contract v1 exportjai (`Documents/GWToolboxpp/SZABOBE16IRX9/QuestProgress/exports/...`, 2026-10-17 és 2026-11-25 között). A fájlokat csak olvastuk, nem másoltuk a repóba. Hat karakter szerepel bennük, ebből öt `isPreSearing=true`. A karakterazonosítók itt nem szerepelnek.

| `gameQuestId` | wiki game-link cím | Hol jelent meg | Szerkezeti megfigyelés |
| --- | --- | --- | --- |
| 1462 | Getting Started in Guild Wars | mind az 5 Pre-Searing karakter, a post-Searing karakternél nem | egy monk karakternél ugyanazon az ID-n 1 → 2 cél, az első teljesítve |
| 84 | Monk Test | csak monk primary (2) | 1 cél, illetve 2 cél az első teljesítve, és `completed_observed`/`probable` (reward) |
| 81 | Mesmer Test | mesmer primary (1) és egy ismeretlen professionű karakter, monknál soha | 1 → 2 cél, `ready_for_reward` |
| 54 | Further Adventures | monk primary (1), Monk Test reward bizonyíték mellett | 1 cél, `objective_progress` |
| 56 | Adventure with an Ally | monk primary (1) | 1 cél |
| 220 | War Preparations (7 ID közös címe) | csak monk primary (2) | `objective_progress`, illetve `completed_observed`/`probable` |

További Pre-Searing ID-k is megjelentek, ezek a pilot hatókörén kívül esnek: 38, 39, 41, 51, 70, 71, 80. A post-Searing karakteren 261 jelent meg. Ezeket nem katalogizáltuk.

## Ismert ellentmondások és nyitott pontok

- **War Preparations:** a cikk infoboxa `id = 219`, a game-link tábla 35, 217–222 ID-t irányít ugyanerre a címre, a helyi exportban pedig 220 jelent meg monk karaktereken. A disambiguation oldal hat Pre-Searing változatot említ. A profession → ID kötést egyik forrás sem rögzíti, ezért a státusz `ambiguous` és `gameQuestId = null`.
- **Mesmer Test:** a cikk infoboxából hiányzik a `preceded by` mező, ezért a War Preparations → Mesmer Test `related_follow_up` nincs rögzítve.
- **Elágazások:** a profession testek és a Further Adventures cikkek több folytatást is felsorolnak, de nem mondják ki, hogy ezek kizárják-e egymást. Ezért `branching.kind = unknown`.
- **Getting Started in Guild Wars:** a forrás szerint az elfogadás időpontjától függ, hogy a Town Crier cél megjelenik-e (ismert bug). Ez a lezárást befolyásolja, és `notes[]` alatt szerepel.
- **Adventure with an Ally (56):** az upstream `HintsModule.cpp` `case 56: // Adventure with an ally` sora fejlesztői annotáció, nem rögzítés.

## Források

| id | típus | cím | revízió | URL / útvonal |
| --- | --- | --- | --- | --- |
| `gww-game-integration-quests-0-499` | `wiki_game_integration_table` | Guild Wars Wiki:Game integration/Quests/0..499 | 2532784 (2013-02-03T21:59:07Z) | https://wiki.guildwars.com/wiki/Guild_Wars_Wiki:Game_integration/Quests/0..499 |
| `gww-game-integration-quests-500-999` | `wiki_game_integration_table` | Guild Wars Wiki:Game integration/Quests/500..999 | 2558929 (2013-11-21T07:45:24Z) | https://wiki.guildwars.com/wiki/Guild_Wars_Wiki:Game_integration/Quests/500..999 |
| `gww-game-integration-quests-1000-1499` | `wiki_game_integration_table` | Guild Wars Wiki:Game integration/Quests/1000..1499 | 2729407 (2026-05-31T21:17:09Z) | https://wiki.guildwars.com/wiki/Guild_Wars_Wiki:Game_integration/Quests/1000..1499 |
| `gww-getting-started-in-guild-wars` | `wiki_article` | Getting Started in Guild Wars | 2741623 (2026-09-23T21:23:17Z) | https://wiki.guildwars.com/wiki/Getting_Started_in_Guild_Wars |
| `gww-game-link-quest-1462` | `wiki_game_link` | Game link:Quest 1462 | 2729073 (2026-05-27T20:55:37Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_1462 |
| `gww-war-preparations` | `wiki_article` | War Preparations | 2741375 (2026-09-21T23:05:30Z) | https://wiki.guildwars.com/wiki/War_Preparations |
| `gww-war-preparations-disambiguation` | `wiki_article` | War Preparations (disambiguation) | 1312330 (2009-01-20T22:05:04Z) | https://wiki.guildwars.com/wiki/War_Preparations_(disambiguation) |
| `gww-game-link-quest-35` | `wiki_game_link` | Game link:Quest 35 | 2651051 (2020-04-22T13:40:58Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_35 |
| `gww-game-link-quest-220` | `wiki_game_link` | Game link:Quest 220 | 2650908 (2020-04-22T13:38:34Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_220 |
| `gww-warrior-test` | `wiki_article` | Warrior Test | 2741097 (2026-09-18T13:09:07Z) | https://wiki.guildwars.com/wiki/Warrior_Test |
| `gww-game-link-quest-85` | `wiki_game_link` | Game link:Quest 85 | 2651605 (2020-04-22T13:50:17Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_85 |
| `gww-ranger-test` | `wiki_article` | Ranger Test | 2741098 (2026-09-18T13:29:54Z) | https://wiki.guildwars.com/wiki/Ranger_Test |
| `gww-game-link-quest-86` | `wiki_game_link` | Game link:Quest 86 | 2651616 (2020-04-22T13:50:29Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_86 |
| `gww-monk-test` | `wiki_article` | Monk Test | 2741099 (2026-09-18T13:40:51Z) | https://wiki.guildwars.com/wiki/Monk_Test |
| `gww-game-link-quest-84` | `wiki_game_link` | Game link:Quest 84 | 2651594 (2020-04-22T13:50:06Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_84 |
| `gww-necromancer-test` | `wiki_article` | Necromancer Test | 2741055 (2026-09-17T20:37:25Z) | https://wiki.guildwars.com/wiki/Necromancer_Test |
| `gww-game-link-quest-82` | `wiki_game_link` | Game link:Quest 82 | 2651572 (2020-04-22T13:49:44Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_82 |
| `gww-mesmer-test` | `wiki_article` | Mesmer Test | 2741244 (2026-09-20T17:46:58Z) | https://wiki.guildwars.com/wiki/Mesmer_Test |
| `gww-game-link-quest-81` | `wiki_game_link` | Game link:Quest 81 | 2651561 (2020-04-22T13:49:33Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_81 |
| `gww-elementalist-test` | `wiki_article` | Elementalist Test | 2741105 (2026-09-18T14:09:08Z) | https://wiki.guildwars.com/wiki/Elementalist_Test |
| `gww-game-link-quest-83` | `wiki_game_link` | Game link:Quest 83 | 2651583 (2020-04-22T13:49:55Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_83 |
| `gww-further-adventures` | `wiki_article` | Further Adventures | 2741376 (2026-09-21T23:05:55Z) | https://wiki.guildwars.com/wiki/Further_Adventures |
| `gww-game-link-quest-54` | `wiki_game_link` | Game link:Quest 54 | 2651262 (2020-04-22T13:44:34Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_54 |
| `gww-adventure-with-an-ally` | `wiki_article` | Adventure with an Ally | 2727895 (2026-05-11T15:58:07Z) | https://wiki.guildwars.com/wiki/Adventure_with_an_Ally |
| `gww-game-link-quest-56` | `wiki_game_link` | Game link:Quest 56 | 2651284 (2020-04-22T13:44:56Z) | https://wiki.guildwars.com/wiki/Game_link:Quest_56 |
| `gww-template-standard-prerequisites` | `wiki_template` | Template:Standard prerequisites | 2723807 (2026-04-01T22:17:06Z) | https://wiki.guildwars.com/wiki/Template:Standard_prerequisites |
| `repo-hintsmodule-quest-56` | `repo_code` | HintsModule OnQuestAdded_UIMessage: case 56 // Adventure with an ally | bbe0576c0 | GWToolboxdll/Modules/HintsModule.cpp |
| `repo-gwca-questids` | `repo_code` | GWCA Constants QuestID enum | blob 348074fcb3942e44311249bcd0dd0dbfd8719269 | Dependencies/GWCA/include/GWCA/Constants/QuestIDs.h |
| `toolbox-live-exports-2026-11` | `toolbox_live_export` | Local Quest Progress Contract v1 exports of this fork (SZABOBE16IRX9 profile, 2026-10-17..2026-11-25) | — | helyi, nem a repóban |
| `in-game-f10-help-quest-1462-2026-11-27` | `wiki_game_link` | F10 Help panel Game link capture for Quest 1462 (Bence, 2026-11-27) | — (élő kliens, nem wiki-revízió) | https://wiki.guildwars.com/wiki/Getting_Started_in_Guild_Wars?rdfrom=https%3A%2F%2Fwiki.guildwars.com%2Findex.php%3Ftitle%3DGame_link%3AQuest_1462%26redirect%3Dno |

A wiki revíziók a `https://wiki.guildwars.com/index.php?oldid=<revisionId>` címen érhetők el. A katalógus leírásai saját megfogalmazású, tényszerű összefoglalók; a forrást az URL és a revízió azonosítja.


## Játékbeli rögzítés — Getting Started in Guild Wars (1462)

- Dátum: 2026-11-27, kb. 02:55 (Europe/Budapest, UTC+1). Rögzítette: Bence. Képernyőkép nem készült; az URL szövegként érkezett.
- Kontextus: Pre-Searing, elsődleges szakma Monk. A küldetés bent volt a naplóban. A naplóban látható név: Getting Started in Guild Wars. A katalógus `campaign` mezője `prophecies`, a Pre-Searing a `region` (`ascalon_pre_searing`); a bizonyíték `campaignContext` értéke ezért `prophecies`, a Pre-Searing a megjegyzésben szerepel.
- Módszer: a vanilla kliens Help panelje (F10), Toolbox nélkül. A Community Wiki / Quests listában a küldetés linkjére kattintott.
- A böngészőben megnyílt URL (a lap HTTP 403 Forbidden választ adott):
  `https://wiki.guildwars.com/wiki/Getting_Started_in_Guild_Wars?rdfrom=https%3A%2F%2Fwiki.guildwars.com%2Findex.php%3Ftitle%3DGame_link%3AQuest_1462%26redirect%3Dno`
- Az átirányítás előtti cím az `rdfrom` paraméterből: `Game_link:Quest_1462`. A „Redirected from” sor nem jelent meg: a wiki `ingame-help` előtagja elnyomja, és az `rdfrom`-os céloldal 403-at ad.
- Ez a 403 várható, nem azt jelenti, hogy a Help rossz cikkre visz. A kliens a `Game_link:Quest_1462` címet nyitja; a wiki 302-vel az `rdfrom` lekérdezést fűzi a cikkre, és a wiki terheléselosztója ezt a lekérdezést 403-mal utasítja el. A cikk `https://wiki.guildwars.com/wiki/Getting_Started_in_Guild_Wars` `rdfrom` nélkül elérhető. A Toolbox ugyanezt a 403-at kerülve a feloldott cikket nyitja, ezért a pre-redirect érték rögzítéséhez Toolbox nélkül kellett a Help panelt használni.
- Státusz: `verified_in_game`. A 1462 ettől automatikusan kapcsolható (`linked`). Ebből nem következik más küldetés lezárása.
