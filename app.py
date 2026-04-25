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

st.title("Smart Notes Generator")
st.caption("Speech -> Transcript -> Smart Notes")

st.sidebar.header("Model Settings")
asr_model_size = st.sidebar.selectbox(
    "ASR model (Whisper)",
    options=["tiny", "base", "small", "medium", "large"],
    index=1,
)

summary_model_options = ["bart", "distilbart"]
if callable(available_models):
    try:
        detected = available_models()
        if detected:
            summary_model_options = detected
    except Exception:
        pass

summary_model_key = st.sidebar.selectbox(
    "Summarization model",
    options=summary_model_options,
    index=summary_model_options.index("bart-ft") if "bart-ft" in summary_model_options else 0,
)

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
            st.text_area("", value=transcript, height=400, key="transcript")

        with right_col:
            st.subheader("Summary / Smart Notes")
            st.text_area("", value=smart_notes, height=400, key="summary")

        if transcript.startswith("[ERROR]") or smart_notes.startswith("[ERROR]"):
            st.error("Pipeline finished with errors. Please check messages above.")
        else:
            st.success("Pipeline completed.")

st.divider()
st.markdown(
    """
    ### Integration Contract
    - `from asr import transcribe` should expose a function compatible with `transcribe(audio_path: str) -> str`
    - `from summarization import summarize` should expose a function compatible with `summarize(text: str) -> str`

    Optional parameters are supported when available:
    - `transcribe(audio_path: str, model_size: str = "base")`
    - `summarize(text: str, model_key: str = "bart")`
    """
)
