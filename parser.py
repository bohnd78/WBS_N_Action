"""
parser.py - Obsidian 마크다운 노트 파서
YAML frontmatter + 본문 섹션에서 WBS / Action Item 데이터 추출
"""

import re
from datetime import datetime

try:
    import frontmatter
    HAS_FRONTMATTER = True
except ImportError:
    HAS_FRONTMATTER = False


# ──────────────────────────────────────────────
# 메인 파싱 함수
# ──────────────────────────────────────────────
def parse_obsidian_note(content: str, filename: str = "") -> tuple[str | None, dict | str]:
    """
    Obsidian 마크다운 노트를 파싱하여 (유형, 데이터) 반환.

    Returns:
        ('wbs', data_dict)       WBS 항목인 경우
        ('action_item', data_dict) Action Item인 경우
        (None, error_message)    파싱 불가인 경우
    """
    now = datetime.now().strftime("%Y-%m-%d")

    if HAS_FRONTMATTER:
        try:
            post = frontmatter.loads(content)
            meta = dict(post.metadata)
            body = post.content
        except Exception as e:
            # fallback: 수동 파싱
            meta, body = _manual_parse(content)
    else:
        meta, body = _manual_parse(content)

    note_type = str(meta.get("type", "")).strip().lower()

    if note_type == "wbs":
        data = {
            "wbs_category":     _safe_str(meta.get("wbs_category", "")),
            "wbs_type":         _safe_str(meta.get("wbs_type", "")),
            "registered_date":  _safe_str(meta.get("registered_date", now)),
            "content":          _extract_section(body, "내용") or _safe_str(meta.get("content", "")),
            "start_date":       _safe_str(meta.get("start_date", "")),
            "due_date":         _safe_str(meta.get("due_date", "")),
            "end_date":         _safe_str(meta.get("end_date", "")),
            "status":           _safe_str(meta.get("status", "todo")),
            "notes":            _extract_section(body, "기타 특이사항") or _safe_str(meta.get("notes", "")),
            "source_file":      filename,
        }
        return "wbs", data

    elif note_type == "action_item":
        data = {
            "action_type":      _safe_str(meta.get("action_type", "")),
            "registered_date":  _safe_str(meta.get("registered_date", now)),
            "content":          _extract_section(body, "내용") or _safe_str(meta.get("content", "")),
            "start_date":       _safe_str(meta.get("start_date", "")),
            "due_date":         _safe_str(meta.get("due_date", "")),
            "end_date":         _safe_str(meta.get("end_date", "")),
            "status":           _safe_str(meta.get("status", "todo")),
            "notes":            _extract_section(body, "기타") or _safe_str(meta.get("notes", "")),
            "wbs_id":           None,   # 업로드 후 수동 연결
            "source_file":      filename,
        }
        return "action_item", data

    else:
        return None, f"알 수 없는 노트 유형 (type='{meta.get('type', 'undefined')}'). WBS 또는 action_item 이어야 합니다."


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────
def _safe_str(value) -> str:
    """None / NaN 안전 변환."""
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none", "null") else s


def _extract_section(content: str, section_name: str) -> str:
    """## 섹션명 아래 텍스트 추출 (다음 ## 전까지)."""
    pattern = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def _manual_parse(content: str) -> tuple[dict, str]:
    """python-frontmatter 없을 때 수동 YAML 파싱."""
    meta: dict = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_block = parts[1]
            body = parts[2].strip()
            for line in yaml_block.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip().strip('"').strip("'")

    return meta, body


# ──────────────────────────────────────────────
# 다중 파일 일괄 파싱
# ──────────────────────────────────────────────
def parse_multiple_notes(file_contents: list[tuple[str, str]]) -> list[dict]:
    """
    여러 노트를 파싱하여 결과 리스트 반환.

    Args:
        file_contents: [(filename, content), ...] 리스트

    Returns:
        [{'filename', 'type', 'data', 'success'}, ...] 리스트
    """
    results = []
    for filename, content in file_contents:
        note_type, data = parse_obsidian_note(content, filename)
        results.append({
            "filename": filename,
            "type": note_type,
            "data": data,
            "success": note_type in ("wbs", "action_item"),
        })
    return results
