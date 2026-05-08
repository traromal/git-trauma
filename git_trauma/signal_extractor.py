from __future__ import annotations

from .models import CommitSignals, Emotion, EmotionalCommit


def classify(signals: CommitSignals) -> tuple[Emotion, float, list[str]]:
    """Rule-based emotion classification. Returns (emotion, intensity 0-1, reasons)."""
    score: dict[Emotion, float] = {e: 0.0 for e in Emotion}
    reasons: list[str] = []

    # --- CRISIS ---
    if signals.has_crisis_keywords:
        score[Emotion.CRISIS] += 0.5
        reasons.append(f"crisis keywords: {', '.join(signals.crisis_keywords_found)}")
    if signals.is_late_night and signals.lines_deleted > 100:
        score[Emotion.CRISIS] += 0.4
        reasons.append(f"late night ({signals.hour:02d}:xx) + {signals.lines_deleted} lines deleted")
    if signals.is_revert:
        score[Emotion.CRISIS] += 0.3
        score[Emotion.PANIC] += 0.2
        reasons.append("revert commit")

    # --- PANIC ---
    if signals.velocity > 8:
        score[Emotion.PANIC] += 0.5
        reasons.append(f"high velocity: {signals.velocity:.1f} commits/hr")
    if signals.lines_deleted > 500:
        score[Emotion.PANIC] += 0.3
        reasons.append(f"mass deletion: {signals.lines_deleted} lines")
    if signals.is_late_night and signals.velocity > 4:
        score[Emotion.PANIC] += 0.3
        reasons.append("rapid late-night commits")

    # --- DESPAIR ---
    if signals.time_gap_hours > 168 and signals.churn > 300:
        score[Emotion.DESPAIR] += 0.6
        reasons.append(f"1 week gap ({signals.time_gap_hours:.0f}h) then {signals.churn} lines changed")
    if signals.is_late_night and signals.has_crisis_keywords and signals.lines_deleted > signals.lines_added:
        score[Emotion.DESPAIR] += 0.4
        reasons.append("late-night crisis + net deletion")

    # --- FRUSTRATION ---
    if signals.lines_deleted > signals.lines_added * 2 and signals.lines_deleted > 50:
        score[Emotion.FRUSTRATION] += 0.4
        reasons.append(f"deleted {signals.lines_deleted} vs added {signals.lines_added}")
    msg_lower = signals.message.lower()
    if any(w in msg_lower for w in ["fix", "again", "still", "another"]):
        score[Emotion.FRUSTRATION] += 0.3
        reasons.append("repetitive fix language")
    if signals.is_weekend and signals.is_late_night:
        score[Emotion.FRUSTRATION] += 0.2
        reasons.append("weekend late-night work")

    # --- RELIEF ---
    if any(w in msg_lower for w in ["finally", "works", "working", "solved", "done", "fixed", "at last"]):
        score[Emotion.RELIEF] += 0.6
        reasons.append("relief language detected")
    if signals.time_gap_hours > 2 and signals.net_change > 0 and not signals.has_crisis_keywords:
        score[Emotion.RELIEF] += 0.2

    # --- FLOW ---
    if (
        not signals.is_late_night
        and not signals.has_crisis_keywords
        and 9 <= signals.hour <= 17
        and signals.lines_added > signals.lines_deleted
        and signals.lines_added > 20
        and signals.velocity < 6
    ):
        score[Emotion.FLOW] += 0.5
        reasons.append(f"daytime productive work, +{signals.lines_added} lines")
    if signals.time_gap_hours > 0.5 and signals.time_gap_hours < 4 and not signals.has_crisis_keywords:
        score[Emotion.FLOW] += 0.2

    # --- PRIDE ---
    if any(w in msg_lower for w in ["feat:", "feature", "implement", "add", "launch", "release", "ship"]):
        score[Emotion.PRIDE] += 0.4
        reasons.append("feature/release commit")
    if signals.lines_added > 200 and not signals.has_crisis_keywords and not signals.is_late_night:
        score[Emotion.PRIDE] += 0.3
        reasons.append(f"large feature addition: +{signals.lines_added} lines")

    # --- GRIND ---
    if signals.churn < 20 and not signals.has_crisis_keywords:
        score[Emotion.GRIND] += 0.3
        reasons.append("small incremental commit")
    if any(w in msg_lower for w in ["wip", "progress", "minor", "small", "tweak", "cleanup", "lint"]):
        score[Emotion.GRIND] += 0.3
        reasons.append("grind-type commit message")

    # pick winner
    best_emotion = max(score, key=lambda e: score[e])
    best_score = score[best_emotion]

    if best_score < 0.1:
        best_emotion = Emotion.NEUTRAL
        intensity = 0.1
    else:
        intensity = min(best_score, 1.0)

    return best_emotion, intensity, reasons


def extract(signals_list: list[CommitSignals]) -> list[EmotionalCommit]:
    results: list[EmotionalCommit] = []
    for s in signals_list:
        emotion, intensity, reasons = classify(s)
        results.append(EmotionalCommit(
            signals=s,
            emotion=emotion,
            intensity=intensity,
            narrative="",          # filled by narrator if LLM enabled
            raw_signals_used=reasons,
        ))
    return results
