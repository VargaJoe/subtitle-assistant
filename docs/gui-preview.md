# Feliratműhely — korai GUI

Az M7a előzetes felülete a közös helyi projektet kezeli. A mentések ugyanazt a
revíziós API-t használják, mint az agent; nincs külön modellbelépés vagy MCP.
A teljes GUI-elfogadás még nyitott, az aktuális korlátokat külön rögzítjük.

## Megnyitás és munkatér

A repository gyökeréből az indító elindítja vagy eléri a helyi kiszolgálót,
és megnyitja a böngészőt:

```powershell
.\Start-SubtitleAssistant.cmd
```

Az alapmunkatér `.local/subtitle-assistant`. A jelenlegi FBI-pilot külön
munkatérben van; annak újranyitása:

```powershell
.\Start-SubtitleAssistant.cmd --workspace ".local\m7a-pilot\20261118T174200Z\workspace"
```

A munkatér útvonala az oldalsáv alján látszik. Az adatok ebben a könyvtárban,
`workspace.sqlite3` adatbázisban maradnak; másik munkatér megnyitása másik
projektlistát mutat. A böngésző URL-je önmagában nem indítja el a kiszolgálót.

## Mit jelent a Cody név?

Az agent munkajelzésben küldi az `agent_label` címkét, mentéseknél az `actor`
mezőt. A felület ezt a projektben rögzített nevet mutatja. A címke önmagában
nem hitelesített személyazonosság; más jogosult helyi kliens is küldhet címkét.

A hozzáférés ettől külön működik: a helyi API saját generált privát tokent
használ, a böngésző pedig egyszer használható indítási hivatkozásból kap helyi
session-cookie-t. Ez nem fordítóprovider API-kulcsa, és nem Codex/SuperGrok OAuth.
A privát runtime-fájlokat ne másoljuk promptba vagy forráskezelőbe.

## Agentmunka, ellenőrzés és letöltés

Az agent munkafázisa és a fordítás exportálhatósága külön állapot. Az agent
befejezheti a fordítást úgy, hogy néhány forráshelyet vagy célszöveget még
ellenőrizendőnek jelöl. Az „agent végzett” ezért nem jelent automatikusan
letölthető végleges SRT-t.

A fordítás státuszkártyája mutatja az átnézett/összes bejegyzést, az elmaradt
vagy ellenőrizendő sorokat és a hozzájuk vezető műveletet. Befejezetlen munka
is letölthető **munkaváltozatként**, megerősítés után. A `.draft.srt` a videóban
is jelöli a függő helyeket: `[ELLENŐRIZENDŐ]`, `[ELAVULT FORDÍTÁS]`, illetve
hiányzó célnál `[NINCS FORDÍTÁS]` és a forrásszöveg. Külön letölthető az
időbélyeges ellenőrzési lista. A letöltés az adott mentett revízió pillanatképe,
nem jelöli átnézettnek a szöveget; a szerkezeti/időhorgony-ellenőrzés továbbra is fut.

A végleges célnyelvi export minden bejegyzéshez aktuális, átnézett fordítást és
sikeres szerkezeti ellenőrzést igényel. A forrás is külön letölthető.

Kézi javításnál az **Átnézett fordítás** jelölést a szöveg/idő szerkesztése után
állítsd be, ha ellenőrizted az eredményt. A forrás vagy időzítés javítása
felülvizsgálandóvá teszi a korábbi fordítást. A kézi cél alapból védett.

A karakter/másodperc jelzés olvashatósági segítség, nem általános minőségi
garancia. A szöveg tömöríthető, vagy az időzítés kifejezetten javítható;
sortörés nem mozgathatja el az időhorgonyokat.

A részben megírt fordítást is el lehet menteni az **Átnézett fordítás** jelölés
nélkül; ilyenkor tartós munkaváltozatként marad meg. Az átnézettség nem mentési feltétel.

## Mi marad meg bezárás vagy frissítés után?

- A sikeresen **mentett** forrás, fordítás, időzítés, védelem, előzmény és
  munkajelzés tartós, ugyanazon munkatérből újranyitható.
- A még **nem mentett** szerkesztés a nyitott lap memóriájában él. Az alkalmazás
  távozás előtt figyelmeztet; frissítés előtt mentsd vagy vesd el a javításokat.
- Ha egy mentés eredménye hálózati hiba miatt ismeretlen, a lap megőrzi a pontos
  kérésazonosítót. Nyugtával ellenőrizhető vagy azonos kérésként újraküldhető;
  új azonosítóval megismételni nem szükséges.
- A böngészőlap bezárása nem töröl projektet. A felület **Bezárás** gombja a
  helyi kiszolgálót állítja le; a munkatér akkor is megmarad.

A teljes munkafolyamat és műveleti határok az
[agentes eszközleírásban](agent-tool-workflow.md) találhatók.
