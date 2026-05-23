# 개발자 가이드 — Project Agent (WBS & Action Item 관리)

> SAP Sales Process ERP 구현 프로젝트 관리 도구  
> 이 가이드는 프로젝트를 처음 설정하거나 기능을 추가하려는 개발자를 위한 문서입니다.

---

## 목차

1. [개발 환경 설정 (처음부터)](#1-개발-환경-설정-처음부터)
2. [프로젝트 구조 및 코드 컨벤션](#2-프로젝트-구조-및-코드-컨벤션)
3. [새 기능 추가 방법](#3-새-기능-추가-방법)
4. [DB 마이그레이션 패턴](#4-db-마이그레이션-패턴)
5. [WBS / Action 유형 추가](#5-wbs--action-유형-추가)
6. [Streamlit 개발 팁](#6-streamlit-개발-팁)
7. [테스트 가이드라인](#7-테스트-가이드라인)
8. [Git 워크플로우](#8-git-워크플로우)
9. [디버깅 가이드](#9-디버깅-가이드)

---

## 1. 개발 환경 설정 (처음부터)

### 1-1. 전제 조건

| 항목 | 최소 버전 | 확인 명령 |
|------|----------|----------|
| Python | 3.11+ | `python3 --version` |
| macOS | 12+ (Monterey) | - |
| zsh | 5.8+ | `zsh --version` |
| Git | 2.40+ | `git --version` |

### 1-2. 저장소 클론

```bash
git clone https://github.com/<org>/WBS_N_Action.git
cd WBS_N_Action
```

### 1-3. 가상환경 생성 및 활성화

```bash
# 가상환경 생성 (정해진 이름 사용)
python3 -m venv env_WBS_N_Action

# 활성화
source env_WBS_N_Action/bin/activate

# 비활성화 (작업 종료 시)
deactivate
```

### 1-4. 의존성 설치

```bash
# 핵심 의존성
pip install -r requirements.txt

# 음성 기능 (선택적)
pip install faster-whisper ffmpeg-python

# ffmpeg 시스템 도구 (음성 변환용)
brew install ffmpeg
```

**requirements.txt 내용**:
```
streamlit>=1.35.0
pandas>=2.0.0
python-frontmatter>=1.1.0
python-dateutil>=2.9.0
plotly>=5.20.0
openai>=1.30.0
```

### 1-5. 앱 실행

```bash
# 방법 1: restart.sh 사용 (권장)
./restart.sh           # 기본 포트 8577
./restart.sh 8888      # 포트 지정

# 방법 2: 직접 실행 (개발용, 포그라운드)
source env_WBS_N_Action/bin/activate
streamlit run app.py --server.port 8577

# 접속
open http://localhost:8577
```

### 1-6. DB 초기화 확인

앱 최초 실행 시 `project_agent.db`가 자동 생성되며 기본 마스터 데이터가 삽입됩니다.

```bash
# SQLite CLI로 확인
sqlite3 project_agent.db

# 테이블 목록
.tables
# → action_items  action_types  llm_settings  wbs_items  wbs_types

# 기본 WBS 유형 확인
SELECT * FROM wbs_types LIMIT 5;

# 종료
.quit
```

---

## 2. 프로젝트 구조 및 코드 컨벤션

### 2-1. 파일별 역할

| 파일 | 역할 | 수정 빈도 |
|------|------|-----------|
| `app.py` | Streamlit UI, 탭/폼 렌더링, 이벤트 처리 | 높음 |
| `database.py` | SQLite CRUD, 계층 알고리즘, 마스터 데이터 | 보통 |
| `agent.py` | LLM API 호출, 프롬프트 관리 | 낮음 |
| `charts.py` | Plotly 차트 생성 | 낮음 |
| `parser.py` | Obsidian .md 파싱 | 낮음 |
| `voice_processor.py` | STT + LLM 음성 분석 | 낮음 |

### 2-2. Python 코드 컨벤션

#### 명명 규칙
```python
# 함수명: snake_case
def get_wbs_by_id(wbs_id: int) -> dict | None: ...
def _wbs_form(mode="add", item_id=None): ...  # 프라이빗: 언더스코어 접두사

# 상수: UPPER_CASE
STATUS_OPTIONS = ["todo", "in_progress", "done", "blocked"]
DEFAULT_WBS_TYPES = [...]

# 변수: snake_case
all_items = db.get_all_wbs_flat()
f_search = st.text_input(...)
```

#### 타입 힌트
```python
# 파이썬 3.10+ 문법 사용
def get_conn() -> sqlite3.Connection: ...
def get_wbs_by_id(wbs_id: int) -> dict | None: ...
def get_wbs_children(parent_id: int | None) -> list[dict]: ...
def parse_date_safe(val) -> date | None: ...
```

#### 오류 처리
```python
# DB 마이그레이션: 오류 무시 (이미 존재하는 컬럼)
try:
    c.execute("ALTER TABLE wbs_items ADD COLUMN new_col TEXT")
    conn.commit()
except Exception:
    pass

# LLM 호출: 명시적 오류 메시지 반환
try:
    resp = client.chat.completions.create(...)
    return resp.choices[0].message.content
except Exception as e:
    return f"❌ LLM 오류: {str(e)}"

# DB 단건 조회: None 반환
def get_wbs_by_id(wbs_id: int) -> dict | None:
    ...
    return df.iloc[0].to_dict() if not df.empty else None
```

### 2-3. Streamlit 컨벤션

#### session_state 사용 패턴
```python
# 플래그 기반 폼 표시/숨김
st.session_state["show_wbs_form"] = True   # 열기
st.session_state.pop("show_wbs_form", None)  # 닫기 (KeyError 안전)

# 수정 대상 ID 추적
st.session_state["edit_wbs_id"] = wbs_id
st.session_state.pop("edit_wbs_id", None)

# 항상 저장/삭제 후 st.rerun() 호출
db.insert_wbs(data)
st.success("✅ 저장되었습니다!")
st.rerun()
```

#### 고유 키 생성 패턴
```python
# 폼 접두사로 충돌 방지
pfx = f"wbs_{mode}_{item_id or parent_id or 'new'}"
st.text_input("WBS 코드", key=f"{pfx}_code")
st.selectbox("카테고리", cats, key=f"{pfx}_cat")

# 버튼 키: 아이디 기반
st.button("✏️", key=f"ewbs_{wid}")
st.button("🗑️", key=f"dwbs_{wid}")
```

#### HTML 렌더링
```python
# CSS 클래스 기반 (app.py 상단 <style> 블록)
st.markdown('<div class="wbs-node wbs-node-l1">...</div>', unsafe_allow_html=True)

# 인라인 스타일 (동적 값)
st.markdown(
    f'<div style="background:{color};border-radius:8px">...</div>',
    unsafe_allow_html=True
)
```

### 2-4. SQL 컨벤션

```python
# 날짜: TEXT 타입, YYYY-MM-DD
# 빈 날짜: NULL이 아닌 빈 문자열 ''
# 진척률: INTEGER 0-100

# 파라미터 바인딩 (SQL Injection 방지)
c.execute("SELECT * FROM wbs_items WHERE id=?", (wbs_id,))

# executemany로 일괄 삽입
c.executemany(
    "INSERT OR IGNORE INTO wbs_types (category, type_name) VALUES (?, ?)",
    DEFAULT_WBS_TYPES,
)
```

---

## 3. 새 기능 추가 방법

### 3-1. 새 탭 추가

**예시**: "📈 분석 보고서" 탭 추가

**1단계**: `app.py`의 `main()` 함수에서 탭 추가

```python
def main():
    render_header()
    tab_wbs, tab_act, tab_upload, tab_gantt, tab_agent, tab_admin, tab_report = st.tabs([
        "📋 WBS 관리",
        "✅ Action Items",
        "📤 노트 업로드",
        "📊 Gantt & 대시보드",
        "🤖 AI 에이전트",
        "⚙️ 시스템/데이터 관리",
        "📈 분석 보고서",  # ← 추가
    ])
    with tab_wbs:    render_wbs_tab()
    # ... 기존 탭들 ...
    with tab_report: render_report_tab()  # ← 추가
```

**2단계**: 탭 렌더 함수 작성

```python
def render_report_tab():
    st.subheader("📈 분석 보고서")
    # 구현 내용
    stats = db.get_summary_stats()
    st.metric("전체 진척률", f"{stats['avg_progress']}%")
```

### 3-2. 새 차트 추가

**1단계**: `charts.py`에 함수 추가

```python
def make_new_chart(df: pd.DataFrame) -> go.Figure:
    """새 차트 설명."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="#1e293b",
            plot_bgcolor="#1e293b",
            font=dict(color="#e2e8f0"),
            height=200
        )
        return fig
    
    # 차트 구현 (다크 테마 유지)
    fig = go.Figure(go.Bar(
        x=df["col1"],
        y=df["col2"],
        marker=dict(color="#7c3aed"),
    ))
    fig.update_layout(
        title=dict(text="차트 제목", font=dict(size=14, color="#e2e8f0")),
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
```

**2단계**: `app.py`에서 호출

```python
import charts as ch

# render_gantt_tab() 또는 새 탭에서
df = db.get_some_data()
st.plotly_chart(ch.make_new_chart(df), use_container_width=True)
```

### 3-3. 새 DB 쿼리 함수 추가

`database.py`에 함수 추가:

```python
def get_wbs_by_owner(owner: str) -> pd.DataFrame:
    """담당자별 WBS 목록 조회."""
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM wbs_items WHERE owner=? ORDER BY wbs_level, wbs_code",
        conn,
        params=(owner,)
    )
    conn.close()
    return df
```

### 3-4. LLM 프롬프트 추가

`agent.py`에 새 함수 추가:

```python
def generate_owner_report(
    owner: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "gpt-4o-mini",
) -> str:
    """특정 담당자의 업무 현황 분석 보고서 생성."""
    ctx = _build_project_context()
    prompt = f"""
다음 프로젝트 현황에서 담당자 '{owner}'의 업무를 분석하세요.

{ctx}

분석 항목:
1. 담당 WBS 목록과 진척률
2. 지연 위험 항목
3. 권고사항
"""
    
    if not HAS_OPENAI:
        return "❌ openai 패키지 필요"
    
    client = _get_client(api_key, base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1500,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ 오류: {str(e)}"
```

---

## 4. DB 마이그레이션 패턴

### 4-1. 신규 컬럼 추가

`database.py`의 `init_db()` 함수에 마이그레이션 코드 추가:

```python
def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # ... 기존 CREATE TABLE ...
    
    # 구 DB 호환 컬럼 마이그레이션
    for col_sql in [
        "ALTER TABLE wbs_items ADD COLUMN progress INTEGER DEFAULT 0",
        "ALTER TABLE wbs_items ADD COLUMN parent_wbs_id INTEGER",
        "ALTER TABLE wbs_items ADD COLUMN wbs_code TEXT DEFAULT ''",
        "ALTER TABLE wbs_items ADD COLUMN wbs_level INTEGER DEFAULT 1",
        "ALTER TABLE wbs_items ADD COLUMN owner TEXT DEFAULT ''",
        # ← 여기에 새 컬럼 추가
        "ALTER TABLE wbs_items ADD COLUMN new_column TEXT DEFAULT ''",
    ]:
        try:
            c.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # 이미 존재하면 무시
```

> **⚠️ 중요**: `CREATE TABLE IF NOT EXISTS`의 컬럼 정의에도 추가해야 합니다 (신규 DB 생성 시 적용).

### 4-2. 신규 테이블 추가

```python
def init_db():
    # ... 기존 코드 ...
    
    # 새 테이블 생성
    c.execute("""
        CREATE TABLE IF NOT EXISTS meeting_notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            meeting_date TEXT,
            attendees   TEXT,
            summary     TEXT,
            wbs_id      INTEGER,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
```

### 4-3. 데이터 이전 (기존 데이터 변환)

```python
def migrate_status_values():
    """기존 'todo' 상태를 'scheduled'로 변환 (WBS 테이블)."""
    conn = get_conn()
    conn.execute(
        "UPDATE wbs_items SET status='scheduled' WHERE status='todo'"
    )
    conn.commit()
    conn.close()
```

> 이런 함수는 `init_db()` 마지막에 한 번만 실행되도록 작성합니다.

---

## 5. WBS / Action 유형 추가

### 5-1. 코드에서 기본값 추가 (영구적)

`database.py`의 `DEFAULT_WBS_TYPES` 또는 `DEFAULT_ACTION_TYPES` 수정:

```python
DEFAULT_WBS_TYPES = [
    ("To be process 개발", "process 체계도"),
    # ... 기존 항목들 ...
    ("신규 카테고리", "신규 유형"),  # ← 추가
]

DEFAULT_ACTION_TYPES = [
    "task list 및 관련 일정표 작성",
    # ... 기존 항목들 ...
    "신규 Action 유형",  # ← 추가
]
```

> **참고**: `INSERT OR IGNORE`를 사용하므로 앱 재시작 시 자동으로 추가됩니다.

### 5-2. UI에서 추가 (런타임)

⚙️ 시스템/데이터 관리 탭 > WBS 항목 유형 / Action Item 유형에서 직접 추가하면 즉시 적용됩니다.

---

## 6. Streamlit 개발 팁

### 6-1. 개발 중 핫 리로드

```bash
# 소스 변경 감지 자동 리로드 (기본 활성화)
streamlit run app.py --server.port 8577

# 리로드 비활성화 (성능 테스트 시)
streamlit run app.py --server.fileWatcherType none
```

### 6-2. session_state 디버깅

```python
# 개발 시 임시로 추가하여 session_state 내용 확인
with st.expander("🔧 Debug: session_state"):
    st.json(dict(st.session_state))
```

### 6-3. 다이얼로그 (st.dialog) 사용법

```python
@st.dialog("다이얼로그 제목", width="large")
def my_dialog():
    # 다이얼로그 내용
    if st.button("닫기"):
        st.rerun()  # 다이얼로그 닫기

# 다이얼로그 열기 (플래그 기반)
if st.session_state.get("open_my_dialog"):
    my_dialog()

if st.button("열기"):
    st.session_state["open_my_dialog"] = True
    st.rerun()
```

### 6-4. 폼 내 동적 selectbox

```python
# 카테고리 선택 → 유형 목록 연동
cat = st.selectbox("카테고리", cats, key="cat_sel")
types = db.get_wbs_types_by_category(cat)  # 카테고리 변경 시 자동 재실행
wtype = st.selectbox("유형", types, key="type_sel")
```

### 6-5. 컬럼 레이아웃

```python
# 비율 지정 레이아웃
c1, c2, c3 = st.columns([1, 3, 1])  # 1:3:1 비율

# 균등 분할
c1, c2, c3, c4, c5 = st.columns(5)  # 5등분
```

### 6-6. Plotly 다크 테마 설정

모든 차트에 일관된 다크 테마 적용:

```python
fig.update_layout(
    paper_bgcolor="#1e293b",   # 차트 외부 배경
    plot_bgcolor="#0f172a",    # 차트 플롯 영역 배경
    font=dict(color="#e2e8f0", family="Pretendard, sans-serif"),
    margin=dict(l=10, r=10, t=50, b=10),
)
```

---

## 7. 테스트 가이드라인

현재 공식 테스트 프레임워크는 없으나, 다음 방식으로 기능 검증합니다.

### 7-1. DB 함수 단위 테스트 (수동)

```python
# scratch_test.py 생성하여 로컬 테스트
import database as db

def test_wbs_crud():
    db.init_db()
    
    # 삽입 테스트
    new_id = db.insert_wbs({
        "wbs_category": "To be process 개발",
        "wbs_type": "process 체계도",
        "wbs_code": "TEST.1",
        "wbs_level": 1,
        "status": "scheduled",
        "progress": 0,
    })
    assert new_id > 0, "삽입 실패"
    
    # 조회 테스트
    item = db.get_wbs_by_id(new_id)
    assert item is not None
    assert item["wbs_code"] == "TEST.1"
    
    # 삭제 테스트
    db.delete_wbs(new_id)
    assert db.get_wbs_by_id(new_id) is None
    
    print("✅ WBS CRUD 테스트 통과")

test_wbs_crud()
```

### 7-2. 롤업 알고리즘 테스트

```python
def test_rollup():
    db.init_db()
    
    # 부모 WBS 생성
    parent_id = db.insert_wbs({
        "wbs_category": "Test", "wbs_type": "Parent",
        "wbs_code": "T.1", "wbs_level": 1, "status": "in_progress"
    })
    
    # 자식 WBS 생성
    child_id = db.insert_wbs({
        "wbs_category": "Test", "wbs_type": "Child",
        "wbs_code": "T.1.1", "wbs_level": 2,
        "parent_wbs_id": parent_id, "status": "in_progress"
    })
    
    # Action Item 추가 (done 2, todo 1)
    for i in range(2):
        db.insert_action({"action_type": "테스트", "content": f"완료{i}",
                          "status": "done", "wbs_id": child_id})
    db.insert_action({"action_type": "테스트", "content": "미완료",
                      "status": "todo", "wbs_id": child_id})
    
    # 자식 롤업: 2/3 = 67%
    child_prog = db.apply_rollup_progress(child_id)
    assert child_prog == 67, f"자식 진척률 오류: {child_prog}"
    
    # 부모 롤업: 자식 평균 = 67%
    parent_prog = db.apply_rollup_progress(parent_id)
    assert parent_prog == 67, f"부모 진척률 오류: {parent_prog}"
    
    # 정리
    db.delete_wbs(parent_id)
    print("✅ 롤업 알고리즘 테스트 통과")

test_rollup()
```

### 7-3. 파서 테스트

```python
from parser import parse_obsidian_note

def test_parser():
    wbs_content = """\
---
type: wbs
wbs_code: "1.1"
wbs_category: "Test"
wbs_type: "Test Type"
status: scheduled
start_date: "2025-01-01"
due_date: "2025-12-31"
---

## 내용
테스트 내용입니다.
"""
    typ, data = parse_obsidian_note(wbs_content, "test.md")
    assert typ == "wbs", f"유형 오류: {typ}"
    assert data["wbs_code"] == "1.1"
    assert data["content"] == "테스트 내용입니다."
    print("✅ 파서 테스트 통과")

test_parser()
```

### 7-4. Streamlit UI 체크리스트 (수동)

새 기능 추가 후 다음 항목을 수동으로 확인합니다:

- [ ] 새 WBS 루트 추가 후 트리에 표시되는가?
- [ ] Sub WBS 추가 후 들여쓰기가 올바른가?
- [ ] WBS 수정 후 변경사항이 반영되는가?
- [ ] WBS 삭제 후 하위 WBS와 Action이 함께 삭제되는가?
- [ ] 진척률 롤업 후 정확한 값이 반영되는가?
- [ ] Action Item 추가 후 WBS 카드에 Action 수가 업데이트되는가?
- [ ] 상태 필터가 정상 동작하는가?
- [ ] Gantt 차트에 날짜 입력한 항목이 표시되는가?
- [ ] AI 에이전트 탭에서 프로젝트 컨텍스트가 포함된 응답이 오는가?
- [ ] 노트 업로드 후 파싱 결과가 올바른가?

---

## 8. Git 워크플로우

### 8-1. 브랜치 전략

```
main          ← 프로덕션 (안정 버전)
├── dev       ← 개발 통합 브랜치
│   ├── feat/voice-memo-ui    ← 기능 개발
│   ├── fix/rollup-bug        ← 버그 수정
│   └── docs/update-readme   ← 문서 업데이트
└── hotfix/   ← 긴급 수정
```

### 8-2. 커밋 메시지 컨벤션

```
<type>: <short description>

[optional body]
[optional footer]
```

**type 목록**:

| type | 의미 |
|------|------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 코드 리팩토링 (기능 변경 없음) |
| `docs` | 문서 수정 |
| `style` | 코드 포맷팅, CSS |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 설정 파일 수정 |

**예시**:
```
feat: WBS 마법사 Step-by-Step 다이얼로그 추가

- 8단계 WBS 입력 위자드 구현 (@st.dialog 사용)
- 카테고리 선택 → 유형 연동 드롭다운
- 완료 시 .md 다운로드 + DB 직접 저장 옵션

Closes #42
```

### 8-3. .gitignore 확인

```gitignore
# 가상환경 (반드시 제외)
env_WBS_N_Action/

# DB 파일 (개인 데이터 포함 가능)
project_agent.db

# Python 캐시
__pycache__/
*.pyc

# 로그
streamlit.log

# macOS
.DS_Store
```

### 8-4. PR(Pull Request) 체크리스트

PR 생성 전 확인:

- [ ] 브랜치명이 컨벤션을 따르는가?
- [ ] `requirements.txt`가 업데이트 되었는가? (새 패키지 추가 시)
- [ ] `init_db()` 마이그레이션이 작성되었는가? (DB 변경 시)
- [ ] `CLAUDE.md`의 함수 레퍼런스가 업데이트 되었는가? (새 함수 추가 시)
- [ ] 수동 UI 체크리스트를 통과했는가?
- [ ] 커밋 메시지가 컨벤션을 따르는가?

---

## 9. 디버깅 가이드

### 9-1. 로그 확인

```bash
# 실시간 로그 확인
tail -f streamlit.log

# 최근 50줄
tail -50 streamlit.log

# 오류만 필터링
grep -i "error\|exception\|traceback" streamlit.log
```

### 9-2. DB 직접 조회

```bash
sqlite3 project_agent.db

# 전체 WBS 계층 확인
SELECT id, wbs_level, wbs_code, wbs_type, parent_wbs_id, status, progress
FROM wbs_items ORDER BY wbs_level, wbs_code;

# WBS별 Action 통계
SELECT w.wbs_type,
       COUNT(a.id) AS total,
       SUM(CASE WHEN a.status='done' THEN 1 ELSE 0 END) AS done
FROM wbs_items w
LEFT JOIN action_items a ON w.id = a.wbs_id
GROUP BY w.id;

# 마감 초과 항목
SELECT * FROM action_items
WHERE due_date < date('now') AND status != 'done';

# LLM 설정 확인
SELECT * FROM llm_settings;
```

### 9-3. 일반 오류 및 해결법

| 오류 | 원인 | 해결 |
|------|------|------|
| `sqlite3.OperationalError: no such column` | 마이그레이션 누락 | DB 삭제 후 재시작 OR 수동 ALTER TABLE |
| `AttributeError: 'NoneType' object` | `get_wbs_by_id()` 반환값 None | 호출 전 None 체크 |
| `KeyError: 'progress'` | 구 DB 스키마 | `init_db()` 재실행, 마이그레이션 확인 |
| Streamlit `DuplicateWidgetID` | 동일 key 중복 | pfx 패턴으로 고유 key 생성 |
| `faster-whisper` ImportError | 패키지 미설치 | `pip install faster-whisper` |
| OpenAI `AuthenticationError` | 잘못된 API 키 | Admin 탭에서 키 재입력 |
| 포트 충돌 | 기존 프로세스 실행 중 | `./restart.sh` 또는 `pkill -f streamlit` |

### 9-4. 성능 이슈

```python
# WBS 트리가 느릴 때: get_all_wbs_flat() 호출 횟수 확인
# Streamlit 리렌더링 시 매 탭 활성화마다 전체 쿼리 실행됨
# → st.cache_data 적용 고려 (단, 데이터 변경 시 cache 무효화 필요)

@st.cache_data(ttl=30)  # 30초 캐시
def cached_get_all_wbs():
    return db.get_all_wbs_flat()
```

> **⚠️ 주의**: `st.cache_data` 사용 시 데이터 변경 후 `st.cache_data.clear()`를 호출하거나 TTL을 짧게 설정해야 합니다.
