from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# Force UTF-8 on Windows so emojis render correctly
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from typing import Annotated, Optional

import typer
from typer import Context
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from . import __version__
from .git_parser import GitParseError, find_repo, parse_commits
from .models import RepoAnalysis
from .narrator import narrate_batch
from .signal_extractor import extract
from .renderer import terminal as term_renderer
from .renderer import web as web_renderer

load_dotenv()

app = typer.Typer(
    name="git-trauma",
    help="Emotional analysis of your git history.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=False,
    invoke_without_command=True,
)

console = Console(highlight=False)
err     = Console(stderr=True, highlight=False)


# ── helpers ───────────────────────────────────────────────────────────────────

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"git-trauma {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[Optional[bool], typer.Option("--version", "-V", callback=_version_callback, is_eager=True, help="Show version")] = None,
) -> None:
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


def _abort(msg: str) -> None:
    err.print(f"[bold red]Error:[/bold red] {msg}")
    raise typer.Exit(code=1)


def _build_analysis(
    repo_path: Path,
    *,
    branch: str | None,
    author: str | None,
    limit: int | None,
    since: datetime | None,
    no_llm: bool,
    provider: str,
    api_key: str | None,
    model: str | None,
    mode: str = "normal",
) -> RepoAnalysis:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Parsing git history…", total=None)

        try:
            repo = find_repo(repo_path)
        except GitParseError as e:
            _abort(str(e))

        repo_name = Path(repo.working_dir).name

        progress.update(task, description="Extracting commits…")
        try:
            signals = parse_commits(
                repo,
                branch=branch,
                author=author,
                limit=limit,
                since=since,
            )
        except GitParseError as e:
            _abort(str(e))

        progress.update(task, description=f"Classifying {len(signals)} commits…")
        commits = extract(signals)

        if not no_llm:
            _env = "GROQ_API_KEY" if provider == "groq" else "ANTHROPIC_API_KEY"
            key  = api_key or os.environ.get(_env)
            if key:
                label = "Groq" if provider == "groq" else "Claude"
                progress.update(task, description=f"Generating narratives via {label}…")
                try:
                    commits = narrate_batch(commits, provider=provider, api_key=key, model=model or None, mode=mode)
                except RuntimeError as e:
                    err.print(f"[yellow]Warning:[/yellow] LLM narration failed: {e}")
            else:
                err.print(
                    f"[yellow]Tip:[/yellow] Set {_env} for AI-generated narratives. "
                    "Running in rule-based mode."
                )

        return RepoAnalysis(
            repo_path=str(repo.working_dir),
            repo_name=repo_name,
            commits=commits,
            generated_at=datetime.now(timezone.utc),
        )


# ── main command ──────────────────────────────────────────────────────────────

@app.command()
def analyze(
    path: Annotated[Path, typer.Argument(help="Path to git repo")] = Path("."),
    branch: Annotated[Optional[str], typer.Option("--branch", "-b", help="Branch to analyse")] = None,
    author: Annotated[Optional[str], typer.Option("--author", "-a", help="Filter by author name/email")] = None,
    limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="Max commits to analyse")] = 200,
    since: Annotated[Optional[str], typer.Option("--since", "-s", help="Since date (YYYY-MM-DD)")] = None,
    no_llm: Annotated[bool, typer.Option("--no-llm", help="Skip LLM narration (faster, free)")] = False,
    provider: Annotated[str, typer.Option("--provider", "-p", help="LLM provider: anthropic or groq")] = "anthropic",
    api_key: Annotated[Optional[str], typer.Option("--api-key", help="API key (overrides env var)")] = None,
    model: Annotated[Optional[str], typer.Option("--model", help="Model override (default: haiku / llama-3.1-8b-instant)")] = None,
    mode: Annotated[str, typer.Option("--mode", "-m", help="Output mode: normal | roast | therapist | corporate")] = "normal",
    web: Annotated[bool, typer.Option("--web", "-w", help="Open interactive HTML report in browser")] = False,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Save HTML report to file")] = None,
    compact: Annotated[bool, typer.Option("--compact", "-c", help="Compact table view")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Output raw JSON")] = False,
    version: Annotated[Optional[bool], typer.Option("--version", callback=_version_callback, is_eager=True)] = None,
) -> None:
    """
    Analyse the emotional state of your git history.

    [dim]Examples:[/dim]

      [cyan]git-trauma[/cyan]                          Analyse current repo (last 200 commits)
      [cyan]git-trauma --no-llm[/cyan]                 Rule-based only, no API key needed
      [cyan]git-trauma --web[/cyan]                    Open interactive D3 report in browser
      [cyan]git-trauma --author alice --limit 50[/cyan] Filter by author
      [cyan]git-trauma --since 2024-01-01[/cyan]       Commits after date
    """
    since_dt: datetime | None = None
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            _abort(f"Invalid date format '{since}'. Use YYYY-MM-DD.")

    analysis = _build_analysis(
        path,
        branch=branch,
        author=author,
        limit=limit,
        since=since_dt,
        no_llm=no_llm,
        provider=provider,
        api_key=api_key,
        model=model,
        mode=mode,
    )

    if json_out:
        _dump_json(analysis)
        return

    if web or output:
        out_path = web_renderer.render_and_open(analysis, output) if web else web_renderer.render(analysis, output)
        console.print(f"[green]✓[/green] HTML report saved to [cyan]{out_path}[/cyan]")
        if not web:
            return

    term_renderer.render(analysis, compact=compact, mode=mode)


# ── subcommand: worst ─────────────────────────────────────────────────────────

@app.command()
def worst(
    path: Annotated[Path, typer.Argument()] = Path("."),
    n: Annotated[int, typer.Option("--count", "-n")] = 5,
    no_llm: Annotated[bool, typer.Option("--no-llm")] = False,
) -> None:
    """Show the [bold red]N worst[/bold red] commits in the repo."""
    from .models import Emotion
    analysis = _build_analysis(path, branch=None, author=None, limit=500, since=None, no_llm=no_llm, provider="anthropic", api_key=None, model=None)
    bad_emotions = {Emotion.CRISIS, Emotion.PANIC, Emotion.DESPAIR}
    worst_commits = sorted(
        [c for c in analysis.commits if c.emotion in bad_emotions],
        key=lambda c: c.intensity,
        reverse=True,
    )[:n]

    if not worst_commits:
        console.print("[green]No crisis commits found. Impressive.[/green]")
        return

    console.print(f"\n[bold red]Top {n} worst commits in {analysis.repo_name}:[/bold red]\n")
    for i, ec in enumerate(worst_commits, 1):
        s = ec.signals
        ts = s.timestamp.strftime("%Y-%m-%d %H:%M")
        console.print(f"  [bold]{i}.[/bold] {ec.symbol} [{ec.color}]{ec.emotion.value.upper()}[/{ec.color}]  [dim]{ts}[/dim]  [cyan]{s.short_hash}[/cyan]")
        console.print(f"     [italic]\"{s.message}\"[/italic]")
        if ec.narrative:
            console.print(f"     [dim]→ {ec.narrative}[/dim]")
        console.print(f"     [dim]+{s.lines_added} -{s.lines_deleted}  {s.author}[/dim]\n")


# ── subcommand: stats ─────────────────────────────────────────────────────────

@app.command()
def stats(
    path: Annotated[Path, typer.Argument()] = Path("."),
    no_llm: Annotated[bool, typer.Option("--no-llm")] = True,
) -> None:
    """Print aggregate emotional statistics."""
    analysis = _build_analysis(path, branch=None, author=None, limit=500, since=None, no_llm=no_llm, provider="anthropic", api_key=None, model=None)

    console.print(f"\n[bold]Stats for {analysis.repo_name}[/bold]  [dim]({analysis.total_commits} commits)[/dim]\n")

    counts = analysis.emotion_counts
    total  = analysis.total_commits
    for emotion in sorted(counts, key=lambda e: counts[e], reverse=True):
        pct   = counts[emotion] / total * 100
        bar   = "█" * int(pct / 2)
        from .models import EMOTION_SYMBOL, EMOTION_COLOR
        color = EMOTION_COLOR[emotion]
        console.print(
            f"  {EMOTION_SYMBOL[emotion]} [{color}]{emotion.value:<13}[/{color}]"
            f"  [{color}]{bar:<50}[/{color}]  [dim]{counts[emotion]:>3} ({pct:.0f}%)[/dim]"
        )

    console.print()
    console.print(f"  Crisis rate:      [{'red' if analysis.crisis_rate > 0.3 else 'green'}]{analysis.crisis_rate*100:.1f}%[/]")
    console.print(f"  Dominant emotion: [bold]{analysis.dominant_emotion.value}[/bold]")
    console.print()


# ── JSON dump ─────────────────────────────────────────────────────────────────

def _dump_json(analysis: RepoAnalysis) -> None:
    data = {
        "repo": analysis.repo_name,
        "generated_at": analysis.generated_at.isoformat(),
        "stats": {
            "total_commits": analysis.total_commits,
            "crisis_rate": round(analysis.crisis_rate, 4),
            "dominant_emotion": analysis.dominant_emotion.value,
            "emotion_counts": {e.value: c for e, c in analysis.emotion_counts.items()},
        },
        "commits": [
            {
                "hash": ec.signals.hash,
                "short_hash": ec.signals.short_hash,
                "author": ec.signals.author,
                "timestamp": ec.signals.timestamp.isoformat(),
                "message": ec.signals.message,
                "lines_added": ec.signals.lines_added,
                "lines_deleted": ec.signals.lines_deleted,
                "files_changed": ec.signals.files_changed,
                "emotion": ec.emotion.value,
                "intensity": round(ec.intensity, 3),
                "narrative": ec.narrative,
                "signals": ec.raw_signals_used,
            }
            for ec in analysis.commits
        ],
    }
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
