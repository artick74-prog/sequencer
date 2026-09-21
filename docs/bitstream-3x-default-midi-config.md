# Bitstream 3X — default MIDI Config

Базовый профиль для текущего сетапа: Bitstream 3X работает как MIDI-контроллер для компьютера и как MIDI→USB интерфейс для Akai XR20.

## MIDI CONFIG

| Параметр | Значение по умолчанию | Назначение |
|---|---|---|
| MIDI Channel | 001 | Базовый MIDI-канал контроллера |
| Prg Ch → Scene | OFF | Program Change не переключает сцены Bitstream |
| Mackie fader fbk | OFF | Включать только при отдельной настройке Mackie Control |
| Shift lock Chan. | OFF | Не блокировать подстановку MIDI-канала в User Mode |
| Shift lock Midi | ON | При удержании SHIFT обычные контролы не отправляют MIDI наружу |
| Realtime → Internal state | OFF | Bitstream сам не генерирует MIDI Clock (F8) |
| Realtime → Tempo mode | One shot | Изменение внутреннего темпа применяется одним шагом |
| Realtime → Internal tempo | 130 BPM | Резервное значение; при Internal state = OFF не используется |
| Realtime → External source | USB In | Если понадобится внешняя синхронизация, брать её от компьютера по USB |
| Realtime → SMPTE rate | 24 FPS | Резервное значение; сейчас SMPTE не используется |
| Realtime → Internal mode | MIDI Clock | Оставить MIDI Clock, а не SMPTE |
| MIDI Filter → Filter State | ON | Входящий MIDI-фильтр включён |
| MIDI Filter → Filter Type | Realtime Events | Отсекаются realtime-события (Clock/Start/Stop/Continue), обычные Note/CC проходят |
| Merger Sources → MIDI In | ON | Принимать MIDI с внешнего DIN-входа, например с Akai XR20 |
| Merger Sources → USB In | OFF | Не принимать MIDI от компьютера в merger в базовом профиле |
| Merger Outputs → MIDI Out 1 | OFF | Не дублировать входящий MIDI обратно на DIN MIDI OUT 1 |
| Merger Outputs → USB Out 1 | ON | Передавать входящий MIDI с XR20 в компьютер по USB |

## Текущий сценарий маршрутизации

```
Akai XR20 MIDI OUT
        ↓
Bitstream 3X MIDI IN
        ↓
MIDI Merger
        ↓
USB OUT 1
        ↓
Computer
        ↓
Fender Studio / web sequencer
```

То есть для записи фингер-драмминга с XR20 используется правило:

**MIDI IN = ON → USB OUT 1 = ON**

и одновременно:

**USB IN = OFF, MIDI OUT 1 = OFF**

## Базовые глобальные настройки вне MIDI CONFIG

- Operating Mode: **Standard**
- Group Select: **000**
- Scene Select: **000**
- 2-Axis: **ON**
- Automations: **OFF**, если они специально не нужны
- Sync-24: **не использовать**, если нет отдельной задачи с DIN Sync

## Примечание по Mackie Control

`Mackie fader fbk` по умолчанию оставляем **OFF**. Если Bitstream будет отдельно настроен в Studio One как Mackie Control-пульт с двусторонней обратной связью, этот параметр можно протестировать в состоянии **ON**.
