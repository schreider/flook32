#!/bin/bash
# ============================================================================
# Сборка веб-ресурсов в C-массивы для прошивки FLOOK32
# Использование: ./compress_webui.sh
# Результат: index_html_gz.h, favicon_ico.h, icon_192_png_gz.h, chart_min_js_gz.h, chartjs_adapter_gz.h
# ============================================================================
set -e
cd "$(dirname "$0")"

CHART_URL="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"
ADAPTER_URL="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"

clear
echo ""
echo "        ╔══════════════════════════════════════════╗"
echo "        ║       Сборка веб-ресурсов FLOOK32        ║"
echo "        ╚══════════════════════════════════════════╝"
echo ""
echo "  ███████╗██╗      ██████╗  ██████╗ ██╗  ██╗ ██████╗ ██████╗"
echo "  ██╔════╝██║     ██╔═══██╗██╔═══██╗██║ ██╔╝ ╚════██╗╚════██╗"
echo "  █████╗  ██║     ██║   ██║██║   ██║█████╔╝   █████╔╝ █████╔╝"
echo "  ██╔══╝  ██║     ██║   ██║██║   ██║██╔═██╗   ╚═══██╗██╔═══╝"
echo "  ██║     ███████╗╚██████╔╝╚██████╔╝██║  ██╗ ██████╔╝███████╗"
echo "  ╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""
echo "                     t.me/schreid"
echo "             github.com/schreider/flook32"
echo ""

# ----- index.html -----
echo "  ├─ index.html → index_html_gz.h"
gzip -9 -c src/index.html > index.html.gz
xxd -i -n index_html_gz index.html.gz | \
    sed 's/unsigned char index_html_gz\[\] = {/const unsigned char index_html_gz\[\] PROGMEM = {/' \
    > index_html_gz.h
rm index.html.gz
echo "  └─ ✅ Готово"

# ----- favicon.ico -----
echo "  ├─ favicon.ico → favicon_ico.h"
xxd -i -n favicon_ico src/favicon.ico | \
    sed 's/unsigned char favicon_ico\[\] = {/const unsigned char favicon_ico\[\] PROGMEM = {/' \
    > favicon_ico.h
echo "  └─ ✅ Готово"

# ----- icon-192.png -----
echo "  ├─ icon_192.png → icon_192_png_gz.h"
gzip -9 -c src/icon_192.png > icon_192.png.gz
xxd -i -n icon_192_png_gz icon_192.png.gz | \
    sed 's/unsigned char icon_192_png_gz\[\] = {/const unsigned char icon_192_png_gz\[\] PROGMEM = {/' \
    > icon_192_png_gz.h
rm icon_192.png.gz
echo "  └─ ✅ Готово"

# ----- Chart.js -----
echo "  ├─ Скачивание Chart.js..."
curl -sL "$CHART_URL" -o chart.min.js
echo "  ├─ chart.min.js → chart_min_js_gz.h"
gzip -9 -c chart.min.js > chart.min.js.gz
xxd -i -n chart_min_js_gz chart.min.js.gz | \
    sed 's/unsigned char chart_min_js_gz\[\] = {/const unsigned char chart_min_js_gz\[\] PROGMEM = {/' \
    > chart_min_js_gz.h
rm chart.min.js chart.min.js.gz
echo "  └─ ✅ Готово"

# ----- Chart.js Adapter -----
echo "  ├─ Скачивание Chart.js Adapter..."
curl -sL "$ADAPTER_URL" -o adapter.js
echo "  ├─ adapter.js → chartjs_adapter_gz.h"
gzip -9 -c adapter.js > adapter.js.gz
xxd -i -n chartjs_adapter_gz adapter.js.gz | \
    sed 's/unsigned char chartjs_adapter_gz\[\] = {/const unsigned char chartjs_adapter_gz\[\] PROGMEM = {/' \
    > chartjs_adapter_gz.h
rm adapter.js adapter.js.gz
echo "  └─ ✅ Готово"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║         ✅  СБОРКА ЗАВЕРШЕНА!            ║"
echo "  ║                                          ║"
echo "  ║            index_html_gz.h               ║"
echo "  ║            favicon_ico.h                 ║"
echo "  ║            icon_192_png_gz.h             ║"
echo "  ║            chart_min_js_gz.h             ║"
echo "  ║            chartjs_adapter_gz.h          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""