"""
Layout of the dashboard, close to the Roche ION Material Availability dashboard:
blue top bar with a navigation menu, blue section headers, coloured material status tiles.
Also the animated loading screen shown while the AI summary is generated.

Kept apart from app.py so that app.py only contains the analysis.
"""

import base64
import html
import json
import os

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

RADIUS = "2px"  # ION uses almost square corners
BAR_HEIGHT = 54  # px, height of the blue top bar (fixed, full width)
# Chevron pointing left (same icon family as Streamlit's "open sidebar" arrow)
CHEVRON_LEFT = ("url(\"data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E"
                "%3Cpath d='M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z'/%3E%3C/svg%3E\")")
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "roche_logo.png")

CSS = f"""
<style>
.stApp {{ background-color: #F3F5F8; }}
[data-testid="stDecoration"] {{ display: none; }}
/* Streamlit's own toolbar (Deploy, menu) sits on the right of the blue bar, in white */
header[data-testid="stHeader"] {{ background: transparent; height: {BAR_HEIGHT}px; z-index: 1000002; }}
header[data-testid="stHeader"] [data-testid="stToolbar"] {{ top: 50%; transform: translateY(-50%); right: 12px; }}
header[data-testid="stHeader"] button, header[data-testid="stHeader"] [data-testid="stToolbar"] * {{ color: #fff !important; }}
.block-container {{ padding-top: {BAR_HEIGHT + 4}px; }}
/* Sidebar starts under the blue bar */
section[data-testid="stSidebar"] {{
  background-color: #FFFFFF; border-right: 1px solid #E1E5EB;
  top: {BAR_HEIGHT}px !important; height: calc(100vh - {BAR_HEIGHT}px) !important;
}}
[data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {{ top: {BAR_HEIGHT + 8}px !important; }}
/* "Close sidebar" button: a left arrow instead of the cross */
section[data-testid="stSidebar"] button[data-testid="baseButton-header"] svg {{ display: none; }}
section[data-testid="stSidebar"] button[data-testid="baseButton-header"]::before {{
  content: ""; display: block; width: 1.5rem; height: 1.5rem; background-color: currentColor;
  -webkit-mask: {CHEVRON_LEFT} center / contain no-repeat; mask: {CHEVRON_LEFT} center / contain no-repeat;
}}

/* Charts: white cards, centred, same look everywhere */
[data-testid="stImage"] {{ display: flex; justify-content: center; }}
[data-testid="stImage"] img {{
  background: #fff; border: 1px solid #E1E5EB; border-radius: {RADIUS}; padding: 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,.05); max-width: 100%; box-sizing: border-box;
}}
html, .main, [data-testid="stAppViewContainer"] {{ scroll-behavior: smooth; }}

/* Square corners on the Streamlit widgets too */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="popover"] ul, .stButton > button,
.stDateInput > div > div, [data-testid="stExpander"] details, [data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"], [data-testid="stNotification"], [data-testid="stAlert"] > div {{
  border-radius: {RADIUS} !important;
}}

.ion-topbar {{
  position: fixed; top: 0; left: 0; right: 0; height: {BAR_HEIGHT}px; z-index: 1000001;
  background: {ION_BLUE}; color: #fff; padding: 0 200px 0 18px;
  display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.2);
}}
.ion-topbar .brand {{ display: flex; align-items: center; gap: 14px; font-size: 1.15rem; font-weight: 600; }}
.ion-topbar .brand img {{ height: 30px; width: auto; display: block; }}
.ion-topbar .hex {{
  border: 2px solid #fff; padding: 1px 10px; font-weight: 700; font-size: .95rem;
  clip-path: polygon(12% 0, 88% 0, 100% 50%, 88% 100%, 12% 100%, 0 50%);
}}
.ion-topbar .sub {{ font-size: .85rem; opacity: .9; }}
.ion-topbar .tag {{ background: rgba(255,255,255,.18); border-radius: {RADIUS}; padding: 2px 8px; font-size: .8rem; }}

/* Navigation menu: stays just under the blue bar while scrolling */
div[data-testid="stVerticalBlock"] > div:has(.ion-nav) {{ position: sticky; top: {BAR_HEIGHT}px; z-index: 990; }}
.ion-nav {{
  display: flex; flex-wrap: wrap; gap: 2px; background: #fff; border: 1px solid #D6DCE5;
  padding: 4px; box-shadow: 0 2px 4px rgba(0,0,0,.06);
}}
.ion-nav a {{
  color: #1F2937 !important; text-decoration: none !important; font-size: .86rem; padding: 6px 12px;
  border-radius: {RADIUS}; white-space: nowrap;
}}
.ion-nav a:hover {{ background: #E8F0FE; }}
.ion-nav a.active {{ background: {ION_BLUE}; color: #fff !important; }}
.emo {{ margin-right: 6px; }}
.ion-anchor {{ scroll-margin-top: {BAR_HEIGHT + 70}px; height: 0; }}
/* the invisible scroll-spy iframe takes no space */
div[data-testid="element-container"]:has( iframe[height="0"]) {{ display: none; }}

.ion-panel {{
  background: {ION_BLUE}; color: #fff; font-weight: 600; padding: 7px 14px; border-radius: {RADIUS};
  margin: 18px 0 8px 0; font-size: .98rem;
}}
.ion-section {{ margin-top: 26px; }}
.ion-section .ion-panel {{ font-size: 1.05rem; padding: 9px 14px; }}

.ion-tiles {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 4px 0 6px 0; }}
.ion-tile {{
  position: relative; color: #fff; border-radius: {RADIUS}; padding: 12px 16px; min-height: 86px; overflow: hidden;
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

.ai-result {{
  background: #fff; border-left: 4px solid {ROCHE_BLUE}; border-radius: {RADIUS}; padding: 16px 20px;
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


def _logo_html():
    """Roche logo from assets/roche_logo.png (kept local, not on GitHub); text badge if missing."""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{data}" alt="Roche">'
    return '<span class="hex">Roche</span>'


def _label(text):
    """Escape a label; a leading emoji gets its own span so it keeps a gap with the text
    (Streamlit's markdown drops the space)."""
    first, _, rest = text.partition(" ")
    if rest and not first.isalnum():
        return f'<span class="emo">{html.escape(first)}</span>{html.escape(rest)}'
    return html.escape(text)


def top_bar(title, subtitle, sections, tag="AI PoC"):
    """Blue title bar + navigation menu. sections = [(anchor_id, label)]: clicking a label
    scrolls down to that section; the menu stays visible at the top of the page."""
    st.markdown(
        f'<div class="ion-topbar"><div class="brand">{_logo_html()}'
        f'<span>{html.escape(title)}</span><span class="sub">{html.escape(subtitle)}</span>'
        f'<span class="tag">{html.escape(tag)}</span></div></div>',
        unsafe_allow_html=True,
    )
    links = "".join(f'<a href="#{a}" target="_self" data-target="{a}">{_label(label)}</a>' for a, label in sections)
    st.markdown(f'<div class="ion-nav">{links}</div>', unsafe_allow_html=True)


SCROLL_SPY_JS = """
<script>
// Highlights in the menu the section currently on screen. The code is installed once in the
// dashboard page itself (not in this iframe), so it survives Streamlit reruns.
(function () {
  const doc = window.parent.document;
  if (doc.getElementById("ion-scroll-spy")) return;
  const script = doc.createElement("script");
  script.id = "ion-scroll-spy";
  script.textContent = `
    (function () {
      const MIN_OFFSET = __OFFSET__;
      let ticking = false, scroller = null;
      function update() {
        ticking = false;
        const links = document.querySelectorAll(".ion-nav a[data-target]");
        if (!links.length) return;
        // a section is "current" once its title is in the upper third of the screen
        const offset = Math.max(MIN_OFFSET, window.innerHeight * 0.35);
        let current = links[0].dataset.target;
        links.forEach(a => {
          const el = document.getElementById(a.dataset.target);
          if (el && el.getBoundingClientRect().top <= offset) current = a.dataset.target;
        });
        // at the very bottom of the page, the last section is the current one
        if (scroller && scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 4) {
          current = links[links.length - 1].dataset.target;
        }
        links.forEach(a => a.classList.toggle("active", a.dataset.target === current));
      }
      function request(e) {
        const t = e && (e.target === document ? document.scrollingElement : e.target);
        if (t && t.scrollHeight > t.clientHeight) scroller = t;
        if (!ticking) { ticking = true; requestAnimationFrame(update); }
      }
      document.addEventListener("scroll", request, true);
      window.addEventListener("resize", request);
      setInterval(update, 700);  // after Streamlit re-renders the menu
      update();
    })();`;
  doc.body.appendChild(script);
})();
</script>
"""


def scroll_spy():
    """Invisible helper: colours in blue the menu entry of the section on screen."""
    components.html(SCROLL_SPY_JS.replace("__OFFSET__", str(BAR_HEIGHT + 90)), height=0)


def section(anchor_id, title):
    """Start of a page section: anchor for the menu + blue header."""
    st.markdown(
        f'<div class="ion-section"><div id="{anchor_id}" class="ion-anchor"></div>'
        f'<div class="ion-panel">{_label(title)}</div></div>',
        unsafe_allow_html=True,
    )


def panel_header(title):
    """Blue sub-header inside a section, like the panels of the ION dashboard."""
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
  .ai { display: flex; gap: 22px; padding: 22px; border-radius: 2px; color: #fff; height: 100vh;
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
