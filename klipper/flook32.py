# -*- coding: utf-8 -*-
#
# ============================================================================
# FLOOK32 Sensor for Klipper
# ============================================================================
# 
# Плагин для интеграции контроллера термокамеры FLOOK32 в экосистему Klipper.
# Обеспечивает двустороннюю связь: чтение температуры воздуха через REST API
# или WebSocket, управление нагревом через G-код команды, мониторинг ошибок.
#
# Copyright (C) 2026 t.me/schreid
# This program is free software under GPLv3.
# Полный текст лицензии: https://www.gnu.org/licenses/gpl-3.0.html
#
# ═══════════════════════════════════════════════════════════════════════════════
#                              ПРИНЦИП РАБОТЫ
# ═══════════════════════════════════════════════════════════════════════════════
#
# Плагин регистрирует виртуальный датчик температуры в Klipper и связывается
# с FLOOK32 в локальной сети. Температура обновляется в реальном времени через WebSocket
# (если установлен websocket-client) или периодическим HTTP-опросом (fallback).
#
# ═══════════════════════════════════════════════════════════════════
#                         РЕЖИМЫ ПОДКЛЮЧЕНИЯ
# ═══════════════════════════════════════════════════════════════════
#
# 1. РУЧНОЙ РЕЖИМ (flook_ip задан в конфиге):
#    • Плагин сразу подключается по указанному IP
#    • UDP-обнаружение не используется для подключения
#    • При первом HTTP-ответе отправляет UDP-запрос с ID устройства,
#      чтобы FLOOK32 сохранил IP Klipper для работы Moonraker
#    • При потере связи продолжает стучаться по тому же IP
#
# 2. АВТОМАТИЧЕСКИЙ РЕЖИМ (flook_ip не задан, auto_discover=True):
#    • Плагин запускает UDP-слушатель на порту 12345
#    • Отправляет broadcast-запрос FLOOK_DISCOVERY
#    • FLOOK32 отвечает с указанием TRUE/FALSE (совпадение ID)
#    • При первом запуске выбирает устройство с наименьшим uptime
#    • Сохраняет ID устройства для последующих подключений
#    • При потере связи перезапускает UDP-поиск
#
# ═══════════════════════════════════════════════════════════════════
#                    ПЕРЕДАЧА ТЕМПЕРАТУРЫ
# ═══════════════════════════════════════════════════════════════════
#
# 1. WEBSOCKET (приоритетный):
#    • Данные поступают в реальном времени (каждую секунду)
#    • Формат: JSON с полями a (воздух), h (нагреватель), tg (цель)
#    • Автоматическое переподключение при обрыве
#    • При активном WebSocket HTTP-опрос НЕ выполняется
#
# 2. HTTP POLLING (fallback):
#    • Периодический запрос GET /api/all
#    • Интервал: report_interval (5-60 сек, по умолчанию 10)
#    • Используется когда WebSocket недоступен или не установлен
#
# ═══════════════════════════════════════════════════════════════════
#                    UDP ОБНАРУЖЕНИЕ (ПРОТОКОЛ)
# ═══════════════════════════════════════════════════════════════════
#
# Формат запроса (плагин → FLOOK32):
#   FLOOK_DISCOVERY:<device_id>   — с указанием ID (если сохранён)
#   FLOOK_DISCOVERY               — без ID (первый запуск)
#
# Формат ответа (FLOOK32 → плагин):
#   FLOOK32:TRUE:<IP>:<uptime>:<T_air>:<device_id>   — ID совпал
#   FLOOK32:FALSE:<IP>:<uptime>:<T_air>:<device_id>  — ID не совпал
#   FLOOK32:<IP>:<uptime>:<T_air>:<device_id>        — старый формат (без ID)
#
# Логика выбора устройства:
#   • Если сохранён ID → подключается ТОЛЬКО к устройству с TRUE и совпадающим ID
#   • Если ID не сохранён → выбирает устройство с TRUE и наименьшим uptime
#   • Если все устройства ответили FALSE → активный поиск с указанием ID
#
# ═══════════════════════════════════════════════════════════════════
#                    СОХРАНЕНИЕ ID УСТРОЙСТВА
# ═══════════════════════════════════════════════════════════════════
#
# ID устройства сохраняется для того, чтобы при следующем запуске
# плагин мог подключиться к ТОМУ ЖЕ FLOOK32, а не к случайному.
# Это критично если в сети несколько принтеров с FLOOK32.
#
# Места хранения (в порядке приоритета):
#   1. Moonraker DB (http://localhost:7125/server/database/item)
#   2. Файл ~/.flook32_id (если Moonraker недоступен)
#
# Сброс ID: команда FLOOK_RESET_ID в консоли Klipper
#
# ═══════════════════════════════════════════════════════════════════
#                    ОТПРАВКА КОНФИГУРАЦИИ
# ═══════════════════════════════════════════════════════════════════
#
# При первом успешном подключении плагин отправляет на FLOOK32
# ВСЕ параметры, явно заданные в printer.cfg. Это позволяет
# настроить устройство прямо из конфига Klipper.
#
# ВАЖНО: отправляются ТОЛЬКО явно заданные параметры.
# Параметры, не указанные в конфиге, остаются без изменений
# на устройстве (значения по умолчанию или предыдущие настройки).
#
# ═══════════════════════════════════════════════════════════════════
#                    МОНИТОРИНГ ОШИБОК
# ═══════════════════════════════════════════════════════════════════
#
# Плагин периодически запрашивает /api/error-log и выводит
# критические ошибки FLOOK32 в консоль Klipper с рекомендациями
# по устранению.
#
# Настройки:
#   • enable_error_notifications — вкл/выкл мониторинг
#   • error_check_interval — периодичность проверки (15-120 сек)
#   • error_notification_max_age — максимальный возраст ошибки
#   • show_trends — показывать тренды температур перед ошибкой
#
# ═══════════════════════════════════════════════════════════════════
#                    G-CODE КОМАНДЫ
# ═══════════════════════════════════════════════════════════════════
#
# Плагин регистрирует 17 G-код команд для управления FLOOK32
# прямо из консоли Klipper. Полный список в разделе G-CODE КОМАНДЫ.
#
# ═══════════════════════════════════════════════════════════════════
#
# ПРИМЕР КОНФИГУРАЦИИ:
#   [flook32]
#   
#   [temperature_sensor chamber]
#   sensor_type: flook32
#   flook_ip: 192.168.1.37
#
# УСТАНОВКА:
#   1. Скопируйте flook32.py в ~/klipper/klippy/extras/             
#   2. Установите websocket-client (опционально):                   
#      pip install websocket-client 
#   3. Скопируйте файл flook32.cfg в папку с printer.cfg
#   4. Добавьте [include flook32.cfg] в printer.cfg                    
#   5. Перезапустите Klipper   
#
# ЗАВИСИМОСТИ:
#   • Стандартная библиотека Python (всегда есть):
#       - socket, json, threading, select, time, logging, os
#   • websocket-client — ОПЦИОНАЛЬНО:
#       - Для real-time обновлений температуры
#       - Установка: pip install websocket-client
#       - Без него работает через HTTP polling
#   • requests — ОПЦИОНАЛЬНО:
#       - Для сохранения ID в Moonraker DB
#       - Установка: pip install requests
#       - Без него ID сохраняется в файл ~/.flook32_id
#       - Работа плагина не нарушается
#
# АВТОР: t.me/schreid
# ВЕРСИЯ: 0.1.0b
# ============================================================================

# ============================================================================
# ИМПОРТЫ
# ============================================================================

# Стандартная библиотека Python — всегда доступна, не требует установки
import socket                   # UDP/TCP сокеты для связи с FLOOK32
import time                     # Таймеры, задержки, метки времени
import threading                # Параллельные потоки: UDP слушатель, WebSocket
import logging                  # Логирование в klippy.log (основной лог Klipper)
import json                     # Парсинг JSON ответов от FLOOK32 API
import select                   # Неблокирующий опрос UDP сокета (select/poll)
import os                       # Работа с файловой системой (чтение/запись ~/.flook32_id)
import sys                      # Системные функции (пути, версия Python)

# ============================================================================
# ОПЦИОНАЛЬНЫЕ ЗАВИСИМОСТИ
# ============================================================================
# Эти библиотеки не обязательны — плагин работает и без них.
# Они подключаются динамически через try/except, чтобы избежать
# ошибок импорта при запуске Klipper.

# WebSocket client — обеспечивает real-time обновление температуры.
# Установка: pip install websocket-client
# Если не установлен — плагин использует HTTP-опрос (медленнее).
try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

# Requests — используется для сохранения ID устройства в Moonraker DB.
# Входит в стандартную поставку Python в окружении Klipper.
# Если недоступен — ID сохраняется только в файл ~/.flook32_id.
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

# Температурные пределы для сенсора Klipper.
# Выход за эти границы считается ошибкой датчика.
MIN_TEMP = -100.0              # Минимальная отображаемая температура (°C)
MAX_TEMP = 200.0               # Максимальная отображаемая температура (°C)

# UDP-обнаружение FLOOK32 в локальной сети.
# Порт должен совпадать с UDP_PORT в прошивке FLOOK32.
UDP_PORT = 12345               # Порт для отправки и приёма UDP-пакетов
UDP_BROADCAST_IP = "255.255.255.255"  # Широковещательный адрес (все устройства в сети)

# ============================================================================
# КОМПАКТНОЕ ОТОБРАЖЕНИЕ ПАРАМЕТРОВ (COMPACT MAPPING)
# ============================================================================
# 
# При отправке конфигурации на FLOOK32 через POST /api/config каждый параметр
# передаётся в JSON с коротким ключом (2-4 символа) для экономии трафика и
# размера пакета. Этот словарь сопоставляет полные имена параметров из
# printer.cfg с короткими ключами API FLOOK32.
#
# Пример:
#   printer.cfg:        max_heater_temp: 100.0
#   Короткий ключ:      mt
#   JSON на FLOOK32:    {"mt": 100.0}
#
# Используется в _send_config_to_esp() при формировании JSON для отправки.

compact_mapping = {
    # ========== ТЕМПЕРАТУРНЫЕ ПОРОГИ ==========
    'max_heater_temp': 'mt',              # Макс. температура нагревателя (°C)
    'critical_temp': 'ct',                # Критическая температура (°C)
    'critical_hysteresis': 'ch',          # Гистерезис сброса перегрева (°C)
    'max_air_temp': 'ma',                 # Макс. температура воздуха (°C)
    'air_hysteresis': 'ah',              # Гистерезис перегрева воздуха (°C)
    'hysteresis': 'hy',                  # Гистерезис управления по воздуху (°C)
    'heater_hysteresis': 'hh',           # Гистерезис нагревателя (°C)
    'enable_heater_hysteresis': 'eH',    # Включить управление по нагревателю (bool)
    'default_target_temp': 'dt',         # Целевая температура по умолчанию (°C)
    'invert_heater_signal': 'iH',        # Инвертировать сигнал SSR (bool)
    'invert_fan_signal': 'iF',           # Инвертировать сигнал вентилятора (bool)
    'max_fan_duty': 'mFD',               # Макс. мощность вентилятора (0-1023)
    
    # ========== ВЕНТИЛЯТОР ==========
    'fan_on_temp': 'fT',                 # Температура включения вентилятора (°C)
    'fan_off_hysteresis': 'fH',          # Гистерезис выключения вентилятора (°C)
    'fan_min_on_time': 'fM',             # Мин. время работы (сек)
    'fan_efficiency_timeout': 'fE',      # Таймаут проверки эффективности (сек)
    'fan_efficiency_threshold': 'fF',    # Порог эффективности (°C)
    'enable_fan_efficiency_check': 'eF', # Включить проверку эффективности (bool)
    
    # ========== THERMAL RUNAWAY (ЧЕТЫРЁХФАЗНАЯ ЗАЩИТА) ==========
    'enable_thermal_runaway': 'tR',      # Включить защиту (bool)
    'runaway_phase1_time': 'r1',         # Длительность фазы 1 (мин)
    'runaway_phase2_time': 'r2',         # Длительность фазы 2 (мин)
    'runaway_max_time_to_target': 'rT',  # Макс. время до цели (мин)
    'runaway_quick_check_temp': 'rQC',   # Фаза 0: мин. температура нагревателя через 45 сек (°C)
    'runaway_min_heater_rise': 'rH',     # Мин. рост нагревателя (°C/мин)
    'runaway_min_air_rise': 'rA',        # Мин. рост воздуха (°C/мин)
    'runaway_max_heater_drop': 'rD',     # Макс. падение нагревателя (°C)
    'runaway_hysteresis': 'rY',          # Гистерезис срабатывания (°C)
    'runaway_recovery_timeout': 'rR',    # Таймаут восстановления (сек)
    'runaway_fan_on': 'rF',              # Включить вентилятор при срабатывании (bool)
    
    # ========== UNEXPECTED HEAT (НЕОЖИДАННЫЙ НАГРЕВ) ==========
    'enable_unexpected_heat': 'uH',      # Включить защиту (bool)
    'unexpected_heat_timeout': 'uT',     # Таймаут ожидания (сек)
    'unexpected_heat_threshold': 'uP',   # Порог срабатывания (°C)
    'min_cooling_rate': 'mC',            # Мин. скорость охлаждения (°C/сек)
    'unexpected_heat_hysteresis': 'uY',  # Гистерезис сброса (°C)
    'unexpected_heat_clear_time': 'uC',  # Время автосброса (мс)
    'unexpected_heat_safe_offset': 'uS', # Безопасный отступ (°C)
    'enable_unexpected_heat_adaptive': 'uA', # Адаптивный порог (bool)
    'adaptive_base_temp': 'aB',          # Базовая температура (°C)
    'adaptive_coefficient': 'aC',        # Коэффициент адаптации
    'adaptive_min_offset': 'aM',         # Мин. адаптивный отступ (°C)
    
    # ========== КОНТРОЛЬ СКОРОСТИ РОСТА ==========
    'enable_abnormal_rate': 'eA',        # Включить контроль (bool)
    'abnormal_rate_threshold': 'aT',     # Порог аномальной скорости (°C/сек)
    
    # ========== MAX6675 (ТЕРМОПАРА) ==========
    'max6675_offset': 'mO',              # Калибровочное смещение (°C)
    'enable_max6675_protection': 'mP',   # Включить защиту датчика (bool)
    'max6675_stability_samples': 'mS',   # Сэмплов для стабильности
    'max6675_temp_jump_threshold': 'mJ', # Порог скачка температуры (°C)
    'max6675_min_temp': 'mN',            # Мин. допустимая температура (°C)
    'max6675_max_temp': 'mX',            # Макс. допустимая температура (°C)
    
    # ========== DS18B20 (ДАТЧИК ВОЗДУХА) ==========
    'ds18b20_offset': 'dO',              # Калибровочное смещение (°C)
    'ds18b20_scale': 'dS',               # Масштабирующий коэффициент
    'ds18b20_cal_enabled': 'dC',         # Включить калибровку (bool)
    'enable_air_sensor_protection': 'aP',# Включить защиту датчика (bool)
    'air_sensor_stability_samples': 'aS',# Сэмплов для стабильности
    'air_sensor_temp_jump_threshold': 'aJ', # Порог скачка (°C)
    'air_sensor_min_temp': 'aN',         # Мин. температура (°C)
    'air_sensor_max_temp': 'aX',         # Макс. температура (°C)
    'air_sensor_unstable_range': 'aU',   # Диапазон нестабильности (°C)
    'air_sensor_unstable_deviation': 'aV', # Отклонение (°C)
    'air_sensor_unstable_window': 'aW',  # Окно анализа (измерений)
    'air_sensor_direction_changes': 'aD',# Смены направления
    
    # ========== ОШИБКИ И БЛОКИРОВКИ ==========
    'max_error_retries': 'mR',           # Макс. повторов до блокировки
    'error_window_minutes': 'eW',        # Окно подсчёта ошибок (мин)
    'min_time_between_same_errors': 'mE',# Мин. время между ошибками (мс)
    'min_time_between_overheat_counts': 'mOc', # Мин. время между перегревами (мс)
    'unlock_password': 'uPw',            # Пароль разблокировки
    'settings_locked': 'sl',             # Блокировка настроек (bool)
    
    # ========== LED ИНДИКАЦИЯ ==========
    'led_enabled': 'lE',                 # Включить LED (bool)
    'led_count': 'lC',                   # Количество светодиодов
    'led_brightness': 'lB',              # Яркость (0-255)
    'led_pin': 'lP',                     # Пин LED
    
    # ========== HEARTBEAT (СТОРОЖЕВОЙ ТАЙМЕР) ==========
    'heartbeat_pulse_ms': 'hP',          # Длительность импульса (мс)
    'heartbeat_pause_ms': 'hQ',          # Пауза между импульсами (мс)
    
    # ========== СИСТЕМНЫЕ ИНТЕРВАЛЫ ==========
    'read_interval': 'rI',               # Интервал чтения датчиков (мс)
    'control_interval': 'cI',            # Основной цикл управления (мс)
    'trend_interval': 'tI',              # Интервал сохранения трендов (мс)
    'heap_check_interval': 'hI',         # Интервал проверки памяти (мс)
    'loop_watchdog_timeout': 'lW',       # Таймаут Task Watchdog (мс)
    'enable_loop_watchdog': 'eL',        # Включить Watchdog (bool)
    'udp_discovery_timeout': 'uD',       # Таймаут UDP поиска (мс)
    'discovery_retry_interval': 'dR',    # Интервал повтора UDP (мс)
    
    # ========== АВТООТКЛЮЧЕНИЕ ПО MOONRAKER ==========
    'auto_shutdown_enabled': 'aSd',      # Включить автоотключение (bool)
    'auto_shutdown_minutes': 'aSm',      # Минут ожидания после печати
    
    # ========== ТЕРМАЛЬНАЯ МОДЕЛЬ ==========
    'enable_thermal_model': 'tM',        # Включить модель (bool)
    'thermal_model_sensitivity': 'tS',   # Чувствительность (0.5-3.0)
    'thermal_model_check_interval': 'tC',# Интервал проверки (мс)
    'thermal_model_log_warnings': 'tL',  # Логировать предупреждения (bool)
    
    # ========== АППАРАТНЫЕ ПИНЫ ==========
    'pin_ssr': 'pS',                     # Пин SSR (нагреватель)
    'pin_fan': 'pF',                     # Пин вентилятора (ШИМ)
    'pin_watchdog': 'pW',                # Пин Watchdog (heartbeat)
    'pin_onewire': 'pO',                 # Пин OneWire (DS18B20)
    'pin_max_sck': 'pK',                 # Пин MAX6675 SCK
    'pin_max_so': 'pM',                  # Пин MAX6675 SO
    'pin_max_cs': 'pC',                  # Пин MAX6675 CS
    'pin_buzzer': 'pB',                  # Пин зуммера
    'pin_led': 'pL',                     # Пин LED
    
    # ========== ИНТЕРВАЛЫ УПРАВЛЕНИЯ ==========
    'heater_control_interval': 'hC',     # Интервал управления нагревателем (мс)
    'fan_control_interval': 'fC',        # Интервал управления вентилятором (мс)
    'runaway_check_interval': 'rC',      # Интервал проверки Runaway (мс)
    'unexpected_check_interval': 'uCc',  # Интервал проверки Unexpected Heat (мс)
    'rate_check_interval': 'rAc',        # Интервал проверки скорости роста (мс)
    
    # ========== АВТООГРАНИЧЕНИЕ ВЕНТИЛЯТОРА ==========
    'enable_fan_auto_limit': 'eFAL',     # Включить автоограничение (bool)
    'fan_auto_limit_hysteresis': 'fALH', # Гистерезис автоограничения (°C)
    'fan_auto_limit_adjust_step': 'fALA',# Шаг изменения duty
    'fan_auto_limit_min_duty': 'fALM',   # Минимальный duty
    'fan_auto_limit_check_interval': 'fALI', # Интервал проверки (мс)
    'fan_auto_limit_stable_count': 'fALS',# Замеров для стабилизации
    'fan_auto_limit_adapted': 'fALAd',   # Флаг адаптации автоограничения (bool)
    
    # ========== ЗУММЕР ==========
    'buzzer_enabled': 'bE',              # Включить зуммер (bool)
    'buzzer_non_critical_enabled': 'bN', # Сигнал на некритичные ошибки (bool)
    'buzzer_melody': 'bM',               # Мелодия (0=короткий, 1=двойной, 2=тревога)
}

# ============================================================================
# ОСНОВНОЙ КЛАСС СЕНСОРА
# ============================================================================

class FLOOK32Sensor:
    """
    Сенсор температуры камеры 3D-принтера, интегрированный с контроллером FLOOK32.
    
    Класс реализует интерфейс сенсора Klipper и обеспечивает:
      - Автоматическое обнаружение FLOOK32 в локальной сети через UDP broadcast
      - Чтение температуры воздуха в реальном времени (WebSocket или HTTP)
      - Управление нагревом через G-код команды (17 команд)
      - Мониторинг ошибок FLOOK32 с выводом в консоль Klipper
      - Отправку пользовательской конфигурации на устройство
    
    Режимы подключения:
      1. РУЧНОЙ (flook_ip задан) — прямое подключение по указанному IP
      2. АВТОМАТИЧЕСКИЙ (auto_discover=True) — поиск через UDP broadcast
    
    Передача данных (в порядке приоритета):
      1. WebSocket — real-time обновления (если установлен websocket-client)
      2. HTTP polling — периодические запросы (интервал: report_interval)
    """
    
    def __init__(self, config):
        """
        Инициализация сенсора при загрузке плагина Klipper.
        
        Параметры:
          config — объект конфигурации Klipper, содержащий все настройки из printer.cfg
        
        Порядок инициализации:
          1. Загрузка базовых параметров подключения (IP, порт, режим)
          2. Загрузка ВСЕХ параметров конфигурации (температуры, защиты, пины, ...)
          3. Определение явно заданных параметров (для отправки на устройство)
          4. Инициализация переменных состояния (температуры, флаги, счётчики)
          5. Загрузка сохранённого ID устройства
          6. Регистрация G-код команд
          7. Запуск фоновых потоков (UDP-слушатель, цикл опроса)
        """
        
        # =====================================================================
        # БАЗОВАЯ ИНИЦИАЛИЗАЦИЯ
        # =====================================================================
        
        # Объект принтера Klipper — точка входа во всю систему
        self.printer = config.get_printer()
        # Реактор — планировщик задач Klipper (используется для таймеров)
        self.reactor = self.printer.get_reactor()
        # Имя датчика — последняя часть имени секции (например, "chamber")
        self.name = config.get_name().split()[-1]
        
        logging.info("=" * 60)
        logging.info("FLOOK32 датчик '{}' инициализация (режим: air)".format(self.name))
        logging.info("=" * 60)
        
        # =====================================================================
        # ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ
        # =====================================================================
        
        # IP адрес FLOOK32 в локальной сети
        # Если не задан — будет использоваться автообнаружение через UDP
        self.flook_ip = config.get('flook_ip', None)
        # HTTP/WebSocket порт (по умолчанию 80)
        self.flook_port = config.getint('flook_port', 80)
        
        # Определяем режим подключения
        if self.flook_ip:
            # РУЧНОЙ РЕЖИМ: IP указан явно, автообнаружение не требуется
            self.auto_discover = False
            logging.info("Ручной режим, IP={}:{}".format(self.flook_ip, self.flook_port))
        else:
            # АВТОМАТИЧЕСКИЙ РЕЖИМ: IP не задан, ищем через UDP
            self.auto_discover = config.getboolean('auto_discover', True)
            logging.info("Автоматический режим, авто-поиск={}".format(
                'включен' if self.auto_discover else 'выключен'))
        
        # =====================================================================
        # ПАРАМЕТРЫ ОПРОСА И УВЕДОМЛЕНИЙ
        # =====================================================================
        
        # Тихий режим — отключает ВСЕ сообщения в консоль Klipper
        # (логирование в файл продолжается независимо от этого параметра)
        self.silent_mode = config.getboolean('silent', False)
        if self.silent_mode:
            logging.info("Тихий режим включен")
        
        # Интервал HTTP-опроса (используется ТОЛЬКО когда WebSocket недоступен)
        # Диапазон: 5-60 секунд, по умолчанию 10 секунд
        self.report_interval = config.getfloat('report_interval', 10.0, minval=5.0, maxval=60.0)
        logging.info("Интервал отчета = {} сек".format(self.report_interval))
        
        # =====================================================================
        # НАСТРОЙКИ АВТОУВЕДОМЛЕНИЙ ОБ ОШИБКАХ
        # =====================================================================
        
        # Включить/выключить мониторинг ошибок FLOOK32
        self.enable_error_notifications = config.getboolean('enable_error_notifications', True)
        # Максимальный возраст ошибки для вывода (сек). 0 = без ограничений
        self.error_notification_max_age = config.getint('error_notification_max_age', 600, minval=0, maxval=86400)
        # Периодичность проверки API ошибок (сек)
        self.error_check_interval = config.getint('error_check_interval', 30, minval=15, maxval=120)
        # Показывать тренды температур перед ошибкой
        self.show_trends = config.getboolean('show_trends', True)
        # Максимальное количество строк трендов (0 = все)
        self.max_trend_lines = config.getint('max_trend_lines', 30, minval=0, maxval=100)
        
        if self.enable_error_notifications:
            logging.info("Автоуведомления об ошибках: ВКЛЮЧЕНЫ")
        else:
            logging.info("Автоуведомления об ошибках: ОТКЛЮЧЕНЫ")
        
        # =====================================================================
        # ЗАГРУЗКА ВСЕХ ПАРАМЕТРОВ КОНФИГУРАЦИИ
        # =====================================================================
        # Каждый параметр имеет значение по умолчанию, диапазон допустимых значений
        # и подробное описание в printer.cfg.
        # Здесь они загружаются в атрибуты объекта для использования в методах.
        
        # --- ПАРАМЕТРЫ НАГРЕВАТЕЛЯ ---
        self.max_heater_temp = config.getfloat('max_heater_temp', 100.0, minval=30, maxval=300)
        self.critical_temp = config.getfloat('critical_temp', 110.0, minval=40, maxval=350)
        self.critical_hysteresis = config.getfloat('critical_hysteresis', 5.0, minval=0.1, maxval=50)
        self.max_air_temp = config.getfloat('max_air_temp', 70.0, minval=20, maxval=200)
        self.air_hysteresis = config.getfloat('air_hysteresis', 3.0, minval=0.1, maxval=50)
        self.hysteresis = config.getfloat('hysteresis', 0.5, minval=0.1, maxval=5.0)
        self.heater_hysteresis = config.getfloat('heater_hysteresis', 4.0, minval=1.0, maxval=30.0)
        self.enable_heater_hysteresis = config.getboolean('enable_heater_hysteresis', True)
        self.default_target_temp = config.getfloat('default_target_temp', 0.0, minval=0, maxval=100)
        self.invert_heater_signal = config.getboolean('invert_heater_signal', False)
        self.max_fan_duty = config.getint('max_fan_duty', 1023, minval=0, maxval=1023)
        
        # --- ПАРАМЕТРЫ ВЕНТИЛЯТОРА ---
        self.fan_on_temp = config.getfloat('fan_on_temp', 55.0, minval=0, maxval=120)
        self.fan_off_hysteresis = config.getfloat('fan_off_hysteresis', 3.0, minval=1, maxval=30)
        self.fan_min_on_time = config.getint('fan_min_on_time', 30, minval=10, maxval=300)
        self.invert_fan_signal = config.getboolean('invert_fan_signal', False)
        self.fan_efficiency_timeout = config.getfloat('fan_efficiency_timeout', 120.0, minval=30, maxval=600)
        self.fan_efficiency_threshold = config.getfloat('fan_efficiency_threshold', 2.0, minval=0.5, maxval=20)
        self.enable_fan_efficiency_check = config.getboolean('enable_fan_efficiency_check', True)
        self.enable_fan_auto_limit = config.getboolean('enable_fan_auto_limit', False)
        self.fan_auto_limit_hysteresis = config.getfloat('fan_auto_limit_hysteresis', 3.0, minval=0.5, maxval=10)
        self.fan_auto_limit_adjust_step = config.getint('fan_auto_limit_adjust_step', 10, minval=1, maxval=20)
        self.fan_auto_limit_min_duty = config.getint('fan_auto_limit_min_duty', 400, minval=0, maxval=1023)
        self.fan_auto_limit_check_interval = config.getint('fan_auto_limit_check_interval', 5000, minval=1000, maxval=30000)
        self.fan_auto_limit_stable_count = config.getint('fan_auto_limit_stable_count', 3, minval=1, maxval=10)
        
        # --- THERMAL RUNAWAY (ЧЕТЫРЁХФАЗНАЯ ЗАЩИТА) ---
        self.enable_thermal_runaway = config.getboolean('enable_thermal_runaway', True)
        self.runaway_phase1_time = config.getint('runaway_phase1_time', 5, minval=1, maxval=30)
        self.runaway_phase2_time = config.getint('runaway_phase2_time', 15, minval=5, maxval=60)
        self.runaway_max_time_to_target = config.getfloat('runaway_max_time_to_target', 30.0, minval=10, maxval=120)
        self.runaway_min_heater_rise = config.getfloat('runaway_min_heater_rise', 2.0, minval=0.5, maxval=30)
        self.runaway_min_air_rise = config.getfloat('runaway_min_air_rise', 0.5, minval=0.1, maxval=10)
        self.runaway_max_heater_drop = config.getfloat('runaway_max_heater_drop', 15.0, minval=5, maxval=50)
        self.runaway_hysteresis = config.getfloat('runaway_hysteresis', 2.0, minval=0.5, maxval=10)
        self.runaway_recovery_timeout = config.getint('runaway_recovery_timeout', 30, minval=10, maxval=300)
        self.runaway_fan_on = config.getboolean('runaway_fan_on', False)
        self.runaway_quick_check_temp = config.getfloat('runaway_quick_check_temp', 60.0, minval=20, maxval=200)
        
        # --- UNEXPECTED HEAT (НЕОЖИДАННЫЙ НАГРЕВ) ---
        self.enable_unexpected_heat = config.getboolean('enable_unexpected_heat', True)
        self.unexpected_heat_timeout = config.getfloat('unexpected_heat_timeout', 45.0, minval=5, maxval=300)
        self.unexpected_heat_threshold = config.getfloat('unexpected_heat_threshold', 15.0, minval=5, maxval=50)
        self.min_cooling_rate = config.getfloat('min_cooling_rate', 1.0, minval=0.01, maxval=20)
        self.unexpected_heat_hysteresis = config.getfloat('unexpected_heat_hysteresis', 3.0, minval=0.5, maxval=20)
        self.unexpected_heat_clear_time = config.getint('unexpected_heat_clear_time', 30000, minval=5000, maxval=600000)
        self.unexpected_heat_safe_offset = config.getfloat('unexpected_heat_safe_offset', 10.0, minval=5, maxval=50)
        self.enable_unexpected_heat_adaptive = config.getboolean('enable_unexpected_heat_adaptive', False)
        self.adaptive_base_temp = config.getfloat('adaptive_base_temp', 20.0, minval=10, maxval=40)
        self.adaptive_coefficient = config.getfloat('adaptive_coefficient', 0.3, minval=0, maxval=1)
        self.adaptive_min_offset = config.getfloat('adaptive_min_offset', 30.0, minval=10, maxval=100)
        
        # --- КОНТРОЛЬ АНОМАЛЬНОЙ СКОРОСТИ РОСТА ---
        self.enable_abnormal_rate = config.getboolean('enable_abnormal_rate', True)
        self.abnormal_rate_threshold = config.getfloat('abnormal_rate_threshold', 5.0, minval=0.5, maxval=50)
        
        # --- MAX6675 (ТЕРМОПАРА) ---
        self.max6675_offset = config.getfloat('max6675_offset', 0.0, minval=-50, maxval=50)
        self.enable_max6675_protection = config.getboolean('enable_max6675_protection', True)
        self.max6675_stability_samples = config.getint('max6675_stability_samples', 3, minval=1, maxval=10)
        self.max6675_temp_jump_threshold = config.getfloat('max6675_temp_jump_threshold', 20.0, minval=5, maxval=100)
        self.max6675_min_temp = config.getfloat('max6675_min_temp', -50.0, minval=-100, maxval=0)
        self.max6675_max_temp = config.getfloat('max6675_max_temp', 400.0, minval=100, maxval=1000)
        
        # --- DS18B20 (ДАТЧИК ВОЗДУХА) ---
        self.ds18b20_offset = config.getfloat('ds18b20_offset', 0.0, minval=-10, maxval=10)
        self.ds18b20_scale = config.getfloat('ds18b20_scale', 1.0, minval=0.9, maxval=1.1)
        self.ds18b20_cal_enabled = config.getboolean('ds18b20_cal_enabled', False)
        self.enable_air_sensor_protection = config.getboolean('enable_air_sensor_protection', True)
        self.air_sensor_stability_samples = config.getint('air_sensor_stability_samples', 5, minval=3, maxval=20)
        self.air_sensor_temp_jump_threshold = config.getfloat('air_sensor_temp_jump_threshold', 2.0, minval=1, maxval=50)
        self.air_sensor_min_temp = config.getfloat('air_sensor_min_temp', -40.0, minval=-100, maxval=0)
        self.air_sensor_max_temp = config.getfloat('air_sensor_max_temp', 125.0, minval=50, maxval=200)
        self.air_sensor_unstable_range = config.getfloat('air_sensor_unstable_range', 3.0, minval=0.5, maxval=20)
        self.air_sensor_unstable_deviation = config.getfloat('air_sensor_unstable_deviation', 1.5, minval=0.1, maxval=10)
        self.air_sensor_unstable_window = config.getint('air_sensor_unstable_window', 10, minval=3, maxval=50)
        self.air_sensor_direction_changes = config.getint('air_sensor_direction_changes', 3, minval=1, maxval=20)
        
        # --- СИСТЕМА ОШИБОК И БЛОКИРОВОК ---
        self.max_error_retries = config.getint('max_error_retries', 3, minval=1, maxval=20)
        self.error_window_minutes = config.getint('error_window_minutes', 10, minval=1, maxval=240)
        self.min_time_between_same_errors = config.getint('min_time_between_same_errors', 30000, minval=1000, maxval=300000)
        self.min_time_between_overheat_counts = config.getint('min_time_between_overheat_counts', 5000, minval=1000, maxval=60000)
        self.unlock_password = config.get('unlock_password', 'unlock')
        self.settings_locked = config.getboolean('settings_locked', True)
        
        # --- LED ИНДИКАЦИЯ ---
        self.led_enabled = config.getboolean('led_enabled', True)
        self.led_count = config.getint('led_count', 3, minval=1, maxval=100)
        self.led_brightness = config.getint('led_brightness', 50, minval=0, maxval=255)
        self.led_pin = config.getint('led_pin', 27, minval=0, maxval=39)
        
        # --- HEARTBEAT (СТОРОЖЕВОЙ ТАЙМЕР) ---
        self.heartbeat_pulse_ms = config.getint('heartbeat_pulse_ms', 100, minval=10, maxval=1000)
        self.heartbeat_pause_ms = config.getint('heartbeat_pause_ms', 900, minval=100, maxval=10000)
        
        # --- СИСТЕМНЫЕ ИНТЕРВАЛЫ ---
        self.read_interval = config.getint('read_interval', 1000, minval=100, maxval=5000)
        self.control_interval = config.getint('control_interval', 3000, minval=1000, maxval=30000)
        self.trend_interval = config.getint('trend_interval', 5000, minval=500, maxval=10000)
        self.heap_check_interval = config.getint('heap_check_interval', 30000, minval=5000, maxval=60000)
        self.loop_watchdog_timeout = config.getint('loop_watchdog_timeout', 30000, minval=5000, maxval=60000)
        self.enable_loop_watchdog = config.getboolean('enable_loop_watchdog', True)
        self.udp_discovery_timeout = config.getint('udp_discovery_timeout', 30000, minval=5000, maxval=60000)
        self.discovery_retry_interval = config.getint('discovery_retry_interval', 1000, minval=500, maxval=10000)
        
        # --- АВТООТКЛЮЧЕНИЕ ПО MOONRAKER ---
        self.auto_shutdown_enabled = config.getboolean('auto_shutdown_enabled', False)
        self.auto_shutdown_minutes = config.getint('auto_shutdown_minutes', 30, minval=5, maxval=120)
        
        # --- ТЕРМАЛЬНАЯ МОДЕЛЬ ---
        self.enable_thermal_model = config.getboolean('enable_thermal_model', False)
        self.thermal_model_sensitivity = config.getfloat('thermal_model_sensitivity', 1.0, minval=0.5, maxval=3.0)
        self.thermal_model_check_interval = config.getint('thermal_model_check_interval', 2000, minval=500, maxval=10000)
        self.thermal_model_log_warnings = config.getboolean('thermal_model_log_warnings', True)
        
        # --- АППАРАТНЫЕ ПИНЫ ---
        self.pin_ssr = config.getint('pin_ssr', 32, minval=0, maxval=39)
        self.pin_fan = config.getint('pin_fan', 33, minval=0, maxval=39)
        self.pin_watchdog = config.getint('pin_watchdog', 26, minval=0, maxval=39)
        self.pin_onewire = config.getint('pin_onewire', 21, minval=0, maxval=39)
        self.pin_max_sck = config.getint('pin_max_sck', 18, minval=0, maxval=39)
        self.pin_max_so = config.getint('pin_max_so', 19, minval=0, maxval=39)
        self.pin_max_cs = config.getint('pin_max_cs', 5, minval=0, maxval=39)
        self.pin_buzzer = config.getint('pin_buzzer', 25, minval=0, maxval=39)
        self.pin_led = config.getint('pin_led', 27, minval=0, maxval=39)
        
        # --- ДОПОЛНИТЕЛЬНЫЕ ИНТЕРВАЛЫ УПРАВЛЕНИЯ ---
        self.heater_control_interval = config.getint('heater_control_interval', 200, minval=50, maxval=1000)
        self.fan_control_interval = config.getint('fan_control_interval', 1000, minval=500, maxval=5000)
        self.runaway_check_interval = config.getint('runaway_check_interval', 5000, minval=1000, maxval=30000)
        self.unexpected_check_interval = config.getint('unexpected_check_interval', 2000, minval=500, maxval=10000)
        self.rate_check_interval = config.getint('rate_check_interval', 1000, minval=500, maxval=5000)
        
        # --- ЗУММЕР ---
        self.buzzer_enabled = config.getboolean('buzzer_enabled', True)
        self.buzzer_non_critical_enabled = config.getboolean('buzzer_non_critical_enabled', False)
        self.buzzer_melody = config.getint('buzzer_melody', 1, minval=0, maxval=2)
        
        # =====================================================================
        # ОПРЕДЕЛЕНИЕ ЯВНО ЗАДАННЫХ ПАРАМЕТРОВ
        # =====================================================================
        # Параметры, НЕ входящие в этот список, считаются "явно заданными"
        # и будут отправлены на FLOOK32 при первом подключении.
        connection_params = ['flook_ip', 'flook_port', 'auto_discover', 'sensor_type', 
                           'sensor_mode', 'min_temp', 'max_temp', 'report_interval',
                           'enable_error_notifications', 'error_notification_max_age', 
                           'error_check_interval', 'silent', 'show_trends', 'max_trend_lines']
        
        self._explicit_params = {}
        
        if hasattr(config, 'get_prefix_options'):
            for param in config.get_prefix_options(''):
                if param not in connection_params:
                    value = config.get(param, None)
                    self._explicit_params[param] = value
        else:
            # Fallback если get_prefix_options недоступен
            known_params = ['max_heater_temp', 'critical_temp', 'fan_on_temp', 
                          'auto_shutdown_enabled', 'auto_shutdown_minutes']
            for param in known_params:
                try:
                    value = config.get(param, None)
                    if value is not None:
                        self._explicit_params[param] = value
                except:
                    pass
        
        self._has_custom_config = len(self._explicit_params) > 0
        
        # =====================================================================
        # ПЕРЕМЕННЫЕ СОСТОЯНИЯ (ДАННЫЕ, ПОЛУЧАЕМЫЕ С FLOOK32)
        # =====================================================================
        self.air_temp = 25.0               # Температура воздуха (DS18B20)
        self.heater_temp = 25.0            # Температура нагревателя (MAX6675)
        self.target_temp = 0.0             # Целевая температура
        self.heater_state = False          # Состояние нагревателя (вкл/выкл)
        self.fan_state = False             # Состояние вентилятора
        self.fan_duty = 0                  # Мощность вентилятора (0-1023)
        self.system_locked = False         # Флаг блокировки системы
        self.lock_message = ""             # Сообщение о причине блокировки
        self.uptime = 0                    # Время работы устройства (сек)
        self.error_count = 0               # Количество ошибок в журнале
        self.klipper_detected = False      # Klipper обнаружен?
        self.klipper_ip = ""               # IP Klipper
        self.thermal_confidence = 0        # Уверенность термальной модели (%)
        self.thermal_heater_rate = 0       # Скорость нагрева (°C/мин)
        self.thermal_cooling_rate = 0      # Скорость охлаждения (°C/сек)
        self.device_id = None              # ID устройства (из /api/all)
        
        # Температурные пределы для сенсора Klipper
        self.min_temp = MIN_TEMP          # -100°C
        self.max_temp = MAX_TEMP          # 200°C
        
        # Счётчики ошибок HTTP-соединения
        self._http_errors = 0             # Текущее количество ошибок подряд
        self._max_http_errors = 5         # Порог для объявления потери связи
        self.connection_lost_time = 0     # Время потери связи (0 = связь есть)
        
        # Переменные для автоуведомлений об ошибках
        self._last_error_check_time = 0   # Время последней проверки ошибок
        self._last_critical_ts = 0        # Timestamp последней обработанной критической ошибки
        self._connected_before = False    # Было ли подключение ранее
        self._device_found_after_reset = False  # Устройство найдено после сброса?
        
        # Переменные для отправки конфигурации
        self._config_sending = False      # Флаг: конфигурация отправляется прямо сейчас
        self._config_sent_message = False # Сообщение об отправке уже выведено?
        self._queue_lock = threading.Lock()  # Блокировка для очереди отправки
        self.config_sent = False          # Конфигурация успешно отправлена?
        self.config_apply_attempts = 0    # Количество попыток отправки
        self.max_config_attempts = 3      # Максимальное количество попыток
        
        # =====================================================================
        # РЕЖИМ РАБОТЫ И ID УСТРОЙСТВА
        # =====================================================================
        
        # Ручной режим: IP указан явно, автообнаружение не используется
        self.manual_mode = self.flook_ip is not None
        # Способ хранения ID: "moonraker", "file", или None
        self._storage_method = None
        # Кэш URL Moonraker API
        self._moonraker_url_cache = None
        # Устройство выбрано (для авторежима)
        self.device_selected = False
        
        # Флаги для предотвращения повторных предупреждений
        self._wrong_id_warning_shown = False    # Предупреждение о несовпадении ID
        self._no_device_warning_shown = False   # Предупреждение об отсутствии устройств
        self._no_id_warning_shown = False       # Предупреждение об отсутствии сохранённого ID
        
        if not self.manual_mode:
            # Загружаем сохранённый ID устройства (если есть)
            self.saved_device_id = self._load_device_id()
            if self.saved_device_id:
                logging.info("Загружен ID устройства: {}".format(self.saved_device_id))
        else:
            # В ручном режиме ID не нужен
            self.saved_device_id = None
        
        # =====================================================================
        # WEBSOCKET (ОПЦИОНАЛЬНО, ДЛЯ REAL-TIME ОБНОВЛЕНИЙ)
        # =====================================================================
        self.ws = None                     # Объект WebSocket
        self.ws_thread = None              # Поток WebSocket
        self.ws_running = False            # Флаг работы WebSocket
        self.ws_connected = False          # Флаг подключения
        self.ws_reconnect_delay = 10       # Задержка перед переподключением (сек)
        self._ws_error_reported = False    # Ошибка WebSocket уже выведена?
        
        # =====================================================================
        # UDP ОБНАРУЖЕНИЕ
        # =====================================================================
        self.udp_running = False           # Флаг работы UDP-слушателя
        self.udp_thread = None             # Поток UDP-слушателя
        
        # =====================================================================
        # РЕГИСТРАЦИЯ В KLIPPER
        # =====================================================================
        
        # Регистрируем датчик в Klipper как temperature_sensor
        self.printer.add_object("temperature_sensor " + self.name, self)
        
        # Блокировка для потокобезопасного доступа к температуре
        self.temp_lock = threading.Lock()
        # Флаг остановки всех потоков (вызывается при завершении Klipper)
        self.stop_thread = False
        # Очередь отложенных уведомлений (до инициализации gcode)
        self._pending_notifications = []
        
        # Получаем объект G-кода для регистрации команд
        self.gcode = self.printer.lookup_object('gcode')
        # Регистрируем 17 G-код команд
        self._safe_register_commands()
        
        # =====================================================================
        # ЗАПУСК ФОНОВЫХ ПОТОКОВ
        # =====================================================================
        
        # Основной цикл опроса датчика (WebSocket или HTTP)
        self.sensor_thread = threading.Thread(target=self._sensor_loop)
        self.sensor_thread.daemon = True
        self.sensor_thread.start()
        
        # UDP-слушатель для автообнаружения (только в автоматическом режиме)
        if not self.manual_mode and self.auto_discover and not self.flook_ip:
            self.udp_running = True
            self.udp_thread = threading.Thread(target=self._udp_discovery_loop)
            self.udp_thread.daemon = True
            self.udp_thread.start()
            logging.info("UDP обнаружение запущено")
        
        # Отправляем накопленные уведомления (если были)
        self._flush_pending_notifications()
        
        logging.info("FLOOK32 датчик '{}' инициализирован (режим: air)".format(self.name))
        logging.info("=" * 60)
    
    def _safe_register_commands(self):
        """
        Безопасная регистрация G-код команд.
        
        Использует try/except для каждой команды, чтобы избежать
        ошибок при повторной регистрации (если в конфиге несколько датчиков).
        """
        commands = [
            ('FLOOK_STATUS', self.cmd_FLOOK_STATUS),
            ('FLOOK_TEMP', self.cmd_FLOOK_TEMP),
            ('FLOOK_SET', self.cmd_FLOOK_SET),
            ('FLOOK_OFF', self.cmd_FLOOK_OFF),
            ('FLOOK_DISCOVER', self.cmd_FLOOK_DISCOVER),
            ('FLOOK_SET_IP', self.cmd_FLOOK_SET_IP),
            ('FLOOK_ADAPT_START', self.cmd_FLOOK_ADAPT_START),
            ('FLOOK_ADAPT_ABORT', self.cmd_FLOOK_ADAPT_ABORT),
            ('FLOOK_ADAPT_STATUS', self.cmd_FLOOK_ADAPT_STATUS),
            ('FLOOK_UNLOCK', self.cmd_FLOOK_UNLOCK),
            ('FLOOK_LOCK', self.cmd_FLOOK_LOCK),
            ('FLOOK_REBOOT', self.cmd_FLOOK_REBOOT),
            ('FLOOK_ERRORS', self.cmd_FLOOK_ERRORS),
            ('FLOOK_CONFIG_GET', self.cmd_FLOOK_CONFIG_GET),
            ('FLOOK_AUTO_SHUTDOWN', self.cmd_FLOOK_AUTO_SHUTDOWN),
            ('FLOOK_AUTO_SHUTDOWN_STATUS', self.cmd_FLOOK_AUTO_SHUTDOWN_STATUS),
            ('FLOOK_RESET_ID', self.cmd_FLOOK_RESET_ID),
            ('FLOOK_CALIBRATE', self.cmd_FLOOK_CALIBRATE),
        ]
        for cmd_name, handler in commands:
            try:
                self.gcode.register_command(cmd_name, handler)
            except:
                pass  # Команда уже зарегистрирована другим экземпляром
    
    # =====================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =====================================================================
    
    def _normalize_id(self, device_id):
        """
        Нормализует ID устройства: переводит в верхний регистр
        и дополняет нулями слева до 8 символов (формат hex).
        
        Пример: "1a2b" → "00001A2B"
        """
        if not device_id:
            return None
        device_id = str(device_id).upper()
        return device_id.zfill(8)
    
    def _send_notification(self, message, is_error=False):
        """
        Отправляет уведомление в консоль Klipper и опционально в Moonraker.
        
        Параметры:
          message  — текст сообщения
          is_error — True для ошибок (префикс "!! "), False для инфо ("// ")
        """
        if is_error:
            logging.error("FLOOK32: {}".format(message))
        else:
            logging.info("FLOOK32: {}".format(message))
        
        # В тихом режиме не выводим сообщения в консоль
        if self.silent_mode:
            return
        
        prefix = "!! " if is_error else "// "
        final_msg = prefix + "FLOOK32: " + message
        
        # Если gcode ещё не инициализирован — добавляем в очередь
        if not hasattr(self, 'gcode') or not self.gcode:
            self._queue_notification(message, is_error)
            return
        
        try:
            self.gcode.respond_raw(final_msg)
        except:
            pass
        
        # Для критических ошибок отправляем также в Moonraker
        if is_error and HAS_REQUESTS:
            threading.Thread(target=self._send_moonraker_notification, 
                           args=(final_msg, is_error), daemon=True).start()
    
    def _queue_notification(self, message, is_error=False):
        """Добавляет уведомление в очередь, если gcode ещё не доступен."""
        if not hasattr(self, '_pending_notifications'):
            self._pending_notifications = []
        self._pending_notifications.append((message, is_error))
    
    def _flush_pending_notifications(self):
        """Отправляет все накопленные уведомления из очереди."""
        if hasattr(self, '_pending_notifications') and self._pending_notifications:
            for message, is_error in self._pending_notifications:
                self._send_notification(message, is_error)
            self._pending_notifications.clear()
    
    def _send_moonraker_notification(self, message, is_error=False):
        """Отправляет уведомление в Moonraker (если доступен)."""
        if not HAS_REQUESTS:
            return
        try:
            moonraker_url = self._get_moonraker_url()
            if moonraker_url:
                payload = {"message": message, "type": "error" if is_error else "info"}
                requests.post(moonraker_url + "/server/notification", json=payload, timeout=1)
        except:
            pass
    
    def _get_moonraker_url(self):
        """
        Определяет URL Moonraker API (http://localhost:<порт>).
        Перебирает стандартные порты: 7125, 7126, 7130.
        Результат кэшируется для ускорения последующих вызовов.
        """
        if self._moonraker_url_cache is not None:
            return self._moonraker_url_cache
        
        for port in [7125, 7126, 7130]:
            url = "http://localhost:{}".format(port)
            try:
                response = requests.get(url + "/server/info", timeout=0.5)
                if response.status_code == 200:
                    self._moonraker_url_cache = url
                    return url
            except:
                continue
        return None
    
    def _save_device_id(self, device_id):
        """
        Сохраняет ID устройства.
        Приоритет: Moonraker DB -> файл ~/.flook32_id
        """
        device_id = self._normalize_id(device_id)
        if not device_id:
            return False
        
        saved = False
        moonraker_url = self._get_moonraker_url()
        
        logging.info("=== FLOOK32 СОХРАНЕНИЕ ID ===")
        logging.info("ID: {}".format(device_id))
        logging.info("Moonraker URL: {}".format(moonraker_url))
        logging.info("HAS_REQUESTS: {}".format(HAS_REQUESTS))
        
        if moonraker_url and HAS_REQUESTS:
            try:
                base_url = moonraker_url.rstrip('/')
                logging.info("Base URL: {}".format(base_url))
                
                # Создаём namespace через PUT
                namespace_url = base_url + "/server/database/namespace?namespace=flook32"
                logging.info("Namespace URL: {}".format(namespace_url))
                
                ns_response = requests.put(namespace_url, timeout=2)
                logging.info("Namespace response status: {}".format(ns_response.status_code))
                logging.info("Namespace response body: {}".format(ns_response.text[:200]))
                
                # Сохраняем ID
                payload = {"namespace": "flook32", "key": "device_id", "value": device_id}
                item_url = base_url + "/server/database/item"
                logging.info("Item URL: {}".format(item_url))
                logging.info("Payload: {}".format(payload))
                
                response = requests.post(item_url, json=payload, timeout=2)
                logging.info("Save response status: {}".format(response.status_code))
                logging.info("Save response body: {}".format(response.text[:200]))
                
                if response.status_code in (200, 201):
                    try:
                        resp_data = response.json()
                        if resp_data.get('result') or resp_data.get('value'):
                            logging.info("✅ ID сохранен в Moonraker DB")
                            self._storage_method = "moonraker"
                            saved = True
                        else:
                            logging.warning("Ответ не содержит result/value: {}".format(resp_data))
                    except Exception as json_err:
                        logging.warning("Не удалось распарсить JSON: {}".format(json_err))
                        # Всё равно считаем успехом, если статус хороший
                        logging.info("✅ ID сохранен в Moonraker DB (статус {})".format(response.status_code))
                        self._storage_method = "moonraker"
                        saved = True
                else:
                    logging.warning("❌ Ошибка сохранения, статус: {}".format(response.status_code))
                    
            except Exception as e:
                logging.error("❌ Ошибка Moonraker: {}".format(e))
                import traceback
                logging.error(traceback.format_exc())
        else:
            logging.warning("Moonraker недоступен: url={}, requests={}".format(moonraker_url, HAS_REQUESTS))
        
        # Fallback в файл
        if not saved:
            logging.info("Сохраняем в файл как fallback...")
            file_path = os.path.expanduser("~/.flook32_id")
            try:
                with open(file_path, 'w') as f:
                    f.write(device_id)
                logging.info("✅ ID сохранен в файл: {}".format(file_path))
                self._storage_method = "file"
                saved = True
            except Exception as e:
                logging.error("❌ Не удалось сохранить ID в файл: {}".format(e))
        
        return saved
    
    def _load_device_id(self):
        """Загружает сохранённый ID устройства."""
        # Пробуем Moonraker
        moonraker_url = self._get_moonraker_url()
        if moonraker_url and HAS_REQUESTS:
            try:
                base_url = moonraker_url.rstrip('/')
                response = requests.get(
                    base_url + "/server/database/item?namespace=flook32&key=device_id", 
                    timeout=2)
                
                if response.status_code == 200:
                    data = response.json()
                    # Проверяем наличие result.value
                    value = data.get('result', {}).get('value')
                    if value:
                        device_id = self._normalize_id(value)
                        if device_id:
                            logging.info("Загружен ID из Moonraker DB: {}".format(device_id))
                            self._storage_method = "moonraker"
                            return device_id
            except Exception as e:
                logging.debug("Ошибка загрузки из Moonraker: {}".format(e))
        
        # Fallback в файл
        file_path = os.path.expanduser("~/.flook32_id")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    device_id = self._normalize_id(f.read().strip())
                    if device_id:
                        logging.info("Загружен ID из файла: {}".format(device_id))
                        self._storage_method = "file"
                        return device_id
        except Exception as e:
            logging.debug("Ошибка загрузки из файла: {}".format(e))
        
        return None
    
    def _delete_device_id(self):
        """Удаляет сохранённый ID устройства."""
        moonraker_url = self._get_moonraker_url()
        if moonraker_url and HAS_REQUESTS:
            try:
                requests.delete(
                    moonraker_url + "/server/database/item?namespace=flook32&key=device_id", 
                    timeout=2)
            except:
                pass
        
        file_path = os.path.expanduser("~/.flook32_id")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        self._storage_method = None
    
    # =====================================================================
    # HTTP КОММУНИКАЦИЯ С FLOOK32
    # =====================================================================
    
    def _http_get_json(self, path, timeout=3):
        """
        Выполняет HTTP GET запрос к FLOOK32 и парсит JSON из ответа.
        
        Особенности реализации:
          • Использует низкоуровневые сокеты (без requests) — минимальные зависимости
          • Ручной поиск JSON в ответе (пропускает HTTP-заголовки)
          • Балансировка скобок для точного определения конца JSON
          • Защита от частичных ответов
        """
        if not self.flook_ip:
            return None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.flook_ip, self.flook_port))
            
            request = "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n".format(path, self.flook_ip)
            sock.send(request.encode())
            
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            
            text = response.decode('utf-8', errors='ignore')
            
            # Поиск начала JSON ([ или {)
            start = -1
            for i, char in enumerate(text):
                if char in ['[', '{']:
                    start = i
                    break
            
            if start == -1:
                return None
            
            json_str = text[start:]
            
            # Поиск конца JSON с учётом вложенности и строк
            bracket_count = 0
            in_string = False
            escape = False
            end = 0
            
            for i, char in enumerate(json_str):
                if escape:
                    escape = False
                    continue
                if char == '\\':
                    escape = True
                    continue
                if char == '"' and not escape:
                    in_string = not in_string
                    continue
                if not in_string:
                    if char in ['[', '{']:
                        bracket_count += 1
                    elif char in [']', '}']:
                        bracket_count -= 1
                        if bracket_count == 0:
                            end = i + 1
                            break
            
            if end == 0:
                return None
            
            json_str = json_str[:end]
            return json.loads(json_str)
            
        except:
            self._http_errors += 1
            return None
    
    def _http_post(self, path, data=None, timeout=3):
        """
        Выполняет HTTP POST запрос к FLOOK32.
        Поддерживает передачу данных в URL-encoded формате.
        """
        if not self.flook_ip:
            return None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.flook_ip, self.flook_port))
            
            body = ""
            if data:
                if isinstance(data, dict):
                    body = "&".join([k + "=" + v for k, v in data.items()])
                else:
                    body = str(data)
            
            request = "POST {} HTTP/1.1\r\nHost: {}\r\n".format(path, self.flook_ip)
            if body:
                request += "Content-Length: {}\r\n".format(len(body))
            request += "Connection: close\r\n\r\n"
            if body:
                request += body
            
            sock.send(request.encode())
            time.sleep(0.3)  # Даём ESP32 время на обработку запроса
            response = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except:
                    break
            response = response.decode()
            sock.close()
            
            if '\r\n\r\n' in response:
                return response.split('\r\n\r\n', 1)[1]
            return response
        except:
            return None
    
    def _send_config_to_esp(self):
        """
        Отправляет пользовательскую конфигурацию на FLOOK32.
        
        Алгоритм:
          1. Разблокирует настройки через /api/unlock-settings
          2. Отправляет JSON с конфигурацией через POST /api/config
          3. Блокирует настройки обратно через /api/lock-settings
        """
        if not self.flook_ip or not self._has_custom_config:
            return False
        
        with self._queue_lock:
            if self._config_sending:
                return False
            self._config_sending = True
        
        try:
            config_data = {}
            for cfg_name, short_name in compact_mapping.items():
                if cfg_name in self._explicit_params and hasattr(self, cfg_name):
                    value = getattr(self, cfg_name)
                    if isinstance(value, bool):
                        value = 1 if value else 0
                    config_data[short_name] = value
            
            if not config_data:
                return True
            
            unlock_result = self._http_post(
                "/api/unlock-settings?password={}".format(self.unlock_password), timeout=2)
            
            if not unlock_result:
                return False
            unlock_lower = unlock_result.lower()
            if "unlocked" not in unlock_lower and "already" not in unlock_lower:
                return False
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.flook_ip, self.flook_port))
            body = json.dumps(config_data)
            request = "POST /api/config HTTP/1.1\r\n"
            request += "Host: {}\r\n".format(self.flook_ip)
            request += "Content-Type: application/json\r\n"
            request += "Content-Length: {}\r\n".format(len(body))
            request += "Connection: close\r\n\r\n"
            request += body
            sock.send(request.encode())
            response = sock.recv(4096).decode()
            sock.close()
            
            if "OK" in response or "OK_RESTART" in response:
                self._lock_settings()
                
                if "OK_RESTART" in response:
                    self.flook_ip = None
                    self.discovery_complete = False
                return True
            return False
        except:
            return False
        finally:
            with self._queue_lock:
                self._config_sending = False
    
    def _lock_settings(self):
        """Блокирует настройки на устройстве (защита от случайных изменений)."""
        if not self.flook_ip:
            return False
        try:
            self._http_post("/api/lock-settings", timeout=2)
            return True
        except:
            return False
    
    def _update_from_api(self):
        """
        Получает и парсит данные с FLOOK32 через HTTP GET /api/all.
        
        Обновляет все локальные переменные состояния.
        При потере связи запускает процедуру переподключения.
        """
        if not self.flook_ip:
            return False
        
        data = self._http_get_json("/api/all", timeout=2)
        if not data:
            self._http_errors += 1
            if self._http_errors >= self._max_http_errors and self.connection_lost_time == 0:
                self.connection_lost_time = time.time()
                self._send_notification("Потеряна связь с {}".format(self.flook_ip), is_error=True)
                if not self.manual_mode:
                    self.flook_ip = None
                    self.discovery_complete = False
                    self.auto_discover = True
            return False
        
        was_lost = (self.connection_lost_time != 0)
        self._http_errors = 0
        
        if was_lost:
            downtime = time.time() - self.connection_lost_time
            self.connection_lost_time = 0
            logging.info("Связь с FLOOK32 {} восстановлена (потеря: {:.1f} сек)".format(
                self.flook_ip, downtime))
            self._send_notification("Связь с FLOOK32 восстановлена (потеря: {:.1f} сек)".format(
                downtime), is_error=False)
            self.auto_discover = False
        
        was_first_connection = not self._connected_before
        
        with self.temp_lock:
            # Парсим компактный JSON ответ (короткие ключи для экономии трафика)
            if 't' in data:
                self.target_temp = float(data['t'])
            if 's' in data:
                state = int(data['s'])
                self.heater_state = (state & 1) != 0  # Бит 0 = нагреватель
                self.fan_state = (state & 2) != 0     # Бит 1 = вентилятор
            if 'fp' in data:
                self.fan_duty = int(data['fp'])
            if 'a' in data:
                try:
                    temp = float(data['a'])
                    if MIN_TEMP <= temp <= MAX_TEMP:
                        self.air_temp = temp
                except:
                    pass
            if 'h' in data:
                try:
                    temp = float(data['h'])
                    if MIN_TEMP <= temp <= MAX_TEMP:
                        self.heater_temp = temp
                except:
                    pass
            if 'u' in data:
                self.uptime = data['u']
            if 'l' in data:
                self.system_locked = data['l'] == 1
            if 'e' in data:
                self.error_count = data['e']
            
            if 'id' in data:
                self.device_id = self._normalize_id(data['id'])
                
                if not self.saved_device_id:
                    self.saved_device_id = self.device_id
                    self._save_device_id(self.device_id)
                
                if was_first_connection and not self._device_found_after_reset:
                    logging.info("Устройство найдено, ID={}".format(self.device_id))
                    # В ручном режиме отправляем UDP-запрос с ID один раз
                    if self.manual_mode and self.saved_device_id:
                        self._send_manual_udp_discovery()
                    self._device_found_after_reset = True
                    self._connected_before = True
                    if self.saved_device_id:
                        self.discovery_complete = False
        
        return True
    
    # =====================================================================
    # UDP ОБНАРУЖЕНИЕ (ЕДИНЫЙ МЕТОД)
    # =====================================================================
    
    def _connect_to(self, ip, device_id):
        """
        Подключается к найденному устройству.
        Если уже подключены к этому же IP — не спамим уведомлениями.
        """
        if self.flook_ip == ip and self.discovery_complete:
            return
        
        self.flook_ip = ip
        self.discovery_complete = True
        self.auto_discover = False
        
        if device_id and not self.saved_device_id:
            self.saved_device_id = device_id
            self._save_device_id(device_id)
        
        logging.info("UDP: подключен к {}, ID={}".format(ip, device_id))
        self._send_notification("Найден FLOOK32 (IP: {}, ID: {})".format(
            ip, device_id if device_id else 'None'))
        
        if HAS_WEBSOCKET:
            self._start_websocket()

    def _send_manual_udp_discovery(self):
        """
        Отправляет один UDP-запрос с ID в ручном режиме.
        Это позволяет FLOOK32 сохранить IP Klipper для работы Moonraker.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.5)
            msg = "FLOOK_DISCOVERY:{}".format(self.saved_device_id)
            sock.sendto(msg.encode(), (UDP_BROADCAST_IP, UDP_PORT))
            sock.close()
            logging.info("Ручной режим: UDP-запрос с ID отправлен на broadcast")
        except Exception as e:
            logging.debug("Ручной режим: ошибка UDP: {}".format(e))
    
    def _udp_discovery_loop(self):
        """
        Единый цикл UDP-обнаружения. Отправляет broadcast-запрос
        и ждёт ответы от FLOOK32. Работает в одном потоке с одним сокетом.
        
        Отправляет запрос с ID (если сохранён), получает TRUE/FALSE,
        подключается к нужному устройству.
        """
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', UDP_PORT))
            sock.settimeout(2.0)
        except Exception as e:
            logging.error("UDP: не удалось открыть сокет: {}".format(e))
            return
        
        while self.udp_running and not self.stop_thread:
            if self.flook_ip and self.discovery_complete:
                time.sleep(5)
                continue
            
            try:
                if self.saved_device_id:
                    msg = "FLOOK_DISCOVERY:{}".format(self.saved_device_id)
                else:
                    msg = "FLOOK_DISCOVERY"
                
                sock.sendto(msg.encode(), (UDP_BROADCAST_IP, UDP_PORT))
                
                start = time.time()
                while time.time() - start < 3.0:
                    try:
                        data, addr = sock.recvfrom(1024)
                        response = data.decode().strip()
                        
                        if not response.startswith("FLOOK32:"):
                            continue
                        
                        parts = response.split(':')
                        
                        if len(parts) >= 6 and parts[1] in ('TRUE', 'FALSE'):
                            match_status = parts[1].upper() == 'TRUE'
                            ip = parts[2]
                            device_id = self._normalize_id(parts[5]) if len(parts) > 5 else None
                        elif len(parts) == 5 and parts[1].count('.') == 3:
                            match_status = True
                            ip = parts[1]
                            device_id = self._normalize_id(parts[4]) if len(parts) > 4 else None
                        else:
                            continue
                        
                        logging.debug("UDP ответ: {}, match={}, ID={}".format(ip, match_status, device_id))
                        
                        if self.saved_device_id:
                            if match_status and device_id == self.saved_device_id:
                                self._connect_to(ip, device_id)
                                break
                        else:
                            if match_status:
                                self._connect_to(ip, device_id)
                                break
                                
                    except socket.timeout:
                        break
                        
            except Exception as e:
                logging.debug("UDP ошибка: {}".format(e))
            
            time.sleep(30 if self.flook_ip else 5)
        
        if sock:
            sock.close()
    
    # =====================================================================
    # WEBSOCKET (REAL-TIME ОБНОВЛЕНИЯ)
    # =====================================================================
    
    def _start_websocket(self):
        """Запускает WebSocket подключение к FLOOK32."""
        if not HAS_WEBSOCKET or not self.flook_ip:
            return
        
        if self.ws_thread and self.ws_thread.is_alive():
            return
        
        self.ws_running = True
        self.ws_thread = threading.Thread(target=self._websocket_loop)
        self.ws_thread.daemon = True
        self.ws_thread.start()
    
    def _websocket_loop(self):
        """Цикл WebSocket с автоматическим переподключением при обрыве."""
        while self.ws_running and not self.stop_thread:
            try:
                url = "ws://{}:{}/ws".format(self.flook_ip, self.flook_port)
                self.ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_ws_open,
                    on_message=self._on_ws_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except:
                pass
            
            if self.ws_running and not self.stop_thread:
                time.sleep(self.ws_reconnect_delay)
    
    def _on_ws_open(self, ws):
        """Callback: WebSocket соединение установлено."""
        self.ws_connected = True
        logging.info("WebSocket подключен к {}".format(self.flook_ip))
    
    def _on_ws_message(self, ws, message):
        """Callback: получено сообщение WebSocket с метриками."""
        try:
            data = json.loads(message)
            with self.temp_lock:
                if 'a' in data:
                    try:
                        temp = float(data['a'])
                        if MIN_TEMP <= temp <= MAX_TEMP:
                            self.air_temp = temp
                    except:
                        pass
                if 'h' in data:
                    try:
                        temp = float(data['h'])
                        if MIN_TEMP <= temp <= MAX_TEMP:
                            self.heater_temp = temp
                    except:
                        pass
                if 'tg' in data:
                    self.target_temp = float(data['tg'])
                if 'hs' in data:
                    self.heater_state = bool(data['hs'])
                if 'fs' in data:
                    self.fan_state = bool(data['fs'])
                if 'fp' in data:
                    self.fan_duty = int(data['fp'])
                if 'id' in data:
                    self.device_id = self._normalize_id(data['id'])
        except:
            pass
    
    def _on_ws_error(self, ws, error):
        """Callback: ошибка WebSocket."""
        self.ws_connected = False
    
    def _on_ws_close(self, ws, close_status_code, close_msg):
        """Callback: WebSocket соединение закрыто."""
        self.ws_connected = False
    
    def _stop_websocket(self):
        """Останавливает WebSocket соединение и поток."""
        self.ws_running = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
        self.ws_connected = False
    
    # =====================================================================
    # МОНИТОРИНГ ОШИБОК FLOOK32
    # =====================================================================
    
    def _check_and_report_errors(self):
        """
        Проверяет журнал ошибок FLOOK32 через API и уведомляет о новых
        критических ошибках в консоль Klipper.
        
        Каждая ошибка выводится только один раз (отслеживается по timestamp).
        Старые ошибки игнорируются согласно error_notification_max_age.
        """
        if not self.enable_error_notifications or not self.flook_ip:
            return
        
        current_time = time.time()
        if current_time - self._last_error_check_time < self.error_check_interval:
            return
        
        self._last_error_check_time = current_time
        
        data = self._http_get_json("/api/error-log", timeout=2)
        if not data:
            return
        
        errors_list = data if isinstance(data, list) else data.get('errorLog', [])
        if not errors_list:
            return
        
        current_uptime_sec = self.uptime if self.uptime > 0 else 0
        sorted_errors = sorted(errors_list, key=lambda x: x.get('ts', 0))
        
        for err in sorted_errors:
            ts_sec = err.get('ts', 0)
            error_age = current_uptime_sec - ts_sec
            
            if self.error_notification_max_age > 0 and error_age > self.error_notification_max_age:
                continue
            
            sev = err.get('sev', err.get('severity', 'info'))
            if sev != 'critical':
                continue
            
            if ts_sec <= self._last_critical_ts:
                continue
            
            self._last_critical_ts = ts_sec
            
            msg = err.get('msg', err.get('message', ''))
            hours = ts_sec // 3600
            minutes = (ts_sec % 3600) // 60
            seconds = ts_sec % 60
            time_str = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
            count = err.get('count', 1)
            count_str = " (x{})".format(count) if count > 1 else ""
            
            error_message = "КРИТИЧЕСКАЯ ОШИБКА [{}]: {}{}".format(time_str, msg, count_str)
            self._send_notification(error_message, is_error=True)
            
            recommendations = self._get_recommendations_text(msg)
            if recommendations:
                self._send_notification(recommendations, is_error=True)
    
    def _get_recommendations_text(self, error_msg):
        """Возвращает рекомендации по устранению типовых ошибок."""
        if 'ПЕРЕГРЕВ НАГРЕВАТЕЛЯ' in error_msg or 'criticalOverheat' in error_msg:
            return "Рекомендации: проверьте SSR, нагреватель и вентилятор"
        elif 'ПЕРЕГРЕВ ВОЗДУХА' in error_msg or 'airOverheat' in error_msg:
            return "Рекомендации: проверьте циркуляцию воздуха"
        elif 'THERMAL RUNAWAY' in error_msg:
            return "Рекомендации: проверьте питание 220В и датчик температуры MAX6675"
        elif 'MAX6675' in error_msg:
            return "Рекомендации: проверьте подключение MAX6675 и термопары"
        elif 'DS18B20' in error_msg:
            return "Рекомендации: проверьте подключение DS18B20"
        else:
            return "Рекомендации: проверьте подключение FLOOK32 и лог ошибок"
    
    # =====================================================================
    # ОСНОВНОЙ ЦИКЛ ОПРОСА
    # =====================================================================
    
    def _sensor_loop(self):
        """
        Основной цикл работы сенсора. Выполняется в отдельном потоке.
        
        Задачи:
          • Периодический опрос FLOOK32 (HTTP или WebSocket)
          • Отправка конфигурации при первом подключении
          • Проверка ошибок FLOOK32
          • Передача температуры в Klipper через callback
        """
        mcu = self.printer.lookup_object('mcu')
        last_error_check = 0
        
        while not self.stop_thread:
            current_time = time.time()
            
            # Проверка ошибок FLOOK32
            if current_time - last_error_check >= self.error_check_interval:
                last_error_check = current_time
                try:
                    self._check_and_report_errors()
                except:
                    pass
            
            if self.flook_ip:
                # Запуск WebSocket если доступен
                if HAS_WEBSOCKET and not self.ws_connected and not self.ws_thread:
                    self._start_websocket()
                
                # Отправка конфигурации при первом подключении
                if (self._has_custom_config and not self.config_sent and 
                    self.config_apply_attempts < self.max_config_attempts):
                    with self._queue_lock:
                        sending = self._config_sending
                    if not sending:
                        if self._send_config_to_esp():
                            self.config_sent = True
                            if not self._config_sent_message:
                                self._send_notification("Конфигурация сохранена")
                                self._config_sent_message = True
                        else:
                            self.config_apply_attempts += 1
                
                # HTTP опрос (если WebSocket не подключен)
                if not self.ws_connected:
                    self._update_from_api()
                
                # Передача температуры в Klipper
                with self.temp_lock:
                    temp = self.air_temp
                
                measured_time = self.reactor.monotonic()
                print_time = mcu.estimated_print_time(measured_time)
                if hasattr(self, '_callback'):
                    self._callback(print_time, temp)
            
            time.sleep(self.report_interval)
    
    # =====================================================================
    # G-CODE КОМАНДЫ
    # =====================================================================
    
    def cmd_FLOOK_STATUS(self, gcmd):
        """FLOOK_STATUS — показать полный статус устройства."""
        with self.temp_lock:
            status = "═══ FLOOK32 '{}' ═══\n".format(self.name)
            status += "Режим сенсора: air\n"
            if self.manual_mode:
                status += "Режим подключения: РУЧНОЙ\nIP: {}:{}\n".format(self.flook_ip, self.flook_port)
            elif self.flook_ip:
                status += "Режим подключения: АВТОМАТИЧЕСКИЙ\nIP: {}:{}\n".format(self.flook_ip, self.flook_port)
            else:
                status += "Режим подключения: АВТОМАТИЧЕСКИЙ\nIP: Не подключен\n"
            status += "Воздух: {:.1f}°C\n".format(self.air_temp)
            status += "Нагреватель: {:.1f}°C\n".format(self.heater_temp)
            status += "Цель: {:.1f}°C\n".format(self.target_temp)
            status += "Блокировка: {}\n".format('ДА' if self.system_locked else 'НЕТ')
            status += "Ошибок: {}\n".format(self.error_count)
            gcmd.respond_info(status)
    
    def cmd_FLOOK_TEMP(self, gcmd):
        """FLOOK_TEMP — показать текущую температуру."""
        with self.temp_lock:
            gcmd.respond_info("Воздух: {:.1f}°C, Нагреватель: {:.1f}°C".format(
                self.air_temp, self.heater_temp))
    
    def cmd_FLOOK_SET(self, gcmd):
        """FLOOK_SET S=<температура> — установить целевую температуру."""
        temp = gcmd.get_float('S', 0.0)
        if temp < 0 or temp > 70:
            gcmd.respond_info("Температура должна быть между 0 и 70°C")
            return
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        result = self._http_post("/api/target?value={}".format(temp))
        if result and ("OK" in result or "success" in result):
            with self.temp_lock:
                self.target_temp = temp
            gcmd.respond_info("Целевая температура установлена на {}°C".format(temp))
        else:
            gcmd.respond_info("Не удалось установить температуру")
    
    def cmd_FLOOK_OFF(self, gcmd):
        """FLOOK_OFF — аварийное выключение нагрева."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        result = self._http_post("/api/heater-off")
        if result and ("OK" in result or "success" in result):
            gcmd.respond_info("Нагрев выключен")
        else:
            gcmd.respond_info("Не удалось выключить нагрев")
    
    def cmd_FLOOK_DISCOVER(self, gcmd):
        """FLOOK_DISCOVER — принудительный поиск устройств в сети."""
        gcmd.respond_info("Поиск устройств...")
        time.sleep(5)
        if self.flook_ip:
            gcmd.respond_info("Устройство найдено: {}, ID: {}".format(
                self.flook_ip, self.saved_device_id))
        else:
            gcmd.respond_info("Устройства не найдены")
    
    def cmd_FLOOK_SET_IP(self, gcmd):
        """FLOOK_SET_IP IP=<адрес> — установить IP вручную."""
        ip = gcmd.get('IP')
        if not ip:
            gcmd.respond_info("Использование: FLOOK_SET_IP IP=192.168.1.100")
            return
        try:
            socket.inet_aton(ip)
            self.flook_ip = ip
            self.auto_discover = False
            self.discovery_complete = True
            self._http_errors = 0
            if HAS_WEBSOCKET:
                self._start_websocket()
            gcmd.respond_info("IP установлен на {}".format(ip))
        except:
            gcmd.respond_info("Неверный IP: {}".format(ip))
    
    def cmd_FLOOK_ADAPT_START(self, gcmd):
        """FLOOK_ADAPT_START TARGET=<°C> — запуск адаптации."""
        target = gcmd.get_float('TARGET', 60.0, minval=40, maxval=70)
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        result = self._http_post("/api/adapt/start?target={}".format(target))
        if result and "started" in result.lower():
            gcmd.respond_info("Адаптация запущена до {}°C".format(target))
        else:
            gcmd.respond_info("Не удалось запустить адаптацию")
    
    def cmd_FLOOK_ADAPT_ABORT(self, gcmd):
        """FLOOK_ADAPT_ABORT — прервать адаптацию."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        result = self._http_post("/api/adapt/abort")
        if result:
            gcmd.respond_info("Адаптация прервана")
        else:
            gcmd.respond_info("Не удалось прервать адаптацию")
    
    def cmd_FLOOK_ADAPT_STATUS(self, gcmd):
        """FLOOK_ADAPT_STATUS — статус адаптации."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        data = self._http_get_json("/api/adapt/status")
        if data:
            status = "Адаптация: {}\n".format('ВКЛ' if data.get('inProgress') else 'ВЫКЛ')
            status += "Прогресс: {}%\n".format(data.get('progress', 0))
            status += "Сообщение: {}".format(data.get('message', ''))
            gcmd.respond_info(status)
        else:
            gcmd.respond_info("Не удалось получить статус")
    
    def cmd_FLOOK_UNLOCK(self, gcmd):
        """FLOOK_UNLOCK [PASSWORD=<пароль>] — разблокировать настройки."""
        password = gcmd.get('PASSWORD', self.unlock_password)
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        result = self._http_post("/api/unlock-settings?password={}".format(password))
        if result and "unlocked" in result.lower():
            gcmd.respond_info("Настройки разблокированы")
        else:
            gcmd.respond_info("Не удалось разблокировать")
    
    def cmd_FLOOK_LOCK(self, gcmd):
        """FLOOK_LOCK — заблокировать настройки."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        result = self._http_post("/api/lock-settings")
        if result:
            gcmd.respond_info("Настройки заблокированы")
        else:
            gcmd.respond_info("Не удалось заблокировать")
    
    def cmd_FLOOK_REBOOT(self, gcmd):
        """FLOOK_REBOOT — перезагрузить FLOOK32."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        gcmd.respond_info("Перезагрузка FLOOK32...")
        self._http_post("/api/reboot")
        if HAS_WEBSOCKET:
            self._stop_websocket()
        self.flook_ip = None
        self.discovery_complete = False
        self.config_sent = False
        self._config_sent_message = False
        self._http_errors = 0
        gcmd.respond_info("Команда отправлена")
    
    def cmd_FLOOK_ERRORS(self, gcmd):
        """FLOOK_ERRORS — показать журнал ошибок (последние 10 записей)."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        data = self._http_get_json("/api/error-log")
        if not data:
            gcmd.respond_info("Не удалось получить журнал ошибок")
            return
        errors_list = data if isinstance(data, list) else data.get('errorLog', [])
        if not errors_list:
            gcmd.respond_info("Журнал ошибок пуст")
            return
        gcmd.respond_info("=== ЖУРНАЛ ОШИБОК ===")
        for err in errors_list[-10:]:
            ts = err.get('ts', 0)
            hours = ts // 3600
            minutes = (ts % 3600) // 60
            seconds = ts % 60
            msg = err.get('msg', err.get('message', ''))
            sev = err.get('sev', err.get('severity', 'info'))
            icon = "🔥" if sev == "critical" else "⚠️" if sev == "warning" else "ℹ️"
            gcmd.respond_info("{} [{:02d}:{:02d}:{:02d}] {}".format(icon, hours, minutes, seconds, msg))
    
    def cmd_FLOOK_CONFIG_GET(self, gcmd):
        """FLOOK_CONFIG_GET — показать текущую конфигурацию устройства."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        data = self._http_get_json("/api/config")
        if not data:
            gcmd.respond_info("Не удалось получить конфигурацию")
            return
        status = "⚙️ КОНФИГУРАЦИЯ FLOOK32:\n"
        status += "  maxHeaterTemp: {}°C\n".format(data.get('mt', 0))
        status += "  criticalTemp: {}°C\n".format(data.get('ct', 0))
        status += "  maxAirTemp: {}°C\n".format(data.get('ma', 0))
        status += "  hysteresis: {}°C\n".format(data.get('hy', 0))
        status += "  heaterHysteresis: {}°C\n".format(data.get('hh', 0))
        status += "  fanOnTemp: {}°C\n".format(data.get('fT', 0))
        status += "  maxFanDuty: {}\n".format(data.get('mFD', 1023))
        status += "  invertHeaterSignal: {}\n".format('Да' if data.get('iH') else 'Нет')
        status += "  invertFanSignal: {}\n".format('Да' if data.get('iF') else 'Нет')
        status += "  autoShutdownEnabled: {}\n".format('Да' if data.get('aSd') else 'Нет')
        status += "  autoShutdownMinutes: {}\n".format(data.get('aSm', 30))
        status += "  adaptationPerformed: {}\n".format('Да' if data.get('aPd') else 'Нет')
        gcmd.respond_info(status)
    
    def cmd_FLOOK_AUTO_SHUTDOWN(self, gcmd):
        """FLOOK_AUTO_SHUTDOWN [ENABLE=1] [MINUTES=30] — настройка автоотключения."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        enable = gcmd.get_int('ENABLE', None)
        minutes = gcmd.get_int('MINUTES', None)
        params = []
        if enable is not None:
            params.append("enable={}".format('1' if enable == 1 else '0'))
        if minutes is not None:
            params.append("minutes={}".format(minutes))
        if params:
            result = self._http_post("/api/moonraker-shutdown?{}".format('&'.join(params)))
            if result and ("OK" in result or "success" in result):
                gcmd.respond_info("Автоотключение обновлено")
            else:
                gcmd.respond_info("Не удалось обновить")
        else:
            gcmd.respond_info("Использование: FLOOK_AUTO_SHUTDOWN ENABLE=1 MINUTES=30")
    
    def cmd_FLOOK_AUTO_SHUTDOWN_STATUS(self, gcmd):
        """FLOOK_AUTO_SHUTDOWN_STATUS — статус автоотключения."""
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        data = self._http_get_json("/api/config")
        if data:
            enabled = data.get('aSd', False)
            minutes = data.get('aSm', 30)
            gcmd.respond_info("Автоотключение: {} ({} мин)".format(
                'ВКЛ' if enabled else 'ВЫКЛ', minutes))
        else:
            gcmd.respond_info("Не удалось получить статус")
    
    def cmd_FLOOK_RESET_ID(self, gcmd):
        """
        FLOOK_RESET_ID — сбросить сохранённый ID устройства и начать перепоиск.
        Полезно при замене FLOOK32 или смене устройства.
        """
        if self.manual_mode:
            gcmd.respond_info("Ручной режим, сброс ID не требуется")
            return
        
        old_id = self.saved_device_id if self.saved_device_id else "None"
        
        self.saved_device_id = None
        self.flook_ip = None
        self.discovery_complete = False
        self._connected_before = False
        self._device_found_after_reset = False
        self._wrong_id_warning_shown = False
        self._no_device_warning_shown = False
        self._no_id_warning_shown = False
        self._last_critical_ts = 0
        
        self._delete_device_id()
        
        gcmd.respond_info("ID сброшен (был: {})".format(old_id))
        gcmd.respond_info("UDP-цикл сам найдёт устройство за 1-2 итерации...")
    
    def cmd_FLOOK_CALIBRATE(self, gcmd):
        """FLOOK_CALIBRATE TEMP=<эталон> — калибровка MAX6675."""
        temp = gcmd.get_float('TEMP', 100.0, minval=0, maxval=400)
        if not self.flook_ip:
            gcmd.respond_info("Нет подключенного устройства")
            return
        result = self._http_post("/api/calibrate-max6675?temp={}".format(temp))
        if result and ("OK" in result or "success" in result):
            gcmd.respond_info("Калибровка выполнена с эталоном {}°C".format(temp))
        else:
            gcmd.respond_info("Не удалось выполнить калибровку")
    
    # =====================================================================
    # ИНТЕРФЕЙС ДЛЯ KLIPPER
    # =====================================================================
    
    def setup_minmax(self, min_temp, max_temp):
        """Установка диапазона температур (вызывается Klipper)."""
        pass
    
    def get_report_time_delta(self):
        """Возвращает интервал опроса в секундах."""
        return self.report_interval
    
    def setup_callback(self, cb):
        """Устанавливает callback для передачи температуры в Klipper."""
        self._callback = cb
    
    def get_temp(self, eventtime):
        """
        Возвращает текущую температуру воздуха.
        Вызывается Klipper для обновления показаний датчика.
        """
        with self.temp_lock:
            temp = self.air_temp
            if temp < MIN_TEMP or temp > MAX_TEMP:
                temp = 25.0
            return temp, 0.0
    
    def stats(self, eventtime):
        """Возвращает статистику для отчётов Klipper."""
        with self.temp_lock:
            temp = self.air_temp
            status = '{}: воздух={:.1f} цель={:.1f}'.format(
                self.name, temp, self.target_temp)
            if self.flook_ip:
                status += ' ip={}'.format(self.flook_ip)
            return False, status
    
    def close(self):
        """
        Корректное завершение работы: остановка всех потоков,
        закрытие WebSocket и UDP-сокета.
        """
        self.stop_thread = True
        self.udp_running = False
        self._stop_websocket()
        if self.sensor_thread.is_alive():
            self.sensor_thread.join(timeout=2.0)

# ============================================================================
# ТОЧКА ВХОДА ДЛЯ KLIPPER
# ============================================================================

def load_config(config):
    """
    Регистрирует сенсор FLOOK32 в Klipper.
    Вызывается автоматически при загрузке плагина.
    """
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("flook32", FLOOK32Sensor)
