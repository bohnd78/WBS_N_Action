"""
agent.py - LLM Agent 모듈
Obsidian 노트 / 프로젝트 데이터를 분석하는 AI 에이전트
OpenAI 호환 API (OpenAI / Ollama / 로컬 LLM) 지원
"""

import json
from datetime import datetime
import database as db

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# ──────────────────────────────────────────────
# 시스템 프롬프트
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 ERP 구현 프로젝트(SAP Sales Process 모듈) 전문 컨설턴트 AI 어시스턴트입니다.

당신의 역할:
1. **WBS & Action Item 분석**: 현재 프로젝트 상태를 분석하고 위험 요소를 식별합니다
2. **일정 전략 제안**: 마감 임박 항목에 대한 우선순위와 실행 전략을 제안합니다
3. **노트 파싱 지원**: Obsidian 노트에서 구조화된 데이터를 추출합니다
4. **SAP/ERP 전문 지식**: SD 모듈, RAP 프로그래밍, Fit-Gap 분석 등 ERP 구현 관련 질문에 답변합니다

대화 시 항상:
- 구체적이고 실행 가능한 조언 제공
- 프로젝트 데이터 기반으로 답변
- 한국어로 답변 (기술 용어는 영어 혼용 가능)
- 마감 임박 항목은 ⚠️ 로 강조

현재 프로젝트 컨텍스트가 제공되면 해당 데이터를 기반으로 분석합니다."""


def _build_project_context() -> str:
    """현재 DB 데이터를 요약하여 LLM 컨텍스트 문자열 생성."""
    stats = db.get_summary_stats()
    wbs_df = db.get_wbs_items()
    act_df = db.get_action_items()
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"=== 프로젝트 현황 ({today}) ===",
        f"WBS: 총 {stats['wbs_total']}건 | 완료 {stats['wbs_done']} | 진행중 {stats['wbs_in_progress']} | 블록 {stats['wbs_blocked']}",
        f"Action Item: 총 {stats['act_total']}건 | 완료 {stats['act_done']} | 진행중 {stats['act_in_progress']}",
        f"7일 내 마감: {stats['upcoming_wbs'] + stats['upcoming_act']}건",
        f"평균 진척률: {stats['avg_progress']}%",
        "",
    ]

    # 진행중/블록 WBS
    active_wbs = wbs_df[wbs_df["status"].isin(["in_progress", "blocked"])]
    if not active_wbs.empty:
        lines.append("=== 진행중/블록 WBS ===")
        for _, r in active_wbs.iterrows():
            progress = r.get("progress", 0)
            lines.append(
                f"[{r['wbs_category']}] {r['wbs_type']} | 상태:{r['status']} | {progress}% | 마감:{r['due_date'] or '-'}"
            )
        lines.append("")

    # 마감 임박 Action Items (7일)
    if not act_df.empty:
        overdue = act_df[
            (act_df["due_date"] != "") &
            (act_df["due_date"] <= (datetime.now().strftime("%Y-%m-%d"))) &
            (act_df["status"] != "done")
        ]
        if not overdue.empty:
            lines.append("=== ⚠️ 마감 초과 Action Items ===")
            for _, r in overdue.iterrows():
                lines.append(f"[{r['action_type']}] {r['content'][:60]} | 마감:{r['due_date']}")
            lines.append("")

    return "\n".join(lines)


def _get_client(api_key: str, base_url: str):
    """OpenAI 클라이언트 생성."""
    if not HAS_OPENAI:
        return None
    kwargs = {"api_key": api_key or "ollama"}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def chat(
    messages: list[dict],
    api_key: str = "",
    base_url: str = "",
    model: str = "gpt-4o-mini",
    include_project_context: bool = True,
) -> str:
    """
    LLM에 메시지 전송 후 응답 반환.

    Args:
        messages: [{"role": "user"/"assistant", "content": "..."}] 리스트
        api_key: OpenAI API 키 (Ollama면 빈 문자열)
        base_url: 로컬 LLM URL (예: http://localhost:11434/v1)
        model: 모델명
        include_project_context: True면 시스템 프롬프트에 프로젝트 현황 추가

    Returns:
        응답 문자열
    """
    if not HAS_OPENAI:
        return "❌ openai 패키지가 설치되지 않았습니다. `pip install openai` 실행 후 재시작하세요."

    client = _get_client(api_key, base_url)
    if client is None:
        return "❌ LLM 클라이언트 초기화 실패."

    system_content = SYSTEM_PROMPT
    if include_project_context:
        ctx = _build_project_context()
        system_content = SYSTEM_PROMPT + "\n\n" + ctx

    full_messages = [{"role": "system", "content": system_content}] + messages

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ LLM 오류: {str(e)}"


def extract_action_items_from_note(
    note_content: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """
    자유 형식 노트에서 Action Item 자동 추출.

    Returns:
        [{"action_type": ..., "content": ..., "due_date": ..., "status": ...}, ...]
    """
    if not HAS_OPENAI:
        return []

    prompt = f"""다음 노트에서 Action Item을 추출하여 JSON 배열로 반환하세요.
각 항목: {{"action_type": "미팅(출장)|문서작성|개발(분석/설계)|준비작업|역량확보|테스트|task list 및 관련 일정표 작성 중 하나", "content": "내용", "due_date": "YYYY-MM-DD 또는 빈 문자열", "status": "todo|in_progress|done|blocked"}}

노트:
{note_content}

JSON 배열만 반환 (다른 텍스트 없이):"""

    client = _get_client(api_key, base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
        )
        raw = resp.choices[0].message.content.strip()
        # JSON 블록 추출
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return []


def generate_strategy(
    api_key: str = "",
    base_url: str = "",
    model: str = "gpt-4o-mini",
) -> str:
    """현재 프로젝트 상태 기반 수행 전략 문서 생성."""
    ctx = _build_project_context()
    prompt = f"""다음 ERP 프로젝트 현황을 바탕으로 수행 전략 보고서를 작성해주세요.

{ctx}

보고서 형식:
1. 현황 요약
2. 주요 리스크 및 대응방안 (⚠️ 표시)
3. 우선순위 Action Plan (이번 주)
4. 중기 권고사항 (다음 2주)
5. KPI 달성을 위한 체크리스트"""

    if not HAS_OPENAI:
        return "❌ openai 패키지 필요"

    client = _get_client(api_key, base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=3000,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ 전략 생성 오류: {str(e)}"
