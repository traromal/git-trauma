from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

Mode = Literal["normal", "roast", "therapist", "corporate"]


class Emotion(str, Enum):
    CRISIS      = "crisis"
    PANIC       = "panic"
    FLOW        = "flow"
    FRUSTRATION = "frustration"
    RELIEF      = "relief"
    PRIDE       = "pride"
    GRIND       = "grind"
    DESPAIR     = "despair"
    NEUTRAL     = "neutral"


# ASCII symbols — no emoji
EMOTION_SYMBOL = {
    Emotion.CRISIS:      "[!!]",
    Emotion.PANIC:       "[!!]",
    Emotion.FLOW:        "[~~]",
    Emotion.FRUSTRATION: "[--]",
    Emotion.RELIEF:      "[ok]",
    Emotion.PRIDE:       "[^^]",
    Emotion.GRIND:       "[..]",
    Emotion.DESPAIR:     "[xx]",
    Emotion.NEUTRAL:     "[  ]",
}

EMOTION_COLOR = {
    Emotion.CRISIS:      "bold red",
    Emotion.PANIC:       "red",
    Emotion.FLOW:        "bold cyan",
    Emotion.FRUSTRATION: "yellow",
    Emotion.RELIEF:      "green",
    Emotion.PRIDE:       "bold green",
    Emotion.GRIND:       "dim white",
    Emotion.DESPAIR:     "bold magenta",
    Emotion.NEUTRAL:     "white",
}

EMOTION_BAR_CHAR = {
    Emotion.CRISIS:      "▓",
    Emotion.PANIC:       "▓",
    Emotion.FLOW:        "░",
    Emotion.FRUSTRATION: "▒",
    Emotion.RELIEF:      "░",
    Emotion.PRIDE:       "░",
    Emotion.GRIND:       "·",
    Emotion.DESPAIR:     "▓",
    Emotion.NEUTRAL:     "·",
}


@dataclass
class CommitSignals:
    hash: str
    short_hash: str
    author: str
    email: str
    timestamp: datetime
    message: str
    lines_added: int
    lines_deleted: int
    files_changed: int
    hour: int
    day_of_week: int
    time_gap_hours: float
    velocity: float
    is_revert: bool
    has_crisis_keywords: bool
    crisis_keywords_found: list[str] = field(default_factory=list)

    @property
    def churn(self) -> int:
        return self.lines_added + self.lines_deleted

    @property
    def net_change(self) -> int:
        return self.lines_added - self.lines_deleted

    @property
    def is_late_night(self) -> bool:
        return self.hour >= 23 or self.hour <= 4

    @property
    def is_weekend(self) -> bool:
        return self.day_of_week >= 5


@dataclass
class EmotionalCommit:
    signals: CommitSignals
    emotion: Emotion
    intensity: float
    narrative: str
    raw_signals_used: list[str] = field(default_factory=list)

    @property
    def symbol(self) -> str:
        return EMOTION_SYMBOL[self.emotion]

    @property
    def color(self) -> str:
        return EMOTION_COLOR[self.emotion]


@dataclass
class RepoAnalysis:
    repo_path: str
    repo_name: str
    commits: list[EmotionalCommit]
    generated_at: datetime

    @property
    def total_commits(self) -> int:
        return len(self.commits)

    @property
    def emotion_counts(self) -> dict[Emotion, int]:
        counts: dict[Emotion, int] = {}
        for ec in self.commits:
            counts[ec.emotion] = counts.get(ec.emotion, 0) + 1
        return counts

    @property
    def dominant_emotion(self) -> Emotion:
        counts = self.emotion_counts
        return max(counts, key=lambda e: counts[e]) if counts else Emotion.NEUTRAL

    @property
    def crisis_rate(self) -> float:
        if not self.commits:
            return 0.0
        bad = sum(1 for c in self.commits if c.emotion in (Emotion.CRISIS, Emotion.PANIC, Emotion.DESPAIR))
        return bad / len(self.commits)

    @property
    def worst_commit(self) -> EmotionalCommit | None:
        bad = [c for c in self.commits if c.emotion in (Emotion.CRISIS, Emotion.PANIC, Emotion.DESPAIR)]
        return max(bad, key=lambda c: c.intensity) if bad else None

    @property
    def best_commit(self) -> EmotionalCommit | None:
        good = [c for c in self.commits if c.emotion in (Emotion.FLOW, Emotion.PRIDE, Emotion.RELIEF)]
        return max(good, key=lambda c: c.intensity) if good else None
