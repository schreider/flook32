@echo off
chcp 65001 >nul
:: ============================================================================
:: Сборка веб-ресурсов в C-массивы для прошивки FLOOK32
:: Использование: compress_webui.bat
:: Результат: index_html_gz.h, favicon_ico.h, icon_192_png_gz.h, chart_min_js_gz.h, chartjs_adapter_gz.h
:: ============================================================================
cd /d "%~dp0"

set CHART_URL=https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js
set ADAPTER_URL=https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js
set SRC_URL=https://raw.githubusercontent.com/schreider/flook32/main/firmware/flook32/src

cls
echo.
echo         ╔══════════════════════════════════════════╗
echo         ║       Сборка веб-ресурсов FLOOK32        ║
echo         ╚══════════════════════════════════════════╝
echo.
echo  ███████╗██╗      ██████╗  ██████╗ ██╗  ██╗ ██████╗ ██████╗
echo  ██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝ ╚════██╗╚════██╗
echo  █████╗  ██║     ██║   ██║██║   ██║█████╔╝   █████╔╝ █████╔╝
echo  ██╔══╝  ██║     ██║   ██║██║   ██║██╔═██╗   ╚═══██╗██╔═══╝
echo  ██║     ███████╗╚██████╔╝╚██████╔╝██║  ██╗ ██████╔╝███████╗
echo  ╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo.
echo                      t.me/schreid
echo               github.com/schreider/flook32
echo.

:: Создаём папку src если нет
if not exist "src" mkdir "src"

:: ----- index.html -----
if not exist "src\index.html" (
    echo   ├─ Скачивание index.html...
    powershell -Command "Invoke-WebRequest -Uri '%SRC_URL%/index.html' -OutFile 'src\index.html'" 2>nul
)
echo   ├─ index.html → index_html_gz.h
powershell -Command "$in=[System.IO.File]::ReadAllBytes('src\index.html'); $out=New-Object System.IO.MemoryStream; $gz=New-Object System.IO.Compression.GzipStream($out,[System.IO.Compression.CompressionMode]::Compress); $gz.Write($in,0,$in.Length); $gz.Close(); [System.IO.File]::WriteAllBytes('index.html.gz',$out.ToArray())" 2>nul
powershell -Command "$b=[System.IO.File]::ReadAllBytes('index.html.gz'); $h=($b|%%{'0x{0:X2},' -f $_}) -join ' '; $c='const unsigned char index_html_gz[] PROGMEM = {'+[Environment]::NewLine+'  '+$h+[Environment]::NewLine+'};'+[Environment]::NewLine+'const unsigned int index_html_gz_len = '+$b.Length+';'+[Environment]::NewLine; [System.IO.File]::WriteAllText('index_html_gz.h',$c,[System.Text.Encoding]::ASCII)" 2>nul
del index.html.gz 2>nul
echo   └─ ✅ Готово

:: ----- favicon.ico -----
if not exist "src\favicon.ico" (
    echo   ├─ Скачивание favicon.ico...
    powershell -Command "Invoke-WebRequest -Uri '%SRC_URL%/favicon.ico' -OutFile 'src\favicon.ico'" 2>nul
)
echo   ├─ favicon.ico → favicon_ico.h
powershell -Command "$b=[System.IO.File]::ReadAllBytes('src\favicon.ico'); $h=($b|%%{'0x{0:X2},' -f $_}) -join ' '; $c='const unsigned char favicon_ico[] PROGMEM = {'+[Environment]::NewLine+'  '+$h+[Environment]::NewLine+'};'+[Environment]::NewLine+'const unsigned int favicon_ico_len = '+$b.Length+';'+[Environment]::NewLine; [System.IO.File]::WriteAllText('favicon_ico.h',$c,[System.Text.Encoding]::ASCII)" 2>nul
echo   └─ ✅ Готово

:: ----- icon-192.png -----
if not exist "src\icon_192.png" (
    echo   ├─ Скачивание icon_192.png...
    powershell -Command "Invoke-WebRequest -Uri '%SRC_URL%/icon_192.png' -OutFile 'src\icon_192.png'" 2>nul
)
echo   ├─ icon_192.png → icon_192_png_gz.h
powershell -Command "$in=[System.IO.File]::ReadAllBytes('src\icon_192.png'); $out=New-Object System.IO.MemoryStream; $gz=New-Object System.IO.Compression.GzipStream($out,[System.IO.Compression.CompressionMode]::Compress); $gz.Write($in,0,$in.Length); $gz.Close(); [System.IO.File]::WriteAllBytes('icon_192.png.gz',$out.ToArray())" 2>nul
powershell -Command "$b=[System.IO.File]::ReadAllBytes('icon_192.png.gz'); $h=($b|%%{'0x{0:X2},' -f $_}) -join ' '; $c='const unsigned char icon_192_png_gz[] PROGMEM = {'+[Environment]::NewLine+'  '+$h+[Environment]::NewLine+'};'+[Environment]::NewLine+'const unsigned int icon_192_png_gz_len = '+$b.Length+';'+[Environment]::NewLine; [System.IO.File]::WriteAllText('icon_192_png_gz.h',$c,[System.Text.Encoding]::ASCII)" 2>nul
del icon_192.png.gz 2>nul
echo   └─ ✅ Готово

:: ----- Chart.js -----
echo   ├─ Скачивание Chart.js...
powershell -Command "Invoke-WebRequest -Uri '%CHART_URL%' -OutFile 'chart.min.js'" 2>nul
echo   ├─ chart.min.js → chart_min_js_gz.h
powershell -Command "$in=[System.IO.File]::ReadAllBytes('chart.min.js'); $out=New-Object System.IO.MemoryStream; $gz=New-Object System.IO.Compression.GzipStream($out,[System.IO.Compression.CompressionMode]::Compress); $gz.Write($in,0,$in.Length); $gz.Close(); [System.IO.File]::WriteAllBytes('chart.min.js.gz',$out.ToArray())" 2>nul
powershell -Command "$b=[System.IO.File]::ReadAllBytes('chart.min.js.gz'); $h=($b|%%{'0x{0:X2},' -f $_}) -join ' '; $c='const unsigned char chart_min_js_gz[] PROGMEM = {'+[Environment]::NewLine+'  '+$h+[Environment]::NewLine+'};'+[Environment]::NewLine+'const unsigned int chart_min_js_gz_len = '+$b.Length+';'+[Environment]::NewLine; [System.IO.File]::WriteAllText('chart_min_js_gz.h',$c,[System.Text.Encoding]::ASCII)" 2>nul
del chart.min.js chart.min.js.gz 2>nul
echo   └─ ✅ Готово

:: ----- Chart.js Adapter -----
echo   ├─ Скачивание Chart.js Adapter...
powershell -Command "Invoke-WebRequest -Uri '%ADAPTER_URL%' -OutFile 'adapter.js'" 2>nul
echo   ├─ adapter.js → chartjs_adapter_gz.h
powershell -Command "$in=[System.IO.File]::ReadAllBytes('adapter.js'); $out=New-Object System.IO.MemoryStream; $gz=New-Object System.IO.Compression.GzipStream($out,[System.IO.Compression.CompressionMode]::Compress); $gz.Write($in,0,$in.Length); $gz.Close(); [System.IO.File]::WriteAllBytes('adapter.js.gz',$out.ToArray())" 2>nul
powershell -Command "$b=[System.IO.File]::ReadAllBytes('adapter.js.gz'); $h=($b|%%{'0x{0:X2},' -f $_}) -join ' '; $c='const unsigned char chartjs_adapter_gz[] PROGMEM = {'+[Environment]::NewLine+'  '+$h+[Environment]::NewLine+'};'+[Environment]::NewLine+'const unsigned int chartjs_adapter_gz_len = '+$b.Length+';'+[Environment]::NewLine; [System.IO.File]::WriteAllText('chartjs_adapter_gz.h',$c,[System.Text.Encoding]::ASCII)" 2>nul
del adapter.js adapter.js.gz 2>nul
echo   └─ ✅ Готово

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║         ✅  СБОРКА ЗАВЕРШЕНА!            ║
echo   ║                                          ║
echo   ║            index_html_gz.h               ║
echo   ║            favicon_ico.h                 ║
echo   ║            icon_192_png_gz.h             ║
echo   ║            chart_min_js_gz.h             ║
echo   ║            chartjs_adapter_gz.h          ║
echo   ╚══════════════════════════════════════════╝
echo.
pause