# 15mincityGraz

Reproduktion von Willberg, Fink & Toivonen (2023) für Graz.

> Willberg, E., Fink, C., & Toivonen, T. (2023). The 15-minute city for all? – Measuring individual and temporal variations in walking accessibility. *Journal of Transport Geography*, 106, 103521. https://doi.org/10.1016/j.jtrangeo.2022.103521

Originalcode und Messdaten: https://github.com/DigitalGeographyLab/15_minute_city_for_all_article (Apache 2.0)

## Ziel

## Daten

- `data/raw/bezirke_bevoelkerung.csv`: Einwohner pro Grazer Bezirk, Stand 01.01.2026. **Erzeugt von `notebooks/00_bevoelkerung_bezirke.py`** (lädt die PDFs der Stadt Graz, liest sie aus, prüft die Summen). Quelle: Stadt Graz, Präsidialamt, Referat für Statistik, [Bevölkerung nach Bezirken](https://www.graz.at/cms/dokumente/10022937_7771507/8024c4a9/Bev%C3%B6lkerung%20nach%20Bezirken_01.021.2026.pdf). Bezirksnamen an OSM angepasst (`St.Leonhard` → `Sankt Leonhard`, `St.Peter` → `Sankt Peter`). Spalten:
  - `einwohner`: anwesende Bevölkerung (Haupt- + Nebenwohnsitze + Obdachlose)
  - `einwohner_hws`: nur Hauptwohnsitze
  - `alter_60_69`, `alter_70plus`: Hauptwohnsitze nach Alter, aus den [Bezirksauswertungen](https://www1.graz.at/statistik/Bev%C3%B6lkerung/Bezirksauswertungen/Bezirk_final_05.pdf) (`Bezirk_final_01.pdf` bis `_17.pdf`), Stand 01.01.2026
  - `anteil_65plus`: **geschätzt**, da die Stadt nur 10-Jahres-Gruppen ausweist: (70+ + ½ × 60–69) / Hauptwohnsitze. Annahme: die 60–69-Jährigen sind gleichmäßig über die Jahrgänge verteilt.

## Ordnerstruktur

```
data/raw/         Rohdaten (nicht im Repo)
data/processed/   aufbereitete Daten (nicht im Repo)
notebooks/        marimo-Notebooks
figures/          Abbildungen
report/           Bericht
references/       Paper, Notizen zum Original
```

## Ausführen

Umgebung einrichten (einmalig): `uv sync`

Die Notebooks bauen aufeinander auf und werden **in dieser Reihenfolge** ausgeführt
(in VS Code: „marimo: open as marimo notebook“ oder im Terminal `uv run marimo edit notebooks/<datei>.py`):

| Notebook | macht | schreibt |
|---|---|---|
| `00_bevoelkerung_bezirke.py` | Einwohner + Alter pro Bezirk aus den PDFs der Stadt Graz | `data/raw/bezirke_bevoelkerung.csv` |
| `01_gehgeschwindigkeiten.py` | Gehgeschwindigkeiten aus den Messdaten des Originals | `data/processed/speeds.csv` |
| `02_supermaerkte.py` | Supermärkte aus OSM, Bereinigung, Öffnungszeiten | `data/processed/supermaerkte.gpkg` |
| `03_netz_bevoelkerung.py` | Fußwegnetz, Bezirke, Wohngebäude mit Einwohnern | `walk_network_graz.graphml`, `bezirke.gpkg`, `wohngebaeude.gpkg` |
| `04_erreichbarkeit.py` | Routing, 8 Modelle, Ergebnis, Sensitivität (braucht 01–03) | `ergebnis_gebaeude.gpkg`, `ergebnis_modelle.csv`, `sensitivitaet.csv` |
| `05_abbildungen.py` | Abbildungen (noch offen) | `figures/` |

00, 01, 02 und 03 sind unabhängig voneinander, 03 braucht nur die CSV aus 00 (liegt im Repo).
Gemeinsame Einstellungen (Koordinatensystem, Zeitpunkte, Dateinamen) stehen in `notebooks/einstellungen.py` – Änderungen dort gelten für alle Notebooks und sollten abgesprochen werden.

Der erste Lauf von 02 und 03 lädt Daten aus OpenStreetMap und kann einige Minuten dauern; die Antworten werden in `data/raw/osmnx_cache/` gespeichert.

## Team
