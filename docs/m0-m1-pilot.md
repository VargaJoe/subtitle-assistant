# M0 és M1 első működő változat — helyi pilot

Dátum: 2026-11-17. Ág: `feature/tool-core-m1`. A vizsgálat az import–mentés–visszanyitás–lekérdezés–forrásexport munkafolyamatot igazolja, nem fordításminőséget.

## Kiválasztott anyag

Joe által megadott eredeti:

```text
subtitles_eng/FBI.S04E01.720p.AMZN.WEB-DL.DDP5.1.H.264.HUN.ENG-PTHD.eng.srt
```

- Méret: **61 180 byte**.
- SHA-256: `c6240429d8022ffd09d29838712fad0f886576287f68162732058d232cdf432f`.
- Encoding: UTF-8 BOM; sorvég: CRLF.
- Teljes epizód: **848** bejegyzés; a szigorú importban nincs hiba vagy figyelmeztetés.
- Rövid pilot: az első **60** bejegyzés, helyben kinyert forrásrészlet. Tartalmaz HTML-t, hang-/zenei jelölést, több szereplős párbeszédet és mondatfolytatásokat. Hasznos referenciahelyek: 1–2, 24, 31, 42 és 45; a megszólítás/karakterviszony értelmezése M3 munka, most nincs kitalált címkézés.
- A teljes/részlet forrást és az exportokat nem másoljuk a verziózott tesztkorpuszba. A regressziós tesztek kis szintetikus feliratokon futnak.

## M0 döntések

- A [v1 szerződés](tool-v1-contract.md) és a [JSON-séma](schemas/tool-v1.schema.json) rögzíti az envelope-ot, azonosítást, revíziókat, hibákat és a következő M2/M7 műveletek határát.
- Az eredeti byte-ok a SQLite projektben archiválódnak; külön munkaszöveg és munkaidőzítés készül.
- A modelltől független belépés `python -S -m subtitle_translator.tool`; a [repo indítómutatója](../AGENTS.md) ezt hivatkozza.
- A jelenlegi SQLite-séma v1, az üres munkatér inicializálása támogatott. Idegen/future séma elutasított; régi `.progress`/output/modelek migrációja nincs.
- A két korábbi felhasználói diff byte szerint megmaradt: `subtitle_translator/core/rate_limiter.py` és `translate_all_srt.ps1`. Nem részei az új mag implementációjának.

## Helyi projekt és eredmények

Az alábbi mappa személyes pilotadat, `.gitignore` alatt marad:

```text
.local/m1-pilot/20261117T175319Z/
```

| Adat | Érték |
|---|---|
| Munkatér | `.local/m1-pilot/20261117T175319Z/workspace` |
| Teljes projekt | `prj_3825c110fd2e4838b3c973f2e3dcb8ba` |
| 60 bejegyzéses projekt | `prj_d99ba2c69ecc41f5bdfaba6ac37f54a3` |
| Forrásexport | `fbi-s04e01.source.srt` |
| Byte-pontos eredeti export | `fbi-s04e01.original.srt` |
| Rövid eredeti részlet | `fbi-s04e01.entries-0001-0060.eng.srt` |
| Rövid forrásexport | `fbi-s04e01.entries-0001-0060.source.srt` |
| Gépi összefoglaló | `summary.json` |

A többi helyi JSON-fájl a külön CLI-folyamatok import-, status-, lapozott bejegyzés-, ellenőrzés- és exportválaszait tartalmazza. A mappanév technikai UTC-azonosító, nem helyi diary-időpont.

Újranyitás a repository gyökeréből:

```powershell
python -S -m subtitle_translator.tool --workspace ".local/m1-pilot/20261117T175319Z/workspace" project status --project "prj_3825c110fd2e4838b3c973f2e3dcb8ba" --json
python -S -m subtitle_translator.tool --workspace ".local/m1-pilot/20261117T175319Z/workspace" entry list --project "prj_3825c110fd2e4838b3c973f2e3dcb8ba" --limit 5 --json
python -S -m subtitle_translator.tool --workspace ".local/m1-pilot/20261117T175319Z/workspace" project validate --project "prj_3825c110fd2e4838b3c973f2e3dcb8ba" --json
```

## Igazolt eredmény

- A teljes fájl importja, külön folyamatból visszanyitása és 127-es lapméretű beolvasása sikeres; **848 külön, stabil bejegyzésazonosító**.
- A kanonikus forrásexport eredeti sorszáma, időbélyegsora és szövege minden bejegyzésnél megegyezik az eredetiével. Az ellenőrzés a produkciós parsertől független, közvetlen forrásblokkokon is megtörtént.
- Az `original` export a teljes bemenettel byte-ról byte-ra megegyezik, a BOM és CRLF is megmaradt.
- Az eredeti bemeneti fájl hash-e a teljes pilot után változatlan.
- A 60 bejegyzéses részlet külön importja és exportja is veszteségmentes.
- A folyamat Python **3.12.1** alatt `-S` módban futott, modell-/hálózathívás nélkül.
- A wheel függőségek nélkül feltelepült külön, üres helyi venvbe; telepített csomagból, a repository gyökerén kívülről is visszanyitotta a 848 bejegyzéses projektet. A környezetben nincs Torch, Transformers, Ollama, PyYAML, dotenv vagy requests.

## Regressziók és hibajavítások

Ellenőrzési parancsok:

```powershell
python -S -m unittest discover -s tests/tool -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_batch_cross_entry.py tests/unit/test_multiline_fix.py tests/integration/test_backend_switching.py -q -o addopts=
```

- Új modelltől független csomag: **43 sikeres teszt** a parseren, adatbázison és külön folyamatú JSON CLI-n. Lefedi a szöveg/HTML/szóköz/milliszekundum megőrzését, encodingokat, blokkdiagnosztikát, tartományokat, sémavédelmet, rollbacket, nyugtákat és megszakított export egyeztetését.
- Meglévő érintett útvonalak: **23 sikeres teszt**, három külső függőségi deprecation figyelmeztetéssel.
- Belső célzott ellenőrzés három konkrét hibát talált és a megvalósítás javította: hiányzó blokkhatár miatti összeolvadás; a Windows sandboxban tiltott hard-link export; SQLite-tartományon túli számok miatti JSON nélküli kivétel. A javítások tényleges kódon futó regressziókat kaptak.
- A JSON-kimenet nem függ a konzol Unicode-kódlapjától. Ismert hibás argumentum/bemenet esetén is egy gépi hiba és nem nulla exit code érkezik.

## Mi nincs kész?

M1 **első működő szelete** kész: import, tartós projekt, inspect/status/list, integritásellenőrzés, source/original export és nyugták. A legacy fordítási/standalone sortördelők teljes összevonása és a hosszabb távú migráció további munka. Célnyelvi fordítás, kézi szerkesztés, HTTP API, teljes skill, GUI, OAuth, képkockák és STT még nincsenek implementálva.

A következő munka az M1 fennmaradó formatterhatár rendezése, majd M2: a szolgáltatások fölötti csomag-/módosítási műveletek, API és skill. A korai GUI M7a továbbra is M2 után következik, az OAuth később marad.

A mostani roundtrip az eredeti adatok hű megőrzését igazolja. Több bejegyzésen átívelő szöveg **lefordítása**, más célnyelvi tördelése, formázási hatóköre és az eredeti start/stop időablakokra történő szemantikai visszaillesztése külön, kötelező M2-próba. A legacy csoportosítás/visszaosztás megőrzendő kiindulópont; az új eszköz fordítási szerződése is csoportos, időbélyegekhez illesztett feldolgozást ír elő.
