# MIDI Reference Library

Эта папка — исследовательский корпус для анализа музыкальных решений, а не библиотека готовых лупов для прямого использования в релизах.

Цель: извлекать из референсов закономерности — ритм, плотность, интервалы, velocity, микротайминг, структуру партий и типичные способы развития — а затем писать новые партии для текущих проектов.

## Структура

```text
reference-library/
  raw/
    acidvoice/
    groove/
    nrgcp/
  analysis/
  sources.json
```

- `raw/` — исходные MIDI/архивы без правок.
- `analysis/` — производные компактные отчёты, которые создаёт анализатор.
- `sources.json` — происхождение и назначение каждого корпуса.

## Текущие источники

### AcidVoice TB-303 patterns

Четыре коротких референсных MIDI-паттерна: `pattern07.mid`, `pattern14.mid`, `pattern19.mid`, `pattern23.mid`.

Используются прежде всего для анализа 303-логики: позиции атак, паузы, повторяемость, интервалы, velocity/accent и длительности нот.

### Groove MIDI Dataset

MIDI-only архив Google/Magenta Groove MIDI Dataset.

Используется прежде всего для барабанного groove: kick/snare/hats/percussion, velocity и микротайминг.

### NRG-CP

Корпус коротких dance/trance/house/EDM MIDI-фрагментов.

Используется как материал для анализа гармонико-ритмических фигур, плотности и повторяемых паттернов. Не считать весь корпус «чистым Tech House» или «чистым Acid House»: жанровую применимость надо проверять по конкретным результатам анализа.

## Анализ

Запуск без зависимостей:

```bash
python scripts/analyze_reference_library.py
```

Только один источник:

```bash
python scripts/analyze_reference_library.py --source acidvoice
python scripts/analyze_reference_library.py --source groove
python scripts/analyze_reference_library.py --source nrgcp
```

Для быстрого теста большого корпуса:

```bash
python scripts/analyze_reference_library.py --source nrgcp --limit 500
```

С детальными записями по каждому MIDI:

```bash
python scripts/analyze_reference_library.py --details
```

Результаты:
- `reference-library/analysis/summary.json` — компактная статистика по корпусам;
- `reference-library/analysis/files.jsonl` — опциональная детализация по каждому файлу.

Анализатор считает:
- tempo / PPQ / размер;
- количество нот и ориентировочную плотность;
- 16-step onset histogram;
- pitch mode и интервалы относительно него;
- velocity;
- для барабанов — группы kick / snare-clap / closed hat / open hat / toms / cymbals / other percussion.

Это только первый слой. Позже поверх этих данных можно строить жанровые профили и генератор новых вариантов, который использует статистику корпуса, но не копирует конкретный MIDI один в один.
