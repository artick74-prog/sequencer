# Sequencer — контекст для ассистента

Музыкальный проект в `d:\Dev\Sequencer`. **Не связан с astroprofessor.**

Перед нетривиальной задачей читай этот файл.

## Окна проекта

| Файл | Назначение |
|------|------------|
| `index.html` | Chiptune Piano Roll (Web Audio, без железа) |
| `midi-host.html` | Hardware MIDI Host → TD-3 + XR20; GM-скетч-дорожки для прослушки/экспорта |
| `scripts/generate_td3_acid_riffs.py` | Генератор acid-фраз в `.mid` |

Запуск UI:

```bash
python -m http.server 8080
```

- Chiptune: http://localhost:8080/
- Hardware host: http://localhost:8080/midi-host.html

Web MIDI работает в **Chrome / Edge** на `localhost`. Встроенный браузер Cursor может не отдать MIDI — тогда открыть URL снаружи.

---

## Hardware MIDI Host (`midi-host.html`)

Плеер Standard MIDI для живого сетапа + цикл правок с Cursor. Браузер и Cursor синхронизируются через папку `projects/`.

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

### Синхронизация с Cursor (важно)

Ассистент **не видит браузер** — только файлы в репо.

1. Один раз: **Bind projects/** → выбрать `d:\Dev\Sequencer\projects` (Chrome/Edge).
2. Load MIDI → **Sync to Cursor** — пишет прямо в репо:
   - `projects/current.json` — все ноты
   - `projects/overview.json` — структура (маркеры, секции, плотность по 8 тактам)
   - `projects/overview.md` — то же человекочитаемо (удобно читать ассистенту)
3. Выделить регион → **Prepare for AI** — Sync + `selection.json` + промпт в буфер.
4. В чате: «посмотри overview и перепиши selection…»
5. Ассистент читает overview → правит `current.json` в диапазоне selection.
6. В хосте: **Reload** → Play.

Без Bind: Sync скачивает файлы — положи их в `projects/` вручную.

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
| `selection.json` | Регион правки (trackId, bars, ticks) |

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
- При правке selection: удалить ноты с `tick ∈ [startTick, endTick)`, вписать новые в том же диапазоне; остальное не трогать.

### Типичные запросы

- «Прочитай overview — где breakdown? Перепиши selection под него»
- «Перепиши selection как breakdown»
- «На треке Bass, такты 17–32 — реже и ниже»
- «Reload сделал — теперь плотнее TD-3 в том же регионе»

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
