#!/usr/bin/env bash

set -euo pipefail

GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-Admin123}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="${SCRIPT_DIR}/grafana/provisioning/dashboards"

declare -A DASHBOARDS=(
  ["node_exporter"]="1860"
  ["cadvisor"]="14282"
  ["postgres"]="9628"
  ["redis"]="763"
  ["nginx_vts"]="2949"
)

check_deps() {
  for cmd in curl jq; do
    if ! command -v "$cmd" &>/dev/null; then
      echo "❌ Требуется '$cmd'. Установите: apt install $cmd / brew install $cmd"
      exit 1
    fi
  done
}

wait_for_grafana() {
  echo "⏳ Ожидаем готовности Grafana ($GRAFANA_URL)..."
  local max_attempts=30
  local attempt=0
  until curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    "${GRAFANA_URL}/api/health" | jq -r '.database' | grep -q "ok"; do
    attempt=$((attempt + 1))
    if [[ $attempt -ge $max_attempts ]]; then
      echo "❌ Grafana не ответила за ${max_attempts} попыток. Проверьте что контейнер запущен."
      exit 1
    fi
    echo "   Попытка ${attempt}/${max_attempts}..."
    sleep 3
  done
  echo "✅ Grafana готова"
}

download_dashboard() {
  local name="$1"
  local dashboard_id="$2"
  local output_file="${DASHBOARDS_DIR}/${name}_${dashboard_id}.json"

  echo "📥 Скачиваем: ${name} (ID: ${dashboard_id})"

  local meta_url="https://grafana.com/api/dashboards/${dashboard_id}/revisions/latest/download"
  local raw_json

  raw_json=$(curl -sf --max-time 30 "$meta_url") || {
    echo "   ⚠️  Не удалось скачать дашборд ${dashboard_id} с grafana.com. Пропускаем."
    return
  }

  local wrapped_json
  wrapped_json=$(echo "$raw_json" | jq '{
    dashboard: (. + {id: null, uid: null}),
    overwrite: true,
    folderId: 0,
    inputs: []
  }')

  local result
  result=$(curl -sf \
    -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
    -H "Content-Type: application/json" \
    -d "$wrapped_json" \
    "${GRAFANA_URL}/api/dashboards/import") || {
    echo "   ⚠️  Ошибка импорта через API. Сохраняем raw JSON для ручного импорта."
    echo "$raw_json" > "$output_file"
    echo "   💾 Сохранён: ${output_file}"
    return
  }

  local uid
  uid=$(echo "$result" | jq -r '.uid // empty')

  if [[ -n "$uid" ]]; then
    curl -sf \
      -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
      "${GRAFANA_URL}/api/dashboards/uid/${uid}" \
      | jq '.dashboard' \
      > "$output_file"
    echo "   ✅ Импортирован и сохранён: ${output_file} (uid: ${uid})"
  else
    echo "$raw_json" > "$output_file"
    echo "   ✅ Сохранён raw JSON: ${output_file}"
  fi
}

main() {
  check_deps
  mkdir -p "$DASHBOARDS_DIR"
  wait_for_grafana

  echo ""
  echo "📊 Скачиваем дашборды..."
  echo ""

  for name in "${!DASHBOARDS[@]}"; do
    download_dashboard "$name" "${DASHBOARDS[$name]}"
  done

  echo ""
  echo "🎉 Готово! Файлы в: ${DASHBOARDS_DIR}"
  echo ""
  echo "   Если Grafana уже запущена — выполни для применения:"
  echo "   docker-compose restart grafana"
}

main "$@"