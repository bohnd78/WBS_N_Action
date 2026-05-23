"""
app.py - Project Agent: WBS & Action Item 관리
ERP Sales Process 구현 프로젝트 관리 도구
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import database as db
import charts as ch
import agent as ag

st.set_page_config(
    page_title="Project Agent · ERP",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 글로벌 CSS ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0f172a; color: #e2e8f0; }
.block-container { padding: 1.2rem 1.5rem; }

/* 탭 */
.stTabs [data-baseweb="tab-list"] { gap:6px; background:transparent; border-bottom:1px solid #1e293b; }
.stTabs [data-baseweb="tab"] { background:#1e293b; color:#94a3b8; border-radius:8px 8px 0 0;
  padding:8px 18px; font-weight:500; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg,#7c3aed,#4f46e5) !important;
  color:#fff !important; }

/* 카드 */
.kpi-card { background:#1e293b; border-radius:12px; padding:16px; text-align:center;
  border:1px solid #334155; position:relative; overflow:hidden; }
.kpi-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px;
  background:linear-gradient(90deg,#7c3aed,#4f46e5); }
.kpi-val { font-size:2rem; font-weight:700; color:#f1f5f9; line-height:1.1; }
.kpi-label { font-size:0.75rem; color:#64748b; margin-top:4px; }
.kpi-delta { font-size:0.8rem; margin-top:6px; }

/* 상태 뱃지 */
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.72rem;
  font-weight:600; letter-spacing:.3px; }
.badge-todo        { background:#1e293b; color:#94a3b8; border:1px solid #475569; }
.badge-in_progress { background:#451a03; color:#f59e0b; border:1px solid #92400e; }
.badge-done        { background:#052e16; color:#22c55e; border:1px solid #166534; }
.badge-blocked     { background:#450a0a; color:#ef4444; border:1px solid #991b1b; }

/* WBS 트리 */
.wbs-node { border-radius:8px; padding:10px 14px; margin:3px 0;
  border:1px solid #334155; background:#1e293b; transition:border .15s; }
.wbs-node:hover { border-color:#7c3aed; }
.wbs-node-l1 { border-left:4px solid #7c3aed; }
.wbs-node-l2 { border-left:4px solid #2563eb; margin-left:20px; }
.wbs-node-l3 { border-left:4px solid #0891b2; margin-left:40px; }
.wbs-node-l4 { border-left:4px solid #059669; margin-left:60px; }

/* 항목 카드 */
.item-card { background:#1e293b; border:1px solid #334155; border-radius:10px;
  padding:14px 16px; margin-bottom:8px; transition:border .2s; }
.item-card:hover { border-color:#7c3aed; }
.item-card-title { font-weight:600; color:#f1f5f9; font-size:0.95rem; }
.item-card-meta  { font-size:0.78rem; color:#64748b; margin-top:4px; }

/* 입력 요소 */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
  background:#1e293b !important; color:#e2e8f0 !important; border-color:#334155 !important; }
.stButton > button { border-radius:8px; font-weight:500; }
.stButton > button[kind="primary"] {
  background:linear-gradient(135deg,#7c3aed,#4f46e5) !important;
  border:none !important; color:#fff !important; }
div[data-testid="stExpander"] { background:#1e293b; border:1px solid #334155;
  border-radius:10px; margin-bottom:6px; }
div[data-testid="stExpander"]:hover { border-color:#7c3aed; }
.stMetric { background:#1e293b; border-radius:10px; padding:12px; border:1px solid #334155; }
.alert-warn { background:#451a03; border:1px solid #92400e; border-radius:8px;
  padding:10px 14px; color:#fbbf24; font-size:0.85rem; margin:6px 0; }
.chat-user { background:#1e3a5f; border-radius:10px 10px 2px 10px; padding:10px 14px;
  margin:6px 0; color:#e2e8f0; }
.chat-ai { background:#1e293b; border-radius:2px 10px 10px 10px; padding:10px 14px;
  margin:6px 0; color:#e2e8f0; border-left:3px solid #7c3aed; }
</style>
""", unsafe_allow_html=True)

db.init_db()

STATUS_OPTIONS = db.STATUS_OPTIONS
STATUS_EMOJI   = db.STATUS_EMOJI
STATUS_LABEL   = db.STATUS_LABEL
STATUS_COLOR   = db.STATUS_COLOR
WBS_STATUS_OPTIONS = db.WBS_STATUS_OPTIONS
WBS_STATUS_EMOJI   = db.WBS_STATUS_EMOJI
WBS_STATUS_LABEL   = db.WBS_STATUS_LABEL
WBS_STATUS_COLOR   = db.WBS_STATUS_COLOR


# ── 유틸 ────────────────────────────────────────
def parse_date_safe(val) -> date | None:
    if not val or str(val).strip() in ("", "nan", "None", "NaT"):
        return None
    try:
        return datetime.strptime(str(val).strip()[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def d2s(d) -> str:
    return str(d) if d else ""

def badge(status: str, wbs: bool = False) -> str:
    if wbs:
        lbl = WBS_STATUS_LABEL.get(status, status)
        em  = WBS_STATUS_EMOJI.get(status, "")
        col = WBS_STATUS_COLOR.get(status, "#64748b")
        return (f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
                f'font-size:.72rem;font-weight:600;background:{col}22;color:{col};'
                f'border:1px solid {col}55">{em} {lbl}</span>')
    lbl = STATUS_LABEL.get(status, status)
    return f'<span class="badge badge-{status}">{STATUS_EMOJI.get(status,"")} {lbl}</span>'

def days_until(due: str) -> int | None:
    if not due or str(due).strip() in ("", "nan"):
        return None
    try:
        return (datetime.strptime(due[:10], "%Y-%m-%d").date() - date.today()).days
    except Exception:
        return None

def deadline_chip(due: str) -> str:
    d = days_until(due)
    if d is None:
        return ""
    if d < 0:
        return f'<span style="color:#ef4444;font-size:.75rem">⏰ {abs(d)}일 초과</span>'
    if d <= 3:
        return f'<span style="color:#f59e0b;font-size:.75rem">⏰ D-{d}</span>'
    if d <= 7:
        return f'<span style="color:#fbbf24;font-size:.75rem">📅 D-{d}</span>'
    return f'<span style="color:#64748b;font-size:.75rem">📅 D-{d}</span>'


# ── 헤더 KPI ────────────────────────────────────
def render_header():
    stats = db.get_summary_stats()
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem">
      <div style="font-size:2rem">🚀</div>
      <div>
        <div style="font-size:1.4rem;font-weight:700;color:#f1f5f9">Project Agent</div>
        <div style="font-size:.8rem;color:#64748b">ERP Sales Process 구현 · WBS & Action Item 관리</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(7)
    kpis = [
        ("📋 WBS 총계",      stats["wbs_total"],      "#7c3aed"),
        ("✅ WBS 완료",       stats["wbs_done"],        "#22c55e"),
        ("🔄 WBS 진행중",    stats["wbs_in_progress"], "#f59e0b"),
        ("🚫 WBS 블록",      stats["wbs_blocked"],     "#ef4444"),
        ("📌 Action 총계",   stats["act_total"],       "#0891b2"),
        ("✅ Action 완료",   stats["act_done"],        "#22c55e"),
        ("⏰ 7일내 마감",    stats["upcoming_wbs"] + stats["upcoming_act"], "#f43f5e"),
    ]
    for col, (label, val, color) in zip(cols, kpis):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
              <div style="position:absolute;top:0;left:0;right:0;height:3px;background:{color}"></div>
              <div class="kpi-val" style="color:{color}">{val}</div>
              <div class="kpi-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    # 진행중/블록 알림
    upcoming = stats["upcoming_wbs"] + stats["upcoming_act"]
    if upcoming:
        st.markdown(f'<div class="alert-warn">⚠️ 7일 이내 마감 {upcoming}건 — Action Items 탭에서 확인하세요</div>',
                    unsafe_allow_html=True)
    st.divider()


# ── WBS 탭 ──────────────────────────────────────
def render_wbs_tab():
    st.subheader("📋 WBS 계층 관리")

    # 툴바
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        f_search = st.text_input("🔍 검색", placeholder="유형/내용 검색...", key="wbs_f_search")
    with c2:
        f_status = st.selectbox("상태 필터", ["전체"] + WBS_STATUS_OPTIONS,
                                format_func=lambda x: "전체" if x == "전체" else WBS_STATUS_LABEL.get(x, x),
                                key="wbs_f_status")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("➕ 루트 WBS", use_container_width=True, type="primary"):
                st.session_state["show_wbs_form"] = not st.session_state.get("show_wbs_form", False)
                st.session_state.pop("edit_wbs_id", None)
                st.session_state.pop("add_child_of", None)
        with col_b:
            if st.button("🔄 전체 롤업", use_container_width=True,
                         help="모든 WBS 진척률을 하위→상위 순으로 재계산"):
                n = db.apply_rollup_all()
                st.success(f"✅ {n}개 WBS 진척률 재계산 완료")
                st.rerun()

    # 루트 WBS 추가 폼
    if st.session_state.get("show_wbs_form"):
        with st.container(border=True):
            st.markdown("#### ➕ 새 WBS (루트)")
            _wbs_form(mode="add")

    # 하위 WBS 추가 폼
    if st.session_state.get("add_child_of"):
        pid = st.session_state["add_child_of"]
        parent = db.get_wbs_by_id(pid)
        with st.container(border=True):
            st.markdown(f"#### ➕ 하위 WBS 추가 → 상위: **{parent.get('wbs_type','') if parent else pid}**")
            _wbs_form(mode="add", parent_id=pid)

    # 수정 폼
    if st.session_state.get("edit_wbs_id"):
        with st.container(border=True):
            st.markdown(f"#### ✏️ WBS 수정 (ID:{st.session_state['edit_wbs_id']})")
            _wbs_form(mode="edit", item_id=st.session_state["edit_wbs_id"])

    st.divider()

    # 트리 렌더링
    all_items = db.get_all_wbs_flat()
    if f_search:
        kw = f_search.lower()
        matched_ids = {
            i["id"] for i in all_items
            if kw in (i.get("wbs_type") or "").lower()
            or kw in (i.get("content") or "").lower()
        }
        # 매칭 항목 + 그 조상까지 포함
        id_to_item = {i["id"]: i for i in all_items}
        def _ancestors(iid):
            pid = id_to_item.get(iid, {}).get("parent_wbs_id")
            return {pid} | _ancestors(pid) if pid else set()
        visible = matched_ids | {a for mid in matched_ids for a in _ancestors(mid)}
        all_items = [i for i in all_items if i["id"] in visible]

    if f_status != "전체":
        all_items = [i for i in all_items if i.get("status") == f_status]

    cmap = db.build_children_map(all_items)
    roots = cmap.get(None, [])

    if not roots and not all_items:
        st.info("등록된 WBS 항목이 없습니다. ➕ 루트 WBS 버튼으로 추가하세요.")
        return

    for node in roots:
        _render_wbs_node(node, depth=1, cmap=cmap)



def _wbs_form(mode="add", item_id=None, parent_id=None):
    p   = db.get_wbs_by_id(item_id) if mode == "edit" and item_id else {}
    pfx = f"wbs_{mode}_{item_id or parent_id or 'new'}"

    # 계층 정보
    all_wbs = db.get_all_wbs_flat()
    wbs_opts = ["없음 (루트)"] + [
        f"{'  ' * (int(r.get('wbs_level') or 1)-1)}[{r.get('wbs_code','')}] {r['wbs_type']} (ID:{r['id']})"
        for r in all_wbs if mode == "add" or r["id"] != item_id
    ]
    cur_parent = "없음 (루트)"
    pid_val = p.get("parent_wbs_id") or parent_id
    if pid_val:
        matched = [o for o in wbs_opts if f"ID:{pid_val})" in o]
        if matched: cur_parent = matched[0]

    sel_parent = st.selectbox("📁 상위 WBS", wbs_opts,
                              index=wbs_opts.index(cur_parent) if cur_parent in wbs_opts else 0,
                              key=f"{pfx}_parent")
    resolved_parent_id = None
    if sel_parent != "없음 (루트)":
        try: resolved_parent_id = int(sel_parent.split("ID:")[1].rstrip(")"))
        except Exception: pass

    c0, c1 = st.columns([1, 3])
    with c0:
        wbs_code = st.text_input("WBS 코드", value=p.get("wbs_code",""), placeholder="1.1", key=f"{pfx}_code")
    with c1:
        cats  = db.get_wbs_categories()
        def_c = cats.index(p["wbs_category"]) if p.get("wbs_category") in cats else 0
        cat   = st.selectbox("카테고리 *", cats, index=def_c, key=f"{pfx}_cat")
    types = db.get_wbs_types_by_category(cat)
    col1, col2 = st.columns(2)
    with col1:
        def_t = types.index(p["wbs_type"]) if p.get("wbs_type") in types else 0
        wtype = st.selectbox("항목 유형 *", types, index=def_t, key=f"{pfx}_type")
    with col2:
        owner = st.text_input("담당자", value=p.get("owner",""), key=f"{pfx}_owner")

    content = st.text_area("내용", value=p.get("content",""), height=70, key=f"{pfx}_content")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: sd = st.date_input("시작일",     value=parse_date_safe(p.get("start_date")), key=f"{pfx}_sd")
    with c2: dd = st.date_input("종료예정일", value=parse_date_safe(p.get("due_date")),   key=f"{pfx}_dd")
    with c3: ed = st.date_input("종료일",     value=parse_date_safe(p.get("end_date")),   key=f"{pfx}_ed")
    with c4:
        cur_st = p.get("status","scheduled")
        def_s  = WBS_STATUS_OPTIONS.index(cur_st) if cur_st in WBS_STATUS_OPTIONS else 0
        status = st.selectbox("일정 상태", WBS_STATUS_OPTIONS, index=def_s,
                              format_func=lambda x: f"{WBS_STATUS_EMOJI[x]} {WBS_STATUS_LABEL[x]}",
                              key=f"{pfx}_st")
    with c5:
        prog = st.slider("진척률(%) 수동", 0, 100, int(p.get("progress",0)), key=f"{pfx}_prog")

    notes = st.text_area("기타", value=p.get("notes",""), height=50, key=f"{pfx}_notes")

    b1, b2 = st.columns([1, 5])
    with b1:
        if st.button("💾 저장", key=f"{pfx}_save", type="primary"):
            lvl = 1
            if resolved_parent_id:
                par = db.get_wbs_by_id(resolved_parent_id)
                lvl = int(par.get("wbs_level") or 1) + 1 if par else 2
            data = dict(wbs_category=cat, wbs_type=wtype, owner=owner,
                        registered_date=p.get("registered_date", date.today().isoformat()),
                        content=content, start_date=d2s(sd), due_date=d2s(dd),
                        end_date=d2s(ed), status=status, progress=prog, notes=notes,
                        parent_wbs_id=resolved_parent_id, wbs_code=wbs_code, wbs_level=lvl)
            if mode == "add":
                db.insert_wbs(data)
                st.session_state.pop("show_wbs_form", None)
                st.session_state.pop("add_child_of", None)
            else:
                db.update_wbs(item_id, data)
                st.session_state.pop("edit_wbs_id", None)
            st.success("✅ 저장되었습니다!"); st.rerun()
    with b2:
        if st.button("취소", key=f"{pfx}_cancel"):
            st.session_state.pop("show_wbs_form", None)
            st.session_state.pop("edit_wbs_id", None)
            st.session_state.pop("add_child_of", None); st.rerun()


def _render_wbs_node(node: dict, depth: int, cmap: dict):
    wid      = int(node["id"])
    prog     = int(node.get("progress") or 0)
    st_val   = node.get("status", "scheduled")
    dl       = deadline_chip(node.get("due_date", ""))
    code     = node.get("wbs_code", "") or ""
    children = cmap.get(wid, [])
    astats   = db.get_action_stats_for_wbs(wid)
    lvl_cls  = f"wbs-node-l{min(depth, 4)}"
    st_badge = badge(st_val, wbs=True)

    # ── Main WBS vs Sub WBS 구분 ──────────────────
    if depth == 1:
        # Main WBS: 굵은 헤더
        kind_label = '<span style="font-size:.7rem;background:#7c3aed22;color:#a78bfa;border:1px solid #7c3aed55;border-radius:4px;padding:1px 7px;margin-right:6px">MAIN</span>'
        icon = "📂"
        child_badge = (f'<span style="font-size:.72rem;background:#1e293b;color:#64748b;'
                       f'border:1px solid #334155;border-radius:4px;padding:1px 7px;margin-left:6px">'
                       f'{len(children)} Sub WBS</span>') if children else ""
    else:
        kind_label = ""
        icon = "📁" if children else "📄"
        child_badge = (f'<span style="font-size:.72rem;color:#64748b;margin-left:4px">'
                       f'({len(children)} Sub)</span>') if children else ""

    act_info = f' <span style="color:#0891b2;font-size:.75rem">🔗{astats["done"]}/{astats["total"]}</span>' \
               if astats["total"] > 0 else ""
    owner_str = f'<span style="color:#94a3b8">{node.get("owner","")}</span>&nbsp;' if node.get("owner") else ""

    st.markdown(
        f'<div class="wbs-node {lvl_cls}">'
        f'{kind_label}'
        f'<span style="font-size:.8rem;color:#64748b;margin-right:4px">{code}</span>'
        f'{icon} <b style="color:#f1f5f9;font-size:{"1rem" if depth==1 else ".92rem"}">{node["wbs_type"]}</b>'
        f'{child_badge}&nbsp;&nbsp;{st_badge}{act_info}'
        f'<span style="float:right;font-size:.78rem">{owner_str}{dl}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 진척률 바 (depth에 따라 색 다르게)
    bar_colors = ["#7c3aed", "#2563eb", "#0891b2", "#059669"]
    col_hex = bar_colors[min(depth - 1, 3)]
    st.markdown(
        f'<div style="background:#1e293b;border-radius:3px;height:6px;margin:-4px 0 4px">'
        f'<div style="background:{col_hex};height:6px;border-radius:3px;width:{prog}%"></div>'
        f'</div>'
        f'<div style="font-size:.72rem;color:#64748b;text-align:right;margin-bottom:4px">{prog}%</div>',
        unsafe_allow_html=True,
    )

    # 버튼 + 내용
    btn_col = st.columns([1, 1, 1, 1, 4])
    with btn_col[0]:
        if st.button("✏️", key=f"ewbs_{wid}", use_container_width=True, help="수정"):
            st.session_state["edit_wbs_id"] = wid
            st.session_state.pop("show_wbs_form", None)
            st.session_state.pop("add_child_of", None)
            st.rerun()
    with btn_col[1]:
        if st.button("➕", key=f"cwbs_{wid}", use_container_width=True,
                     help="Sub WBS 추가" if depth == 1 else "하위 WBS 추가"):
            st.session_state["add_child_of"] = wid
            st.session_state.pop("show_wbs_form", None)
            st.session_state.pop("edit_wbs_id", None)
            st.rerun()
    with btn_col[2]:
        if st.button("📊", key=f"rprog_{wid}", use_container_width=True, help="진척률 롤업"):
            new_p = db.apply_rollup_progress(wid)
            st.success(f"진척률 → {new_p}%")
            st.rerun()
    with btn_col[3]:
        if st.button("🗑️", key=f"dwbs_{wid}", use_container_width=True,
                     help="삭제 (하위 WBS 및 연결 Action 포함)"):
            db.delete_wbs(wid)
            st.rerun()
    with btn_col[4]:
        if node.get("content"):
            st.caption(f"📝 {node['content']}")
        if astats["total"] > 0:
            cols_a = st.columns(4)
            cols_a[0].metric("총 Action", astats["total"])
            cols_a[1].metric("✅ 완료", astats["done"])
            cols_a[2].metric("🔄 진행", astats["in_progress"])
            cols_a[3].metric("🚫 블록", astats["blocked"])

    # Main WBS와 다음 Main WBS 사이 구분선
    if depth == 1 and not children:
        st.markdown("---")

    # ── Sub WBS 재귀 렌더링 ────────────────────────
    if children:
        st.markdown(
            f'<div style="margin-left:{depth*18}px;border-left:2px solid #334155;padding-left:4px">',
            unsafe_allow_html=True,
        )
        for child in children:
            _render_wbs_node(child, depth + 1, cmap)
        st.markdown("</div>", unsafe_allow_html=True)
        if depth == 1:
            st.markdown("---")


def render_action_tab():
    st.subheader("✅ Action Items")

    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([2, 2, 2, 2, 1])
    with col_f1:
        atypes = ["전체"] + db.get_action_type_names()
        f_type = st.selectbox("유형", atypes, key="act_f_type")
    with col_f2:
        f_status = st.selectbox("상태", ["전체"] + STATUS_OPTIONS, key="act_f_status")
    with col_f3:
        # WBS 필터
        all_wbs  = db.get_all_wbs_flat()
        wbs_fopts = ["전체", "📌 WBS 미배정"] + [
            f"[{r.get('wbs_code','')}] {r['wbs_type']} (ID:{r['id']})"
            for r in all_wbs
        ]
        f_wbs = st.selectbox("WBS 필터", wbs_fopts, key="act_f_wbs")
    with col_f4:
        f_search = st.text_input("🔍 검색", placeholder="내용 검색...", key="act_f_search")
    with col_f5:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Action 추가", use_container_width=True, type="primary"):
            st.session_state["show_act_form"] = not st.session_state.get("show_act_form", False)
            st.session_state.pop("edit_act_id", None)

    if st.session_state.get("show_act_form"):
        with st.container(border=True):
            st.markdown("#### ➕ 새 Action Item")
            _action_form(mode="add")

    if st.session_state.get("edit_act_id"):
        with st.container(border=True):
            st.markdown(f"#### ✏️ Action 수정 (ID:{st.session_state['edit_act_id']})")
            _action_form(mode="edit", item_id=st.session_state["edit_act_id"])

    filters = {}
    if f_type != "전체":   filters["action_type"] = f_type
    if f_status != "전체": filters["status"]      = f_status
    df = db.get_action_items(filters)
    if f_search:
        df = df[df["content"].str.contains(f_search, case=False, na=False)]

    # WBS 필터 적용
    if f_wbs == "📌 WBS 미배정":
        df = df[df["wbs_id"].isna()]
    elif f_wbs != "전체":
        try:
            fwid = int(f_wbs.split("ID:")[1].rstrip(")"))
            df = df[df["wbs_id"] == fwid]
        except Exception:
            pass

    # ── WBS 미배정 Action 별도 섹션 표시 (전체 뷰일 때만)
    if f_wbs == "전체":
        unassigned = df[df["wbs_id"].isna()]
        assigned   = df[df["wbs_id"].notna()]
        if not unassigned.empty:
            st.markdown(
                '<div style="background:#1c1917;border:1px solid #78716c;border-radius:8px;'
                'padding:8px 14px;margin:8px 0;font-size:.85rem;color:#a8a29e">'
                '📌 <b>WBS 미배정 Action</b> — 특정 WBS에 속하지 않는 독립 액션'
                f'&nbsp;&nbsp;<b style="color:#f5f5f4">{len(unassigned)}건</b></div>',
                unsafe_allow_html=True,
            )
            for _, row in unassigned.iterrows():
                _render_action_card(row)
            if not assigned.empty:
                st.markdown("---")
                st.caption(f"🔗 WBS 귀속 Action Items — {len(assigned)}건")
        df = assigned if not unassigned.empty else df

    st.caption(f"총 **{len(df)}** 건")
    if df.empty and f_wbs != "전체":
        st.info("해당 조건의 Action Item이 없습니다.")
        return

    for _, row in df.iterrows():
        _render_action_card(row)




def _action_form(mode="add", item_id=None):
    p   = db.get_action_by_id(item_id) if mode == "edit" and item_id else {}
    pfx = f"act_{mode}_{item_id or 'new'}"

    # ── ① WBS 귀속 (최상단 — 가장 중요한 설정) ──
    st.markdown(
        '<div style="background:#1e3a5f;border:1px solid #2563eb;border-radius:8px;'
        'padding:8px 14px;margin-bottom:10px;font-size:.85rem;color:#93c5fd">'
        '📌 <b>WBS 귀속 설정</b> — 이 Action Item이 속할 WBS 항목을 먼저 선택하세요'
        '</div>',
        unsafe_allow_html=True,
    )
    wbs_df  = db.get_all_wbs_flat()
    wbs_opts = ["⬜ 귀속 WBS 없음 (독립 Action)"] + [
        f"{'  ' * (int(r.get('wbs_level') or 1)-1)}[{r.get('wbs_code','')}] {r['wbs_type']} (ID:{r['id']})"
        for r in wbs_df
    ]
    cur = "⬜ 귀속 WBS 없음 (독립 Action)"
    if p.get("wbs_id"):
        matched = [o for o in wbs_opts if f"ID:{p['wbs_id']})" in o]
        if matched: cur = matched[0]
    wbs_sel = st.selectbox(
        "🔗 귀속 WBS *", wbs_opts,
        index=wbs_opts.index(cur) if cur in wbs_opts else 0,
        key=f"{pfx}_wbs",
        help="선택 안 하면 독립 Action으로 분류됩니다. WBS 미배정 항목은 Action Items 탭 상단에서 별도 관리됩니다.",
    )
    # 선택된 WBS 정보 미리보기
    if wbs_sel != "⬜ 귀속 WBS 없음 (독립 Action)":
        try:
            sel_wbs_id = int(wbs_sel.split("ID:")[1].rstrip(")"))
            sel_stats  = db.get_action_stats_for_wbs(sel_wbs_id)
            st.caption(
                f"📊 해당 WBS 현재 Action: 총 {sel_stats['total']}건 "
                f"| 완료 {sel_stats['done']} | 진행중 {sel_stats['in_progress']} | 블록 {sel_stats['blocked']} "
                f"→ 현재 자동 진척률 {sel_stats['auto_progress']}%"
            )
        except Exception:
            pass

    st.divider()

    # ── ② 유형 & 상태 ──
    atypes = db.get_action_type_names()
    col1, col2 = st.columns(2)
    with col1:
        def_t = atypes.index(p["action_type"]) if p.get("action_type") in atypes else 0
        atype = st.selectbox("Action 유형 *", atypes, index=def_t, key=f"{pfx}_type")
    with col2:
        def_s = STATUS_OPTIONS.index(p.get("status","todo")) if p.get("status") in STATUS_OPTIONS else 0
        status = st.selectbox("상태", STATUS_OPTIONS, index=def_s, key=f"{pfx}_st")

    if status == "done":
        st.success("✅ 완료 저장 시 귀속 WBS의 자동 진척률이 변경됩니다 (WBS 카드 📊 자동계산 버튼으로 반영)")

    content = st.text_area("내용 *", value=p.get("content",""), height=80, key=f"{pfx}_content")

    c1,c2,c3 = st.columns(3)
    with c1: sd = st.date_input("시작일",     value=parse_date_safe(p.get("start_date")), key=f"{pfx}_sd")
    with c2: dd = st.date_input("종료예정일", value=parse_date_safe(p.get("due_date")),   key=f"{pfx}_dd")
    with c3: ed = st.date_input("종료일",     value=parse_date_safe(p.get("end_date")),   key=f"{pfx}_ed")

    notes = st.text_area("기타", value=p.get("notes",""), height=55, key=f"{pfx}_notes")

    b1, b2 = st.columns([1, 5])
    with b1:
        if st.button("💾 저장", key=f"{pfx}_save", type="primary"):
            wbs_id = None
            if wbs_sel != "연결 없음":
                try: wbs_id = int(wbs_sel.split("ID:")[1].rstrip(")"))
                except Exception: pass
            data = dict(action_type=atype,
                        registered_date=p.get("registered_date", date.today().isoformat()),
                        content=content, start_date=d2s(sd), due_date=d2s(dd),
                        end_date=d2s(ed), status=status, notes=notes, wbs_id=wbs_id)
            if mode == "add":
                db.insert_action(data); st.session_state.pop("show_act_form", None)
            else:
                db.update_action(item_id, data); st.session_state.pop("edit_act_id", None)
            st.success("✅ 저장되었습니다!"); st.rerun()
    with b2:
        if st.button("취소", key=f"{pfx}_cancel"):
            st.session_state.pop("show_act_form", None)
            st.session_state.pop("edit_act_id", None); st.rerun()


def _render_action_card(row):
    dl = deadline_chip(row.get("due_date",""))
    preview = (row.get("content","") or "")[:50]
    with st.expander(
        f"{STATUS_EMOJI.get(row['status'],'⬜')} [{row['action_type']}] {preview}  |  {row['registered_date']}"
    ):
        ci, ca = st.columns([4, 1])
        with ci:
            st.markdown(f"**내용:** {row.get('content') or '-'}")
            c1,c2,c3,c4 = st.columns(4)
            c1.markdown(f"**시작일**\n{row['start_date'] or '-'}")
            c2.markdown(f"**종료예정**\n{row['due_date'] or '-'}")
            c3.markdown(f"**종료일**\n{row['end_date'] or '-'}")
            c4.markdown(f"**상태**")
            st.markdown(f"{badge(row['status'])} &nbsp; {dl}", unsafe_allow_html=True)
            if row.get("linked_wbs"):
                st.caption(f"🔗 WBS: [{row.get('linked_wbs_cat','')}] {row['linked_wbs']}")
            if row.get("notes"):
                st.caption(f"📝 {row['notes']}")
        with ca:
            if st.button("✏️", key=f"eact_{row['id']}", use_container_width=True, help="수정"):
                st.session_state["edit_act_id"] = int(row["id"])
                st.session_state.pop("show_act_form", None); st.rerun()
            if st.button("🗑️", key=f"dact_{row['id']}", use_container_width=True, help="삭제"):
                db.delete_action(int(row["id"])); st.rerun()


# ── 노트 작성 마법사 (Step-by-step Dialog) ──────
def _wizard_progress_html(step: int, total: int, label: str, hint: str) -> str:
    pct = int(step / total * 100)
    dots = "".join(
        f'<span style="width:10px;height:10px;border-radius:50%;display:inline-block;margin:0 3px;'
        f'background:{"#7c3aed" if i <= step else "#334155"}"></span>'
        for i in range(total)
    )
    return f"""
    <div style="text-align:center;padding:20px 0 14px">
      <div style="margin-bottom:10px">{dots}</div>
      <div style="font-size:.78rem;color:#64748b;letter-spacing:.05em">STEP {step+1} / {total}</div>
      <div style="font-size:1.55rem;font-weight:700;color:#f1f5f9;margin:8px 0 4px">{label}</div>
      <div style="font-size:.85rem;color:#94a3b8">{hint}</div>
    </div>
    <div style="background:#1e293b;border-radius:4px;height:4px;margin-bottom:16px">
      <div style="background:linear-gradient(90deg,#7c3aed,#4f46e5);height:4px;
                  border-radius:4px;width:{pct}%;transition:width .3s"></div>
    </div>
    """


def _wizard_prev_vals_html(vals: dict, labels: dict) -> str:
    if not vals:
        return ""
    items = "".join(
        f'<span style="background:#0f172a;border:1px solid #334155;border-radius:6px;'
        f'padding:3px 10px;font-size:.75rem;color:#94a3b8;margin:2px">'
        f'<b style="color:#7c3aed">{labels.get(k,k)}</b> {v}</span>'
        for k, v in vals.items() if v
    )
    return f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px">{items}</div>'


@st.dialog("📋 WBS 노트 작성 마법사", width="large")
def _wbs_wizard_dialog():
    LABELS = {
        "wbs_code":    "WBS 코드",
        "wbs_category":"카테고리",
        "wbs_type":    "항목 유형",
        "owner":       "담당자",
        "start_date":  "시작일",
        "due_date":    "종료예정일",
        "status":      "일정 상태",
        "content":     "상세 내용",
    }
    cats  = db.get_wbs_categories()
    STEPS = [
        {"key":"wbs_code",    "label":"WBS 코드",   "type":"text",       "hint":"예: 1.0 / 1.1 / 2.1.1  (Enter로 건너뜀)"},
        {"key":"wbs_category","label":"카테고리",   "type":"select",     "hint":"해당 WBS의 카테고리를 선택하세요",     "opts": cats},
        {"key":"wbs_type",    "label":"항목 유형",  "type":"select_dep", "hint":"카테고리에 맞는 유형을 선택하세요"},
        {"key":"owner",       "label":"담당자",     "type":"text",       "hint":"담당자 이름 (Enter로 건너뜀)"},
        {"key":"start_date",  "label":"시작일",     "type":"date",       "hint":"시작일을 선택하세요 (Enter로 건너뜀)"},
        {"key":"due_date",    "label":"종료예정일", "type":"date",       "hint":"종료 예정일을 선택하세요"},
        {"key":"status",      "label":"일정 상태",  "type":"wbs_status", "hint":"현재 일정 상태를 선택하세요"},
        {"key":"content",     "label":"상세 내용",  "type":"textarea",   "hint":"이 WBS 항목의 수행 내용을 간략히 기술하세요 (Enter로 건너뜀)"},
    ]
    TOTAL = len(STEPS)

    if "wiz_wbs_step" not in st.session_state:
        st.session_state["wiz_wbs_step"] = 0
        st.session_state["wiz_wbs_vals"] = {}

    step = st.session_state["wiz_wbs_step"]
    vals = st.session_state["wiz_wbs_vals"]

    # ── 완료 화면 ──────────────────────────────────
    if step >= TOTAL:
        st.markdown('<div style="text-align:center;font-size:1.4rem;padding:10px 0">✅ 입력 완료!</div>', unsafe_allow_html=True)
        cat  = vals.get("wbs_category","")
        sd   = vals.get("start_date","")
        dd   = vals.get("due_date","")
        md_content = f"""\
---
type: wbs
wbs_code: "{vals.get('wbs_code','')}"
wbs_category: "{cat}"
wbs_type: "{vals.get('wbs_type','')}"
status: {vals.get('status','scheduled')}
start_date: "{sd}"
due_date: "{dd}"
end_date: ""
progress: 0
owner: "{vals.get('owner','')}"
notes: ""
---

# {vals.get('wbs_type','WBS 항목')}

## 개요
{vals.get('content','<!-- 내용을 입력하세요 -->')}

## 산출물
- [ ] 산출물 1
- [ ] 산출물 2

## 이슈 / 리스크

## 참고 자료
"""
        st.code(md_content, language="yaml")
        fname = f"WBS_{vals.get('wbs_code','').replace('.','_') or 'new'}.md"

        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            st.download_button("⬇️ .md 다운로드", data=md_content.encode("utf-8"),
                               file_name=fname, mime="text/markdown",
                               use_container_width=True)
        with bc2:
            if st.button("💾 DB에 WBS 저장", use_container_width=True, type="primary"):
                par_id = None
                wbs_code = vals.get("wbs_code", "")
                if wbs_code and "." in wbs_code:
                    parent_code = ".".join(wbs_code.split(".")[:-1])
                    all_w = db.get_all_wbs_flat()
                    match = [w for w in all_w if w.get("wbs_code") == parent_code]
                    if match:
                        par_id = match[0]["id"]
                lvl = (par_id and (db.get_wbs_by_id(par_id) or {}).get("wbs_level", 1) or 0) + 1
                new_id = db.insert_wbs(dict(
                    wbs_category=vals.get("wbs_category", ""),
                    wbs_type=vals.get("wbs_type", ""),
                    content=vals.get("content", ""),
                    start_date=vals.get("start_date", ""),
                    due_date=vals.get("due_date", ""),
                    status=vals.get("status", "scheduled"),
                    progress=0,
                    owner=vals.get("owner", ""),
                    wbs_code=wbs_code,
                    wbs_level=lvl,
                    parent_wbs_id=par_id,
                ))
                st.success(f"✅ WBS 저장 완료 (ID: {new_id})")
        with bc3:
            if st.button("🔄 다시 작성", use_container_width=True):
                st.session_state["wiz_wbs_step"] = 0
                st.session_state["wiz_wbs_vals"] = {}
                st.rerun()
        if st.button("✖ 닫기", use_container_width=True):
            st.session_state["open_wbs_wizard"] = False
            st.session_state["wiz_wbs_step"] = 0
            st.session_state["wiz_wbs_vals"] = {}
            st.rerun()
        return

    cur = STEPS[step]
    st.markdown(_wizard_progress_html(step, TOTAL, cur["label"], cur["hint"]), unsafe_allow_html=True)
    st.markdown(_wizard_prev_vals_html(vals, LABELS), unsafe_allow_html=True)

    with st.form(key=f"wiz_wbs_{step}", clear_on_submit=True):
        val = None
        if cur["type"] == "text":
            val = st.text_input("", placeholder=cur["hint"], label_visibility="collapsed",
                                key=f"wiz_wbs_inp_{step}")
        elif cur["type"] == "textarea":
            val = st.text_area("", placeholder=cur["hint"], label_visibility="collapsed",
                               height=90, key=f"wiz_wbs_inp_{step}")
        elif cur["type"] == "select":
            val = st.selectbox("", cur.get("opts", []), label_visibility="collapsed",
                               key=f"wiz_wbs_inp_{step}")
        elif cur["type"] == "select_dep":
            cat  = vals.get("wbs_category", cats[0] if cats else "")
            opts = db.get_wbs_types_by_category(cat)
            val  = st.selectbox("", opts, label_visibility="collapsed", key=f"wiz_wbs_inp_{step}")
        elif cur["type"] == "wbs_status":
            val = st.selectbox("", WBS_STATUS_OPTIONS,
                               format_func=lambda x: f"{WBS_STATUS_EMOJI[x]} {WBS_STATUS_LABEL[x]}",
                               label_visibility="collapsed", key=f"wiz_wbs_inp_{step}")
        elif cur["type"] == "date":
            val = st.date_input("", value=None, label_visibility="collapsed", key=f"wiz_wbs_inp_{step}")

        c1, c2 = st.columns(2)
        with c1:
            back = st.form_submit_button("← 이전", use_container_width=True, disabled=(step == 0))
        with c2:
            nxt = st.form_submit_button(
                "다음 →  (Enter)" if step < TOTAL - 1 else "✅ 완료  (Enter)",
                use_container_width=True, type="primary"
            )

    if nxt:
        v = "" if val is None else (val.isoformat() if hasattr(val, "isoformat") else str(val).strip())
        if v:
            vals[cur["key"]] = v
        st.session_state["wiz_wbs_vals"] = vals
        st.session_state["wiz_wbs_step"] = step + 1
        st.rerun()
    if back and step > 0:
        st.session_state["wiz_wbs_step"] = step - 1
        st.rerun()


@st.dialog("✅ Action Item 노트 작성 마법사", width="large")
def _action_wizard_dialog():
    LABELS = {
        "action_type": "액션 유형",
        "wbs_id":      "귀속 WBS",
        "owner":       "담당자",
        "start_date":  "시작일",
        "due_date":    "종료예정일",
        "status":      "상태",
        "content":     "할 일 내용",
    }

    # WBS 옵션: id → label, id → 인덴트 레이블
    all_wbs = db.get_all_wbs_flat()
    # ("표시 레이블", wbs_id or None) 리스트
    WBS_CHOICES = [("⬜ 없음 — 독립 Action (WBS 미귀속)", None)]
    for r in all_wbs:
        code  = r.get("wbs_code", "") or ""
        lvl   = int(r.get("wbs_level") or 1)
        indent = "　" * (lvl - 1)  # 전각 공백으로 들여쓰기
        kind  = "📁" if lvl == 1 else "└ 📄"
        label = f"{indent}{kind} [{code}] {r['wbs_type']}" if code else f"{indent}{kind} {r['wbs_type']}"
        WBS_CHOICES.append((label, r["id"]))

    WBS_LABELS = [c[0] for c in WBS_CHOICES]
    WBS_ID_MAP  = {c[0]: c[1] for c in WBS_CHOICES}

    STEPS = [
        {"key": "action_type", "label": "액션 유형",  "type": "select",
         "hint": "수행할 작업의 유형을 선택하세요", "opts": db.get_action_type_names()},
        {"key": "wbs_id",      "label": "귀속 WBS",   "type": "wbs_pick",
         "hint": "이 Action이 속할 WBS를 선택하세요 (없으면 첫 번째 항목 선택 → 독립 Action)"},
        {"key": "owner",       "label": "담당자",     "type": "text",
         "hint": "담당자 이름 (Enter로 건너뜀)"},
        {"key": "start_date",  "label": "시작일",     "type": "date",    "hint": "시작일 선택"},
        {"key": "due_date",    "label": "종료예정일", "type": "date",    "hint": "완료 목표일 선택"},
        {"key": "status",      "label": "현재 상태",  "type": "act_status",
         "hint": "현재 진행 상태를 선택하세요"},
        {"key": "content",     "label": "할 일 내용", "type": "textarea",
         "hint": "수행할 구체적인 내용을 적어주세요 (Enter로 건너뜀)"},
    ]
    TOTAL = len(STEPS)

    if "wiz_act_step" not in st.session_state:
        st.session_state["wiz_act_step"] = 0
        st.session_state["wiz_act_vals"] = {}

    step = st.session_state["wiz_act_step"]
    vals = st.session_state["wiz_act_vals"]

    # ── 완료 화면 ──────────────────────────────────
    if step >= TOTAL:
        st.markdown('<div style="text-align:center;font-size:1.4rem;padding:10px 0">✅ 입력 완료!</div>',
                    unsafe_allow_html=True)
        wbs_id_val = vals.get("wbs_id")   # None or int id
        wbs_label  = vals.get("wbs_id_label", "없음")
        # WBS 코드 역조회 (md 파일용)
        wbs_code_str = ""
        if wbs_id_val:
            matched = [w for w in all_wbs if w["id"] == wbs_id_val]
            if matched:
                wbs_code_str = matched[0].get("wbs_code", "") or ""

        md_content = f"""\
---
type: action_item
action_type: "{vals.get('action_type','')}"
status: {vals.get('status','todo')}
start_date: "{vals.get('start_date','')}"
due_date: "{vals.get('due_date','')}"
end_date: ""
wbs_ref: "{wbs_code_str}"
owner: "{vals.get('owner','')}"
notes: ""
---

# {vals.get('action_type','')} — {vals.get('content','')[:40]}

## 귀속 WBS
{wbs_label}

## 할 일 내용
{vals.get('content','<!-- 내용을 입력하세요 -->')}

## 완료 기준
- [ ] 조건 1
- [ ] 조건 2

## 참고 / 메모

"""
        # WBS 귀속 정보 강조 표시
        wbs_color = "#22c55e" if wbs_id_val else "#64748b"
        st.markdown(
            f'<div style="background:#0f172a;border:1px solid {wbs_color}55;border-left:4px solid {wbs_color};'
            f'border-radius:8px;padding:10px 14px;margin:8px 0;font-size:.85rem">'
            f'🔗 <b style="color:{wbs_color}">귀속 WBS:</b> {wbs_label}</div>',
            unsafe_allow_html=True,
        )
        st.code(md_content, language="yaml")

        import re
        safe  = re.sub(r"[^\w가-힣]", "_", vals.get("content", "action")[:20])
        fname = f"Action_{safe}.md"

        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            st.download_button("⬇️ .md 다운로드", data=md_content.encode("utf-8"),
                               file_name=fname, mime="text/markdown",
                               use_container_width=True)
        with bc2:
            if st.button("💾 DB에 Action 저장", use_container_width=True, type="primary"):
                db.insert_action(dict(
                    action_type=vals.get("action_type", ""),
                    content=vals.get("content", ""),
                    start_date=vals.get("start_date", ""),
                    due_date=vals.get("due_date", ""),
                    status=vals.get("status", "todo"),
                    wbs_id=wbs_id_val,   # None = 독립 Action
                    notes="",
                ))
                st.success(f"✅ Action 저장 완료 → {'독립 Action' if not wbs_id_val else wbs_label}")
        with bc3:
            if st.button("🔄 다시 작성", use_container_width=True):
                st.session_state["wiz_act_step"] = 0
                st.session_state["wiz_act_vals"] = {}
                st.rerun()
        if st.button("✖ 닫기", use_container_width=True):
            st.session_state["open_act_wizard"] = False
            st.session_state["wiz_act_step"] = 0
            st.session_state["wiz_act_vals"] = {}
            st.rerun()
        return

    cur = STEPS[step]
    st.markdown(_wizard_progress_html(step, TOTAL, cur["label"], cur["hint"]), unsafe_allow_html=True)
    # 이전 답변 표시 (wbs_id는 label로 표시)
    disp_vals = {}
    for k, v in vals.items():
        if k == "wbs_id":
            disp_vals["귀속 WBS"] = vals.get("wbs_id_label", str(v))
        elif not k.endswith("_label"):
            disp_vals[LABELS.get(k, k)] = v
    st.markdown(_wizard_prev_vals_html(disp_vals, {}), unsafe_allow_html=True)

    with st.form(key=f"wiz_act_{step}", clear_on_submit=True):
        val = None
        if cur["type"] == "text":
            val = st.text_input("", placeholder=cur["hint"], label_visibility="collapsed",
                                key=f"wiz_act_inp_{step}")
        elif cur["type"] == "textarea":
            val = st.text_area("", placeholder=cur["hint"], label_visibility="collapsed",
                               height=90, key=f"wiz_act_inp_{step}")
        elif cur["type"] == "select":
            val = st.selectbox("", cur.get("opts", []), label_visibility="collapsed",
                               key=f"wiz_act_inp_{step}")
        elif cur["type"] == "wbs_pick":
            # 계층 WBS 선택기
            if not all_wbs:
                st.info("등록된 WBS가 없습니다. WBS 탭에서 먼저 WBS를 생성하세요.")
            val = st.selectbox("", WBS_LABELS, label_visibility="collapsed",
                               key=f"wiz_act_inp_{step}")
        elif cur["type"] == "act_status":
            val = st.selectbox("", STATUS_OPTIONS,
                               format_func=lambda x: f"{STATUS_EMOJI[x]} {STATUS_LABEL[x]}",
                               label_visibility="collapsed", key=f"wiz_act_inp_{step}")
        elif cur["type"] == "date":
            val = st.date_input("", value=None, label_visibility="collapsed",
                                key=f"wiz_act_inp_{step}")

        c1, c2 = st.columns(2)
        with c1:
            back = st.form_submit_button("← 이전", use_container_width=True, disabled=(step == 0))
        with c2:
            nxt = st.form_submit_button(
                "다음 →  (Enter)" if step < TOTAL - 1 else "✅ 완료  (Enter)",
                use_container_width=True, type="primary"
            )

    if nxt:
        if cur["type"] == "wbs_pick":
            # wbs_id(int or None)와 label 모두 저장
            chosen_label = val if val else WBS_LABELS[0]
            chosen_id    = WBS_ID_MAP.get(chosen_label)
            vals["wbs_id"]       = chosen_id
            vals["wbs_id_label"] = chosen_label
        else:
            v = "" if val is None else (val.isoformat() if hasattr(val, "isoformat") else str(val).strip())
            if v:
                vals[cur["key"]] = v
        st.session_state["wiz_act_vals"] = vals
        st.session_state["wiz_act_step"] = step + 1
        st.rerun()
    if back and step > 0:
        st.session_state["wiz_act_step"] = step - 1
        st.rerun()


# ── 노트 업로드 탭 ───────────────────────────────
def _make_wbs_template() -> str:
    """WBS 노트용 Obsidian 템플릿 생성."""
    return """\
---
type: wbs
wbs_code: "1.1"
wbs_category: "To be process 개발"
wbs_type: "process 체계도"
status: scheduled
start_date: ""
due_date: ""
end_date: ""
progress: 0
owner: ""
notes: ""
---

# {{wbs_type}}

## 개요
<!-- 이 WBS 항목의 목적과 범위를 간략히 기술하세요 -->

## 상세 내용
<!-- 수행해야 할 구체적인 업무 내용 -->

## 산출물
- [ ] 산출물 1
- [ ] 산출물 2

## 이슈 / 리스크
<!-- 진행 중 발견된 이슈나 리스크 기록 -->

## 참고 자료
<!-- 관련 문서, URL, SAP Note 등 -->
"""


def _make_action_template() -> str:
    """Action Item 노트용 Obsidian 템플릿 생성."""
    return """\
---
type: action_item
action_type: "문서작성"
status: todo
start_date: ""
due_date: ""
end_date: ""
wbs_ref: ""
notes: ""
---

# {{action_type}} — {{title}}

## 할 일 내용
<!-- 수행해야 할 구체적인 내용을 기술하세요 -->

## 완료 기준
- [ ] 조건 1
- [ ] 조건 2

## 참고 / 메모
<!-- 관련 정보, 링크, SAP 트랜잭션 코드 등 -->
"""


def _make_meeting_template() -> str:
    """회의록 겸 Action Item 추출용 Obsidian 템플릿."""
    return """\
---
type: action_item
action_type: "미팅(출장)"
status: todo
start_date: ""
due_date: ""
end_date: ""
wbs_ref: ""
notes: ""
---

# 회의록 — {{date}} {{title}}

## 참석자
- 

## 안건
1. 

## 논의 내용
<!-- 핵심 결정 사항 및 논의 내용 -->

## Action Items
<!-- 아래 항목은 LLM Agent가 자동 추출합니다 -->
- [ ] [@담당자] 내용 (기한: )
- [ ] [@담당자] 내용 (기한: )

## 다음 회의 예정
- 일시:
- 안건:
"""


def render_upload_tab():
    from parser import parse_multiple_notes

    # ── 다이얼로그 플래그 기반 호출 (st.rerun() 후에도 유지) ──
    if st.session_state.get("open_wbs_wizard"):
        _wbs_wizard_dialog()
    if st.session_state.get("open_act_wizard"):
        _action_wizard_dialog()

    st.subheader("📋 Obsidian 연동")

    # ── 템플릿 다운로드 섹션 ────────────────────────
    st.markdown("### 📥 Obsidian 템플릿 다운로드")
    st.markdown(
        "아래 템플릿을 Obsidian **Templates 폴더**에 저장 후 사용하세요. "
        "`type` frontmatter가 파싱 키입니다."
    )

    TEMPLATES = [
        {
            "label": "📋 WBS 항목 템플릿",
            "filename": "WBS_Template.md",
            "content": _make_wbs_template(),
            "desc": "`type: wbs` — WBS 계층 항목 작성용. wbs_code, wbs_category, status 등 포함.",
            "color": "#7c3aed",
        },
        {
            "label": "✅ Action Item 템플릿",
            "filename": "ActionItem_Template.md",
            "content": _make_action_template(),
            "desc": "`type: action_item` — 개별 Task/Action 작성용. WBS와 연결 가능.",
            "color": "#0891b2",
        },
        {
            "label": "📝 회의록 템플릿",
            "filename": "Meeting_Template.md",
            "content": _make_meeting_template(),
            "desc": "`type: action_item` — 회의록 겸 Action Item 추출용. LLM Agent가 Action 자동 추출.",
            "color": "#059669",
        },
    ]

    cols = st.columns(3)
    WIZARD_LABELS = ["📋 WBS 마법사로 작성", "✅ Action 마법사로 작성", None]
    for col, tpl, wiz_label in zip(cols, TEMPLATES, WIZARD_LABELS):
        with col:
            st.markdown(
                f'<div style="background:#1e293b;border:1px solid {tpl["color"]}55;'
                f'border-left:4px solid {tpl["color"]};border-radius:8px;padding:12px 14px;margin-bottom:8px">'
                f'<div style="font-weight:600;color:#f1f5f9;margin-bottom:6px">{tpl["label"]}</div>'
                f'<div style="font-size:.78rem;color:#94a3b8">{tpl["desc"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                label=f"⬇️ 빈 템플릿 다운로드",
                data=tpl["content"].encode("utf-8"),
                file_name=tpl["filename"],
                mime="text/markdown",
                use_container_width=True,
                key=f"dl_{tpl['filename']}",
            )
            if wiz_label:
                if st.button(wiz_label, use_container_width=True, key=f"wiz_btn_{tpl['filename']}",
                             type="primary"):
                    if "WBS" in wiz_label:
                        st.session_state["open_wbs_wizard"] = True
                        st.session_state["wiz_wbs_step"] = 0
                        st.session_state["wiz_wbs_vals"] = {}
                    else:
                        st.session_state["open_act_wizard"] = True
                        st.session_state["wiz_act_step"] = 0
                        st.session_state["wiz_act_vals"] = {}


    # ── YAML 스키마 참조표 ──────────────────────────
    with st.expander("📖 YAML Frontmatter 스키마 참조", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**WBS 노트 (`type: wbs`)**")
            st.code("""\
---
type: wbs              # 필수
wbs_code: "1.1"        # WBS 번호 (1.0, 1.1, 2.1.1 등)
wbs_category: "..."    # 카테고리
wbs_type: "..."        # 항목 유형명
status: scheduled      # scheduled | in_progress | done | cancelled
start_date: "2025-06-01"
due_date:   "2025-06-30"
end_date:   ""
progress: 0            # 0~100 (수동 진척률)
owner: "홍길동"
notes: ""
---""", language="yaml")
        with c2:
            st.markdown("**Action Item 노트 (`type: action_item`)**")
            st.code("""\
---
type: action_item      # 필수
action_type: "문서작성" # 유형 (마스터 데이터 기준)
status: todo           # todo | in_progress | done | blocked
start_date: "2025-06-01"
due_date:   "2025-06-15"
end_date:   ""
wbs_ref: "1.1"         # 귀속 WBS 코드 (선택)
notes: ""
---""", language="yaml")

        st.info(
            "💡 **wbs_ref** 필드에 WBS 코드(예: `1.1`)를 입력하면 업로드 시 자동으로 해당 WBS에 귀속됩니다. "
            "WBS 코드가 없거나 매칭 실패 시 '독립 Action'으로 분류됩니다."
        )

    st.divider()

    # ── 파일 업로드 섹션 ────────────────────────────
    st.markdown("### 📤 노트 업로드 → DB 저장")
    st.markdown(
        "작성한 `.md` 파일을 업로드하면 자동으로 파싱하여 WBS / Action Item으로 저장합니다."
    )

    uploaded = st.file_uploader("마크다운 파일 선택 (복수 가능)", type=["md"], accept_multiple_files=True)
    if not uploaded:
        return

    file_contents = [(f.name, f.read().decode("utf-8", errors="replace")) for f in uploaded]

    results = parse_multiple_notes(file_contents)

    st.markdown(f"### 파싱 결과 ({len(results)}개 파일)")
    for r in results:
        icon = "✅" if r["success"] else "⚠️"
        with st.expander(f"{icon} {r['filename']}  →  {r['type'] or '인식불가'}"):
            if r["success"]:
                st.json({k:v for k,v in r["data"].items() if k != "source_file"})
            else:
                st.warning(str(r["data"]))

    valid = [r for r in results if r["success"]]
    invalid = len(results) - len(valid)
    if invalid:
        st.warning(f"{invalid}개 파일은 인식되지 않아 제외됩니다.")

    if valid:
        col1, col2 = st.columns([2, 5])
        with col1:
            if st.button(f"⬇️ {len(valid)}개 항목 가져오기", type="primary"):
                for r in valid:
                    if r["type"] == "wbs": db.insert_wbs(r["data"])
                    elif r["type"] == "action_item": db.insert_action(r["data"])
                st.success(f"🎉 {len(valid)}개 항목 저장 완료!")
                st.balloons(); st.rerun()

    # AI 분석 (자유 노트 → Action Item 추출)
    st.divider()
    st.markdown("#### 🤖 AI 자유 노트 분석 (Action Item 자동 추출)")
    free_note = st.text_area("자유 형식 노트 붙여넣기", height=150, key="free_note_input",
                              placeholder="오늘 회의에서 나온 내용, 현장 메모 등...")
    if st.button("🔍 AI로 Action Item 추출") and free_note.strip():
        api_key  = db.get_llm_setting("api_key")
        base_url = db.get_llm_setting("base_url")
        model    = db.get_llm_setting("model", "gpt-4o-mini")
        with st.spinner("AI 분석 중..."):
            items = ag.extract_action_items_from_note(free_note, api_key, base_url, model)
        if items:
            st.success(f"**{len(items)}개** Action Item 추출됨")
            for i, item in enumerate(items):
                with st.expander(f"[{item.get('action_type','')}] {str(item.get('content',''))[:50]}"):
                    st.json(item)
            if st.button("📥 전체 저장"):
                for item in items:
                    db.insert_action({**item, "registered_date": date.today().isoformat()})
                st.success("저장 완료!"); st.rerun()
        else:
            st.warning("추출된 항목이 없거나 LLM 설정이 필요합니다. ⚙️ 시스템 관리 탭에서 API 키를 입력하세요.")


# ── Gantt / 대시보드 탭 ──────────────────────────
def render_gantt_tab():
    st.subheader("📊 Gantt & 대시보드")
    stats = db.get_summary_stats()

    t1, t2 = st.tabs(["📈 차트 대시보드", "🗂️ Gantt 차트"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(ch.make_status_donut(stats, "wbs"), use_container_width=True)
        with c2:
            st.plotly_chart(ch.make_status_donut(stats, "act"), use_container_width=True)

        wbs_df = db.get_wbs_items()
        if not wbs_df.empty:
            st.plotly_chart(ch.make_progress_bar_chart(wbs_df), use_container_width=True)
            st.plotly_chart(ch.make_category_timeline(wbs_df), use_container_width=True)

    with t2:
        view = st.radio("보기", ["WBS", "Action Items"], horizontal=True, key="gantt_view")
        if view == "WBS":
            gdf = db.get_gantt_data()
            st.plotly_chart(ch.make_gantt(gdf, "WBS Gantt Chart"), use_container_width=True)
            if gdf.empty:
                st.info("시작일 / 종료예정일이 입력된 WBS 항목이 없습니다.")
        else:
            gdf = db.get_action_gantt_data()
            st.plotly_chart(ch.make_gantt(gdf, "Action Items Gantt"), use_container_width=True)
            if gdf.empty:
                st.info("시작일 / 종료예정일이 입력된 Action Item이 없습니다.")


# ── AI 에이전트 탭 ───────────────────────────────
def render_agent_tab():
    st.subheader("🤖 AI 프로젝트 에이전트")

    api_key  = db.get_llm_setting("api_key")
    base_url = db.get_llm_setting("base_url")
    model    = db.get_llm_setting("model", "gpt-4o-mini")

    if not api_key and not base_url:
        st.warning("⚠️ LLM 미설정 — ⚙️ 시스템/데이터 관리 탭 > LLM 설정에서 API 키 또는 로컬 LLM URL을 입력하세요.")

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("📋 현황 분석 요청", use_container_width=True, type="primary"):
            st.session_state.setdefault("chat_history", [])
            st.session_state["chat_history"].append({"role":"user","content":"현재 프로젝트 전체 현황을 분석하고 주요 위험요소와 권고사항을 알려줘."})
            with st.spinner("AI 분석 중..."):
                reply = ag.chat(st.session_state["chat_history"], api_key, base_url, model)
            st.session_state["chat_history"].append({"role":"assistant","content":reply})
            st.rerun()
    with col_btn2:
        if st.button("⚠️ 마감 임박 알림", use_container_width=True):
            st.session_state.setdefault("chat_history", [])
            st.session_state["chat_history"].append({"role":"user","content":"마감이 임박하거나 초과된 항목들의 우선순위 처리 전략을 제안해줘."})
            with st.spinner("AI 분석 중..."):
                reply = ag.chat(st.session_state["chat_history"], api_key, base_url, model)
            st.session_state["chat_history"].append({"role":"assistant","content":reply})
            st.rerun()
    with col_btn3:
        if st.button("📝 전략 보고서 생성", use_container_width=True):
            with st.spinner("보고서 생성 중..."):
                report = ag.generate_strategy(api_key, base_url, model)
            st.session_state.setdefault("chat_history", [])
            st.session_state["chat_history"].append({"role":"assistant","content":report})
            st.rerun()

    st.divider()

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # 채팅 히스토리 표시
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

    # 입력창
    user_input = st.chat_input("프로젝트 관련 질문을 입력하세요... (ERP, SAP, RAP, WBS 등)")
    if user_input:
        st.session_state["chat_history"].append({"role":"user","content":user_input})
        with st.spinner("AI 응답 중..."):
            reply = ag.chat(st.session_state["chat_history"], api_key, base_url, model)
        st.session_state["chat_history"].append({"role":"assistant","content":reply})
        st.rerun()

    if st.session_state["chat_history"]:
        if st.button("🗑️ 대화 초기화", key="clear_chat"):
            st.session_state["chat_history"] = []; st.rerun()


# ── 시스템/데이터 관리 탭 ────────────────────────
def render_admin_tab():
    st.subheader("⚙️ 시스템/데이터 관리")
    sub1, sub2, sub3 = st.tabs(["📂 WBS 항목 유형", "🏷️ Action Item 유형", "🔑 LLM 설정"])

    # WBS 유형
    with sub1:
        st.markdown("#### WBS 항목 유형 등록/삭제")
        with st.form("add_wbs_type_form", clear_on_submit=True):
            existing_cats = db.get_wbs_categories()
            c1, c2 = st.columns(2)
            with c1:
                cat_sel = st.selectbox("카테고리", ["+ 신규 카테고리"] + existing_cats)
                new_cat = st.text_input("신규 카테고리명")
            with c2:
                new_type = st.text_input("새 항목 유형명 *")
            if st.form_submit_button("➕ 추가"):
                cat = new_cat.strip() if cat_sel == "+ 신규 카테고리" else cat_sel
                if cat and new_type.strip():
                    ok = db.add_wbs_type(cat, new_type.strip())
                    st.success(f"추가 완료!") if ok else st.warning("이미 존재합니다.")
                    if ok: st.rerun()
                else:
                    st.warning("카테고리와 항목명을 모두 입력하세요.")
        st.divider()
        wdf = db.get_all_wbs_types()
        if wdf.empty:
            st.info("등록된 항목이 없습니다.")
        else:
            for cat in wdf["category"].unique():
                st.markdown(f"**{cat}**")
                for _, row in wdf[wdf["category"] == cat].iterrows():
                    c1, c2 = st.columns([8,1])
                    c1.markdown(f"&nbsp;&nbsp;• {row['type_name']}", unsafe_allow_html=True)
                    if c2.button("🗑️", key=f"dwt_{row['id']}", help="삭제"):
                        db.delete_wbs_type(int(row["id"])); st.rerun()

    # Action 유형
    with sub2:
        st.markdown("#### Action Item 유형 등록/삭제")
        with st.form("add_action_type_form", clear_on_submit=True):
            new_at = st.text_input("새 Action 유형명 *")
            if st.form_submit_button("➕ 추가"):
                if new_at.strip():
                    ok = db.add_action_type(new_at.strip())
                    st.success("추가 완료!") if ok else st.warning("이미 존재합니다.")
                    if ok: st.rerun()
                else:
                    st.warning("유형명을 입력하세요.")
        st.divider()
        adf = db.get_all_action_types()
        if adf.empty:
            st.info("등록된 항목이 없습니다.")
        else:
            for _, row in adf.iterrows():
                c1, c2 = st.columns([8, 1])
                c1.markdown(f"• {row['type_name']}")
                if c2.button("🗑️", key=f"dat_{row['id']}", help="삭제"):
                    db.delete_action_type(int(row["id"])); st.rerun()

    # LLM 설정
    with sub3:
        st.markdown("#### LLM 연결 설정")
        st.markdown("""
        **지원 모드:**
        - **OpenAI**: API Key 입력, Base URL 비워두기
        - **로컬 Ollama**: API Key 비워두기, Base URL = `http://localhost:11434/v1`
        - **기타 OpenAI 호환 API**: Base URL 직접 입력
        """)
        with st.form("llm_settings_form"):
            api_key  = st.text_input("API Key", value=db.get_llm_setting("api_key"),
                                     type="password", placeholder="sk-...")
            base_url = st.text_input("Base URL (로컬 LLM용)", value=db.get_llm_setting("base_url"),
                                     placeholder="http://localhost:11434/v1")
            model    = st.text_input("모델명", value=db.get_llm_setting("model","gpt-4o-mini"),
                                     placeholder="gpt-4o-mini / llama3 / etc.")
            if st.form_submit_button("💾 설정 저장", type="primary"):
                db.set_llm_setting("api_key",  api_key.strip())
                db.set_llm_setting("base_url", base_url.strip())
                db.set_llm_setting("model",    model.strip() or "gpt-4o-mini")
                st.success("✅ LLM 설정 저장 완료!")


# ── 음성 메모 탭 ─────────────────────────────────
def render_voice_tab():
    import voice_processor as vp

    st.subheader("🎙️ 음성 메모 → WBS / Action Item 변환")
    st.markdown(
        "현장 미팅·출장 음성 파일을 업로드하면 **자동 텍스트 변환 → AI 분석 → WBS/Action 매칭**까지 처리합니다."
    )

    # ── 환경 체크 배너 ─────────────────────────────
    has_whisper = vp.HAS_WHISPER
    has_ffmpeg  = vp.HAS_FFMPEG
    if not has_whisper or not has_ffmpeg:
        missing = []
        if not has_whisper: missing.append("`pip install faster-whisper`")
        if not has_ffmpeg:  missing.append("`pip install ffmpeg-python` + `brew install ffmpeg`")
        st.error("⚠️ 필수 패키지 미설치: " + " | ".join(missing))
        st.stop()

    api_key  = db.get_llm_setting("api_key")
    base_url = db.get_llm_setting("base_url")
    model    = db.get_llm_setting("model", "gpt-4o-mini")

    # ── Step 1: 파일 업로드 ─────────────────────────
    st.markdown("### Step 1 · 음성 파일 업로드")
    col_up1, col_up2, col_up3 = st.columns([3, 2, 2])
    with col_up1:
        audio_file = st.file_uploader(
            "음성 파일 선택", type=["m4a","mp3","wav","ogg","aac","flac"],
            label_visibility="collapsed",
        )
    with col_up2:
        lang = st.selectbox("언어", ["ko","en","ja","zh"], index=0,
                            format_func=lambda x: {"ko":"한국어","en":"영어","ja":"일본어","zh":"중국어"}[x])
    with col_up3:
        model_size = st.selectbox("Whisper 모델", ["tiny","small","medium"],
                                  index=1,
                                  format_func=lambda x: {
                                      "tiny":  "tiny  (빠름·낮은정확도)",
                                      "small": "small (균형 ✅)",
                                      "medium":"medium (느림·높은정확도)",
                                  }[x])

    if not audio_file:
        st.info("💡 .m4a .mp3 .wav .ogg 파일을 업로드하세요.")
        return

    file_bytes = audio_file.read()
    file_ext   = audio_file.name.rsplit(".", 1)[-1]
    st.markdown(
        f'<div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;'
        f'font-size:.85rem;color:#94a3b8">'
        f'📎 <b style="color:#f1f5f9">{audio_file.name}</b> &nbsp; '
        f'{len(file_bytes)/1024:.0f} KB</div>',
        unsafe_allow_html=True,
    )

    # ── Step 2: 음성→텍스트 변환 ─────────────────────
    st.markdown("### Step 2 · 음성 텍스트 변환 (Whisper STT)")
    if st.button("▶ 변환 시작", type="primary", use_container_width=False):
        with st.spinner(f"🎙️ Whisper `{model_size}` 모델로 변환 중... (첫 실행 시 모델 다운로드 포함)"):
            try:
                full_text, segments = vp.transcribe_audio(
                    file_bytes, file_ext, model_size=model_size, language=lang
                )
                st.session_state["voice_transcript"] = full_text
                st.session_state["voice_segments"]   = segments
                st.session_state.pop("voice_analysis", None)  # 재분석 초기화
                st.success(f"✅ 변환 완료 — {len(full_text)}자")
            except Exception as e:
                st.error(f"❌ 변환 실패: {e}")

    # 변환 결과 표시
    if "voice_transcript" in st.session_state:
        transcript = st.session_state["voice_transcript"]
        segments   = st.session_state.get("voice_segments", [])

        st.markdown("#### 📝 변환된 텍스트")
        edited_transcript = st.text_area(
            "", value=transcript, height=180, label_visibility="collapsed",
            key="voice_transcript_edit",
            help="내용 수정 후 AI 분석 가능"
        )
        st.session_state["voice_transcript"] = edited_transcript

        if segments:
            with st.expander(f"⏱️ 타임스탬프 세부 내용 ({len(segments)}개 구간)", expanded=False):
                for seg in segments:
                    st.markdown(
                        f'<span style="color:#64748b;font-size:.78rem">[{seg["start"]}s ~ {seg["end"]}s]</span> '
                        f'{seg["text"]}',
                        unsafe_allow_html=True,
                    )

        st.divider()

        # ── Step 3: AI 분석 ──────────────────────────
        st.markdown("### Step 3 · AI 분석 — WBS / Action Item 추출")
        if not api_key and not base_url:
            st.warning("⚙️ LLM 미설정 — [시스템/데이터 관리] 탭 → LLM 설정에서 API Key 또는 Ollama URL을 입력하세요.")
        else:
            if st.button("🤖 AI 분석 실행", type="primary"):
                with st.spinner("AI가 WBS·Action Item 후보를 분석 중..."):
                    try:
                        analysis = vp.analyze_transcript(
                            edited_transcript, api_key=api_key, base_url=base_url, model=model
                        )
                        # WBS 매칭
                        all_wbs = db.get_all_wbs_flat()
                        analysis["wbs_matched"] = vp.match_wbs_candidates(
                            analysis.get("wbs_candidates", []), all_wbs
                        )
                        analysis["action_matched"] = vp.match_action_candidates(
                            analysis.get("action_candidates", []), all_wbs
                        )
                        analysis["source_filename"] = audio_file.name
                        st.session_state["voice_analysis"] = analysis
                    except Exception as e:
                        st.error(f"❌ AI 분석 오류: {e}")

    # ── Step 4: 리뷰 & 저장 ──────────────────────────
    if "voice_analysis" in st.session_state:
        analysis = st.session_state["voice_analysis"]

        st.markdown("### Step 4 · 결과 리뷰 & 저장")

        # 요약 박스
        st.markdown(
            f'<div style="background:#0f172a;border:1px solid #7c3aed55;border-left:4px solid #7c3aed;'
            f'border-radius:8px;padding:12px 16px;margin:8px 0">'
            f'<div style="font-size:.75rem;color:#a78bfa;letter-spacing:.06em">AI 요약</div>'
            f'<div style="color:#f1f5f9;margin-top:6px">{analysis.get("summary","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        meta_cols = st.columns(3)
        meta_cols[0].metric("미팅 날짜", analysis.get("meeting_date") or "-")
        meta_cols[1].metric("참석자", ", ".join(analysis.get("attendees") or []) or "-")
        meta_cols[2].metric(
            "후보 항목",
            f"WBS {len(analysis.get('wbs_matched',[]))}건 + Action {len(analysis.get('action_matched',[]))}건"
        )

        st.markdown("---")

        # ── WBS 후보 체크박스 ──────────────────────────
        wbs_matched = analysis.get("wbs_matched", [])
        sel_new_wbs = []
        if wbs_matched:
            st.markdown("#### 📂 WBS 후보")
            st.caption("✅ = 기존 WBS 매칭됨 | 🆕 = 신규 생성 | 체크박스로 저장할 항목 선택")
            for i, m in enumerate(wbs_matched):
                cand = m["candidate"]
                matched = m["matched"]
                conf   = m["confidence"]

                conf_color = {"high": "#22c55e", "medium": "#f59e0b", "none": "#64748b"}[conf]
                conf_icon  = {"high": "✅ 기존 매칭", "medium": "🟡 유사 매칭", "none": "🆕 신규"}[conf]

                label_html = (
                    f'{conf_icon} &nbsp; <b>{cand.get("wbs_type","")}</b>'
                    f'<span style="color:#64748b;font-size:.78rem"> [{cand.get("wbs_category","")}]'
                    f' {"→ 기존: " + matched["wbs_type"] if matched else ""}</span>'
                )
                st.markdown(
                    f'<div style="background:#0f172a;border:1px solid {conf_color}44;'
                    f'border-left:3px solid {conf_color};border-radius:6px;'
                    f'padding:6px 12px;margin:4px 0;font-size:.85rem">{label_html}</div>',
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns([1, 10])
                with c1:
                    checked = st.checkbox("", key=f"vwbs_chk_{i}",
                                         value=(conf == "none"),  # 신규만 기본 체크
                                         label_visibility="collapsed")
                with c2:
                    if matched and conf != "none":
                        st.caption(f"→ 기존 WBS ID {matched['id']} 사용 (저장 불필요)")
                    elif checked:
                        st.caption(f"코드: {cand.get('wbs_code_hint','')} | 이유: {cand.get('reason','')}")
                if checked and not matched:
                    sel_new_wbs.append(cand)

        # ── Action 후보 체크박스 ───────────────────────
        action_matched = analysis.get("action_matched", [])
        sel_actions = []
        if action_matched:
            st.markdown("#### ✅ Action Item 후보")
            st.caption("저장할 항목을 선택하세요")
            for i, act in enumerate(action_matched):
                wbs_id = act.get("matched_wbs_id")
                wbs_label = ""
                if wbs_id:
                    all_w = db.get_all_wbs_flat()
                    match = [w for w in all_w if w["id"] == wbs_id]
                    wbs_label = f"🔗 {match[0]['wbs_type']}" if match else ""
                else:
                    wbs_label = "📌 WBS 미귀속 (독립 Action)"

                st.markdown(
                    f'<div style="background:#0f172a;border:1px solid #0891b255;'
                    f'border-left:3px solid #0891b2;border-radius:6px;'
                    f'padding:6px 12px;margin:4px 0;font-size:.85rem">'
                    f'<b>{act.get("action_type","")}</b> — {act.get("content","")[:80]}'
                    f'<span style="color:#64748b;font-size:.76rem"> | 기한: {act.get("due_date") or "-"} | {wbs_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns([1, 10])
                with c1:
                    checked = st.checkbox("", key=f"vact_chk_{i}", value=True,
                                         label_visibility="collapsed")
                with c2:
                    st.caption(f"{wbs_label} | 담당: {act.get('owner') or '-'}")
                if checked:
                    sel_actions.append({**act, "matched_wbs_id": wbs_id})

        st.markdown("---")

        # ── 저장 버튼 ──────────────────────────────────
        sv1, sv2, sv3 = st.columns(3)
        with sv1:
            if st.button("💾 선택 항목 DB 저장", type="primary", use_container_width=True,
                         disabled=(not sel_new_wbs and not sel_actions)):
                saved_wbs = 0
                saved_act = 0
                wbs_id_map = {}  # wbs_type → new_id (방금 생성한 WBS)

                # 신규 WBS 저장
                for cand in sel_new_wbs:
                    code = cand.get("wbs_code_hint", "") or ""
                    par_id = None
                    if code and "." in code:
                        parent_code = ".".join(code.split(".")[:-1])
                        flat = db.get_all_wbs_flat()
                        pmatch = [w for w in flat if w.get("wbs_code") == parent_code]
                        if pmatch:
                            par_id = pmatch[0]["id"]
                    lvl = ((db.get_wbs_by_id(par_id) or {}).get("wbs_level", 0) + 1) if par_id else 1
                    new_id = db.insert_wbs(dict(
                        wbs_category=cand.get("wbs_category", ""),
                        wbs_type=cand.get("wbs_type", ""),
                        content=cand.get("reason", ""),
                        start_date="", due_date="", status="scheduled",
                        progress=0, owner="",
                        wbs_code=code, wbs_level=lvl, parent_wbs_id=par_id,
                    ))
                    wbs_id_map[cand.get("wbs_type", "")] = new_id
                    saved_wbs += 1

                # Action 저장
                for act in sel_actions:
                    wbs_id = act.get("matched_wbs_id")
                    # 방금 생성한 WBS에 연결 시도
                    if not wbs_id:
                        hint = act.get("wbs_ref_hint", "")
                        if hint:
                            wbs_id = wbs_id_map.get(hint)
                    db.insert_action(dict(
                        action_type=act.get("action_type", ""),
                        content=act.get("content", ""),
                        start_date="",
                        due_date=act.get("due_date", ""),
                        status=act.get("status", "todo"),
                        wbs_id=wbs_id,
                        notes=f"음성 메모 자동 추출: {audio_file.name}",
                    ))
                    saved_act += 1

                st.success(f"✅ WBS {saved_wbs}건 + Action {saved_act}건 저장 완료!")
                st.session_state.pop("voice_analysis", None)
                st.rerun()

        with sv2:
            # 회의록 .md 내보내기
            md_note = vp.make_meeting_note_md(
                edited_transcript, analysis, audio_file.name
            )
            safe_name = audio_file.name.rsplit(".", 1)[0].replace(" ", "_")
            st.download_button(
                "⬇️ 회의록 .md 내보내기", data=md_note.encode("utf-8"),
                file_name=f"Meeting_{safe_name}.md", mime="text/markdown",
                use_container_width=True,
            )

        with sv3:
            if st.button("🔄 새 음성 파일 처리", use_container_width=True):
                for k in ["voice_transcript", "voice_segments", "voice_analysis"]:
                    st.session_state.pop(k, None)
                st.rerun()


# ── 메인 ─────────────────────────────────────────
def main():
    render_header()
    tab_wbs, tab_act, tab_upload, tab_voice, tab_gantt, tab_agent, tab_admin = st.tabs([
        "📋 WBS 관리",
        "✅ Action Items",
        "📤 Obsidian 연동",
        "🎙️ 음성 메모",
        "📊 Gantt & 대시보드",
        "🤖 AI 에이전트",
        "⚙️ 시스템/데이터 관리",
    ])
    with tab_wbs:    render_wbs_tab()
    with tab_act:    render_action_tab()
    with tab_upload: render_upload_tab()
    with tab_voice:  render_voice_tab()
    with tab_gantt:  render_gantt_tab()
    with tab_agent:  render_agent_tab()
    with tab_admin:  render_admin_tab()


if __name__ == "__main__":
    main()
