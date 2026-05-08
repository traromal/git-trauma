from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import git
from git import Repo, InvalidGitRepositoryError

from .models import CommitSignals


class GitParseError(Exception):
    pass


def find_repo(path: str | Path = ".") -> Repo:
    try:
        return Repo(str(path), search_parent_directories=True)
    except InvalidGitRepositoryError:
        raise GitParseError(f"No git repository found at or above: {path}")


def parse_commits(
    repo: Repo,
    *,
    branch: str | None = None,
    author: str | None = None,
    limit: int | None = None,
    since: datetime | None = None,
) -> list[CommitSignals]:
    rev = branch or repo.active_branch.name

    kwargs: dict = {"max_count": limit} if limit else {}
    if since:
        kwargs["after"] = since.strftime("%Y-%m-%d")

    try:
        commits = list(repo.iter_commits(rev, **kwargs))
    except git.GitCommandError as e:
        raise GitParseError(f"Failed to read commits: {e}")

    if author:
        author_lower = author.lower()
        commits = [
            c for c in commits
            if author_lower in c.author.name.lower() or author_lower in c.author.email.lower()
        ]

    if not commits:
        raise GitParseError("No commits found matching your filters.")

    return _build_signals(commits)


def _build_signals(commits: list) -> list[CommitSignals]:
    signals: list[CommitSignals] = []

    # commits are newest-first from gitpython; reverse for chronological gap calc
    chronological = list(reversed(commits))
    timestamps = [_to_utc(c.authored_datetime) for c in chronological]

    # rolling window: commits per hour (2h window)
    velocities = _compute_velocities(timestamps)

    for i, commit in enumerate(chronological):
        ts = timestamps[i]
        prev_ts = timestamps[i - 1] if i > 0 else None
        gap_hours = (ts - prev_ts).total_seconds() / 3600 if prev_ts else 0.0

        stats = commit.stats.total
        lines_added   = stats.get("insertions", 0)
        lines_deleted = stats.get("deletions", 0)
        files_changed = stats.get("files", 0)

        msg = commit.message.strip()
        msg_lower = msg.lower()

        crisis_words = _find_crisis_keywords(msg_lower)

        signals.append(CommitSignals(
            hash=commit.hexsha,
            short_hash=commit.hexsha[:7],
            author=commit.author.name,
            email=commit.author.email,
            timestamp=ts,
            message=msg.split("\n")[0][:120],  # first line, capped
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            files_changed=files_changed,
            hour=ts.hour,
            day_of_week=ts.weekday(),
            time_gap_hours=round(gap_hours, 2),
            velocity=velocities[i],
            is_revert="revert" in msg_lower,
            has_crisis_keywords=bool(crisis_words),
            crisis_keywords_found=crisis_words,
        ))

    # return newest-first (user expects this)
    return list(reversed(signals))


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_velocities(timestamps: list[datetime]) -> list[float]:
    window_hours = 2.0
    velocities: list[float] = []
    for i, ts in enumerate(timestamps):
        count = sum(
            1 for t in timestamps
            if 0 <= (ts - t).total_seconds() / 3600 <= window_hours
        )
        velocities.append(round(count / window_hours, 2))
    return velocities


_CRISIS_KEYWORDS = [
    "please", "wtf", "why", "broken", "hate", "fuck", "shit",
    "damn", "argh", "ugh", "help", "not working", "doesn't work",
    "wont work", "won't work", "still broken", "fix again", "revert",
    "disaster", "horrible", "terrible", "nightmare", "kill me",
    "i give up", "no idea", "confused", "lost", "panic",
]


def _find_crisis_keywords(msg_lower: str) -> list[str]:
    return [kw for kw in _CRISIS_KEYWORDS if kw in msg_lower]
