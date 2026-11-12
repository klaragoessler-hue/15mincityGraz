# Originalcode des Papers (kommentiert)

Code aus dem Repository der Autor:innen:
https://github.com/DigitalGeographyLab/15_minute_city_for_all_article

> Willberg, E., Fink, C., & Toivonen, T. (2023). The 15-minute city for all? – Measuring individual and temporal variations in walking accessibility. *Journal of Transport Geography*, 106, 103521.

Lizenz des Originals: **Apache 2.0** (laut README des Original-Repos).

## Dateien

| Datei | Inhalt |
|---|---|
| `original/WalkingAccessibilityRoutingTEMPORAL.py` | Routing-Skript, **unverändert** (im Original-Repo im Ordner `visualisation/`) |
| `original/WalkingAccessibilityRoutingVISUALIZATION.py` | Abbildungs-Skript, **unverändert** (im Original-Repo im Ordner `processing/`) |
| `routing_kommentiert.py` | Routing-Skript mit Kommentaren |
| `visualisierung_kommentiert.py` | Abbildungs-Skript mit Kommentaren |

**Änderungen gegenüber dem Original:** In den `*_kommentiert.py`-Dateien wurden nur Kommentarzeilen ergänzt, der Code selbst ist unverändert.

Kommentar-Legende:
- `ERKLÄRUNG` – was der Abschnitt macht
- `PROBLEM` – Fehler oder Unklarheit im Original (Material für die Kritik)
- `GRAZ` – was wir für Graz anders machen

Die Skripte **laufen nicht** (fehlende Eingabedaten, leerer Pfad, Syntaxfehler, veraltete OSMnx-Funktionen). Sie dienen nur zum Nachlesen der Methode. Unser eigener Code liegt in `notebooks/`.

Die Messdaten der Gehgeschwindigkeiten (`data/Walking_speed_measurements_EW_CH_*.csv`) sind nicht hier abgelegt. Sie werden für die Analyse nach `data/raw/` geladen.
