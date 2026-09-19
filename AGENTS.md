# Sequencer — контекст для ассистента

Музыкальный проект в `d:\Dev\Sequencer`. **Не связан с astroprofessor.**

Перед нетривиальной задачей читай этот файл.

## Окна проекта

| Файл | Назначение |
|------|------------|
| `index.html` | Chiptune / MIDI / SoundFont Piano Roll + Loop Constructor |
| `midi-host.html` | Hardware MIDI Host → TD-3 + XR20; GM-скетч-дорожки для прослушки/экспорта |
| `scripts/generate_td3_acid_riffs.py` | Генератор acid-фраз в `.mid` |

Запуск UI:

Рекомендуемый вариант для Hardware MIDI Host — локальный bridge-сервер:

```text
start-midi-host.bat
```

или:

```bash
python scripts/local_server.py --open
```

Он слушает только `127.0.0.1:8080`, открывает `http://localhost:8080/midi-host.html` и даёт UI одно-кнопочный обмен с GitHub:
- **Sync to AI** → пишет `projects/current.json` + overview, делает git commit и push;
- **Reload from AI** → делает `git pull --ff-only` и загружает свежий `projects/current.json`.

Обычный `python -m http.server 8080` остаётся fallback-вариантом без Git bridge.

- Chiptune: http://localhost:8080/
- Hardware host: http://localhost:8080/midi-host.html

### Chiptune Loop Constructor

`index.html` теперь умеет использовать ту же локальную MIDI Reference Library как конструктор.

- Кнопка **Loops** открывает справа встроенный Loop Browser.
- Browser читает `GET /api/library` и `GET /api/library/midi?id=...`; отдельная копия библиотеки не создаётся.
- **Preview** слушает MIDI при текущем BPM проекта, не изменяя piano roll, и следует engine активной дорожки: CHIP / SF2 / MIDI HW.
- Browser разделяет **Style / Role / Instrument family / GM Program**. `acid` считается стилем/жанром, а не инструментальной ролью: piano/chord MIDI из acid-набора больше не должен отображаться как role=acid. Для старых pack-index v2 UI вычисляет effective role из `classificationRoles` и `classificationPrograms`, поэтому фильтрация исправляется без немедленной перепаковки.
- В карточке loop показывается точный `GM <program> <name>`, если MIDI содержит Program Change. Если Program Change отсутствует, UI теперь различает данные файла и звук прослушивания: например `MIDI: no Program Change · Preview: GM 33 Electric Bass (finger)`. Это означает, что тембр пришёл из текущей настройки SF2-дорожки, а не из самого MIDI.
- При Preview в каждой карточке есть тонкий циклический progress bar и подпись общей длины (`bars · seconds`), чтобы сразу видеть длину loop и положение внутри текущего круга.
- У каждого loop есть пользовательский рейтинг **1–5 ★**, который хранится в browser localStorage по стабильному MIDI id. Повторный клик по текущей оценке очищает её. Фильтр Rating позволяет быстро показать rated loops, 4★+ favorites или выбранный минимальный рейтинг.
- У каждого loop можно задать пользовательское **display name** кнопкой ✎. Переименование не меняет исходный MIDI-файл и не трогает pack/member; alias хранится по стабильному MIDI id. При alias браузер показывает новое имя крупно и отдельной строкой `Original: ...mid`. Поиск учитывает и alias, и исходное имя.
- **LOAD** загружает MIDI в активную из трёх дорожек. После загрузки это обычные ноты секвенсора, а не живая ссылка на исходный файл.
- Короткий loop автоматически физически повторяется до длины текущего паттерна: 1 bar → 4 копии в 4-bar pattern, 2 bars → 2 копии и т.д.
- Если reference loop длиннее текущего паттерна, pattern автоматически расширяется до ближайшего целого такта (в пределах текущего лимита 16 bars).
- Melodic MIDI квантуется на сетку 1/16, но одновременно звучащие ноты, velocity и длительности/gate сохраняются в polyphonic cell. Импортированные `chords` и `arrangement` можно LOAD.
- У каждой дорожки есть engine:
  - **CHIP** — старый chiptune-осциллятор; melodic playback остаётся монофоническим, даже если внутри дорожки хранится аккорд;
  - **SF2** — полифонический SoundFont playback. По умолчанию используется Yamaha XG bank из `@logue/sf2synth`; кнопка **SF2…** позволяет загрузить локальный `.sf2`. Для melodic track выбирается GM Program 0–127;
  - **MIDI HW** — полифонический Web MIDI output во внешнее устройство с выбором канала. Дефолты под текущий сетап: Track 1 → ch1, Track 2 → ch2, Track 3 → ch10.
- TD-3 физически монофоничен: режим MIDI HW не делает сам TD-3 полифоническим. Но импортированные gate/duration и перекрытия Note On/Off сохраняются и отправляются наружу, поэтому legato/slide-жесты могут отрабатываться так, как их понимает сам TD-3.
- Для drums GM percussion преобразуется в 8 внутренних drum lanes, но при импорте для каждой lane запоминается доминирующий исходный GM drum note. Поэтому SF2/HW playback сохраняет исходный тип kick/snare/hat/cymbal настолько, насколько позволяет 8-lane модель.
- В track header хранится `Source` и есть **↻ Source**: заново загрузить исходный reference MIDI, если пользователь хочет сбросить свои правки на этой дорожке.
- Source metadata, engine, MIDI channel, GM program и polyphonic note data сохраняются внутри проекта/варианта; исходные файлы библиотеки никогда не изменяются.
- Piano Roll / Drum Grid поддерживают горизонтальный zoom обычным колесом мыши над сеткой: wheel up = шире, wheel down = уже/overview. Диапазон шага 4–64 px, zoom запоминается в localStorage и старается удерживать музыкальную позицию под курсором. Shift+wheel остаётся горизонтальной прокруткой.
- Верхняя кнопка **↓ Update** вызывает локальный `POST /api/update`: при чистом worktree делает `git fetch` + `git pull --ff-only origin main`, возвращает новый commit, затем локальный bridge сам корректно перезапускается на том же порту через свежий `scripts/local_server.py`. Браузер ждёт возвращения `/api/health` и сам перезагружает страницу с cache-buster. Это основной способ подтягивать новые изменения после первоначальной установки кнопки; PowerShell для обычных обновлений больше не нужен.

Кнопка **Sync to AI** в Chiptune пишет и пушит:
- `projects/chiptune-current.json` — полный проект и source metadata;
- `projects/chiptune-overview.md` — активный pattern, его длина, engine/channel/program каждой дорожки, источники/rating и polyphonic note events с velocity/gate;
- `projects/chiptune-loop-ratings.json` — текущие пользовательские оценки reference loops, чтобы ассистент после Sync мог учитывать favorites;
- `projects/chiptune-loop-aliases.json` — пользовательские display names reference loops. Алиасы также живут в browser localStorage, а после Sync сохраняются в репозитории; при запуске браузер подмешивает более свежие synced aliases обратно в локальное состояние;
- `projects/chiptune-loop-selection.json` — до 20 последних прослушанных loop с точными Program Change по MIDI-каналам, GM names/families, ролью и простой оценкой onset-polyphony. Это позволяет ассистенту после **Sync to AI** видеть, какие именно инструменты были в недавно прослушанных файлах.

После этой кнопки ассистент может прочитать текущее состояние конструктора из GitHub и обсуждать с пользователем конкретные загруженные лупы и их правки. Не утверждать, что видно текущее состояние браузера, пока пользователь не нажал **Sync to AI** после изменений.

---

## Hardware MIDI Host (`midi-host.html`)

Плеер Standard MIDI для живого сетапа + цикл правок через GitHub. Браузер и ассистент синхронизируются через папку `projects/`.

### Цепочка

```
PC USB → TD-3 → MIDI Out (5-pin DIN) → XR20 In
```

| Канал (1–16, как в Cubase) | Инструмент |
|----------------------------|------------|
| **2** | TD-3 acid (Behringer слушает ch2) |
| **1** | XR20 bass (сквозь TD-3 на DIN) |
| **10** | XR20 drums (сквозь TD-3 на DIN) |

Один MIDI Out = TD-3. У каждой Cubase-дорожки в UI свой `channel` (можно сменить).

### Импорт

- **Load MIDI** сохраняет **дорожки Cubase как есть** (имена, раздельно). Пустые conductor-треки без нот скрываются.
- Канал дорожки = самый частый channel в её нотах (потом правится в UI).
- Маркеры Cubase попадают в `markers[]` и в overview/sections.

### Синхронизация с AI / GitHub (важно)

Ассистент **не видит браузер** — он читает файлы из GitHub. Поэтому нормальный рабочий режим — запуск через `start-midi-host.bat` / `scripts/local_server.py`.

1. **Load MIDI** → загрузить многодорожечный Standard MIDI.
2. **Sync to AI**:
   - пишет `projects/current.json`, `overview.json`, `overview.md`;
   - автоматически делает git commit и `git push origin <current branch>`.
3. После Sync ассистент может сразу прочитать новую версию из GitHub.
4. Ассистент правит `current.json`/другие файлы в GitHub.
5. В хосте **Reload from AI**:
   - `git pull --ff-only`;
   - загрузка свежего `projects/current.json`;
   - Play.

API локального bridge:
- `GET /api/health` — проверка связи;
- `POST /api/sync` — write + commit + push;
- `POST /api/reload` — pull + return current.json.

Bridge перед Sync делает `git fetch` и не пушит поверх более свежей удалённой версии: в таком случае UI попросит сначала **Reload from AI**.

Старый **Bind projects/** остаётся fallback для браузеров с File System Access API. Без bridge и без Bind Sync скачивает файлы вручную.

### Файлы в `projects/`

| Файл | Назначение |
|------|------------|
| `current.json` | Полный проект (source of truth для нот) |
| `overview.md` / `overview.json` | Карта аранжировки + **ASCII-паттерны по секциям** (сетка 1/32) |

ASCII в overview:
- Сетка **1/32** (32 слота на такт). Humanized-ноты в пределах ±½ слота притягиваются к ближайшему слоту.
- Ноты дальше snap считаются `hardOff` (квантизация нарушена намеренно) — точные tick остаются в `current.json`.
- Легенда: `.` пусто · `x` удар · `X` акцент · `o` тихо · `*` две+ ноты в слоте · `#` пик heatmap.
- По каждой секции (маркеры Cubase): heatmap, паттерны треков, доминирующий 2-bar loop.
После Sync (или `python scripts/regen_overview.py`) ассистент читает ASCII по секциям.

### Формат `current.json`

```json
{
  "version": 1,
  "name": "my-groove",
  "ppq": 480,
  "tempo": 120,
  "tracks": [
    {
      "id": "t2",
      "name": "Bass",
      "channel": 1,
      "role": "xr20-bass",
      "mute": false,
      "notes": [
        { "tick": 0, "duration": 120, "note": 28, "velocity": 115 }
      ]
    }
  ]
}
```

- `channel` — **1–16** (Cubase-style).
- `tick` / `duration` — PPQ (при 480: 1/4 = 480, 1/16 = 120).
- Для точечной правки пользователь задаёт трек/секцию/такты в чате; остальное не трогать.

### Типичные запросы

- «Прочитай overview — где breakdown?»
- «На треке Bass, такты 17–32 — реже и ниже»
- «В Hook сделай TD-3 плотнее, остальные секции не трогай»
- «Reload сделал — теперь поправь тот же диапазон»

### TD-3: правило программирования Acid-партий (важно)

Для текущего железа пользователя **Velocity — не просто громкость, а главный способ управлять характером/акцентом TD-3**.

- Обычные acid-ноты держать **низкими по Velocity**, ориентир примерно **25–40**.
- Редкий сильный акцент поднимать примерно до **115–127**. На текущем TD-3 это даёт характерное резкое «кваканье»/раскрытие тембра.
- **Не** писать обычную acid-партию диапазоном 90–120 почти на каждой ноте: тогда пропадает контраст между телом паттерна и настоящим Accent.
- Высокий Velocity использовать **как смысловое событие**. Для текущего трека/вкуса пользователя рабочий ориентир — обычно 1–2 сильных акцента на такт или реже; это **не универсальный канон Acid**. Внешние 303-референсы могут быть заметно более акцентированными.
- При анализе и генерации Acid смотреть не только на pitch/tick, но обязательно на **velocity contour**.

Ритмическая логика:
- Сначала строить **16-step rhythmic machine pattern**, потом подбирать высоты.
- Предпочитать короткий повторяемый 1-тактовый рифф с паузами и редкими вариациями каждые 4/8 тактов.
- Большая часть нот может сидеть на одной опорной высоте; 1–2 соседние ноты работают как цвет/прокол.
- Избегать «лестниц», гаммообразных ходов и очевидного арпеджио, если пользователь специально этого не просит.
- Slide/legato делать точечно: небольшое перекрытие разных высот допустимо как 303-жест, но не превращать весь паттерн в связную линию.

Swing / ручные правки пользователя:
- После обработки в Fender Studio точные `tick` в `projects/current.json` считаются **намеренным грувом**.
- Не выравнивать обратно humanized/swing-позиции на строгую 1/16 без отдельной просьбы.
- Текущий Hook Acid **между маркерами Hook и Build 1** — эталон текущего вкуса пользователя по работе Velocity и swing: большинство нот имеют Velocity около 26–39, а один выраженный акцент в такте поднимается примерно до 118.
- При будущих правках Acid сохранять эту динамическую логику, если пользователь не попросил иной характер.

---

## MIDI Reference Library

Папка `reference-library/` — исследовательский корпус референсов для анализа музыкального языка. Это **не** набор готовых лупов для прямого копирования в проекты.

Сырьё:
- `raw/acidvoice/` — короткие TB-303 MIDI-паттерны;
- `raw/groove/` — Groove MIDI Dataset (барабаны, velocity, microtiming);
- `raw/nrgcp/` — dance/trance/house/EDM MIDI corpus.

Перед сочинением жанровой партии, когда нужен надёжный референс, сначала можно смотреть не только общие знания модели, но и производную статистику этого корпуса.

Анализатор:

```bash
python scripts/analyze_reference_library.py
```

Быстрый анализ одного источника:

```bash
python scripts/analyze_reference_library.py --source acidvoice
python scripts/analyze_reference_library.py --source groove
python scripts/analyze_reference_library.py --source nrgcp --limit 500
```

Результат: `reference-library/analysis/summary.json`. С `--details` также создаётся `files.jsonl`.

### Style Library Browser

`style-library.html` — локальный браузер MIDI-референсов. Он работает через `scripts/local_server.py` и читает большую локальную библиотеку **напрямую из MIDI-файлов, ZIP и TAR.GZ**, без обязательной распаковки и без загрузки больших WAV-паков в GitHub.

По умолчанию локальная библиотека берётся из соседней папки:

```text
d:\Dev\midi-reference
```

Путь можно переопределить переменной окружения `MIDI_REFERENCE_ROOT`.

Архитектура библиотеки двухслойная:
- исходные MIDI/ZIP/TAR.GZ остаются нетронутыми как raw corpus;
- производная папка `<MIDI_REFERENCE_ROOT>/packs/` содержит небольшие ZIP-паки, сгруппированные как **style → role/type → source**, максимум примерно 1000 MIDI на ZIP;
- `packs/library-index.json` хранит готовый индекс: id, source, genre, kind, roles, GM programs, pack/member и classification metadata;
- Style Library при наличии индекса читает именно packs, поэтому для построения списка не сканирует большой TAR.GZ, а preview достаёт один маленький member из ZIP;
- при первом старте после внедрения pack-архитектуры, если индекса ещё нет, сервер автоматически один раз классифицирует raw corpus и строит packs. Исходные архивы не удаляются;
- **Rebuild packs** пересобирает производный слой после добавления новых источников или изменения классификатора.

API bridge:
- `GET /api/library` — готовый индекс; предпочитает pack-index, при его отсутствии работает с raw;
- `GET /api/library/midi?id=...` — получить один MIDI из pack ZIP либо raw fallback;
- `POST /api/library/rescan` — перечитать текущий индекс;
- `POST /api/library/repack` — заново классифицировать raw corpus и атомарно пересобрать categorized ZIP packs;
- старый `POST /api/library/optimize` сохранён как fallback/диагностический endpoint.

Browser умеет фильтровать по source/style/type, слушать выбранный MIDI через GM SoundFont и одновременно отправлять его в Hardware MIDI. Для preview hardware обычно: bass → ch1 XR20, acid → ch2 TD-3, drums → ch10 XR20. Кнопка **Open in Host** открывает выбранный MIDI как проект в `midi-host.html`.

Классификация role/type использует имя/путь и содержимое MIDI: канал 10, регистр, полифонию и General MIDI Program Change. Многоканальные файлы с несколькими ролями могут получать тип `arrangement` и список ролей/GM-программ; неоднозначные остаются `unclassified`.

Playback в Style Library использует короткий lookahead scheduler вместо создания таймеров на весь MIDI сразу. При быстром переключении файлов старый fetch отменяется, старые MIDI-события очищаются, а загрузка SoundFont переиспользуется одной общей promise. В инспекторе выбранного файла показываются длина в тактах/времени и транспортная полоса с текущей позицией.

Правило использования:
- извлекать закономерности: onset pattern, плотность, интервалы, velocity, длительности, groove;
- не переносить конкретный MIDI-паттерн в проект один-в-один;
- AcidVoice особенно полезен как внешний референс 303-ритмики. В четырёх текущих файлах Accent закодирован контрастом Velocity примерно `64/74` против `127`; плотность Accent сильно различается между паттернами, поэтому переносить правило «1–2 Accent на такт» как жанровую догму нельзя;
- Groove — для drums/groove;
- NRG-CP — широкий EDM-корпус, поэтому не считать каждый пример каноническим Tech House/Acid House без дополнительной фильтрации.

---

## GM-оркестровка (скетч-дорожки)

Для разнообразия длинных партий (например Acid → духовые / фортепиано) добавляй **отдельные дорожки** под General MIDI. **Program Change не используем** — один трек = один инструмент навсегда.

### Именование дорожки (обязательно)

```
{program} {каноническое GM-имя}
```

Примеры: `56 Trumpet`, `0 Acoustic Grand Piano`, `66 Tenor Sax`, `61 Brass Section`.

- Номер **0–127** (мелодические GM-программы).
- Пробел после номера, затем имя из справочника `scripts/gm-instruments.json`.
- Хост парсит имя regex `^(\d{1,3})\s+(.+)$` → `role: "gm"`, program для будущего SF2-preview.

### Каналы

| Канал | Назначение |
|-------|------------|
| **1** | XR20 bass (железо) |
| **2** | TD-3 acid (железо) |
| **10** | XR20 drums (железо) |
| **3–9, 11–16** | GM-скетч (по одному инструменту на канал) |

Новый GM-трек: возьми **первый свободный** канал из `3–9, 11–16` (см. `nextFreeGmChannel` в `midi-host.html`).

### Как работать с Acid

1. Прочитай `overview.md` — где Acid перегружен / однообразен.
2. Добавь GM-дорожки (`56 Trumpet`, `0 Acoustic Grand Piano`, …).
3. **Перенеси** выбранные ноты с `Acid` (id `t15`, ch 2) на новые треки; на Acid эти ноты **удали**.
4. При необходимости **транспонируй** (303-диапазон C2–C4 → духовые/фортепиано обычно G3–C6).
5. Dub: не заливай духовыми всё подряд — точечно по секциям (Hook, Dance, Build).

### Формат трека в `current.json`

```json
{
  "id": "t17",
  "name": "56 Trumpet",
  "channel": 5,
  "role": "gm",
  "mute": false,
  "notes": [
    { "tick": 46080, "duration": 120, "note": 67, "velocity": 95 }
  ]
}
```

- `role`: `"gm"` для скетч-инструментов; железо — `xr20-bass`, `td3`, `xr20-drums`.
- **Не** пиши Program Change в MIDI — достаточно имени дорожки.

### Полезные GM для dub / оркестровки

| Program | Инструмент |
|--------:|------------|
| 0 | Acoustic Grand Piano |
| 48 | String Ensemble 1 |
| 56 | Trumpet |
| 58 | Trombone |
| 61 | Brass Section |
| 66 | Tenor Sax |
| 73 | Flute |

Полный список: `scripts/gm-instruments.json`.

### Экспорт / прослушка

- **Export MIDI** — отдельная Cubase-дорожка на каждый трек; имя `56 Trumpet` сохраняется; маркеры в conductor.
- На каждой дорожке есть кнопка **MIDI**: экспортирует только эту дорожку как **SMF Format 0** с одним `MTrk`; сохраняются tempo, 4/4, markers, исходный MIDI channel, note/velocity/duration. Это удобно для быстрой проверки/редактирования одной партии в Fender Studio/Cubase.
- **Browser audio (SF2)** в `midi-host.html`: при **Play** загружается GM SoundFont (Yamaha XG с CDN, или свой `.sf2` через **Load SF2**). Program берётся из **номера в имени** дорожки (`56 Trumpet` → preset 56). GM-треки играют только в SF2; железо (ch 1/2/10) — опционально через **Hardware MIDI Out**.
- Финальные тембры — Kontakt / другие VST в Cubase; MIDI-дорожки те же.

### Типичные запросы

- «Разбавь Acid в Dance 1: часть нот на 56 Trumpet и 0 Piano»
- «Добавь GM-strings на Build, Acid там урежь»
- «Прочитай overview — где Acid monotonous, предложи GM-дорожки»

---

## TD-3 Acid Riff Generator

Генератор MIDI-фраз для **Behringer TD-3** (TB-303 clone).

| Файл | Назначение |
|------|------------|
| `scripts/generate_td3_acid_riffs.py` | Генератор (чистый Python 3, без зависимостей) |
| `output/td3_acid_riffs_20.mid` | Текущий выход: 20 фраз |

### Запуск

```bash
python scripts/generate_td3_acid_riffs.py
```

### Формат файла (критично!)

Каждая фраза = **ровно 4 такта**:

```
[ 2 такта музыка ] → [ 2 такта тишина ] → следующая фраза
```

- Активная зона: **32 шестнадцатых** (ровно 2 такта нот)
- Пауза: **2 полных такта** тишины
- Всего: 20 × 4 = **80 тактов** (~2:40 при 120 BPM)

Маркеры в MIDI:
- `01 START Rolling E pump` — начало фразы
- `01 END` — конец музыки (начало паузы)

Под барабаны в DAW:
- **4-тактовый луп** = одна фраза целиком (play + rest)
- **2-тактовый луп** = только музыкальная часть

### Параметры MIDI

- **BPM:** 120 (dub)
- **Channel в генераторе:** 1 (MIDI channel 0 в коде) — для DAW/файлов-фраз
- **Живой сетап (midi-host):** TD-3 слушает **канал 2**
- **PPQ:** 480
- **Сетка:** 1/16
- **Диапазон нот:** E1–C2 (классический бас 303)
- **Акценты:** velocity 115 vs 88
- **Слайды:** tied notes (`slide=True` → note_off откладывается до следующей ноты другой высоты)

### Нормализация длины

Мотивы в `PHRASES` — **исходные паттерны**, не обязательно 2 такта.

`normalize_to_two_bars()`:
- считает фактическую длину мотива в 1/16;
- **циклически повторяет** мотив до 32 sixteenth notes;
- на границе повтора **слайд отключается**;
- поле `bars` в `PHRASES` — только справочно, **не задаёт длину**.

### Структура фразы в коде

```python
(
    [n(E1, 1, ACCENT), n(G1, 1, NORMAL, SLIDE), r(2), ...],
    1,                    # исходная длина (справочно)
    "Rolling E pump",
)
```

Хелперы: `n(note, dur_16ths, velocity, slide=False)`, `r(dur_16ths)`.

### TD-3: как слушать

1. MIDI → TD-3: в генераторе ch1; в живом хосте **ch2**
2. Cutoff высоко, resonance 60–80%, decay короткий
3. Slide/Accent на синте включены
4. Транспонирование — на TD-3 при необходимости

### Типичные запросы

- «Сгенерируй ещё 20 фраз в формате 2+2 @ 120»
- «Сделай фразы плотнее / агрессивнее»
- «Разбей на отдельные MIDI-файлы»
- «Поменяй BPM / тональность»
- «Во второй такт — вариация, а не просто повтор»

### История

Перенесено из `astroprofessor` (2026-07). Исходная проблема: фразы разной длины без чётких границ в piano roll. Решение: фиксированная сетка 2+2 и нормализация по фактической длине нот.
