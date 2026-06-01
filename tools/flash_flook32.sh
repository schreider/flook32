#!/bin/bash
# ============================================================================
# Прошивка FLOOK32 (Linux/macOS)
# Использование: ./flash_flook32.sh
# ============================================================================
set -e
cd "$(dirname "$0")"

LATEST_JSON_URL="https://raw.githubusercontent.com/schreider/flook32/main/firmware/flook32/latest.json"

clear
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""
echo "        ╔══════════════════════════════════════════╗"
echo "        ║          🔌 Прошивка FLOOK32             ║"
echo "        ╚══════════════════════════════════════════╝"
echo ""
echo "  ███████╗██╗      ██████╗  ██████╗ ██╗  ██╗ ██████╗ ██████╗"
echo "  ██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝ ╚════██╗╚════██╗"
echo "  █████╗  ██║     ██║   ██║██║   ██║█████╔╝   █████╔╝ █████╔╝"
echo "  ██╔══╝  ██║     ██║   ██║██║   ██║██╔═██╗   ╚═══██╗██╔═══╝"
echo "  ██║     ███████╗╚██████╔╝╚██████╔╝██║  ██╗ ██████╔╝███████╗"
echo "  ╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""
echo "                  Контроллер термокамеры"
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

# ===== 2. Получаем последнюю версию из latest.json =====
echo "   📥 Проверяю последнюю версию..."

JSON=$(curl -sL "$LATEST_JSON_URL")
LATEST_VER=$(echo "$JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null)
FIRMWARE_URL=$(echo "$JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['flash_url'])" 2>/dev/null)

if [ -z "$LATEST_VER" ] || [ -z "$FIRMWARE_URL" ]; then
    echo "   ❌ Не удалось определить версию"
    exit 1
fi

echo "   ✅ Последняя версия: v$LATEST_VER"

# ===== 3. Проверяем локальный файл или скачиваем =====
FIRMWARE="$(dirname "$0")/flook32_flash.bin"

if [ -f "$FIRMWARE" ] && [ -s "$FIRMWARE" ]; then
    echo "   ✅ Прошивка найдена локально"
else
    echo "   📥 Скачиваю flook32_flash.bin v$LATEST_VER..."
    curl -sL "$FIRMWARE_URL" -o "$FIRMWARE"
    if [ -f "$FIRMWARE" ] && [ -s "$FIRMWARE" ]; then
        echo "   ✅ Прошивка загружена"
    else
        echo "   ❌ Не удалось скачать прошивку"
        echo "      Проверьте интернет"
        exit 1
    fi
fi

# ===== 4. Ищем ESP32 =====
echo ""
echo "   🔍 Поиск ESP32..."
echo ""

PORT=""
for dev in /dev/ttyUSB* /dev/ttyACM* /dev/cu.usbserial* /dev/cu.SLAB_USBtoUART*; do
    if [ -e "$dev" ]; then
        echo "   ├─ Пробуем $dev..."
        if esptool.py --port "$dev" --chip esp32 --baud 460800 flash_id &>/dev/null; then
            PORT="$dev"
            echo "   └─ ✅ Найден на $dev"
            break
        fi
    fi
done

if [ -z "$PORT" ]; then
    echo "   └─ ❌ ESP32 не найден"
    echo ""
    echo "   🔧 Проверьте:"
    echo "   ┌─ Подключён ли USB-кабель"
    echo "   ├─ Права: sudo usermod -a -G dialout \$USER"
    echo "   └─ BOOT+EN → режим загрузки"
    exit 1
fi

# ===== 5. Прошиваем =====
echo ""
echo "   ⚡ Прошивка v$LATEST_VER..."
echo "   ┌─ Порт: $PORT"
echo "   └─ Файл: flook32_flash.bin"
echo ""

esptool.py --port "$PORT" --chip esp32 --baud 460800 --before default-reset --after hard-reset write-flash -z 0x0 "$FIRMWARE"

if [ $? -ne 0 ]; then
    echo ""
    echo "   ❌ Ошибка прошивки!"
    echo ""
    echo "   🔧 Попробуйте:"
    echo "   ┌─ BOOT+EN → режим загрузки"
    echo "   ├─ Проверить драйвер CH340/CP210x"
    echo "   └─ Data-кабель, не зарядка"
    exit 1
fi

echo ""
echo "   ╔══════════════════════════════════════════╗"
echo "   ║                                          ║"
echo "   ║     ✅  ПРОШИВКА v$LATEST_VER ЗАВЕРШЕНА!  ║"
echo "   ║                                          ║"
echo "   ║     🔄  Перезагрузка...                   ║"
echo "   ║     📡  Точка доступа через 10 сек:       ║"
echo "   ║         FLOOK32-XXXX                      ║"
echo "   ║         Пароль: flook1234                 ║"
echo "   ║                                          ║"
echo "   ╚══════════════════════════════════════════╝"
echo ""
echo "   🔗 https://github.com/schreider/flook32"
