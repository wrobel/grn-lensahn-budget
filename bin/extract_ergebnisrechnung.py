import re
from pathlib import Path
from typing import Iterable, List

import pandas as pd
import pdfplumber

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
}

COLUMN_NAMES = [
    "Spalte 13 (Kontenbereich)",
    "Spalte 24 (Lfd. Nr.)",
    "Spalte 3 (Ertrags- und Aufwandsarten)",
    "Spalte 4 (Ergebnis des Vorjahres in EUR)",
    "Spalte 5 (Fortgeschriebener Ansatz des Haushaltsjahres in EUR)",
    "Spalte 6 (Ist-Ergebnis des Haushaltsjahres in EUR)",
    "Spalte 7 (Vergleich Ansatz/Ist in EUR)",
    "Spalte 8 (Übertragene Ermächtigungen in EUR)",
]


def clean_cell(cell: str | None) -> str:
    if cell is None:
        return ""
    if not isinstance(cell, str):
        return str(cell)
    return " ".join(cell.split())


def normalise_row(row: List[str | None], width: int) -> List[str]:
    cleaned = [clean_cell(cell) for cell in row]
    if len(cleaned) < width:
        cleaned.extend([""] * (width - len(cleaned)))
    return cleaned[:width]


def extract_table_rows(table: List[List[str | None]]) -> Iterable[List[str]]:
    if not table:
        return []
    width = len(table[0])
    data_rows = []
    for row in table[3:]:
        normalised = normalise_row(row, width)
        if all(cell == "" for cell in normalised):
            continue
        data_rows.append(normalised)
    return data_rows


def extract_ergebnis_rows(pdf_path: Path) -> List[List[str]]:
    rows: List[List[str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        in_section = False
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "Ergebnisrechnung" not in text or "Ertrags-" not in text:
                if in_section:
                    break
                continue
            in_section = True
            tables = page.extract_tables(TABLE_SETTINGS)
            for table in tables:
                first_cell = table[0][0] if table and table[0] else ""
                if "Ergebnisrechnung" not in (first_cell or ""):
                    continue
                rows.extend(extract_table_rows(table))
    return rows


def main() -> None:
    input_dir = Path("input/balance")
    output_dir = Path("analysis/ergebnisrechnung")
    output_dir.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(input_dir.glob("Schlussbilanz *.pdf")):
        match = re.search(r"(\d{4})", pdf_path.name)
        if not match:
            continue
        year = match.group(1)
        rows = extract_ergebnis_rows(pdf_path)
        if not rows:
            print(f"Keine Ergebnisrechnung in {pdf_path.name} gefunden.")
            continue
        df = pd.DataFrame(rows, columns=COLUMN_NAMES)
        output_path = output_dir / f"ergebnisrechnung_{year}.csv"
        df.to_csv(output_path, index=False)
        print(f"{output_path} erstellt (Zeilen: {len(df)})")


if __name__ == "__main__":
    main()
