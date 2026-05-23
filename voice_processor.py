"""
voice_processor.py — 음성 메모 처리 모듈

파이프라인:
  음성 파일 → faster-whisper STT → 텍스트
  텍스트 → LLM 분석 → WBS/Action 후보 구조화
  후보 → 기존 DB WBS 매칭
"""

import os
import json
import tempfile
from pathlib import Path

# ── faster-whisper ────────────────────────────────
try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

# ── ffmpeg (오디오 변환) ────────────────────────────
try:
    import ffmpeg as _ffmpeg
    HAS_FFMPEG = True
except ImportError:
    HAS_FFMPEG = False


# ── 전역 모델 캐시 (재사용) ─────────────────────────
_whisper_model_cache: dict = {}


def _get_whisper_model(model_size: str = "small") -> "WhisperModel | None":
    """WhisperModel을 캐싱하여 재사용."""
    if not HAS_WHISPER:
        return None
    if model_size not in _whisper_model_cache:
        _whisper_model_cache[model_size] = WhisperModel(
            model_size,
            device="auto",         # M-chip: CoreML 자동 감지
            compute_type="auto",
        )
    return _whisper_model_cache[model_size]


def convert_to_wav(src_bytes: bytes, src_ext: str) -> bytes:
    """
    오디오 파일을 WAV(16kHz mono)로 변환.
    faster-whisper가 WAV를 가장 안정적으로 처리.
    """
    suffix = src_ext if src_ext.startswith(".") else f".{src_ext}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        tmp_in.write(src_bytes)
        tmp_in_path = tmp_in.name

    tmp_out_path = tmp_in_path.replace(suffix, "_converted.wav")
    try:
        (
            _ffmpeg
            .input(tmp_in_path)
            .output(tmp_out_path, ar=16000, ac=1, format="wav")
            .overwrite_output()
            .run(quiet=True)
        )
        with open(tmp_out_path, "rb") as f:
            return f.read()
    finally:
        for p in [tmp_in_path, tmp_out_path]:
            try:
                os.unlink(p)
            except Exception:
                pass


def transcribe_audio(
    file_bytes: bytes,
    file_ext: str,
    model_size: str = "small",
    language: str = "ko",
) -> tuple[str, list[dict]]:
    """
    음성 파일 → 텍스트 변환.

    Returns:
        (full_text, segments)
        segments: [{"start": float, "end": float, "text": str}, ...]
    """
    if not HAS_WHISPER:
        raise RuntimeError("faster-whisper 패키지가 설치되지 않았습니다. `pip install faster-whisper`")

    # WAV로 변환 (m4a, mp3 등 지원)
    ext = file_ext.lower().lstrip(".")
    if ext in ("wav",):
        wav_bytes = file_bytes
    else:
        if not HAS_FFMPEG:
            raise RuntimeError("ffmpeg-python이 설치되지 않았습니다. `pip install ffmpeg-python` + `brew install ffmpeg`")
        wav_bytes = convert_to_wav(file_bytes, ext)

    model = _get_whisper_model(model_size)

    # 임시 파일로 저장 후 변환
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        segments_gen, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,            # 음성 구간만 처리 (무음 제거)
            vad_parameters={"min_silence_duration_ms": 500},
        )
        segments = []
        texts = []
        for seg in segments_gen:
            segments.append({
                "start": round(seg.start, 1),
                "end":   round(seg.end, 1),
                "text":  seg.text.strip(),
            })
            texts.append(seg.text.strip())
        full_text = " ".join(texts)
        return full_text, segments
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── LLM 분석 ─────────────────────────────────────
VOICE_ANALYSIS_PROMPT = """당신은 ERP 프로젝트 관리 전문가입니다.
다음은 프로젝트 미팅/현장 음성 메모의 텍스트 변환본입니다.

이 텍스트를 분석하여 아래 JSON 형식으로 반환하세요:

{{
  "summary": "2~4줄 요약",
  "meeting_date": "YYYY-MM-DD 또는 빈 문자열",
  "attendees": ["참석자1", "참석자2"],
  "wbs_candidates": [
    {{
      "wbs_type": "WBS 항목명",
      "wbs_category": "카테고리 (To-Be Process 개발 | 현업 담당자 교육 | 기술 지원 등)",
      "wbs_code_hint": "예: 1.1 (모르면 빈 문자열)",
      "reason": "이 내용이 WBS 항목인 이유"
    }}
  ],
  "action_candidates": [
    {{
      "action_type": "미팅(출장)|문서작성|개발(분석/설계)|준비작업|역량확보|테스트|task list 및 관련 일정표 작성",
      "content": "구체적인 할 일 내용",
      "due_date": "YYYY-MM-DD 또는 빈 문자열",
      "status": "todo",
      "wbs_ref_hint": "귀속될 WBS 항목명 (모르면 빈 문자열)",
      "owner": "담당자 (모르면 빈 문자열)"
    }}
  ]
}}

음성 텍스트:
{transcript}

JSON만 반환 (다른 텍스트 없이):"""


def analyze_transcript(
    transcript: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "gpt-4o-mini",
) -> dict:
    """
    텍스트 → WBS/Action 구조화 (LLM 분석).

    Returns:
        {summary, meeting_date, attendees, wbs_candidates, action_candidates}
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {
            "summary": "❌ openai 패키지 필요",
            "meeting_date": "", "attendees": [],
            "wbs_candidates": [], "action_candidates": [],
        }

    kwargs = {"api_key": api_key or "ollama"}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)

    prompt = VOICE_ANALYSIS_PROMPT.format(transcript=transcript[:4000])

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2048,
        )
        raw = resp.choices[0].message.content.strip()
        # JSON 블록 추출
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                if part.startswith("json"):
                    raw = part[4:].strip()
                    break
                elif part.strip().startswith("{"):
                    raw = part.strip()
                    break
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {
            "summary": f"⚠️ JSON 파싱 실패: {e}",
            "meeting_date": "", "attendees": [],
            "wbs_candidates": [], "action_candidates": [],
        }
    except Exception as e:
        return {
            "summary": f"❌ LLM 오류: {e}",
            "meeting_date": "", "attendees": [],
            "wbs_candidates": [], "action_candidates": [],
        }


def match_wbs_candidates(
    candidates: list[dict],
    existing_wbs: list[dict],
) -> list[dict]:
    """
    WBS 후보 → 기존 WBS 매칭.

    Args:
        candidates: analyze_transcript의 wbs_candidates
        existing_wbs: db.get_all_wbs_flat() 결과

    Returns:
        [{"candidate": {...}, "matched": {...} or None, "confidence": "high|medium|none"}]
    """
    results = []
    for cand in candidates:
        cand_type = (cand.get("wbs_type") or "").lower()
        cand_code = (cand.get("wbs_code_hint") or "").strip()
        matched = None
        confidence = "none"

        for w in existing_wbs:
            w_type = (w.get("wbs_type") or "").lower()
            w_code = (w.get("wbs_code") or "").strip()

            # 1순위: wbs_code 일치
            if cand_code and w_code and cand_code == w_code:
                matched = w
                confidence = "high"
                break

            # 2순위: wbs_type 완전 일치
            if cand_type and w_type and cand_type == w_type:
                matched = w
                confidence = "high"
                break

            # 3순위: 부분 일치 (3글자 이상 공통 문자열)
            if cand_type and w_type and len(cand_type) >= 3:
                common = sum(1 for c in cand_type if c in w_type)
                if common / max(len(cand_type), 1) > 0.5:
                    matched = w
                    confidence = "medium"
                    # break 안 함 (더 좋은 매칭 탐색)

        results.append({
            "candidate": cand,
            "matched":   matched,
            "confidence": confidence,
        })
    return results


def match_action_candidates(
    action_candidates: list[dict],
    existing_wbs: list[dict],
) -> list[dict]:
    """
    Action 후보의 wbs_ref_hint → 기존 WBS ID 매칭.

    Returns:
        action_candidates에 matched_wbs_id 필드 추가한 리스트
    """
    result = []
    for act in action_candidates:
        hint = (act.get("wbs_ref_hint") or "").lower()
        matched_id = None
        if hint:
            for w in existing_wbs:
                w_type = (w.get("wbs_type") or "").lower()
                if hint in w_type or w_type in hint:
                    matched_id = w["id"]
                    break
        result.append({**act, "matched_wbs_id": matched_id})
    return result


def make_meeting_note_md(
    transcript: str,
    analysis: dict,
    filename: str = "",
) -> str:
    """
    음성 분석 결과 → Obsidian 회의록 .md 생성.
    """
    from datetime import datetime
    date_str = analysis.get("meeting_date") or datetime.now().strftime("%Y-%m-%d")
    attendees = "\n".join(f"- {a}" for a in (analysis.get("attendees") or []))
    actions_md = "\n".join(
        f"- [ ] [@{a.get('owner','?')}] {a['content']} (기한: {a.get('due_date') or '-'})"
        for a in (analysis.get("action_candidates") or [])
    )
    return f"""\
---
type: action_item
action_type: "미팅(출장)"
status: done
meeting_date: "{date_str}"
source_audio: "{filename}"
notes: ""
---

# 회의록 — {date_str}

## 요약
{analysis.get('summary', '')}

## 참석자
{attendees or '- (미확인)'}

## 원본 텍스트
> {transcript[:1500]}{'...' if len(transcript) > 1500 else ''}

## Action Items
{actions_md or '- (없음)'}
"""
