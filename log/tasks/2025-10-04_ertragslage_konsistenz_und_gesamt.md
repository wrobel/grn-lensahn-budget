# 2025-10-04: Prüfung Ertragslage-Tabellen und Aggregation

## Aufgabe
- Konsistenz der Jahresüberlappungen zwischen den Tabellen `analysis/ertragslage/ertragslage_*.csv` prüfen.
- Bei stimmigen Daten eine Gesamttabelle über sieben Jahre erstellen.

## Vorgehen
- Skript `analysis/ertragslage/combine_ertragslage.py` erstellt. Es lädt alle Jahresdateien, validiert Differenzen und Überlappungen und generiert eine gemeinsame Tabelle.
- Skript ausgeführt, wodurch `analysis/ertragslage/ertragslage_2018-2024.csv` erzeugt wurde.

## Ergebnis
- Alle Überlappungen waren konsistent; keine Abweichungen festgestellt.
- Aggregierte Tabelle `analysis/ertragslage/ertragslage_2018-2024.csv` enthält die Werte 2018–2024 je Kategorie.
