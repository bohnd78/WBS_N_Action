"""
database.py - SQLite 기반 데이터 관리 모듈
Project Agent: WBS & Action Item 관리 (ERP Sales Process)
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "project_agent.db"

# ──────────────────────────────────────────────
# 마스터 데이터 기본값
# ──────────────────────────────────────────────
DEFAULT_WBS_TYPES = [
    ("To be process 개발", "process 체계도"),
    ("To be process 개발", "process map"),
    ("To be process 개발", "시스템 요건 정의서"),
    ("To be process 개발", "Fit-n-Gap 해결방안 정의"),
    ("To be process 개발", "통합 테스트 시나리오"),
    ("Proto typing", "프로세스 설계"),
    ("Proto typing", "조직구조"),
    ("Proto typing", "데이터 정의"),
    ("Proto typing", "Configuration"),
    ("Proto typing", "개발항목 및 인터페이스 정의"),
    ("Sub-project", "매출마감 통합관리 체계 구축"),
    ("Sub-project", "Special Deal and rebate 프로세스 개선"),
    ("Sub-project", "주문 통합 시스템 구축"),
    ("Sub-project", "고객별 출하조건 기반-재고 할당 시뮬레이션 시스템 구축"),
    ("Sub-project", "RMA 프로세스 간소화"),
    ("Sub-project", "PO전량 관리 프로세스 구축"),
    ("Risk 관리", "L4 기준으로 개발정의서 작성하는 불합리성 대응"),
    ("Risk 관리", "RAP modeling 역량 미확보로 인한 스펙정의서 작성 속도 지연 및 품질 저하 우려"),
]

DEFAULT_ACTION_TYPES = [
    "task list 및 관련 일정표 작성",
    "미팅(출장)",
    "문서작성",
    "개발(분석/설계)",
    "준비작업",
    "역량확보",
    "테스트",
]

# Action Item 상태
STATUS_OPTIONS = ["todo", "in_progress", "done", "blocked"]
STATUS_EMOJI   = {"todo": "⬜", "in_progress": "🔄", "done": "✅", "blocked": "🚫"}
STATUS_LABEL   = {"todo": "대기", "in_progress": "진행중", "done": "완료", "blocked": "블록"}
STATUS_COLOR   = {"todo": "#64748b", "in_progress": "#f59e0b", "done": "#22c55e", "blocked": "#ef4444"}

# WBS 계층 노드 상태 (일정 관리 기준)
WBS_STATUS_OPTIONS = ["scheduled", "in_progress", "done", "cancelled"]
WBS_STATUS_EMOJI   = {"scheduled": "⏳", "in_progress": "🔄", "done": "✅", "cancelled": "🚫"}
WBS_STATUS_LABEL   = {"scheduled": "예정", "in_progress": "실행중", "done": "완료", "cancelled": "취소"}
WBS_STATUS_COLOR   = {"scheduled": "#64748b", "in_progress": "#f59e0b", "done": "#22c55e", "cancelled": "#475569"}


# ──────────────────────────────────────────────
# DB 연결 & 초기화
# ──────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # WBS 항목 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS wbs_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            wbs_category    TEXT,
            wbs_type        TEXT,
            registered_date TEXT,
            content         TEXT,
            start_date      TEXT,
            due_date        TEXT,
            end_date        TEXT,
            status          TEXT DEFAULT 'todo',
            progress        INTEGER DEFAULT 0,
            notes           TEXT,
            source_file     TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 구 DB 호환 컬럼 마이그레이션
    for col_sql in [
        "ALTER TABLE wbs_items ADD COLUMN progress INTEGER DEFAULT 0",
        "ALTER TABLE wbs_items ADD COLUMN parent_wbs_id INTEGER",
        "ALTER TABLE wbs_items ADD COLUMN wbs_code TEXT DEFAULT ''",
        "ALTER TABLE wbs_items ADD COLUMN wbs_level INTEGER DEFAULT 1",
        "ALTER TABLE wbs_items ADD COLUMN owner TEXT DEFAULT ''",
    ]:
        try:
            c.execute(col_sql)
            conn.commit()
        except Exception:
            pass

    # Action Item 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS action_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type     TEXT,
            registered_date TEXT,
            content         TEXT,
            start_date      TEXT,
            due_date        TEXT,
            end_date        TEXT,
            status          TEXT DEFAULT 'todo',
            notes           TEXT,
            wbs_id          INTEGER,
            source_file     TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # WBS 유형 마스터
    c.execute("""
        CREATE TABLE IF NOT EXISTS wbs_types (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            category  TEXT NOT NULL,
            type_name TEXT NOT NULL,
            UNIQUE(category, type_name)
        )
    """)

    # Action 유형 마스터
    c.execute("""
        CREATE TABLE IF NOT EXISTS action_types (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT NOT NULL UNIQUE
        )
    """)

    # LLM 설정 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS llm_settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # 기본 WBS 유형 삽입
    c.executemany(
        "INSERT OR IGNORE INTO wbs_types (category, type_name) VALUES (?, ?)",
        DEFAULT_WBS_TYPES,
    )

    # 기본 Action 유형 삽입
    c.executemany(
        "INSERT OR IGNORE INTO action_types (type_name) VALUES (?)",
        [(t,) for t in DEFAULT_ACTION_TYPES],
    )

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# WBS CRUD
# ──────────────────────────────────────────────
def get_wbs_items(filters: dict | None = None) -> pd.DataFrame:
    conn = get_conn()
    query = "SELECT * FROM wbs_items"
    params: list = []
    conditions: list[str] = []

    if filters:
        if filters.get("category"):
            conditions.append("wbs_category = ?")
            params.append(filters["category"])
        if filters.get("status"):
            conditions.append("status = ?")
            params.append(filters["status"])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY registered_date DESC, id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    # progress 컬럼 보장
    if "progress" not in df.columns:
        df["progress"] = 0
    return df


def get_wbs_by_id(wbs_id: int) -> dict | None:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM wbs_items WHERE id=?", conn, params=(wbs_id,))
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None


def insert_wbs(data: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO wbs_items
           (wbs_category, wbs_type, registered_date, content,
            start_date, due_date, end_date, status, progress, notes, source_file,
            parent_wbs_id, wbs_code, wbs_level, owner)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("wbs_category", ""),
            data.get("wbs_type", ""),
            data.get("registered_date", datetime.now().strftime("%Y-%m-%d")),
            data.get("content", ""),
            data.get("start_date", ""),
            data.get("due_date", ""),
            data.get("end_date", ""),
            data.get("status", "scheduled"),
            data.get("progress", 0),
            data.get("notes", ""),
            data.get("source_file", ""),
            data.get("parent_wbs_id"),
            data.get("wbs_code", ""),
            data.get("wbs_level", 1),
            data.get("owner", ""),
        ),
    )
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id


def update_wbs(wbs_id: int, data: dict):
    conn = get_conn()
    conn.execute(
        """UPDATE wbs_items
           SET wbs_category=?, wbs_type=?, content=?,
               start_date=?, due_date=?, end_date=?, status=?, progress=?, notes=?,
               parent_wbs_id=?, wbs_code=?, wbs_level=?, owner=?
           WHERE id=?""",
        (
            data.get("wbs_category", ""),
            data.get("wbs_type", ""),
            data.get("content", ""),
            data.get("start_date", ""),
            data.get("due_date", ""),
            data.get("end_date", ""),
            data.get("status", "scheduled"),
            data.get("progress", 0),
            data.get("notes", ""),
            data.get("parent_wbs_id"),
            data.get("wbs_code", ""),
            data.get("wbs_level", 1),
            data.get("owner", ""),
            wbs_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_wbs(wbs_id: int):
    """WBS 삭제 - 하위 자식들도 함께 삭제."""
    conn = get_conn()
    # 자식 먼저 재귀 삭제
    children = get_wbs_children(wbs_id)
    conn.close()
    for child in children:
        delete_wbs(child["id"])
    conn = get_conn()
    conn.execute("DELETE FROM wbs_items WHERE id=?", (wbs_id,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# WBS 계층 구조 함수
# ──────────────────────────────────────────────
def get_wbs_children(parent_id: int | None) -> list[dict]:
    """특정 부모 ID의 직속 자식 WBS 목록 반환."""
    conn = get_conn()
    if parent_id is None:
        df = pd.read_sql_query(
            "SELECT * FROM wbs_items WHERE parent_wbs_id IS NULL ORDER BY wbs_code, id",
            conn,
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM wbs_items WHERE parent_wbs_id=? ORDER BY wbs_code, id",
            conn, params=(parent_id,),
        )
    conn.close()
    for col in ("progress", "parent_wbs_id", "wbs_code", "wbs_level", "owner"):
        if col not in df.columns:
            df[col] = None
    return df.to_dict("records")


def get_all_wbs_flat() -> list[dict]:
    """계층 정렬(wbs_code 기준) 전체 WBS 목록 반환."""
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM wbs_items ORDER BY wbs_level, wbs_code, id", conn
    )
    conn.close()
    for col in ("progress", "parent_wbs_id", "wbs_code", "wbs_level", "owner"):
        if col not in df.columns:
            df[col] = None
    return df.to_dict("records")


def build_children_map(items: list[dict]) -> dict:
    """items 리스트로 {parent_id: [child, ...]} 매핑 생성."""
    cmap: dict = {None: []}
    for item in items:
        pid = item.get("parent_wbs_id")
        if pid not in cmap:
            cmap[pid] = []
        cmap[pid].append(item)
    return cmap


def calculate_rollup_progress(wbs_id: int) -> int:
    """
    재귀적으로 WBS 진척률 계산.
    - 자식 없는 리프: Action Item 완료 비율 OR 수동 progress 값
    - 부모 노드: 활성(취소 제외) 자식들의 진척률 평균
    """
    children = get_wbs_children(wbs_id)
    if not children:
        # 리프 노드: Action Item 기반 자동계산 우선, 없으면 수동값
        stats = get_action_stats_for_wbs(wbs_id)
        if stats["total"] > 0:
            return stats["auto_progress"]
        wbs = get_wbs_by_id(wbs_id)
        return int(wbs.get("progress") or 0) if wbs else 0

    # 부모 노드: 취소 제외한 자식 평균
    active = [c for c in children if c.get("status") != "cancelled"]
    if not active:
        return 0
    child_progs = [calculate_rollup_progress(c["id"]) for c in active]
    return round(sum(child_progs) / len(child_progs))


def apply_rollup_progress(wbs_id: int) -> int:
    """재귀 롤업 계산 후 DB에 저장. 계산된 값 반환."""
    prog = calculate_rollup_progress(wbs_id)
    conn = get_conn()
    conn.execute("UPDATE wbs_items SET progress=? WHERE id=?", (prog, wbs_id))
    conn.commit()
    conn.close()
    return prog


def apply_rollup_all() -> int:
    """루트 노드 기준으로 전체 WBS 진척률 재계산 후 DB 업데이트. 처리 건수 반환."""
    roots = get_wbs_children(None)
    count = 0

    def _rollup_recursive(wbs_id: int):
        nonlocal count
        children = get_wbs_children(wbs_id)
        for child in children:
            _rollup_recursive(child["id"])
        apply_rollup_progress(wbs_id)
        count += 1

    for root in roots:
        _rollup_recursive(root["id"])
    return count


# ──────────────────────────────────────────────
# Action Item CRUD
# ──────────────────────────────────────────────
def get_action_stats_for_wbs(wbs_id: int) -> dict:
    """특정 WBS에 연결된 Action Item 통계 반환."""
    conn = get_conn()
    c = conn.cursor()
    total  = c.execute("SELECT COUNT(*) FROM action_items WHERE wbs_id=?", (wbs_id,)).fetchone()[0]
    done   = c.execute("SELECT COUNT(*) FROM action_items WHERE wbs_id=? AND status='done'", (wbs_id,)).fetchone()[0]
    in_prog= c.execute("SELECT COUNT(*) FROM action_items WHERE wbs_id=? AND status='in_progress'", (wbs_id,)).fetchone()[0]
    blocked= c.execute("SELECT COUNT(*) FROM action_items WHERE wbs_id=? AND status='blocked'", (wbs_id,)).fetchone()[0]
    conn.close()
    auto_progress = round((done / total) * 100) if total > 0 else 0
    return {
        "total": total, "done": done,
        "in_progress": in_prog, "blocked": blocked,
        "auto_progress": auto_progress,
    }


def apply_auto_progress(wbs_id: int) -> int:
    """연결된 Action Item 완료 비율로 WBS 진척률 자동 업데이트. 계산된 값 반환."""
    stats = get_action_stats_for_wbs(wbs_id)
    prog  = stats["auto_progress"]
    conn  = get_conn()
    conn.execute("UPDATE wbs_items SET progress=? WHERE id=?", (prog, wbs_id))
    conn.commit()
    conn.close()
    return prog


def get_action_items(filters: dict | None = None) -> pd.DataFrame:
    conn = get_conn()
    query = """
        SELECT a.*, w.wbs_type AS linked_wbs, w.wbs_category AS linked_wbs_cat
        FROM action_items a
        LEFT JOIN wbs_items w ON a.wbs_id = w.id
    """
    params: list = []
    conditions: list[str] = []

    if filters:
        if filters.get("action_type"):
            conditions.append("a.action_type = ?")
            params.append(filters["action_type"])
        if filters.get("status"):
            conditions.append("a.status = ?")
            params.append(filters["status"])
        if filters.get("wbs_id"):
            conditions.append("a.wbs_id = ?")
            params.append(filters["wbs_id"])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY a.registered_date DESC, a.id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_action_by_id(action_id: int) -> dict | None:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM action_items WHERE id=?", conn, params=(action_id,))
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None


def insert_action(data: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO action_items
           (action_type, registered_date, content, start_date, due_date,
            end_date, status, notes, wbs_id, source_file)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("action_type", ""),
            data.get("registered_date", datetime.now().strftime("%Y-%m-%d")),
            data.get("content", ""),
            data.get("start_date", ""),
            data.get("due_date", ""),
            data.get("end_date", ""),
            data.get("status", "todo"),
            data.get("notes", ""),
            data.get("wbs_id"),
            data.get("source_file", ""),
        ),
    )
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id


def update_action(action_id: int, data: dict):
    conn = get_conn()
    conn.execute(
        """UPDATE action_items
           SET action_type=?, content=?, start_date=?, due_date=?,
               end_date=?, status=?, notes=?, wbs_id=?
           WHERE id=?""",
        (
            data.get("action_type", ""),
            data.get("content", ""),
            data.get("start_date", ""),
            data.get("due_date", ""),
            data.get("end_date", ""),
            data.get("status", "todo"),
            data.get("notes", ""),
            data.get("wbs_id"),
            action_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_action(action_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM action_items WHERE id=?", (action_id,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# 마스터 데이터 조회/관리
# ──────────────────────────────────────────────
def get_wbs_categories() -> list[str]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM wbs_types ORDER BY category")
    cats = [r[0] for r in c.fetchall()]
    conn.close()
    return cats


def get_wbs_types_by_category(category: str) -> list[str]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT type_name FROM wbs_types WHERE category=? ORDER BY type_name", (category,))
    types = [r[0] for r in c.fetchall()]
    conn.close()
    return types


def get_all_wbs_types() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM wbs_types ORDER BY category, type_name", conn)
    conn.close()
    return df


def add_wbs_type(category: str, type_name: str) -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO wbs_types (category, type_name) VALUES (?, ?)", (category, type_name)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def delete_wbs_type(type_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM wbs_types WHERE id=?", (type_id,))
    conn.commit()
    conn.close()


def get_action_type_names() -> list[str]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT type_name FROM action_types ORDER BY type_name")
    types = [r[0] for r in c.fetchall()]
    conn.close()
    return types


def get_all_action_types() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM action_types ORDER BY type_name", conn)
    conn.close()
    return df


def add_action_type(type_name: str) -> bool:
    conn = get_conn()
    try:
        conn.execute("INSERT INTO action_types (type_name) VALUES (?)", (type_name,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def delete_action_type(type_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM action_types WHERE id=?", (type_id,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# LLM 설정
# ──────────────────────────────────────────────
def get_llm_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    c = conn.cursor()
    row = c.execute("SELECT value FROM llm_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_llm_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO llm_settings (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# 대시보드 요약 통계
# ──────────────────────────────────────────────
def get_summary_stats() -> dict:
    conn = get_conn()
    c = conn.cursor()

    wbs_total       = c.execute("SELECT COUNT(*) FROM wbs_items").fetchone()[0]
    wbs_done        = c.execute("SELECT COUNT(*) FROM wbs_items WHERE status='done'").fetchone()[0]
    wbs_blocked     = c.execute("SELECT COUNT(*) FROM wbs_items WHERE status='blocked'").fetchone()[0]
    wbs_in_progress = c.execute("SELECT COUNT(*) FROM wbs_items WHERE status='in_progress'").fetchone()[0]

    act_total       = c.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
    act_done        = c.execute("SELECT COUNT(*) FROM action_items WHERE status='done'").fetchone()[0]
    act_blocked     = c.execute("SELECT COUNT(*) FROM action_items WHERE status='blocked'").fetchone()[0]
    act_in_progress = c.execute("SELECT COUNT(*) FROM action_items WHERE status='in_progress'").fetchone()[0]

    today      = datetime.now().strftime("%Y-%m-%d")
    week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    upcoming_wbs = c.execute(
        "SELECT COUNT(*) FROM wbs_items WHERE due_date BETWEEN ? AND ? AND status != 'done'",
        (today, week_later),
    ).fetchone()[0]
    upcoming_act = c.execute(
        "SELECT COUNT(*) FROM action_items WHERE due_date BETWEEN ? AND ? AND status != 'done'",
        (today, week_later),
    ).fetchone()[0]

    # 전체 평균 진척률
    avg_progress_row = c.execute("SELECT AVG(progress) FROM wbs_items").fetchone()
    avg_progress = round(avg_progress_row[0] or 0, 1)

    conn.close()
    return {
        "wbs_total": wbs_total,
        "wbs_done": wbs_done,
        "wbs_blocked": wbs_blocked,
        "wbs_in_progress": wbs_in_progress,
        "act_total": act_total,
        "act_done": act_done,
        "act_blocked": act_blocked,
        "act_in_progress": act_in_progress,
        "upcoming_wbs": upcoming_wbs,
        "upcoming_act": upcoming_act,
        "avg_progress": avg_progress,
    }


# ──────────────────────────────────────────────
# Gantt 용 데이터
# ──────────────────────────────────────────────
def get_gantt_data() -> pd.DataFrame:
    """start_date / due_date 가 있는 WBS 항목 반환."""
    conn = get_conn()
    df = pd.read_sql_query(
        """SELECT id, wbs_category, wbs_type, content, start_date, due_date, end_date,
                  status, progress
           FROM wbs_items
           WHERE start_date != '' AND due_date != ''
           ORDER BY start_date""",
        conn,
    )
    conn.close()
    if "progress" not in df.columns:
        df["progress"] = 0
    return df


def get_action_gantt_data() -> pd.DataFrame:
    """start_date / due_date 가 있는 Action Item 반환."""
    conn = get_conn()
    df = pd.read_sql_query(
        """SELECT a.id, a.action_type, a.content, a.start_date, a.due_date, a.end_date,
                  a.status, w.wbs_type AS linked_wbs
           FROM action_items a
           LEFT JOIN wbs_items w ON a.wbs_id = w.id
           WHERE a.start_date != '' AND a.due_date != ''
           ORDER BY a.start_date""",
        conn,
    )
    conn.close()
    return df
