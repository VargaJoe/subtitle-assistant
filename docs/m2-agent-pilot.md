# M2 — csoportos agentes fordítási pilot

2026-11-17. M1 formatterrendezés és M2 technikai kilépési feltételei teljesültek a
`feature/tool-core-m1` ágon. A módosítások helyiek; nincs új commit, push, PR vagy
merge. A kiinduló HEAD `01eb7a43`. A GUI a következő M7a mérföldkő.

## Mi működik?

- Standard könyvtáras közös mag, JSON CLI, helyi HTTP API és
  [repo-skill](../skills/subtitle-assistant/SKILL.md), modellbelépés/MCP nélkül.
- Teljes mondat-/formázási egységekből képzett csomagok, szomszédos forrás- és
  célnyelvi kontextussal. Egzakt unit/cue ID-s visszaillesztés, hiány/duplikáció/
  elavult revízió/forráshash elutasítása, atomikus mentés és idempotens nyugták.
- Forrás-, cél- és időzítésjavítás; védett kézi célszöveg, before/after előzmény és
  visszaállítás. A régi forrásra épült fordítás visszaállítva is felülvizsgálandó.
- Munkafázis, frissesség, kooperatív szünet és beküldés-visszavonás. A heartbeat
  nem emeli a tartalmi revíziót és nem oldhatja fel a kért szünetet.
- Célnyelvi export közös display formatterrel. Legacy writer, standalone
  reformatter és target export ugyanazt a könnyű sortördelést használja;
  az eredeti és forrásexport továbbra sem tördeli át a szöveget.
- Workspace schema 2, explicit v1→v2 migráció megőrzött SQLite-backuppal.

Futtatható kérések és pontos határok:
[agentes munkafolyamat](agent-tool-workflow.md),
[v1.1 szerződés](tool-v1-contract.md),
[JSON-séma](schemas/tool-v1.schema.json),
[OpenAPI](schemas/tool-v1.openapi.json).

## Valódi fordítás és felfedezhetőség

Az [M0/M1 pilot](m0-m1-pilot.md) FBI S04E01 anyagának első 60 bejegyzését egy
előzmény nélküli belső agent kapta magyar fordításra. A feladat nem nevezett meg
CLI-t, API-t vagy skillt. A megtalált út:
`AGENTS.md → skills/subtitle-assistant/SKILL.md → workflow → JSON CLI`.
Ez valódi, külön kontextusú belső harness-próba; más desktopok/harness-ek globális
felfedezését nem igazolja. Más repositoryból továbbra is ismert kliensútvonal vagy
betöltött skillhivatkozás szükséges.

Mind a 60 cue eszközön át importálva, 57 egységben lefordítva, beküldve,
validálva és exportálva. A 7–8., 26–27., 49–50. cue közös egység; a célszöveg
jelentésrészei az eredeti időablakokhoz kerültek. 53 fordított és 7 szándékosan
megőrzött cue készült. A szülői nyelvi review a 49. cue többes számát javíttatta
`entry.edit` útján; az első export megmaradt, a javítás új outputba került.

Helyi, gitignored bizonyítékok:

- `.local/m2-pilot/20261117T190424Z/fresh-use/fresh-use-report.md` — részletes
  használati napló, nyelvi kérdések, pontos kérések és nyugták.
- Ugyanott `fbi-s04e01.entries-0001-0060.hu.reviewed.srt` — javított magyar minta.
- Munkatér: `fresh-use/workspace`; projekt
  `prj_98be8b667ef0441a915f224c23fd859b`, revízió 3.

A kézi összevetés minden cue indexét/start/stop idejét, a zenejelek dőlt tagjeit,
a beszélőjelöléseket és a teljes célszöveget ellenőrizte. Automatikus ellenőrzés:
60/60 cue, 0 nem kért időváltozás, `valid=true`, `target_ready=true`.
A javított export SHA-256:
`2490d2667a055cc6666935e235fd57a9be0b0d84f179a47fb7abd239f636b46e`.
A teljes, 848-as eredeti FBI-fájl SHA-256 változatlan:
`c6240429d8022ffd09d29838712fad0f886576287f68162732058d232cdf432f`.

## Ugyanez HTTP-n, tiszta telepítésből

A végső wheel Python 3.12.1-es tiszta venvbe, függőségek nélkül települt.
Az izolált telepített CLI valódi loopback szervert indított és HTTP-n importált,
előkészített, ugyanazon átnézett fordításokat új cue-azonosítókhoz rendelve
beküldött, védetté tett egy célsort, validált és exportált. A HTTP-export
byte-pontosan azonos a javított CLI-exporttal.

Az azonos submit replay nem duplikált; a kézi módosítás előtti revízió új UUID-s
beküldése ütközött. A pause megmaradt finished heartbeat után is, amíg resume nem
érkezett. Tiszta shutdown után az API `api_not_running` hibát adott, ugyanaz a
projekt közvetlen CLI-ből továbbra is validálható maradt.

- Bizonyíték: `.local/m2-pilot/20261117T190424Z/http-use/summary.json`, valamint
  `requests/` és `evidence/`; a token egyik naplóban sem szerepel.
- HTTP-projekt: `prj_7c1310ec4e784b7586ead63664677c32`, revízió 3.
- Nincs telepítve Torch, Transformers, Ollama, PyYAML, dotenv vagy requests.
- Wheel SHA-256:
  `16f6b2483542e2a9efa9df1d6589626b7a3fbc37fbaedd0a090831c7c384b167`.

## Regressziók és korlátok

**105 model-free teszt sikeres**, köztük 12 valódi HTTP-teszt és szintetikus
kétnyelvű fixture eltérő sorfelosztással, ismételt SRT-indexszel, cue-határon
átnyúló dőlt formázással, részleges kiemeléssel és beszélőváltással. **23 érintett
legacy teszt sikeres**, három függőségi deprecation warninggal, offline módban.

```powershell
python -S -m unittest discover -s tests/tool -q
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
./.venv/Scripts/python.exe -m pytest tests/unit/test_api_batch_cross_entry.py tests/unit/test_multiline_fix.py tests/integration/test_backend_switching.py -q -o addopts=
```

A szűk review által reprodukált és javított hibák: pause-t feloldó terminal
heartbeat; stale fordítást újra elfogadó restore; CRLF/CR kézi javítás után
elromló export; a HTMLParser által a következő cue-ba pufferelt `AT&T` szöveg és
hibás preservation-ellenőrzés. Mind regressziós teszttel lezárva. A sémák JSON-ja,
154 hivatkozása és a 21 művelet argumentum-paritása ellenőrzött; külön standards
validator nem futott. Skill-validator sikeres. A két korábbi owner-módosítás
(`rate_limiter.py`, `translate_all_srt.ps1`) hash szerint változatlan.

A csoportosítás heurisztika, a szerkezeti ellenőrzés nem bizonyítja önmagában a
szemantikai időillesztést. A részlet videós/emberi elfogadása még nincs meg.
Kiemelt nyelvi kérdések: a G-5 utalás, a 29. „too” vonatkozása, intézménynév,
valamint a rövid bemutatkozások olvashatósága. A 47. cue kb. 30,7 karakter/s;
időzítését nem nyújtottuk meg. Tartós film-/karakter-/glosszáriumadat M3 feladat.

A próba közben még M1-es dokumentációt olvasott az agent; az aktuális
szerződés/README/roadmap már M2-re frissült. A lezárt batch ID-val küldött
aktivitást a tool helyesen visszautasította; a skill pontosítva: beküldés után
projekt-szintű aktivitás batch ID nélkül.

Kézi smoke: nyisd meg a javított SRT-t az eredeti videóval; nézd meg a 7–9.
jelentésillesztést, a 16./20./37. beszélőváltást, a 29. utalást és a 46–49.
bemutatkozásokat. Következő fejlesztés M7a: forrás/cél egymás mellett,
kézi szöveg-/időzítésjavítás és élő agentállapot a már elkészült szolgáltatásokkal.
