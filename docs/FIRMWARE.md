[🔙 На главную](../README.md)

# 🔥 Прошивка FLOOK32

**Файл:** `flook32.ino`

Подробное техническое описание прошивки ESP32 для контроллера нагрева камеры.

---

## Содержание

1. [Общая информация](#1-общая-информация)
2. [Аппаратная часть](#2-аппаратная-часть)
3. [Структура прошивки](#3-структура-прошивки-setup--loop)
4. [Датчики](#4-датчики)
5. [Управление SSR](#5-управление-ssr-нагреватель)
6. [Управление вентилятором](#6-управление-вентилятором-pwm)
7. [Система защит](#7-система-защит)
8. [Термальная модель](#8-термальная-модель-машинное-обучение)
9. [Адаптация](#9-адаптация-самонастройка)
10. [Система ошибок и журналирования](#10-система-ошибок-и-журналирования)
11. [История для графика](#11-история-для-графика-trends)
12. [LED индикация](#12-led-индикация-neopixel-ws2812b)
13. [Звуковая индикация](#13-звуковая-индикация-зуммер)
14. [Watchdog](#14-watchdog)
15. [Интеграция с Klipper/Moonraker](#15-интеграция-с-klippermoonraker)
16. [Ручной таймер](#16-ручной-таймер)
17. [Кнопка сброса](#17-кнопка-сброса)
18. [Автоперезагрузка](#18-автоперезагрузка-по-бездействию)
19. [Конфигурация](#19-конфигурация)
20. [OTA обновление](#20-ota-обновление)
21. [Веб-сервер](#21-веб-сервер)
22. [Система логирования](#22-система-логирования)
23. [Мьютексы](#23-мьютексы-и-критические-секции)
- [Приложение A: Значения по умолчанию](#приложение-a-значения-по-умолчанию)
- [Приложение Б: Диаграмма состояний](#приложение-б-диаграмма-состояний)
- [Приложение В: Глоссарий](#приложение-в-глоссарий)


---

## 1. Общая информация

#### ⚙️ Ключевые возможности

- Поддержание заданной температуры в камере
- Два независимых датчика температуры:
  - MAX6675 (термопара)
  - DS18B20 (воздух)
- ШИМ-управление вентилятором с автоограничением мощности
- Обучаемая термальная модель:
  - прогноз нагрева
  - прогноз охлаждения
  - раннее обнаружение аномалий
- Многоуровневая защита:
  - перегрев
  - thermal runaway
  - неожиданный нагрев
- Аппаратный watchdog (ESP-01S) для отключения 220В
- Адаптивная самонастройка под камеру и вентиляцию
- Web-интерфейс (SPA) с real-time графиком
- WebSocket + HTTP REST API
- OTA обновление прошивки
- Обнаружение Klipper / Moonraker (UDP)
- LED-индикация состояний
- Звуковая сигнализация ошибок

#### 🎯 Целевая платформа

- ESP32 (рекомендуется ESP-32D DevKit C V4)
- Flash: минимум 4MB

#### Зависимости (библиотеки)

| Библиотека | Автор | Назначение |
|------------|-------|------------|
| [Adafruit NeoPixel](https://github.com/adafruit/Adafruit_NeoPixel) | Adafruit | LED лента WS2812B |
| [OneWire](https://www.pjrc.com/teensy/td_libs_OneWire.html) | Jim Studt, Tom Polland, Robin James | Шина для DS18B20 |
| [DallasTemperature](https://github.com/milesburton/Arduino-Temperature-Control-Library) | Miles Burton | Датчик DS18B20 |
| [ArduinoJson](https://arduinojson.org/) | Benoit Blanchon | Парсинг JSON |
| [ESPAsyncWebServer](https://github.com/ESP32Async/ESPAsyncWebServer) | ESP32Async | Веб-сервер |
| [AsyncTCP](https://github.com/ESP32Async/AsyncTCP) | ESP32Async | Асинхронный TCP |

#### Файловая структура

```
firmware/flook32/
├── flook32.ino                         // ВСЯ прошивка (~10000+ строк)
├── index_html_gz.h                     // Сжатый gzip веб-интерфейса
├── favicon_ico.h                       // Иконка для вкладок браузера (48×48)
├── icon_192_png_gz.h                   // Иконка для домашнего экрана смартфонов (192×192)
├── chart_min_js_gz.h                   // Сжатая gzip библиотека Chart.js
├── chartjs_adapter_gz.h                // Сжатый gzip адаптер date-fns для Chart.js
├── compress_webui.bat                  // Скрипт сборки (Windows)
├── compress_webui.sh                   // Скрипт сборки (Linux/macOS)
└── src/                                // Исходники веб-ресурсов
    ├── index.html                      // Исходный HTML
    ├── favicon.ico                     // Исходная иконка браузера
    └── icon_192.png                    // Исходная иконка для смартфонов
```

---

## 2. Аппаратная часть

#### Таблица GPIO пинов

| Пин     | Назначение           | Направление | Подтяжка                 | Примечание |
|---------|----------------------|-------------|--------------------------|------------|
| GPIO32  | SSR нагреватель      | OUTPUT      | —                        | HIGH = вкл (если не инвертирован) |
| GPIO33  | Вентилятор PWM       | OUTPUT      | —                        | 0–1023, частота 17 kHz |
| GPIO26  | Watchdog heartbeat   | OUTPUT      | —                        | Импульс на ESP-01S |
| GPIO21  | DS18B20 (1-Wire)     | INPUT       | Встроена в модуль 4.7k   | — |
| GPIO18  | MAX6675 SCK          | OUTPUT      | —                        | SPI |
| GPIO19  | MAX6675 SO (MISO)    | INPUT       | —                        | SPI |
| GPIO5   | MAX6675 CS           | OUTPUT      | —                        | SPI (Chip Select) |
| GPIO25  | Бипер                | OUTPUT      | —                        | Активный/пассивный |
| GPIO27  | LED лента WS2812B    | OUTPUT      | —                        | NeoPixel data |
| GPIO17  | Кнопка сброса        | INPUT       | INPUT_PULLUP             | Удержание 5 сек = сброс к заводским |


#### Особенности работы модуля MAX6675 (термопара K-типа)

- Разрешение: 0.25°C
- Диапазон: 0–1024°C
- Обновление: ~70 мс на чтение

---

#### Особенности работы модуля DS18B20 (датчик воздуха)

- Интерфейс 1-Wire
- Диапазон: -55 до +125°C
- Обновление: 200 мс (9 бит)

#### Особенности работы модуля SSR (твердотельное реле)

- Инверсия сигнала настраивается в конфиге (LOW/HIGH)

#### Особенности работы MOSFET модуля (PWM)

- Частота ШИМ: 17 kHz (неслышимый диапазон)
- Разрешение: 0–1023 (10 бит)
- Нелинейная зависимость мощности
- Сырой duty для регулировки

#### Особенности работы LED (WS2812B)

- Количество светодиодов настраивается (1–100)

#### Особенности работы бипера

- Активный бипер: управление HIGH/LOW

#### Принцип работы внешнего watchdog (ESP-01S)

- ESP32 отправляет импульс каждые (pulseMs + pauseMs) мс
- ESP-01S мониторит GPIO2
- Если импульсы пропали > 6 секунд → реле размыкается → 220V отключается
- Это аппаратная защита, не зависит от софта основной ESP32

---

## 3. Структура прошивки (setup + loop)

### 3.1 setup() — полная последовательность

```
1. Serial.begin(115200)
   └─ Вывод версии, причины перезагрузки
   └─ Логирование причины перезагрузки в журнал ошибок:
       ├─ Аварийные причины (пан́ика, watchdog, brownout) → addErrorToLog()
       └─ Штатные (включение питания, софт-ресет) → не логируются
   └─ Проверка свободного места в NVS (nvs_get_stats)
       └─ Если свободно <10% → предупреждение в журнал ошибок

2. Preferences (NVS)
   └─ Генерация/загрузка уникального device_id
   └─ Проверка целостности конфига (размер sizeof(Config))

3. loadConfig()
   └─ Загрузка из Preferences (NVS)
   └─ loadDutyTable()
   └─ Валидация (config.validate())

4. Инициализация пинов
   └─ pinMode для SSR, Watchdog, 1-Wire, MAX6675 (SCK/SO/CS), бипер, LED

5. Инициализация периферии
   ├─ initFanPWM() — настройка ШИМ
   ├─ initButton() — кнопка на GPIO17 (INPUT_PULLUP)
   ├─ OneWire + DallasTemperature
   ├─ digitalWrite SSR = инвертированный LOW
   ├─ digitalWrite Watchdog = HIGH
   └─ digitalWrite Buzzer = LOW

6. Система ошибок
   └─ errors.loadLockState() — восстановление блокировки

7. Датчики
   ├─ DS18B20
   │   ├─ begin()
   │   ├─ setResolution(9 бит)
   │   ├─ setWaitForConversion(false)
   │   ├─ Проверка наличия устройств
   │   └─ Пробное чтение (задержка 1 сек)
   └─ MAX6675
       └─ initMAX6675() — проверка доступности

8. Термальная модель
   └─ initThermalModel()
       └─ Если enableThermalModel → updateProtectionsForThermalModel()

9. Wi-Fi
   ├─ Если есть сохранённые учётные данные:
   │   ├─ WiFi.mode(WIFI_STA)
   │   ├─ WiFi.begin(ssid, password)
   │   └─ 20 попыток по 500 мс = 10 сек таймаут
   │       ├─ Успех → wifiConnected = true
   │       └─ Неудача → сброс учётных данных, переход в AP
   └─ AP режим:
       ├─ SSID = "FLOOK32-" + MAC (последние 4 байта)
       ├─ Пароль = "flook1234"
       └─ IP = 192.168.4.1

10. UDP
    └─ udp.begin(UDP_PORT)
    └─ Для Klipper/Moonraker обнаружения

11. WebSocket + HTTP сервер
    ├─ CORS заголовки
    ├─ ws.onEvent(onWebSocketEvent)
    ├─ favicon.ico (из PROGMEM, gzip)
    ├─ / → index.html (чанкированный gzip из PROGMEM)
    ├─ ETag кэширование ("v1")
    ├─ API маршруты (30+ эндпоинтов)
    ├─ /api/duty-table (GET + add)
    ├─ /api/device-id
    ├─ /api/thermal-status
    ├─ /api/config POST (полный парсинг JSON + валидация + saveConfig)
    ├─ /api/update OTA (запись во flash + перезагрузка)
    └─ 404 обработчик

12. FreeRTOS задачи
    ├─ SensorTask: ядро 1, приоритет 8, стек 4KB
    ├─ ControlTask: ядро 1, приоритет 10, стек 12KB (основной цикл управления)
    ├─ WebTask: ядро 0, приоритет 7, стек 16KB (метрики, WebSocket, история)
    ├─ HeartbeatTask: ядро 1, приоритет 5, стек 1KB (импульс watchdog)
    └─ LEDTask: ядро 0, приоритет 2, стек 2KB (индикация)

13. Watchdog
    └─ esp_task_wdt_add(controlTaskHandle)
    └─ Таймаут = config.loopWatchdogTimeout

14. Финальные действия
    ├─ Проверка флага автоперезагрузки (Preferences)
    ├─ Мелодия запуска (если не системная блокировка)
    └─ resetActivityTimer() — таймер бездействия
```
### 3.2 loop()

```
loop() — `vTaskDelay(portMAX_DELAY)`
Бесконечное ожидание — вся логика выполняется в задачах FreeRTOS.
После завершения инициализации:
setup()
│
└── vTaskDelete(NULL)
```

Основная причина:
- Параллельное выполнение:
  - контроль температуры
  - WebSocket
  - защита
  - PWM
  - watchdog
  - адаптация

### 3.3 Приоритеты FreeRTOS задач

| Задача        | Ядро | Приоритет | Стек  | Назначение |
|---------------|------|-----------|-------|------------|
| SensorTask    | 1    | 8         | 4KB   | Чтение датчиков |
| ControlTask   | 1    | 10        | 12KB  | Управление нагревом, защиты, адаптация |
| WebTask       | 0    | 9         | 16KB  | WebSocket, HTTP, метрики, история |
| HeartbeatTask | 1    | 5         | 1KB   | Импульс на watchdog |
| LEDTask       | 0    | 2         | 2KB   | LED индикация |

### 3.4 Конфигурация (Preferences / NVS)

Хранение: Preferences (NVS — Non-Volatile Storage)

Пространства имён:

| Namespace | Назначение |
|-----------|------------|
| `"flook"` | Конфиг, Wi-Fi, lastTarget, статус блокировки |
| `"dutyTable"` | Таблица T_возд → duty вентилятора |
| `"thermal"` | Коэффициенты термальной модели |

#### Ключи:

- "device_id" — уникальный идентификатор устройства  
- "device_id_created" — время создания  
- "config" — сериализованная структура Config (с проверкой sizeof)  
- PREF_AUTO_REBOOT_FLAG — флаг автоперезагрузки

### 3.5 HTTP сервер

Библиотека: ESPAsyncWebServer

Порт: 80

CORS: разрешены все источники

Сжатие: gzip для index.html (из PROGMEM)

Кэширование: ETag "v1", Cache-Control: max-age=3600

---

## 4. Датчики

### 4.1 MAX6675 (термопара K-типа)

Интерфейс: программный SPI

- SCK = config.pinMaxSck (GPIO18)
- SO  = config.pinMaxSo (GPIO19)
- CS  = config.pinMaxCs (GPIO5)

#### Алгоритм чтения (readMAX6675)

```
- Чтение 16 бит через SPI (битовый сдвиг)
- Проверка служебных битов MAX6675:
  - D2 = 0 → нормальное значение
  - D1 = fault (обрыв термопары)
- Извлечение температуры:
  - `(value >> 3) * 0.25°C`
- Проверка валидности значения:
  - диапазон `minTemp..maxTemp`
- Фильтрация скачков:
  - если `|T - T_prev| > config.max6675TempJumpThreshold` → игнор / ошибка
- Усреднение:
  - `config.max6675StabilitySamples` (скользящее окно)
```
#### Защита MAX6675

- Проверка диапазона: `minTemp..maxTemp`
- Проверка скачков: порог `config.max6675TempJumpThreshold`
- Сэмплы стабильности: `config.max6675StabilitySamples`
- При выходе за диапазон или скачке → ошибка `max6675Error`

#### Частота опроса

- Выполняется в `SensorTask`
- Интервал: `config.readInterval` (по умолчанию 1000 мс)

### 4.2 DS18B20 (датчик воздуха)

**Интерфейс:** 1-Wire (библиотеки OneWire + DallasTemperature)

DATA = config.pinOneWire (GPIO21)

**Разрешение:** 9 бит (0.5°C)  
**Установка:** `ds18b20->setResolution(9)`  

**Обоснование:** минимальная задержка конвертации (~94 мс)

**Метод опроса:** асинхронный — `requestTemperatures()` → `vTaskDelay(100ms)` → `getTempCByIndex(0)`

#### Алгоритм чтения (readDS18B20Temperature)

```
1. ds18b20->requestTemperatures()
2. Ожидание: while (!ds18b20->isConversionComplete()) delay(10)
3. tempC = ds18b20->getTempCByIndex(0)
4. Проверка на DEVICE_DISCONNECTED_C (-127°C)
   └─ Если да → возврат DEVICE_DISCONNECTED_C, ds18b20Error = true
5. Применение калибровки:
   └─ Если config.ds18b20CalEnabled:
       result = tempC * config.ds18b20Scale + config.ds18b20Offset
   └─ Иначе: result = tempC
6. Сохранение ds18b20LastValidTemp
```
#### Защита DS18B20

- Проверка диапазона: `minTemp..maxTemp`
- Проверка скачков: порог `config.airSensorTempJumpThreshold`

#### Анализ нестабильности

- Окно анализа: `config.airSensorUnstableWindow` отсчётов  
- Допустимый размах: `config.airSensorUnstableRange`  
- Допустимое отклонение: `config.airSensorUnstableDeviation`  
- Допустимые смены направления: `config.airSensorDirectionChanges`  
- Сэмплы стабильности: `config.airSensorStabilitySamples`

#### Частота опроса

- Выполняется в `SensorTask`  
- Интервал: `config.readInterval`

---

## 5. Управление SSR (нагреватель)

### 5.1 Принцип работы

Дискретный выход (HIGH/LOW) с программным гистерезисом.

Пин: `config.pinSsr` (GPIO32 по умолчанию)

Инверсия: `config.invertHeaterSignal`

- false → HIGH = вкл, LOW = выкл  
- true → LOW = вкл, HIGH = выкл  

### 5.2 Два режима управления

#### Режим 1: По воздуху (`enableHeaterHysteresis = false`)

```
ВКЛ:  airTemp ≤ targetTemp - hysteresis
ВЫКЛ: airTemp ≥ targetTemp + hysteresis
```
#### Режим 2: По воздуху и нагревателю (`enableHeaterHysteresis = true`)

```
ВКЛ:  airTemp ≤ targetTemp - hysteresis
      И heaterTemp < maxHeaterTemp - heaterHysteresis
ВЫКЛ: heaterTemp ≥ maxHeaterTemp + heaterHysteresis
      ИЛИ airTemp ≥ targetTemp + hysteresis
```

### 5.3 Принудительное отключение

Нагреватель выключается при:

- `targetTemp == 0`
- Критической ошибке (`errors.hasCriticalError()`)
- `runawayTriggered == true`
- `criticalOverheatLock == true`
- `airOverheatLock == true`
- `errors.unexpectedHeat == true`
- `errors.isSystemLocked() == true`
- `heaterTemp >= config.criticalTemp`
- `airTemp >= config.maxAirTemp`
- Завершении печати по Moonraker (`shouldShutdownByPrintStatus()`)
- Срабатывании ручного таймера

### 5.4 Частота управления

Выполняется в `ControlTask`

Интервал: `config.heaterControlInterval` (по умолчанию 50 мс = 20 Гц)

---

## 6. Управление вентилятором (PWM)

### 6.1 Аппаратный ШИМ

Периферия: LEDC (LED Control)  
Пин: `config.pinFan` (GPIO33 по умолчанию)  
Частота: 17 кГц (неслышимый диапазон)  
Разрешение: 10 бит (0–1023)

```
ledc_timer_config_t ledc_timer = {
    .speed_mode = LEDC_LOW_SPEED_MODE,
    .duty_resolution = LEDC_TIMER_10_BIT,
    .timer_num = LEDC_TIMER_0,
    .freq_hz = DEFAULT_FAN_PWM_FREQ,  // 17000
    .clk_cfg = LEDC_AUTO_CLK
};
```
### 6.2 Логика включения/выключения

```
ВКЛ:  heaterTemp ≥ fanOnTemp (по умолчанию 55°C)
ВЫКЛ: heaterTemp ≤ fanOnTemp - fanOffHysteresis
      И отработал fanMinOnTime (мин. время работы, по умолчанию 30 сек)
```
### 6.3 Режимы управления мощностью

#### Без автоограничения (`enableFanAutoLimit = false`)

Вентилятор всегда работает на `maxFanDuty` при включении.

#### С автоограничением (`enableFanAutoLimit = true`)

После достижения `heaterTemp ≈ maxHeaterTemp` мощность динамически корректируется:

```
Если heaterTemp > maxHeaterTemp + fanAutoLimitHysteresis:
    duty += fanAutoLimitAdjustStep (увеличиваем охлаждение)
Если heaterTemp < maxHeaterTemp - fanAutoLimitHysteresis:
    duty -= fanAutoLimitAdjustStep (уменьшаем охлаждение)

Ограничения:
    duty = constrain(duty, fanAutoLimitMinDuty, 1023)
```
### 6.4 Стартовая мощность по таблице

При включении вентилятора используется `getStartupDutyByAirTemp(airTemp)` — линейная интерполяция по таблице `dutyTable`, заполненной при адаптации.


### 6.5 Аварийный режим (100%)

При критических ошибках вентилятор форсируется на 100% через updateFan() по флагам в isCriticalErrorActive(). После снятия ошибки restoreFanNormalMode() выключает вентилятор и сбрасывает флаги форсирования. Дальнейшее управление передаётся updateFan(), который сам решит, нужно ли включать вентилятор по текущей температуре.


### 6.6 Частота управления

Выполняется в `ControlTask`

Интервал: `config.fanControlInterval` (по умолчанию 1000 мс)

---

## 7. Система защит

### 7.1 Общая архитектура

Все защиты работают в `ControlTask` независимо друг от друга. Приоритеты:

| Приоритет | Защита | Последствия |
|----------|--------|-------------|
| 1 (высший) | Система заблокирована | Всё отключено, требуется пароль |
| 2 | Критический перегрев нагревателя | SSR выкл, вентилятор 100% |
| 3 | Перегрев воздуха | SSR выкл, вентилятор 100% |
| 4 | Thermal Runaway | SSR выкл, опционально вентилятор |
| 5 | Неожиданный нагрев | SSR выкл, вентилятор 100% |
| 6 | Неэффективность вентилятора | Только предупреждение |
| 7 | Аномальный рост | Только предупреждение |


#### Трёхступенчатая эскалация

- Однократное срабатывание → остановка нагрева  
- Повторение в пределах `errorWindowMinutes` → счётчик++  
- Счётчик ≥ `maxErrorRetries` (3) → полная блокировка системы (требуется пароль)

### 7.2 Критический перегрев нагревателя

Функция: `checkHeaterOverheat()`  
Интервал: `config.controlInterval` (1000 мс)

#### Условие

```
heaterTemp > config.criticalTemp (по умолчанию 120°C)
```
#### Действия

- `errors.criticalOverheatCount++`
- `criticalOverheatLock = true`
- `errors.criticalOverheat = true`
- Выключение SSR

#### Сброс состояния

```
heaterTemp < criticalTemp - criticalHysteresis (120 - 5 = 115°C)
```
#### Блокировка системы

При:

```
criticalOverheatCount ≥ maxErrorRetries → `errors.lockSystem()`
```
### 7.3 Перегрев воздуха

Функция: `checkAirOverheat()`  
Интервал: `config.controlInterval` (1000 мс)

#### Условие

```
airTemp > config.maxAirTemp (по умолчанию 70°C)
```
#### Действия

- `errors.airOverheatCount++`
- `airOverheatLock = true`
- Выключение SSR

#### Сброс состояния

```
airTemp < maxAirTemp - airHysteresis (70 - 3 = 67°C)
```

### 7.4 Thermal Runaway (четырёхфазный контроль)

Функция: `checkThermalRunaway()`  
Интервал: `config.runawayCheckInterval` (5000 мс)

#### Условие запуска

```
targetTemp > 0 И heaterState == true И heaterTemp < targetTemp
```

#### Фаза 0 (первые 45 секунд)

```
Контроль: быстрая проверка нагревателя
Условие: heaterTemp < runawayQuickCheckTemp через 45 сек после включения
Действие: alarm — датчик отвалился от радиатора или нагреватель неисправен
```

#### Фаза 1 (0 – phase1Time минут)

```
Контроль: скорость нагрева НАГРЕВАТЕЛЯ
Условие: heaterTemp - startHeaterTemp < runawayMinHeaterRisePerMin × elapsedMin
Действие: alarm
```

#### Фаза 2 (phase1Time – phase2Time минут)

```
Контроль: скорость нагрева ВОЗДУХА
Условие: airTemp - startAirTemp < runawayMinAirRisePerMin × (elapsedMin - phase1Time)
Действие: alarm
```

#### Фаза 3 (> phase2Time минут)

```
Контроль: прогноз времени до цели
Условие: (targetTemp - airTemp) / currentRate > runawayMaxTimeToTarget
Действие: alarm
```

#### При срабатывании

- `errors.thermalRunawayCount++`
- `errors.thermalRunaway = true`
- `runawayTriggered = true`
- Выключение SSR
- Автосброс: через `runawayRecoveryTimeout` секунд

### 7.5 Неожиданный нагрев (Unexpected Heat)

Функция: `checkUnexpectedHeat()`  
Интервал: `config.unexpectedCheckInterval` (2000 мс)

#### Условие

```
!heaterState И fanState И heaterTemp > порог
```

---

#### Адаптивный порог

```
Базовый: maxHeaterTemp - unexpectedHeatThreshold
Адаптивный (если включён):
    порог = базовый - (airTemp - adaptiveBaseTemp) × adaptiveCoefficient
    ограничен: [maxHeaterTemp - adaptiveMinOffset, базовый]
```

#### Действия

- Ожидание `unexpectedHeatTimeout` секунд  
- Если `heaterTemp` не упала ниже ожидаемой → alarm  
- `errors.unexpectedHeatCount++`  


#### Сброс

```
heaterTemp < порог - unexpectedHeatHysteresis
```
### 7.6 Контроль эффективности вентилятора

Функция: `checkFanEfficiency()`  
Интервал: в составе `timerProtections` (1000 мс)

#### Условие

```
!heaterState И fanState И heaterTemp > maxAirTemp - 10
```

#### Проверка

Через `fanEfficiencyTimeout` секунд:

- падение температуры < `fanEfficiencyThreshold`

#### Действие

- Только предупреждение (не блокирует систему)

### 7.7 Контроль аномального роста

Функция: `checkHeatingRate()`  
Интервал: `config.rateCheckInterval` (1000 мс)

#### Условие

```
heaterState И скорость роста > abnormalRateThreshold (5°C/сек)
```
#### Действие

- Предупреждение в лог

### 7.8 Контроль датчика воздуха

Функция: `checkAirSensor()`  
Интервал: в составе `timerProtections` (1000 мс)

#### Анализ

- размах значений  
- отклонение  
- смены направления за `airSensorUnstableWindow` отсчётов  

#### При нестабильности

- `errors.airSensorUnstable = true`  
- предупреждение

---

## 8. Термальная модель (машинное обучение)

### 8.1 Принцип работы

Модель предсказывает температуру нагревателя на основе:

- текущей температуры  
- мощности нагревателя (0 или 1, релейное управление)  
- измеренной при адаптации скорости нагрева (`heaterRate`, °C/мин)

---

#### Формула предсказания

```
T_pred = T_current + (heaterRate / 60) × Δt × power × correction
```

---

#### Коррекция (correction)

Снижение скорости при приближении к целевой температуре:

- если разница < 10°C:

```
correction = разница / 10
```
- минимум:

```
correction = 0.3 (30% от номинальной скорости)
```

### 8.2 Обучение в реальном времени

Вызывается: `checkThermalModel()` каждые `thermalModelCheckInterval` (2000 мс)

---

#### Алгоритм

- Сравнивается предыдущее предсказание с реальной температурой  
- Вычисляется ошибка:

```
error = T_real - T_pred
```
- Если:

```
|error| > noiseFloor × 2
```
#### Обновление модели

- `heaterRate += error × 0.001` (градиентный шаг)
- `heaterRate = constrain(heaterRate, 1.0, 30.0)`
- Обновляется `noiseFloor` (экспоненциальное сглаживание)
- Корректируется `confidence` (растёт при стабильно малых ошибках)

#### Особенности

- Обучается только при активном нагреве (`heaterState == true`)
- `coolingRate` не обновляется онлайн (задаётся при адаптации)
- Автосохранение в Preferences раз в час

### 8.3 Обнаружение аномалий

Скользящее окно: 5 последних ошибок за 10 секунд

#### Пороги

**Предупреждение:**

```
avgError > noiseFloor × 3 × sensitivity
```
**Критическое:**

```
avgError > порог × 2.5
```
#### При критическом отклонении

- Выключение SSR  
- Запись в лог ошибок

### 8.4 Сохранение и загрузка

Хранение: Preferences, namespace "thermal"

#### Ключи

- `heaterRate`
- `coolingRate`
- `noiseFloor`
- `confidence`
- `samples`

#### Автосохранение

- раз в час  
- при каждом значимом обновлении  

#### Загрузка

- при старте, если модель включена  
- если данных нет — инициализация из адаптации

### 8.5 Влияние на другие защиты

При активной термальной модели (`protectionOverride.thermalModelActive = true`):

| Защита | Изменение |
|--------|----------|
| Thermal Runaway | Пороги смягчаются в 2 раза (модель обнаруживает аномалии раньше) |
| Unexpected Heat | Отключается |
| Контроль скорости воздуха | Включается дополнительная проверка `checkAirHeatingRate()` |

---

## 9. Адаптация (самонастройка)

### 9.1 Цель

Измерить тепловые характеристики конкретного принтера и рассчитать оптимальные пороги защит без ручного подбора.  
Занимает 15–40 минут.

### 9.2 Условия запуска

- Система не заблокирована  
- Датчики исправны  
- Температуры выровнены (разница < 4°C)  
- Обе температуры < 35°C  
- Целевая температура: 40–70°C  

### 9.3 Фазы

#### Фаза 0: Ожидание стабилизации

- Всё выключено  
- Ожидание выравнивания `T_нагр ≈ T_возд` (разница < 4°C)  
- Требование: обе температуры < 35°C и > 5°C  
- Проверка стабильности: 3 замера подряд с изменением < 0.5°C  

#### Фаза 1: Измерение шумов датчиков

- 30 секунд сбора показаний в покое  
- Расчёт σ (среднеквадратичного отклонения) для MAX6675 и DS18B20  

Результат:
- `heaterSensorNoiseLevel`
- `airSensorNoiseLevel`

#### Фаза 2: Измерение базовых параметров

- 10 секунд замера максимальных межвыборочных скачков  

Результат:
- `heaterSensorMaxJump`
- `airSensorMaxJump`

#### Фаза 3: Калибровка вентилятора (если `enableFanAutoLimit`)

- Поиск оптимальной мощности:
  - снижение `duty` от 1023 до минимального, удерживающего `maxHeaterTemp`  
- Результат:
  - `optimalPower`
  - `calibratedMinDuty`

- Поиск температуры включения:
  - тестирование порогов от 30°C с шагом 5°C  
- Результат:
  - `fanOnTemp`
  - `fanOffHysteresis`

#### Фаза 4: Нагрев с вентилятором

- Охлаждение до 35°C  
- Включение нагрева с вентилятором  

Измерение:
- средней скорости нагрева нагревателя  
- пиковой мгновенной скорости  
- скорости за первые 30 секунд  

- ожидание стабилизации (4°C допуск, 5 секунд)

#### Фаза 5: Ожидание пользователя

Таймаут: 30 минут  

Пользователь должен:
- опустить стол в нижнее положение  
- включить нагрев стола на 100–110°C  
- закрыть камеру  
- нажать «Продолжить» в веб-интерфейсе  

#### Фаза 6: Нагрев камеры

Самая длительная фаза

- нагрев воздуха до `adaptTargetTemp` (или таймаут 30 минут)

Измерение:
- `maxAirHeatingRate` — макс. скорость нагрева воздуха  
- `heatingRateAir` — средняя скорость  
- `timeToReachTarget` — время до цели  

Калибровка параметров автоограничения:
- перебор комбинаций: шаг × интервал × гистерезис × стабильность  
- выбор лучшей по минимальному размаху температуры  
- заполнение таблицы `duty (T_возд → мощность)`

После достижения цели:
- замер скорости охлаждения  

#### Фаза 7: Завершение

- расчёт и сохранение всех параметров  
- `finishAdaptation(true)`

#### Фаза 8: Ошибка

- завершение с `finishAdaptation(false)`

### 9.4 Применение результатов

#### Формулы расчёта порогов

| Параметр | Формула |
|----------|--------|
| runawayMinHeaterRisePerMin | heatingRateHeater × 0.4 |
| runawayMinAirRisePerMin | heatingRateAir × 0.4 |
| runawayMaxTimeToTarget | timeToTarget × 2.5 |
| max6675TempJumpThreshold | maxHeatingRate × 2.0 |
| abnormalRateThreshold | maxHeatingRate × 1.5 |
| hysteresis | airSensorNoiseLevel × 2 |
| minCoolingRate | coolingRate × 0.15 |

#### Сохранение

- `config.adaptationPerformed = true`
- `saveConfig()`

### 9.5 Прерывание

Кнопка «Прервать» в веб-интерфейсе

```
abortAdaptation()
```
Действия:
- выключение нагрева  
- сброс флагов

---

## 10. Система ошибок и журналирования

### 10.1 Структура Errors

Централизованная структура `errors` управляет всеми ошибками системы.

### Флаги ошибок

**Критические:**
- `criticalOverheat`
- `airOverheat`
- `thermalRunaway`
- `unexpectedHeat`

**Датчик нагревателя:**
- `max6675Disconnected`
- `max6675Noise`
- `max6675OutOfRange`
- `max6675Unstable`
- `max6675Stuck`

**Датчик воздуха:**
- `ds18b20Disconnected`
- `airSensorNoise`
- `airSensorOutOfRange`
- `airSensorUnstable`

**Системные:**
- `emergencyStop`
- `systemLocked`

#### Дополнительно

- флаги логирования (для предотвращения дублирования записей)
- счётчики повторов для каждого типа ошибки
- временные метки последних срабатываний

### 10.2 Блокировка системы

#### Условие

```
счётчик ошибок ≥ maxErrorRetries (3)
в пределах errorWindowMinutes (10 минут)
```
#### Действия

- `errors.lockSystem(reason, errorType)`
- сохранение в Preferences:
  - `systemLocked`
  - `lockReason`
  - `lockTime`
- выключение нагрева
- требуется пароль для разблокировки

#### Разблокировка

```
POST /api/unlock?password=XXX
```
#### После разблокировки

- сброс всех счётчиков  
- удаление сохранённого состояния блокировки  
- `errors.unlockSystem()`

### 10.3 Восстановление после ошибок

- Автосброс Thermal Runaway: через `runawayRecoveryTimeout` секунд  
- Автосброс Unexpected Heat: при охлаждении до безопасной температуры + `unexpectedHeatClearTime`  
- Автовосстановление MAX6675: при `max6675StabilitySamples` стабильных чтений подряд  

#### Проверка автоочистки

```
errors.checkAutoClear()
```

- вызывается каждые 5 секунд в WebTask

### 10.4 Журнал ошибок

Хранение: `std::vector<ErrorLogEntry>`  
Максимум: 20 записей (FIFO)

#### Структура записи

| Поле | Тип | Описание |
|------|-----|----------|
| timestamp | uint32_t | время от запуска (мс) |
| message | string | текст ошибки |
| severity | string | critical / warning / info |
| trendData | snapshot | только для критических |
| errorCount | int | счётчик повторений |
| hash | uint32_t | DJB2-хеш сообщения |

#### Дедупликация

- одинаковые некритические ошибки: не чаще `minTimeBetweenSameErrors` (30 сек)
- уведомления: не чаще 30 секунд

#### Потокобезопасность

- `errorLogMux (portMUX)` при доступе из разных задач

### 10.5 Уведомления

Функция:
`addNotificationToLog(message)`

- только некритичные события  
- severity = `info`  
- без трендов  
- без звукового сигнала  

### 10.6 Очистка при низкой памяти

При:

```
freeHeap < 20KB или maxBlock < 20KB
```
Действия:

- журнал сокращается до 10 записей  
- кэш конфигурации сбрасывается  

---

## 11. История для графика (Trends)

### 11.1 Структура записи

Формат: `CompactTrendEntry` — 16 байт на точку

| Поле | Тип | Описание |
|------|-----|----------|
| timestamp | uint32_t | время от запуска (мс) |
| airTemp | int16_t | T_воздух × 10 |
| heaterTemp | int16_t | T_нагревателя × 10 |
| targetTemp | int16_t | цель × 10 |
| predictedTemp | int16_t | модель × 10 |
| flags | uint8_t | SSR / вентилятор |

### 11.2 Кольцевой буфер

- размер: `TREND_BUFFER_SIZE = 600`
- память: 600 × 16 = 9600 байт (статическая)
- глубина: ~30 минут при `trendInterval = 3000 мс`

#### Индексация

- `trendIndex` — следующая ячейка
- `trendBufferFilled` — флаг полного заполнения

#### Потокобезопасность

- `trendBufferMux (portMUX)`

### 11.3 Запись

Функция:

```
addToTrendBuffer()
```
- интервал: `config.trendInterval` (3000 мс)
- выполняется в WebTask
- при активной модели добавляется `predictedTemp`

### 11.4 Отправка клиентам

- при подключении: `sendHistoryToClient()` (чанки по 60 точек)
- в реальном времени: WebSocket `history_update`
- по запросу:

```
sendUpdatesSince(timestamp)
```
→ только новые точки

---

## 12. LED индикация (NeoPixel WS2812B)

### 12.1 Аппаратная часть

Библиотека: Adafruit NeoPixel  
Пин: `config.pinLed` (GPIO27 по умолчанию)  
Количество: `config.ledCount` (1–100, по умолчанию 3)  
Яркость: `config.ledBrightness` (0–255, по умолчанию 50)  
Полное отключение: `config.ledEnabled = false`

Задача: `LEDTask`, ядро 0, приоритет 2, интервал 50 мс (20 Гц)

### 12.2 Режимы индикации

| Индекс | Режим | Цвет | Анимация | Условие |
|--------|-------|------|----------|---------|
| 0 | Выкл | — | — | LED отключены |
| 1 | Ожидание | Синий `{0, 80, 255}` | Дыхание (простая синусоида, 4 сек) | `targetTemp == 0` |
| 2 | Первый нагрев | Белый `{255, 255, 255}` | Прогресс-бар с градиентом яркости | `targetTemp > 0 && heaterState && !targetWasReached` |
| 3 | Поддержание | Зелёный `{0, 255, 80}` | Прогресс-бар с градиентом яркости | `targetWasReached == true` |
| 4 | Адаптация | Фиолетовый `{160, 0, 255}` | Прогресс-бар с градиентом яркости | `adaptationInProgress` |
| 5 | Ошибка | Красный `{255, 0, 0}` | Ровное мигание (300 мс) | Любая критическая ошибка или блокировка |

### 12.3 Приоритеты

Режимы выбираются по порядку (первый подходящий — побеждает):

1. Ошибка / блокировка системы
2. Адаптация
3. Первый нагрев до цели (белый)
4. Поддержание температуры (зелёный)
5. Ожидание (синий)

Особые случаи (выполняются до проверки приоритетов):
- **Удержание кнопки сброса** — оранжевый прогресс-бар, LED-индикация приостанавливается
- **Режим точки доступа Wi-Fi** — бегущий огонёк
- **Подключение к Wi-Fi** — зелёно-голубая волна (3 сек + затухание 0.5 сек)

### 12.4 Логика перехода белый → зелёный

```
Установка targetTemp > 0:
  targetWasReached = false
  └─ Белый прогресс-бар (первый нагрев)

Достижение цели:
  airTemp >= targetTemp - hysteresis
  └─ targetWasReached = true
  └─ Зелёный прогресс-бар (поддержание)

Сброс цели:
  targetTemp = 0
  └─ targetWasReached = false
  └─ Следующий нагрев снова белый
```

### 12.5 Зелёный прогресс-бар (поддержание)

Отображает положение температуры воздуха внутри диапазона `[targetTemp - hysteresis, targetTemp]`:

```
Прогресс = (airTemp - (targetTemp - hysteresis)) / hysteresis × 100%

Пример (цель 60°C, гистерезис 0.5°C):
  60.0°C → 100% (все LED горят)
  59.8°C → 60%  (3 из 5 LED)
  59.5°C → 0%   (все погасли, включается нагрев)
  59.5°C → нагрев вкл → прогресс растёт → 60.0°C → нагрев выкл → цикл повторяется
```

Полоска «дышит» в такт циклам нагрева: убывает при остывании, растёт при нагреве.

### 12.6 Типы анимаций

| Тип | Описание |
|-----|----------|
| `LED_BREATH` | Простая синусоида яркости 15-100%. Период задаётся параметром |
| `LED_BLINK` | Ровное мигание вкл/выкл с заданным интервалом |
| `LED_PROGRESS` | Заполнение слева направо. Заполненная часть: градиент яркости от тусклого к яркому. Пустая часть: фон 10% яркости. Прогресс сглаживается с инерцией |
| `LED_RUNNING` | Одна яркая точка + затухающий хвост из 3 LED (1 → 0.5 → 0.33 → 0.25). Скорость задаётся параметром |

### 12.7 Особые режимы

#### Режим точки доступа (AP mode)
- Нет клиентов → оранжевый `{255, 150, 0}` бегущий огонёк, медленно (200 мс)
- Есть клиенты → зелёный `{0, 255, 100}` бегущий огонёк, быстро (80 мс)

#### Подключение к Wi-Fi (STA mode)
- Фаза 1 (3 сек): зелёно-голубая волна с гауссовым профилем, цвет плавно переходит зелёный → голубой
- Фаза 2 (0.5 сек): плавное затухание всех LED

#### Кнопка сброса (GPIO17)
При удержании кнопки LED-индикация приостанавливается. Отображается оранжевый прогресс-бар заполнения (5 сек до сброса). При достижении 5 секунд — тройная вспышка белым, сброс настроек, перезагрузка.

### 12.8 Плавные переходы

При смене режима цвет интерполируется в течение 400 мс через EaseInOutCubic: `currRGB → targetRGB`. Это создаёт эффект плавного «переливания» цвета.

---

## 13. Звуковая индикация (зуммер)

### 13.1 Аппаратная часть

Тип: активный зуммер (HIGH/LOW)  
Пин: `config.pinBuzzer` (GPIO25 по умолчанию)  
Управление: `webTask`, функция `updateBuzzer()`

### 13.2 Мелодии

| Индекс | Название | Описание |
|--------|----------|----------|
| 0 | Короткий писк | 1 шаг, 150 мс |
| 1 | Двойной писк | 500 мс × 2, пауза 200 мс |
| 2 | Аларм | 7 писков по 800 мс |

Выбор: `config.buzzerMelody (0–2)`

### 13.3 Воспроизведение

Конечный автомат:

- используется `MelodyStep[]`
- без блокировки
- каждый шаг выполняется в `updateBuzzer()`

Запуск:

```
playMelody(melodyType, force)
```
### 13.4 Когда срабатывает

- критические ошибки — всегда (если `buzzerEnabled`)
- некритические — если `buzzerNonCriticalEnabled`
- система заблокирована — каждые 60 секунд (напоминание)
- запуск системы — короткий писк (если нет блокировки)

---

## 14. Watchdog

### 14.1 Внутренний (Task Watchdog)

Контролирует: `ControlTask`

- добавление: `esp_task_wdt_add(controlTaskHandle)`
- таймаут: `config.loopWatchdogTimeout` (30000 мс)
- сброс: `esp_task_wdt_reset()` в каждом цикле

При зависании → паника и перезагрузка ESP32

### 14.2 Внешний (ESP-01S)

Пин: `config.pinWatchdog` (GPIO26)

Сигнал:

```
heartbeatPulseMs (100 мс)
каждые heartbeatPulseMs + heartbeatPauseMs (1000 мс)
```

Задача: `HeartbeatTask`, ядро 1, приоритет 5

#### Условие генерации

- targetTemp > 0  
- нет критических ошибок  

#### Принцип работы

ESP-01S мониторит GPIO2:

- если импульсы пропали > 6 секунд  
→ реле размыкается  
→ отключение 220V

---

## 15. Интеграция с Klipper/Moonraker

### 15.1 UDP Discovery (обнаружение Klipper)

Порт: UDP_PORT (12345)  
Задача: WebTask, интервал 5000 мс  

Протокол: Klipper отправляет broadcast `"FLOOK_DISCOVERY"` → ESP32 отвечает:


FLOOK32:<IP>:<uptime>:<T_air>:<device_id_hex>

Ответ сохраняется:
`klipperStatus.update(remoteIP)` — IP, время, счётчик запросов

### 15.2 Обнаружение Moonraker

Условие:

```
klipperStatus.detected == true
```
#### Алгоритм

Перебор портов:
- 7125
- 7126
- 7130
- 4408
- 8000
- 8080
- 8899

Запрос:

```
GET http://<klipper_ip>:<port>/server/info
```
Поиск:
- `"moonraker"`
- `"klippy"`

#### Результат

При успехе:
- сохранение `moonrakerHost`
- сохранение `moonrakerPort`

#### Повтор

Если не найден:
- повтор каждые 5 минут

### 15.3 Статус печати

Функция: `fetchPrintStatus()`  
Интервал: 60000 мс (1 минута)

Эндпоинт:

```
GET /printer/objects/query?print_stats
```
#### Состояния

- `"printing"` — печать идёт  
- `"paused"` — пауза  
- `"standby"`, `"complete"`, `"error"` — завершено  

#### Детектирование завершения

```
"printing" → не "printing" и не "paused"
```
### 15.4 Автоотключение по завершению печати

#### Условия

- `config.autoShutdownEnabled == true`
- `printEndTime != 0`
- `(millis() - printEndTime) / 60000 ≥ config.autoShutdownMinutes`

#### Действия

- выключение SSR  
- `targetTemp = 0`  
- выключение вентилятора  
- лог уведомление  

#### Ошибки Moonraker

- счётчик: `moonrakerState.consecutiveErrors`
- при 3 ошибках:
  - сброс `moonrakerHost`
  - повторный поиск

---

## 16. Ручной таймер

### 16.1 Назначение

Отключение нагрева через заданное время независимо от печати и Moonraker.

API:

```
POST /api/manual-timer?enable=1&minutes=N
```
(N = 30–600)

#### 16.2 Логика

Проверка (ControlTask):

```
manualTimerActive && millis() >= manualTimerEndTime
```
#### Действия

- выключение SSR  
- `targetTemp = 0`  
- выключение вентилятора  
- сохранение `lastTarget = 0`  
- уведомление:
  - "⏰ Ручной таймер: нагрев отключён"

---

## 17. Кнопка сброса

### 17.1 Аппаратная часть

Пин: GPIO17  
Режим: INPUT_PULLUP (LOW = нажата)

### 17.2 Логика

- короткое нажатие (< 5 сек): игнорируется  

- удержание ≥ 5 сек:
  - LED: заполнение оранжевым  
  - тройная вспышка белым  
  - очистка Preferences:
    - "flook"
    - "dutyTable"
    - "thermal"
  - перезагрузка ESP32  

---

## 18. Автоперезагрузка по бездействию

### 18.1 Условия

- `targetTemp == 0`
- `heaterState == false`
- система не заблокирована
- бездействие ≥ `AUTO_REBOOT_TIMEOUT` (24 часа)

### 18.2 Процесс

- установка `PREF_AUTO_REBOOT_FLAG`
- перезагрузка ESP32

#### При старте

- если флаг установлен → мелодия не играет  
- сброс: любое действие пользователя → `resetActivityTimer()`

---

## 19. Конфигурация

### 19.1 Хранение

Метод: Preferences (NVS)  
Namespace: `"flook"`  
Ключ: `"config"` — бинарный дамп `Config` (sizeof проверка)

### 19.2 Дополнительные namespace

| Namespace | Назначение |
|----------|-----------|
| "flook" | конфиг, Wi-Fi, lastTarget, статус блокировки |
| "dutyTable" | таблица T_возд → duty вентилятора |
| "thermal" | коэффициенты термальной модели |

### 19.3 Загрузка

- проверка `sizeof(Config)`
- несоответствие → сброс к заводским
- Wi-Fi восстанавливается отдельно
- валидация параметров в пределах

### 19.4 Сохранение

- `config.validate()`  
- бинарный дамп структуры  
- отдельное сохранение:
  - Wi-Fi
  - автоотключение
  - lastTarget

---

## 20. OTA обновление

### 20.1 Эндпоинты

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/update` | Ручная загрузка `.bin` файла через веб-интерфейс |
| GET | `/api/check-update` | Проверка наличия новой версии через `latest.json` на GitHub |
| POST | `/api/update-ota` | Автоматическое обновление — перезагрузка в режим OTA |

### 20.2 Ручное обновление (`/api/update`)

Принимает `.bin` файл через `multipart/form-data`.

**Процесс:**
- `Update.begin(maxSketchSpace)` — подготовка раздела
- `Update.write(data, len)` — запись чанков
- `Update.end(true)` — финализация

**Проверка ошибок:** `Update.hasError()`

**При успехе:** ответ `"UPDATE_SUCCESS"`, перезагрузка через 500 мс.

### 20.3 Проверка обновлений (`/api/check-update`)

Скачивает JSON-файл `latest.json` из репозитория GitHub, сравнивает версию прошивки с указанной в JSON.

**Расположение:** `firmware/flook32/latest.json`

**Формат `latest.json`:**
```json
{
  "version": "0.1.0",
  "ota_url": "https://raw.githubusercontent.com/.../flook32_ota.bin",
  "flash_url": "https://raw.githubusercontent.com/.../flook32_flash.bin",
  "notes": "Описание изменений",
  "force": false
}
```

**Поля:**
- `version` — версия прошивки (сравнивается с `FW_VERSION`)
- `ota_url` — прямая ссылка на `.bin` файл для автоматического обновления
- `flash_url` — прямая ссылка на `.bin` файл для прошивки по USB (используется скриптами)
- `notes` — описание изменений (отображается в веб-интерфейсе)
- `force` — принудительное обновление (`true` = предложить обновление независимо от версии)

**Логика:** обновление доступно если `version != FW_VERSION` ИЛИ `force == true`.

### 20.4 Автоматическое обновление (`/api/update-ota`)

1. Запрашивает `latest.json`, получает URL из поля `ota_url`
2. Сохраняет URL и флаг `ota_pending` в NVS
3. Перезагружает устройство
4. При старте (до инициализации Watchdog и задач FreeRTOS) проверяет флаг
5. Если флаг установлен — подключается к Wi-Fi, скачивает прошивку через `Update.writeStream()`, прошивается
6. Сбрасывает флаг и перезагружается с новой прошивкой

**Защита от зацикливания:** при 4 неудачных попытках OTA флаг автоматически сбрасывается.

### 20.5 Скрипты прошивки

Скрипты `flash_flook32.bat` (Windows) и `flash_flook32.sh` (Linux/macOS) автоматически получают последнюю версию и URL для скачивания из `latest.json` (поле `flash_url`).

### 20.6 Веб-интерфейс

На странице Настройки → OTA:
- **Загрузить файл вручную** — выбор `.bin` файла и отправка на `/api/update`
- **Проверить обновления** — запрос к `/api/check-update`, отображение версии и изменений
- **Обновить автоматически** — запуск `/api/update-ota`

### 20.7 Ограничения

- Максимальный размер: `ESP.getFreeSketchSpace()`
- Формат: `.bin`
- После обновления: автоматическая перезагрузка
- Для работы автообновления требуется доступ в интернет (режим STA)
- OTA выполняется до запуска Watchdog — безопасно для системы

---

## 21. Веб-сервер

### 21.1 Технологии

- HTTP: ESPAsyncWebServer (порт 80)  
- WebSocket: `/ws`  
- CORS: разрешены все источники  
- кэширование: `ETag "v1"`, `Cache-Control: max-age=3600`  

### 21.2 Отдача статики

- `index.html`:
  - Сжатый gzip из PROGMEM (`flook32_index_html_gz.h`)
  - Чанкированная передача (файл отдаётся клиенту по частям через `beginChunkedResponse`)
  - `Content-Encoding: gzip`
  - `Cache-Control: max-age=3600` (кешируется на 1 час)
  - `ETag: "v1"` — **меняйте на новую версию при каждом обновлении HTML** (например, `"v2"`, `"v3"`), чтобы браузеры загрузили обновлённый интерфейс

- `favicon.ico`:
  - Из PROGMEM (`favicon_ico.h`)
  - `Cache-Control: max-age=31536000, immutable` (1 год)

- `chart.js` (график температур):
  - Сжатый gzip из PROGMEM (`chart_min_js_gz.h`)
  - `Content-Encoding: gzip`
  - `Cache-Control: max-age=31536000, immutable` (1 год)

- `chartjs-adapter.js` (адаптер дат):
  - Сжатый gzip из PROGMEM (`chartjs_adapter_gz.h`)
  - `Content-Encoding: gzip`
  - `Cache-Control: max-age=31536000, immutable` (1 год)

### 21.3 API эндпоинты

| Метод | Путь | Обработчик |
|------|------|------------|
| GET | /api/all | handleApiAllStates |
| GET | /api/config | handleApiConfig |
| POST | /api/config | обновление конфига (JSON) |
| POST | /api/config/defaults | handleApiConfigDefaults |
| GET | /api/wifi/status | handleApiWifiStatus |
| GET | /api/wifi/scan | handleApiWifiScan |
| GET | /api/wifi/connect | handleApiWifiConnect |
| POST | /api/wifi/reset | handleApiWifiReset |
| GET | /api/error-log | handleApiErrorLog |
| POST | /api/error-log/clear | handleApiErrorLogClear |
| GET | /api/uptime | handleApiUptime |
| GET | /api/target | handleApiGetTarget |
| POST | /api/target | handleApiTarget |
| POST | /api/heater-off | handleApiHeaterOff |
| GET | /api/heater-state | handleApiGetHeaterState |
| GET | /api/fan-state | handleApiGetFanState |
| POST | /api/reboot | handleApiReboot |
| POST | /api/reboot-all | handleApiRebootAll |
| GET | /api/nvs-health | занятость NVS |
| POST | /api/unlock | handleApiUnlock |
| POST | /api/lock-settings | handleApiLockSettings |
| POST | /api/unlock-settings | handleApiUnlockSettings |
| POST | /api/adapt/start | handleApiStartAdaptation |
| POST | /api/adapt/abort | handleApiAbortAdaptation |
| GET | /api/adapt/status | handleApiAdaptationStatus |
| POST | /api/adapt/continue | handleApiAdaptContinue |
| GET | /api/memory | handleApiMemory |
| POST | /api/calibrate-max6675 | handleApiCalibrateMAX6675 |
| POST | /api/thermal-model/reset | handleApiResetThermalModel |
| GET | /api/thermal-status | статус термальной модели |
| POST | /api/moonraker-shutdown | handleApiMoonrakerShutdown |
| POST | /api/manual-timer | handleApiManualTimer |
| GET | /api/duty-table | таблица duty |
| GET | /api/duty-table/add | добавление точки |
| GET | /api/device-id | ID устройства |
| POST | /api/update | OTA обновление |

### 21.4 WebSocket события

#### Сервер → клиент

- `metrics` — метрики (каждую секунду)  
- `history_chunk` — чанки истории при подключении  
- `history_update` — новые точки  

#### Клиент → сервер

- `get_updates:<timestamp>` — история с указанного времени  
- `get_history` — полная история  

### 21.5 Работа с памятью

- static char[] вместо String  
- StaticJsonDocument<N> вместо DynamicJsonDocument  
- чанки по 60 точек  
- configCacheValid = 2 секунды  

---

## 22. Система логирования

### 22.1 Уровни

```cpp
#define LOG_LEVEL 1  // 0=DEBUG, 1=INFO, 2=WARN, 3=ERROR, 4=SILENT

LOG_DEBUG(fmt, ...) // только LOG_LEVEL=0  
LOG_INFO(fmt, ...)  // ≤1  
LOG_WARN(fmt, ...)  // ≤2  
LOG_ERROR(fmt, ...) // ≤3  
LOG_FATAL(fmt, ...) // всегда  
```
### 22.2 Вывод

- Serial (115200 бод)  
- формат: `[LEVEL] сообщение`  
- `LOG_FATAL` всегда выводится  

---

## 23. Мьютексы и критические секции

| Мьютекс | Назначение | Доступ |
|--------|------------|--------|
| tempMux | airTemp, heaterTemp | sensorTask (запись), все (чтение) |
| snapshotMux | SystemSnapshot | controlTask (запись), API (чтение) |
| errorLogMux | ErrorLogEntry vector | webTask / controlTask |
| trendBufferMux | trendBuffer[600] | webTask / controlTask |
| max6675Mux | SPI MAX6675 | sensorTask / webTask |

### Карта мьютексов и доступа задач

```
SensorTask
├── tempMux (запись)
└── max6675Mux (чтение)

ControlTask
├── tempMux (чтение)
├── snapshotMux (запись)
├── errorLogMux (чтение)
└── trendBufferMux (чтение для ошибок)

WebTask
├── errorLogMux (запись/чтение)
├── trendBufferMux (запись)
└── max6675Mux (калибровка)

API handler
├── snapshotMux (чтение)
└── errorLogMux (чтение)
```
#### Макросы температуры

```cpp
#define ENTER_CRITICAL_TEMP() // Вход + замер времени ожидания
#define EXIT_CRITICAL_TEMP()  // Выход
```
---

## Приложение A: Значения по умолчанию

### Системные константы

| Константа | Значение | Назначение |
|----------|----------|------------|
| MAX_ERROR_LOG | 20 | Максимум записей в журнале |
| TREND_BUFFER_SIZE | 600 | Точек в истории |
| MAX_DUTY_TABLE_SIZE | 20 | Точек в таблице duty |
| AUTO_REBOOT_TIMEOUT | 86400000 мс | Бездействие до автоперезагрузки |
| BUTTON_HOLD_TIME | 5000 мс | Время удержания кнопки сброса |
| MAX6675_READ_INTERVAL | 500 мс | Период опроса термопары |
| DS18B20_RESOLUTION | 9 бит | Разрешение датчика воздуха |
| UDP_PORT | 12345 | Порт обнаружения Klipper |

### Температурные пороги

| Параметр | Значение | Описание |
|----------|----------|----------|
| maxHeaterTemp | 110°C | Макс. рабочая температура нагревателя |
| criticalTemp | 120°C | Порог критического перегрева |
| criticalHysteresis | 5°C | Гистерезис сброса перегрева |
| maxAirTemp | 70°C | Макс. температура воздуха |
| airHysteresis | 3°C | Гистерезис перегрева воздуха |
| hysteresis | 0.5°C | Гистерезис управления по воздуху |
| heaterHysteresis | 4°C | Гистерезис управления по нагревателю |
| defaultTargetTemp | 0°C | Цель по умолчанию |

### Вентилятор

| Параметр | Значение | Описание |
|----------|----------|----------|
| fanOnTemp | 55°C | Порог включения вентилятора |
| fanOffHysteresis | 3°C | Гистерезис выключения |
| fanMinOnTime | 30 сек | Мин. время работы |
| maxFanDuty | 1023 | Макс. мощность ШИМ (10 бит) |
| fanPwmFreq | 17000 Гц | Частота ШИМ |

### Интервалы управления

| Параметр | Значение | Описание |
|----------|----------|----------|
| heaterControlInterval | 200 мс | Период управления SSR |
| fanControlInterval | 1000 мс | Период управления вентилятором |
| readInterval | 1000 мс | Период опроса датчиков |
| trendInterval | 3000 мс | Период сохранения истории |
| controlInterval | 3000 мс | Основной цикл защит |
| runawayCheckInterval | 5000 мс | Проверка Thermal Runaway |
| unexpectedCheckInterval | 2000 мс | Проверка Unexpected Heat |
| rateCheckInterval | 1000 мс | Проверка аномального роста |
| loopWatchdogTimeout | 30000 мс | Таймаут Task Watchdog |

### Система ошибок

| Параметр | Значение | Описание |
|----------|----------|----------|
| maxErrorRetries | 3 | Ошибок до блокировки |
| errorWindowMinutes | 10 | Окно подсчёта (мин) |
| minTimeBetweenSameErrors | 30000 мс | Дедупликация ошибок |
| unlockPassword | "unlock" | Пароль разблокировки |

### Heartbeat

| Параметр | Значение | Описание |
|----------|----------|----------|
| heartbeatPulseMs | 100 мс | Длительность импульса |
| heartbeatPauseMs | 900 мс | Пауза между импульсами |

### LED

| Параметр | Значение | Описание |
|----------|----------|----------|
| ledCount | 3 | Количество светодиодов |
| ledBrightness | 50 | Яркость (0-255) |
| ledEnabled | true | LED включены |

### Зуммер

| Параметр | Значение | Описание |
|----------|----------|----------|
| buzzerEnabled | true | Зуммер включён |
| buzzerNonCriticalEnabled | true | Некритические ошибки |
| buzzerMelody | 1 | Мелодия по умолчанию |

### Пины (заводские)

| Пин | Назначение |
|-----|-----------|
| 32 | SSR нагреватель |
| 33 | Вентилятор PWM |
| 26 | Watchdog heartbeat |
| 21 | DS18B20 (1-Wire) |
| 18 | MAX6675 SCK |
| 19 | MAX6675 SO |
| 5 | MAX6675 CS |
| 25 | Бипер |
| 27 | LED WS2812B |
| 17 | Кнопка сброса |

---

## Приложение Б: Диаграмма состояний

```
ЗАПУСК
│
▼
ИНИЦИАЛИЗАЦИЯ (setup)
│
▼
ОЖИДАНИЕ (цель=0)
│
├── цель>0 ──▶ НАГРЕВ
│ │
│ ├── цель достигнута ──▶ ПОДДЕРЖАНИЕ
│ │ │
│ ├── перегрев ──▶ АВАРИЯ (стоп)
│ │ │
│ ├── runaway ──▶ АВАРИЯ (стоп)
│ │ │
│ └── unexpected ──▶ АВАРИЯ (стоп)
│ │
│ 3 ошибки за 10 мин
│ │
│ ▼
│ БЛОКИРОВКА (пароль)
│
└── цель=0 ◀── (сброс цели или таймер)
```

---

## Приложение В: Глоссарий

| Термин | Значение |
|--------|----------|
| SSR | Solid State Relay — твердотельное реле, коммутирует 220В |
| Duty | Коэффициент заполнения ШИМ (0–1023), мощность вентилятора |
| PWM | Pulse Width Modulation — широтно-импульсная модуляция |
| LEDC | LED Control — аппаратный ШИМ-контроллер ESP32 |
| GPIO | General Purpose Input/Output — пин общего назначения |
| SPI | Serial Peripheral Interface — протокол обмена с MAX6675 |
| 1-Wire | Однопроводная шина для датчика DS18B20 |
| NVS | Non-Volatile Storage — энергонезависимая память ESP32 |
| Preferences | Библиотека Arduino для работы с NVS |
| FreeRTOS | Операционная система реального времени |
| Task | Задача FreeRTOS — независимый поток выполнения |
| Mutex | Мьютекс — синхронизация доступа к общим данным |
| Heap | Куча — динамическая память программы |
| Stack | Стек — память для переменных и вызовов функций |
| PROGMEM | Память программ (flash), для хранения констант |
| Watchdog | Сторожевой таймер — перезагрузка при зависании |
| Heartbeat | Периодический сигнал для внешнего watchdog |
| Thermocouple | Термопара K-типа — датчик температуры нагревателя |
| MAX6675 | Микросхема-усилитель термопары с SPI-интерфейсом |
| DS18B20 | Цифровой датчик температуры, интерфейс 1-Wire |
| Thermal Runaway | Неконтролируемый разогрев при неисправности |
| Unexpected Heat | Нагрев при выключенном SSR (залипшее реле) |
| Klipper | Прошивка для 3D-принтеров |
| Moonraker | Веб-сервер для Klipper (API) |
| API | Application Programming Interface |
| REST | Representational State Transfer — стиль API |
| JSON | JavaScript Object Notation — формат обмена данными |
| WebSocket | Протокол двусторонней связи поверх TCP |
| SPA | Single Page Application — одностраничное приложение |
| OTA | Over The Air — обновление прошивки по Wi-Fi |
| gzip | Формат сжатия веб-интерфейса |
| ETag | HTTP-заголовок для кэширования |
| CORS | Cross-Origin Resource Sharing |
| UDP | User Datagram Protocol — обнаружение Klipper |
| AP | Access Point — режим точки доступа Wi-Fi |
| STA | Station — режим клиента Wi-Fi |
| RSSI | Received Signal Strength Indicator |
| NeoPixel | Адресная светодиодная лента WS2812B |
| FIFO | First In First Out — очередь с вытеснением |
| EaseInOut | Функция плавности для LED-анимаций |
| DJB2 | Алгоритм хеширования для дедупликации ошибок |
| UART | Universal Asynchronous Receiver-Transmitter |
| Baud Rate | Скорость Serial (115200 бод) |
| Brownout | Провал напряжения питания |
| Panic | Критическая ошибка FreeRTOS |

[🔝 Наверх](#-прошивка-flook32)

---

[🔙 На главную](../README.md)
