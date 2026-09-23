# Changelog

## 2026-09-24 — Grid-attached notes follow Swing live

### Fixed
- Moving the Swing slider now moves notes that are already exactly attached to the current straight/swung quantize grid together with the shifted grid lines.
- Free/humanized notes between grid lines are deliberately left untouched.
- Moving Swing back toward 0% remaps the same grid-attached notes back toward their straight positions, so the operation does not accumulate timing offsets.
- Playback scheduling is rebuilt when the slider gesture finishes; MIDI export continues to use the stored ticks literally.

## 2026-09-24 — Swing becomes an editable quantize grid

### Changed
- Swing is now a **0–100% quantize-grid parameter** instead of a hidden playback/export timing transform. 0% is straight; 100% gives the classic 2:1 triplet feel.
- Piano Roll draws the shifted swing subdivisions and uses the same positions for Snap, Draw, note drag, resize and Arrow Left/Right.
- Added **Apply Swing**: selected Piano Roll notes are quantized when a selection exists; otherwise the whole project is quantized. Applying it again does not accumulate extra swing.
- Playback and MIDI export now use stored note ticks literally, so a MIDI file that already contains swing is never swung a second time by the sequencer.
- Triplet quantize grids remain triplet grids and ignore Swing.

## 2026-09-24 — Marker row seeks the clicked bar

### Fixed
- Обычный клик по marker row или по подписи marker flag теперь ставит playhead на реально выбранный такт, а не притягивает его к началу секции. Двойной клик и ПКМ по флажку по-прежнему открывают редактор маркера.


## 2026-09-24 — Marker flags stay locked to bars while zooming

### Fixed
- Marker flags and vertical marker guides now derive their X-position directly from musical ticks and the current `barW`, so zooming the timeline moves them together with the bar grid instead of leaving the flags behind.
- Marker section widths are recalculated on every zoom step, preserving the existing ellipsis behavior without breaking bar alignment.


## 2026-09-24 — Marker labels stay inside their sections

### Fixed
- На узком timeline подпись каждого marker flag теперь жёстко ограничена пространством до следующего маркера и сокращается через `…`, не наезжая на соседей. На широком zoom полное название остаётся видимым, если оно реально помещается.


## 2026-09-24 — Responsive marker labels

### Fixed
- Подписи флажков на timeline теперь используют всё доступное место до следующего маркера. При широком zoom полное название показывается сразу; троеточие появляется только когда места действительно не хватает.


## 2026-09-24 — Editable marker flags

### Added
- Маркеры на timeline теперь выглядят как зелёные флажки; полный текст раскрывается при наведении/focus.
- Двойной клик или ПКМ по флажку открывает редактор названия с **Save**, **Copy name**, **Cancel** и **Delete**; Enter сохраняет, Esc закрывает.
- Обычный клик по флажку по-прежнему ставит cue на соответствующий такт.


## 2026-09-24 — Reload from AI replaces stale local working copy

### Fixed
- **Reload from AI** теперь загружает `projects/current.json` без повторного наложения старого local autosave и сразу переписывает local working copy новым проектом. Это предотвращает возврат удалённых/старых тактов после того, как ассистент перестроил аранжировку в GitHub.


## 2026-09-24 — Dedicated Sequencer download folder

### Changed
- MIDI-файлы из кнопки **MIDI**, общего **Export MIDI** и кнопки **↓** в MIDI Pool теперь сохраняются через local bridge в `Downloads/Sequencer`, а не смешиваются с обычными загрузками браузера.
- Папка создаётся автоматически при первом сохранении. Если local bridge недоступен, используется прежний browser-download fallback.


## 2026-09-24 — Drag-and-drop track ordering

### Added
- Дорожки MIDI Host теперь можно переставлять вверх и вниз drag-and-drop за handle **⋮⋮** слева от имени.
- При наведении показывается линия вставки сверху или снизу выбранной дорожки.
- Новый порядок сохраняется в проекте/локальном autosave и используется при последующем MIDI/cloud export; исходный `cubaseIndex` остаётся неизменным.


## 2026-09-24 — Larger track controls

### Changed
- Кнопки Edit / Preview / ⇄ / MIDI в заголовке дорожки увеличены и вынесены в отдельный второй ряд.
- S/M и octave controls остаются отдельным рядом; высота всех MIDI-дорожек увеличена одинаково, чтобы подписи и кнопки было проще читать и нажимать.


## 2026-09-24 — MIDI Exchange Pool

### Added
- Новый **⇄ MIDI Pool** для быстрого обмена отдельными MIDI-дорожками с Ableton / Studio One / Fender через реальную локальную папку.
- У каждой дорожки появилась кнопка **⇄**, сохраняющая её как однодорожечный Standard MIDI в Pool; обычная кнопка **MIDI** остаётся браузерным download.
- Pool drawer умеет открыть папку в Explorer, добавить/перетащить несколько `.mid/.midi`, обновить список и скачать отдельную копию.
- MIDI из Pool можно перетащить прямо на нужную дорожку и такт; внешний MIDI-файл можно также бросить прямо на timeline, после чего он автоматически попадает в Pool и вставляется в проект.
- Local bridge получил API для list/read/save/open MIDI Pool; сами обменные файлы не попадают в Git.


## 2026-09-24 — Channel-driven instrument routing

### Changed
- MIDI channel is now the active playback destination in Hardware MIDI Host: switching a GM-authored part to CH 1 / 2 / 3 / 10 routes that same MIDI part to XR20 Synth/Bass, TD-3, XR20 1-Shot or XR20 Drums instead of continuing to play its SoundFont program.
- The original GM program/name is preserved while auditioning through hardware, so moving the track back to a GM channel (4–9, 11–16) restores its previous SoundFont instrument.
- The GM Program selector is hidden while a track is on a hardware channel and reappears when it returns to the GM channel pool.
- SF2 fallback for hardware channels now follows the hardware role (Bass/Acid/Percussion) instead of the source GM program.


## 2026-09-23 — Piano/Drum Roll key audition

### Added
- Левая колонка Piano Roll теперь работает как обычная DAW-клавиатура: по клавишам можно нажимать и прослушивать ноты через текущий route дорожки.
- В Drum Roll нажатие по строке/pad preview'ит соответствующий GM/XR20 drum sound с учётом текущего drum view/listen режима.

### Fixed
- XR20 drum rows снова имеют читаемые названия даже при пустом Kit Profile: Kick, Snare, Closed Hi-Hat, Open Hi-Hat, toms, cymbals и т. п.
- Custom Kit Profile labels и явные GM assignments по-прежнему имеют приоритет над fallback-названиями.



## 2026-09-23 — XR20 direct drum-note fallback

### Fixed
- Library drum loops on XR20 tracks no longer go silent when the Kit Profile has no explicit GM assignment for notes that already match XR20 hardware note numbers.
- Explicit Kit Profile mappings still win; otherwise common direct notes such as 36/38/42 are routed straight to the matching XR20 pads.
- Acid Rock 1 now persists CH10 as `xr20-drums` with `drumMap=xr20`, `drumListen=xr20`, and the default XR20 kit profile in both current and cloud project snapshots.



## 2026-09-23 — Full-track Piano Roll and Acid Rock drum cleanup

### Changed
- Double-click по loop/Project Clip теперь открывает в Piano/Drum Roll всю дорожку целиком, а не только границы выбранного clip.
- Full-track Undo/Redo сохраняет всю дорожку вместе с clip ownership; loop containers остаются на timeline и по-прежнему поддерживают repeat/trim.
- В Acid Rock 1 первые 16 тактов Drums преобразованы из library-loop container в обычные ноты барабанной дорожки; квантизация 1/16 сохранена и в `projects/current.json`, и в cloud snapshot.

### Fixed
- Левый loop locator на bar 1 больше не попадает под sticky ruler gutter и теперь перетаскивается так же, как правый.



## 2026-09-23 — Uniform track lane height

### Fixed
- Все hardware и GM дорожки MIDI Host снова имеют одинаковую высоту.
- Пустой GM-program slot аппаратных дорожек больше не наследует глобальные стили `.empty`, которые раздували высоту lane.
- Timeline body и note vector теперь растягиваются на ту же стандартную высоту, что и track header.



## 2026-09-23 — Track GM selector layout

### Changed
- GM Program selector перенесён из строки имени/канала на отдельную строку между routing и кнопками track actions.
- Аппаратные дорожки сохраняют пустой slot той же высоты, поэтому все дорожки остаются выровненными.
- GM selector теперь использует доступную ширину track header и больше не вылезает на timeline.



## 2026-09-23 — Compact project header

### Changed
- **⚙ Settings** перенесён в левый верхний угол между **File ▾** и названием проекта.
- Поле названия проекта теперь автоматически меняет ширину по фактической длине текста вместо постоянной широкой рамки.



## 2026-09-23 — Header menu layout

### Changed
- **File ▾** перенесён в левый верхний угол перед названием проекта.
- **⚙ Settings** перенесён в крайний правый угол верхней навигации, после **Справка**.
- Transport toolbar очищен от меню File/Settings; MIDI route summary остаётся на месте.



## 2026-09-23 — Settings menu cleanup

### Changed
- MIDI Devices, MIDI Monitor и Timing спрятаны из transport toolbar в компактное меню **⚙ Settings**.
- MIDI route summary остаётся видимым рядом с transport, чтобы текущие IN/OUT были заметны без открытия настроек.


## 2026-09-23 — MIDI Devices routing dialog

### Added
- В Hardware MIDI Host добавлено окно **MIDI Devices…** с отдельным выбором Web MIDI input/output.
- В окне видны все доступные MIDI inputs/outputs, выбранные порты и последняя входящая MIDI-активность.
- Кнопка **Use Studio Ports** быстро выбирает `Bitstream In` как вход и `Studio Out` как выход.

### Changed
- При наличии loopMIDI браузер предпочитает виртуальные studio-порты вместо прямого захвата физического TD-3.
- Выбор MIDI In/Out сохраняется в локальном autosave; имена портов также сохраняются в cloud session.
- Текущая студийная раскладка закреплена в MIDI Host: CH1 XR20 bass, CH2 TD-3, CH3 XR20 percussion, CH10 XR20 drums; GM-скетч-каналы теперь начинаются с CH4.


## 2026-05-13 — Arrange View: Ruler, Drag-and-Drop, Context Menu

### Added

#### Тактовая линейка в Arrange View
- `.arrange-ruler` — общая линейка над дорожками A/B.
- Показывает **номера тактов** (bar labels) и **вспомогательные линии долей** (каждые 4 шага).
- **Playhead** — розовый вертикальный индикатор (`var(--playhead)`) текущей позиции воспроизведения.
- Позиция playhead рассчитывается как сумма ширин блоков до `seqIndex` + смещение внутри текущего паттерна по `currentStep`.
- Обновляется в реальном времени через `animatePlayhead()`.

#### Выравнивание линейки с паттернами
- Добавлен `blocksOffset = 61px` (lane padding 8 + label 24 + gap 8 + addBtn 18 + gap 3).
- Ширина линейки: `totalWidth + blocksOffset`.
- Все bar/beat lines и playhead смещены на `blocksOffset`, чтобы первая тактовая черта была ровно над началом первого блока.

#### Drag-and-drop перестановка блоков
- Каждый `.arrange-block` получил `draggable="true"` и `data-si` (индекс в `songSequence`).
- **dragstart** — блок становится полупрозрачным (`.dragging`), запоминается `_dragSourceSi`.
- **dragover** — вычисляется позиция вставки (левая/правая половина блока), показывается **плейсхолдер** (фуксийная полоска 3px, `.drag-placeholder`).
- **drop** — `splice(from, 1)` + `splice(to, 0, item)` с коррекцией индекса.
- **dragend** — очистка классов и плейсхолдеров.
- Работает на обеих дорожках A/B.

#### Delete pattern в контекстном меню
- Правый клик на блоке → контекстное меню → новый пункт «🗑 Delete» (после разделителя).
- Полностью удаляет паттерн: из `_arrangedPatterns[]`, из `songSequence[]` (все ссылки + сдвиг индексов), корректирует `_editingIdx` и `seqIndex`.
- Пункт `disabled` при единственном паттерне в проекте.

### Fixed

#### Контекстное меню не открывалось
- **Причина**: глобальный слушатель `contextmenu` на `document` сразу прятал меню после его показа.
- **Исправление**: добавлен `e.stopPropagation()` в `showPatternCtxMenu()`.
- Глобальные слушатели `click`/`contextmenu` теперь проверяют `_pCtx.contains(e.target)` — меню закрывается только при клике вне его.

### Changed

#### Убраны кнопки «+» между блоками
- В `renderLane()` убран `makeAddBtn(si)` из `forEach`.
- Кнопки «+» остались только по краям каждой дорожки (в начале + в конце).
- При пустой последовательности — один «+» + надпись «Click + to add a pattern».
