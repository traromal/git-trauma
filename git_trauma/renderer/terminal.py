from __future__ import annotations

import random
from collections import Counter

from rich.console import Console
from rich.text import Text

from ..models import Emotion, EmotionalCommit, Mode, RepoAnalysis

console = Console(highlight=False)

# ── design system ─────────────────────────────────────────────────────────────

INDENT  = "   "       # 3-space left margin — generous, calm
BOX_MAX = 76          # max box width
SECTION_W = 70        # max section content width

_ACCENT: dict[str, str] = {
    "normal":    "steel_blue1",
    "roast":     "indian_red1",
    "therapist": "medium_purple1",
    "corporate": "dark_goldenrod",
}

_EC: dict[Emotion, str] = {
    Emotion.CRISIS:      "bold red",
    Emotion.PANIC:       "red",
    Emotion.FLOW:        "cyan",
    Emotion.FRUSTRATION: "yellow",
    Emotion.RELIEF:      "green",
    Emotion.PRIDE:       "bold green",
    Emotion.GRIND:       "grey50",
    Emotion.DESPAIR:     "magenta",
    Emotion.NEUTRAL:     "grey74",
}

_SEVERITY: dict[Emotion, int] = {
    Emotion.CRISIS:      5,
    Emotion.PANIC:       4,
    Emotion.DESPAIR:     4,
    Emotion.FRUSTRATION: 3,
    Emotion.GRIND:       2,
    Emotion.NEUTRAL:     2,
    Emotion.RELIEF:      1,
    Emotion.FLOW:        0,
    Emotion.PRIDE:       0,
}

_SPARK = "▁▂▃▄▅▆▇█"

_TAGLINES: dict[str, list[str]] = {
    "normal": [
        "a calm read of your git history",
        "what your commits say when you're not listening",
        "the psychological profile hidden in your diffs",
        "emotional forensics, gently performed",
    ],
    "roast": [
        "your code crimes, read back to you",
        "no mercy. no survivors. soft lighting.",
        "the code review you deserved but never got",
    ],
    "therapist": [
        "and how did that commit make you feel",
        "presenting symptoms — your git log",
        "a clinical read of your development journey",
    ],
    "corporate": [
        "your commit history, as a strategic asset",
        "synergising your git narrative for impact",
    ],
}

_BLESSING: dict[str, str] = {
    "normal":    "may your next commit be kind",
    "roast":     "now go touch grass",
    "therapist": "session adjourned  ·  same time next week",
    "corporate": "circle back when you have bandwidth",
}


# ── public entry ──────────────────────────────────────────────────────────────

def render(analysis: RepoAnalysis, *, compact: bool = False, mode: Mode = "normal") -> None:
    accent = _ACCENT.get(mode, "steel_blue1")
    _hero(analysis, mode, accent)
    _breath(accent)
    _overview(analysis, accent)
    _highlights(analysis, accent)
    _timeline(analysis.commits, compact=compact, accent=accent)
    _arc(analysis.commits, accent)
    _assessment(analysis, mode, accent)
    _closing(analysis, mode, accent)


# ── primitives ────────────────────────────────────────────────────────────────

def _viewport() -> int:
    return min(console.width, BOX_MAX + len(INDENT) * 2)


def _section_w() -> int:
    return min(console.width - len(INDENT) * 2, SECTION_W)


def _centered(text: Text) -> Text:
    """Wrap a Text in a line padded to center within viewport."""
    vp  = console.width
    pad = max(0, (vp - len(text.plain)) // 2)
    out = Text(" " * pad)
    out.append_text(text)
    return out


def _section(title: str, accent: str) -> None:
    """`◦  title  ─────────────` left-aligned at INDENT."""
    console.print()
    width = _section_w()
    t = Text(INDENT)
    t.append("◦  ", style=f"dim {accent}")
    t.append(title, style=accent)
    t.append("  ", style="dim")
    rule_len = max(0, width - 5 - len(title))
    t.append("─" * rule_len, style=f"dim {accent}")
    console.print(t)
    console.print()


def _breath(accent: str) -> None:
    """Three soft centered dots — a visual exhale between major moments."""
    t = Text("·  ·  ·", style=f"dim {accent}")
    console.print()
    console.print(_centered(t))
    console.print()


def _card(title: str | None, inner_lines: list[Text], accent: str,
          *, title_color: str | None = None) -> None:
    """
    Rounded box. Optional floating title in top border.

      ╭ title ──────────╮
      │  inner          │
      ╰─────────────────╯
    """
    box_w   = min(console.width - len(INDENT) * 2, BOX_MAX)
    inner_w = box_w - 4         # │  ...  │  (1 + 1 padding) × 2

    if title:
        label  = f" {title} "
        fill_n = max(0, box_w - 2 - len(label))
        top    = Text(INDENT)
        top.append("╭", style=f"dim {accent}")
        top.append(label, style=title_color or f"{accent}")
        top.append("─" * fill_n, style=f"dim {accent}")
        top.append("╮", style=f"dim {accent}")
    else:
        top = Text(INDENT + "╭" + "─" * (box_w - 2) + "╮", style=f"dim {accent}")

    bottom = Text(INDENT + "╰" + "─" * (box_w - 2) + "╯", style=f"dim {accent}")
    side   = Text("│", style=f"dim {accent}")

    console.print(top)
    for inner in inner_lines:
        used = len(inner.plain)
        pad  = max(0, inner_w - used)
        row  = Text(INDENT)
        row.append_text(side)
        row.append("  ")
        row.append_text(inner)
        row.append(" " * pad)
        row.append("  ")
        row.append_text(side)
        console.print(row)
    console.print(bottom)


# ── hero ──────────────────────────────────────────────────────────────────────

def _hero(analysis: RepoAnalysis, mode: Mode, accent: str) -> None:
    tagline = random.choice(_TAGLINES.get(mode, _TAGLINES["normal"]))

    console.print()
    console.print(_centered(Text("·  ·  ·", style=f"dim {accent}")))
    console.print()

    # logo
    logo = Text()
    logo.append("git", style=f"dim {accent}")
    logo.append("-",   style="dim")
    logo.append("trauma", style=f"bold {accent}")
    if mode != "normal":
        logo.append("  ·  ", style="dim")
        logo.append(mode, style=f"dim {accent}")
    console.print(_centered(logo))

    console.print()
    console.print(_centered(Text(tagline, style="dim italic")))

    console.print()
    meta = Text()
    meta.append(analysis.repo_name, style="white")
    meta.append("   ·   ", style=f"dim {accent}")
    meta.append(f"{analysis.total_commits} commits", style="dim")
    meta.append("   ·   ", style=f"dim {accent}")
    meta.append(analysis.generated_at.strftime("%b %d, %Y"), style="dim")
    console.print(_centered(meta))


# ── overview ──────────────────────────────────────────────────────────────────

def _overview(analysis: RepoAnalysis, accent: str) -> None:
    commits    = analysis.commits
    total      = len(commits) or 1
    dom        = analysis.dominant_emotion
    crisis_pct = analysis.crisis_rate * 100
    crisis_col = "red" if crisis_pct > 30 else "yellow" if crisis_pct > 15 else "green"
    added      = sum(c.signals.lines_added   for c in commits)
    deleted    = sum(c.signals.lines_deleted for c in commits)
    late_n     = sum(1 for c in commits if c.signals.is_late_night)
    wknd_n     = sum(1 for c in commits if c.signals.is_weekend)
    rev_n      = sum(1 for c in commits if c.signals.is_revert)
    max_vel    = max((c.signals.velocity for c in commits), default=0)
    net        = added - deleted
    crisis_lbl = "critical" if crisis_pct > 40 else "elevated" if crisis_pct > 20 else "moderate" if crisis_pct > 5 else "low"

    _section("overview", accent)

    L, V, G = 16, 18, 4

    def _row(lbl1: str, val1: Text, lbl2: str, val2: Text) -> None:
        line = Text(INDENT + "  ")
        line.append(lbl1.ljust(L), style="dim")
        line.append_text(val1)
        line.append(" " * max(0, V - len(val1.plain) + G))
        line.append(lbl2.ljust(L), style="dim")
        line.append_text(val2)
        console.print(line)

    dom_v = Text(); dom_v.append("● ", style=_EC[dom]); dom_v.append(dom.value, style=_EC[dom])
    cr_v  = Text(); cr_v.append(f"{crisis_pct:.0f}%", style=crisis_col); cr_v.append(f"  {crisis_lbl}", style="dim")
    net_v = Text(f"{net:+,}", style="green" if net >= 0 else "red")
    vel_v = Text(f"{max_vel:.1f} / hr", style="white")

    _row("dominant mood", dom_v,                                                   "crisis rate",   cr_v)
    _row("lines added",   Text(f"+{added:,}",  style="green"),                     "lines deleted", Text(f"−{deleted:,}", style="red"))
    _row("net change",    net_v,                                                    "peak velocity", vel_v)
    _row("late-night",    Text(f"{late_n}  ({late_n/total*100:.0f}%)",  style="yellow" if late_n  else "grey50"),
         "weekends",      Text(f"{wknd_n}  ({wknd_n/total*100:.0f}%)", style="yellow" if wknd_n  else "grey50"))
    if rev_n:
        _row("reverts",   Text(str(rev_n), style="yellow"),                         "",              Text(""))


# ── highlights ────────────────────────────────────────────────────────────────

def _highlights(analysis: RepoAnalysis, accent: str) -> None:
    worst = analysis.worst_commit
    best  = analysis.best_commit
    if not worst and not best:
        return

    _section("highlights", accent)

    def _hl_card(title: str, sym: str, sym_color: str, ec: EmotionalCommit) -> None:
        s   = ec.signals
        ts  = s.timestamp.strftime("%b %d  %H:%M")
        col = _EC[ec.emotion]

        # line 1 — emotion + ts + hash + author
        l1 = Text()
        l1.append(sym + " ", style=sym_color)
        l1.append(f"{ec.emotion.value:<13}", style=col)
        l1.append("   ")
        l1.append(ts, style="dim")
        l1.append("   ")
        l1.append(s.short_hash, style="dim bright_blue")
        l1.append(f"   {s.author}", style="dim")

        # line 2 — message
        msg = s.message.replace('"', "'")
        # truncate to fit card
        max_msg = BOX_MAX - 8
        if len(msg) > max_msg:
            msg = msg[:max_msg - 1] + "…"
        l2 = Text(f'"{msg}"', style="italic white")

        # line 3 — diff + flags
        l3 = Text()
        l3.append(f"+{s.lines_added}",  style="green")
        l3.append("  ")
        l3.append(f"−{s.lines_deleted}", style="red")
        l3.append("   ·   ")
        l3.append(f"{s.files_changed} file{'s' if s.files_changed != 1 else ''}", style="dim")
        if s.is_late_night: l3.append("   ·   late-night", style="dim yellow")
        if s.is_weekend:    l3.append("   ·   weekend",    style="dim yellow")
        if s.velocity > 6:  l3.append(f"   ·   {s.velocity:.0f}/hr", style="dim red")

        _card(title, [l1, l2, l3], accent, title_color=sym_color)
        console.print()

    if best:
        _hl_card("finest",  "✦", "bold green", best)
    if worst:
        _hl_card("darkest", "◐", "bold red",   worst)


# ── timeline (vertical river) ─────────────────────────────────────────────────

def _timeline(commits: list[EmotionalCommit], *, compact: bool, accent: str) -> None:
    _section("timeline", accent)

    if compact:
        _compact_timeline(commits, accent)
        return

    river_col = f"dim {accent}"

    # opening drop
    console.print(Text(INDENT + "│", style=river_col))

    for i, ec in enumerate(commits):
        s   = ec.signals
        col = _EC[ec.emotion]
        ts  = s.timestamp.strftime("%b %d  %H:%M")

        # node row — colored ● dot, then meta
        node = Text(INDENT)
        node.append("●", style=col)
        node.append("─── ", style=river_col)
        node.append(ts, style="dim")
        node.append("    ")
        node.append(f"{ec.emotion.value:<13}", style=col)
        node.append("   ")
        node.append(s.short_hash, style="dim bright_blue")
        node.append(f"   {s.author}", style="dim")
        if s.is_late_night: node.append("   ·  late-night", style="dim yellow")
        if s.is_weekend:    node.append("   ·  weekend",    style="dim yellow")
        if s.velocity > 6:  node.append(f"   ·  {s.velocity:.0f}/hr", style="dim red")
        if s.is_revert:     node.append("   ·  revert",     style="dim red")
        console.print(node)

        # body rows — connected by │
        msg = s.message.replace('"', "'")
        body1 = Text(INDENT)
        body1.append("│", style=river_col)
        body1.append("    ")
        body1.append(f'"{msg}"', style="white")
        console.print(body1)

        body2 = Text(INDENT)
        body2.append("│", style=river_col)
        body2.append("    ")
        body2.append(f"+{s.lines_added}", style="green")
        body2.append("  ")
        body2.append(f"−{s.lines_deleted}", style="red")
        body2.append("   ·   ")
        body2.append(f"{s.files_changed} file{'s' if s.files_changed != 1 else ''}", style="dim")
        console.print(body2)

        if ec.narrative:
            narr = Text(INDENT)
            narr.append("│", style=river_col)
            narr.append("    ")
            narr.append(ec.narrative, style=f"italic {col}")
            console.print(narr)

        # connector to next
        if i < len(commits) - 1:
            console.print(Text(INDENT + "│", style=river_col))

    # closing drop
    console.print(Text(INDENT + "╵", style=river_col))


def _compact_timeline(commits: list[EmotionalCommit], accent: str) -> None:
    river_col = f"dim {accent}"
    console.print(Text(INDENT + "│", style=river_col))
    for ec in commits:
        s   = ec.signals
        col = _EC[ec.emotion]
        line = Text(INDENT)
        line.append("●", style=col)
        line.append("── ", style=river_col)
        line.append(s.timestamp.strftime("%b %d  %H:%M"), style="dim")
        line.append("   ")
        line.append(f"{ec.emotion.value:<13}", style=col)
        line.append("   ")
        line.append(s.short_hash, style="dim bright_blue")
        line.append("   ")
        line.append(f"+{s.lines_added}", style="green")
        line.append(" ")
        line.append(f"−{s.lines_deleted}", style="red")
        line.append("   ")
        msg = s.message.replace('"', "'")
        avail = max(20, console.width - len(line.plain) - 4)
        line.append(msg[:avail], style="white")
        console.print(line)
    console.print(Text(INDENT + "╵", style=river_col))


# ── arc ───────────────────────────────────────────────────────────────────────

def _arc(commits: list[EmotionalCommit], accent: str) -> None:
    if len(commits) < 3:
        return

    _section("arc", accent)

    # full-width sparkline (oldest → newest, so reverse since commits[0] is newest)
    series      = list(reversed(commits))
    width       = min(console.width - len(INDENT) * 2, max(len(series), 56))
    chunk_size  = max(1, len(series) // width)
    buckets: list[float] = []
    for i in range(0, len(series), chunk_size):
        chunk = series[i:i + chunk_size]
        buckets.append(sum(_SEVERITY[c.emotion] for c in chunk) / len(chunk))

    max_val = max(buckets) or 1
    spark   = Text(INDENT)
    for val in buckets:
        idx  = int((val / max_val) * (len(_SPARK) - 1))
        char = _SPARK[idx]
        if val >= 4:
            spark.append(char, style="bold red")
        elif val >= 3:
            spark.append(char, style="yellow")
        elif val <= 1:
            spark.append(char, style=accent)
        else:
            spark.append(char, style="grey50")

    console.print(spark)

    if len(commits) >= 2:
        oldest = commits[-1].signals.timestamp.strftime("%b %d")
        newest = commits[0].signals.timestamp.strftime("%b %d")
        pad    = max(2, len(buckets) - len(oldest) - len(newest))
        legend = Text(INDENT)
        legend.append(oldest, style="dim")
        legend.append(" " * pad)
        legend.append(newest, style="dim")
        console.print(legend)
    console.print()

    # distribution — soft rounded bars
    counts = Counter(ec.emotion for ec in commits)
    total  = len(commits)
    bar_w  = 28

    for emotion in sorted(counts, key=lambda e: counts[e], reverse=True):
        pct    = counts[emotion] / total
        filled = round(pct * bar_w)
        empty  = bar_w - filled
        col    = _EC[emotion]
        row    = Text(INDENT + "  ")
        row.append("● ", style=col)
        row.append(f"{emotion.value:<13}", style=col)
        row.append("  ")
        row.append("▰" * filled, style=col)
        row.append("▱" * empty,  style="grey30")
        row.append(f"   {pct*100:>4.0f}%   {counts[emotion]:>3}", style="dim")
        console.print(row)


# ── assessment ────────────────────────────────────────────────────────────────

_OBS: dict[str, dict[str, str]] = {
    "normal": {
        "late_high":   "Over {late_pct:.0f}% of commits happened after midnight. The bugs don't improve at 3am.",
        "late_mid":    "{late_pct:.0f}% late-night commit rate. Sleep is not optional.",
        "late_low":    "Healthy work hours. Consistent daytime cadence — the kind of discipline that compounds.",
        "wknd_high":   "Weekends make up {wknd_pct:.0f}% of commits. The codebase doesn't know what a Saturday is.",
        "wknd_mid":    "Some weekend work. The boundary exists but it's porous.",
        "crisis_high": "{crisis_pct:.0f}% of commits carry distress signals. This history has real weight.",
        "crisis_mid":  "{crisis_pct:.0f}% crisis rate. Not catastrophic — but there's a pattern here.",
        "crisis_low":  "{crisis_pct:.0f}% crisis rate. A few hard days. All survived.",
        "crisis_zero": "No crisis commits found. Either very disciplined or very selective with history.",
        "revert_high": "{revert_pct:.0f}% revert rate. The undo button and this developer have history.",
        "flow_high":   "Frequent flow-state commits. Stretches of deep, uninterrupted work — worth protecting.",
        "pride_high":  "{pride_pct:.0f}% feature commits. Mostly building, not firefighting. Positive signal.",
        "despair":     "Despair-state commits present. Long silences followed by large changes.",
    },
    "roast": {
        "late_high":   "{late_pct:.0f}% of this codebase was assembled after midnight. It shows.",
        "late_mid":    "Still pushing code past midnight. The heroic feeling fades. The bugs remain.",
        "late_low":    "Works normal hours. Either disciplined or not passionate enough to embarrass yourself at 3am.",
        "wknd_high":   "{wknd_pct:.0f}% weekend commits. Your hobbies are apparently just more debugging.",
        "wknd_mid":    "Weekend commits logged. Your days off are your codebase's days on.",
        "crisis_high": "{crisis_pct:.0f}% crisis rate. Not a git log — a trauma journal with version control.",
        "crisis_mid":  "{crisis_pct:.0f}% in distress. 'Fine' is working overtime here.",
        "crisis_low":  "{crisis_pct:.0f}% crisis commits. Competent enough to survive their own mistakes.",
        "crisis_zero": "Zero crisis commits. Nobody is this calm. Something is squashed, hidden, or both.",
        "revert_high": "Reverted {revert_pct:.0f}% of commits. Confidence and correctness are not the same thing.",
        "flow_high":   "Frequent flow states. Must be nice. Not everyone gets to concentrate.",
        "pride_high":  "{pride_pct:.0f}% feature commits. Mostly adds things. Whether those things were needed is another question.",
        "despair":     "Despair commits on record. Long silence, large mess, repeat.",
    },
    "therapist": {
        "late_high":   "Nocturnal work patterns account for {late_pct:.0f}% of sessions. Consistent with delayed sleep phase disorder.",
        "late_mid":    "Intermittent nocturnal commits. Circadian dysregulation under deadline pressure.",
        "late_low":    "Diurnal commit schedule. Healthy temporal boundaries. Strong prognostic indicator.",
        "wknd_high":   "Weekend commits at {wknd_pct:.0f}%. Classic work-identity enmeshment. Boundaries: absent.",
        "wknd_mid":    "Occasional weekend work. Ambivalence between rest and compulsion.",
        "crisis_high": "{crisis_pct:.0f}% acute distress events. Recurrent crisis episodes. Immediate intervention recommended.",
        "crisis_mid":  "{crisis_pct:.0f}% distress markers. Subclinical pattern. Functional but symptomatic.",
        "crisis_low":  "{crisis_pct:.0f}% crisis rate. Residual stress within manageable range. Monitoring advised.",
        "crisis_zero": "No distress markers. May indicate genuine regulation — or suppression. Further analysis warranted.",
        "revert_high": "Compulsive undoing behaviour ({revert_pct:.0f}%). Classic anxiety-driven correction loop.",
        "flow_high":   "Frequent flow states. High intrinsic motivation. Protective factor against burnout.",
        "pride_high":  "Feature-dominant profile. Strong creative drive. Monitor for perfectionism.",
        "despair":     "Despair episodes present. Long-latency, high-churn events consistent with avoidant patterns.",
    },
    "corporate": {
        "late_high":   "Extended delivery windows ({late_pct:.0f}% off-hours commits) demonstrate exceptional commitment to sprint continuity.",
        "late_mid":    "Off-hours delivery cadence signals strong ownership and proactive value creation.",
        "late_low":    "Core-hours delivery model. Consistent, predictable output. High operational stability.",
        "wknd_high":   "Weekend velocity contributions ({wknd_pct:.0f}%) reflect a passion-led delivery culture.",
        "wknd_mid":    "Selective weekend sprinting. Flexible bandwidth allocation to key deliverables.",
        "crisis_high": "{crisis_pct:.0f}% rapid-response commits. Robust incident ownership and proactive posture.",
        "crisis_mid":  "{crisis_pct:.0f}% high-urgency commits. Strong bias for action. Incident management maturity evident.",
        "crisis_low":  "Low unplanned incident rate ({crisis_pct:.0f}%). Stable delivery. Strong risk governance.",
        "crisis_zero": "Zero incident-driven commits. Exceptional delivery predictability. SLA alignment: outstanding.",
        "revert_high": "Rollback operations ({revert_pct:.0f}%) reflect quality-gate discipline and release integrity.",
        "flow_high":   "Consistent deep-work delivery windows. High-output sprint capacity.",
        "pride_high":  "{pride_pct:.0f}% feature velocity. Positive roadmap contribution. Product-aligned execution.",
        "despair":     "High-latency, high-volume delivery events suggest context-switching challenges requiring realignment.",
    },
}


def _assessment(analysis: RepoAnalysis, mode: Mode, accent: str) -> None:
    commits     = analysis.commits
    total       = len(commits) or 1
    crisis_pct  = analysis.crisis_rate * 100
    late_pct    = sum(1 for c in commits if c.signals.is_late_night) / total * 100
    wknd_pct    = sum(1 for c in commits if c.signals.is_weekend)    / total * 100
    revert_pct  = sum(1 for c in commits if c.signals.is_revert)     / total * 100
    flow_pct    = sum(1 for c in commits if c.emotion == Emotion.FLOW)   / total * 100
    pride_pct   = sum(1 for c in commits if c.emotion == Emotion.PRIDE)  / total * 100
    has_despair = any(c.emotion == Emotion.DESPAIR for c in commits)

    obs = _OBS.get(mode, _OBS["normal"])
    ctx = dict(late_pct=late_pct, wknd_pct=wknd_pct, crisis_pct=crisis_pct,
               revert_pct=revert_pct, flow_pct=flow_pct, pride_pct=pride_pct)

    lines: list[str] = []
    lines.append((obs["late_high"] if late_pct > 40 else obs["late_mid"] if late_pct > 20 else obs["late_low"]).format(**ctx))
    if wknd_pct > 25:
        lines.append(obs["wknd_high"].format(**ctx))
    elif wknd_pct > 10:
        lines.append(obs["wknd_mid"].format(**ctx))
    lines.append((obs["crisis_high"] if crisis_pct > 40 else obs["crisis_mid"] if crisis_pct > 20 else obs["crisis_low"] if crisis_pct > 5 else obs["crisis_zero"]).format(**ctx))
    if revert_pct > 10:
        lines.append(obs["revert_high"].format(**ctx))
    if flow_pct > 20:
        lines.append(obs["flow_high"].format(**ctx))
    if pride_pct > 35:
        lines.append(obs["pride_high"].format(**ctx))
    if has_despair:
        lines.append(obs["despair"].format(**ctx))

    _section("assessment", accent)
    for line in lines:
        row = Text(INDENT + "  ")
        row.append("▸ ", style=f"dim {accent}")
        row.append(line, style="white")
        console.print(row)


# ── closing ───────────────────────────────────────────────────────────────────

_VERDICTS: dict[str, list[tuple[float, str, str]]] = {
    "normal": [
        (0.5,  "critical condition",     "this repository has been through a lot. it shows."),
        (0.35, "significant turbulence", "the log tells a story of real struggle — and survival."),
        (0.2,  "moderate distress",      "some hard days in here. all apparently resolved."),
        (0.05, "mostly healthy",         "a few scars. nothing that didn't heal."),
        (0.0,  "remarkably composed",    "either very skilled, very calm, or very selective with history."),
    ],
    "roast": [
        (0.5,  "a disaster with commits",  "not a codebase. a crime scene with version control."),
        (0.35, "barely holding together",  "duct tape and hope. mostly hope."),
        (0.2,  "mediocre, with ambition",  "could be worse. has been worse. probably will be."),
        (0.05, "fine, i suppose",          "annoyingly functional. boringly adequate."),
        (0.0,  "suspiciously clean",       "nobody commits this calmly. something is being concealed."),
    ],
    "therapist": [
        (0.5,  "acute crisis state",      "immediate therapeutic intervention strongly recommended."),
        (0.35, "chronic stress pattern",  "maladaptive coping strategies present across the timeline."),
        (0.2,  "subclinical distress",    "functional but symptomatic. continued monitoring warranted."),
        (0.05, "within normal range",     "healthy coping indicators. mild residual stress markers."),
        (0.0,  "well-regulated",          "emotional equilibrium maintained. terminating sessions."),
    ],
    "corporate": [
        (0.5,  "high-risk delivery profile",  "immediate process improvement initiative required."),
        (0.35, "elevated risk posture",       "velocity recalibration and retrospective alignment recommended."),
        (0.2,  "improvement opportunity",     "strong foundation with identified growth areas."),
        (0.05, "meets expectations",          "consistent delivery. well-aligned with team okrs."),
        (0.0,  "exceeds expectations",        "exceptional cadence. promotion-track velocity."),
    ],
}


def _closing(analysis: RepoAnalysis, mode: Mode, accent: str) -> None:
    rate     = analysis.crisis_rate
    verdicts = _VERDICTS.get(mode, _VERDICTS["normal"])
    label, detail = next((l, d) for threshold, l, d in verdicts if rate >= threshold)

    console.print()
    console.print()

    # centered verdict
    verdict = Text()
    verdict.append(label, style=f"bold {accent}")
    console.print(_centered(verdict))

    detail_t = Text(detail, style="dim italic")
    console.print(_centered(detail_t))

    console.print()
    console.print()

    # waves
    waves = Text()
    for i in range(9):
        waves.append("～", style=f"dim {accent}")
        if i < 8:
            waves.append("  ", style="dim")
    console.print(_centered(waves))

    console.print()

    # blessing
    blessing = _BLESSING.get(mode, _BLESSING["normal"])
    bless    = Text(blessing, style=f"italic {accent}")
    console.print(_centered(bless))

    console.print()
    console.print(_centered(Text("·  ·  ·", style=f"dim {accent}")))
    console.print()
