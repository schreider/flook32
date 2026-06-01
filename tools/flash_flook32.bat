@echo off
chcp 65001 >nul
title Прошивка FLOOK32
cls
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo        ╔══════════════════════════════════════════╗
echo        ║          🔌 Прошивка FLOOK32             ║
echo        ╚══════════════════════════════════════════╝
echo.
echo  ███████╗██╗      ██████╗  ██████╗ ██╗  ██╗ ██████╗ ██████╗
echo  ██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝ ╚════██╗╚════██╗
echo  █████╗  ██║     ██║   ██║██║   ██║█████╔╝   █████╔╝ █████╔╝
echo  ██╔══╝  ██║     ██║   ██║██║   ██║██╔═██╗   ╚═══██╗██╔═══╝
echo  ██║     ███████╗╚██████╔╝╚██████╔╝██║  ██╗ ██████╔╝███████╗
echo  ╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo.
echo.                  Контроллер термокамеры

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

:: ===== 2. Получаем последнюю версию из latest.json =====
set FIRMWARE=%~dp0flook32_flash.bin
set LATEST_JSON_URL=https://raw.githubusercontent.com/schreider/flook32/main/firmware/flook32/latest.json

echo   📥 Проверяю последнюю версию...

powershell -Command "$json = Invoke-WebRequest -Uri '%LATEST_JSON_URL%' -UseBasicParsing | ConvertFrom-Json; Write-Output $json.version; Write-Output $json.flash_url" > "%TEMP%\ota_info.txt" 2>nul

if not exist "%TEMP%\ota_info.txt" (
    echo   ❌ Не удалось проверить версию
    pause
    exit /b 1
)

set /p LATEST_VER=<"%TEMP%\ota_info.txt"
set FIRMWARE_URL=
for /f "skip=1 delims=" %%a in (%TEMP%\ota_info.txt) do if not defined FIRMWARE_URL set "FIRMWARE_URL=%%a"
del "%TEMP%\ota_info.txt" 2>nul

if "%LATEST_VER%"=="" (
    echo   ❌ Не удалось определить версию
    pause
    exit /b 1
)

echo   ✅ Последняя версия: v%LATEST_VER%

:: ===== 3. Проверяем локальный файл или скачиваем =====
if exist "%FIRMWARE%" (
    echo   ✅ Прошивка найдена локально
) else (
    echo   📥 Скачиваю flook32_flash.bin v%LATEST_VER%...
    powershell -Command "Invoke-WebRequest -Uri '%FIRMWARE_URL%' -OutFile '%FIRMWARE%'" 2>nul
    if exist "%FIRMWARE%" (
        echo   ✅ Прошивка загружена
    ) else (
        echo   ❌ Не удалось скачать прошивку
        echo      Проверьте интернет
        pause
        exit /b 1
    )
)

:: ===== 4. Ищем ESP32 =====
echo.
echo   🔍 Поиск ESP32...
echo.
set PORT=

for /f "usebackq tokens=1" %%a in (`powershell -Command "[System.IO.Ports.SerialPort]::GetPortNames() | ForEach-Object { $_ }"`) do (
    echo   ├─ Пробуем %%a...
    "%ESPTOOL%" --port %%a --chip esp32 --baud 460800 flash_id >nul 2>&1
    if not errorlevel 1 (
        set PORT=%%a
        echo   └─ ✅ Найден на %%a
        goto :flash
    )
)

echo   └─ ❌ ESP32 не найден
echo.
echo   🔧 Проверьте:
echo   ┌─ Подключён ли USB-кабель
echo   ├─ Установлен ли драйвер CH340/CP210x
echo   └─ BOOT+EN → режим загрузки
pause
exit /b 1

:: ===== 5. Прошиваем =====
:flash
echo.
echo   ⚡ Прошивка v%LATEST_VER%...
echo   ┌─ Порт: %PORT%
echo   └─ Файл: flook32_flash.bin
echo.

"%ESPTOOL%" --port %PORT% --chip esp32 --baud 460800 --before default-reset --after hard-reset write-flash -z 0x0 "%FIRMWARE%"

if errorlevel 1 (
    echo.
    echo   ❌ Ошибка прошивки!
    echo.
    echo   🔧 Попробуйте:
    echo   ┌─ BOOT+EN → режим загрузки
    echo   ├─ Проверить драйвер CH340/CP210x
    echo   └─ Data-кабель, не зарядка
    pause
    exit /b 1
)

echo.
echo         ПРОШИВКА v%LATEST_VER% ЗАВЕРШЕНА!  
echo   ╔══════════════════════════════════════════╗
echo   ║                                          ║
echo   ║             Перезагрузка...              ║
echo   ║         Точка доступа через 10 сек:      ║
echo   ║             FLOOK32-XXXX                 ║
echo   ║           Пароль: flook1234              ║
echo   ║                                          ║
echo   ╚══════════════════════════════════════════╝
echo.
echo   🔗 https://github.com/schreider/flook32
timeout /t 5 >nul
