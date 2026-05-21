"""
charts.py - Plotly 기반 차트 모듈
Gantt 차트, 진척률 차트, 상태 분포 차트
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

STATUS_COLOR = {
    "todo":        "#64748b",
    "in_progress": "#f59e0b",
    "done":        "#22c55e",
    "blocked":     "#ef4444",
}

STATUS_LABEL = {
    "todo":        "대기",
    "in_progress": "진행중",
    "done":        "완료",
    "blocked":     "블록",
}

CATEGORY_COLORS = [
    "#7c3aed", "#2563eb", "#0891b2", "#059669",
    "#d97706", "#dc2626", "#7c3aed", "#db2777",
]


def make_gantt(df: pd.DataFrame, title: str = "WBS Gantt Chart") -> go.Figure:
    """
    WBS 또는 Action Item DataFrame으로 Gantt 차트 생성.
    필수 컬럼: start_date, due_date, status
    선택 컬럼: wbs_category, wbs_type, action_type, content, progress
    """
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=title,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"),
            annotations=[dict(text="데이터 없음 (시작일/종료예정일 입력 필요)", showarrow=False,
                              font=dict(size=16, color="#64748b"), xref="paper", yref="paper",
                              x=0.5, y=0.5)],
        )
        return fig

    # 라벨 컬럼 결정
    if "wbs_type" in df.columns:
        df = df.copy()
        df["_label"] = df.apply(
            lambda r: f"[{r.get('wbs_category', '')}] {r.get('wbs_type', '')}", axis=1
        )
        color_col = "wbs_category"
    else:
        df = df.copy()
        df["_label"] = df.apply(
            lambda r: f"[{r.get('action_type', '')}] {str(r.get('content', ''))[:40]}", axis=1
        )
        color_col = "action_type"

    # 날짜 변환
    df["_start"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["_end"]   = pd.to_datetime(df["due_date"],   errors="coerce")
    df = df.dropna(subset=["_start", "_end"])

    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=title, paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
                          font=dict(color="#e2e8f0"))
        return fig

    categories = df[color_col].unique().tolist() if color_col in df.columns else ["항목"]
    cat_color_map = {c: CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i, c in enumerate(categories)}

    fig = go.Figure()

    for _, row in df.iterrows():
        cat = row.get(color_col, "항목") if color_col in df.columns else "항목"
        color = cat_color_map.get(cat, "#7c3aed")
        status = row.get("status", "todo")
        bar_color = STATUS_COLOR.get(status, color)

        progress = row.get("progress", 0)
        hover = (
            f"<b>{row['_label']}</b><br>"
            f"시작: {row['_start'].strftime('%Y-%m-%d')}<br>"
            f"마감: {row['_end'].strftime('%Y-%m-%d')}<br>"
            f"상태: {STATUS_LABEL.get(status, status)}<br>"
            f"진척률: {progress}%"
        )

        duration = max((row["_end"] - row["_start"]).days, 1)

        fig.add_trace(go.Bar(
            y=[row["_label"]],
            x=[duration],
            base=[row["_start"].timestamp() * 1000],
            orientation="h",
            marker=dict(color=bar_color, opacity=0.85, line=dict(width=0)),
            hovertemplate=hover + "<extra></extra>",
            name=STATUS_LABEL.get(status, status),
            showlegend=False,
        ))

        # 진척률 오버레이 (완료 비율)
        if progress > 0:
            done_duration = duration * (progress / 100)
            fig.add_trace(go.Bar(
                y=[row["_label"]],
                x=[done_duration],
                base=[row["_start"].timestamp() * 1000],
                orientation="h",
                marker=dict(color="#22c55e", opacity=0.5, line=dict(width=0)),
                hoverinfo="skip",
                showlegend=False,
            ))

    # 오늘 날짜 수직선
    today_ts = datetime.now().timestamp() * 1000
    fig.add_vline(
        x=today_ts,
        line_dash="dash",
        line_color="#f43f5e",
        line_width=2,
        annotation_text="오늘",
        annotation_font_color="#f43f5e",
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color="#e2e8f0")),
        barmode="overlay",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0", family="Pretendard, sans-serif"),
        xaxis=dict(
            type="date",
            tickformat="%m/%d",
            gridcolor="#334155",
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#334155",
            showgrid=False,
            autorange="reversed",
        ),
        margin=dict(l=10, r=10, t=50, b=10),
        height=max(300, len(df) * 45 + 100),
        hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font_color="#e2e8f0"),
    )
    return fig


def make_status_donut(stats: dict, mode: str = "wbs") -> go.Figure:
    """WBS 또는 Action 상태 도넛 차트."""
    if mode == "wbs":
        values = [
            stats["wbs_total"] - stats["wbs_done"] - stats["wbs_in_progress"] - stats["wbs_blocked"],
            stats["wbs_in_progress"],
            stats["wbs_done"],
            stats["wbs_blocked"],
        ]
        title = "WBS 상태"
    else:
        values = [
            stats["act_total"] - stats["act_done"] - stats["act_in_progress"] - stats["act_blocked"],
            stats["act_in_progress"],
            stats["act_done"],
            stats["act_blocked"],
        ]
        title = "Action 상태"

    labels = ["대기", "진행중", "완료", "블록"]
    colors = ["#64748b", "#f59e0b", "#22c55e", "#ef4444"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=[max(0, v) for v in values],
        hole=0.65,
        marker=dict(colors=colors, line=dict(color="#0f172a", width=2)),
        textinfo="percent+label",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="%{label}: %{value}건<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#e2e8f0"), x=0.5),
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0"),
        margin=dict(l=10, r=10, t=40, b=10),
        height=250,
        showlegend=False,
    )
    return fig


def make_progress_bar_chart(df: pd.DataFrame) -> go.Figure:
    """WBS 항목별 진척률 가로 막대 차트."""
    if df.empty or "progress" not in df.columns:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                          font=dict(color="#e2e8f0"), height=200)
        return fig

    df = df[df["progress"].notna()].copy()
    df["_label"] = df.apply(lambda r: f"[{r.get('wbs_category','')[:8]}] {r.get('wbs_type','')[:20]}", axis=1)
    df = df.sort_values("progress", ascending=True).tail(12)

    colors = [STATUS_COLOR.get(s, "#7c3aed") for s in df["status"]]

    fig = go.Figure(go.Bar(
        x=df["progress"],
        y=df["_label"],
        orientation="h",
        marker=dict(color=colors, opacity=0.85),
        text=[f"{v}%" for v in df["progress"]],
        textposition="outside",
        textfont=dict(color="#e2e8f0", size=11),
        hovertemplate="%{y}<br>진척률: %{x}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="WBS 진척률", font=dict(size=14, color="#e2e8f0")),
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0"),
        xaxis=dict(range=[0, 115], showgrid=True, gridcolor="#334155", zeroline=False),
        yaxis=dict(showgrid=False),
        margin=dict(l=10, r=10, t=40, b=10),
        height=max(250, len(df) * 35 + 80),
    )
    return fig


def make_category_timeline(df: pd.DataFrame) -> go.Figure:
    """카테고리별 작업량 타임라인 (Bar chart by month)."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                          font=dict(color="#e2e8f0"), height=200)
        return fig

    df = df.copy()
    df["_month"] = pd.to_datetime(df["registered_date"], errors="coerce").dt.to_period("M").astype(str)
    grp = df.groupby(["_month", "status"]).size().reset_index(name="count")

    fig = px.bar(
        grp, x="_month", y="count", color="status",
        color_discrete_map=STATUS_COLOR,
        labels={"_month": "월", "count": "건수", "status": "상태"},
        barmode="stack",
    )
    fig.update_layout(
        title=dict(text="월별 등록 현황", font=dict(size=14, color="#e2e8f0")),
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0"),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#334155"),
        margin=dict(l=10, r=10, t=40, b=10),
        height=260,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
