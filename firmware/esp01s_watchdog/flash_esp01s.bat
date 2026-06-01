@echo off
chcp 65001 >nul
title Прошивка ESP-01S (Watchdog)
cls
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo        ╔══════════════════════════════════════════╗
echo        ║       🔌 Прошивка ESP-01S Watchdog       ║
echo        ╚══════════════════════════════════════════╝
echo.
echo  ███████╗██╗      ██████╗  ██████╗ ██╗  ██╗ ██████╗ ██████╗
echo  ██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝ ╚════██╗╚════██╗
echo  █████╗  ██║     ██║   ██║██║   ██║█████╔╝   █████╔╝ █████╔╝
echo  ██╔══╝  ██║     ██║   ██║██║   ██║██╔═██╗   ╚═══██╗██╔═══╝
echo  ██║     ███████╗╚██████╔╝╚██████╔╝██║  ██╗ ██████╔╝███████╗
echo  ╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo.
echo.                 

:: ===== 1. Скачиваем esptool если нет =====
set ESPTOOL=%~dp0esptool.exe
set ESPTOOL_URL=https://github.com/espressif/esptool/releases/download/v5.2.0/esptool-v5.2.0-windows-amd64.zip

if not exist "%ESPTOOL%" (
    echo.
    echo   📥 Скачиваю esptool...
    powershell -Command "Invoke-WebRequest -Uri '%ESPTOOL_URL%' -OutFile '%TEMP%\esptool.zip'" 2>nul
    powershell -Command "Expand-Archive -Path '%TEMP%\esptool.zip' -DestinationPath '%TEMP%\esptool_tmp' -Force" 2>nul
    for /r "%TEMP%\esptool_tmp" %%f in (esptool.exe) do copy "%%f" "%ESPTOOL%" >nul 2>&1
    del "%TEMP%\esptool.zip" /q 2>nul
    rmdir "%TEMP%\esptool_tmp" /s /q 2>nul
    if exist "%ESPTOOL%" (
        echo   ✅ esptool готов
    ) else (
        echo   ❌ Не удалось скачать esptool
        pause
        exit /b 1
    )
) else (
    echo   ✅ esptool уже есть
)

:: ===== 2. Скачиваем прошивку из репозитория =====
set FIRMWARE=%~dp0esp01s_watchdog_flash.bin
set FIRMWARE_URL=https://raw.githubusercontent.com/schreider/flook32/main/firmware/esp01s_watchdog/esp01s_watchdog_flash.bin

echo   📥 Скачиваю прошивку...
powershell -Command "Invoke-WebRequest -Uri '%FIRMWARE_URL%' -OutFile '%FIRMWARE%'" 2>nul

if exist "%FIRMWARE%" (
    echo   ✅ Прошивка загружена
) else (
    echo   ❌ Не удалось скачать прошивку
    echo      Проверьте интернет
    pause
    exit /b 1
)

:: ===== 3. Ищем ESP-01S =====
echo.
echo   🔍 Поиск ESP-01S...
echo.
set PORT=

for /f "usebackq tokens=1" %%a in (`powershell -Command "[System.IO.Ports.SerialPort]::GetPortNames() | ForEach-Object { $_ }"`) do (
    echo   ├─ Пробуем %%a...
    "%ESPTOOL%" --port %%a --chip esp8266 --baud 115200 flash_id >nul 2>&1
    if not errorlevel 1 (
        set PORT=%%a
        echo   └─ ✅ Найден на %%a
        goto :flash
    )
)

echo   └─ ❌ ESP-01S не найден
echo.
echo   🔧 Проверьте:
echo   ┌─ Подключён ли USB-программатор
echo   ├─ Перемычка GPIO0 на GND (режим прошивки)
echo   └─ Внешнее питание 3.3В
pause
exit /b 1

:: ===== 4. Прошиваем =====
:flash
echo.
echo   ⚡ Прошивка...
echo   ┌─ Порт: %PORT%
echo   └─ Файл: esp01s_watchdog_flash.bin
echo.

"%ESPTOOL%" --port %PORT% --chip esp8266 --baud 115200 --before default-reset --after hard-reset write-flash -z 0x0 "%FIRMWARE%"

if errorlevel 1 (
    echo.
    echo   ❌ Ошибка прошивки!
    echo.
    echo   🔧 Попробуйте:
    echo   ┌─ Проверить перемычку GPIO0-GND
    echo   ├─ Нажать RESET на программаторе
    echo   └─ Подать внешние 3.3В
    pause
    exit /b 1
)

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║                                          ║
echo   ║     ✅  ПРОШИВКА ESP-01S ЗАВЕРШЕНА!      ║
echo   ║                                          ║
echo   ║     🔄  Снимите перемычку GPIO0-GND       ║
echo   ║     🔌  Переподключите питание            ║
echo   ║                                          ║
echo   ╚══════════════════════════════════════════╝
echo.
echo   🔗 https://github.com/schreider/flook32
timeout /t 5 >nul