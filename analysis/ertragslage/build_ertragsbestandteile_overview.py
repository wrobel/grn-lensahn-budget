#!/usr/bin/env python3
"""Create a consolidated overview of Lensahn's revenue components."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Sequence

BASE_DIR = Path(__file__).resolve().parent
ERFOLG_DIR = BASE_DIR.parent / "ergebnisrechnung"
LAGE_DIR = BASE_DIR.parent / "lagebericht"

YEARS: Sequence[int] = tuple(range(2018, 2025))
YEAR_COLUMNS: Sequence[str] = tuple(str(year) for year in YEARS)

RELEVANT_LFD_NUMBERS = {
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "19",
}

CATEGORY_ORDER = [
    "Erträge",
    "Finanzerträge",
    "Steuern und ähnliche Abgaben",
    "Zuwendungen und allgemeine Umlagen",
    "Sonstige Transfererträge",
    "öffentlich-rechtliche Leistungsentgelte",
    "privatrechtliche Leistungsentgelte",
    "Kostenerstattungen u. Kostenumlagen",
    "sonstige Erträge",
    "aktivierte Eigenleistungen",
    "Bestandveränderungen",
]

DETAIL_ORDER = {
    "Aggregat": 0,
    "Steuerart": 1,
    "Zuweisungstyp": 1,
    "Teilergebnis": 2,
}
DETAIL_FALLBACK = max(DETAIL_ORDER.values()) + 1

RESET_LABELS = {
    "sonstige Erträge",
    "lfd. Erträge",
    "Finanzerträge",
    "Gesamterträge",
    "Personalaufwendungen",
}


def parse_german_number(raw: str | None) -> float | None:
    """Convert a German formatted string to ``float``."""

    if raw is None:
        return None
    value = raw.strip()
    if not value or value == "-":
        return None
    negative = value.endswith("-")
    if negative:
        value = value[:-1]
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    try:
        number = float(value)
    except ValueError:
        return None
    return -number if negative else number


def format_currency(value: float | None) -> str:
    if value is None:
        return ""
    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def format_count(value: float | None) -> str:
    if value is None:
        return ""
    return f"{int(round(value))}"


def normalise_category(label: str) -> str:
    stripped = label.strip()
    stripped = re.sub(r"^[+=\-\s/.]+", "", stripped)
    return stripped


@dataclass
class OverviewRow:
    category: str
    subcategory: str
    detail_type: str
    product: str
    product_name: str
    metric: str
    values: MutableMapping[int, float | None] = field(default_factory=dict)
    value_format: str = "currency"

    def as_csv_row(self) -> Dict[str, str]:
        result: Dict[str, str] = {
            "Kategorie": self.category,
            "Unterkategorie": self.subcategory,
            "Detailtyp": self.detail_type,
            "Produkt": self.product,
            "Produktname": self.product_name,
            "Kennzahl": self.metric,
        }
        formatter = format_currency if self.value_format == "currency" else format_count
        for year in YEARS:
            result[str(year)] = formatter(self.values.get(year))
        return result


def add_totals(rows: List[OverviewRow]) -> None:
    path = ERFOLG_DIR / "gesamt_ergebnisse_zeitreihe.csv"
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line in reader:
            if line["Lfd. Nr."].strip() not in RELEVANT_LFD_NUMBERS:
                continue
            category = normalise_category(line["Ertrags- und Aufwandsarten"])
            values: Dict[int, float | None] = {}
            for year in YEARS:
                values[year] = parse_german_number(line.get(f"Ergebnis {year}"))
            rows.append(
                OverviewRow(
                    category=category,
                    subcategory="Gesamtsumme",
                    detail_type="Aggregat",
                    product="",
                    product_name="",
                    metric="Ertrag",
                    values=values,
                )
            )


def add_teilergebnis_details(rows: List[OverviewRow]) -> None:
    mapping = {
        "zeitreihe_steuern_und_ähnliche_abgaben.csv": "Steuern und ähnliche Abgaben",
        "zeitreihe_zuwendungen_und_allgemeine_umlagen.csv": "Zuwendungen und allgemeine Umlagen",
        "zeitreihe_sonstige_erträge.csv": "sonstige Erträge",
        "zeitreihe_privatrechtliche_leistungsentgelte.csv": "privatrechtliche Leistungsentgelte",
        "zeitreihe_öffentlich-rechtliche_leistungsentgelte.csv": "öffentlich-rechtliche Leistungsentgelte",
        "zeitreihe_kostenerstattungen_u_kostenumlagen.csv": "Kostenerstattungen u. Kostenumlagen",
    }
    for filename, category_name in mapping.items():
        path = ERFOLG_DIR / filename
        with path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for line in reader:
                scope = line.get("Scope", "").strip()
                if scope == "Gesamtsumme":
                    continue
                product = line.get("Produkt", "").strip()
                product_name = line.get("Produktname", "").strip()
                subcategory = product_name
                detail_type = "Teilergebnis"
                values: Dict[int, float | None] = {}
                for year in YEARS:
                    values[year] = parse_german_number(line.get(str(year)))
                rows.append(
                    OverviewRow(
                        category=category_name,
                        subcategory=subcategory,
                        detail_type=detail_type,
                        product=product,
                        product_name=product_name,
                        metric="Ertrag",
                        values=values,
                    )
                )


def add_tax_breakdown(rows: List[OverviewRow]) -> None:
    detail_scope = {
        "Steuern und ähnliche Abgaben": "Steuerart",
        "Zuwendungen und allgemeine Umlagen": "Zuweisungstyp",
    }
    path = BASE_DIR / "ertragslage_2018-2024.csv"
    current_category: str | None = None
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line in reader:
            label = line["Kategorie"].strip()
            if not label:
                continue
            if label in detail_scope:
                current_category = label
                continue
            if label in RESET_LABELS:
                current_category = None
                continue
            if current_category not in detail_scope:
                current_category = None
                continue
            subcategory = label
            values: Dict[int, float | None] = {}
            for year in YEARS:
                values[year] = parse_german_number(line.get(str(year)))
            rows.append(
                OverviewRow(
                    category=current_category,
                    subcategory=subcategory,
                    detail_type=detail_scope[current_category],
                    product="",
                    product_name="",
                    metric="Ertrag",
                    values=values,
                )
            )


def add_gewerbesteuer_counts(rows: List[OverviewRow]) -> None:
    path = LAGE_DIR / "gewerbesteuer_betriebe_counts.csv"
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line in reader:
            bracket = line["Kategorie"].strip()
            values: Dict[int, float | None] = {}
            for year in YEARS:
                values[year] = parse_german_number(line.get(str(year)))
            rows.append(
                OverviewRow(
                    category="Steuern und ähnliche Abgaben",
                    subcategory="Gewerbesteuer",
                    detail_type=f"Betriebsgrößenklasse: {bracket}",
                    product="",
                    product_name=bracket,
                    metric="Anzahl Betriebe",
                    values=values,
                    value_format="count",
                )
            )


def write_rows(rows: Iterable[OverviewRow]) -> None:
    output_path = BASE_DIR / "ertragsbestandteile_gesamtuebersicht.csv"
    fieldnames = [
        "Kategorie",
        "Unterkategorie",
        "Detailtyp",
        "Produkt",
        "Produktname",
        "Kennzahl",
        *YEAR_COLUMNS,
    ]
    ordered_categories = {name: index for index, name in enumerate(CATEGORY_ORDER)}

    def sort_key(item: OverviewRow) -> tuple[int, int, str, int, str, str]:
        category_index = ordered_categories.get(item.category, len(ordered_categories))
        detail_index = DETAIL_ORDER.get(item.detail_type, DETAIL_FALLBACK)
        subcategory_index = 0 if item.subcategory == "Gesamtsumme" else 1
        return (
            category_index,
            subcategory_index,
            item.subcategory or "",
            detail_index,
            item.detail_type,
            item.product or item.product_name,
        )

    sorted_rows = sorted(rows, key=sort_key)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted_rows:
            writer.writerow(row.as_csv_row())


def main() -> None:
    rows: List[OverviewRow] = []
    add_totals(rows)
    add_teilergebnis_details(rows)
    add_tax_breakdown(rows)
    add_gewerbesteuer_counts(rows)
    write_rows(rows)


if __name__ == "__main__":
    main()
