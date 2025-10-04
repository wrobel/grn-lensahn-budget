
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Sequence

import pandas as pd
import pdfplumber

PDF_DIR = Path("input/balance")
OUTPUT_DIR = Path("analysis/ertragslage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NUMBER_PATTERN = re.compile(r"^-?(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}-?$")
COLUMN_HEADER_PATTERN = re.compile(r"^(?:\d{4}|Differenz)$", re.IGNORECASE)


def clean_number(token: str) -> str:
    """Normalise a numeric token by moving a trailing hyphen to the front."""
    token = token.strip()
    if token.endswith("-"):
        token = "-" + token[:-1]
    return token


def group_words_by_line(words: Sequence[dict], y_tolerance: float = 1.5) -> List[List[dict]]:
    sorted_words = sorted(
        words,
        key=lambda w: (w.get("__page_index__", 0), w["top"], w["x0"]),
    )
    lines: List[List[dict]] = []
    for word in sorted_words:
        if not lines:
            lines.append([word])
            continue
        last_line = lines[-1]
        if (
            word.get("__page_index__", 0) == last_line[0].get("__page_index__", 0)
            and abs(word["top"] - last_line[0]["top"]) <= y_tolerance
        ):
            last_line.append(word)
        else:
            lines.append([word])
    return lines


def extract_section_words(
    pdf: pdfplumber.PDF, section_label: str = "6.4", next_section: str = "6.5"
) -> List[dict]:
    total_pages = len(pdf.pages)
    search_start = max(0, total_pages - 60)
    start_index = None

    for idx in range(search_start, total_pages):
        words = pdf.pages[idx].extract_words(use_text_flow=True) or []
        tokens = {w["text"].strip() for w in words}
        if any(token.startswith(section_label) for token in tokens) and "Ertragslage" in tokens:
            start_index = idx
            break
    if start_index is None:
        raise ValueError(f"Section '{section_label} Ertragslage' not found")

    collected: List[dict] = []
    for page_idx in range(start_index, total_pages):
        words = pdf.pages[page_idx].extract_words(use_text_flow=True) or []
        cutoff = None
        for word in words:
            token = word["text"].strip()
            if token.startswith(next_section):
                cutoff = word["top"]
                break
        for word in words:
            if cutoff is not None and word["top"] >= cutoff:
                continue
            word_copy = dict(word)
            word_copy["__page_index__"] = page_idx
            collected.append(word_copy)
        if cutoff is not None:
            break
    return collected


def parse_ertragslage_words(words: Sequence[dict]) -> tuple[List[str], List[List[str]]]:
    lines = group_words_by_line(words)
    columns: List[str] | None = None
    rows: List[List[str]] = []

    for line in lines:
        tokens = [word["text"].strip() for word in sorted(line, key=lambda w: w["x0"])]
        if not tokens:
            continue
        if tokens[0] in {"Gemeinde", "Lagebericht", "Seite", "erstellt"}:
            continue
        if tokens[:2] == ["6.4", "Ertragslage"]:
            continue
        while tokens and tokens[0] in {"6.4", "6,4"}:
            tokens = tokens[1:]
        if tokens and tokens[0] == "Ertragslage":
            tokens = tokens[1:]
        if all(COLUMN_HEADER_PATTERN.match(token) for token in tokens):
            columns = tokens
            continue

        numeric_tokens: List[str] = []
        label_end = len(tokens)
        for index in range(len(tokens) - 1, -1, -1):
            token = tokens[index]
            if NUMBER_PATTERN.match(token):
                numeric_tokens.insert(0, clean_number(token))
                label_end = index
            else:
                break
        if not numeric_tokens:
            continue
        label_tokens = tokens[:label_end]
        label = " ".join(label_tokens).strip()
        if not label:
            continue
        rows.append([label, *numeric_tokens])

    if columns is None:
        raise ValueError("Column header row not found in section")
    if len(columns) != 3:
        raise ValueError(f"Unexpected number of columns: {columns}")

    return columns, rows


def extract_ertragslage(pdf_path: Path) -> pd.DataFrame:
    with pdfplumber.open(pdf_path) as pdf:
        words = extract_section_words(pdf)
    columns, rows = parse_ertragslage_words(words)
    data = []
    for row in rows:
        if len(row) != 4:
            raise ValueError(f"Unexpected row structure: {row}")
        data.append(row)
    df = pd.DataFrame(data, columns=["Kategorie", *columns])
    return df


def main() -> None:
    pdf_files = sorted(PDF_DIR.glob("Schlussbilanz *.pdf"))
    for pdf_file in pdf_files:
        year_match = re.search(r"(20\d{2})", pdf_file.stem)
        if not year_match:
            continue
        year = year_match.group(1)
        df = extract_ertragslage(pdf_file)
        output_path = OUTPUT_DIR / f"ertragslage_{year}.csv"
        df.to_csv(output_path, index=False)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
