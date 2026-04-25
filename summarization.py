import os

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODELS = {
    "bart": "facebook/bart-large-cnn",
    "distilbart": "sshleifer/distilbart-cnn-12-6",
}

# If set, this can be either a local path or a Hugging Face model id.
FT_MODEL_SOURCE = os.getenv("SMART_NOTES_FT_MODEL", "").strip()

if FT_MODEL_SOURCE:
    MODELS["bart-ft"] = FT_MODEL_SOURCE
elif os.path.isdir("finetuned-bart-samsum"):
    MODELS["bart-ft"] = "./finetuned-bart-samsum"

DEFAULT_MODEL = "bart-ft" if "bart-ft" in MODELS else "bart"
MIN_WORDS_TO_SUMMARIZE = 30

_PIPELINES = {}
DEVICE = 0 if torch.cuda.is_available() else -1
_DEVICE_STR = "cuda" if torch.cuda.is_available() else "cpu"


def available_models() -> list:
    """Return available model keys for UI dropdowns."""
    return list(MODELS.keys())


def _get_pipeline(model_key: str):
    if model_key not in MODELS:
        raise ValueError(f"Unknown model key '{model_key}'. Choose from: {list(MODELS.keys())}")

    if model_key not in _PIPELINES:
        print(f"[summarization] loading model: {MODELS[model_key]}")
        tokenizer = AutoTokenizer.from_pretrained(MODELS[model_key])
        model = AutoModelForSeq2SeqLM.from_pretrained(MODELS[model_key])
        model = model.to(_DEVICE_STR)
        model.eval()
        _PIPELINES[model_key] = (tokenizer, model)

    return _PIPELINES[model_key]


def _compute_lengths(text: str) -> tuple:
    n_words = len(text.split())
    max_len = max(40, min(200, int(n_words * 0.40)))
    min_len = max(15, min(60, int(n_words * 0.15)))
    min_len = min(min_len, max_len - 5)
    return max_len, min_len


def summarize(text: str, model_key: str = DEFAULT_MODEL) -> str:
    """Summarize transcript text into plain-string smart notes."""
    if not text or not text.strip():
        return "[ERROR] Empty input. Please provide a non-empty transcript."

    if len(text.split()) < MIN_WORDS_TO_SUMMARIZE:
        return text.strip()

    try:
        tokenizer, model = _get_pipeline(model_key)
        max_length, min_length = _compute_lengths(text)

        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=1024,
        )
        inputs = {k: v.to(_DEVICE_STR) for k, v in inputs.items()}

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_length,
                min_new_tokens=min_length,
                num_beams=6,
                length_penalty=2.0,
                no_repeat_ngram_size=3,
                early_stopping=True,
                do_sample=False,
            )

        summary = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return summary.strip()
    except Exception as exc:
        return f"[ERROR] {exc}"


def summarize_batch(texts: list, model_key: str = DEFAULT_MODEL) -> list:
    return [summarize(text, model_key=model_key) for text in texts]