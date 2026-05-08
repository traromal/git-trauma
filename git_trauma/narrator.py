from __future__ import annotations

import json
import os
from typing import Literal

from .models import CommitSignals, Emotion, EmotionalCommit, Mode

Provider = Literal["anthropic", "groq"]

_SYSTEM_PROMPTS: dict[str, str] = {
    "normal": """\
You are a dry, witty analyst reviewing a developer's git history.
Given commit signals, write ONE punchy sentence (max 15 words) describing the developer's state.
Be specific to the data. Deadpan humor. No fluff.
Respond JSON only: {"narrative": "...", "emotion": "crisis|panic|flow|frustration|relief|pride|grind|despair|neutral"}
""",

    "roast": """\
You are a savage, brutally honest roaster reviewing a developer's git commit.
You have NO mercy. You call out bad practices, desperate commits, and poor decisions with ruthless accuracy.
Use the actual data (time, lines deleted, message) to make it personal and specific.
Be savage but technically correct. No generic insults — attack the specific evidence.
One sentence, max 20 words. Brutal. Specific. Funny.
Respond JSON only: {"narrative": "...", "emotion": "crisis|panic|flow|frustration|relief|pride|grind|despair|neutral"}
""",

    "therapist": """\
You are an overly clinical psychotherapist writing DSM-style notes on a developer's git commit.
Use formal clinical language. Reference the data as "presenting symptoms".
Diagnose with made-up but plausible-sounding disorders. Recommend treatment.
One sentence, max 20 words. Deadpan clinical tone.
Respond JSON only: {"narrative": "...", "emotion": "crisis|panic|flow|frustration|relief|pride|grind|despair|neutral"}
""",

    "corporate": """\
You are a corporate consultant translating a developer's git commit into LinkedIn synergy-speak.
Use meaningless corporate buzzwords. Spin every crisis as a "growth opportunity".
Reference "stakeholders", "deliverables", "paradigm shifts", "synergy".
One sentence, max 20 words. Pure corporate nonsense that sounds profound.
Respond JSON only: {"narrative": "...", "emotion": "crisis|panic|flow|frustration|relief|pride|grind|despair|neutral"}
""",
}

_VALID_EMOTIONS  = {e.value for e in Emotion}
_GROQ_DEFAULT    = "llama-3.1-8b-instant"
_ANTHROPIC_DEFAULT = "claude-haiku-4-5-20251001"


def default_model(provider: Provider) -> str:
    return _GROQ_DEFAULT if provider == "groq" else _ANTHROPIC_DEFAULT


def narrate_batch(
    commits: list[EmotionalCommit],
    *,
    provider: Provider = "anthropic",
    api_key: str | None = None,
    model: str | None = None,
    mode: Mode = "normal",
) -> list[EmotionalCommit]:
    key = api_key or _resolve_key(provider)
    if not key:
        env = "GROQ_API_KEY" if provider == "groq" else "ANTHROPIC_API_KEY"
        raise RuntimeError(f"{env} not set. Use --no-llm for rule-based mode.")

    resolved_model  = model or default_model(provider)
    system_prompt   = _SYSTEM_PROMPTS.get(mode, _SYSTEM_PROMPTS["normal"])
    narrator        = _GroqNarrator(key, resolved_model, system_prompt) if provider == "groq" \
                      else _AnthropicNarrator(key, resolved_model, system_prompt)

    return [
        EmotionalCommit(
            signals=ec.signals,
            emotion=emotion,
            intensity=ec.intensity,
            narrative=narrative,
            raw_signals_used=ec.raw_signals_used,
        )
        for ec in commits
        for narrative, emotion in [narrator.narrate(ec)]
    ]


def _resolve_key(provider: Provider) -> str | None:
    return os.environ.get("GROQ_API_KEY" if provider == "groq" else "ANTHROPIC_API_KEY")


# ── providers ─────────────────────────────────────────────────────────────────

class _AnthropicNarrator:
    def __init__(self, api_key: str, model: str, system: str) -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model  = model
        self._system = system

    def narrate(self, ec: EmotionalCommit) -> tuple[str, Emotion]:
        try:
            resp = self._client.messages.create(
                model=self._model, max_tokens=120,
                system=self._system,
                messages=[{"role": "user", "content": _payload(ec)}],
            )
            return _parse(resp.content[0].text, ec)
        except Exception:
            return _fallback(ec), ec.emotion


class _GroqNarrator:
    def __init__(self, api_key: str, model: str, system: str) -> None:
        from groq import Groq
        self._client = Groq(api_key=api_key)
        self._model  = model
        self._system = system

    def narrate(self, ec: EmotionalCommit) -> tuple[str, Emotion]:
        try:
            resp = self._client.chat.completions.create(
                model=self._model, max_tokens=120,
                messages=[
                    {"role": "system", "content": self._system},
                    {"role": "user",   "content": _payload(ec)},
                ],
                response_format={"type": "json_object"},
            )
            return _parse(resp.choices[0].message.content, ec)
        except Exception:
            return _fallback(ec), ec.emotion


# ── shared ────────────────────────────────────────────────────────────────────

def _payload(ec: EmotionalCommit) -> str:
    s = ec.signals
    return json.dumps({
        "time":           f"{s.timestamp.strftime('%Y-%m-%d %H:%M')} (hour={s.hour})",
        "message":        s.message,
        "lines_added":    s.lines_added,
        "lines_deleted":  s.lines_deleted,
        "files_changed":  s.files_changed,
        "gap_hours":      s.time_gap_hours,
        "velocity":       s.velocity,
        "is_late_night":  s.is_late_night,
        "is_weekend":     s.is_weekend,
        "is_revert":      s.is_revert,
        "crisis_keywords": s.crisis_keywords_found,
        "rule_emotion":   ec.emotion.value,
        "signals":        ec.raw_signals_used,
    }, indent=2)


def _parse(raw: str, ec: EmotionalCommit) -> tuple[str, Emotion]:
    try:
        data       = json.loads(raw.strip())
        narrative  = data.get("narrative", "").strip()
        emotion_str = data.get("emotion", ec.emotion.value)
        emotion    = Emotion(emotion_str) if emotion_str in _VALID_EMOTIONS else ec.emotion
        return narrative or _fallback(ec), emotion
    except Exception:
        return _fallback(ec), ec.emotion


def _fallback(ec: EmotionalCommit) -> str:
    s = ec.signals
    return {
        Emotion.CRISIS:      f"Crisis at {s.hour:02d}:00. {s.lines_deleted} lines gone. No witnesses.",
        Emotion.PANIC:       f"{s.velocity:.0f} commits/hr. Classic panic spiral.",
        Emotion.FLOW:        f"+{s.lines_added} lines, clean head, good day.",
        Emotion.FRUSTRATION: f"Third attempt. Still not working. Classic.",
        Emotion.RELIEF:      "It works. Don't touch it.",
        Emotion.PRIDE:       f"+{s.lines_added} lines of something that might last.",
        Emotion.GRIND:       "Head down. Nothing exciting. Moving on.",
        Emotion.DESPAIR:     f"{s.time_gap_hours:.0f}h silence then {s.churn} lines. Reckoning.",
        Emotion.NEUTRAL:     "Commit made. World unchanged.",
    }.get(ec.emotion, "Status: unclear.")
