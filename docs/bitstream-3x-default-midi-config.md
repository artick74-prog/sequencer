# Bitstream 3X — default MIDI Config

Базовый профиль для текущего сетапа: Bitstream 3X работает как MIDI-контроллер для компьютера и как MIDI→USB интерфейс для Akai XR20.

> Важно: на конкретном Bitstream 3X пользователя (firmware 1.8 / hardware 2.0) опытным путём подтверждено, что для передачи входящего DIN MIDI в компьютер через MIDI Merger должны быть одновременно включены **MIDI Out 1** и **USB Out 1**. При USB Out 1 = ON и MIDI Out 1 = OFF входящий MIDI в USB не проходил.

## MIDI CONFIG

| Параметр | Значение по умолчанию | Назначение |
|---|---|---|
| MIDI Channel | 016 | Канал собственных фейдеров/ручек Bitstream; вынесен отдельно от музыкальных каналов XR20/TD-3 |
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
| MIDI Filter → Filter State | ON | В рабочем профиле входящий фильтр включён |
| MIDI Filter → Filter Type | Realtime Events | Отсекаются realtime-события (Clock/Start/Stop/Continue), обычные Note/CC проходят |
| Merger Sources → MIDI In | ON | Принимать MIDI с внешнего DIN-входа (XR20 / другой источник) |
| Merger Sources → USB In | OFF | Не принимать MIDI от компьютера в merger в базовом профиле |
| Merger Outputs → MIDI Out 1 | ON | **Обязательно ON для проверенной работы DIN MIDI IN → USB на этом экземпляре** |
| Merger Outputs → USB Out 1 | ON | Передавать merged MIDI в компьютер по USB |

## Проверенный сценарий маршрутизации

```
Akai XR20 MIDI OUT
        ↓
Bitstream 3X MIDI IN
        ↓
MIDI Merger
        ├── MIDI OUT 1 (ON)
        └── USB OUT 1  (ON)
                    ↓
                 Computer
                    ↓
       Fender Studio / Ableton / web sequencer
```

Для записи фингер-драмминга с XR20 используется:

**MIDI IN = ON**  
**USB IN = OFF**  
**MIDI OUT 1 = ON**  
**USB OUT 1 = ON**

### Важно про MIDI-петлю

Поскольку MIDI OUT 1 теперь включён, не подключать его в такую цепь, которая возвращается обратно в Bitstream MIDI IN, если специально не строится контролируемый MIDI-loop/merger. Если DIN MIDI OUT 1 физически никуда не подключён — проблемы нет.

## Текущая карта MIDI-каналов

| Источник | MIDI Channel |
|---|---:|
| XR20 SYNTH / Bass | 1 |
| TD-3 | 2 |
| XR20 1-SHOT | 3 |
| XR20 DRUM | 10 |
| Bitstream controls | 16 |

## Диагностика MIDI-OX — подтверждено

После включения одновременно **MIDI Out 1 + USB Out 1** входящие ноты появились в MIDI-OX. Пример:
- STATUS 90 / 80 — Note On / Note Off на MIDI Channel 1
- DATA1 28h = MIDI note 40 (E2)
- DATA1 29h = MIDI note 41 (F2)
- DATA1 34h = MIDI note 52 (E3)
- B0 7B 00 — CC 123, All Notes Off

В наблюдаемом логе входящий merged MIDI появлялся на MIDI-OX input **IN 2**. Для DAW следует проверить второй виртуальный Bitstream USB input (`Bitstream 3X (Port 2)` / `MIDIIN2 (Bitstream 3X)`) как основной вход для внешнего MIDI, пришедшего через DIN MIDI IN.

## Базовые глобальные настройки вне MIDI CONFIG

- Operating Mode: **Standard**
- Group Select: **000**
- Scene Select: **000**
- 2-Axis: **ON**
- Automations: **OFF**, если они специально не нужны
- Sync-24: **не использовать**, если нет отдельной задачи с DIN Sync

## Примечание по Mackie Control

`Mackie fader fbk` по умолчанию оставляем **OFF**. Если Bitstream будет отдельно настроен в Studio One/Fender Studio Pro как Mackie Control-пульт с двусторонней обратной связью, этот параметр можно протестировать в состоянии **ON**.
