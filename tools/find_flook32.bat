@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Поиск FLOOK32
cls
echo.
echo       ╔══════════════════════════════════════════╗
echo       ║        🔍 Поиск FLOOK32 в сети           ║
echo       ╚══════════════════════════════════════════╝
echo.
echo  ███████╗██╗      ██████╗  ██████╗ ██╗  ██╗ ██████╗ ██████╗
echo  ██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝ ╚════██╗╚════██╗
echo  █████╗  ██║     ██║   ██║██║   ██║█████╔╝   █████╔╝ █████╔╝
echo  ██╔══╝  ██║     ██║   ██║██║   ██║██╔═██╗   ╚═══██╗██╔═══╝
echo  ██║     ███████╗╚██████╔╝╚██████╔╝██║  ██╗ ██████╔╝███████╗
echo  ╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo.
echo                   Контроллер термокамеры
echo.
echo   🌐 Локальная сеть: 192.168.1.0/24
echo   🔍 Сканирование порта 80...
echo.
echo   ┌────────────────────────────────────────┐

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do set "localIP=%%a" & goto :gotIP
:gotIP
set "localIP=%localIP: =%"
for /f "tokens=1-3 delims=." %%a in ("%localIP%") do set "net=%%a.%%b.%%c"

set found=0
set lastbar=0
for /l %%i in (2,1,254) do (
    curl -s -m 0.3 http://%net%.%%i/api/all 2>nul | find """k"":" >nul && (
        set found=1
        set foundIP=%net%.%%i
        goto :found
    )
    set /a "bar=%%i*30/254"
    if !bar! gtr !lastbar! (
        set lastbar=!bar!
        set "line=   │ "
        for /l %%j in (1,1,!bar!) do set "line=!line!▓"
        for /l %%j in (!bar!,1,29) do set "line=!line!░"
        set /a "pct=!bar!*100/30"
        set "line=!line! │ !pct!%%"
        echo !line!
    )
)

:found
echo   └────────────────────────────────────────┘
echo.
if "%found%"=="1" (
    echo.
    echo   ✅  УСТРОЙСТВО НАЙДЕНО!
    echo.
    echo   🌐  http://%foundIP%
    echo.
    echo   ┌─ Запуск браузера...
    echo   └─ ⏳
    timeout /t 1 >nul
    start http://%foundIP%
) else (
    echo.
    echo   ❌  УСТРОЙСТВО НЕ НАЙДЕНО
    echo.
    echo   📡  Подключитесь к точке доступа:
    echo   ┌─ SSID: FLOOK32-XXXX
    echo   ├─ Пароль: flook1234
    echo   └─ http://192.168.4.1
)
echo.
pause >nul