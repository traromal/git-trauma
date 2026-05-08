from __future__ import annotations

import json
import webbrowser
from pathlib import Path

from ..models import EMOTION_COLOR, EMOTION_SYMBOL, RepoAnalysis

_EMOTION_HEX = {
    "crisis":      "#ef4444",
    "panic":       "#f97316",
    "flow":        "#06b6d4",
    "frustration": "#eab308",
    "relief":      "#22c55e",
    "pride":       "#a855f7",
    "grind":       "#6b7280",
    "despair":     "#ec4899",
    "neutral":     "#94a3b8",
}


def render(analysis: RepoAnalysis, output_path: Path | None = None) -> Path:
    commits_json = _build_commits_json(analysis)
    stats_json   = _build_stats_json(analysis)
    html = _build_html(analysis.repo_name, commits_json, stats_json)

    out = output_path or Path(f"git-trauma-{analysis.repo_name}.html")
    out.write_text(html, encoding="utf-8")
    return out


def render_and_open(analysis: RepoAnalysis, output_path: Path | None = None) -> Path:
    out = render(analysis, output_path)
    webbrowser.open(out.as_uri())
    return out


def _build_commits_json(analysis: RepoAnalysis) -> str:
    data = []
    for ec in analysis.commits:
        s = ec.signals
        data.append({
            "hash":         s.short_hash,
            "author":       s.author,
            "timestamp":    s.timestamp.isoformat(),
            "message":      s.message,
            "lines_added":  s.lines_added,
            "lines_deleted": s.lines_deleted,
            "files_changed": s.files_changed,
            "emotion":      ec.emotion.value,
            "intensity":    round(ec.intensity, 3),
            "narrative":    ec.narrative,
            "emoji":        ec.emoji,
            "color":        _EMOTION_HEX.get(ec.emotion.value, "#94a3b8"),
            "is_late_night": s.is_late_night,
            "is_weekend":   s.is_weekend,
            "velocity":     s.velocity,
        })
    return json.dumps(data)


def _build_stats_json(analysis: RepoAnalysis) -> str:
    counts = analysis.emotion_counts
    data = {
        "repo_name":     analysis.repo_name,
        "total_commits": analysis.total_commits,
        "crisis_rate":   round(analysis.crisis_rate * 100, 1),
        "dominant":      analysis.dominant_emotion.value,
        "distribution":  {e.value: c for e, c in counts.items()},
    }
    return json.dumps(data)


def _build_html(repo_name: str, commits_json: str, stats_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>git-trauma · {repo_name}</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 14px;
    line-height: 1.6;
  }}
  header {{
    padding: 32px 48px 0;
    border-bottom: 1px solid #21262d;
  }}
  header h1 {{
    font-size: 24px;
    font-weight: 700;
    color: #f0f6fc;
  }}
  header h1 span {{ color: #58a6ff; }}
  header p {{ color: #8b949e; margin-top: 4px; }}
  .cards {{
    display: flex;
    gap: 16px;
    padding: 24px 48px;
    flex-wrap: wrap;
  }}
  .card {{
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 20px 24px;
    min-width: 160px;
    flex: 1;
  }}
  .card .label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }}
  .card .value {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
  #arc-container {{
    padding: 0 48px;
  }}
  #arc-container h2 {{
    font-size: 13px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }}
  #arc {{ width: 100%; }}
  .tooltip {{
    position: fixed;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    pointer-events: none;
    max-width: 320px;
    z-index: 999;
    font-size: 13px;
    line-height: 1.8;
  }}
  .tooltip .msg {{ font-style: italic; color: #e6edf3; margin-bottom: 4px; }}
  .tooltip .narrative {{ color: #8b949e; }}
  .tooltip .meta {{ margin-top: 8px; color: #6e7681; font-size: 11px; }}
  #commits-container {{
    padding: 24px 48px;
  }}
  #commits-container h2 {{
    font-size: 13px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }}
  #filter-bar {{
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    background: #161b22;
    border: 1px solid #30363d;
    color: #8b949e;
    padding: 4px 12px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    transition: all 0.15s;
  }}
  .filter-btn:hover, .filter-btn.active {{
    border-color: #58a6ff;
    color: #58a6ff;
  }}
  #commit-list {{ max-height: 600px; overflow-y: auto; }}
  .commit-row {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #21262d;
    transition: background 0.1s;
  }}
  .commit-row:hover {{ background: #161b22; }}
  .commit-emoji {{ font-size: 20px; min-width: 28px; text-align: center; }}
  .commit-body {{ flex: 1; }}
  .commit-header {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .commit-hash {{ color: #58a6ff; font-size: 12px; }}
  .commit-author {{ color: #8b949e; font-size: 12px; }}
  .commit-ts {{ color: #6e7681; font-size: 12px; }}
  .commit-emotion {{
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .commit-msg {{ margin-top: 3px; color: #e6edf3; }}
  .commit-narrative {{ margin-top: 2px; color: #8b949e; font-size: 12px; font-style: italic; }}
  .commit-stats {{ display: flex; gap: 12px; margin-top: 4px; font-size: 11px; }}
  .additions {{ color: #3fb950; }}
  .deletions {{ color: #f85149; }}
  .files     {{ color: #6e7681; }}
  #dist-container {{
    padding: 0 48px 48px;
  }}
  #dist-container h2 {{
    font-size: 13px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 16px;
  }}
  #dist-chart {{ width: 100%; max-width: 600px; }}
  .bar-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
  .bar-label {{ width: 100px; font-size: 12px; text-align: right; color: #8b949e; }}
  .bar-track {{ flex: 1; background: #21262d; border-radius: 4px; height: 18px; }}
  .bar-fill  {{ height: 100%; border-radius: 4px; transition: width 0.5s ease; }}
  .bar-count {{ width: 40px; font-size: 12px; color: #6e7681; }}
</style>
</head>
<body>

<header>
  <h1>🧠 git-trauma · <span>{repo_name}</span></h1>
  <p id="subtitle">Loading...</p>
</header>

<div class="cards" id="cards"></div>

<div id="arc-container">
  <h2>Emotional Arc</h2>
  <svg id="arc"></svg>
</div>

<div id="commits-container">
  <h2>Commit History</h2>
  <div id="filter-bar"></div>
  <div id="commit-list"></div>
</div>

<div id="dist-container">
  <h2>Emotion Distribution</h2>
  <div id="dist-chart"></div>
</div>

<div class="tooltip" id="tooltip" style="display:none"></div>

<script>
const COMMITS = {commits_json};
const STATS   = {stats_json};

const COLORS = {{
  crisis:      "#ef4444",
  panic:       "#f97316",
  flow:        "#06b6d4",
  frustration: "#eab308",
  relief:      "#22c55e",
  pride:       "#a855f7",
  grind:       "#6b7280",
  despair:     "#ec4899",
  neutral:     "#94a3b8",
}};

// ── subtitle
document.getElementById("subtitle").textContent =
  `${{STATS.total_commits}} commits  ·  ${{STATS.crisis_rate}}% crisis rate  ·  dominant: ${{STATS.dominant}}`;

// ── cards
const cardData = [
  {{ label: "Total Commits",   value: STATS.total_commits,         color: "#58a6ff" }},
  {{ label: "Crisis Rate",     value: STATS.crisis_rate + "%",     color: STATS.crisis_rate > 30 ? "#ef4444" : STATS.crisis_rate > 15 ? "#eab308" : "#22c55e" }},
  {{ label: "Dominant Vibe",   value: STATS.dominant.toUpperCase(), color: COLORS[STATS.dominant] }},
];
const cardsEl = document.getElementById("cards");
cardData.forEach(c => {{
  cardsEl.innerHTML += `<div class="card">
    <div class="label">${{c.label}}</div>
    <div class="value" style="color:${{c.color}}">${{c.value}}</div>
  </div>`;
}});

// ── emotional arc (D3 line + dots)
(function buildArc() {{
  const margin = {{ top: 20, right: 20, bottom: 30, left: 40 }};
  const width  = document.getElementById("arc-container").clientWidth - margin.left - margin.right;
  const height = 140;

  const severityMap = {{
    crisis: 5, panic: 4, despair: 4, frustration: 3,
    grind: 2, neutral: 2, relief: 1, flow: 0, pride: 0
  }};

  const data = COMMITS.map((c, i) => ({{
    i, sev: severityMap[c.emotion] ?? 2, ...c
  }}));

  const x = d3.scaleLinear().domain([0, data.length - 1]).range([0, width]);
  const y = d3.scaleLinear().domain([0, 5]).range([height, 0]);

  const svg = d3.select("#arc")
    .attr("height", height + margin.top + margin.bottom)
    .attr("width",  width  + margin.left  + margin.right)
    .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

  // gradient fill under curve
  const defs = svg.append("defs");
  const grad = defs.append("linearGradient").attr("id","arcGrad").attr("x1","0%").attr("y1","0%").attr("x2","0%").attr("y2","100%");
  grad.append("stop").attr("offset","0%").attr("stop-color","#58a6ff").attr("stop-opacity",0.3);
  grad.append("stop").attr("offset","100%").attr("stop-color","#58a6ff").attr("stop-opacity",0);

  const area = d3.area().x(d => x(d.i)).y0(height).y1(d => y(d.sev)).curve(d3.curveCatmullRom);
  const line = d3.line().x(d => x(d.i)).y(d => y(d.sev)).curve(d3.curveCatmullRom);

  svg.append("path").datum(data).attr("fill","url(#arcGrad)").attr("d", area);
  svg.append("path").datum(data).attr("fill","none").attr("stroke","#58a6ff").attr("stroke-width",2).attr("d", line);

  // dots colored by emotion
  const tooltip = document.getElementById("tooltip");
  svg.selectAll("circle").data(data).enter().append("circle")
    .attr("cx", d => x(d.i))
    .attr("cy", d => y(d.sev))
    .attr("r",  d => d.sev >= 4 ? 5 : 3)
    .attr("fill", d => COLORS[d.emotion] ?? "#94a3b8")
    .attr("stroke", "#0d1117")
    .attr("stroke-width", 1)
    .on("mousemove", (event, d) => {{
      const ts = new Date(d.timestamp).toLocaleString();
      tooltip.style.display = "block";
      tooltip.style.left    = (event.clientX + 14) + "px";
      tooltip.style.top     = (event.clientY - 14) + "px";
      tooltip.innerHTML = `
        <div class="msg">"${{d.message}}"</div>
        ${{d.narrative ? `<div class="narrative">→ ${{d.narrative}}</div>` : ""}}
        <div class="meta">
          ${{d.emoji}} ${{d.emotion.toUpperCase()}} · ${{ts}}<br>
          +${{d.lines_added}} -${{d.lines_deleted}} · ${{d.files_changed}} files · ${{d.author}}
        </div>`;
    }})
    .on("mouseleave", () => {{ tooltip.style.display = "none"; }});

  // x-axis labels (first, last, middle)
  svg.append("g").attr("transform", `translate(0,${{height}})`).call(
    d3.axisBottom(x).tickValues([0, Math.floor(data.length/2), data.length-1])
      .tickFormat(i => COMMITS[i] ? new Date(COMMITS[i].timestamp).toLocaleDateString() : "")
  ).selectAll("text").style("fill","#6e7681").style("font-size","11px");
  svg.selectAll(".domain,.tick line").attr("stroke","#21262d");
}})();

// ── filter bar + commit list
const ALL_EMOTIONS = [...new Set(COMMITS.map(c => c.emotion))];
let activeFilter = null;

const filterBar = document.getElementById("filter-bar");
filterBar.innerHTML = `<button class="filter-btn active" data-e="all">All</button>` +
  ALL_EMOTIONS.map(e => `<button class="filter-btn" data-e="${{e}}" style="border-color:${{COLORS[e]}}20">
    ${{COMMITS.find(c=>c.emotion===e)?.emoji}} ${{e}}
  </button>`).join("");

filterBar.querySelectorAll(".filter-btn").forEach(btn => {{
  btn.addEventListener("click", () => {{
    filterBar.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.e === "all" ? null : btn.dataset.e;
    renderList();
  }});
}});

function renderList() {{
  const list = document.getElementById("commit-list");
  const visible = activeFilter ? COMMITS.filter(c => c.emotion === activeFilter) : COMMITS;
  list.innerHTML = visible.map(c => {{
    const ts = new Date(c.timestamp).toLocaleString();
    const color = COLORS[c.emotion];
    return `<div class="commit-row">
      <div class="commit-emoji">${{c.emoji}}</div>
      <div class="commit-body">
        <div class="commit-header">
          <span class="commit-hash">${{c.hash}}</span>
          <span class="commit-author">${{c.author}}</span>
          <span class="commit-ts">${{ts}}</span>
          <span class="commit-emotion" style="background:${{color}}22;color:${{color}}">${{c.emotion}}</span>
          ${{c.is_late_night ? '<span style="color:#eab308;font-size:11px">🌙 late night</span>' : ""}}
          ${{c.is_weekend   ? '<span style="color:#eab308;font-size:11px">📅 weekend</span>'   : ""}}
        </div>
        <div class="commit-msg">"${{c.message}}"</div>
        ${{c.narrative ? `<div class="commit-narrative">→ ${{c.narrative}}</div>` : ""}}
        <div class="commit-stats">
          <span class="additions">+${{c.lines_added}}</span>
          <span class="deletions">-${{c.lines_deleted}}</span>
          <span class="files">${{c.files_changed}} files</span>
        </div>
      </div>
    </div>`;
  }}).join("");
}}
renderList();

// ── distribution bars
const distEl = document.getElementById("dist-chart");
const dist   = STATS.distribution;
const total  = STATS.total_commits;
const sorted = Object.entries(dist).sort((a,b) => b[1]-a[1]);
distEl.innerHTML = sorted.map(([e, count]) => {{
  const pct   = count / total * 100;
  const color = COLORS[e];
  const emoji = COMMITS.find(c => c.emotion === e)?.emoji ?? "";
  return `<div class="bar-row">
    <div class="bar-label">${{emoji}} ${{e}}</div>
    <div class="bar-track">
      <div class="bar-fill" style="width:${{pct}}%;background:${{color}}"></div>
    </div>
    <div class="bar-count">${{count}}</div>
  </div>`;
}}).join("");
</script>
</body>
</html>"""
