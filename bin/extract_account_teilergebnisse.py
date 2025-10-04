"""Extract totals and teilergebnis details for a specific account from a Schlussbilanz PDF."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional

import pdfplumber

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
}


@dataclass
class AccountSummary:
    kontenbereich: str
    laufende_nummer: str
    bezeichnung: str
    ist_ergebnis: Decimal


@dataclass
class TeilergebnisEntry:
    produkt: str
    produkt_name: str
    ist_ergebnis: Decimal


class ExtractionError(Exception):
    """Raised when expected data cannot be extracted from the PDF."""


def clean_cell(cell: Optional[str]) -> str:
    if cell is None:
        return ""
    if not isinstance(cell, str):
        return str(cell)
    return " ".join(cell.split())


def normalise_row(row: List[Optional[str]], width: int) -> List[str]:
    cleaned = [clean_cell(cell) for cell in row]
    if len(cleaned) < width:
        cleaned.extend([""] * (width - len(cleaned)))
    return cleaned[:width]


def parse_german_number(value: str) -> Decimal:
    value = value.strip()
    if not value or value == "-":
        return Decimal("0")
    is_negative = False
    if value.endswith("-"):
        is_negative = True
        value = value[:-1]
    value = value.replace(".", "").replace(" ", "").replace(",", ".")
    if not value:
        return Decimal("0")
    number = Decimal(value)
    if is_negative:
        number *= Decimal("-1")
    return number


def normalise_account_name(name: str) -> str:
    return name.lstrip("+-= ").strip()


def extract_data_rows(table: List[List[Optional[str]]]) -> Iterable[List[str]]:
    if not table:
        return []
    width = len(table[0])
    start_index = 0
    for idx, row in enumerate(table):
        cleaned = [clean_cell(cell) for cell in row]
        first_non_empty = next((cell for cell in cleaned if cell), "")
        if first_non_empty.isdigit():
            start_index = idx
            break
    for row in table[start_index:]:
        normalised = normalise_row(row, width)
        if all(cell == "" for cell in normalised):
            continue
        yield normalised


def extract_ergebnis_summary(pdf: pdfplumber.PDF, account_name: str) -> AccountSummary:
    target_name = normalise_account_name(account_name)
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "Ergebnisrechnung" not in text or "Ertrags-" not in text:
            continue
        tables = page.extract_tables(TABLE_SETTINGS)
        for table in tables:
            if not table or not table[0]:
                continue
            first_cell = clean_cell(table[0][0])
            if "Ergebnisrechnung" not in first_cell:
                continue
            for row in extract_data_rows(table):
                if len(row) < 6:
                    continue
                if normalise_account_name(row[2]) != target_name:
                    continue
                ist_ergebnis = parse_german_number(row[5])
                return AccountSummary(
                    kontenbereich=clean_cell(row[0]),
                    laufende_nummer=clean_cell(row[1]),
                    bezeichnung=normalise_account_name(row[2]),
                    ist_ergebnis=ist_ergebnis,
                )
    raise ExtractionError(
        f"Konnte die Ertrags- oder Aufwandsart '{account_name}' nicht in der Ergebnisrechnung finden."
    )


PRODUKT_PATTERN = re.compile(r"Produkt\s*-\s*(?P<num>\d+)\s*-\s*(?P<name>.+)")


def iter_teilergebnis_tables(
    pdf: pdfplumber.PDF, account_name: str
) -> Iterable[tuple[str, str, List[List[str]]]]:
    normalised_target = normalise_account_name(account_name)
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "Teilergebnisrechnung" not in text:
            continue
        if account_name not in text and normalised_target not in text:
            continue
        tables = page.extract_tables(TABLE_SETTINGS)
        for table in tables:
            if not table or not table[0]:
                continue
            header = clean_cell(table[0][0])
            if "Teilergebnisrechnung" not in header:
                continue
            match = PRODUKT_PATTERN.search(header)
            if not match:
                continue
            produkt = match.group("num").strip()
            produkt_name = match.group("name").strip()
            rows = list(extract_data_rows(table))
            if rows:
                yield produkt, produkt_name, rows


def extract_teilergebnis_entries(
    pdf: pdfplumber.PDF, account_name: str
) -> List[TeilergebnisEntry]:
    target_name = normalise_account_name(account_name)
    entries: List[TeilergebnisEntry] = []
    for produkt, produkt_name, rows in iter_teilergebnis_tables(pdf, account_name):
        for row in rows:
            if len(row) < 6:
                continue
            if normalise_account_name(row[2]) != target_name:
                continue
            ist_wert = parse_german_number(row[5])
            if ist_wert == 0:
                continue
            entries.append(
                TeilergebnisEntry(
                    produkt=produkt,
                    produkt_name=produkt_name,
                    ist_ergebnis=ist_wert,
                )
            )
    if not entries:
        raise ExtractionError(
            f"Keine Teilergebnisse mit Betrag ungleich 0 für '{account_name}' gefunden."
        )
    return entries


def write_output_csv(
    output_path: Path,
    year: str,
    summary: AccountSummary,
    entries: List[TeilergebnisEntry],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "jahr",
        "kontenbereich",
        "laufende_nummer",
        "art",
        "scope",
        "produkt",
        "produkt_name",
        "ist_ergebnis_eur",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "jahr": year,
                "kontenbereich": summary.kontenbereich,
                "laufende_nummer": summary.laufende_nummer,
                "art": summary.bezeichnung,
                "scope": "Gesamtsumme",
                "produkt": "",
                "produkt_name": "",
                "ist_ergebnis_eur": f"{summary.ist_ergebnis:.2f}",
            }
        )
        for entry in entries:
            writer.writerow(
                {
                    "jahr": year,
                    "kontenbereich": summary.kontenbereich,
                    "laufende_nummer": summary.laufende_nummer,
                    "art": summary.bezeichnung,
                    "scope": "Teilergebnis",
                    "produkt": entry.produkt,
                    "produkt_name": entry.produkt_name,
                    "ist_ergebnis_eur": f"{entry.ist_ergebnis:.2f}",
                }
            )


def check_consistency(summary: AccountSummary, entries: List[TeilergebnisEntry]) -> None:
    total = sum((entry.ist_ergebnis for entry in entries), Decimal("0"))
    difference = summary.ist_ergebnis - total
    if difference.copy_abs() > Decimal("0.01"):
        raise ExtractionError(
            "Summe der Teilergebnisse ({} EUR) stimmt nicht mit der Gesamtsumme ({} EUR) überein.".format(
                f"{total:.2f}", f"{summary.ist_ergebnis:.2f}"
            )
        )


def build_default_pdf_path(year: str) -> Path:
    return Path("input/balance") / f"Schlussbilanz {year}.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrahiert die Gesamtsumme und Teilergebnisse einer Ertrags- oder Aufwandsart aus einer Schlussbilanz."
        )
    )
    parser.add_argument("year", help="Haushaltsjahr (z.B. 2024)")
    parser.add_argument("account", help="Bezeichnung der Ertrags- oder Aufwandsart")
    parser.add_argument(
        "--pdf",
        dest="pdf_path",
        type=Path,
        help="Pfad zur Schlussbilanz-PDF. Standard: input/balance/Schlussbilanz {Jahr}.pdf",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        type=Path,
        help="Pfad zur Ausgabedatei (CSV)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    year = args.year
    account = args.account
    pdf_path = args.pdf_path or build_default_pdf_path(year)
    output_path = args.output_path or Path("analysis/ergebnisrechnung") / (
        f"teilergebnis_{year}_{account.lower().replace(' ', '_').replace('.', '')}.csv"
    )

    if not pdf_path.exists():
        raise SystemExit(f"PDF nicht gefunden: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        summary = extract_ergebnis_summary(pdf, account)
        entries = extract_teilergebnis_entries(pdf, account)

    check_consistency(summary, entries)
    write_output_csv(output_path, year, summary, entries)
    print(
        f"Extraktion abgeschlossen. Gesamtsumme: {summary.ist_ergebnis:.2f} EUR, "
        f"Teilergebnisse: {len(entries)} -> {output_path}"
    )


if __name__ == "__main__":
    main()
