#!/bin/bash
# ============================================================================
# Прошивка ESP-01S Watchdog (Linux/macOS)
# Использование: ./flash_esp01s.sh
# ============================================================================
set -e
cd "$(dirname "$0")"

FIRMWARE_URL="https://raw.githubusercontent.com/schreider/flook32/main/firmware/esp01s_watchdog/esp01s_watchdog_flash.bin"

clear
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""
echo "        ╔══════════════════════════════════════════╗"
echo "        ║       🔌 Прошивка ESP-01S Watchdog       ║"
echo "        ╚══════════════════════════════════════════╝"
echo ""
echo "  ███████╗██╗      ██████╗  ██████╗ ██╗  ██╗ ██████╗ ██████╗"
echo "  ██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝ ╚════██╗╚════██╗"
echo "  █████╗  ██║     ██║   ██║██║   ██║█████╔╝   █████╔╝ █████╔╝"
echo "  ██╔══╝  ██║     ██║   ██║██║   ██║██╔═██╗   ╚═══██╗██╔═══╝"
echo "  ██║     ███████╗╚██████╔╝╚██████╔╝██║  ██╗ ██████╔╝███████╗"
echo "  ╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""
echo ""

# ===== 1. Установка esptool через pip (если нет) =====
if ! command -v esptool.py &>/dev/null; then
    echo "   📥 Устанавливаю esptool..."
    pip3 install esptool 2>/dev/null || pip install esptool 2>/dev/null || {
        echo "   ❌ Не удалось установить esptool"
        echo "      Установите вручную: pip3 install esptool"
        exit 1
    }
    echo "   ✅ esptool установлен"
else
    echo "   ✅ esptool уже есть"
fi

# ===== 2. Ищем или скачиваем прошивку =====
FIRMWARE="$(dirname "$0")/esp01s_watchdog_flash.bin"

if [ -f "$FIRMWARE" ] && [ -s "$FIRMWARE" ]; then
    echo "   ✅ Прошивка найдена локально"
else
    echo "   📥 Скачиваю прошивку..."
    curl -sL "$FIRMWARE_URL" -o "$FIRMWARE"
    if [ -f "$FIRMWARE" ] && [ -s "$FIRMWARE" ]; then
        echo "   ✅ Прошивка загружена"
    else
        echo "   ❌ Не удалось скачать прошивку"
        echo "      Проверьте интернет"
        exit 1
    fi
fi

# ===== 3. Ищем ESP-01S =====
echo ""
echo "   🔍 Поиск ESP-01S..."
echo ""

PORT=""
for dev in /dev/ttyUSB* /dev/ttyACM* /dev/cu.usbserial* /dev/cu.SLAB_USBtoUART*; do
    if [ -e "$dev" ]; then
        echo "   ├─ Пробуем $dev..."
        if esptool.py --port "$dev" --chip esp8266 --baud 115200 flash_id &>/dev/null; then
            PORT="$dev"
            echo "   └─ ✅ Найден на $dev"
            break
        fi
    fi
done

if [ -z "$PORT" ]; then
    echo "   └─ ❌ ESP-01S не найден"
    echo ""
    echo "   🔧 Проверьте:"
    echo "   ┌─ Подключён ли USB-программатор"
    echo "   ├─ Перемычка GPIO0 на GND (режим прошивки)"
    echo "   └─ Внешнее питание 3.3В"
    exit 1
fi

# ===== 4. Прошиваем =====
echo ""
echo "   ⚡ Прошивка..."
echo "   ┌─ Порт: $PORT"
echo "   └─ Файл: esp01s_watchdog_flash.bin"
echo ""

esptool.py --port "$PORT" --chip esp8266 --baud 115200 --before default-reset --after hard-reset write-flash -z 0x0 "$FIRMWARE"

if [ $? -ne 0 ]; then
    echo ""
    echo "   ❌ Ошибка прошивки!"
    echo ""
    echo "   🔧 Попробуйте:"
    echo "   ┌─ Проверить перемычку GPIO0-GND"
    echo "   ├─ Нажать RESET на программаторе"
    echo "   └─ Подать внешние 3.3В"
    exit 1
fi

echo ""
echo "   ╔══════════════════════════════════════════╗"
echo "   ║                                          ║"
echo "   ║     ✅  ПРОШИВКА ESP-01S ЗАВЕРШЕНА!      ║"
echo "   ║                                          ║"
echo "   ║     🔄  Снимите перемычку GPIO0-GND       ║"
echo "   ║     🔌  Переподключите питание            ║"
echo "   ║                                          ║"
echo "   ╚══════════════════════════════════════════╝"
echo ""
echo "   🔗 https://github.com/schreider/flook32"