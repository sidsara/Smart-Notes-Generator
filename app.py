import tempfile
import inspect
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


def _get_sticker_paths() -> list[str]:
    preferred = [
        "focus-on-the-good.png",
        "online-learning.png",
        "notes (1).png",
        "notes (2).png",
        "laptop.png",
        "medal.png",
        "focus.png",
    ]
    paths = []
    for name in preferred:
        path = STICKERS_DIR / name
        if path.exists():
            paths.append(str(path))
    return paths


st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700&family=Nunito:wght@400;600;700&display=swap');

        .stApp {
            background:
                radial-gradient(circle at 12% 18%, #ffd9ec 0%, transparent 28%),
                radial-gradient(circle at 86% 12%, #d3f5ff 0%, transparent 32%),
                radial-gradient(circle at 24% 88%, #d9ffd6 0%, transparent 25%),
                linear-gradient(145deg, #fff8f5 0%, #f5fbff 52%, #fbfff6 100%);
            font-family: 'Nunito', sans-serif;
        }

        h1, h2, h3 {
            font-family: 'Baloo 2', cursive !important;
            color: #2a3555;
            letter-spacing: 0.3px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f9e4ff 0%, #e8f4ff 44%, #e9ffe9 100%);
            border-right: 1px solid rgba(120, 140, 180, 0.2);
        }

        [data-testid="stFileUploaderDropzone"] {
            border: 2px dashed #9eb4f0;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.65);
        }

        .stButton > button {
            border: none;
            border-radius: 14px;
            padding: 0.78rem 1.2rem;
            font-weight: 700;
            background: linear-gradient(90deg, #ff8fb2 0%, #ffb87a 52%, #ffd166 100%);
            color: #2e2442;
            box-shadow: 0 8px 18px rgba(255, 143, 178, 0.25);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 22px rgba(255, 143, 178, 0.36);
        }

        .hero-card {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(150, 170, 220, 0.32);
            border-radius: 20px;
            padding: 1.15rem 1.3rem 0.8rem 1.3rem;
            box-shadow: 0 10px 26px rgba(110, 130, 180, 0.12);
            margin-bottom: 0.9rem;
        }

        .hero-title {
            font-family: 'Baloo 2', cursive;
            font-size: 2.8rem;
            font-weight: 700;
            color: #273252;
            margin: 0;
            line-height: 1.1;
        }

        .hero-sub {
            margin: 0.35rem 0 0;
            color: #546082;
            font-size: 1.08rem;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.72rem;
        }

        .chip {
            background: linear-gradient(90deg, #ffe9f3 0%, #e9f4ff 100%);
            border: 1px solid #d4e3ff;
            color: #40537f;
            padding: 0.33rem 0.68rem;
            border-radius: 999px;
            font-size: 0.88rem;
            font-weight: 700;
        }

        [data-testid="stTextArea"] textarea {
            border-radius: 16px;
            border: 1px solid #d7e4ff;
            background: rgba(255, 255, 255, 0.84);
            box-shadow: inset 0 2px 8px rgba(130, 150, 190, 0.08);
            color: #20304f;
        }

        .result-tag {
            display: inline-block;
            background: linear-gradient(90deg, #e9f8ff 0%, #f1ffe9 100%);
            border: 1px solid #cde9d9;
            color: #3c5874;
            font-weight: 700;
            font-size: 0.82rem;
            padding: 0.24rem 0.62rem;
            border-radius: 999px;
            margin-bottom: 0.35rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
        <p class="hero-title">Smart Notes Generator</p>
        <p class="hero-sub">Colorful AI workspace: Speech -> Transcript -> Smart Notes</p>
        <div class="chip-row">
            <span class="chip">Upload Audio</span>
            <span class="chip">Whisper ASR</span>
            <span class="chip">Fine-tuned Summarization</span>
            <span class="chip">Study Faster</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

stickers = _get_sticker_paths()
if stickers:
    sticker_cols = st.columns(min(4, len(stickers)))
    for idx, col in enumerate(sticker_cols):
        with col:
            st.image(stickers[idx], width=86)

st.sidebar.header("Model Settings")
asr_model_size = st.sidebar.selectbox(
    "ASR model (Whisper)",
    options=["tiny", "base", "small", "medium", "large"],
    index=1,
)

summary_model_key = "bart-ft"
if callable(available_models):
    try:
        detected = available_models()
        if "bart-ft" not in detected:
            summary_model_key = detected[0] if detected else "bart"
            st.sidebar.warning(
                f"bart-ft not detected locally. Falling back to: {summary_model_key}"
            )
    except Exception:
        summary_model_key = "bart"
        st.sidebar.warning("Could not detect bart-ft. Falling back to bart.")

st.sidebar.caption(f"Summarization model in use: {summary_model_key}")

if stickers:
    st.sidebar.image(stickers[-1], width=110)
    st.sidebar.caption("Pastel mode powered by your stickers")

uploaded_file = st.file_uploader(
    "Upload an audio file",
    type=["mp3", "wav", "m4a"],
    help="Supported formats: mp3, wav, m4a",
)

run_pipeline = st.button("Run pipeline", type="primary", use_container_width=True)

if run_pipeline:
    if uploaded_file is None:
        st.warning("Please upload an audio file first.")
    else:
        suffix = Path(uploaded_file.name).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.read())
            temp_audio_path = tmp.name

        with st.spinner("Running ASR + summarization..."):
            transcribe_signature = inspect.signature(transcribe)
            if "model_size" in transcribe_signature.parameters:
                transcript = transcribe(temp_audio_path, model_size=asr_model_size)
            else:
                transcript = transcribe(temp_audio_path)

            if transcript.startswith("[ERROR]"):
                smart_notes = "[ERROR] Summary skipped because transcription failed."
            else:
                summarize_signature = inspect.signature(summarize)
                if "model_key" in summarize_signature.parameters:
                    smart_notes = summarize(transcript, model_key=summary_model_key)
                else:
                    smart_notes = summarize(transcript)

        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("Transcript")
            st.text_area(
                "Transcript output",
                value=transcript,
                height=400,
                key="transcript",
                label_visibility="collapsed",
            )

        with right_col:
            st.markdown('<span class="result-tag">Smart Notes Panel</span>', unsafe_allow_html=True)
            st.subheader("Summary / Smart Notes")
            st.text_area(
                "Summary output",
                value=smart_notes,
                height=400,
                key="summary",
                label_visibility="collapsed",
            )

        if transcript.startswith("[ERROR]") or smart_notes.startswith("[ERROR]"):
            st.error("Pipeline finished with errors. Please check messages above.")
        else:
            st.success("Pipeline completed.")

st.divider()
with st.expander("Integration Contract", expanded=False):
    st.markdown(
        """
        - from asr import transcribe  -> transcribe(audio_path: str) -> str
        - from summarization import summarize  -> summarize(text: str) -> str

        Optional parameters are supported when available:
        - transcribe(audio_path: str, model_size: str = "base")
        - summarize(text: str, model_key: str = "bart")
        """
    )
