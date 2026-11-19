# Felirateszköz v1.1 — M0/M1 mag és M2 agentes használat

Állapot: 2026-11-17. M0/M1 és az M2 szolgáltatási műveletei implementáltak. Az API-verzió 1.1, a munkatér sémája 2. A futtatható csoportos fordítási, szerkesztési és HTTP-példák az [agentes munkafolyamatban](agent-tool-workflow.md) találhatók. GUI és tartós történetkontextus későbbi lépés; a sorrend a [fejlesztési tervben](tool-first-development-plan.md) szerepel.

## Belépési pont és függőségek

```powershell
python -S -m subtitle_translator.tool capabilities --json
python -S -m subtitle_translator.tool doctor --json
```

A forrásból futó eszköznek Python 3.10+ és annak standard könyvtára szükséges. Nincs kötelező modell, API-kulcs, OAuth-belépés, HTTP szerver, MCP vagy Obsidian/MC kapcsolat. A `-S` bizonyítja, hogy a projektműveletek site-packages nélkül is futnak. Telepített csomagnál a `-S` nem használható, mert a telepítés helyét is kizárná.

Telepítés: `python -m pip install .` vagy a helyben épített wheel; a runtime alapfüggőséglista üres, az HTTP-adapter is standard könyvtárat használ. A `pyproject.toml` a legacy, MarianMT, Gemini és dev csomagcsoportokat külön kezeli. A régi `requirements.txt` a teljes korábbi környezethez megmarad.

A [repository AGENTS.md](../AGENTS.md) a [repo-skillre](../skills/subtitle-assistant/SKILL.md) és a CLI-re mutat. Az HTTP-kliens a munkatérből fedezi fel a helyi végpontot, titok kézi másolása nélkül. A legacy `main.py` és fordítóproviderek továbbra is használhatók, és csak a legacy konfiguráció használatakor történik providerfelderítés.

## Helyi munkatér és adatok

Alapértelmezés: az aktuális munkakönyvtár `.local/subtitle-assistant/` mappája. Más munkakönyvtárból mindig adjunk explicit abszolút `--workspace` értéket. A SQLite-fájl neve `workspace.sqlite3`; WAL-módban a mellékfájljai is a munkatér részei.

M0 döntés: az eredeti fájl **byte-pontos archívuma a SQLite projekt rekordjában BLOB-ként** tárolódik. Így az eredeti másolat, a bejegyzések és az importnyugta egy tranzakcióban keletkeznek; nem kell külön fájl és adatbázis félkész létrehozását egyeztetni. A felhasználói bemeneti fájl nem módosul. Ez pontosítja a terv korábbi, külön forrásfájlokat feltételező tárolási javaslatát.

| Adat | V1 döntés |
|---|---|
| `project_id` | `prj_` + UUID hex; külön import külön projekt |
| `entry_id` | Projektazonosító + `:entry:` + legalább 6 jegyes forráspozíció |
| `ordinal` | 1-től induló fizikai bejegyzéspozíció; nem az SRT sorszáma |
| `source_index` | Eredeti SRT sorszám; duplikáció megmarad és figyelmeztetést ad |
| Idő | Nem negatív egész milliszekundum; `end_ms > start_ms`; SQLite signed-64 tartomány |
| Szöveg | HTML, hangjelölés, sorok és soron belüli/széli szóközök megmaradnak; munkaszöveg sorvége LF |
| Eredeti adatok | Eredeti byte-ok és SHA-256, indexek, szövegek és időzítés külön megőrzött adatok |
| Munkaváltozat | Külön `source_text`, `start_ms`, `end_ms`, `source_revision`, `timing_revision`; `entry.edit` művelettel módosítható |
| Revízió | Új projekt `revision=1`, `context_revision=0`; eredeti adatokra támaszkodó védelmek már működnek |
| Séma | SQLite `application_id=0x53554241`, `user_version=2` |

Alaptáblák: `projects`, `entries`, `diagnostics`, `requests`. A v2 hozzáadja a `translations`, `batches`, `changes`, `jobs` táblákat. Új munkatér v2-ként indul; korábbi v1 munkatér olvasható, az új műveletekhez explicit `workspace migrate` kell, meglévő fájlt felül nem író SQLite-backuppal. Idegen/ismeretlen sémát nem alakítunk át. Régi `.progress`, output vagy tanított modell automatikus importja/törlése nincs.

## Szigorú import

- Automatikusan UTF-8/UTF-8 BOM támogatott. Más encodingot a hívó explicit megadhat: például `--encoding cp1250`. Nincs csendes latin-1 vagy karaktercserés fallback.
- CRLF, LF, CR és vegyes sorvég felismerhető; az eredeti byte-ok mindegyiknél megmaradnak.
- Hibás blokk, sorszám, időformátum, időtartam, tartománytúllépés vagy hiányzó blokkhatár tételes hibát ad blokk-/sorszámmal.
- A szigorú M1 import egyetlen hibás blokk esetén sem hoz létre részleges projektet. Az `inspect --input` a hibás fájlt is megvizsgálja, tárolási mellékhatás nélkül.
- Ismétlődő sorszám vagy csökkenő kezdőidő figyelmeztetés; a forrássorrend megmarad. Nem történik csendes átindexelés vagy rendezés.
- A numerikus sorszám után álló időbélyegszerű sor a törzsben hiányzó blokkhatárt jelez. Egy önálló, sorszám nélküli időbélyegszerű dialógussor önmagában nem bizonyít sérült blokkot; a program nem talál ki hiányzó bejegyzést.
- Az M1 parser alap SRT-időzítést fogad; időbélyeg utáni koordináta-/egyéb kiterjesztés nincs implementálva, ezért diagnosztikát ad.

Az új szigorú dokumentumimport külön útvonal a régi, toleráns fordítóparsertől. A milliszekundum-formázás és a megjelenítési sortördelés közös, modelltől független modulba került. A legacy writer, a standalone reformatter és az új célnyelvi export ugyanazt a formattert használja, bejegyzések közötti szövegmozgatás nélkül. A standalone reformatter átírás előtt a teljes fájlt szigorúan ellenőrzi. A forrás/original export nem használ megjelenítési tördelést.

## M1 műveletek

| Művelet | CLI |
|---|---|
| Képességek/állapot | `capabilities`, `doctor` |
| Tárolás nélküli vizsgálat | `project inspect --input <fájl> [--encoding ...]` |
| Import | `project import --input <fájl> [--source en] [--target hu] [--name ...] [--encoding ...] [--request-id UUID]` |
| Tárolt projekt | `project status --project <ID>` vagy `project inspect --project <ID>` |
| Projektlista | `project list [--limit 50] [--cursor ...]` |
| Bejegyzések | `entry list --project <ID> [--limit 50] [--cursor ...]` |
| Szerkezeti integritás | `project validate --project <ID>` |
| Export | `project export --project <ID> --output <új fájl> [--variant source\|original\|target\|draft] [--expected-revision N] [--request-id UUID]` |
| Nyugta | `request receipt --request-id UUID` |

A `--workspace` és `--json` a gyökérparancsnál vagy a konkrét művelet végén is megadható. A lista lapmérete 1–500, a kurzor a visszakapott `next_cursor` érték; a hívó nem számolja ki. Bejegyzéseknél az utolsó fizikai pozíció, projektlistánál offset a jelenlegi kurzor. M1-ben a lapozás nem zárol egy teljes listanézetet párhuzamos importokkal szemben; a stabil elemazonosítókat kell használni.

`source` export: kanonikus UTF-8, BOM nélkül, LF-sorvég, egy üres sor a blokkok között; a szöveget, HTML-t, SRT-sorszámot és időzítést nem tördeli át. `original` export: a teljes importált byte-sorozat változatlanul. Mindkettő a tárolt archívumból/projektből működik akkor is, ha az eredeti bemeneti fájl később nem elérhető. Az M2 `--variant target` végleges exportja csak teljes, aktuális és felülvizsgált fordításból készülhet, külön tördelési és időhorgony-ellenőrzéssel.

`--variant draft`: videóval kipróbálható, részleges munkaváltozat. A hiányzó cél helyén `[NINCS FORDÍTÁS]` és az aktuális forrásszöveg, a nem aktuális cél előtt `[ELAVULT FORDÍTÁS]`, egyéb ellenőrizendő hely előtt `[ELLENŐRIZENDŐ]` jelenik meg. A kész, aktuális célok jelöletlenek. A csoportos formázási/beszélőjelölési eltérések is felülvizsgálati jelzést kapnak. Az SRT-blokkok épsége és az összes aktuális index/start/stop horgony ekkor is kötelező; hiányzó cue nem hagyható ki. Az export nem írja át a fordítás állapotát, átnézettségét, védelmét vagy a projekt revízióját. A részleges célszöveg már mentéskor tartós `draft`/`unchecked` lehet, az átnézés külön művelet.

A draft export eredményének és tartós nyugtájának `draft` objektuma tartalmazza a projekt/revíziót, `entry_count`, `pending_count`, `missing_count`, `entries` és `formatting_issues` mezőket. Az `entries` minden érintett cue ID-ját, sorszámát, forrásindexét, időpontjait, okát (`missing_translation`, `stale_translation`, `review_required`, `formatting_review`), jelölését és szövegeredetét rögzíti. A GUI megerősítést kér, `.draft.srt` fájlnevet ad, és ugyanazon nyugtából letölthető időbélyeges `.draft.review.txt` listát kínál. A CLI/API tudatos `draft` variánsválasztása ennek megfelelő kifejezett kérés.

Meglévő kimenet felülírása M1-ben nincs. Az eredeti bemeneti útvonalra akkor sem lehet exportálni, ha azóta onnan eltűnt a fájl. Közzététel teljes ideiglenes fájlból, atomikusan és no-clobber módon történik: Windows alatt `rename`, POSIX alatt azonos fájlrendszerű hard link. Az export előtt archívumhash- és bejegyzésintegritás-ellenőrzés fut.

## Envelope, hibák és nyugták

A [JSON-séma](schemas/tool-v1.schema.json) definiálja az envelope-ot és az aktuális műveletek adatalakját. A [OpenAPI-leírás](schemas/tool-v1.openapi.json) a loopback adapter útvonalait rögzíti. Futás közben egyik adapter sem igényel sémaellenőrző könyvtárat; a közös szolgáltatási réteg azonos tartalmi védelmeket és hibakódokat használ.

`--json`: egy JSON-objektum stdouton, ANSI/preambulum nélkül. A JSON ASCII-escape-eket használ a Windows kódlapok miatti karaktervesztés ellen; `json.loads` után a teljes Unicode-szöveg áll rendelkezésre. Siker esetén exit 0, ismert műveleti/bemeneti hiba esetén exit 1. A `--help` emberi súgó, nem gépi művelet. Az `inspect` sikeres lefutása hibás fájlnál is exit 0 lehet: az eredmény `inspection.error_count` értékét ellenőrizni kell; az import ezzel szemben elutasítja a hibás fájlt.

Siker: `ok`, `api_version`, `request_id`, `data`, `warnings`. Hiba: `ok=false`, `api_version`, `request_id`, `error={code,message,details}`, `warnings`. A mutációk kliensoldalon generált UUID-t kapnak, ha nincs explicit ID; a CLI ismert hibánál is visszaadja azt. A read-only kérések ID-ja általában null. A fogyasztók új opcionális adatmezőket figyelmen kívül hagyhatnak; inkompatibilis alak új API-főverziót igényel.

| Hibatípus | Stabil kódok |
|---|---|
| Bemenet | `invalid_arguments`, `invalid_path`, `source_not_found`, `source_read_error`, `source_encoding_error`, `invalid_subtitle`, `invalid_language`, `invalid_request_id`, `invalid_cursor`, `invalid_page` |
| Tároló | `workspace_not_found`, `invalid_workspace`, `workspace_version_unsupported`, `workspace_busy`, `workspace_error`, `project_not_found` |
| Integritás | `source_integrity_error`, `project_integrity_error`, `revision_conflict`, `request_id_conflict` |
| Export | `unsupported_export_variant`, `source_overwrite_refused`, `output_exists`, `export_write_error`, `export_output_changed` |
| Egyeztetés/IO | `request_not_found`, `io_error` |

Azonos import-UUID és azonos normalizált payload ugyanazt a projektet/eredményt adja (`data.replayed=true`); eltérő payload elutasított. A bemeneti fájl hash-e is a payload része. Ha a bemenet időközben eltűnt vagy megváltozott, a korábbi eredményt a nyugtával kell lekérni. Az import a projektet, bejegyzéseket, diagnózist és kész nyugtát egy tranzakcióban írja.

Exportnál előbb tartós `pending` nyugta foglalja le a pontos műveletet, majd létrejön a fájl és `completed` állapot. Ha a folyamat a fájl létrehozása után megszakad, ugyanazzal az UUID-val és változatlan argumentumokkal a várt fájlhash egyeztethető és a nyugta lezárható. Megváltozott/eltűnt kész exportot a replay nem ír újra. A nyugta ismert eredményeket közöl; külső folyamat vagy kézi fájlváltoztatás esetén nem állít globális fájlrendszer-tranzakciót.

## M2 szerződés és későbbi kontextus

- Fordítási egység: összefüggő mondat-/párbeszédrész, amely több időzített bejegyzésre és több megjelenítési sorra is átnyúlhat. A tárolási `Entry` nem jelent külön, kontextus nélkül fordítandó mondatot. Az eredeti megjelenítési tördelés nem kötött célnyelvi tördelés.
- Visszaillesztés: a csoport fordítása új célnyelvi sorfelosztást és eltérő szövegelosztást kaphat, de az eredményt az eredeti bejegyzésazonosítókhoz és azok aktuális start/stop időablakaihoz kell illeszteni. Sortörésből nem keletkezik új időbélyeg vagy indexeltolódás; a csoportot az API-csomag mérethatára sem vághatja el észrevétlenül.
- Formázás: megőrzendő a jelölések hatóköre és a beszélők megkülönböztetése, a sor-/bejegyzéshatáron átnyúló formázást is beleértve. A nyers tag-ek puszta jelenléte nem igazolja a helyes célnyelvi formázást.
- Tartalmi módosítás: UUID, elvárt projektrevízió, azonosító és pontos változások; siker esetén új revízió, eredet és visszaállítható előzmény. A csomag snapshotja tartalmazza a bejegyzések forrás-/időzítésrevízióját is.
- Kézi forrás/időzítés: a munkaváltozat változik, az archívum nem; érintett kontextus/fordítás felülvizsgálandó, régi agentcsomag ütközik.
- Kézi célszöveg: alapból védett; nem azonos a teljes jelenet emberi elfogadásával.
- Fordítási csomag: azonosítók, forráshash/revíziók, kontextusverzió, csak olvasható előzmény/folytatás; válaszban fordítás, nem kitalált időbélyegek.
- Későbbi M3 kontextus: film/sorozat/epizód/jelenet, állítás és bizonyíték, érvényességi tartomány; ismeretlen beszélő/címzett engedett. M2 csak a környező feliratot és korábbi célszöveget adja át; a kontextusrevízió fenntartott alapja 0.
- Agentaktivitás: job/agent/fázis/csomag és szerver által mért frissesség; nem emeli a tartalmi revíziót. Elavult jelzés nem befejezés.
- Munkavezérlés: `pause_requested` külön a visszaigazolt `paused` állapottól. Külső agentet a helyi alkalmazás nem tud tetszőlegesen azonnal leállítani.

Az M2 műveletek és kérésalakok az [agentes munkafolyamatban](agent-tool-workflow.md) szerepelnek. A GUI M7a/M7b feladata. Az alkalmazás szerkezetet és horgonyokat ellenőriz; a fordítás jelentésének és szövegkörnyezetének helyességét az agent/ember vizsgálja.

A régi `translator.py` csoportosítása és HTML-kezelése regressziós kiindulópont. A karakterarányos visszaosztás heurisztika, nem bizonyítja, hogy a fordítás megfelelő jelentésrésze a megfelelő időablakba került. A csomag visszaillesztése nem pótolhat hiányt csendes üres/szövegismétlő paddinggel vagy pozíciós eltolással; bizonytalan eredményt javítandóként kell kezelni. Az M1 source/original roundtrip csak a tárolási/exportálási hűséget igazolja, még nem a lefordított szöveg időbeli és szemantikai illesztését.

## Ellenőrzés és következő határ

```powershell
python -S -m unittest discover -s tests/tool -q
```

Az M0/M1 roundtrip eredménye az [M0/M1 pilotjelentésben](m0-m1-pilot.md), az aktuális csoportos fordítás próbája az [M2 pilotjelentésben](m2-agent-pilot.md) szerepel. A következő fő lépés M7a: kétoszlopos GUI a már közös szerkesztési és munkajelzési szolgáltatások fölött. OAuth és tartós történetkontextus nem része az M2-nek.
