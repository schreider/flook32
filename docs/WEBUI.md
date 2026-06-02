[🔙 На главную](../README.md)

# Веб-интерфейс FLOOK32 — Полная документация

**Файл:** `firmware/flook32/src/index.html`  
**Тип:** Одностраничное приложение (SPA)  
**Размер:** ~1900 строк (HTML + CSS + JavaScript)  
**Зависимости:** Chart.js 3.9.1 + date-fns adapter (CDN)

---

## 🏗️ Архитектурный обзор

Веб-интерфейс работает полностью в браузере и общается с ESP32 по двум каналам:

```
┌──────────────────────────────────────────────┐
│ Браузер                                      │
│ ┌──────────┐  ┌──────────┐ ┌───────────────┐ │
│ │ HTML DOM │  │ Chart.js │ │ JS App Logic  │ │
│ └─────┬────┘  └────┬─────┘ └───────┬───────┘ │
│       │            │               │         │
│       └────────────┴───────────────┘         │
│                    │                         │
│        ┌───────────┴───────────┐             │
│        │ WebSocket   HTTP REST │             │
│        │ (основной) (запасной) │             │
│        └───────────┬───────────┘             │
└────────────────────┼─────────────────────────┘
                     │
                     │       HTTP REST
                     │     (внешний мир)
                     │
             ┌───────┴───────┐       ┌──────────────┐
             │     ESP32     │─────▶│  GitHub API  │
             │    FLOOK32    │       │  (релизы)    │
             └───────────────┘       └──────────────┘
```

| Канал | Протокол | Порт | Использование |
|-------|----------|------|---------------|
| **WebSocket** | `ws://[host]/ws` | 80 | Метрики реального времени, история графика, события блокировки |
| **HTTP REST** | `GET/POST /api/*` | 80 | Конфигурация, Wi-Fi, адаптация, OTA, проверка обновлений, fallback |

**Принцип работы:**  
WebSocket — основной канал для real-time данных.  
HTTP REST — для конфигурации и действий пользователя.  
При обрыве WebSocket интерфейс переключается на HTTP-опрос и параллельно пытается переподключиться с экспоненциальной задержкой.  
Для проверки обновлений ESP32 самостоятельно обращается к GitHub API через HTTPS.

<details>
<summary>📁 DOM-дерево</summary>
  
```
.container
├── .nav-links
│   ├── .nav-link[data-screen="main"]
│   ├── .nav-link[data-screen="config"]
│   ├── .nav-link[data-screen="wifi"]
│   ├── .nav-link[data-screen="errors"]
│   │   └── .badge-container
│   │       ├── #badge-critical
│   │       ├── #badge-warning
│   │       └── #badge-info
│   └── .nav-link[data-screen="adapt"]
├── .flook-header
│   ├── h1
│   └── .header-info
├── #screen-main.screen.active
│   ├── #lockBanner
│   │   ├── #lockMessage
│   │   ├── #unlockPass
│   │   └── button (unlock)
│   ├── .metrics-grid (6 шт)
│   ├── #heaterOffBtn + button (reboot)
│   ├── .chart-container > #tempChart
│   ├── .card
│   │   ├── #presets > .preset[data-temp] (7 шт)
│   │   └── .temp-control > #tempInput + button
│   ├── .config-group (ручной таймер)
│   │   ├── #manualTimerEnable
│   │   ├── #manualTimerMinutes
│   │   ├── #manualTimerMinutesInput
│   │   ├── button.quick-btn (-30, +30, +1ч)
│   │   ├── button (сохранить)
│   │   └── #manualTimerStatus
│   ├── #thermalDiagnostics
│   │   ├── #modelConfidence + #confidenceFill
│   │   ├── #modelError
│   │   ├── #heaterRate
│   │   └── #coolingRate
│   ├── #klipperStatus
│   └── #uptime
├── #screen-config.screen
│   ├── #lockStatus + #unlockPassConfig + #unlockSettingsBtn + #lockSettingsBtn
│   ├── #dangerWarning
│   ├── #configGrid (15 секций)
│   │   └── .config-section#section-{id}
│   │       ├── .section-header
│   │       └── .section-content#content-{id}
│   ├── #saveConfigBtn + #resetDefaultsBtn
│   ├── #currentSettings
│   ├── #update-status + #update-progress-container
│   ├── #firmware-file + button (upload)
│   ├── #update-check-status + #check-update-btn
│   ├── #update-info > #latest-version + #release-notes + button (updateOTA)
│   ├── #calibTemp + button (calibrate)
│   ├── #thermalModelStatusText + button (reset model)
│   ├── #thermalModelNoAdaptationWarning
│   ├── #thermalWarning
│   ├── #thermalRunawayDisabledNote
│   ├── #unexpectedHeatDisabledNote
│   ├── #adaptationStatus
│   ├── #moonrakerAutoShutdown + #moonrakerShutdownMinutes
│   ├── #moonrakerSettingsStatus
│   ├── #fanAutoLimitStatus + #fanAutoLimitStatusText
│   ├── #watchdog-pin + #watchdog-pulse-ms + #watchdog-interval-ms
├── #screen-wifi.screen
│   ├── .wifi-status-item (SSID, IP, RSSI)
│   ├── #wifiScanBlock
│   │   ├── button (scan)
│   │   ├── #networksPanel > #networkSelect + #wifiPassword + button
│   │   └── #scanMessage
│   ├── #wifiResetBlock > button (reset)
│   └── #wifiResultCard > #resultIp + #resultSsid + button (goToIp)
├── #screen-errors.screen
│   ├── .filter-group > .filter-btn[data-filter] (4 шт)
│   ├── button (clear)
│   └── #errorList > .error-item > .error-header + .error-details
├── #screen-adapt.screen
│   ├── #adaptBlocked > #blockReason
│   ├── #adaptReady
│   │   ├── #adaptTarget + button (start)
│   │   └── #adaptStatusMessage
│   ├── #adaptProgress
│   │   ├── #progressAirTemp + #progressHeaterTemp + #progressTarget
│   │   ├── #adaptProgressFill
│   │   ├── #phaseIndicator
│   │   ├── #adaptStatus
│   │   └── button (abort)
│   ├── #adaptWaitingPanel > #continueAdaptBtn
│   ├── #adaptComplete
│   └── #adaptResults
│       ├── #basicResults
│       ├── #runawayResults
│       ├── #unexpectedResults
│       ├── #fanResults
│       ├── #max6675Results
│       ├── #airSensorResults
│       ├── #lockResults
│       ├── #timingResults
│       └── #fanAutoLimitResults
├── .footer
├── #offlineBanner
├── #disclaimerOverlay > .disclaimer-dialog > #disclaimerAcceptBtn + #disclaimerTimer
└── #dynamic-tooltip (создаётся динамически)
```
</details>

<details>
<summary>📁 Карта обработчиков событий</summary>

```
click .nav-link → showScreen(dataset.screen)
click .preset[data-temp] → setTargetTemp()
click #heaterOffBtn → heaterOff()
click reboot button → rebootAll()
click .temp-set-btn → setTargetTemp()

click button (unlock in #lockBanner) → unlockSystem()

click #unlockSettingsBtn → unlockSettings()
click #lockSettingsBtn → lockSettings()
click #saveConfigBtn → saveConfig()
click #resetDefaultsBtn → resetToDefaults()

click .section-header → toggleSection(id)
click .error-header → toggleErrorDetails()
click .filter-btn → renderErrors()
click clear errors → clearErrors()

click start adapt → startAdaptation()
click #continueAdaptBtn → continueAdaptation()
click abort adapt → abortAdaptation()

click scan wifi → scanNetworks()
click connect wifi → connectToNetwork()
click reset wifi → resetWiFi()
click goToIp → goToIp()

click calibrate → calibrateMAX6675()
click reset model → resetThermalModel()
click upload → uploadFirmware()
click #check-update-btn → checkForUpdates()
click #update-info button → updateOTA()

click save timer → saveManualTimer()
click .quick-btn → changeManualTimer()

click #disclaimerAcceptBtn → close overlay + scanNetworks()

input #manualTimerMinutes → syncManualTimerValue()
change #manualTimerMinutesInput → syncManualTimerValue()

mouseenter .help-icon → showTooltipWithDelay()
mouseleave .help-icon → hideTooltipWithDelay()
mouseenter #dynamic-tooltip → cancel hide
mouseleave #dynamic-tooltip → hideTooltipWithDelay()
click document → hideTooltipImmediately()
keydown document → hideTooltipImmediately()

beforeunload window → stopAdaptUpdates()

WebSocket open → сервер автоматически отправляет историю
WebSocket message → updateChartData() / updateUIFromWS()
WebSocket close → offline banner + reconnect
WebSocket error → console.error + reconnect

XHR progress → OTA progress bar
XHR load → OTA result

DOMContentLoaded → initChart() + connectWebSocket() + setInterval(...) + loadMainData() + disclaimer
```
</details>

<details>
<summary>📁 Карта функций — кто кого вызывает</summary>
  
```
setTargetTemp()
  └─> loadMainData()

heaterOff()
  └─> loadMainData()

unlockSystem()
  └─> location.reload()

unlockSettings()
  └─> loadConfig()

lockSettings()
  └─> loadConfig()

saveConfig()
  └─> loadConfig()

resetToDefaults()
  └─> loadConfig()

calibrateMAX6675()
  └─> loadConfig()

checkForUpdates()
  └─> fetch('/api/check-update')
  └─> updateOTA()

updateOTA()
  └─> fetch('/api/update-ota')

loadConfig()
  └─> updateConfigFields()
  └─> updateLockUI()
  └─> updateThermalModelWarnings()
  └─> updateWatchdogInfo()
  └─> restoreSectionStates()
  └─> loadThermalModelStatus()
  └─> loadMoonrakerSettings()
  └─> updateFanAutoLimitStatus()
  └─> initTooltips()

showScreen(id)
  ├─ main   └─> loadMainData() + chart.resize()
  ├─ config └─> loadAllConfigSections() + loadConfig()
  ├─ wifi   └─> loadWifiStatus()
  ├─ errors └─> loadErrors()
  └─ adapt  └─> checkAdaptStatus()

connectWebSocket()
  └─ onopen └─> сервер отправляет историю автоматически

updateUIFromWS(data)
  └─> document.getElementById().textContent (множество)
  └─> document.getElementById().classList (lockBanner)
  └─> document.getElementById().disabled (heaterOffBtn, tempInput)
  └─> document.querySelectorAll().style (presets)

updateChartData(data)
  └─ history_chunk └─> historyPoints.push()
  └─ when receivedChunks == expectedChunks └─> sort + distribute + chart.update()
  └─ history_update └─> datasets.push() + chart.update()

renderErrors()
  └─> updateErrorBadges()

checkAdaptStatus()
  └─> updatePhaseIndicator()
  └─> updateAdaptTemps()
  └─> startAdaptUpdates() / stopAdaptUpdates()

loadAllConfigSections()
  └─> loadConfig()
  └─> initTooltips()

saveManualTimer()
  └─> fetch('/api/manual-timer?enable=0/1&minutes=N')

saveMoonrakerSettings()
  └─> fetch('/api/moonraker-shutdown?enable=0/1&minutes=N')
```
</details>

<details>
<summary>📁 Схема потоков данных</summary>
  
```
WebSocket (message)
  ├─ type: metrics  ──> updateUIFromWS()      ──> DOM (метрики, lock, klipper, thermal)
  ├─ type: history_chunk ──> updateChartData() ──> chart (сборка чанков)
  └─ type: history_update ──> updateChartData() ──> chart (добавление точек)

HTTP GET /api/all
  └─> updateUIFromWS()                         ──> DOM (fallback)

HTTP GET /api/all (adapt active)
  └─> updateAdaptTemps()                       ──> #progress*Temp

HTTP GET /api/error-log
  ├─> renderErrors()                           ──> #errorList
  └─> updateErrorBadges()                      ──> #badge-* + document.title

HTTP GET /api/config
  └─> loadConfig()                             ──> #configGrid, #currentSettings, etc

HTTP GET /api/wifi/status
  └─> loadWifiStatus()                         ──> #wifiSsid, #wifiIp, #wifiRssi

HTTP GET /api/adapt/status
  └─> checkAdaptStatus()                       ──> #adaptProgressFill, #adaptStatus, #phaseIndicator

HTTP GET /api/check-update
  └─> checkForUpdates()                        ──> #update-info, #current-version

HTTP POST /api/update-ota
  └─> updateOTA()                              ──> #update-progress-container, #update-status

JS setInterval (1s)
  └─> updateManualTimerStatus()                ──> #manualTimerStatus

JS setInterval (5s)
  └─> loadMainData()                           ──> updateUIFromWS()

JS setInterval (5s)
  └─> loadWifiStatus()                         ──> #wifiSsid, #wifiIp, #wifiRssi

JS setInterval (10s)
  └─> loadThermalStatus()                      ──> #thermalModelStatusText, #thermalDiagnostics

JS setInterval (10s)
  └─> updateErrorBadges()                      ──> #badge-*, document.title

user action
  ├─ setTargetTemp()   ──> POST /api/target       ──> OK ──> loadMainData()
  ├─ heaterOff()       ──> POST /api/heater-off   ──> OK ──> loadMainData()
  ├─ saveConfig()      ──> POST /api/config       ──> OK ──> loadConfig()
  ├─ unlockSystem()    ──> POST /api/unlock       ──> success ──> reload()
  ├─ unlockSettings()  ──> POST /api/unlock-settings ──> success ──> loadConfig()
  ├─ connectToNetwork()──> POST /api/wifi/connect ──> IP ──> showWifiResult()
  ├─ checkForUpdates() ──> GET /api/check-update  ──> JSON ──> #update-info
  ├─ updateOTA()       ──> POST /api/update-ota   ──> success ──> reload()
  └─ uploadFirmware()  ──> POST /api/update       ──> XHR progress ──> #update-progress-bar
```
</details>

---

## 🔄 Жизненный цикл приложения

### 1. Загрузка страницы (DOMContentLoaded)

```
initChart()
  └─> Создание графика Chart.js с 4 датасетами

connectWebSocket()
  └─> ws://[host]/ws
      ├─ onopen → сервер начинает отправку истории (history_chunk)
      └─ onerror/onclose → запуск reconnect

loadMainData()
loadWifiStatus()
loadThermalStatus()
```
Интервалы:

```
setInterval(loadMainData, 5000)
setInterval(loadWifiStatus, 5000)
setInterval(loadThermalStatus, 10000)
```

Фоновый опрос ошибок (беджи) — каждые 10 секунд, **кроме случая, когда открыт экран ошибок**.

Восстановление состояния:

- последний экран (`sessionStorage`)
- свёрнутые секции настроек

---

### 2. Переключение экранов (`showScreen(id)`)

```
1. Скрыть все .screen
2. Показать screen-{id}
3. Обновить навигацию
4. Сохранить в sessionStorage
```

Загрузка данных:

```
main   → loadMainData() + chart.resize()
config → загрузка конфигурации (один раз)
wifi   → loadWifiStatus()
errors → loadErrors()
adapt  → checkAdaptStatus()
```

---

### 3. Разрушение (`beforeunload`)

- остановка адаптации (если активна)
- WebSocket закрывается браузером

---

## 📡 WebSocket протокол

### Подключение

```javascript
ws = new WebSocket(`ws://${window.location.hostname}/ws`)
```

---

### Сообщения сервер → клиент

#### Метрики (тип `metrics`)

```json
{
  "type": "metrics",
  "a": 45.2,
  "h": 89.7,
  "tg": 60.0,
  "hs": 1,
  "fs": 1,
  "fp": 512,
  "u": 3600,
  "systemLocked": 0,
  "lockMessage": "Причина блокировки",
  "klipper": {
    "detected": true,
    "ip": "192.168.1.100"
  },
  "md": true,
  "thermalEnabled": true,
  "thermal": {
    "confidence": 85,
    "error": 2.1,
    "heaterRate": 12.5,
    "coolingRate": 0.05
  }
}
```

<details>
<summary>📁 Спецификация полей metrics</summary>

| Поле | Тип | Диапазон | Описание |
|------|-----|----------|----------|
| `type` | string | `"metrics"` | Идентификатор типа сообщения |
| `a` | float | °C | Текущая температура воздуха в камере (DS18B20) |
| `h` | float | °C | Текущая температура нагревателя (MAX6675) |
| `tg` | float | °C | Заданная целевая температура |
| `hs` | int | 0 или 1 | Состояние нагревателя (1 = включён, 0 = выключен) |
| `fs` | int | 0 или 1 | Состояние вентилятора (1 = включён, 0 = выключен) |
| `fp` | int | 0–1023 | Текущий ШИМ-сигнал вентилятора (duty cycle) |
| `u` | int | секунды | Время непрерывной работы ESP32 (uptime) |
| `systemLocked` | int | 0 или 1 | Флаг полной системной блокировки (1 = заблокирована) |
| `lockMessage` | string | — | Человекочитаемая причина блокировки |
| `klipper.detected` | bool | — | Обнаружен ли Klipper в локальной сети |
| `klipper.ip` | string | — | IP-адрес хоста с Klipper/Moonraker |
| `md` | bool | — | Обнаружен ли Moonraker API |
| `thermalEnabled` | bool | — | Активирована ли обучаемая термальная модель |
| `thermal.confidence` | int | 0–100 | Уверенность модели в прогнозе (проценты) |
| `thermal.error` | float | °C | Текущее отклонение прогноза модели от факта |
| `thermal.heaterRate` | float | °C/мин | Измеренная скорость нагрева нагревателя |
| `thermal.coolingRate` | float | °C/сек | Измеренная скорость остывания с вентилятором |

</details>

---

#### Загрузка истории (тип `history_chunk`)

```json
{
  "type": "history_chunk",
  "chunk": 0,
  "total": 10,
  "data": [
    {
      "t": 123456789,
      "a": 45.2,
      "h": 89.7,
      "tg": 60.0,
      "pred": 61.5
    }
  ]
}
```

- `chunk` – индекс текущего фрагмента (начиная с 0)
- `total` – общее количество фрагментов
- `data` – массив точек; каждая точка содержит:
  - `t` – миллисекундный timestamp
  - `a` – температура воздуха
  - `h` – температура нагревателя
  - `tg` – целевая температура
  - `pred` – прогноз модели (может отсутствовать)

Клиент собирает все точки из последовательных чанков. Когда `receivedChunks === expectedChunks`, данные сортируются по `t` и отображаются на графике.

---

#### Обновление в реальном времени (тип `history_update`)

```json
{
  "type": "history_update",
  "data": [
    {
      "t": 123456789,
      "a": 46.1,
      "h": 91.2,
      "tg": 60.0,
      "pred": 62.0
    }
  ]
}
```
Структура точек та же, что и в `history_chunk`. Данные добавляются к существующим датасетам без полной перерисовки.

---

### Команды клиент → сервер

В текущей реализации клиент **не отправляет** никаких команд для запроса истории. Сервер автоматически отправляет накопленную историю сразу после установки WebSocket-соединения. Команда `get_history` зарезервирована, но не используется.

---

### Reconnect логика

```javascript
const WS = {
    MAX_RECONNECT_DELAY: 30000,
    BASE_RECONNECT_DELAY: 3000
};

delay = Math.min(BASE_RECONNECT_DELAY * wsReconnectAttempts, MAX_RECONNECT_DELAY);
```

---

## 🌐 REST API

### Метрики

| Метод | Endpoint | Описание |
|------|----------|----------|
| GET | `/api/all` | Все метрики (та же структура, что и WS-сообщение `metrics`) |
| GET | `/api/uptime` | Аптайм в секундах |
| POST | `/api/target?value=N` | Установка целевой температуры |
| POST | `/api/heater-off` | Аварийное отключение нагревателя |
| POST | `/api/unlock?password=X` | Разблокировка системы после полной блокировки |
| POST | `/api/reboot-all` | Полная перезагрузка ESP32 |

### Конфигурация

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| GET | `/api/config` | — | Компактный JSON конфигурации | Загрузка всех настроек |
| POST | `/api/config` | JSON (body) | `"OK"` / `"OK_RESTART"` | Сохранение |
| POST | `/api/config/defaults` | — | `"OK"` | Сброс к заводским настройкам |
| POST | `/api/unlock-settings?password=X` | password | `"Settings unlocked"` или `{"success":true}` | Разблокировка настроек |
| POST | `/api/lock-settings` | — | `"OK"` | Блокировка настроек |

---

### Калибровка

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| POST | `/api/calibrate-max6675?temp=N` | temp (эталонная температура) | `{"success": true, "offset": 2.5}` | Калибровка датчика MAX6675 |

---

### Термальная модель

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| POST | `/api/thermal-model/reset` | — | `"Thermal model reset to adaptation data"` | Сброс модели к данным адаптации |

---

### Таймеры

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| POST | `/api/manual-timer?enable=0` | — | `"OK"` | Выключение ручного таймера |
| POST | `/api/manual-timer?enable=1&minutes=N` | minutes | `"OK"` | Запуск ручного таймера |
| POST | `/api/moonraker-shutdown?enable=0` | — | `{"success": true}` | Отключение автоотключения |
| POST | `/api/moonraker-shutdown?enable=1&minutes=N` | minutes | `{"success": true}` | Включение автоотключения |

**Примечание:**
- Ручной таймер: одна и та же кнопка «Запустить» отправляет `enable=1&minutes=N`, если чекбокс включён, либо `enable=0`, если выключен.
- Moonraker автоотключение: постоянный фоновый опрос не выполняется; настройки загружаются один раз при старте и при открытии экрана настроек.

---

### Wi-Fi

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| GET | `/api/wifi/status` | — | `{ssid, ip, rssi}` | Текущий статус подключения |
| GET | `/api/wifi/scan` | — | `{networks: [{ssid, rssi}, ...]}` | Сканирование доступных сетей |
| POST | `/api/wifi/connect` | ssid, password (query params) | `{success: true, ip: "x.x.x.x"}` | Подключение к выбранной сети |
| POST | `/api/wifi/reset` | — | `"OK"` | Сброс настроек Wi-Fi и переход в режим точки доступа |

---

### Адаптация

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| GET | `/api/adapt/status` | `t` (timestamp для предотвращения кэширования) | JSON с полями `inProgress`, `phase`, `progress`, `message`, `blocked`, `blockedReason` | Проверка статуса адаптации |
| POST | `/api/adapt/start?target=N` | target (целевая температура) | `"OK"` | Запуск процесса адаптации |
| POST | `/api/adapt/continue` | — | `"OK"` | Продолжение адаптации после фазы ожидания |
| POST | `/api/adapt/abort` | — | `"OK"` | Аварийное прерывание адаптации |

---

### Журнал ошибок

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| GET | `/api/error-log` | — | Массив объектов ошибок | Загрузка журнала |
| POST | `/api/error-log/clear` | — | `"OK"` | Полная очистка журнала |

---

### OTA

| Метод | Endpoint | Параметры | Возвращает | Использование |
|------|----------|-----------|------------|---------------|
| POST | `/api/update` | FormData с полем `firmware` (.bin файл) | `"UPDATE_SUCCESS"` при успехе | Ручная загрузка прошивки через веб-интерфейс |
| GET | `/api/check-update` | — | `{"updateAvailable":bool,"currentVersion":"...","latestVersion":"...","downloadUrl":"...","releaseNotes":"..."}` | Проверка наличия новой версии на GitHub |
| POST | `/api/update-ota` | `url` — ссылка на .bin файл | `{"success":true,"message":"Update OK, restarting..."}` | Автоматическое обновление прошивки из релиза |

---

## 📊 Поток данных графика

### Временная шкала

```
serverStartTime = Date.now() - uptime_seconds * 1000
x = (timestamp_point - serverStartTime) / 1000
```

---

### Загрузка истории

```
1. WebSocket open
2. Сервер начинает отправку history_chunk (массив чанков)
3. Клиент накапливает точки в historyPoints[]
4. Когда получено количество чанков == total, данные сортируются и отображаются
5. chart.update()
```

---

### Обработка чанков

```
receivedChunks++;
if (receivedChunks === expectedChunks) {
    historyPoints.sort((a,b) => a.t - b.t);
    // распределение по датасетам
    chart.update();
}
```

---

### Реальное время

- точки из `history_update` добавляются напрямую в датасеты
- без полной перерисовки

---

### Переподключение

- история загружается заново (сервер отправляет полный набор чанков)
- потерянные точки восстанавливаются

---

## 🔄 Частота обновления

```javascript
const POLLING = {
    MAIN_DATA: 5000,
    WIFI_STATUS: 5000,
    THERMAL_STATUS: 10000,
    ERROR_BADGES: 10000,
    ADAPT_STATUS: 1000,
    ADAPT_TEMPS: 2000
};
```
<details>
<summary>📁 Динамическое обновление DOM</summary>
  
```
#airTemp → WS/HTTP → updateUIFromWS()
#heaterTemp → WS/HTTP → updateUIFromWS()
#targetTemp → WS/HTTP → updateUIFromWS()
#heaterState → WS/HTTP → updateUIFromWS()
#fanState → WS/HTTP → updateUIFromWS()
#fanDuty → WS/HTTP → updateUIFromWS()
#uptime → WS/HTTP → updateUIFromWS()

#lockBanner → WS/HTTP → updateUIFromWS()
#lockMessage → WS/HTTP → updateUIFromWS()

#klipperStatus → WS/HTTP
#thermalDiagnostics → WS/HTTP (10s)

#tempChart → WS → updateChartData()

#manualTimerStatus → JS → 1s

#errorList → HTTP → renderErrors()

#badge-critical / #badge-warning / #badge-info → HTTP → updateErrorBadges()

document.title → updateErrorBadges()

#wifi* → loadWifiStatus()

#adaptProgressFill → checkAdaptStatus()
#progressAirTemp → updateAdaptTemps()

#offlineBanner → WS events
```
</details>

<details>
<summary>📁 Константы</summary>

```
POLLING:
MAIN_DATA = 5000
WIFI_STATUS = 5000
THERMAL_STATUS = 10000
ERROR_BADGES = 10000
ADAPT_STATUS = 1000
ADAPT_TEMPS = 2000

WS:
BASE = 3000
MAX = 30000

AS:
MIN = 30
MAX = 600
STEP = 15
DEFAULT = 30
```
</details>

<details>
<summary>📁 Порядок инициализации</summary>

```
DOMContentLoaded →
1. initChart()
2. connectWebSocket()
3. loadMainData()
4. loadWifiStatus()
5. loadThermalStatus()
6. setInterval(...)
7. loadAllConfigSections()
8. restore sessionStorage
9. initManualTimer()
10. loadMoonrakerSettings()
11. bind filters
12. initTooltips()
13. export globals
```
</details>

---

### Таблица

| Данные | Канал | Интервал | Примечание |
|--------|------|----------|------------|
| Метрики | WS | realtime | основной |
| Метрики fallback | HTTP | 5s | при обрыве |
| Uptime | HTTP | 1 раз | при WS connect |
| Wi-Fi | HTTP | 5s | только экран |
| Thermal | HTTP | 10s | диагностика |
| Ошибки (беджи) | HTTP | 10s | всегда, кроме экрана ошибок |
| Adapt status | HTTP | 1s | активен |
| Adapt temps | HTTP | 2s | активен |
| Таймер | JS | 1s | локально |

---

## 🎛️ Состояния интерфейса

### Глобальные переменные

```javascript
systemLocked
settingsLocked
wsConnected
currentFilter
chart
serverStartTime
adaptInterval
adaptTempInterval
manualTimerActive
manualTimerEndTime
```

---

### Матрица влияния

| Элемент | systemLocked | settingsLocked | wsConnected | adaptation |
|--------|-------------|----------------|------------|-----------|
| Пресеты | ❌ | — | — | — |
| Ввод цели | ❌ | — | — | — |
| Heater OFF | ❌ | — | — | — |
| Баннер | ✅ | — | — | — |
| Настройки | — | ❌ | — | — |
| Save | — | ❌ | — | — |
| Offline | — | — | ❌ | — |
| График | — | — | fallback | — |
| Adapt progress | — | — | — | ✅ |

<details>
<summary>📁 Визуальные состояния</summary>

```
systemLocked:
- lockBanner show
- inputs disabled
- presets opacity 0.5

settingsLocked:
- save disabled
- inputs disabled

wsConnected = false:
- offlineBanner show
- HTTP fallback

adaptation active:
- adaptProgress show
- adaptReady hidden
```
</details>

---

### Схема состояний блокировки

Система проходит через три уровня эскалации при обнаружении проблем:

```
┌─────────┐    Критический перегрев     ┌──────────────────┐
│  НОРМА  │────────────────────────────>│  ВРЕМЕННАЯ       │
│         │                             │  БЛОКИРОВКА      │
│         │<────────────────────────────│  (нагрев откл.)  │
└─────────┘    Остывание до нормы       └──────┬───────────┘
     │                                         │
     │  3 ошибки за окно подсчёта              │
     └─────────────────────────────────────────┘
                         ↓
               ┌──────────────────┐
               │  ПОЛНАЯ          │
               │  БЛОКИРОВКА      │
               │  (требуется       │
               │   пароль)        │
               └──────────────────┘
```

**Сброс счётчика ошибок:**
- Счётчик сбрасывается автоматически через `errorWindowMinutes` минут без новых ошибок.
- Временная блокировка снимается, когда температура опускается ниже порога минус гистерезис.

**Пароль разблокировки:**
- Задаётся в настройках (секция «Блокировка»).
- После ввода пароля счётчик ошибок сбрасывается, блокировка снимается.
- Даже перезагрузка устройства не сбрасывает полную блокировку без пароля.

---

### Зависимости настроек

| Настройка | Условие | Причина |
|-----------|--------|--------|
| enableThermalModel | adaptationPerformed !== true | нужна адаптация |
| enableFanAutoLimit | adaptationPerformed !== true | нужна адаптация |
| runawayProtection | thermalModel === true | заменяется термальной моделью |
| unexpectedHeat | thermalModel === true | заменяется термальной моделью |

## 🗺️ Конфигурационная карта (компактные ключи → полные имена)

```javascript
{
    // Основные защиты
    mt:  "maxHeaterTemp",
    ct:  "criticalTemp",
    ch:  "criticalHysteresis",
    ma:  "maxAirTemp",
    ah:  "airHysteresis",
    hy:  "hysteresis",
    hh:  "heaterHysteresis",
    eH:  "enableHeaterHysteresis",
    dt:  "defaultTargetTemp",
    iH:  "invertHeaterSignal",
    iF:  "invertFanSignal",

    // Вентилятор
    fT:  "fanOnTemp",
    fH:  "fanOffHysteresis",
    fM:  "fanMinOnTime",
    mFD: "maxFanDuty",
    eF:  "enableFanEfficiencyCheck",
    fE:  "fanEfficiencyTimeout",
    fF:  "fanEfficiencyThreshold",

    // Автоограничение вентилятора
    eFAL:  "enableFanAutoLimit",
    fALH:  "fanAutoLimitHysteresis",
    fALA:  "fanAutoLimitAdjustStep",
    fALM:  "fanAutoLimitMinDuty",
    fALI:  "fanAutoLimitCheckInterval",
    fALS:  "fanAutoLimitStableCount",
    fALAd: "fanAutoLimitAdapted",

    // Thermal Runaway
    tR:  "enableThermalRunawayProtection",
    r1:  "runawayPhase1Time",
    r2:  "runawayPhase2Time",
    rT:  "runawayMaxTimeToTarget",
    rH:  "runawayMinHeaterRisePerMin",
    rA:  "runawayMinAirRisePerMin",
    rD:  "runawayMaxHeaterDrop",
    rY:  "runawayHysteresis",
    rR:  "runawayRecoveryTimeout",
    rF:  "runawayFanOn",

    // Неожиданный нагрев
    uH:  "enableUnexpectedHeatProtection",
    uT:  "unexpectedHeatTimeout",
    uP:  "unexpectedHeatThreshold",
    mC:  "minCoolingRate",
    uY:  "unexpectedHeatHysteresis",
    uC:  "unexpectedHeatClearTime",
    uS:  "unexpectedHeatSafeOffset",
    uA:  "enableUnexpectedHeatAdaptive",
    aB:  "adaptiveBaseTemp",
    aC:  "adaptiveCoefficient",
    aM:  "adaptiveMinOffset",

    // MAX6675
    mO:  "max6675Offset",
    mP:  "enableMAX6675Protection",
    mS:  "max6675StabilitySamples",
    mJ:  "max6675TempJumpThreshold",
    mN:  "max6675MinTemp",
    mX:  "max6675MaxTemp",

    // DS18B20
    dO:  "ds18b20Offset",
    dS:  "ds18b20Scale",
    dC:  "ds18b20CalEnabled",
    aP:  "enableAirSensorProtection",
    aS:  "airSensorStabilitySamples",
    aJ:  "airSensorTempJumpThreshold",
    aN:  "airSensorMinTemp",
    aX:  "airSensorMaxTemp",
    aU:  "airSensorUnstableRange",
    aV:  "airSensorUnstableDeviation",
    aW:  "airSensorUnstableWindow",
    aD:  "airSensorDirectionChanges",

    // Диагностика
    eA:  "enableAbnormalRate",
    aT:  "abnormalRateThreshold",

    // Блокировка
    mR:  "maxErrorRetries",
    eW:  "errorWindowMinutes",
    mE:  "minTimeBetweenSameErrors",
    mOc: "minTimeBetweenOverheatCounts",
    uPw: "unlockPassword",
    sl:  "settingsLocked",

    // Тайминги
    hP:  "heartbeatPulseMs",
    hQ:  "heartbeatPauseMs",
    rI:  "readInterval",
    cI:  "controlInterval",
    tI:  "trendInterval",
    hI:  "heapCheckInterval",
    lW:  "loopWatchdogTimeout",
    uD:  "udpDiscoveryTimeout",
    dR:  "discoveryRetryInterval",
    eL:  "enableLoopWatchdog",
    hC:  "heaterControlInterval",
    fC:  "fanControlInterval",
    rC:  "runawayCheckInterval",
    uCc: "unexpectedCheckInterval",
    rAc: "rateCheckInterval",

    // Общие
    aSd: "moonrakerAutoShutdown",
    aSm: "moonrakerShutdownMinutes",

    // Термальная модель
    tM:  "enableThermalModel",
    tS:  "thermalModelSensitivity",
    tC:  "thermalModelCheckInterval",
    tL:  "thermalModelLogWarnings",

    // LED
    lE:  "ledEnabled",
    lC:  "ledCount",
    lB:  "ledBrightness",
    lP:  "ledPin",

    // Бипер
    bE:  "buzzerEnabled",
    bN:  "buzzerNonCriticalEnabled",
    bM:  "buzzerMelody",

    // Пины
    pS:  "pinSsr",
    pF:  "pinFan",
    pW:  "pinWatchdog",
    pO:  "pinOneWire",
    pK:  "pinMaxSck",
    pM:  "pinMaxSo",
    pC:  "pinMaxCs",
    pB:  "pinBuzzer",
    pL:  "pinLed",

    // Адаптация (результаты)
    aPd: "adaptationPerformed",
    aHr: "adaptedHeaterRiseRate",
    aAr: "adaptedAirRiseRate",
    aCr: "adaptedCoolingRate",
    aNt: "adaptedNoiseThreshold",
    aUr: "adaptedUnstableRange",
    aTg: "adaptedTimeToTarget",
    fEf: "fanEffective",
    aTt: "adaptationTimestamp"
}
```

---

## ⚠️ Обработка ошибок

### HTTP (с таймаутом)

```javascript
async function apiGet(endpoint) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
        const response = await fetch(endpoint, {
            method: 'GET',
            headers: { 'Connection': 'close' },
            signal: controller.signal
        });

        clearTimeout(timeout);

        if (!response.ok) {
            throw new Error(await response.text());
        }

        return await response.json();
    } catch (e) {
        clearTimeout(timeout);
        throw e;
    }
}
```

<details>
<summary>📁 Список всех alert() и confirm()</summary>

| Функция | Тип | Текст |
|---------|-----|-------|
| `setTargetTemp()` | alert | Система заблокирована |
| `setTargetTemp()` | alert | Температура должна быть 0-70°C |
| `setTargetTemp()` | alert | Ошибка установки температуры |
| `heaterOff()` | alert | Система заблокирована |
| `heaterOff()` | confirm | Отключить нагрев? |
| `heaterOff()` | alert | Ошибка отключения нагрева |
| `rebootAll()` | confirm | Перезагрузить устройство? |
| `unlockSystem()` | alert | Введите пароль |
| `unlockSystem()` | alert | Система разблокирована |
| `unlockSystem()` | alert | Неверный пароль |
| `unlockSettings()` | alert | Введите пароль разблокировки |
| `unlockSettings()` | alert | Неверный пароль |
| `lockSettings()` | alert | Ошибка блокировки настроек |
| `saveConfig()` | confirm | Сохранить настройки? Некоторые изменения требуют перезагрузки. |
| `saveConfig()` | alert | ✅ Настройки сохранены |
| `saveConfig()` | alert | ✅ Настройки сохранены. Устройство будет перезагружено для применения пинов. |
| `saveConfig()` | alert | ❌ Ошибка: (текст ошибки) |
| `saveConfig()` | alert | ❌ Ошибка соединения: (текст) |
| `resetToDefaults()` | alert | Сначала разблокируйте настройки |
| `resetToDefaults()` | confirm | ⚠️ Сбросить ВСЕ настройки к заводским? Wi-Fi настройки будут сохранены. Это действие нельзя отменить! |
| `calibrateMAX6675()` | alert | 🔒 Сначала разблокируйте настройки |
| `calibrateMAX6675()` | alert | Введите эталонную температуру (0-400°C) |
| `calibrateMAX6675()` | confirm | Калибровать MAX6675 по эталону N°C? |
| `calibrateMAX6675()` | alert | ✅ Калибровка выполнена! |
| `calibrateMAX6675()` | alert | ❌ Ошибка калибровки |
| `uploadFirmware()` | alert | Выберите файл прошивки (.bin) |
| `uploadFirmware()` | alert | Неверный формат файла. Ожидается .bin |
| `uploadFirmware()` | alert | Файл слишком большой (максимум 2MB) |
| `uploadFirmware()` | confirm | Обновить прошивку из файла "name" (N KB)? ⚠️ Не отключайте питание во время обновления! |
| `uploadFirmware()` | alert | ❌ Ошибка обновления (статус) |
| `uploadFirmware()` | alert | ❌ Ошибка соединения при обновлении |
| `connectToNetwork()` | alert | Выберите сеть из списка |
| `connectToNetwork()` | alert | Введите пароль сети |
| `connectToNetwork()` | alert | Пароль должен быть не менее 8 символов |
| `connectToNetwork()` | alert | ❌ (текст ошибки) |
| `connectToNetwork()` | alert | ❌ Ошибка соединения: (текст) |
| `connectToNetwork()` | alert | ⚠️ Подключение выполнено, но IP не получен. |
| `resetWiFi()` | confirm | ⚠️ Сбросить Wi-Fi настройки? Устройство перезагрузится в режим точки доступа "FLOOK32-XXXX". Пароль точки доступа: flook1234 |
| `resetWiFi()` | alert | ❌ Ошибка сброса Wi-Fi |
| `goToIp()` | alert | IP адрес не получен |
| `clearErrors()` | confirm | Очистить журнал ошибок? Это действие нельзя отменить. |
| `clearErrors()` | alert | ❌ Ошибка очистки журнала |
| `startAdaptation()` | alert | Целевая температура должна быть 40-70°C |
| `startAdaptation()` | confirm | Запустить адаптацию до N°C? Процесс займёт 15-30 минут. |
| `startAdaptation()` | alert | ❌ Ошибка запуска адаптации: (текст) |
| `abortAdaptation()` | confirm | Прервать адаптацию? Нагрев будет отключён, все данные потеряются. |
| `abortAdaptation()` | alert | ❌ Ошибка: (текст) |
| `continueAdaptation()` | alert | ❌ Ошибка: (текст) |
| `continueAdaptation()` | alert | ❌ Ошибка соединения: (текст) |
| `resetThermalModel()` | confirm | Сбросить термальную модель? |
| `resetThermalModel()` | alert | ✅ Модель сброшена |
| `resetThermalModel()` | alert | ❌ Ошибка: (текст) |
| `saveManualTimer()` | alert | Время должно быть от 30 до 600 минут |
| `saveManualTimer()` | alert | ✅ Таймер запущен! Нагрев отключится через X |
| `saveManualTimer()` | alert | Таймер выключен |
| `saveMoonrakerSettings()` | alert | Время должно быть от 5 до 120 минут |
| `saveMoonrakerSettings()` | alert | Настройки сохранены |
| `saveMoonrakerSettings()` | alert | Ошибка: (текст) |
| `saveMoonrakerSettings()` | alert | Ошибка соединения: (текст) |

</details>

---

### Реакция интерфейса

| Ситуация | Поведение |
|----------|----------|
| HTTP ошибка | alert |
| WS обрыв | офлайн баннер |
| JSON ошибка | console.error |
| неверный пароль | alert |
| Wi-Fi ошибка | сообщение + alert |
| OTA ошибка | красный статус |
| конфиг ошибка | поля пустые |

---

### Fallback стратегия

```
WS > HTTP > last data
```

```
WS ok:
  realtime

WS down:
  HTTP polling 5s
  reconnect

HTTP down:
  last values
```

---

## 💾 Локальное хранение и кэширование

### sessionStorage

| Ключ | Назначение |
|------|-----------|
| flookScreen | экран |
| flookCollapsedSections | UI состояние |

---

### Оптимизация

- chart.update()
- обновление только при изменении
- config кешируется
- Wi-Fi только при активной вкладке

<details>
<summary>📁 sessionStorage — полная схема</summary>

``` 
sessionStorage
├── flookScreen
│ └── "main" | "config" | "wifi" | "errors" | "adapt"
└── flookCollapsedSections
└── {"basic": true, "thermal": false, "runaway": true, "unexpected": false, ...}
``` 
| Ключ | Запись (setItem) | Чтение (getItem) |
|------|-----------------|-----------------|
| `flookScreen` | `showScreen()` | `DOMContentLoaded` |
| `flookCollapsedSections` | `toggleSection()` | `restoreSectionStates()` (из `loadConfig()`) |

</details>

## 🛡️ Безопасность

| Механизм | Назначение |
|----------|----------|
| unlock API | пароль вне JS |
| confirm() | защита от случайных кликов |
| OTA проверка | размер + bin |
| escapeHtml | XSS защита |

---

### Опасные операции

- heater off
- reboot
- wifi reset
- error clear
- factory reset
- adapt start/stop
- OTA
- thermal reset

## ♿ Доступность (Accessibility)

| Элемент | Реализация |
|---------|-----------|
| Семантика | `<header>`, `<nav>`, `<main>` |
| Клавиатура | `tabindex`, `role="button"` |
| Screen reader | `aria-label` |
| Контраст | тёмная тема |
| Фокус | стандарт + анимации |
| Escape | закрытие тултипов |

---

## 🎨 Система стилизации

### Цвета

| Назначение | HEX |
|-----------|-----|
| фон | #1e1e2e |
| карточки | #2a2a36 |
| границы | #3d3d4a |
| воздух | #ff8a5c |
| нагреватель | #6c5ce7 |
| цель | #00b894 |
| warning | #fdcb6e |
| danger | #d63031 |
| текст | #e4e4e7 |
| вторичный | #a0a0b0 |

---

### Брейкпоинты

| Устройство | Ширина | Изменения |
|------------|--------|----------|
| планшет | 768px | 2→1 колонки |
| телефон | 480px | 3→2 метрики |

---

### Анимации

| Элемент | Эффект |
|--------|-------|
| кнопки | scale |
| hover | translateY |
| стрелки | rotate |
| баннер | slide |
| тултипы | fade |

<details>
<summary>📁 CSS-классы</summary>
  
```
.container — центрирование  
.nav-links — навигация  
.nav-link.active — активная вкладка  
.card — карточка  
.metrics-grid — сетка  

.metric-air  
.metric-heater  
.metric-target  

.btn / .btn-primary / .btn-danger  
.quick-btn  
.preset.active  
.screen.active  
.chart-container  
.config-section  
.section-header.collapsed  
.error-item  

.severity-critical  
.severity-warning  
.severity-info  

.badge-critical  
.badge-warning  
.badge-info  

.progress-fill  
.phase-step.active  
.tooltip-content  
.offline-banner  
.footer  
```
</details>

---

## 📱 Экран адаптации

### Фазы

```javascript
const ADAPT_PHASES = [
    '',
    'Ожидание стабилизации',
    'Измерение шумов датчиков',
    'Измерение базовых параметров',
    'Калибровка вентилятора',
    'Нагрев с вентилятором',
    'ОЖИДАНИЕ ПОДТВЕРЖДЕНИЯ',
    'Нагрев камеры',
    'ЗАВЕРШЕНО',
    'ОШИБКА'
];
```

---

### Действия

| Фаза | Что происходит |
|------|--------------|
| 1 | Ожидание стабилизации всех датчиков до комнатной температуры |
| 2 | Сбор статистики шумов DS18B20 и MAX6675 в статичном состоянии |
| 3 | Включение нагревателя и измерение скорости роста температуры |
| 4 | Включение вентилятора на полную мощность и измерение эффективности охлаждения |
| 5 | Совместная работа нагревателя и вентилятора для оценки баланса |
| 6 | ОЖИДАНИЕ ПОДТВЕРЖДЕНИЯ — пауза для опускания стола и включения его нагрева |
| 7 | Финальный нагрев камеры с учётом тепла от стола |
| 8 | ЗАВЕРШЕНО — расчёт и сохранение оптимальных параметров |
| 9 | ОШИБКА — аварийное прерывание из-за нештатной ситуации |

---

### Подготовка к адаптации

**Чек-лист перед запуском:**
- [ ] Система полностью исправна, все датчики работают
- [ ] Температура в камере комнатная (20–30°C)
- [ ] Камера принтера открыта (Фаза 1)
- [ ] Нагревательный стол выключен
- [ ] Ничего не мешает работе вентилятора
- [ ] Все защиты временно отключаются на время адаптации

**На Фазе 6 (ОЖИДАНИЕ ПОДТВЕРЖДЕНИЯ):**
- [ ] Опустить нагревательный стол в самый низ камеры если это возможно
- [ ] Включить нагрев стола на 100–110°C
- [ ] Нажать «ПРОДОЛЖИТЬ АДАПТАЦИЮ»
- [ ] Закрыть камеру принтера

---

### Интерпретация результатов

После завершения адаптации система автоматически подбирает и сохраняет параметры:

| Группа параметров | Что оптимизируется |
|-------------------|-------------------|
| Базовые характеристики | Скорость нагрева, скорость прогрева воздуха, эффективность вентилятора |
| Thermal Runaway | Минимальные пороги роста температуры (40% от измеренных) |
| Неожиданный нагрев | Порог срабатывания и таймаут на основе скорости остывания |
| Вентилятор | Оптимальный duty cycle и температура включения |
| MAX6675 / DS18B20 | Уровень шума, пороги скачков и нестабильности |
| Блокировка | Количество повторных ошибок (на основе времени нагрева) |
| Автоограничение вентилятора | Минимальный duty для удержания температуры |

---

### UI структура

```
adaptReady
adaptBlocked
adaptProgress
adaptWaitingPanel
adaptComplete
adaptResults
```

---

## 🧠 Термальная модель

### Назначение

Обучаемая термальная модель — это математический предсказатель температуры, который:
- Прогнозирует температуру на 5 секунд вперёд
- Сравнивает прогноз с реальными показаниями датчиков
- Постоянно корректирует свои параметры (скорость нагрева, скорость остывания)
- Обнаруживает аномалии за 10–15 секунд вместо 5–30 минут у классических защит

### Ключевые метрики

| Метрика | Описание | Норма |
|--------|----------|-------|
| `confidence` | Уверенность модели в прогнозе | Растёт со временем, >80% |
| `error` | Отклонение прогноза от факта | <3°C |
| `heaterRate` | Скорость нагрева нагревателя | Определяется адаптацией |
| `coolingRate` | Скорость остывания с вентилятором | Определяется адаптацией |

### Алгоритм работы

```
1. Модель получает текущие температуры (воздух, нагреватель)
2. Вычисляет прогноз на +5 секунд вперёд
3. Через 5 секунд сравнивает прогноз с реальностью
4. Корректирует внутренние коэффициенты (медленно, с damping)
5. Если отклонение > порог * чувствительность → тревога
```

### Отличие от Thermal Runaway

| Характеристика | Thermal Runaway | Термальная модель |
|---------------|-----------------|-------------------|
| Время обнаружения | 5–30 минут | 10–15 секунд |
| Принцип | Статические пороги | Динамический прогноз |
| Чувствительность | Фиксированная | Настраиваемая (0.5–3.0) |
| Адаптивность | Ручная настройка | Самообучается |
| Требования | Нет | Нужна адаптация |

### Когда срабатывает модель

- Нагреватель растёт быстрее или медленнее прогноза
- Охлаждение происходит не по ожидаемому сценарию
- Вентилятор не даёт ожидаемого эффекта
- Резкое изменение скорости температуры

Отображается карточкой на главном экране при активности (`#thermalDiagnostics`).

---

## 🔍 Экран ошибок

### Формат

```json
{
  "ts": 3600,
  "msg": "Перегрев воздуха",
  "sev": "critical",
  "td": "данные",
  "count": 3
}
```

---

### Severity

```
critical → 🔥
warning → ⚠️
info → ℹ️
```

---

### Типовые ошибки и их причины

| Сообщение | Severity | Возможная причина | Рекомендация |
|-----------|----------|-------------------|--------------|
| Перегрев нагревателя | critical | Неисправен SSR, датчик, утечка воздуха | Проверить SSR и термопару |
| Перегрев воздуха | critical | Не работает вентилятор, закрыты отверстия | Проверить вентилятор |
| Thermal Runaway | critical | Нагреватель не греет, датчик отклеился | Проверить нагреватель и датчик |
| Неожиданный нагрев | critical | Залипшее реле, утечка тока | Проверить SSR |
| Сбой MAX6675 | critical | Обрыв термопары, помехи | Проверить соединения |
| Сбой DS18B20 | warning | Обрыв датчика воздуха | Проверить 1-Wire линию |
| Аномальный рост температуры | warning | Короткое замыкание, скачок напряжения | Проверить нагреватель |
| Вентилятор неэффективен | warning | Засорение, износ вентилятора | Очистить или заменить |
| Датчик воздуха нестабилен | warning | Помехи, плохой контакт | Проверить проводку |

---

### Обновление

```
/api/error-log → каждые 10с
обновление badge + title
```

---

## 💬 Сценарии

### Быстрый старт

```
открыть → выбрать температуру → таймер → авто off
```

---

### Первая настройка

```
wifi → config → unlock → adapt → готово
```

---

### Диагностика

```
ошибки → фильтр → анализ → решение
```

---

### Wi-Fi смена

```
scan → select → password → connect → IP → переход
```

---

## 🏨 Режим точки доступа (AP mode)

При загрузке страницы проверяется, работает ли устройство в режиме точки доступа:

```javascript
const isAP = location.hostname.endsWith('.4.1') || location.hostname.startsWith('192.168.4.');
```

Если `isAP === true`, интерфейс запускается в ограниченном режиме:
- Все экраны, кроме **Wi-Fi**, скрываются.
- График не инициализируется.
- WebSocket не подключается.
- Сразу показывается экран Wi-Fi и запускается сканирование сетей.

---

## 🔧 Технические детали

### Формат времени

```
3600 → ``ч``м``с
120  → ``м``с
30   → ``с
```

---

### Таймауты

| Операция | Время |
|----------|------|
| GET | 3s |
| POST | 5s |
| Wi-Fi scan | 15s |
| IP wait | 25s |
| reboot | 2s |
| OTA | 2–5s |
| WS reconnect | 3–30s |

---

### Ограничения

| Параметр | Значение |
|----------|----------|
| OTA | 2MB |
| Wi-Fi пароль | 8+ |
| температура | 0–70°C |
| таймер | 30–600 мин |
| история | 30 мин |
| точки | ~600 |

---

### Совместимость браузеров

Интерфейс использует современные Web API. Минимальные версии:

| Браузер | Версия | Ключевые API |
|---------|--------|-------------|
| Chrome | 67+ | WebSocket, fetch, AbortController |
| Firefox | 63+ | WebSocket, fetch, AbortController |
| Safari | 12.1+ | WebSocket, fetch, AbortController |
| Edge | 79+ | WebSocket, fetch, AbortController |
| Opera | 54+ | WebSocket, fetch, AbortController |

Мобильные браузеры (iOS Safari, Android Chrome) полностью поддерживаются.

---

## 📝 Примечания для разработчиков

### Сборка прошивки (кратко)

Прошивка компилируется под ESP32 (Arduino IDE). Загружается через OTA-интерфейс в браузере. Требования к файлу:
- Формат `.bin`
- Размер не более 2 МБ
- Собран для конкретной платы

### Структура `currentConfig`

Объект `currentConfig` хранит **все** параметры конфигурации под полными именами. При отправке на сервер (POST `/api/config`) используется преобразование в компактные ключи (см. карту выше). При получении с сервера — обратное преобразование.

### Добавление новой секции в настройки

1. Создать запись в `CONFIG_SECTIONS_HTML` с HTML-разметкой секции.
2. Добавить объект в массив `CONFIG_SECTIONS` с полями `id` и `title`.
3. В `loadConfig()` прочитать значение из `compact` ответа.
4. В `saveConfig()` добавить поле в `compact` для отправки.
5. Убедиться, что ID новых input/select элементов соответствуют ключам в `currentConfig`.

### Особенности WebSocket

- Клиент **не запрашивает** историю — сервер отправляет её автоматически при подключении.
- История разбивается на чанки (`history_chunk`), каждый содержит индекс, общее количество и массив точек.
- После полной загрузки истории сервер переходит к отправке инкрементальных обновлений (`history_update`).
- При реконнекте история загружается заново полностью.

[🔝 Наверх](#веб-интерфейс-flook32)

---

[🔙 На главную](../README.md)
