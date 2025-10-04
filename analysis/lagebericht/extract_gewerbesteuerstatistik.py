"""Extracts Gewerbesteuer category counts from Schlussbilanz PDFs."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

import pdfplumber

PDF_DIR = Path("input/balance")
OUTPUT_CSV = Path("analysis/lagebericht/gewerbesteuer_betriebe_counts.csv")
CATEGORY_PATTERN = re.compile(r"^(?P<count>\d+)\s+(?P<label>.*?)\s+(?P<percent>\d{1,3},\d{2})\s*%$")


class ExtractionError(Exception):
    """Raised when the expected table cannot be located."""


def clean_label(raw: str) -> str:
    label = raw.strip()
    if label.lower().startswith("betriebe "):
        label = label[len("betriebe ") :]
    return " ".join(label.split())


def iter_gewerbesteuer_rows(text_lines: Iterable[str]) -> Iterable[tuple[str, int]]:
    capture = False
    for line in text_lines:
        if "Bei der Gewerbesteuer ergibt sich" in line:
            capture = True
            continue
        if not capture:
            continue
        match = CATEGORY_PATTERN.match(line.strip())
        if not match:
            if capture:
                # Stop once the table ends.
                break
            continue
        count = int(match.group("count"))
        percent = match.group("percent")
        label = clean_label(match.group("label"))
        if percent == "100,00":
            # Skip the total row
            continue
        if not label:
            continue
        yield label, count


def extract_counts_for_year(pdf_path: Path) -> Dict[str, int]:
    with pdfplumber.open(pdf_path) as pdf:
        for page in reversed(pdf.pages):
            text = page.extract_text() or ""
            if "6.8 Entwicklung der Gemeinde" not in text:
                continue
            lines = text.split("\n")
            rows = list(iter_gewerbesteuer_rows(lines))
            if rows:
                return dict(rows)
    raise ExtractionError(f"Tabelle in {pdf_path.name} nicht gefunden")


def collect_counts(years: List[int]) -> Dict[str, Dict[int, int]]:
    data: Dict[str, Dict[int, int]] = defaultdict(dict)
    for year in years:
        pdf_path = PDF_DIR / f"Schlussbilanz {year}.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        counts = extract_counts_for_year(pdf_path)
        for label, value in counts.items():
            data[label][year] = value
    return data


def write_csv(data: Dict[str, Dict[int, int]], years: List[int], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["Kategorie", *[str(year) for year in years]]
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for category in sorted(data):
            row = {"Kategorie": category}
            for year in years:
                row[str(year)] = data[category].get(year, 0)
            writer.writerow(row)


def main(years: Iterable[int] | None = None, output: Path = OUTPUT_CSV) -> None:
    if years is None:
        years = sorted(
            int(path.stem.split()[-1])
            for path in PDF_DIR.glob("Schlussbilanz *.pdf")
            if path.stem.split()[-1].isdigit()
        )
    else:
        years = sorted(years)
    data = collect_counts(list(years))
    write_csv(data, list(years), output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="*", type=int, help="Einschränkung auf bestimmte Jahre")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV, help="Pfad zur Ergebnis-CSV")
    args = parser.parse_args()
    main(args.years, args.output)
