# Aufgabe
Erstellung einer Gesamtübersicht der Ertragsbestandteile der Gemeinde Lensahn auf Basis der Gesamtzeitreihe sowie der Teilergebnis-Zeitreihen und der erweiterten Steueraufteilungen.

# Umsetzung
- Aufbereitung eines neuen Skripts `analysis/ertragslage/build_ertragsbestandteile_overview.py`, das die Gesamtwerte der Ergebnisrechnung, die detaillierten Teilergebnis-Zeitreihen sowie die Steuer- und Gewerbesteuerstatistiken zusammenführt.
- Automatisierte Generierung der Tabelle `analysis/ertragslage/ertragsbestandteile_gesamtuebersicht.csv` mit Jahreswerten 2018-2024, differenziert nach Aggregaten, Steuerarten, Teilergebnissen und Gewerbesteuer-Betriebsgrößenklassen.

# Quellen
- `analysis/ergebnisrechnung/gesamt_ergebnisse_zeitreihe.csv`
- `analysis/ergebnisrechnung/zeitreihe_steuern_und_ähnliche_abgaben.csv`
- `analysis/ergebnisrechnung/zeitreihe_zuwendungen_und_allgemeine_umlagen.csv`
- `analysis/ergebnisrechnung/zeitreihe_sonstige_erträge.csv`
- `analysis/ergebnisrechnung/zeitreihe_privatrechtliche_leistungsentgelte.csv`
- `analysis/ergebnisrechnung/zeitreihe_öffentlich-rechtliche_leistungsentgelte.csv`
- `analysis/ergebnisrechnung/zeitreihe_kostenerstattungen_u_kostenumlagen.csv`
- `analysis/ertragslage/ertragslage_2018-2024.csv`
- `analysis/lagebericht/gewerbesteuer_betriebe_counts.csv`
