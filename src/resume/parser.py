from pathlib import Path


def load_resume_text(path: str | Path) -> str:
    """Load plain text from PDF, DOCX, or TXT resume files."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace").strip()

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError("PDF contained no extractable text.")
        return text

    if suffix in {".docx", ".doc"}:
        from docx import Document

        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
        if not text:
            raise ValueError("DOCX contained no text.")
        return text

    raise ValueError(f"Unsupported format: {suffix}. Use .pdf, .docx, or .txt")
