import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = ROOT / "data" / "raw" / "zpp_2300_1_article_25.txt"
OUTPUT_FILE = ROOT / "data" / "chunks.jsonl"


@dataclass(frozen=True)
class ArticleConfig:
    source_id: str
    document_title: str
    article: str
    heading: str
    source_url: str
    accessed_at: str
    edition_date: str | None
    chunk_ids: dict[str, str]


ARTICLE_25 = ArticleConfig(
    source_id="zpp_2300_1_pravo_gov",
    document_title="Закон Российской Федерации от 07.02.1992 № 2300-1 «О защите прав потребителей»",
    article="25",
    heading="Право потребителя на обмен товара надлежащего качества",
    source_url="http://pravo.gov.ru/proxy/ips/?docbody=&nd=102014512",
    accessed_at="2026-09-25",
    edition_date=None,
    chunk_ids={
        "1": "zpp_2300_1_art_25_p1",
        "2": "zpp_2300_1_art_25_p2",
    },
)


def normalize_text(raw_text: str) -> str:
    text = raw_text.replace("\u00a0", " ")
    text = "\n".join(line.rstrip(" \t") for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_article_text(normalized_text: str, config: ArticleConfig) -> str:
    heading = f"Статья {config.article}. {config.heading}"
    if heading not in normalized_text:
        raise ValueError(f"Heading not found: {heading}")
    return normalized_text.split(heading, maxsplit=1)[1]


def extract_paragraphs(article_text: str) -> tuple[str, str]:
    lines = article_text.splitlines()
    while lines and not lines[0].strip():
        lines = lines[1:]

    first_index = next(
        (index for index, line in enumerate(lines) if re.match(r"^\s*1\.\s+", line)),
        None,
    )
    if first_index is None:
        raise ValueError("Paragraph 1 not found.")

    second_index = next(
        (
            index
            for index in range(first_index + 1, len(lines))
            if re.match(r"^\s*2\.\s+", lines[index])
        ),
        None,
    )
    if second_index is None:
        raise ValueError("Paragraph 2 not found.")

    paragraph_1 = "\n".join(lines[first_index:second_index]).strip()
    paragraph_2 = "\n".join(lines[second_index:]).strip()

    if not paragraph_1 or not paragraph_2:
        raise ValueError("Could not isolate both paragraphs.")

    return paragraph_1, paragraph_2


def build_chunk_record(paragraph: str, text: str, config: ArticleConfig) -> dict[str, object]:
    return {
        "chunk_id": config.chunk_ids[paragraph],
        "source_id": config.source_id,
        "document_title": config.document_title,
        "article": config.article,
        "paragraph": paragraph,
        "heading": config.heading,
        "text": text,
        "source_url": config.source_url,
        "accessed_at": config.accessed_at,
        "edition_date": config.edition_date,
    }


def write_chunks(chunks: list[dict[str, object]]) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = OUTPUT_FILE.with_suffix(".jsonl.tmp")

    with temp_file.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False))
            handle.write("\n")

    temp_file.replace(OUTPUT_FILE)


def main() -> None:
    if not RAW_FILE.exists():
        raise SystemExit(f"Input file not found: {RAW_FILE}")

    raw_text = RAW_FILE.read_text(encoding="utf-8")
    normalized_text = normalize_text(raw_text)
    article_text = extract_article_text(normalized_text, ARTICLE_25)
    paragraph_1, paragraph_2 = extract_paragraphs(article_text)

    chunks = [
        build_chunk_record("1", paragraph_1, ARTICLE_25),
        build_chunk_record("2", paragraph_2, ARTICLE_25),
    ]
    write_chunks(chunks)
    print("Created data/chunks.jsonl with 2 chunks.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc
