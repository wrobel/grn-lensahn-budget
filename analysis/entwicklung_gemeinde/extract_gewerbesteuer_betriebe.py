from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
import pdfplumber

PDF_DIR = Path("input/balance")
OUTPUT_DIR = Path("analysis/entwicklung_gemeinde")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SECTION_HEADING = "6.8 Entwicklung der Gemeinde"
STATEMENT_ANCHOR = "Bei der Gewerbesteuer ergibt sich"
LINE_PATTERN = re.compile(r"^(?P<count>\d+)\s+(?P<label>.+?)\s+(?P<share>\d+,\d+)\s%$")


def find_section_page(pdf: pdfplumber.PDF) -> int:
    total_pages = len(pdf.pages)
    search_window = range(max(0, total_pages - 12), total_pages)
    for index in search_window:
        text = pdf.pages[index].extract_text() or ""
        if SECTION_HEADING in text:
            return index
    raise ValueError(f"Section '{SECTION_HEADING}' not found")


def parse_statistic_lines(lines: Iterable[str]) -> Dict[str, int]:
    categories: "OrderedDict[str, int]" = OrderedDict()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        match = LINE_PATTERN.match(line)
        if not match:
            continue
        label = match.group("label").strip()
        if not label:
            continue
        label = re.sub(r"^[Bb]etriebe\s+", "", label)
        if label == "100,00":
            continue
        count = int(match.group("count"))
        categories[label] = count
    if not categories:
        raise ValueError("No statistic rows parsed from section")
    return categories


def extract_gewerbesteuer_counts(pdf_path: Path) -> Dict[str, int]:
    with pdfplumber.open(pdf_path) as pdf:
        section_page = find_section_page(pdf)
        text = pdf.pages[section_page].extract_text() or ""
    anchor_index = text.find(STATEMENT_ANCHOR)
    if anchor_index == -1:
        raise ValueError(
            f"Anchor text '{STATEMENT_ANCHOR}' not found on section page in {pdf_path.name}"
        )
    relevant_text = text[anchor_index:].splitlines()
    return parse_statistic_lines(relevant_text[1:])




def dataframe_to_markdown(df: pd.DataFrame) -> str:
    headers = [df.index.name or "Kategorie", *df.columns.tolist()]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
    for index, row in df.iterrows():
        values = [index, *row.tolist()]
        formatted = []
        for value in values:
            if value is pd.NA or (isinstance(value, float) and pd.isna(value)):
                formatted.append('')
            else:
                formatted.append(str(int(value)) if isinstance(value, (int, float)) and float(value).is_integer() else str(value))
        lines.append('| ' + ' | '.join(formatted) + ' |')
    return '\n'.join(lines)

def build_dataframe(counts_by_year: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    ordered_categories: list[str] = []
    for year in sorted(counts_by_year.keys()):
        for category in counts_by_year[year].keys():
            if category not in ordered_categories:
                ordered_categories.append(category)
    data = {
        year: [counts_by_year[year].get(category, pd.NA) for category in ordered_categories]
        for year in sorted(counts_by_year.keys())
    }
    df = pd.DataFrame(data, index=ordered_categories)
    df.index.name = "Kategorie"
    return df


def main() -> None:
    counts_by_year: Dict[str, Dict[str, int]] = {}
    for pdf_file in sorted(PDF_DIR.glob("Schlussbilanz *.pdf")):
        year_match = re.search(r"(20\d{2})", pdf_file.stem)
        if not year_match:
            continue
        year = year_match.group(1)
        print(f"Processing {year} ({pdf_file.name})")
        counts_by_year[year] = extract_gewerbesteuer_counts(pdf_file)
    if not counts_by_year:
        raise SystemExit("No PDF files processed")
    df = build_dataframe(counts_by_year)
    csv_path = OUTPUT_DIR / "gewerbesteuer_betriebe.csv"
    df.to_csv(csv_path)
    markdown_path = OUTPUT_DIR / "gewerbesteuer_betriebe.md"
    markdown_path.write_text(dataframe_to_markdown(df) + "\n")
    print(f"Wrote {csv_path}")
    print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()
