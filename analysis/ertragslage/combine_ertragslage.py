from __future__ import annotations

import csv
import math
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

DATA_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = DATA_DIR / "ertragslage_2018-2024.csv"
CSV_PATTERN = "ertragslage_20*.csv"


@dataclass(frozen=True)
class ErtragslageRow:
    category: str
    previous_value: Optional[float]
    current_value: Optional[float]
    difference: Optional[float]


@dataclass(frozen=True)
class ErtragslageTable:
    path: Path
    previous_year: str
    current_year: str
    rows: list[ErtragslageRow]


def parse_decimal(value: str | None) -> Optional[float]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Cannot parse decimal value: {value!r}") from exc


def format_decimal(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def load_ertragslage_tables(files: Iterable[Path]) -> list[ErtragslageTable]:
    tables: list[ErtragslageTable] = []
    for path in sorted(files):
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or len(reader.fieldnames) != 4:
                raise ValueError(f"Unexpected header structure in {path}")
            category_header, previous_year, current_year, diff_header = reader.fieldnames
            if category_header != "Kategorie":
                raise ValueError(f"Unexpected first header '{category_header}' in {path}")
            rows: list[ErtragslageRow] = []
            for record in reader:
                rows.append(
                    ErtragslageRow(
                        category=record["Kategorie"].strip(),
                        previous_value=parse_decimal(record[previous_year]),
                        current_value=parse_decimal(record[current_year]),
                        difference=parse_decimal(record[diff_header]),
                    )
                )
            tables.append(
                ErtragslageTable(
                    path=path,
                    previous_year=previous_year,
                    current_year=current_year,
                    rows=rows,
                )
            )
    if not tables:
        raise FileNotFoundError("No ertragslage CSV files were found")
    return tables


def ensure_overlap_consistency(tables: list[ErtragslageTable]) -> None:
    for previous, current in zip(tables, tables[1:]):
        if previous.current_year != current.previous_year:
            raise ValueError(
                "Year mismatch between tables: "
                f"{previous.path.name} -> {current.path.name}"
            )
        previous_values = {row.category: row.current_value for row in previous.rows}
        current_values = {row.category: row.previous_value for row in current.rows}
        mismatches: list[tuple[str, Optional[float], Optional[float]]] = []
        for category in sorted(set(previous_values) & set(current_values)):
            a = previous_values.get(category)
            b = current_values.get(category)
            if a is None and b is None:
                continue
            if a is None or b is None or not math.isclose(a, b, abs_tol=0.01):
                mismatches.append((category, a, b))
        if mismatches:
            details = "; ".join(
                f"{category}: {a!r} vs {b!r}" for category, a, b in mismatches
            )
            raise ValueError(
                f"Overlapping year '{previous.current_year}' contains mismatched values: {details}"
            )


def ensure_difference_consistency(table: ErtragslageTable) -> None:
    for row in table.rows:
        prev_value = row.previous_value
        curr_value = row.current_value
        diff_value = row.difference
        if prev_value is None or curr_value is None or diff_value is None:
            continue
        expected = curr_value - prev_value
        if not math.isclose(expected, diff_value, abs_tol=0.01):
            raise ValueError(
                f"Difference mismatch for '{row.category}' in {table.current_year}: "
                f"expected {expected:.2f}, found {diff_value:.2f}"
            )


def build_combined_table(tables: list[ErtragslageTable]) -> list[list[str]]:
    category_order: OrderedDict[str, None] = OrderedDict()
    values: defaultdict[str, dict[str, Optional[float]]] = defaultdict(dict)
    all_years: set[str] = set()

    for table in tables:
        ensure_difference_consistency(table)
        all_years.update([table.previous_year, table.current_year])
        for row in table.rows:
            category = row.category
            if category not in category_order:
                category_order[category] = None
            values[category][table.previous_year] = row.previous_value
            values[category][table.current_year] = row.current_value

    sorted_years = sorted(all_years)
    header = ["Kategorie", *sorted_years]
    data_rows: list[list[str]] = [header]
    for category in category_order:
        row = [category]
        for year in sorted_years:
            row.append(format_decimal(values[category].get(year)))
        data_rows.append(row)
    return data_rows


def main() -> None:
    csv_files = list(DATA_DIR.glob(CSV_PATTERN))
    tables = load_ertragslage_tables(csv_files)
    ensure_overlap_consistency(tables)
    combined_rows = build_combined_table(tables)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(combined_rows)
    print(f"Wrote {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
