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
- Style Library: http://localhost:8080/style-library.html
- Hardware host: http://localhost:8080/midi-host.html
- Все три страницы используют общую верхнюю навигационную шапку с кнопками **Chiptune Sequencer / Style Library / MIDI Host**; текущая страница подсвечивается.
- В Style Library есть кнопка **Library report**. Она строит инвентаризацию всей локальной MIDI-библиотеки из текущего pack/raw index и пушит в GitHub два файла: `reference-library/library-inventory.md` (читаемая сводка для Obsidian) и `reference-library/library-inventory.csv` (полный построчный каталог всех MIDI). В сводке есть counts по source/style/role/classification method, GM families/programs и разбивка по каждому source. Исходные MIDI при этом не копируются в GitHub.

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

### Sidebar / arrangement playlist

- Левый sidebar очищен от постоянного **Signal chain**, дублирующего **AI sync** блока и длинной служебной подсказки. Эти данные остаются в коде/проектных метаданных, но не занимают рабочее пространство.
- В sidebar остаются Browser audio / SoundFont и Hardware MIDI Out переключатели, краткая карточка Project и **Arrangement playlist**.
- Arrangement playlist строится из Cubase/MIDI markers. Каждый пункт показывает start bar, section name и диапазон тактов до следующего marker.
- Обычный клик по пункту playlist: останавливает текущий transport при необходимости, переносит playhead на marker, прокручивает timeline к этой позиции и сразу запускает playback от выбранной секции через активные SF2/HW routes.
- Во время воспроизведения текущая секция в playlist подсвечивается автоматически.
- Track/note/event counts и density map больше не показываются в sidebar; подробный `buildOverview()` остаётся для Sync to AI / overview files.
- В верхнем transport MIDI Host есть **Swing Grid 0–100%**, кнопка **Apply Swing** и **Master Transpose ±36 semitones**. Swing больше не является скрытым playback-эффектом: он деформирует выбранную straight quantize-grid Piano Roll; 0% = ровная сетка, 100% = 2:1 triplet feel. Triplet grid (`1/8T`, `1/16T`) Swing не деформирует.
- На каждой pitched track есть компактный **octave − / +** control (`transposeOctaves`, диапазон ±3 octaves). Drum/percussion tracks его не применяют.
- Swing Grid / master transpose / per-track octave сохраняются в project JSON и local autosave. Piano Roll рисует реально сдвинутые swing-линии, а Snap, Draw, drag, resize и Arrow Left/Right используют те же позиции. Ноты, уже стоящие точно на текущей quantize-grid, **двигаются вместе с линиями прямо при движении Swing slider**; свободные/humanized ноты между линиями не затрагиваются. **Apply Swing** остаётся явной квантизацией: при выделении меняются только выделенные ноты, без выделения — весь проект. Playback использует сохранённые ticks буквально и не добавляет второй swing-слой. В ⚙ Settings есть **DAW exchange · Straight MIDI**: явный Export MIDI / single-track MIDI / MIDI Pool export неразрушающе снимают текущий swing с grid-attached нот, а straight MIDI, возвращённый через MIDI Pool, автоматически садится обратно на текущую Swing Grid; Save Project / Sync to AI всегда сохраняют реальный project timing.
- У каждого MIDI Host track вместо checkbox Mute используются DAW-style кнопки **S / M**. **S** поддерживает multi-solo: если хотя бы один track solo, звучат только solo tracks, кроме отдельно muted; **M** всегда глушит конкретную дорожку.
- Track header имеет стабильную структуру: **name + MIDI channel**, отдельный **GM Program slot**, ряд **S/M + octave** и отдельный более крупный ряд **Edit / Preview / ⇄ / MIDI**. У GM-дорожек в program slot показывается полный список GM 0–127; у аппаратных дорожек этот slot остаётся пустым, чтобы все track lanes имели одинаковую высоту.
- Слева от имени дорожки есть drag-handle **⋮⋮**: дорожки можно переставлять вверх/вниз обычным drag-and-drop. Порядок сохраняется как порядок `project.tracks[]`; исходный `cubaseIndex` не переписывается и остаётся provenance исходного импорта.
- Высота всех MIDI Host track lanes зафиксирована одинаковой; hardware/GM больше не отличаются по высоте. Пустой hardware program slot использует отдельный placeholder-класс и не пересекается с глобальным `.empty`.
- S/M теперь работают без stop/restart transport: scheduler хранит общую очередь и проверяет актуальное solo/mute состояние прямо перед NOTE ON. SF2 timers тоже проверяют состояние в момент фактической отправки; Hardware MIDI использует короткий 120 ms lookahead. При переходе дорожки в silent уже звучащие её ноты получают NOTE OFF без глобального All Notes Off, поэтому остальные дорожки не должны спотыкаться.
- Muted/non-solo tracks больше не становятся полупрозрачными: состояние видно только по цвету кнопок S/M. Счётчики вида `264n` / `968n` из track header удалены.
- MIDI Host имеет локальный **autosave** в browser localStorage (`midi-host-autosave-v1`). Для текущего проекта автоматически сохраняются routing каждой track (channel/role), Solo/Mute, per-track octave, project name, tempo, Swing и Master Transpose; из UI — zoom, Loop, выбранные MIDI In / MIDI Out и Browser Audio / Hardware MIDI toggles. Сохранение вызывается при каждом изменении и ещё раз на `beforeunload`.
- Кнопка **MIDI Devices…** открывает встроенное окно Web MIDI routing. В нём вручную выбираются **Receive From** и **Send To**, показываются все доступные inputs/outputs и последняя активность входа. Кнопка **Use Studio Ports** выбирает текущий виртуальный studio-route: `Bitstream In` → browser и browser → `Studio Out`. При первом запуске эти имена также являются preferred defaults, поэтому старый прямой TD-3 route не должен перехватываться, если loopMIDI уже запущен.
- Служебные кнопки **MIDI Devices…**, **MIDI Monitor** и **Timing** убраны из постоянной transport-панели в компактное меню **⚙ Settings**. Сам MIDI route summary остаётся видимым в toolbar.
- Верхняя шапка MIDI Host теперь устроена как desktop-приложение: слева идут **File ▾ → ⚙ Settings → название проекта**. В transport-панели меню File/Settings больше не дублируются.
- Поле названия проекта автоматически подстраивает ширину под фактический текст: короткое имя занимает мало места, длинное растягивает поле до установленного максимума.
- Кнопка **☁ Save Project** создаёт при первом сохранении самостоятельную GitHub-папку `projects/cloud/<project-id>/`, а последующие сохранения обновляют ту же папку. Внутри: `manifest.json`, `README.md`, `midi-host/project.json`, `session.json`, `overview.json/.md`, полный `arrangement.mid` и отдельный Standard MIDI для каждой дорожки в `midi-host/tracks/`. Поэтому облачный проект не зависит от скачанного локального JSON для восстановления музыкального материала.
- Cloud folder намеренно рассчитан на два редактора: сейчас `manifest.editors.midiHost=true`, а позже Chiptune Sequencer сможет сохранять свою часть в той же папке под `chiptune/`.
- Кнопка **☁ Projects** открывает встроенный список `projects/cloud/*`. Серверные GET endpoint'ы `/api/projects` и `/api/project/load?id=<project-id>` отдают список проектов и полный MIDI Host snapshot. При Open cloud snapshot считается авторитетным: его routing/Solo/Mute не перекрываются глобальным local autosave; затем открытый snapshot сам становится новым локальным autosave. Также восстанавливаются session-настройки (zoom, loop, Browser Audio / Hardware MIDI Out и MIDI Out по имени, если устройство уже доступно).
- В MIDI Host есть встроенный **♫ Loops** drawer, который читает тот же `/api/library`, что Chiptune Loop Browser. Доступны search + style/role/instrument-family/exact-GM-program/source/rating filters; ratings/aliases используют те же localStorage keys, поэтому оценки совместимы между двумя редакторами. Preview всегда идёт через browser SF2, не через hardware MIDI.
- Карточки Loop Browser draggable. Drop на `.track-body` выбирает target track и bar по X-позиции, привязывает начало к началу такта, масштабирует source PPQ в project PPQ и добавляет ноты в текущую аранжировку без изменения исходного MIDI. Для CH10/XR20 Drums предпочтительно берутся source notes на MIDI channel 10; для остальных target tracks — pitched notes не на channel 10.
- Для XR20 Drums GM→XR20 mapping сначала использует явные назначения Kit Profile. Если назначения нет, но GM note уже совпадает со стандартным MIDI note аппаратного XR20 pad (например 36 Kick, 38 Snare, 42 Closed Hat), применяется прямой fallback на этот pad. Такой hit **не считается unresolved и не подавляется на Hardware MIDI Out**.
- Каждый drop записывается в `project.clips[]` с source library id, target track/startTick и provenance. **☁ Save Project** передаёт уникальные использованные library ids серверу; сервер копирует точные исходные MIDI в `midi-host/clips/` внутри cloud project и перечисляет их в `manifest.json`. Таким образом cloud project хранит не только итоговый arrangement/track MIDI, но и оригинальные library clips, реально использованные в проекте.
- Local autosave MIDI Host теперь также содержит `workingProject` — полный текущий editable project snapshot. После refresh / one-click Update он восстанавливается раньше `projects/current.json`, поэтому ещё не отправленные в GitHub drag/drop правки не теряются. Cloud meta показывает `UNSAVED` после вставки и очищается после **☁ Save Project**.
- Основные project/file actions MIDI Host сгруппированы в верхнее меню **File**: **New Project**, **Open Project…**, **Save Project**, Import MIDI/JSON, Export MIDI, а также служебные Reload/Sync/Bind. Горячие клавиши: Ctrl/Cmd+N, Ctrl/Cmd+O, Ctrl/Cmd+S.
- Timeline markers отображаются как зелёные **флажки**. Обычный клик в marker row, в том числе поверх подписи флажка, ставит cue на **реально кликнутый такт**; маркер не магнитит playhead к началу секции. Двойной клик или ПКМ по флажку открывает редактор полного названия с **Save / Copy name / Delete**. Позиция флажка вычисляется напрямую из musical tick → bar grid (`tick / ticksPerBar * barW`), поэтому при zoom он остаётся жёстко привязан к своему такту. Каждый флажок ограничен шириной секции до следующего маркера: при широком zoom полное название видно сразу, а при узком оно обрезается через троеточие и не наезжает на соседей.
- **New Project** отвязывается от предыдущей cloud-папки и создаёт 32-тактовый starter project с пустыми дорожками Bass (CH1 XR20), Acid (CH2 TD-3), Percussion (CH3 XR20 1-Shot), Overdriven Guitar (GM29/CH4), Electric Piano 1 (GM4/CH5), Drums (CH10 XR20). Пустой starter timeline держится через `minimumLengthTicks`, пока новые MIDI clips не удлинят аранжировку.
- После refresh / one-click Update / обычного перезапуска браузера локальный `workingProject` может восстановиться раньше `projects/current.json`, чтобы не потерять незасинхронизированные правки. Но явная команда **Reload from AI** теперь является жёсткой перезагрузкой: она грузит `projects/current.json` с `restoreLocal: false` и сразу переписывает local autosave, поэтому устаревшая локальная копия больше не может вернуть старые такты. Обычное автоматическое наложение routing/settings по signature сохраняется для стандартной загрузки проекта.


Плеер Standard MIDI для живого сетапа + цикл правок через GitHub. Браузер и ассистент синхронизируются через папку `projects/`.

### MIDI Exchange Pool

Для быстрого обмена отдельными MIDI-партиями с Ableton / Studio One / Fender MIDI Host имеет локальный **⇄ MIDI Pool**.

- Локальный bridge хранит реальные `.mid/.midi` файлы вне Git-репозитория в `%LOCALAPPDATA%\Sequencer\MIDI Pool` (путь можно переопределить через `MIDI_EXCHANGE_ROOT`).
- Кнопка **⇄** в заголовке дорожки пишет текущую дорожку в Pool как однодорожечный Standard MIDI. Кнопка **MIDI**, общий **Export MIDI** и кнопка **↓** у файла в Pool сохраняют MIDI через local bridge в `%USERPROFILE%\Downloads\Sequencer` (путь можно переопределить через `SEQUENCER_DOWNLOAD_ROOT`); если bridge недоступен, остаётся fallback на обычный browser download.
- Кнопка **⇄ MIDI Pool** в toolbar открывает drawer со списком файлов, **Open folder**, **+ MIDI…** и Refresh. Open folder нужен для надёжного обмена с внешними DAW через обычный Explorer, без зависимости от browser-to-desktop drag API.
- Файлы из Pool можно drag-and-drop на любую дорожку/такт MIDI Host; они вставляются как обычный Project Clip с текущим non-destructive provenance/revert snapshot.
- Внешний `.mid/.midi` также можно бросить прямо на timeline-дорожку: файл сначала сохраняется в Pool, затем вставляется в выбранный такт.
- Drag нескольких внешних MIDI на одну дорожку пока импортирует только первый файл; сам Pool принимает несколько файлов за раз.
- API bridge: `GET /api/midi-pool`, `GET /api/midi-pool/file?name=...`, `POST /api/midi-pool/save`, `POST /api/midi-pool/open`, `POST /api/midi-download/save`.

### Цепочка

Текущий Windows studio-route строится через loopMIDI + MIDI-OX, чтобы Fender Studio и браузерный MIDI Host могли оставаться открытыми одновременно и не захватывали физические MIDI-порты напрямую:

```text
Bitstream 3X → MIDI-OX → Bitstream In (loopMIDI) → Fender / browser

Fender / browser → Studio Out (loopMIDI) → MIDI-OX → TD-3 USB
                                                     ↓
                                              MIDI OUT (DIN)
                                                     ↓
                                                   XR20
```

В приложениях выбираются виртуальные порты **Bitstream In** и **Studio Out**. Физические `Bitstream 3X` / `TD-3` держит MIDI-OX.

| Канал (1–16, как в Fender/Studio One) | Инструмент |
|----------------------------|------------|
| **1** | XR20 bass / Synth |
| **2** | TD-3 acid |
| **3** | XR20 percussion / 1-Shot |
| **10** | XR20 drums |

Один виртуальный MIDI Out = `Studio Out`; дальше MIDI-OX отдаёт поток в TD-3, а TD-3 пропускает нужные каналы на XR20 по DIN. У каждой дорожки в UI свой `channel` (можно сменить).

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

## Rhythm Library / live audition

- Собственная pitch-free библиотека ритмических формул: `user-library/rhythms/index.json`; схема описана в `user-library/rhythms/README.md`.
- Rhythm pattern хранит абстрактную сетку (`bars`, `stepsPerBar`) и события `pos / dur / vel`; MIDI pitch в библиотеке не хранится.
- В MIDI Host кнопка **♬ Rhythms** открывает отдельный Rhythm Browser.
- Пользователь выбирает pitched target track, start bar, fixed audition pitch и Gate. Клик по rhythm pattern:
  - временно глушит только NOTE ON исходной target track;
  - ставит project Loop на длину pattern (обычно 1 bar, clave = 2 bars);
  - запускает project backing tracks и одновременно играет rhythm pattern через реальный route target track (TD-3/XR20/SF2);
  - показывает временный ghost slot на timeline;
  - не меняет project notes до **Apply to track**.
- **Previous / Next** позволяют быстро листать отфильтрованные rhythms; category/search работают поверх одной библиотеки.
- Global MIDI Host Swing остаётся отдельным groove-layer; Rhythm Gate масштабирует только длительности событий.
- **Apply to track** заменяет note onsets внутри audition slot, после подтверждения. Если slot пересекает library clip, clip metadata отсоединяется, чтобы provenance не лгал после редактирования.
- Библиотека расширена до **278** формул: Core 20 + Guitar 144 + Bass 42 + Acid 36 + Keys 36.
- В Rhythm Browser добавлен фильтр **Bank**. Режим `Auto for target` автоматически подбирает Guitar/Bass/Acid/Keys по выбранной дорожке (role / GM program / имени); `All banks` показывает всё.
- Guitar events могут дополнительно хранить будущие articulation metadata `attack` (`CHORD/CHOKE/MUTE/SUSTAIN`) и `stroke` (`DOWN/UP`). Текущий playback пока использует только `pos/dur/vel`, но articulation metadata не теряется.
- У каждой Rhythm Browser карточки есть **✎ editor**. Ручные правки не меняют built-in pattern: **Save as new revision** добавляет персональную редакцию.
- После появления редакций карточка показывает **‹ / ›** и счётчик: `O · N` = оригинал + N редакций, `V3/10` = выбранная 3-я из 10. Стрелки сразу audition'ят выбранную версию.
- В редакторе attack можно добавить/удалить кликом; существующий hit можно drag-and-drop передвинуть по сетке с сохранением `dur/vel` и guitar articulation metadata.
- **LIVE preview в Rhythm Editor** включён всегда: открытие ✎ запускает/продолжает audition, а каждый click/drag немедленно подменяет временный rhythm overlay без перезапуска backing transport. Cancel/Close возвращает сохранённую Original/revision; Save передаёт audition уже новой сохранённой revision.
- Browser presentation теперь группирует built-in patterns с **одинаковыми onset positions** внутри одного bank/family/bar/grid в одну карточку. Разные `dur/vel` исполнения этой же ритмической формы листаются отдельными **Variant ‹ / ›**; source entries в `index.json` при этом не удаляются.
- В Rhythm Editor выбранный hit имеет музыкальные duration presets `1/32, 1/16, 1/16·, 1/8, 1/8·, 1/4, 1/4·, 1/2, 1/2·, 1/1`; ширина зелёного блока визуально отражает stored `dur`. Для 16-step 4/4 это соответственно `0.5,1,1.5,2,3,4,6,8,12,16` grid steps; для 12-step triplet grid значения пересчитываются пропорционально.
- Global Rhythm **Gate** остаётся отдельным playback multiplier поверх stored duration: при 100% длительность соответствует выбранной музыкальной величине.
- Rhythm Editor использует **no-overlap** правило для ручных правок: после add/move hit все предыдущие ноты, которые заходят за следующий onset, автоматически укорачиваются ровно до этого onset. Выбор слишком длинного duration preset также cap'ится следующим onset; последняя нота cap'ится границей pattern. Удаление следующего hit обратно ноту не растягивает автоматически.
- Кнопка **▣** на выбранной редакции сохраняет её как отдельный custom rhythm. Редакции и custom rhythms сейчас живут в browser localStorage (`midi_host_rhythm_revisions_v1`, `midi_host_custom_rhythms_v1`) и переживают обычный refresh / one-click Update; built-in `index.json` не переписывается.

## User Style Library (arranger-style drafts)

Отдельно от внешней MIDI Reference Library существует собственная библиотека переиспользуемых стилей:

- индекс: `user-library/styles/index.json`;
- документация схемы: `user-library/styles/README.md`;
- черновики: `user-library/styles/drafts/<style-id>/style.json`.
- В `style-library.html` кнопка **My Styles** показывает эти заготовки отдельно от внешних MIDI loops.
- Кнопка открытия draft style ведёт в `midi-host.html?userStyle=<id>`; MIDI Host создаёт самостоятельную 16-тактовую заготовку с bass + drums из style JSON.
- Draft style хранит одновременно:
  - готовые `realizedNotes` для немедленного воспроизведения;
  - `events` баса в бар-относительном виде (`bar`, `tick`, `duration`, `rootRef`, `interval`, `velocity`) для будущего reharmonize;
  - default harmony и provenance исходного drum loop.
- Жизненный цикл: `draft` → `mature`. Позже mature style может получить arranger-секции Main A/B/C/D, Fill, Break, Intro, Ending.
- Первые заготовки:
  - **Acid Rock 1** — текущий rock drum groove + Tresillo Rock bass;
  - **Acid Rock 2** — тот же drum family + Kick Lock Long bass.
- Не путать cloud project и user style: project — конкретная аранжировка, style — переиспользуемый шаблон.


## Main timeline ruler gesture
- Горизонтальный zoom основного timeline теперь имеет тот же максимум, что Piano Roll: `BAR_W_MAX = PIANO_ROLL_BAR_W_MAX = 8192 px/bar`. Нумерация тактов исправлена: при достаточном zoom (`labelEvery=1`) подписывается каждый такт; при сильном zoom-out подписи по-прежнему прореживаются, чтобы не наслаиваться.


- Основная линейка секвенсора теперь повторяет Piano Roll: обычный click или преимущественно horizontal drag двигает cue/playhead по тактам; преимущественно vertical drag меняет горизонтальный zoom.
- Направление одинаковое с Piano Roll: drag вниз = шире/zoom in, drag вверх = уже/zoom out. `Ctrl/Cmd + wheel` использует то же направление: wheel down = шире, wheel up = уже.
- После того как vertical drag уже вошёл в zoom mode, ЛКМ остаётся зажатой и горизонтальное движение одновременно pan'ит timeline в Studio One-style direct manipulation: мышь вправо → содержимое timeline визуально едет вправо, мышь влево → содержимое едет влево. Режим не переключается обратно в seek до отпускания кнопки.
- `Shift+drag` по-прежнему задаёт loop range, зелёные locator handles работают отдельно и не смешиваются с zoom gesture.
## Track Piano Roll / Project Clips

- Loop Browser остаётся источником preview/drag-and-drop. После drop MIDI остаётся **Project Clip** на timeline: clip хранит repeat/trim/provenance и может растягиваться как loop, но исходный Library MIDI никогда не редактируется напрямую.
- Двойной клик по любому видимому Project Clip теперь открывает **всю дорожку целиком**, а не только диапазон конкретного clip. Кнопка **Edit** на track header делает то же самое. В Piano/Drum Roll видны все ноты дорожки от начала до текущей длины проекта, включая ноты, принадлежащие loop clips и обычным Track Parts.
- Левая колонка Piano/Drum Roll является audition keyboard: click/pointer-down по piano key или drum row проигрывает соответствующий pitch/pad через текущий route дорожки. Для XR20 row audition учитывает текущий drum view/listen mapping. XR20 drum rows всегда показывают понятные fallback-названия (Kick, Snare, Closed Hi-Hat и т. п.), если в Kit Profile нет custom/GM label.
- Для full-track editor используется скрытый `nativeTrackPart` как backing store новых нот, но существующие `clipId` сохраняются. Поэтому loop на timeline остаётся loop-контейнером, а его ноты одновременно доступны в общем Piano/Drum Roll. При редактировании loop, с которого открыт editor, этот clip помечается как edited instance.
- Dock показывает track, **Full track**, project bar range, note count, MIDI/drum rows, bar/beat grid и playhead, синхронизированный с главным transport.
- Нижний Piano Roll можно закрыть и менять по высоте drag'ом верхнего разделителя; высота сохраняется в localStorage `midi_host_piano_roll_height_v1`. Максимальная высота почти равна всей высоте `.main`. Pitch canvas содержит полный MIDI-диапазон 0–127; колесо мыши прокручивает регистр. Горизонтальный zoom: `Ctrl/Cmd + wheel` (24–8192 px/bar); ruler gesture поддерживает cue/pan/vertical-drag zoom.
- `Snap to Grid` поддерживает `1/4`, `1/8`, `1/8T`, `1/16`, `1/16T`, `1/32`, `1/64` (default `1/16`, хранится в `midi_host_piano_roll_snap_v1`). Пустой manual Project Clip по-прежнему может открываться как отдельный 1-bar MIDI Part для быстрого Draw.
- Tool modes: `1` = Select/Arrow, `5` = Draw/Paint; при Draw удержание `Ctrl/Cmd` временно включает Select. Box/multi-select и Ctrl/Cmd-click работают на всех видимых нотах дорожки.
- Горячие клавиши используют `KeyboardEvent.code`; `Ctrl/Cmd+C/V/D/A/Z/Y`, Arrow Left/Right, Arrow Up/Down и Shift+Up/Down работают внутри editor. Undo/Redo в full-track mode сохраняет snapshots **всей дорожки**, включая clip ownership, до 100 состояний.
- Новые ноты, нарисованные в full-track mode вне отдельного clip editor, принадлежат скрытому Track Part; существующие loop-owned ноты сохраняют свой `clipId`.
- Audition и live commit работают как раньше: изменения слышны сразу, а при playback scheduler перезапускается с текущего tick.
- Loop locators на основной линейке независимы от playhead. Левый locator больше не выступает под sticky gutter на bar 1, поэтому его можно нормально перетаскивать вправо; Shift+drag по ruler задаёт весь loop range.


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
| **3** | XR20 percussion / 1-Shot (железо) |
| **4–9, 11–16** | GM-скетч (по одному инструменту на канал) |

В MIDI Host **канал является текущим playback destination**. Если GM-партию временно переключить на **ch 1 / 2 / 3 / 10**, аппаратный route имеет приоритет над её GM-именем: та же MIDI-партия играет соответственно XR20 Synth/Bass, TD-3, XR20 1-Shot или XR20 Drums. Возврат на канал из GM-пула снова включает SoundFont и восстанавливает GM program из имени дорожки.

Новый GM-трек: возьми **первый свободный** канал из `4–9, 11–16` (см. `nextFreeGmChannel` в `midi-host.html`).

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
- **Browser audio (SF2)** в `midi-host.html`: при **Play** загружается GM SoundFont (Yamaha XG с CDN, или свой `.sf2` через **Load SF2**). Program берётся из **номера в имени** дорожки (`56 Trumpet` → preset 56). На GM-каналах 4–9 и 11–16 дорожка играет через SF2; временный перевод этой же партии на аппаратный ch 1/2/3/10 сразу переключает playback на соответствующее железо. При возврате на GM-канал исходный GM program сохраняется.
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
