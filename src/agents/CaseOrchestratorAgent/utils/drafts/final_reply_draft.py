from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.agents.CaseOrchestratorAgent.utils.actions.text import humanize_field


def strip_case_id_lines(text: str) -> str:
    lines = []
    for ln in (text or "").splitlines():
        if ln.strip().lower().startswith("case id:"):
            continue
        lines.append(ln)
    return "\n".join(lines).strip()


def build_option1_public_text(topic_keywords: Optional[List[str]]) -> str:
    topics = topic_keywords or []
    lines: List[str] = []

    if topics:
        lines.append(f"Regarding your question about: {', '.join(topics)}")
        lines.append("")

    tk = " ".join(t.lower() for t in topics)
    if "dynamic" in tk:
        lines += [
            "A dynamic tariff means the electricity price can change over time (often hourly), based on market prices.",
            "This can be cheaper at some hours and higher at others.",
            "",
            "Practical tips:",
            "- You can save money if you shift usage to cheaper hours.",
            "- A smart meter is often needed for correct hourly billing.",
        ]
    else:
        lines += [
            "Thanks for your message. We will share the relevant information with you shortly.",
        ]

    return "\n".join(lines).strip()


def build_option2_missing_info_text(action_specs: List[Dict[str, Any]]) -> str:
    blocked = [a for a in (action_specs or []) if a.get("action_status") == "blocked"]
    if not blocked:
        return ""

    lines: List[str] = []
    lines.append("To continue with your request, please reply with the following information:")

    for a in blocked:
        action_type = a.get("action_type") or "requested action"
        res = a.get("result") or {}
        reason = res.get("blocked_reason")

        if reason == "missing_entity":
            missing = res.get("missing") or []
            if missing:
                lines.append(f"- For {action_type}:")
                for m in missing:
                    lines.append(f"  - {humanize_field(m)}")

        elif reason == "low_confidence_intent":
            lines.append(f"- Please confirm what you want us to do for: {action_type}")

        else:
            lines.append(f"- {action_type}: we need more information")

    return "\n".join(lines).strip()


def build_option3_processing_text(action_specs: List[Dict[str, Any]], intents: List[Dict[str, Any]]) -> str:
    planned = [a for a in (action_specs or []) if a.get("action_status") == "planned"]

    lines: List[str] = []
    lines.append("Thanks for your message. We are looking into your request and will help you as soon as possible.")

    if planned:
        lines.append("")
        lines.append("What we will do now:")
        for a in planned:
            lines.append(f"- {a.get('action_type')}")

    return "\n".join(lines).strip()



def merge_old_and_new_customer_reply(old_customer_reply: str, new_customer_reply: str) -> str:
    separator = "====="
    old_text = strip_case_id_lines(old_customer_reply or "").strip()
    new_text = strip_case_id_lines(new_customer_reply or "").strip()

    parts = []
    if old_text:
        parts.append(old_text)

    if old_text and new_text:
        parts.append(separator)

    if new_text:
        parts.append(new_text)

    return "\n\n".join(parts).strip()