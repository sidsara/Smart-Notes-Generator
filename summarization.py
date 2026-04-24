def summarize(text: str) -> str:
    """Mock summarization function. Replace with teammate implementation."""
    clean_text = text.strip()
    if not clean_text:
        return "[MOCK SUMMARY] No transcript content provided."

    excerpt = clean_text[:220]
    return f"[MOCK SUMMARY] {excerpt}..."