# 관리자 가이드 — Project Agent (WBS & Action Item 관리)

> SAP Sales Process ERP 구현 프로젝트 관리 도구  
> 서버 설정, 서비스 관리, 백업/복구, 트러블슈팅을 위한 관리자 문서

---

## 목차

1. [시스템 요구사항](#1-시스템-요구사항)
2. [최초 설치 절차](#2-최초-설치-절차)
3. [서비스 관리 (restart.sh)](#3-서비스-관리-restartsh)
4. [포트 설정](#4-포트-설정)
5. [LLM 설정](#5-llm-설정)
6. [DB 백업 및 복구](#6-db-백업-및-복구)
7. [로그 파일 관리](#7-로그-파일-관리)
8. [보안 고려사항](#8-보안-고려사항)
9. [트러블슈팅](#9-트러블슈팅)
10. [업데이트 절차](#10-업데이트-절차)
11. [모니터링](#11-모니터링)

---

## 1. 시스템 요구사항

### 1-1. 하드웨어 (권장)

| 항목 | 최소 | 권장 |
|------|------|------|
| CPU | 2코어 | 4코어 |
| RAM | 4GB | 8GB |
| 디스크 | 2GB 여유 | 10GB (음성 파일 처리 시) |

> **음성 처리(faster-whisper) 추가 요구사항**:  
> - Apple Silicon (M1/M2/M3): CoreML 자동 사용, RAM 8GB+ 권장  
> - Intel Mac: CPU 모드 동작, `small` 모델 권장 (메모리 사용량 ~500MB)

### 1-2. 소프트웨어

| 항목 | 버전 | 설치 확인 |
|------|------|----------|
| macOS | 12 Monterey 이상 | `sw_vers` |
| Python | 3.11 이상 | `python3 --version` |
| zsh | 5.8 이상 | `zsh --version` |
| Git | 2.40 이상 (선택) | `git --version` |
| ffmpeg | 6.0 이상 (음성 기능 필요 시) | `ffmpeg -version` |
| Homebrew | 최신 (ffmpeg 설치용) | `brew --version` |

### 1-3. 네트워크

| 항목 | 설명 |
|------|------|
| 기본 포트 | `8577` (변경 가능) |
| 외부 통신 | OpenAI API (`api.openai.com:443`) — LLM 기능 사용 시 |
| 로컬 전용 | 로컬 LLM(Ollama) 사용 시 외부 통신 불필요 |

---

## 2. 최초 설치 절차

### 2-1. 프로젝트 디렉토리 확인

```bash
# 설치 위치 확인
ls -la /Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action/

# 필수 파일 존재 여부 확인
ls app.py database.py agent.py charts.py parser.py voice_processor.py requirements.txt restart.sh
```

### 2-2. 가상환경 생성

```bash
cd /Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action

# 가상환경 생성 (이름 고정: env_WBS_N_Action)
python3 -m venv env_WBS_N_Action

# 가상환경 확인
ls env_WBS_N_Action/bin/python
ls env_WBS_N_Action/bin/streamlit  # 설치 후
```

### 2-3. 패키지 설치

```bash
source env_WBS_N_Action/bin/activate

# 핵심 패키지 설치
pip install -r requirements.txt

# 설치 확인
pip list | grep -E "streamlit|pandas|plotly|openai"

# 음성 기능 패키지 (선택)
pip install faster-whisper ffmpeg-python

# ffmpeg 시스템 도구 설치 (음성 변환 필요 시)
brew install ffmpeg
```

### 2-4. 실행 권한 설정

```bash
# restart.sh 실행 권한 부여
chmod +x restart.sh

# 확인
ls -la restart.sh
# -rwxr-xr-x ...
```

### 2-5. 최초 실행 및 DB 초기화

```bash
# 앱 시작 (DB 자동 생성)
./restart.sh

# DB 생성 확인
ls -la project_agent.db

# 정상 실행 확인
tail -5 streamlit.log
```

### 2-6. 브라우저 접속 확인

```bash
# macOS 기본 브라우저로 열기
open http://localhost:8577
```

---

## 3. 서비스 관리 (restart.sh)

### 3-1. 스크립트 개요

`restart.sh`는 zsh 스크립트로, 앱의 안전한 시작/재시작을 담당합니다.

**동작 순서**:
1. 기존 `streamlit run app.py` 프로세스 탐색 및 종료 (`SIGTERM` → 2초 대기 → `SIGKILL`)
2. 지정 포트 사용 여부 확인 (충돌 시 대체 포트 입력 요청)
3. 가상환경 존재 확인
4. `nohup`으로 백그라운드 실행, `streamlit.log`에 출력 추가

### 3-2. 사용법

```bash
# 기본 실행 (포트 8577)
./restart.sh

# 포트 지정
./restart.sh 8888

# source로 실행 (서브셸 종료 없이, 터미널 세션 유지 시)
source restart.sh
source restart.sh 8888
```

### 3-3. 프로세스 상태 확인

```bash
# 실행 중 여부 확인
pgrep -f "streamlit run app.py"

# 상세 정보 (PID, 포트 등)
lsof -i :8577 -sTCP:LISTEN
ps aux | grep "streamlit run app.py" | grep -v grep

# 실시간 로그 확인
tail -f streamlit.log
```

### 3-4. 수동 종료

```bash
# 일반 종료
pkill -f "streamlit run app.py"

# 강제 종료
pkill -9 -f "streamlit run app.py"

# PID로 종료
kill $(pgrep -f "streamlit run app.py")
```

### 3-5. 시스템 재시작 후 자동 시작 설정

#### launchd (macOS 권장)

```bash
# plist 파일 생성
cat > ~/Library/LaunchAgents/com.project.wbs-agent.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.project.wbs-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>/Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action/restart.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>WorkingDirectory</key>
    <string>/Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action</string>
    <key>StandardOutPath</key>
    <string>/Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action/streamlit.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action/streamlit.log</string>
</dict>
</plist>
EOF

# 서비스 등록
launchctl load ~/Library/LaunchAgents/com.project.wbs-agent.plist

# 서비스 시작
launchctl start com.project.wbs-agent

# 서비스 상태 확인
launchctl list | grep wbs-agent
```

---

## 4. 포트 설정

### 4-1. 기본 포트 변경

`restart.sh`에서 기본 포트를 변경:

```bash
# restart.sh 12번째 줄
DEFAULT_PORT=8577   # ← 원하는 포트로 변경
```

### 4-2. 포트 사용 확인

```bash
# 8577 포트 사용 여부
lsof -iTCP:8577 -sTCP:LISTEN

# 사용 가능한 포트 탐색
for port in 8577 8578 8579 8580 8888 9999; do
    lsof -iTCP:$port -sTCP:LISTEN -t &>/dev/null || echo "포트 $port 사용 가능"
done
```

### 4-3. 포트 충돌 해결

`restart.sh`는 포트 충돌 시 대화형으로 대체 포트를 입력받습니다:

```
⚠️  포트 8577 가 다른 서비스에 의해 사용 중입니다.
   점유 프로세스:
   PID 12345    python3

   대체 포트 번호 입력 (Enter = 취소): 8888
```

---

## 5. LLM 설정

### 5-1. 설정 위치

LLM 설정은 DB(`llm_settings` 테이블)에 저장됩니다.  
**웹 UI**: ⚙️ 시스템/데이터 관리 탭 > 🔑 LLM 설정

### 5-2. OpenAI 설정

```
API Key:  sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Base URL: (공백)
모델명:   gpt-4o-mini
```

**OpenAI API 키 발급**:
1. https://platform.openai.com 접속
2. API Keys → Create new secret key
3. 복사하여 앱에 입력

**모델 선택 가이드**:

| 모델 | 속도 | 비용 | 적합 용도 |
|------|------|------|----------|
| `gpt-4o-mini` | 빠름 | 낮음 | 일반 프로젝트 관리, 기본 분석 |
| `gpt-4o` | 보통 | 중간 | 정확한 한국어 분석, 전략 보고서 |
| `gpt-4-turbo` | 느림 | 높음 | 긴 컨텍스트, 복잡한 분석 |

### 5-3. Ollama (로컬 LLM) 설정

```bash
# Ollama 설치
brew install ollama

# 서비스 시작
ollama serve

# 모델 다운로드 (처음 한 번만)
ollama pull llama3              # 4.7GB, 한국어 지원
ollama pull mistral             # 4.1GB
ollama pull qwen2.5:7b          # 한국어 성능 우수

# 실행 중 모델 확인
ollama list
```

앱 설정:
```
API Key:  (공백)
Base URL: http://localhost:11434/v1
모델명:   llama3
```

> **Ollama + M-chip Mac**: Metal 가속이 자동으로 사용됩니다. 8GB RAM 이상 권장.

### 5-4. DB 직접 설정 (관리자용)

UI 없이 직접 설정할 경우:

```bash
sqlite3 project_agent.db << 'EOF'
INSERT OR REPLACE INTO llm_settings (key, value) VALUES ('api_key', 'sk-your-key-here');
INSERT OR REPLACE INTO llm_settings (key, value) VALUES ('base_url', '');
INSERT OR REPLACE INTO llm_settings (key, value) VALUES ('model', 'gpt-4o-mini');
EOF
```

### 5-5. LLM 설정 확인

```bash
sqlite3 project_agent.db "SELECT key, substr(value,1,10)||'...' FROM llm_settings;"
```

---

## 6. DB 백업 및 복구

### 6-1. 수동 백업

```bash
# 날짜 포함 백업 파일 생성
cp project_agent.db "project_agent_$(date +%Y%m%d_%H%M%S).db"

# 예: project_agent_20250523_185959.db
```

### 6-2. 자동 백업 스크립트

```bash
#!/usr/bin/env zsh
# backup_db.sh — DB 자동 백업 (cron 등록 권장)

PROJ_DIR="/Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action"
BACKUP_DIR="$PROJ_DIR/backups"
DB_FILE="$PROJ_DIR/project_agent.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# SQLite 안전 백업 (WAL 모드 고려)
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/project_agent_$DATE.db'"

# 30일 이상 된 백업 삭제
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete

echo "✅ 백업 완료: $BACKUP_DIR/project_agent_$DATE.db"
```

**cron 등록 (매일 오전 6시)**:
```bash
crontab -e
# 아래 추가:
0 6 * * * /bin/zsh /Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action/backup_db.sh
```

### 6-3. DB 복구

```bash
# 앱 중지
pkill -f "streamlit run app.py"

# 현재 DB 백업 (복구 실패 대비)
cp project_agent.db project_agent_before_restore.db

# 백업 파일로 복구
cp backups/project_agent_20250523_120000.db project_agent.db

# 무결성 확인
sqlite3 project_agent.db "PRAGMA integrity_check;"
# 정상: "ok"

# 앱 재시작
./restart.sh
```

### 6-4. DB 무결성 확인

```bash
sqlite3 project_agent.db << 'EOF'
PRAGMA integrity_check;
PRAGMA foreign_key_check;

-- 고아 Action Item 확인 (WBS 없는 wbs_id 참조)
SELECT COUNT(*) FROM action_items a
LEFT JOIN wbs_items w ON a.wbs_id = w.id
WHERE a.wbs_id IS NOT NULL AND w.id IS NULL;

-- 고아 WBS 확인 (부모 없는 parent_wbs_id)
SELECT COUNT(*) FROM wbs_items a
LEFT JOIN wbs_items b ON a.parent_wbs_id = b.id
WHERE a.parent_wbs_id IS NOT NULL AND b.id IS NULL;
EOF
```

### 6-5. DB 초기화 (전체 데이터 삭제)

> **⚠️ 위험**: 이 작업은 되돌릴 수 없습니다. 반드시 백업 후 진행하세요.

```bash
# 백업 먼저
cp project_agent.db project_agent_$(date +%Y%m%d_%H%M%S)_backup.db

# DB 파일 삭제 → 앱 재시작 시 자동 재생성
rm project_agent.db
./restart.sh
```

---

## 7. 로그 파일 관리

### 7-1. 로그 파일 위치

| 파일 | 설명 |
|------|------|
| `streamlit.log` | Streamlit 런타임 로그 (앱 시작/오류/HTTP 요청) |

### 7-2. 로그 확인

```bash
# 실시간 모니터링
tail -f streamlit.log

# 최근 100줄
tail -100 streamlit.log

# 오류 필터링
grep -E "ERROR|CRITICAL|Traceback|Exception" streamlit.log

# 특정 날짜 필터링
grep "2025-05-23" streamlit.log

# 로그 크기 확인
ls -lh streamlit.log
du -h streamlit.log
```

### 7-3. 로그 순환 (Log Rotation)

로그 파일이 커질 경우 정기적으로 비워줍니다:

```bash
# 로그 비우기 (앱 실행 중에도 안전)
> streamlit.log          # 파일 비우기 (truncate)
# 또는
cat /dev/null > streamlit.log

# 보관 후 비우기
mv streamlit.log streamlit_$(date +%Y%m%d).log
touch streamlit.log
```

**logrotate 설정** (자동화):

```bash
# /usr/local/etc/logrotate.d/wbs-agent 파일 생성
cat > /usr/local/etc/logrotate.d/wbs-agent << 'EOF'
/Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action/streamlit.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    copytruncate
}
EOF

# logrotate 수동 실행 (테스트)
logrotate -v /usr/local/etc/logrotate.d/wbs-agent
```

### 7-4. 로그 레벨

Streamlit 로그 레벨 설정:

```bash
# 디버그 모드로 실행 (상세 로그)
STREAMLIT_LOGGER_LEVEL=debug streamlit run app.py

# 로그 최소화
STREAMLIT_LOGGER_LEVEL=warning streamlit run app.py
```

또는 `~/.streamlit/config.toml` 설정:

```toml
[logger]
level = "warning"
messageFormat = "%(asctime)s %(message)s"
```

---

## 8. 보안 고려사항

### 8-1. API 키 보안

- **API 키는 DB(`llm_settings`)에 저장**됩니다. DB 파일은 로컬 파일시스템에 평문으로 저장됩니다.
- 파일 권한 설정:
  ```bash
  chmod 600 project_agent.db   # 소유자만 읽기/쓰기
  ```
- 공유 환경에서는 DB 파일이 다른 사용자에게 노출되지 않도록 주의

### 8-2. 네트워크 접근 제한

기본적으로 `127.0.0.1` (로컬호스트)에서만 접근 가능합니다. 팀 내 공유가 필요한 경우에만 외부 접근을 허용하세요.

```bash
# 팀 내 공유 (같은 네트워크 내)
./env_WBS_N_Action/bin/streamlit run app.py \
    --server.port 8577 \
    --server.address 0.0.0.0

# 특정 IP만 허용 (방화벽)
# macOS 방화벽: 시스템 환경설정 > 보안 및 개인 정보 > 방화벽
```

> **⚠️ 주의**: 외부 노출 시 API 키와 프로젝트 데이터가 네트워크에 노출될 수 있습니다. 업무 외 환경에서는 사용하지 마세요.

### 8-3. 음성 파일 보안

업로드된 음성 파일은 `tempfile`을 통해 임시 저장 후 즉시 삭제됩니다. 영구 저장되지 않습니다.

---

## 9. 트러블슈팅

### 9-1. 앱이 시작되지 않는 경우

```bash
# 로그 확인
tail -30 streamlit.log

# 가상환경 확인
ls env_WBS_N_Action/bin/streamlit

# 수동 실행으로 오류 확인
source env_WBS_N_Action/bin/activate
streamlit run app.py --server.port 8577
```

**일반적인 원인 및 해결**:

| 오류 | 해결 |
|------|------|
| `No module named 'streamlit'` | `pip install -r requirements.txt` |
| `Address already in use` | `./restart.sh` 또는 `pkill -f streamlit` |
| `sqlite3.OperationalError` | DB 파일 삭제 후 재시작 (데이터 손실 주의) |
| `Permission denied: restart.sh` | `chmod +x restart.sh` |

### 9-2. 포트 충돌

```bash
# 포트 점유 프로세스 확인
lsof -iTCP:8577 -sTCP:LISTEN
# 또는
lsof -i :8577

# 특정 PID 종료
kill -9 <PID>

# 다른 포트로 실행
./restart.sh 8888
```

### 9-3. DB 오류

```bash
# DB 잠금 해제 (동시 접근 시)
sqlite3 project_agent.db "PRAGMA journal_mode=WAL;"

# DB 무결성 검사
sqlite3 project_agent.db "PRAGMA integrity_check;"

# DB 복구 시도
sqlite3 project_agent.db ".dump" > dump.sql
mv project_agent.db project_agent_corrupt.db
sqlite3 project_agent.db < dump.sql
```

### 9-4. UI가 업데이트되지 않는 경우

1. 브라우저 새로고침 (`Cmd+R`)
2. Streamlit 하드 리프레시 (`Cmd+Shift+R` 또는 우측 상단 메뉴 > Clear cache)
3. 앱 재시작: `./restart.sh`

### 9-5. 음성 처리 오류

```bash
# faster-whisper 미설치
pip install faster-whisper

# ffmpeg 미설치
brew install ffmpeg
pip install ffmpeg-python

# 모델 다운로드 실패 (인터넷 필요)
# ~/.cache/huggingface/hub/ 에 다운로드됨
# 프록시 환경: HF_ENDPOINT 환경변수 설정 필요
```

### 9-6. LLM 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| `AuthenticationError` | 잘못된 API 키 | Admin 탭에서 API 키 재입력 |
| `ConnectionRefusedError` | Ollama 미실행 | `ollama serve` 실행 |
| `Model not found` | 잘못된 모델명 | `ollama list`로 확인 후 정확한 이름 입력 |
| `RateLimitError` | OpenAI 요청 한도 초과 | 잠시 대기 후 재시도 |
| `Timeout` | 네트워크 느림 | `max_tokens` 줄이기 또는 더 빠른 모델 선택 |

### 9-7. Streamlit 관련 오류

```bash
# Streamlit 캐시 초기화
streamlit cache clear

# config 재설정
rm -rf ~/.streamlit/config.toml

# 패키지 재설치
pip install --upgrade streamlit
```

### 9-8. 진척률 이상

**증상**: 전체 롤업 후 진척률이 예상과 다름

**확인 방법**:
```bash
sqlite3 project_agent.db << 'EOF'
-- WBS별 Action 완료 현황
SELECT w.id, w.wbs_code, w.wbs_type, w.progress,
       COUNT(a.id) AS total_action,
       SUM(CASE WHEN a.status='done' THEN 1 ELSE 0 END) AS done_action
FROM wbs_items w
LEFT JOIN action_items a ON w.id = a.wbs_id
GROUP BY w.id;

-- 취소 상태 자식 확인 (롤업 제외 대상)
SELECT id, wbs_code, wbs_type, status
FROM wbs_items
WHERE status = 'cancelled';
EOF
```

---

## 10. 업데이트 절차

### 10-1. 코드 업데이트

```bash
# 백업
cp project_agent.db project_agent_$(date +%Y%m%d_%H%M%S)_pre_update.db

# 최신 코드 Pull (git 사용 시)
git pull origin main

# 의존성 업데이트
source env_WBS_N_Action/bin/activate
pip install -r requirements.txt --upgrade

# 재시작 (DB 마이그레이션 자동 실행)
./restart.sh
```

### 10-2. DB 스키마 업데이트

코드에 새 컬럼이 추가된 경우:

1. `init_db()`의 `ALTER TABLE` 블록에 추가 (개발자 작업)
2. 앱 재시작 시 자동으로 마이그레이션 실행
3. 기존 데이터에는 기본값이 채워짐

```bash
# 마이그레이션 확인
sqlite3 project_agent.db ".schema wbs_items"
```

### 10-3. 패키지 업데이트

```bash
source env_WBS_N_Action/bin/activate

# 업데이트 가능한 패키지 확인
pip list --outdated

# 안전한 업데이트 (requirements.txt 버전 범위 내)
pip install -r requirements.txt --upgrade

# 특정 패키지만 업데이트
pip install --upgrade streamlit
pip install --upgrade openai
```

---

## 11. 모니터링

### 11-1. 앱 상태 확인 스크립트

```bash
#!/usr/bin/env zsh
# health_check.sh

PROJ_DIR="/Users/jihoonjung/Documents/Antigravity_prj/WBS_N_Action"
PORT=8577

echo "=== WBS Agent 상태 확인 $(date) ==="

# 프로세스 확인
PID=$(pgrep -f "streamlit run app.py")
if [[ -n "$PID" ]]; then
    echo "✅ 프로세스 실행 중 (PID: $PID)"
else
    echo "❌ 프로세스 없음"
fi

# 포트 확인
if lsof -iTCP:$PORT -sTCP:LISTEN -t &>/dev/null; then
    echo "✅ 포트 $PORT 응답"
else
    echo "❌ 포트 $PORT 응답 없음"
fi

# HTTP 응답 확인
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT 2>/dev/null)
if [[ "$HTTP_STATUS" == "200" ]]; then
    echo "✅ HTTP 응답 정상 ($HTTP_STATUS)"
else
    echo "⚠️ HTTP 응답: $HTTP_STATUS"
fi

# DB 확인
DB_FILE="$PROJ_DIR/project_agent.db"
if [[ -f "$DB_FILE" ]]; then
    DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
    WBS_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM wbs_items;" 2>/dev/null)
    ACTION_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM action_items;" 2>/dev/null)
    echo "✅ DB 정상 (크기: $DB_SIZE, WBS: ${WBS_COUNT}건, Action: ${ACTION_COUNT}건)"
else
    echo "❌ DB 파일 없음"
fi

# 로그 파일 크기
LOG_SIZE=$(du -h "$PROJ_DIR/streamlit.log" 2>/dev/null | cut -f1)
echo "ℹ️ 로그 파일 크기: ${LOG_SIZE:-N/A}"
```

### 11-2. 주요 지표 SQL

```bash
# 일간 현황 리포트
sqlite3 project_agent.db << 'EOF'
SELECT '=== 일간 현황 ===' AS title;
SELECT
    (SELECT COUNT(*) FROM wbs_items) AS '전체 WBS',
    (SELECT COUNT(*) FROM wbs_items WHERE status='in_progress') AS '진행중 WBS',
    (SELECT COUNT(*) FROM wbs_items WHERE status='done') AS '완료 WBS',
    (SELECT ROUND(AVG(progress),1) FROM wbs_items) AS '평균 진척률(%)';

SELECT '=== Action Items ===' AS title;
SELECT
    (SELECT COUNT(*) FROM action_items) AS '전체 Action',
    (SELECT COUNT(*) FROM action_items WHERE status='done') AS '완료',
    (SELECT COUNT(*) FROM action_items WHERE status='blocked') AS '블록';

SELECT '=== 마감 임박 (7일) ===' AS title;
SELECT wbs_type, due_date, status
FROM wbs_items
WHERE due_date BETWEEN date('now') AND date('now', '+7 days')
  AND status != 'done'
ORDER BY due_date;
EOF
```

---

## 부록: 설치 검증 체크리스트

```
최초 설치 후 확인 항목:

[ ] Python 3.11+ 설치 확인
[ ] 가상환경 생성 (env_WBS_N_Action/)
[ ] requirements.txt 패키지 설치 완료
[ ] restart.sh 실행 권한 설정 (chmod +x)
[ ] 앱 최초 실행 성공
[ ] project_agent.db 자동 생성 확인
[ ] 브라우저에서 http://localhost:8577 접속 확인
[ ] 헤더 KPI 카드 표시 확인
[ ] WBS 추가/삭제 동작 확인
[ ] Action Item 추가/삭제 동작 확인
[ ] Gantt 차트 정상 표시 확인 (날짜 있는 항목 필요)
[ ] Admin 탭 > LLM 설정 저장 확인
[ ] AI 에이전트 탭 > LLM 응답 확인
[ ] 자동 백업 스크립트 설정 (선택)
[ ] launchd 자동 시작 설정 (선택)
```
