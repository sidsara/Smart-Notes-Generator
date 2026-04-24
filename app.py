import tempfile
from pathlib import Path

import streamlit as st

# Team integration: use real modules when available, otherwise fall back to mocks.
try:
    from asr import transcribe  # type: ignore
except Exception:
    def transcribe(audio_path: str) -> str:
        return f"[MOCK TRANSCRIPT] Audio received: {audio_path}. This is a sample transcript."

try:
    from summarization import summarize  # type: ignore
except Exception:
    def summarize(text: str) -> str:
        return f"[MOCK SUMMARY] {text[:180]}..."


st.set_page_config(page_title="Smart Notes Generator", page_icon="🎙️", layout="wide")

st.title("Smart Notes Generator")
st.caption("Speech -> Transcript -> Smart Notes")

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
            transcript = transcribe(temp_audio_path)
            smart_notes = summarize(transcript)

        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("Transcript")
            st.text_area("", value=transcript, height=400, key="transcript")

        with right_col:
            st.subheader("Summary / Smart Notes")
            st.text_area("", value=smart_notes, height=400, key="summary")

        st.success("Pipeline completed.")

st.divider()
st.markdown(
    """
    ### Integration Contract
    - `from asr import transcribe` should expose a function compatible with `transcribe(audio_path: str) -> str`
    - `from summarization import summarize` should expose a function compatible with `summarize(text: str) -> str`

    If these files are not yet present, the app uses mock functions so the UI can still be tested.
    """
)
