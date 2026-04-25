import base64
import html as html_lib
import inspect
import json
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from asr import transcribe
from summarization import summarize

try:
    from summarization import available_models
except Exception:
    available_models = None


st.set_page_config(page_title="Smart Notes Generator", page_icon="🎙️", layout="wide")

PROJECT_DIR = Path(__file__).parent
STICKERS_DIR = PROJECT_DIR / "stickers"
HISTORY_FILE = PROJECT_DIR / ".smart_notes_history.json"


# ── History persistence helpers ────────────────────────────────────────────────
def _load_history_from_disk() -> list:
    """Load history from persistent JSON file."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load history from disk: {e}")
            return []
    return []


def _save_history_to_disk(history: list) -> None:
    """Save history to persistent JSON file."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
        print(f"[INFO] History saved to disk ({len(history)} items)")
    except Exception as e:
        print(f"[ERROR] Failed to save history to disk: {e}")


# ──────────────────────────────────────────────────────────────────────────────

for key, value in {
    "transcript": "",
    "smart_notes": "",
    "pipeline_status": "idle",
    "last_file_name": "",
    "last_file_size": 0,
    "history": _load_history_from_disk(),  # Load persisted history on app start
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


summary_model_key = "bart-ft"
if callable(available_models):
    try:
        detected = available_models()
        if "bart-ft" not in detected:
            summary_model_key = detected[0] if detected else "bart"
    except Exception:
        summary_model_key = "bart"


# ── Helpers ────────────────────────────────────────────────────────────────────
def _sticker_path(name: str) -> Path | None:
    p = STICKERS_DIR / name
    return p if p.exists() else None


def _sticker_uri(name: str) -> str:
    p = _sticker_path(name)
    if not p:
        return ""
    ext = p.suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _fmt_size(n: int) -> str:
    if n < 1024:        return f"{n} B"
    if n < 1048576:     return f"{n/1024:.1f} KB"
    return f"{n/1048576:.1f} MB"


# ── Current page (via session state for reliable navigation) ──────────────────
if "current_page" not in st.session_state:
    st.session_state["current_page"] = st.query_params.get("page", "smart_notes")
current_page = st.session_state["current_page"]


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700;800&family=Nunito:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }

/* Background */
.stApp {
    background:
        radial-gradient(ellipse at 8% 14%,  #ffe4f3 0%, transparent 32%),
        radial-gradient(ellipse at 92% 8%,  #d9f0ff 0%, transparent 30%),
        radial-gradient(ellipse at 50% 95%, #e6ffed 0%, transparent 35%),
        linear-gradient(160deg, #fdfbff 0%, #f5f9ff 55%, #f3fff6 100%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.78);
    backdrop-filter: blur(18px);
    border-right: 1px solid rgba(200,210,235,0.4);
}

/* Card */
.card {
    background: rgba(255,255,255,0.8);
    border-radius: 20px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 8px 28px rgba(100,120,170,0.09);
    border: 1px solid rgba(220,228,248,0.7);
    margin-bottom: 0.9rem;
}

/* ── Hero titles — Baloo 2 everywhere ── */
.hero-title {
    font-family: 'Baloo 2', cursive;
    font-size: 2.1rem;
    font-weight: 800;
    color: #1e2d50;
    line-height: 1.15;
    margin: 0 0 0.25rem 0;
}
.hero-sub { color: #6b7a9e; font-weight: 600; font-size: 0.97rem; margin: 0 0 0.85rem 0; }
.chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.chip {
    font-size: 0.76rem; font-weight: 700; color: #4a5580;
    background: linear-gradient(90deg,#f0ebff,#e6f3ff);
    border: 1px solid #d5dcf7; border-radius: 999px;
    padding: 0.26rem 0.7rem;
}

/* Upload zone */
[data-testid="stFileUploaderDropzone"] {
    border-radius: 18px !important;
    border: 2.5px dashed #c5bbff !important;
    background: rgba(245,243,255,0.55) !important;
    transition: border-color 0.2s;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: #a298f5 !important; }

.file-pill {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.38rem 0.8rem; border-radius: 10px;
    border: 1px solid #e0daf8; background: rgba(255,255,255,0.88);
    color: #4a5282; font-weight: 700; font-size: 0.84rem;
    margin: 0.3rem 0 0.5rem 0;
}

/* Run button — only in main area */
[data-testid="stMainBlockContainer"] .stButton > button {
    border: none; border-radius: 14px;
    background: linear-gradient(90deg,#f06292 0%,#f4845f 50%,#f7c94b 100%);
    color: #fff; font-weight: 800; font-size: 1rem;
    padding: 0.75rem 1rem;
    box-shadow: 0 8px 24px rgba(240,100,130,0.28);
    transition: transform 0.15s, box-shadow 0.15s;
}
[data-testid="stMainBlockContainer"] .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 13px 30px rgba(240,100,130,0.35);
}

/* Status banner */
.status-banner {
    border-radius: 14px; padding: 0.8rem 1.1rem;
    font-weight: 700; font-size: 0.92rem;
    margin: 0.5rem 0 0.4rem 0;
    display: flex; align-items: center; gap: 0.7rem;
}
.status-banner.idle    { background: rgba(230,232,255,0.5); border: 1px solid #d2d7f7; color: #4a5082; }
.status-banner.running { background: linear-gradient(90deg,#fff3cd,#ffefd8); border: 1px solid #f5d78b; color: #7a5b10; }
.status-banner.success { background: linear-gradient(90deg,#d9f7e8,#e8fff0); border: 1px solid #a5e0be; color: #1f7a4a; }
.status-banner.error   { background: linear-gradient(90deg,#ffe5e8,#fff0f2); border: 1px solid #f5b2bb; color: #9b2233; }

/* Progress flow */
.flow-row  { display: flex; align-items: center; gap: 0.25rem; flex-wrap: nowrap; }
.flow-step { display: flex; flex-direction: column; align-items: center; min-width: 56px; }
.flow-dot  {
    width: 28px; height: 28px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.68rem; font-weight: 800;
}
.flow-dot.todo    { background: rgba(255,255,255,0.45); color: #b0b8d0; border: 1.5px solid rgba(255,255,255,0.7); }
.flow-dot.current { background: #fff; color: #f06292; border: 2px solid #f06292; box-shadow: 0 0 0 3px rgba(240,98,146,0.18); }
.flow-dot.done    { background: rgba(210,255,230,0.9); color: #27875b; border: 1.5px solid rgba(150,220,180,0.8); }
.flow-dot.error   { background: #fde8eb; color: #d93050; border: 1.5px solid #f4a6b2; }
.flow-label { font-size: 0.62rem; font-weight: 700; color: rgba(255,255,255,0.9); margin-top: 0.2rem; text-align: center; }
.flow-line  { height: 2px; flex: 1; min-width: 18px; max-width: 60px; border-radius: 99px; background: rgba(255,255,255,0.35); }
.flow-line.done { background: rgba(210,255,230,0.8); }

/* Progress card gradient */
.progress-card {
    border-radius: 18px;
    background: linear-gradient(90deg, #f06292 0%, #f4845f 48%, #f7c94b 100%);
    padding: 0.9rem 1.3rem;
    margin-bottom: 1.1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    box-shadow: 0 8px 24px rgba(240,100,130,0.22);
}

/* ── Result panels — self-contained HTML ── */
.panel-wrap {
    position: relative;
    border-radius: 18px;
    padding: 1.1rem 1.2rem 1.1rem 1.2rem;
    background: rgba(255,255,255,0.8);
    overflow: hidden;
    margin-bottom: 0.5rem;
}
.panel-purple { border: 1px solid #d8cef8; box-shadow: 0 4px 18px rgba(140,130,200,0.09); }
.panel-green  { border: 1px solid #b8e8cb; box-shadow: 0 4px 18px rgba(100,200,140,0.09); }

.panel-badge {
    display: inline-block; font-size: 0.72rem; font-weight: 700;
    border-radius: 999px; padding: 0.17rem 0.58rem; margin-bottom: 0.35rem;
}
.badge-purple { background: #ede8ff; color: #6347c7; border: 1px solid #d2c7f5; }
.badge-green  { background: #e3fded; color: #27875b; border: 1px solid #a5e0be; }

/* Panel titles use Baloo 2 */
.panel-title {
    font-family: 'Baloo 2', cursive;
    font-size: 1.55rem;
    font-weight: 700;
    color: #232d4b;
    margin: 0 0 0.55rem 0;
    line-height: 1.2;
}

/* Text display area */
.result-text {
    background: rgba(248,250,255,0.92);
    border: 1px solid #dee5f8;
    border-radius: 12px;
    padding: 0.8rem 1rem;
    min-height: 220px;
    max-height: 340px;
    overflow-y: auto;
    font-size: 0.875rem;
    line-height: 1.72;
    color: #232d4b;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: 'Nunito', sans-serif;
}
.result-text.green-bg { background: rgba(246,255,250,0.92); border-color: #c8e8d2; }
.result-text.empty    { color: #b0b8d0; font-style: italic; }

/* Sticker corner inside panels */
.panel-sticker {
    position: absolute;
    bottom: 10px; right: 12px;
    width: 100px;
    opacity: 0.92;
    pointer-events: none;
}

/* ── Sidebar nav links ── */
.side-section {
    font-family: 'Baloo 2', cursive;
    font-size: 0.82rem; font-weight: 700;
    color: #8a92b8;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: 1rem 0 0.35rem 0;
}
.nav-link {
    display: block;
    padding: 0.44rem 0.7rem;
    border-radius: 10px;
    margin-bottom: 0.26rem;
    font-weight: 700; font-size: 0.875rem;
    color: #636d96;
    text-decoration: none !important;
    border: 1px solid transparent;
    transition: background 0.15s;
}
.nav-link:hover  { background: rgba(240,242,255,0.75); }
.nav-link.active { background: linear-gradient(90deg,#e3fded,#f0fff6); border-color: #a5e0be; color: #257a50; }

.sidebar-card {
    background: rgba(255,255,255,0.65);
    border: 1px solid #e4e9f8;
    border-radius: 14px;
    padding: 0.7rem 0.85rem;
    margin-top: 0.75rem;
}
.sidebar-card-title { font-weight: 800; font-size: 0.82rem; color: #4a5280; margin-bottom: 0.18rem; }
.sidebar-card-text  { font-size: 0.78rem; color: #6e7899; margin: 0; line-height: 1.45; }

/* History + Help pages */
.page-title {
    font-family: 'Baloo 2', cursive;
    font-size: 1.9rem; font-weight: 800;
    color: #1e2d50; margin: 0 0 0.2rem 0;
}
.history-item {
    background: rgba(255,255,255,0.82);
    border: 1px solid #dce4f5;
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 4px 14px rgba(100,120,170,0.07);
}
.history-meta {
    font-size: 0.78rem; color: #8a96b8; font-weight: 600; margin-bottom: 0.5rem;
}
.history-text {
    font-size: 0.84rem; color: #3a4260; line-height: 1.6;
    max-height: 120px; overflow-y: auto;
    background: rgba(248,250,255,0.9);
    border: 1px solid #e4e9f8; border-radius: 10px;
    padding: 0.6rem 0.8rem;
    white-space: pre-wrap;
}
.help-section { margin-bottom: 1.2rem; }
.help-section h3 {
    font-family: 'Baloo 2', cursive;
    font-size: 1.15rem; font-weight: 700; color: #3d4e79;
    margin: 0 0 0.4rem 0;
}
.help-section p, .help-section li {
    font-size: 0.88rem; color: #5a6282; line-height: 1.65;
}

@media (max-width: 900px) {
    .hero-title { font-size: 1.6rem; }
    .flow-line  { min-width: 10px; }
}
</style>
""", unsafe_allow_html=True)


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
logo_uri = _sticker_uri("focus-on-the-good.png")
if logo_uri:
    st.sidebar.markdown(
        f'<img src="{logo_uri}" style="width:145px;margin:0.3rem 0 0.6rem 0;" />',
        unsafe_allow_html=True,
    )

st.sidebar.markdown('<p class="side-section">⚙️ Model Settings</p>', unsafe_allow_html=True)
asr_model_size = st.sidebar.selectbox(
    "ASR model (Whisper)",
    options=["tiny", "base", "small", "medium", "large"],
    index=1,
)
st.sidebar.caption(f"Summarization model: **{summary_model_key}**")

# Navigation — Use Streamlit's native page linking (stays in same tab)
st.sidebar.markdown('<p class="side-section">📌 Navigation</p>', unsafe_allow_html=True)

# Clickable text labels for navigation
nav_labels = [
    ("smart_notes", "📄 Smart Notes"),
    ("history",     "🗂️ Notes History"),
    ("help",        "❔ Help & Docs"),
]
for page_id, label in nav_labels:
    if st.sidebar.button(label, key=f"nav_{page_id}", use_container_width=True):
        st.session_state["current_page"] = page_id
        st.rerun()

# Sidebar sticker card
focus_uri = _sticker_uri("focus.png") or _sticker_uri("notes (3).png")
if focus_uri:
    st.sidebar.markdown(
        f"""
        <div class="sidebar-card" style="text-align:center;margin-top:1.1rem;">
            <img src="{focus_uri}" style="width:95px;margin-bottom:0.35rem;" />
            <p class="sidebar-card-title">Audio → Impact</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

plant_uri  = _sticker_uri("plante lumiere.png")
plant_html = f'<img src="{plant_uri}" style="width:42px;float:right;" />' if plant_uri else ""
st.sidebar.markdown(
    f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">💡 Focus tip</div>
        <p class="sidebar-card-text">Small steps today.<br/>Big impact tomorrow.</p>
        {plant_html}
    </div>
    """,
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SMART NOTES
# ══════════════════════════════════════════════════════════════════════════════
if current_page == "smart_notes":

    # ── Hero ──────────────────────────────────────────────────────────────────
    hero_col, img_col = st.columns([0.78, 0.22], gap="small")

    with hero_col:
        st.markdown(
            """
            <div class="card">
                <p class="hero-title">✨ Smart Notes Generator</p>
                <p class="hero-sub">Colorful AI workspace: Speech → Transcript → Smart Notes</p>
                <div class="chip-row">
                    <span class="chip">⬆️ Upload Audio</span>
                    <span class="chip">🎙️ Whisper ASR</span>
                    <span class="chip">✨ Fine-tuned Summarization</span>
                    <span class="chip">⚡ Study Faster</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with img_col:
        # Girl sticker — height is constrained by the hero card (~130 px)
        girl = _sticker_path("fille.png") or _sticker_path("online-learning.png")
        if girl:
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:center;height:100%;">'
                f'<img src="{_sticker_uri(girl.name)}" style="max-height:155px;max-width:100%;object-fit:contain;" />'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Upload + Run ──────────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Drop your audio file here",
        type=["mp3", "wav", "m4a", "flac"],
        help="Limit 200 MB per file • MP3, WAV, M4A, FLAC",
    )

    if uploaded_file is not None:
        st.markdown(
            f'<div class="file-pill">📎 {uploaded_file.name}'
            f' <span style="opacity:.6;">{_fmt_size(uploaded_file.size)}</span></div>',
            unsafe_allow_html=True,
        )

    run_pipeline = st.button("🚀 Generate Smart Notes", type="primary", use_container_width=True)

    # ── Pipeline logic ────────────────────────────────────────────────────────
    if run_pipeline:
        if uploaded_file is None:
            st.session_state["pipeline_status"] = "error"
            st.session_state["transcript"]  = "[ERROR] Please upload an audio file first."
            st.session_state["smart_notes"] = "[ERROR] Summary skipped because transcription failed."
        else:
            st.session_state["pipeline_status"] = "running"
            st.session_state["last_file_name"]  = uploaded_file.name
            st.session_state["last_file_size"]  = uploaded_file.size

            suffix = Path(uploaded_file.name).suffix or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                temp_audio_path = tmp.name

            with st.spinner("Running ASR + summarization…"):
                transcribe_sig = inspect.signature(transcribe)
                if "model_size" in transcribe_sig.parameters:
                    transcript = transcribe(temp_audio_path, model_size=asr_model_size)
                else:
                    transcript = transcribe(temp_audio_path)

                if transcript.startswith("[ERROR]"):
                    smart_notes = "[ERROR] Summary skipped because transcription failed."
                    pipe_status = "error"
                else:
                    summarize_sig = inspect.signature(summarize)
                    if "model_key" in summarize_sig.parameters:
                        smart_notes = summarize(transcript, model_key=summary_model_key)
                    else:
                        smart_notes = summarize(transcript)
                    pipe_status = "error" if smart_notes.startswith("[ERROR]") else "success"

            st.session_state["transcript"]      = transcript
            st.session_state["smart_notes"]     = smart_notes
            st.session_state["pipeline_status"] = pipe_status

            # Save to history on success
            if pipe_status == "success":
                new_item = {
                    "name":       uploaded_file.name,
                    "transcript": transcript,
                    "smart_notes": smart_notes,
                    "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                st.session_state["history"].append(new_item)
                _save_history_to_disk(st.session_state["history"])  # Persist to disk
                print(f"[SUCCESS] Added to history: {uploaded_file.name}")

    # ── Read state ────────────────────────────────────────────────────────────
    status         = st.session_state["pipeline_status"]
    transcript_val = st.session_state["transcript"]
    notes_val      = st.session_state["smart_notes"]

    # ── Status banner ─────────────────────────────────────────────────────────
    _ICONS = {"idle":"🎯","running":"⚡","success":"✅","error":"❌"}
    _TEXTS = {
        "idle":    "Ready — upload an audio file and click Generate.",
        "running": "Processing your audio… grab a coffee ☕",
        "success": "Pipeline completed successfully!",
        "error":   "Something went wrong. Check the messages below.",
    }
    st.markdown(
        f'<div class="status-banner {status}">'
        f'<span style="font-size:1.2rem;">{_ICONS.get(status,"")}</span>'
        f'<span>{_TEXTS.get(status,"")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Progress flow (gradient card matching reference image) ────────────────
    steps  = ["Upload", "ASR (Whisper)", "Summarizing", "Smart Notes", "Done"]
    states = ["todo"] * 5
    if status == "idle":
        states[0] = "current"
    elif status == "running":
        states[:3] = ["done", "done", "current"]
    elif status == "success":
        states = ["done"] * 5
    elif status == "error":
        if transcript_val.startswith("[ERROR]"):
            states[0] = "done"; states[1] = "error"
        else:
            states[0] = "done"; states[1] = "done"; states[2] = "error"

    nodes = [
        f'<div class="flow-step">'
        f'<span class="flow-dot {states[i]}">{i+1}</span>'
        f'<span class="flow-label">{steps[i]}</span>'
        f'</div>'
        for i in range(len(steps))
    ]
    lines = [
        '<span class="flow-line'
        + (' done' if states[i] in ("done","error") and states[i+1] in ("done","error","current") else "")
        + '"></span>'
        for i in range(len(steps) - 1)
    ]
    timeline = "".join(nodes[i] + (lines[i] if i < len(lines) else "") for i in range(len(steps)))

    rocket_uri  = _sticker_uri("fusee.png")
    rocket_html = f'<img src="{rocket_uri}" style="height:72px;flex-shrink:0;" />' if rocket_uri else ""

    st.markdown(
        f'<div class="progress-card">'
        f'{rocket_html}'
        f'<div class="flow-row" style="flex:1;">{timeline}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Result panels ─────────────────────────────────────────────────────────
    micro_uri    = _sticker_uri("micro.png")
    checklist_uri = _sticker_uri("carnet avec crayon.png") or _sticker_uri("livre.png")

    micro_html     = f'<img class="panel-sticker" src="{micro_uri}" />'     if micro_uri     else ""
    checklist_html = f'<img class="panel-sticker" src="{checklist_uri}" />' if checklist_uri else ""

    def _panel(panel_cls, badge_cls, badge, title, text, sticker_html="", extra_cls=""):
        is_empty = not text.strip()
        body     = html_lib.escape(text) if not is_empty else "Results will appear here after the pipeline runs…"
        txt_cls  = f"result-text {extra_cls} {'empty' if is_empty else ''}".strip()
        return (
            f'<div class="panel-wrap {panel_cls}">'
            f'<span class="panel-badge {badge_cls}">{badge}</span>'
            f'<p class="panel-title">{title}</p>'
            f'<div class="{txt_cls}">{body}</div>'
            f'{sticker_html}'
            f'</div>'
        )

    left_col, right_col = st.columns(2, gap="large")

    with left_col:
        st.markdown(
            _panel("panel-purple", "badge-purple", "Whisper Output",
                   "🎙️ Transcript", transcript_val, micro_html),
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            _panel("panel-green", "badge-green", "AI Summary",
                   "📝 Summary / Smart Notes", notes_val, checklist_html, "green-bg"),
            unsafe_allow_html=True,
        )

    # ── Alerts ────────────────────────────────────────────────────────────────
    if status == "error":
        st.error("Pipeline finished with errors. Please check the messages above.")
    elif status == "success":
        st.success("Pipeline completed successfully! 🎉")

    # ── Integration contract ──────────────────────────────────────────────────
    with st.expander("Integration Contract", expanded=False):
        st.markdown(
            """
            - `from asr import transcribe` → `transcribe(audio_path: str) -> str`
            - `from summarization import summarize` → `summarize(text: str) -> str`

            Optional parameters supported when available:
            - `transcribe(audio_path: str, model_size: str = "base")`
            - `summarize(text: str, model_key: str = "bart")`
            """
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: NOTES HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif current_page == "history":

    st.markdown(
        '<div class="card">'
        '<p class="page-title">🗂️ Notes History</p>'
        '<p style="color:#6b7a9e;font-weight:600;margin:0;">All your previously generated smart notes, newest first.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    history = st.session_state.get("history", [])

    if not history:
        st.markdown(
            """
            <div class="card" style="text-align:center;padding:2.5rem 1.5rem;">
                <p style="font-size:2.5rem;margin:0;">📭</p>
                <p style="font-family:'Baloo 2',cursive;font-size:1.3rem;font-weight:700;color:#3d4e79;margin:0.5rem 0 0.2rem 0;">
                    No notes yet
                </p>
                <p style="color:#8a96b8;font-size:0.9rem;margin:0;">
                    Head over to <a href="?page=smart_notes" style="color:#6347c7;font-weight:700;">Smart Notes</a>
                    and run your first audio file.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for item in reversed(history):
            t_safe = html_lib.escape(item["transcript"])
            n_safe = html_lib.escape(item["smart_notes"])
            st.markdown(
                f"""
                <div class="history-item">
                    <div class="history-meta">📎 {item["name"]} &nbsp;·&nbsp; 🕐 {item["timestamp"]}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;">
                        <div>
                            <p style="font-family:'Baloo 2',cursive;font-weight:700;font-size:0.95rem;
                                      color:#3d4e79;margin:0 0 0.3rem 0;">🎙️ Transcript</p>
                            <div class="history-text">{t_safe}</div>
                        </div>
                        <div>
                            <p style="font-family:'Baloo 2',cursive;font-weight:700;font-size:0.95rem;
                                      color:#3d4e79;margin:0 0 0.3rem 0;">📝 Smart Notes</p>
                            <div class="history-text" style="background:rgba(246,255,250,0.92);border-color:#c8e8d2;">{n_safe}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.button("🗑️ Clear history", type="primary"):
            st.session_state["history"] = []
            _save_history_to_disk([])  # Clear disk history as well
            print("[INFO] History cleared")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HELP & DOCS
# ══════════════════════════════════════════════════════════════════════════════
elif current_page == "help":

    st.markdown(
        '<div class="card">'
        '<p class="page-title">❔ Help & Docs</p>'
        '<p style="color:#6b7a9e;font-weight:600;margin:0;">Everything you need to know about Smart Notes Generator.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Section 1: How it works
    st.markdown(
        """
        <div class="card">
            <div class="help-section">
                <h3>🚀 How it works</h3>
                <ol>
                    <li><strong>Upload</strong> an audio file (MP3, WAV, M4A or FLAC, max 200 MB).</li>
                    <li>Click <strong>Generate Smart Notes</strong>.</li>
                    <li>The app transcribes your audio using <strong>OpenAI Whisper</strong> (ASR).</li>
                    <li>The transcript is then summarized by a <strong>fine-tuned BART model</strong>.</li>
                    <li>Both the full transcript and the smart notes appear in the result panels.</li>
                </ol>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 2: Whisper model
    st.markdown(
        """
        <div class="card">
            <div class="help-section">
                <h3>🎙️ Choosing a Whisper model</h3>
                <p>Use the <em>ASR model (Whisper)</em> dropdown in the sidebar:</p>
                <ul>
                    <li><strong>tiny / base</strong> — fastest, good for short clear recordings.</li>
                    <li><strong>small / medium</strong> — better accuracy, slightly slower.</li>
                    <li><strong>large</strong> — highest accuracy, slowest (requires a GPU for comfort).</li>
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 3: Notes History
    st.markdown(
        """
        <div class="card">
            <div class="help-section">
                <h3>🗂️ Notes History</h3>
                <p>Every successful pipeline run is saved automatically to the Notes History page for the duration of your session. History is cleared when you close the browser tab.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 4: Integration contract
    st.markdown(
        """
        <div class="card">
            <div class="help-section">
                <h3>⚙️ Integration contract</h3>
                <p>The app expects two Python modules in the same directory:</p>
                <ul>
                    <li><code>asr.py</code> — exposes <code>transcribe(audio_path: str) → str</code></li>
                    <li><code>summarization.py</code> — exposes <code>summarize(text: str) → str</code></li>
                </ul>
                <p>Both functions may optionally accept extra keyword arguments (<code>model_size</code>, <code>model_key</code>) that the app will pass automatically when detected.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section 5: Troubleshooting
    st.markdown(
        """
        <div class="card">
            <div class="help-section">
                <h3>🐛 Troubleshooting</h3>
                <ul>
                    <li>If transcription fails, check that <code>ffmpeg</code> is installed and on your PATH.</li>
                    <li>If the summary is blank or very short, try a longer audio clip.</li>
                    <li>Out-of-memory errors → switch to a smaller Whisper model in the sidebar.</li>
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )