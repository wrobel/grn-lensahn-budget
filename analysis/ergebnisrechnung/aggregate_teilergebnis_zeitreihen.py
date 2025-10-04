#!/usr/bin/env python3
"""Create multi-year overviews for selected revenue categories."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

BASE_DIR = Path(__file__).parent

# Target categories and known filename suffix aliases
CATEGORY_ALIASES = {
    "steuern_und_ähnliche_abgaben": {"steuern_und_ähnliche_abgaben"},
    "zuwendungen_und_allgemeine_umlagen": {"zuwendungen_und_allgemeine_umlagen"},
    "öffentlich-rechtliche_leistungsentgelte": {"öffentlich-rechtliche_leistungsentgelte"},
    "privatrechtliche_leistungsentgelte": {"privatrechtliche_leistungsentgelte"},
    "kostenerstattungen_u_kostenumlagen": {
        "kostenerstattungen_u_kostenumlagen",
        "kostenerstattungen",
    },
    "sonstige_erträge": {"sonstige_erträge"},
}

HEADER_COLUMNS = [
    "kontenbereich",
    "laufende_nummer",
    "art",
    "scope",
    "produkt",
    "produkt_name",
]

NumberMap = Dict[int, float]
RowKey = Tuple[str, str, str, str, str, str]
DataMap = Dict[RowKey, NumberMap]


def parse_value(raw: str) -> float | None:
    """Return a float for the raw value or ``None`` for empty strings."""

    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return float(raw)


def collect_category_data(paths: Sequence[Path]) -> Tuple[List[RowKey], DataMap]:
    data: DataMap = defaultdict(dict)
    order: List[RowKey] = []

    for path in sorted(paths):
        try:
            year = int(path.stem.split("_")[1])
        except (IndexError, ValueError) as error:
            raise ValueError(f"Unexpected filename format: {path.name}") from error

        with path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                key: RowKey = tuple(row[column] for column in HEADER_COLUMNS)  # type: ignore[arg-type]
                if key not in order:
                    order.append(key)

                value = parse_value(row.get("ist_ergebnis_eur", ""))
                if value is not None:
                    data[key][year] = value

    return order, data


def write_overview(path: Path, order: Iterable[RowKey], data: DataMap, years: Sequence[int]) -> None:
    header = [
        "Kontenbereich",
        "Lfd. Nr.",
        "Art",
        "Scope",
        "Produkt",
        "Produktname",
        *[str(year) for year in years],
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for key in order:
            row = list(key)
            values = data.get(key, {})
            for year in years:
                value = values.get(year)
                row.append("" if value is None else f"{value:.2f}")
            writer.writerow(row)


def main() -> None:
    base_pattern = "teilergebnis_*.csv"
    available_files = list(BASE_DIR.glob(base_pattern))

    if not available_files:
        raise SystemExit("Keine Teilergebnis-Dateien gefunden.")

    files_by_category: Dict[str, List[Path]] = {key: [] for key in CATEGORY_ALIASES}

    for path in available_files:
        parts = path.stem.split("_", 2)
        if len(parts) != 3:
            continue
        _, year_part, category_part = parts
        if not year_part.isdigit():
            continue
        for target, aliases in CATEGORY_ALIASES.items():
            if category_part in aliases:
                files_by_category[target].append(path)
                break

    years = sorted(
        {
            int(path.stem.split("_")[1])
            for path_list in files_by_category.values()
            for path in path_list
        }
    )

    for category, paths in files_by_category.items():
        if not paths:
            continue
        order, data = collect_category_data(paths)
        output_path = BASE_DIR / f"zeitreihe_{category}.csv"
        write_overview(output_path, order, data, years)


if __name__ == "__main__":
    main()
