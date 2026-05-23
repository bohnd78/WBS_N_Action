# Project Agent · WBS & Action Item 관리 — CLAUDE.md

> **AI 코딩 어시스턴트(Claude, Gemini 등)를 위한 프로젝트 핵심 정보 파일**  
> 이 파일을 먼저 읽고 코드 수정을 시작하세요.

---

## 1. 프로젝트 개요

**Project Agent**는 SAP Sales Process (SD 모듈) ERP 구현 프로젝트의 WBS 및 Action Item을 관리하는 **Streamlit 기반 웹 애플리케이션**입니다.

- **실행 환경**: Python 3.11+, 가상환경 `env_WBS_N_Action/`
- **DB**: SQLite (`project_agent.db`) — 파일 기반, 마이그레이션 자동
- **기본 포트**: `8577`
- **UI 언어**: 한국어 (기술 용어는 영어 혼용)

---

## 2. 핵심 명령어

```bash
# 앱 실행 (기본 포트 8577)
./restart.sh

# 포트 직접 지정
./restart.sh 8555

# source 실행 (서브셸 종료 없이)
source restart.sh

# 수동 실행 (개발용)
source env_WBS_N_Action/bin/activate
streamlit run app.py --server.port 8577

# 로그 확인
tail -f streamlit.log

# 실행 중 PID 확인
pgrep -f "streamlit run app.py"

# 강제 종료
pkill -f "streamlit run app.py"

# 의존성 설치
pip install -r requirements.txt
pip install faster-whisper ffmpeg-python  # 음성 기능 (선택)
```

---

## 3. 파일 구조

```
WBS_N_Action/
├── app.py              # Streamlit UI (1515줄) — 메인 진입점
├── database.py         # SQLite CRUD + 계층 롤업 로직 (684줄)
├── agent.py            # LLM 연동 (OpenAI/Ollama 호환) (211줄)
├── parser.py           # Obsidian .md YAML frontmatter 파서 (136줄)
├── charts.py           # Plotly Gantt/도넛/막대 차트 (267줄)
├── voice_processor.py  # faster-whisper STT + LLM 분석 (347줄)
├── project_agent.db    # SQLite DB (자동 생성)
├── requirements.txt    # 핵심 의존성 (openai, streamlit, plotly 등)
├── restart.sh          # 프로세스 관리 스크립트 (zsh)
├── streamlit.log       # 런타임 로그
├── WBS_Template.md     # Obsidian WBS 노트 템플릿
├── ActionItem_Template.md # Obsidian Action Item 노트 템플릿
└── env_WBS_N_Action/   # Python 가상환경 (git 제외)
```

---

## 4. 아키텍처 개요

```
app.py (Streamlit UI)
  ├── database.py   ← SQLite CRUD, 계층 구조, 롤업
  ├── agent.py      ← OpenAI API 호출, 프로젝트 컨텍스트 빌드
  ├── charts.py     ← Plotly 차트 생성 (Gantt, Donut, Bar)
  ├── parser.py     ← Obsidian .md YAML frontmatter 파싱
  └── voice_processor.py ← faster-whisper STT + LLM 분석
```

**데이터 흐름**: UI 이벤트 → `app.py` 핸들러 → `database.py` CRUD → SQLite → DataFrame → UI 렌더링

---

## 5. DB 스키마 (핵심 테이블)

### `wbs_items`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER PK | 자동 증가 |
| `wbs_category` | TEXT | 카테고리 (예: "To be process 개발") |
| `wbs_type` | TEXT | 항목 유형 (예: "process 체계도") |
| `wbs_code` | TEXT | 계층 코드 (예: "1.1", "2.1.1") |
| `wbs_level` | INTEGER | 계층 깊이 (루트=1) |
| `parent_wbs_id` | INTEGER | 부모 WBS ID (NULL=루트) |
| `content` | TEXT | 상세 내용 |
| `start_date` | TEXT | YYYY-MM-DD |
| `due_date` | TEXT | YYYY-MM-DD |
| `end_date` | TEXT | YYYY-MM-DD |
| `status` | TEXT | `scheduled`/`in_progress`/`done`/`cancelled` |
| `progress` | INTEGER | 0-100 진척률 |
| `owner` | TEXT | 담당자 |
| `registered_date` | TEXT | 등록일 |
| `notes` | TEXT | 기타 메모 |
| `source_file` | TEXT | 업로드 원본 파일명 |
| `created_at` | TEXT | DB 저장 시각 |

### `action_items`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER PK | 자동 증가 |
| `action_type` | TEXT | 유형 (마스터 테이블 참조) |
| `wbs_id` | INTEGER FK | 귀속 WBS ID (NULL=독립 Action) |
| `content` | TEXT | 할 일 내용 |
| `status` | TEXT | `todo`/`in_progress`/`done`/`blocked` |
| `start_date` | TEXT | YYYY-MM-DD |
| `due_date` | TEXT | YYYY-MM-DD |
| `end_date` | TEXT | YYYY-MM-DD |
| `notes` | TEXT | 기타 메모 |
| `registered_date` | TEXT | 등록일 |
| `source_file` | TEXT | 업로드 원본 파일명 |

### `wbs_types` (마스터)
- `(category, type_name)` UNIQUE 제약
- 기본값: `DEFAULT_WBS_TYPES` in `database.py`

### `action_types` (마스터)
- `type_name` UNIQUE 제약
- 기본값: `DEFAULT_ACTION_TYPES` in `database.py`

### `llm_settings`
- `(key, value)` key-value 저장소
- 키: `api_key`, `base_url`, `model`

---

## 6. 핵심 패턴 및 컨벤션

### 6-1. DB 연결 패턴
```python
# 매 함수 호출마다 연결 생성/반환 — 커넥션 풀 없음
conn = get_conn()          # sqlite3.connect(DB_PATH, check_same_thread=False)
# ... 쿼리 수행 ...
conn.commit()
conn.close()
```

### 6-2. 컬럼 마이그레이션 패턴
```python
# init_db()에서 ALTER TABLE — 기존 DB 호환 보장
for col_sql in ["ALTER TABLE wbs_items ADD COLUMN new_col TEXT DEFAULT ''"]:
    try:
        c.execute(col_sql)
        conn.commit()
    except Exception:
        pass  # 이미 존재하면 무시
```

### 6-3. Streamlit 상태 관리 패턴
```python
# 폼 표시 제어 — session_state 플래그 사용
st.session_state["show_wbs_form"] = True   # 폼 열기
st.session_state.pop("edit_wbs_id", None)  # 다른 폼 닫기
st.rerun()                                  # 즉시 리렌더링
```

### 6-4. WBS 계층 렌더링 패턴
```python
# build_children_map → {parent_id: [children]} 딕셔너리
cmap = db.build_children_map(all_items)
roots = cmap.get(None, [])       # 루트 노드
for node in roots:
    _render_wbs_node(node, depth=1, cmap=cmap)  # 재귀 렌더링
```

### 6-5. 진척률 롤업 알고리즘
```python
# 리프 노드: Action Item 완료 비율 (없으면 수동 progress)
# 부모 노드: 활성(취소 제외) 자식 진척률 평균
def calculate_rollup_progress(wbs_id):
    children = get_wbs_children(wbs_id)
    if not children:
        stats = get_action_stats_for_wbs(wbs_id)
        return stats["auto_progress"] if stats["total"] > 0 else manual_progress
    active = [c for c in children if c["status"] != "cancelled"]
    return round(sum(calculate_rollup_progress(c["id"]) for c in active) / len(active))
```

### 6-6. LLM 클라이언트 패턴
```python
# OpenAI 호환 — api_key="ollama" + base_url로 로컬 LLM 지원
kwargs = {"api_key": api_key or "ollama"}
if base_url:
    kwargs["base_url"] = base_url
client = OpenAI(**kwargs)
```

### 6-7. CSS 테마 시스템
- **배경색**: `#0f172a` (앱 배경) / `#1e293b` (카드)
- **강조색**: `#7c3aed` (보라, Primary) / `#4f46e5` (인디고)
- **상태색**: `#22c55e` 완료, `#f59e0b` 진행중, `#ef4444` 블록, `#64748b` 대기
- 모든 CSS는 `app.py` 상단의 `st.markdown("""<style>...""")` 블록에 집중

---

## 7. 상태 값 (하드코딩된 상수)

```python
# Action Item 상태 (database.py)
STATUS_OPTIONS = ["todo", "in_progress", "done", "blocked"]

# WBS 계층 상태 (database.py)
WBS_STATUS_OPTIONS = ["scheduled", "in_progress", "done", "cancelled"]
```

> **⚠️ 중요**: 상태 값은 DB에 영문 소문자로 저장됩니다. UI 레이블은 별도 딕셔너리(`STATUS_LABEL`, `WBS_STATUS_LABEL`)로 관리합니다.

---

## 8. Obsidian 연동 스키마

### WBS 노트 (`type: wbs`)
```yaml
---
type: wbs                   # 파싱 트리거 (필수)
wbs_code: "1.1"             # WBS 계층 코드
wbs_category: "..."         # wbs_types.category 일치
wbs_type: "..."             # wbs_types.type_name 일치
status: scheduled           # WBS 상태 4가지 중 하나
start_date: "2025-06-01"
due_date: "2025-06-30"
end_date: ""
progress: 0
owner: "홍길동"
notes: ""
---
```

### Action Item 노트 (`type: action_item`)
```yaml
---
type: action_item           # 파싱 트리거 (필수)
action_type: "문서작성"     # action_types.type_name 일치
status: todo
start_date: "2025-06-01"
due_date: "2025-06-15"
end_date: ""
wbs_ref: "1.1"              # 귀속 WBS 코드 (선택, 매칭 실패 시 독립 Action)
notes: ""
---
```

---

## 9. 코드 스타일 가이드라인

### Python
- **타입 힌트** 사용 (`def func(x: int) -> str:`)
- **함수명**: snake_case (`render_wbs_tab`, `get_wbs_by_id`)
- **프라이빗 함수**: 언더스코어 접두사 (`_wbs_form`, `_render_wbs_node`)
- **오류 처리**: `try/except Exception: pass` (DB 마이그레이션), 주요 경로는 명시적 처리
- **None 반환**: DB 조회 실패 시 `None` 반환 (`get_wbs_by_id`)
- **DataFrame vs dict**: 단건은 `dict`, 다건은 `pd.DataFrame`

### Streamlit
- **session_state 키 명명**: `snake_case` (예: `edit_wbs_id`, `show_wbs_form`)
- **폼 키 접두사**: `pfx = f"wbs_{mode}_{item_id or 'new'}"` 로 고유성 보장
- **st.rerun()**: 저장/삭제 후 반드시 호출
- **unsafe_allow_html=True**: 커스텀 카드, 뱃지, 진척률 바에 사용

### SQL
- **날짜**: TEXT 타입 `YYYY-MM-DD` 문자열 저장
- **빈 날짜**: `NULL` 대신 빈 문자열 `''` 사용
- **진척률**: INTEGER 0-100

---

## 10. 절대 하지 말 것 (MUST NOT)

1. **`check_same_thread=True` 사용 금지** — Streamlit 멀티스레드 환경에서 DB 오류 발생
2. **전역 SQLite 커넥션 유지 금지** — 항상 함수 내에서 `get_conn()` → `close()` 패턴
3. **`st.experimental_*` API 사용 금지** — deprecated, `st.dialog`, `st.cache_data` 사용
4. **상태 값 한국어 저장 금지** — DB에는 항상 영문 소문자 (`todo`, `done` 등)
5. **`wbs_master_types`, `action_master_types` 테이블명 오용 금지** — 실제 테이블명은 `wbs_types`, `action_types`
6. **`progress` 컬럼 직접 100 이상 값 입력 금지** — 0-100 범위 검증 필요
7. **`parent_wbs_id`를 삭제할 WBS ID로 직접 수정 금지** — `delete_wbs()`는 재귀 삭제 수행
8. **LLM API 키를 소스코드에 하드코딩 금지** — DB `llm_settings` 테이블에서 관리
9. **`streamlit.log` 파일 삭제 금지** — `nohup` 출력 대상 파일

---

## 11. 주요 함수 레퍼런스

| 모듈 | 함수 | 설명 |
|------|------|------|
| `database` | `init_db()` | DB 초기화 + 마이그레이션 |
| `database` | `get_all_wbs_flat()` | 전체 WBS 계층 정렬 목록 |
| `database` | `build_children_map(items)` | 부모-자식 매핑 딕셔너리 생성 |
| `database` | `apply_rollup_all()` | 전체 WBS 진척률 재계산 |
| `database` | `apply_rollup_progress(wbs_id)` | 단일 WBS 롤업 후 저장 |
| `database` | `get_action_stats_for_wbs(wbs_id)` | WBS별 Action 통계 |
| `database` | `get_summary_stats()` | 헤더 KPI 통계 |
| `database` | `get_gantt_data()` | Gantt 차트용 WBS 데이터 |
| `agent` | `chat(messages, ...)` | LLM 채팅 응답 |
| `agent` | `extract_action_items_from_note(note, ...)` | 자유 노트 → Action 추출 |
| `agent` | `generate_strategy(...)` | 전략 보고서 생성 |
| `charts` | `make_gantt(df, title)` | Gantt 차트 Figure |
| `charts` | `make_status_donut(stats, mode)` | 상태 도넛 차트 |
| `parser` | `parse_obsidian_note(content, filename)` | .md 파싱 → (type, data) |
| `voice_processor` | `transcribe_audio(bytes, ext, ...)` | 음성 → 텍스트 |
| `voice_processor` | `analyze_transcript(text, ...)` | 텍스트 → WBS/Action 구조화 |

---

## 12. 새 기능 추가 체크리스트

- [ ] DB 컬럼 추가 시 → `init_db()`의 `ALTER TABLE` 마이그레이션 블록에 추가
- [ ] 새 상태 값 추가 시 → `STATUS_OPTIONS`, `STATUS_EMOJI`, `STATUS_LABEL`, `STATUS_COLOR` 4개 딕셔너리 모두 업데이트
- [ ] 새 탭 추가 시 → `main()`의 `st.tabs()` 리스트와 `with tab_xxx:` 블록에 추가
- [ ] 새 마스터 유형 추가 시 → Admin 탭 UI + `database.py`의 `DEFAULT_*` 리스트에 추가
- [ ] Plotly 차트 추가 시 → `charts.py`에 `make_*()` 함수 추가 후 `render_gantt_tab()`에서 호출
