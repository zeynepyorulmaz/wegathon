from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import re

from ..config import settings
from ..schemas import ParsedOutput


_PROMPT_CACHE: dict[str, str] = {}


def _read_system_prompt(path: Path) -> str:
    key = str(path)
    if key in _PROMPT_CACHE:
        return _PROMPT_CACHE[key]
    content = path.read_text(encoding="utf-8")
    _PROMPT_CACHE[key] = content
    return content


def build_messages(user_input: str) -> Dict[str, Any]:
    system_prompt = _read_system_prompt(settings.prompt_path)
    # Reinforce JSON-only response as the final instruction
    system_prompt_final = system_prompt.strip() + "\n\nSADECE geçerli JSON döndür. Hiçbir ek açıklama ekleme."
    return {
        "system": system_prompt_final,
        "user": user_input,
    }


def _supports_temperature(model: str) -> bool:
    name = model.lower()
    # Some nano/preview models only support default temperature; avoid setting it explicitly
    if "nano" in name or name.startswith("gpt-5"):
        return False
    return True


def call_openai(messages: Dict[str, str]) -> str:
    from openai import OpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=settings.openai_api_key)

    params: Dict[str, Any] = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": messages["system"]},
            {"role": "user", "content": messages["user"]},
        ],
    }

    if settings.enforce_json:
        params["response_format"] = {"type": "json_object"}
    if _supports_temperature(settings.model):
        params["temperature"] = 0

    try:
        completion = client.chat.completions.create(**params)
    except Exception as e:
        msg = str(e).lower()
        mutated = False
        if "temperature" in msg and ("unsupported" in msg or "does not support" in msg):
            params.pop("temperature", None)
            mutated = True
        if "response_format" in msg and ("unsupported" in msg or "does not support" in msg):
            params.pop("response_format", None)
            mutated = True
        if mutated:
            completion = client.chat.completions.create(**params)
        else:
            raise

    content = completion.choices[0].message.content or ""
    return content


def _extract_first_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in response")
    return text[start : end + 1]


def call_anthropic(messages: Dict[str, str]) -> str:
    from anthropic import Anthropic

    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = Anthropic(api_key=settings.anthropic_api_key)

    msg = client.messages.create(
        model=settings.model,
        max_tokens=4096,
        temperature=0,
        system=messages["system"],
        messages=[{"role": "user", "content": messages["user"]}],
    )

    # Concatenate text blocks
    parts: list[str] = []
    for block in msg.content:
        if getattr(block, "type", "") == "text":
            parts.append(getattr(block, "text", ""))
    content = "".join(parts)

    if settings.enforce_json:
        content = _extract_first_json_block(content)
    return content


def parse_with_llm(user_input: str) -> ParsedOutput:
    messages = build_messages(user_input)

    if settings.llm_provider == "openai":
        raw = call_openai(messages)
    else:
        raw = call_anthropic(messages)

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        # Best effort recovery from non-JSON; try brace extraction
        data = json.loads(_extract_first_json_block(raw))

    # Normalize to expected schema, then validate
    normalized = _normalize_to_schema(data)
    parsed = ParsedOutput.model_validate(normalized)
    return parsed


# -------------------------
# Normalization Utilities
# -------------------------

_COUNTRY_MAP = {
    # Turkish
    "türkiye": "TR",
    "turkiye": "TR",
    "turkey": "TR",
    "almanya": "DE",
    "almanca": "DE",
    "alm": "DE",
    "almanya cumhuriyeti": "DE",
    # English common
    "germany": "DE",
    "deutschland": "DE",
    "united states": "US",
    "usa": "US",
    "united kingdom": "GB",
    "uk": "GB",
    # Add more as needed
}


def _iso_country(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    v = value.strip()
    if len(v) == 2 and v.isalpha() and v.upper() == v:
        return v
    key = v.lower()
    return _COUNTRY_MAP.get(key, v[:2].upper() if len(v) >= 2 else v)


def _ensure_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    # Coerce dict/str to list-empty to be safe
    return []


def _compute_end_date_if_missing(d: Dict[str, Any]) -> None:
    start = d.get("start_date")
    duration = d.get("duration")
    if start and duration and not d.get("end_date"):
        try:
            dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = dt + timedelta(days=int(duration) - 1 if int(duration) > 0 else 0)
            d["end_date"] = end_dt.strftime("%Y-%m-%d")
        except Exception:
            # Best effort; ignore if parsing fails
            pass


def _parse_duration_to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, dict):
        # Support shapes like {"min_days": 3, "max_days": 4} or {"min": 3, "max": 4}
        candidates: List[int] = []
        for key in ("max_days", "min_days", "max", "min", "days", "value", "count"):
            v = value.get(key)
            if isinstance(v, (int, float)):
                candidates.append(int(v))
            elif isinstance(v, str):
                try:
                    candidates.append(int(v))
                except Exception:
                    pass
        if candidates:
            return max(candidates)
        # Fallback: look for numeric values in nested dict as strings
        try:
            text = json.dumps(value, ensure_ascii=False)
            nums = [int(n) for n in re.findall(r"\d+", text)]
            if nums:
                return max(nums)
        except Exception:
            pass
        return None
    if isinstance(value, str):
        # Extract all integers in the string, e.g. "3-4 gün" -> [3, 4]
        nums = [int(n) for n in re.findall(r"\d+", value)]
        if not nums:
            return None
        # If a range is given, choose the max to be conservative
        return max(nums)
    return None


def _coerce_assumption(item: Any) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "field": "unknown",
            "issue": "assumption applied based on parsing rules",
            "assumed_value": item,
        }
    field = item.get("field", "unknown")
    issue = item.get("issue")
    if not isinstance(issue, str) or not issue.strip():
        issue = "assumption applied based on parsing rules"
    assumed_value = item.get("assumed_value")
    return {
        "field": field,
        "issue": issue,
        "assumed_value": assumed_value,
    }


def _coerce_ambiguity(item: Any) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "field": "unknown",
            "issue": "ambiguity detected during parsing",
            "assumed_value": item,
        }
    field = item.get("field", "unknown")
    issue = item.get("issue")
    if not isinstance(issue, str) or not issue.strip():
        issue = "ambiguity detected during parsing"
    assumed_value = item.get("assumed_value")
    return {
        "field": field,
        "issue": issue,
        "assumed_value": assumed_value,
    }


def _normalize_to_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)

    # departure
    departure = dict(out.get("departure") or {})
    if departure:
        if "country" in departure:
            departure["country"] = _iso_country(departure.get("country"))
        if "detected" not in departure:
            # Heuristic: if Istanbul TR default is often assumed; mark false, else true
            city = (departure.get("city") or "").lower()
            country = (departure.get("country") or "").upper()
            assumed_istanbul = city in {"istanbul", "i̇stanbul"} and country in {"TR", ""}
            departure["detected"] = False if assumed_istanbul else True
        out["departure"] = departure

    # destination
    destination = dict(out.get("destination") or {})
    if destination:
        if "country" in destination:
            destination["country"] = _iso_country(destination.get("country"))
        if "detected" not in destination:
            destination["detected"] = True
        out["destination"] = destination

    # dates
    dates = dict(out.get("dates") or {})
    if dates:
        # Normalize duration to an int if model returned a string like "3-4 gün"
        if dates.get("duration") is not None and not isinstance(dates.get("duration"), int):
            dur = _parse_duration_to_int(dates.get("duration"))
            if dur is not None:
                dates["duration"] = dur
        _compute_end_date_if_missing(dates)
        out["dates"] = dates

    # budget defaults
    budget = dict(out.get("budget") or {})
    if budget is not None:
        if budget.get("currency") in (None, ""):
            budget["currency"] = "TRY"
        if budget.get("amount") in (None, ""):
            budget["specified"] = False if budget.get("specified") is None else budget.get("specified")
        if budget.get("per_person") is None:
            budget["per_person"] = False
        out["budget"] = budget

    # travelers normalization
    travelers = dict(out.get("travelers") or {})
    if travelers:
        # Ensure children is a list
        children_val = travelers.get("children")
        if not isinstance(children_val, list):
            travelers["children"] = []
        # Coerce count to int when possible
        count_val = travelers.get("count")
        if isinstance(count_val, str):
            try:
                travelers["count"] = int(count_val)
            except Exception:
                pass
        elif isinstance(count_val, float):
            travelers["count"] = int(count_val)
        out["travelers"] = travelers

    # travel_style defaults (no-ops if present)
    travel_style = dict(out.get("travel_style") or {})
    out["travel_style"] = travel_style

    # arrays expected by schema
    out["preferences"] = _ensure_list(out.get("preferences"))
    out["special_occasions"] = _ensure_list(out.get("special_occasions"))

    # remove any parsing_metadata if model produced it; not part of the response schema
    out.pop("parsing_metadata", None)

    return out


