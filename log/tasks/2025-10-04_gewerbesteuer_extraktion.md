# 2025-10-04 – Gewerbesteuerstatistik extrahiert

- Aufgabe: Extraktion der Tabellen aus Abschnitt 6.8 "Entwicklung der Gemeinde" der Schlussbilanzen 2019–2024.
- Vorgehen: Neues Skript `analysis/entwicklung_gemeinde/extract_gewerbesteuer_betriebe.py` erstellt, das mithilfe von pdfplumber die relevanten Seiten findet, die Statistiken parst und eine Jahresübersicht erzeugt.
- Ergebnis: Aggregierte Werte als CSV und Markdown in `analysis/entwicklung_gemeinde/gewerbesteuer_betriebe.csv` bzw. `.md` gespeichert.
