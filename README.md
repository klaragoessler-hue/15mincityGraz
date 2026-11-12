# 15mincityGraz

Reproduktion von Willberg, Fink & Toivonen (2023) für Graz.

> Willberg, E., Fink, C., & Toivonen, T. (2023). The 15-minute city for all? – Measuring individual and temporal variations in walking accessibility. *Journal of Transport Geography*, 106, 103521. https://doi.org/10.1016/j.jtrangeo.2022.103521

Originalcode und Messdaten: https://github.com/DigitalGeographyLab/15_minute_city_for_all_article (Apache 2.0)

## Ziel

## Daten

- `data/raw/bezirke_bevoelkerung.csv`: Einwohner pro Grazer Bezirk, Stand 01.01.2026. Quelle: Stadt Graz, Präsidialamt, Referat für Statistik, [Bevölkerung nach Bezirken](https://www.graz.at/cms/dokumente/10022937_7771507/8024c4a9/Bev%C3%B6lkerung%20nach%20Bezirken_01.021.2026.pdf). Bezirksnamen an OSM angepasst (`St.Leonhard` → `Sankt Leonhard`, `St.Peter` → `Sankt Peter`). Spalten:
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

## Team
