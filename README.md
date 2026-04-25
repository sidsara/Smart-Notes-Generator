# 📝 Smart Notes Generator: Audio to Impact

**Smart Notes Generator** is an AI-powered workspace designed to transform spoken words into structured, actionable insights. By leveraging state-of-the-art NLP models, this platform handles the entire pipeline from raw audio to refined, smart summaries.

## 🚀 The Pipeline
1. **Audio Ingestion:** Supports `mp3`, `wav`, `m4a`, and `flac` formats.
2. **Speech Transcription (ASR):** Powered by **OpenAI Whisper** for high-accuracy text extraction.
3. **Fine-tuned Summarization:** Uses a specialized **BART** model fine-tuned on the **SAMSum** dataset (housed in `finetuned-bart-samsum/`) to generate concise, human-like notes.

---

## 🎨 Interface & Demo
The application is built with **Streamlit**, featuring a side-by-side view of the full transcript and the generated smart notes.

### Model Settings
Users can configure the pipeline directly from the sidebar:
* **ASR Model (Whisper):** Select from `tiny`, `base`, `small`, `medium`, or `large` sizes.
* **Summarization:** Features our custom **bart-ft** (Fine-Tuned) model for superior summary quality compared to vanilla models.

![App Screenshot](assets/app-screenshot.png)


---

## 🛠️ Project Structure
- `app.py`: The main Streamlit interface and UI logic.
- `asr.py`: Module handling the Whisper ASR engine (`transcribe(...)`).
- `summarization.py`: Module managing the BART model and inference (`summarize(...)`).
- `finetuned-bart-samsum/`: Local directory containing the weights for the fine-tuned summarization model.
- `requirements.txt`: Python dependencies (PyTorch, Transformers, OpenAI-Whisper, etc.).
- `packages.txt`: System-level dependencies (`ffmpeg`) required for Whisper runtime.

---

## 💻 Local Setup

1. **Environment Setup:**
```bash
conda activate study
pip install -r requirements.txt
```

2. **GPU Acceleration:**
The pipeline is optimized for CUDA. If an NVIDIA GPU is detected, the models will automatically load onto `cuda` for significantly faster inference.

3. **Run the App:**
```bash
streamlit run app.py
```
Then open the local URL shown in the terminal (usually `http://localhost:8501`).

---

## 🤝 Integration Contract
The `app.py` interface imports the following functions:

```python
from asr import transcribe
from summarization import summarize

# ASR behavior:
# transcribe(audio_path: str, model_size: str = "base") -> str

# Summarization behavior:
# summarize(text: str, model_key: str = "bart-ft") -> str
```

---

## ☁️ Deployment
This project is configured for **Streamlit Community Cloud**:
1. Push the code to your GitHub repository.
2. Connect your GitHub account to [share.streamlit.io](https://share.streamlit.io).
3. Ensure `packages.txt` is present so the cloud environment installs `ffmpeg` for audio processing.

---

## 📄 Final Report Assembly
The following sections are required for the final deliverable:
1. **Introduction:** Problem statement and project goals.
2. **Methodology:** Pipeline overview (Audio → Whisper ASR → BART Summarization).
3. **ASR Module:** Implementation details and model size trade-offs.
4. **Summarization Module:** Details on the BART fine-tuning process and the SAMSum dataset.
5. **Deployment & Workflow:** GitHub collaboration and Streamlit Cloud setup.
6. **Results:** Qualitative examples of transcripts and generated notes.
7. **Future Scope:** Improvements like speaker diarization and evaluation metrics (ROUGE/BERTScore).
