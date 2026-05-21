#!/usr/bin/env zsh
# ─────────────────────────────────────────────────────────
# restart.sh  — WBS & Action Agent 재시작 스크립트
# 사용법:
#   ./restart.sh          # 기본 포트 8553
#   ./restart.sh 8555     # 포트 직접 지정
#   source restart.sh     # source 실행도 지원
# ─────────────────────────────────────────────────────────

# source vs ./ 실행 감지 — exit vs return 구분
_is_sourced=0
[[ "${(%):-%x}" != "$0" ]] && _is_sourced=1
_exit() { (( _is_sourced )) && return "$1" || exit "$1"; }

SCRIPT_DIR="${0:A:h}"
# source 실행 시 $0 가 zsh 이므로 PWD로 fallback
[[ "$SCRIPT_DIR" == "/bin" || "$SCRIPT_DIR" == "/usr/bin" ]] && SCRIPT_DIR="$PWD"

VENV_STREAMLIT="$SCRIPT_DIR/env_WBS_N_Action/bin/streamlit"
DEFAULT_PORT=8553
PORT="${1:-$DEFAULT_PORT}"

is_port_in_use() {
  lsof -iTCP:"$1" -sTCP:LISTEN -t &>/dev/null
}

# ── 1) 기존 Streamlit 프로세스 먼저 종료 ──────────────
echo ""
echo "🔴 기존 Streamlit 프로세스 종료 중..."

PIDS=$(pgrep -f "streamlit run app.py" 2>/dev/null)
if [[ -n "$PIDS" ]]; then
  echo "   종료: PID $PIDS"
  kill $PIDS 2>/dev/null
  sleep 2
  # 아직 살아있으면 강제 종료
  LEFTOVER=$(pgrep -f "streamlit run app.py" 2>/dev/null)
  if [[ -n "$LEFTOVER" ]]; then
    echo "   강제 종료: PID $LEFTOVER"
    kill -9 $LEFTOVER 2>/dev/null
    sleep 1
  fi
else
  echo "   실행 중인 프로세스 없음"
fi

# ── 2) 포트 확인 (종료 후) ────────────────────────────
if is_port_in_use "$PORT"; then
  echo ""
  echo "⚠️  포트 $PORT 가 다른 서비스에 의해 사용 중입니다."
  echo "   점유 프로세스:"
  lsof -iTCP:"$PORT" -sTCP:LISTEN | awk 'NR>1 {printf "   PID %-8s %s\n", $2, $1}'
  echo ""

  while true; do
    printf "   대체 포트 번호 입력 (Enter = 취소): "
    read ALT_PORT
    if [[ -z "$ALT_PORT" ]]; then
      echo "❌ 취소되었습니다."
      _exit 1; return 2>/dev/null
    fi
    if ! [[ "$ALT_PORT" =~ '^[0-9]+$' ]] || (( ALT_PORT < 1024 || ALT_PORT > 65535 )); then
      echo "   ⚠️  유효하지 않은 포트입니다 (1024~65535)."
      continue
    fi
    if is_port_in_use "$ALT_PORT"; then
      echo "   ⚠️  포트 $ALT_PORT 도 사용 중입니다. 다시 입력하세요."
      continue
    fi
    PORT="$ALT_PORT"
    break
  done
fi

# ── 3) 가상환경 확인 ──────────────────────────────────
if [[ ! -f "$VENV_STREAMLIT" ]]; then
  echo "❌ 가상환경을 찾을 수 없습니다: $VENV_STREAMLIT"
  _exit 1; return 2>/dev/null
fi

# ── 4) 앱 시작 ────────────────────────────────────────
echo "🚀 포트 $PORT 에서 앱을 시작합니다..."
echo ""

cd "$SCRIPT_DIR"
nohup "$VENV_STREAMLIT" run app.py \
  --server.port "$PORT" \
  --server.headless true \
  >> "$SCRIPT_DIR/streamlit.log" 2>&1 &

APP_PID=$!
disown "$APP_PID" 2>/dev/null   # source 실행 시 background job 경고 억제

sleep 2

if kill -0 "$APP_PID" 2>/dev/null; then
  echo "✅ 앱 실행 중  (PID: $APP_PID)"
  echo "   Local URL : http://localhost:$PORT"
  echo "   로그 파일 : $SCRIPT_DIR/streamlit.log"
  echo ""
  echo "   종료: kill $APP_PID   |   재시작: ./restart.sh $PORT"
else
  echo "❌ 앱 시작 실패. 최근 로그:"
  tail -20 "$SCRIPT_DIR/streamlit.log"
  _exit 1; return 2>/dev/null
fi
