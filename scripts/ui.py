"""
Layout of the dashboard, close to the Roche ION Material Availability dashboard:
blue top bar, blue panel headers, coloured material status tiles.
Also the animated loading screen shown while the AI summary is generated.

Kept apart from app.py so that app.py only contains the analysis.
"""

import html
import json

import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components

ROCHE_BLUE = "#0B41CD"
ION_BLUE = "#1A73E8"
STATUS_ORDER = ["Actual Stock Out", "Potential Stock Out", "Below Safety", "Good Part"]
STATUS_COLORS = {
    "Actual Stock Out": "#E0443A",
    "Potential Stock Out": "#F28C28",
    "Below Safety": "#F5C518",
    "Good Part": "#2FA84F",
}
STATUS_ICONS = {"Actual Stock Out": "!", "Potential Stock Out": "▲", "Below Safety": "↓", "Good Part": "✓"}
STATUS_DEFINITIONS = {
    "Actual Stock Out": "The current delivery confirmation is later than the SAP requirement date or the delivery is "
                        "overdue. The production demand is not covered: 100% of the safety buffer and GR time are used.",
    "Potential Stock Out": "The current delivery confirmation is later than the SAP requirement date. More than 70% of "
                           "the safety buffer is consumed; GR time is not used.",
    "Below Safety": "The current delivery confirmation is later than the SAP requirement date. Less than 70% of the "
                    "safety buffer is consumed; GR time is not used.",
    "Good Part": "The current delivery confirmation is earlier than the SAP requirement date. The production demand is covered.",
}

CSS = f"""
<style>
.stApp {{ background-color: #F3F5F8; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; }}
section[data-testid="stSidebar"] {{ background-color: #FFFFFF; border-right: 1px solid #E1E5EB; }}

.ion-topbar {{
  background: {ION_BLUE}; color: #fff; border-radius: 4px; padding: 10px 18px; margin-bottom: 14px;
  display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,.15);
}}
.ion-topbar .brand {{ display: flex; align-items: center; gap: 12px; font-size: 1.15rem; font-weight: 600; }}
.ion-topbar .hex {{
  border: 2px solid #fff; padding: 1px 10px; font-weight: 700; font-size: .95rem;
  clip-path: polygon(12% 0, 88% 0, 100% 50%, 88% 100%, 12% 100%, 0 50%);
}}
.ion-topbar .sub {{ font-size: .85rem; opacity: .9; }}
.ion-topbar .tag {{ background: rgba(255,255,255,.18); border-radius: 3px; padding: 2px 8px; font-size: .8rem; }}

.ion-panel {{
  background: {ION_BLUE}; color: #fff; font-weight: 600; padding: 7px 14px; border-radius: 4px 4px 0 0;
  margin: 18px 0 8px 0; font-size: .98rem;
}}

.ion-tiles {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 4px 0 6px 0; }}
.ion-tile {{
  position: relative; color: #fff; border-radius: 4px; padding: 12px 16px; min-height: 86px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.15);
}}
.ion-tile .num {{ font-size: 2rem; font-weight: 700; line-height: 1.1; }}
.ion-tile .lbl {{ font-size: .88rem; margin-top: 2px; }}
.ion-tile .pct {{ font-size: .78rem; opacity: .9; }}
.ion-tile .icon {{
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%); font-size: 2.6rem; font-weight: 700;
  opacity: .35;
}}
.ion-tile.light {{ color: #3A3A3A; }}
@media (max-width: 900px) {{ .ion-tiles {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}

.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 2px solid #D6DCE5; }}
.stTabs [data-baseweb="tab"] {{
  background: #fff; border: 1px solid #D6DCE5; border-bottom: none; border-radius: 4px 4px 0 0; padding: 6px 14px;
}}
.stTabs [aria-selected="true"] {{ background: {ION_BLUE}; color: #fff; }}
.stTabs [aria-selected="true"] p {{ color: #fff; }}

.ai-result {{
  background: #fff; border-left: 4px solid {ROCHE_BLUE}; border-radius: 4px; padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.12); line-height: 1.6;
}}
.ai-result .meta {{ color: #6B7280; font-size: .8rem; margin-top: 10px; }}
</style>
"""


def apply_style():
    """Inject the CSS and align the matplotlib charts with the dashboard colours."""
    st.markdown(CSS, unsafe_allow_html=True)
    plt.rcParams.update({
        "axes.prop_cycle": plt.cycler(color=[ION_BLUE, "#E0443A", "#F28C28", "#2FA84F", "#7B61FF",
                                             "#00A3AD", "#F5C518", "#8C8C8C"]),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "font.size": 10,
    })


def top_bar(title, subtitle, tag="AI PoC"):
    st.markdown(
        f'<div class="ion-topbar"><div class="brand"><span class="hex">Roche</span>'
        f'<span>{html.escape(title)}</span><span class="sub">{html.escape(subtitle)}</span></div>'
        f'<span class="tag">{html.escape(tag)}</span></div>',
        unsafe_allow_html=True,
    )


def panel_header(title):
    """Blue section header, like the panels of the ION dashboard."""
    st.markdown(f'<div class="ion-panel">{html.escape(title)}</div>', unsafe_allow_html=True)


def status_tiles(status_counts: dict, total: int):
    """The four ION material status tiles, counting the comments of the selection."""
    tiles = []
    for status in STATUS_ORDER:
        count = int(status_counts.get(status, 0))
        if status == "Good Part":  # ION shows "Unknown Status (Good Part)" with the good parts
            count += int(status_counts.get("Unknown Status (Good Part)", 0))
        pct = count / total * 100 if total else 0
        light = " light" if status == "Below Safety" else ""
        tiles.append(
            f'<div class="ion-tile{light}" style="background:{STATUS_COLORS[status]}">'
            f'<div class="num">{count}</div><div class="lbl">{status}</div>'
            f'<div class="pct">{pct:.1f}% of the comments</div>'
            f'<div class="icon">{STATUS_ICONS[status]}</div></div>'
        )
    st.markdown(f'<div class="ion-tiles">{"".join(tiles)}</div>', unsafe_allow_html=True)


def status_definitions():
    with st.expander("Material Status Definitions"):
        for status in STATUS_ORDER:
            st.markdown(f"- **{status}**: {STATUS_DEFINITIONS[status]}")


# ---------------------------------------------------------------------------
# AI summary: animated loading screen
# ---------------------------------------------------------------------------

LOADING_HTML = """
<div id="ai" class="ai">
  <div class="left">
    <svg viewBox="0 0 200 200" class="brain" aria-hidden="true">
      <circle cx="100" cy="100" r="86" class="ring r1"/>
      <circle cx="100" cy="100" r="62" class="ring r2"/>
      <circle cx="100" cy="100" r="38" class="ring r3"/>
      <g class="orbit o1"><circle cx="100" cy="14" r="5" class="dot"/></g>
      <g class="orbit o2"><circle cx="100" cy="38" r="4" class="dot"/></g>
      <g class="orbit o3"><circle cx="100" cy="62" r="3.5" class="dot"/></g>
      <circle cx="100" cy="100" r="16" class="core"/>
    </svg>
    <div class="counter"><span id="cnt">0</span><small>comments analysed</small></div>
    <div class="sub" id="sub"></div>
  </div>
  <div class="right">
    <div class="title">Analysing planner comments<span class="blink">_</span></div>
    <ul id="steps"></ul>
    <div class="bar"><div id="fill"></div></div>
    <div class="stream" id="stream"></div>
  </div>
</div>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  .ai { display: flex; gap: 22px; padding: 22px; border-radius: 6px; color: #fff; height: 100vh;
        background: radial-gradient(circle at 15% 20%, #2D6BFF 0%, #0B41CD 40%, #021E66 100%); overflow: hidden; }
  .left { width: 210px; flex-shrink: 0; text-align: center; }
  .brain { width: 170px; height: 170px; }
  .ring { fill: none; stroke: rgba(255,255,255,.22); stroke-width: 1.2; stroke-dasharray: 4 6; }
  .r1 { animation: spin 14s linear infinite; transform-origin: 100px 100px; }
  .r2 { animation: spin 9s linear infinite reverse; transform-origin: 100px 100px; }
  .r3 { animation: spin 6s linear infinite; transform-origin: 100px 100px; }
  .orbit { transform-origin: 100px 100px; }
  .o1 { animation: spin 3.2s linear infinite; } .o2 { animation: spin 2.4s linear infinite reverse; }
  .o3 { animation: spin 1.7s linear infinite; }
  .dot { fill: #7FD3FF; filter: drop-shadow(0 0 4px #7FD3FF); }
  .core { fill: #fff; animation: pulse 1.4s ease-in-out infinite; transform-origin: 100px 100px; }
  .counter { font-size: 30px; font-weight: 700; margin-top: 6px; font-variant-numeric: tabular-nums; }
  .counter small { display: block; font-size: 12px; font-weight: 400; opacity: .8; }
  .left .sub { font-size: 11px; opacity: .7; margin-top: 8px; line-height: 1.5; }
  .right { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .title { font-size: 17px; font-weight: 600; margin-bottom: 10px; letter-spacing: .2px; }
  .blink { animation: blink 1s step-end infinite; }
  ul { list-style: none; margin: 0; padding: 0; font-size: 13px; }
  li { padding: 4px 0; display: flex; gap: 10px; align-items: baseline; opacity: .35; transition: opacity .3s; }
  li.on, li.done { opacity: 1; }
  li .ic { width: 16px; flex-shrink: 0; text-align: center; }
  li.done .ic { color: #6CFFB0; }
  li.on .ic { display: inline-block; animation: spin 1s linear infinite; }
  li.on { color: #BFE6FF; font-weight: 600; }
  li .v { color: #BFE6FF; }
  .bar { height: 5px; background: rgba(255,255,255,.18); border-radius: 3px; margin: 12px 0 10px; overflow: hidden; }
  #fill { height: 100%; width: 0; border-radius: 3px; transition: width .4s ease;
          background: linear-gradient(90deg, #7FD3FF, #6CFFB0, #7FD3FF); background-size: 200% 100%;
          animation: shine 1.6s linear infinite; }
  .stream { flex: 1; overflow: hidden; font-family: Menlo, Consolas, monospace; font-size: 11px;
            opacity: .75; mask-image: linear-gradient(to bottom, transparent, #000 25%, #000 75%, transparent); }
  .stream div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 1px 0;
                animation: fadein .4s ease; }
  .stream b { color: #7FD3FF; font-weight: 400; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes pulse { 0%,100% { transform: scale(.85); opacity: .85; } 50% { transform: scale(1.1); opacity: 1; } }
  @keyframes blink { 50% { opacity: 0; } }
  @keyframes shine { to { background-position: -200% 0; } }
  @keyframes fadein { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; } }
</style>
<script>
  const D = __DATA__;
  const steps = document.getElementById("steps"), fill = document.getElementById("fill");
  const cnt = document.getElementById("cnt"), stream = document.getElementById("stream");
  document.getElementById("sub").textContent = D.sub;
  D.steps.forEach(s => {
    const li = document.createElement("li");
    li.innerHTML = '<span class="ic">○</span><span><span class="t"></span> <span class="v"></span></span>';
    li.querySelector(".t").textContent = s.text;
    li.querySelector(".v").textContent = s.value ? "— " + s.value : "";
    li.querySelector(".v").style.visibility = "hidden";
    steps.appendChild(li);
  });
  const items = [...steps.children];
  let i = 0;
  function next() {
    if (i > 0) { const p = items[i - 1]; p.className = "done"; p.querySelector(".ic").textContent = "✓";
                 p.querySelector(".v").style.visibility = "visible"; }
    if (i >= items.length) return;
    const li = items[i]; li.className = "on"; li.querySelector(".ic").textContent = "◌";
    // the last step (LLM writing) stays active until Python replaces this screen
    fill.style.width = Math.round((i + 1) / (items.length + 1) * 100) + "%";
    if (i < items.length - 1) setTimeout(next, D.stepMs);
    i++;
  }
  next();
  // counter: comments "analysed", reaches the total during the first steps
  const t0 = performance.now(), dur = D.stepMs * 3;
  (function tick(now) {
    const k = Math.min(1, (now - t0) / dur);
    cnt.textContent = Math.round(D.total * (1 - Math.pow(1 - k, 3))).toLocaleString("en-US");
    if (k < 1) requestAnimationFrame(tick);
  })(t0);
  // stream of real (translated) comments scrolling by
  let j = 0;
  setInterval(() => {
    if (!D.comments.length) return;
    const c = D.comments[j++ % D.comments.length];
    const div = document.createElement("div");
    div.innerHTML = "<b>›</b> ";
    div.appendChild(document.createTextNode(c));
    stream.appendChild(div);
    while (stream.children.length > 9) stream.removeChild(stream.firstChild);
  }, 260);
</script>
"""


def ai_loading_screen(steps, total, sub, comments, step_ms=900, height=380):
    """Render the animated loading screen. steps = [{"text": ..., "value": ...}], the last one
    stays active until the caller replaces the screen (e.g. when the LLM has answered)."""
    data = {"steps": steps, "total": int(total), "sub": sub, "comments": comments, "stepMs": step_ms}
    payload = json.dumps(data).replace("</", "<\\/")
    components.html(LOADING_HTML.replace("__DATA__", payload), height=height)


def ai_result(text, meta):
    st.markdown(
        f'<div class="ai-result">{html.escape(text).replace(chr(10), "<br>")}'
        f'<div class="meta">{html.escape(meta)}</div></div>',
        unsafe_allow_html=True,
    )
