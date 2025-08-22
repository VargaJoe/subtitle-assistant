# Subtitle Assistant

🎬 **AI-alapú feliratfordító eszköz**, amely elsősorban azoknak készült, akiknek **szükségük van** feliratokra a multimédiás tartalmakhoz való hozzáféréshez (például a hallássérültek).

## 🎯 A projekt célja

**Fő cél**: A projekt azokat a felhasználókat szolgálja, akik **nem tudnak** feliratok nélkül filmeket vagy sorozatokat nézni — elsősorban a hallássérült közösséget, akik a feliratokra támaszkodnak a hozzáférés érdekében.

**Másodlagos célok**: Támogatja továbbá azokat, akik nem értik az eredeti nyelvet, illetve a nyelvtanulókat.

Bár a szélesebb közönség gyakran a feliratokat egyfajta luxusnak vagy kényelmi szolgáltatásnak tekinti, **elsődlegesen azokat tartom szem előtt, akiknek nincs alternatívájuk**. A célom, hogy kommunikációs szakadékokat hidaljunk át magas minőségű feliratfordításokkal, és valóban hozzáférhetővé tegyük a szórakoztatást mindenki számára.

## ⚡ Ajánlott: MarianMT Backend 

**MarianMT** jelenleg az elsődlegesen ajánlott backend a feliratfordításhoz, mert megfelelő egyensúlyt kínál sebesség és minőség között.

### 🚀 Gyors kezdés MarianMT-vel

```bash
# Egyetlen felirat file fordítása
python main.py "movie.srt" --backend marian

# Időbélyegeken átívelő mondat felismerése (ajánlott)
python main.py "movie.srt" --backend marian --multiline-strategy smart

# Több file együttes fordítása
python main.py "subtitles/*.srt" --backend marian --verbose

# Különféle többsoros fordítási stratégiák
python main.py "movie.srt" --backend marian --multiline-strategy smart      # Inteligens felismerés
python main.py "movie.srt" --backend marian --multiline-strategy preserve_lines  # Sortörések megtartása
python main.py "movie.srt" --backend marian --multiline-strategy join_all  # Mondatok összefűzése
```

### 🎯 MarianMT főbb jellemzői

- ⚡ **Nagyon gyors**: jelentős sebességjavulás a korábbi megoldásokhoz képest
- 🧠 **Intelligens feldolgozás**: cross-entry mondatfelismerés több időbélyegen átívelő mondatokhoz
- 🎭 **Okos felismerés**: automatikusan megkülönbözteti a párbeszédet és az időbélyegeken átívelő mondatokat
- ⏱️ **Időzítés megőrzése**: arányos szövegkiosztással megtartja az eredeti felirat időzítését
- 🖥️ **Helyi feldolgozás**: a modellek letöltése után nincs szükség internetkapcsolatra
- 💾 **Automatikus modellkezelés**: a modellek automatikus letöltése és gyorsítótárazása
- 🔄 **GPU gyorsítás**: CUDA támogatás, ha elérhető; különben CPU fallback

## 🛠️ Telepítés és beállítás

### Előfeltételek
- Python 3.8+
- MarianMT használatához: PyTorch és Transformers

### MarianMT beállítása (ajánlott)

```bash
# Clone repository
git clone https://github.com/VargaJoe/subtitle-assistant.git
cd subtitle-assistant

# Install dependencies (including MarianMT)
pip install -r requirements.txt

# Test installation
python main.py --help
```

### Alternatíva: Ollama Backend (haladó felhasználóknak kísérletezéshez)

```bash
# Ollama telepítése (lásd: ollama.ai)
# Model letöltése fordításhoz
ollama pull gemma3:latest

# Ollama backend beállítása a config.yaml file-ban
translation:
  backend: "ollama"
```

## 📖 Használati példák

### Alap fordítás

```bash
# Egyszerű fordítás (EN → HU)
python main.py "episode.srt"

# Kimeneti file megadása
python main.py "episode.srt" --output "episode.hu.srt"

# Verbose (beszédes) output
python main.py "episode.srt" --verbose
```

### Haladó MarianMT funkciók

```bash
# Okos többsoros )cross-entry) felismerés (ajánlott)
python main.py "episode.srt" --backend marian --multiline-strategy smart --cross-entry-detection

# Többsoros felismerés kikapcsolása szükség esetén
python main.py "episode.srt" --backend marian --no-cross-entry-detection

# különféle fordítási módok
python main.py "episode.srt" --backend marian --mode line-by-line  # Mondatonkénti fordítás, folytatható
python main.py "episode.srt" --backend marian --mode batch         # Gyorsabb feldolgozáshoz
python main.py "episode.srt" --backend marian --mode whole-file    # Kis file-ok esetén a leggyorsabb
```

### Batch feldolgozás

```bash
# az összes felirat file feldolgozása egy mappán belül
python main.py "season1/*.srt" --backend marian --verbose

# Feldolgozás kimeneti file nevezéktana alapján
python main.py "season1/*.srt" --backend marian --output "translated/{name}.hu.srt"
```

## 🏗️ Fordítási backend rendszerek

### 🔥 MarianMT Backend (ajánlott)
- **Legjobb elérhető megoldás:** A MarianMT a tesztelt backend rendszerek közül a legjobb alap fordítási minőséget biztosítja, általában **80–90%** körül elfogadható eredményt adva.
- **Ismert korlátozások:** Előfordulhat, hogy nehezebben kezeli a speciális szleng/argo kifejezéseket, formális/informális beszédváltásokat, illetve ritkán előfordulhat számára értelmetlen kimenet.
- **Leginkább alkalmas:** használatra, gyors feldolgozásra és megbízható alapminőségre
- **Előnyök:** nagyon gyors, többsoros felismerés, offline mód
- **Hátrányok:** csak fordítással foglalkozik (nincs multi-model pipeline), időnként előforduló minőség-ingadozások
- **Nyelvek:** EN↔HU (Helsinki-NLP)
- **Model:** Helsinki-NLP/opus-mt-en-hu (484MB, automatikusan letöltődik)

### 🧪 Ollama háttér (kísérleti, nem ajánlott)
- **Figyelem:** Alapos kísérletezés és prompt-optimalizálás ellenére az Ollama modellek (sem fordításra, sem multi-model pipeline-ra) nem adtak kielégítő minőséget. A fordítás gyakran nem ajánlott használatra.
- **Alkalmas:** kísérleti kutatáshoz, egyedi modellek vizsgálatához
- **Hátrányok:** lassabb, Ollama telepítést igényel, kísérleti státusz, a tesztek alapján gyengébb fordítási minőség
- **Funkciók:** elméletben multi-model architektúra 4 lépéses munkafolyamattal: szövegösszefüggés → fordítás → ellenőrzés → dialógus (a gyakorlatban a minőség nem megfelelő)

## 🎛️ Konfiguráció

A konfigurációt a `config.yaml` kezeli, CLI felülírási lehetőségekkel:

```yaml
# MarianMT beállítás (ajánlott)
translation:
  backend: "marian"
  source_language: "en"
  target_language: "hu"

marian:
  multiline_strategy: "smart"      # Intelligens felismerés
  cross_entry_detection: true     # Cross-entry mondatok figyelése
  max_new_tokens: 128
  device: "auto"                   # "auto", "cuda", "cpu"

processing:
  translation_mode: "line-by-line"
  resume_enabled: true
  verbose: true
```

## 📚 Haladó funkciók

### Cross-Entry mondatfelismerés (MarianMT)
Automatikusan felismeri azokat a mondatokat, amelyek több egymást követő felirat-bejegyzésen, időbélyegen átívelnek:

```
Input:  Entry 1: "This is now"
        Entry 2: "an NYPD homicide investigation,"  
        Entry 3: "so if we collar Hughes, we'll let you know."

Result: Translates as unified sentence while preserving original timing
        Entry 1: "Ez"
        Entry 2: "most egy rendőrségi gyilkossági"
        Entry 3: "nyomozás, szóval ha elkapjuk Hughest, szólunk."
```

### Multi-Model Pipeline (Ollama)
Speciális, 4 lépéses fordítási munkafolyamat:
1. **Context Analysis** - történet- és szereplőelemzés
2. **Translation** - kontextusfigyelő elsődleges fordítás
3. **Technical Validation** - nyelvtani és minőségi ellenőrzés
4. **Dialogue Specialist** - karakterhang és konzisztencia

## 🔍 Teljesítmény-összehasonlítás

| Háttér    | Sebesség / bejegyzés | Jellemzők                                | Minőség            | Ajánlott használat       |
|-----------|----------------------|------------------------------------------|--------------------|--------------------------|
| **MarianMT** | **0.14s** ⚡⚡⚡⚡⚡   | Cross-entry detection, Smart multiline   | **Jó (80–90%)** ⭐⭐⭐⭐ | **Termelés**            |
| Ollama    | 5-6s ⚡               | Multi-model pipeline, Context analysis   | **Nem kielégítő**  | Kísérleti / nem ajánlott |

## 📋 Támogatott nyelvpárok

### MarianMT (Helsinki-NLP modellek)
- **Elsődleges**: Angol ↔ Magyar ✅ (teljes körű tesztelés)

### Ollama
- Bármely nyelvpár, amelyet a kiválasztott modell támogat

## 📖 Dokumentáció

- **[MarianMT User Guide](docs/MARIANMT_USER_GUIDE.md)** - Teljes MarianMT használati útmutató ⭐ **Ajánlott**
- **[Multi-Model Architecture Guide](docs/multi-model-guide.md)** - Haladó Ollama pipeline dokumentáció
- **[Implementation Tasks](docs/implementation-tasks.md)** - Fejlesztési előrehaladás követése
- **[Traditional Translation Guide](docs/traditional-translation-guide.md)** - Alapfordítási módok

## 🧪 Tesztelés

```bash
# Run cross-entry detection tests
python tests/test_cross_entry_detection.py

# Test translation with sample file
python main.py "test_sample.srt" --backend marian --verbose
```

## ⚠️ Fontos megjegyzések

- **A MarianMT a jelenleg elérhető legjobb fordítási megoldás**, körülbelül 80–90% kielégítő eredménnyel a feliratokra; időnként előfordulhat nehezebb szleng, formális/informális beszédváltás, vagy ritka, nehezen értelmezhető kimenet.
- Az Ollama háttér (fordításra és multi-model megoldásokra) nem adott elfogadható eredményt alapos kísérletezés után sem.
- A cross-entry mondatfelismerés egyedi MarianMT funkció, amely jobb fordítási minőséget biztosít összetett feliratoknál.
- Az összes feldolgozás helyben történik — nincs adatküldés külső szolgáltatásoknak.
- **Ez az eszköz elsődlegesen a hallássérült felhasználók hozzáférését prioritizálja**, nem a kényelmi funkciókat a felhasználók számára.

## 📜 Modell licenc & attribúció

A projekt a Helsinki-NLP/opus-mt-en-hu modellt használja angol↔magyar fordításhoz MarianMT-n keresztül.

- **Model:** [Helsinki-NLP/opus-mt-en-hu on Hugging Face](https://huggingface.co/Helsinki-NLP/opus-mt-en-hu)
- **Licenc:** MIT License (lásd a model card-ot)
- **Attribúció:** © Tiedemann, Jörg, OPUS-MT, University of Helsinki

Kérjük, tekintse át a modell licencét és feltételeit, mielőtt kereskedelmi vagy nyilvános felhasználásra alkalmazná.

## 🤝 Közreműködés

Szívesen fogadjuk a hozzájárulásokat! Kérjük, nézze meg a fejlesztési útmutatót a részletes irányelvekért.

## 📄 Licenc

A projekt MIT licenc alatt áll — lásd a LICENSE fájlt a részletekért.

---

**🎬 Élvezze a lefordított feliratokat MarianMT villámgyors feldolgozásával és intelligens cross-entry felismerésével!**
