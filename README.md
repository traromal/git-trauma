<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue" alt="Python">
  <img src="https://img.shields.io/github/actions/workflow/status/traromal/git-trauma/ci.yml?branch=master&label=CI" alt="CI">
  <img src="https://img.shields.io/github/license/traromal/git-trauma" alt="License">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome">
</p>

# git-trauma

Emotional analysis of your git history. Classifies commits into emotions (crisis, panic, flow, frustration, relief, pride, grind, despair) and optionally narrates them via AI.

![Demo](assets/demo.gif)

## Installation

```bash
pip install git-trauma
```

Or install from source:

```bash
git clone https://github.com/traromal/git-trauma
cd git-trauma
pip install .
```

Requires **Python ≥ 3.10**.

## Setup API Keys (Optional)

Without an API key, git-trauma runs in rule-based mode (no AI narratives). To enable AI narration, set one of these:

### Groq

```bash
export GROQ_API_KEY="gsk_..."
```

### Anthropic

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or create a `.env` file in the directory you run the command from:

```
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

Run inside any git repo:

```bash
git-trauma
```

### Options

| Flag | Description |
|------|-------------|
| `--no-llm` | Rule-based only, no API key needed |
| `--web`, `-w` | Open interactive D3 HTML report in browser |
| `--output`, `-o` | Save HTML report to file |
| `--provider`, `-p` | LLM provider: `anthropic` (default) or `groq` |
| `--api-key` | API key (overrides env var) |
| `--model` | Model override (default: claude-3-haiku / llama-3.1-8b-instant) |
| `--mode`, `-m` | Narration style: `normal`, `roast`, `therapist`, `corporate` |
| `--branch`, `-b` | Branch to analyze |
| `--author`, `-a` | Filter by author name/email |
| `--limit`, `-n` | Max commits to analyze (default: 200) |
| `--since`, `-s` | Since date (YYYY-MM-DD) |
| `--compact`, `-c` | Compact table view |
| `--json` | Output raw JSON |
| `--version`, `-V` | Show version |

### Subcommands

```bash
git-trauma analyze              # default command
git-trauma worst                # show N worst commits
git-trauma stats                # aggregate emotional statistics
```

### Examples

```bash
# Basic analysis of current repo
git-trauma

# Rule-based only (faster, free)
git-trauma --no-llm

# Interactive HTML report
git-trauma --web

# Roast the author's commits
git-trauma --mode roast --author alice

# Filter by date range
git-trauma --since 2024-01-01 --limit 50

# Show worst commits
git-trauma worst --count 10

# Use Groq instead of Anthropic
git-trauma --provider groq
```

## Demo GIF

Generate your own demo GIF with [VHS](https://github.com/charmbracelet/vhs):

```bash
# Install VHS (one time)
go install github.com/charmbracelet/vhs@latest

# Record the demo
vhs demo.tape
```

## Output

Terminal table with emotion classification, intensity scores, and optional AI narratives. For the full interactive experience, use `--web` to open a D3-based HTML report in your browser.

## Project Structure

```
git_trauma/
├── cli.py              # CLI entry point (typer)
├── models.py           # Data models (Emotion, CommitSignals, etc.)
├── git_parser.py       # Git commit parsing
├── signal_extractor.py # Rule-based emotion classification
├── narrator.py         # AI narration (Groq/Anthropic)
└── renderer/
    ├── terminal.py     # Terminal table output
    └── web.py          # HTML/D3 report
```
