# Subtitle Assistant

🎬 **AI-alapú feliratfordító eszköz**, amely elsősorban azoknak készült, akiknek **szükségük van** feliratokra a multimédiás tartalmakhoz való hozzáféréshez (például a hallássérültek).

## 🎯 A projekt célja

**Fő cél**: A projekt azokat a felhasználókat szolgálja, akik **nem tudnak** feliratok nélkül filmeket vagy sorozatokat nézni — elsősorban a hallássérült közösséget, akik a feliratokra támaszkodnak a hozzáférés érdekében.

**Másodlagos célok**: Támogatja továbbá azokat, akik nem értik az eredeti nyelvet, illetve a nyelvtanulókat.

Bár a szélesebb közönség gyakran a feliratokat egyfajta luxusnak vagy kényelmi szolgáltatásnak tekinti, **elsődlegesen azokat tartom szem előtt, akiknek nincs alternatívájuk**. A célom, hogy kommunikációs szakadékokat hidaljunk át magas minőségű feliratfordításokkal, és valóban hozzáférhetővé tegyük a szórakoztatást mindenki számára.

## ⚡ Ajánlott: MarianMT Backend

**MarianMT** jelenleg az elsődlegesen ajánlott backend a feliratfordításhoz, mert megfelelő egyensúlyt kínál sebesség és minőség között.

> **Megjegyzés:** Csak az angol→magyar (EN→HU) fordítás lett teljes körűen tesztelve. A MarianMT sok más nyelvpárt is támogat (pl. német→magyar, japán→magyar stb.), de ezek minősége nem ismert, eltérő lehet. A legtöbb nyelvpárhoz elegendő a `--source` és `--target` paramétereket megadni, a modell automatikusan kiválasztásra kerül. A `--model` paraméter csak egyedi vagy nem szabványos modellekhez szükséges.

### Főbb jellemzők
- ⚡ **Nagyon gyors**: 40x gyorsabb, mint az Ollama (0.14s vs 5-6s bejegyzésenként)
- 🧠 **Intelligens feldolgozás**: Cross-entry mondatfelismerés több időbélyegen átívelő mondatokhoz
- 🎭 **Okos felismerés**: Automatikusan megkülönbözteti a párbeszédet és az időbélyegeken átívelő mondatokat
- ⏱️ **Időzítés megőrzése**: Arányos szövegkiosztással megtartja az eredeti felirat időzítését
- 🖥️ **Helyi feldolgozás**: A modellek letöltése után nincs szükség internetkapcsolatra
- 💾 **Automatikus modellkezelés**: A modellek automatikus letöltése és gyorsítótárazása
- 🔄 **GPU gyorsítás**: CUDA támogatás, ha elérhető; különben CPU fallback

### Gyors kezdés
```bash
# Angolról magyarra (tesztelt)
python main.py "movie.srt" --backend marian --source en --target hu

# Más nyelvpárok (minőség nem tesztelt)
python main.py "movie.srt" --backend marian --source ja --target hu
```

> **Tipp:** A fordítás minősége függhet a nyelvpártól és a felirat stílusától. Az eredmények finomhangolhatók a következő paraméterekkel:
> - `--cross-entry-detection` vagy `--no-cross-entry-detection`
> - `--multiline-strategy smart|preserve_lines|join_all`
> Próbálj ki különböző kombinációkat a legjobb eredmény érdekében az adott nyelvhez és feliratformátumhoz.

## 🛠️ Telepítés és beállítás

### Előfeltételek
- Python 3.8+
- MarianMT használatához: PyTorch és Transformers

### Beállítás
```bash
# Repository klónozása
git clone https://github.com/VargaJoe/subtitle-assistant.git
cd subtitle-assistant

# Függőségek telepítése
pip install -r requirements.txt

# Telepítés tesztelése
python main.py --help
```

## 🏗️ Fordítási backend rendszerek

### MarianMT Backend (ajánlott)
- **Legjobb elérhető megoldás:** Megbízható fordítási minőség (~80–90% elfogadható eredmény).
- **Ismert korlátozások:** Előfordulhat, hogy nehezebben kezeli a szlenget, formális/informális beszédváltásokat, és ritka esetekben értelmetlen kimenetet ad.
- **Nyelvek:** EN↔HU (Helsinki-NLP).
- **Model:** Helsinki-NLP/opus-mt-en-hu (484MB, automatikusan letöltődik).

### Ollama háttér (kísérleti)
- **Figyelem:** Alapos tesztelés ellenére az Ollama modellek nem adtak kielégítő fordítási minőséget, nem alkalmasak termelési használatra.
- **Alkalmas:** Kísérleti kutatáshoz, egyedi AI modellek vizsgálatához.
- **Hátrányok:** Lassabb, telepítést igényel, kísérleti státusz.

## 📚 Haladó funkciók

### Cross-Entry mondatfelismerés
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
