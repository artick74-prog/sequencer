# Changelog

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
