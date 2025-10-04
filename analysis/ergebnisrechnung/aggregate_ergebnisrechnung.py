#!/usr/bin/env python3
"""Aggregate Ergebnisrechnung CSV files into multi-year overview tables."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

BASE_DIR = Path(__file__).parent
INPUT_PATTERN = "ergebnisrechnung_*.csv"

COLUMN_NAMES = {
    "konto": "Spalte 13 (Kontenbereich)",
    "lfd": "Spalte 24 (Lfd. Nr.)",
    "art": "Spalte 3 (Ertrags- und Aufwandsarten)",
    "vorjahr": "Spalte 4 (Ergebnis des Vorjahres in EUR)",
    "plan": "Spalte 5 (Fortgeschriebener Ansatz des Haushaltsjahres in EUR)",
    "ist": "Spalte 6 (Ist-Ergebnis des Haushaltsjahres in EUR)",
    "abweichung": "Spalte 7 (Vergleich Ansatz/Ist in EUR)",
    "erm": "Spalte 8 (Übertragene Ermächtigungen in EUR)",
}

NumberDict = Dict[int, float]
DataDict = Dict[Tuple[str, str, str], NumberDict]


def parse_number(raw: str) -> float | None:
    """Convert a German formatted number string to float.

    Returns ``None`` for empty strings. A trailing ``-`` is treated as a negative sign.
    """

    if raw is None:
        return None
    value = raw.strip()
    if not value or value == "-":
        return 0.0
    negative = value.endswith("-")
    if negative:
        value = value[:-1]
    value = value.replace(".", "").replace(",", ".")
    try:
        number = float(value)
    except ValueError:
        return None
    return -number if negative else number


def format_number(value: float | None) -> str:
    """Format a float using German decimal formatting."""

    if value is None:
        return ""
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def collect_data(paths: Sequence[Path]):
    result_data: DataDict = defaultdict(dict)
    plan_data: DataDict = defaultdict(dict)
    abweichung_data: DataDict = defaultdict(dict)
    erm_data: DataDict = defaultdict(dict)
    order: List[Tuple[str, str, str]] = []

    for path in sorted(paths):
        year = int(path.stem.split("_")[-1])
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for line in reader:
                key = (
                    line[COLUMN_NAMES["konto"]].strip(),
                    line[COLUMN_NAMES["lfd"]].strip(),
                    line[COLUMN_NAMES["art"]].strip(),
                )
                if key not in order:
                    order.append(key)

                ist_value = parse_number(line[COLUMN_NAMES["ist"]])
                if ist_value is not None:
                    result_data[key][year] = ist_value

                plan_value = parse_number(line[COLUMN_NAMES["plan"]])
                if plan_value is not None:
                    plan_data[key][year] = plan_value

                abweichung_value = parse_number(line[COLUMN_NAMES["abweichung"]])
                if abweichung_value is not None:
                    abweichung_data[key][year] = abweichung_value

                erm_value = parse_number(line[COLUMN_NAMES["erm"]])
                if erm_value is not None:
                    erm_data[key][year] = erm_value

                prev_value = parse_number(line[COLUMN_NAMES["vorjahr"]])
                prev_year = year - 1
                if prev_value is not None and prev_year not in result_data[key]:
                    result_data[key][prev_year] = prev_value

    return order, result_data, plan_data, abweichung_data, erm_data


def write_table(
    path: Path,
    keys: Iterable[Tuple[str, str, str]],
    years: Sequence[int],
    data: DataDict,
    prefix: str,
) -> None:
    header = ["Kontenbereich", "Lfd. Nr.", "Ertrags- und Aufwandsarten"] + [
        f"{prefix} {year}" for year in years
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for key in keys:
            row = list(key)
            values = data.get(key, {})
            for year in years:
                value = values.get(year)
                row.append(format_number(value))
            writer.writerow(row)


def main() -> None:
    input_files = sorted(BASE_DIR.glob(INPUT_PATTERN))
    if not input_files:
        raise SystemExit("No input files found")

    keys, results, plans, deviations, authorisations = collect_data(input_files)

    result_years = sorted({year for values in results.values() for year in values})
    plan_years = sorted({year for path in input_files for year in [int(path.stem.split("_")[-1])]})

    write_table(
        BASE_DIR / "gesamt_ergebnisse_zeitreihe.csv",
        keys,
        result_years,
        results,
        "Ergebnis",
    )
    write_table(
        BASE_DIR / "gesamt_haushaltsplanung_zeitreihe.csv",
        keys,
        plan_years,
        plans,
        "Plan",
    )
    write_table(
        BASE_DIR / "gesamt_abweichungen_zeitreihe.csv",
        keys,
        plan_years,
        deviations,
        "Abweichung",
    )
    write_table(
        BASE_DIR / "gesamt_uebertragene_ermaechtigungen_zeitreihe.csv",
        keys,
        plan_years,
        authorisations,
        "Übertragene Ermächtigung",
    )


if __name__ == "__main__":
    main()
