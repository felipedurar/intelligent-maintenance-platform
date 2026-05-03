from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    text: str
    source: str
    chunk_index: int


def discover_markdown_files(paths: list[str], base_dir: str | Path = ".") -> list[Path]:
    root = Path(base_dir)
    files: list[Path] = []
    for raw_path in paths:
        path = root / raw_path
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            files.append(path)
        if path.is_dir():
            files.extend(
                file for file in path.rglob("*") if file.suffix.lower() in {".md", ".txt"}
            )
    return sorted(set(files))


def _chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = current[-overlap_chars:] if overlap_chars > 0 else ""

        if len(paragraph) <= max_chars:
            current = f"{current}\n\n{paragraph}".strip() if current else paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = start + max_chars
            chunks.append(paragraph[start:end].strip())
            start = max(end - overlap_chars, end)
        current = ""

    if current:
        chunks.append(current)

    return chunks


def load_document_chunks(
    paths: list[str],
    base_dir: str | Path = ".",
    max_chars: int = 1200,
    overlap_chars: int = 150,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for file_path in discover_markdown_files(paths, base_dir):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        relative_source = str(file_path.relative_to(Path(base_dir)))
        for index, chunk_text in enumerate(_chunk_text(text, max_chars, overlap_chars)):
            chunks.append(
                DocumentChunk(
                    id=f"{relative_source}:{index}",
                    text=chunk_text,
                    source=relative_source,
                    chunk_index=index,
                )
            )
    return chunks
