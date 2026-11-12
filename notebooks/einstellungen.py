"""
GEMEINSAME EINSTELLUNGEN für alle Notebooks (00 bis 05).

WARUM eine eigene Datei?
Vier Leute arbeiten an verschiedenen Notebooks. Damit am Ende alles zusammenpasst,
müssen alle mit denselben Werten rechnen: gleiches Koordinatensystem, gleiche
Zeitpunkte, gleiche Dateinamen. Diese Werte stehen deshalb NUR HIER.
Jedes Notebook holt sie sich mit z. B.:

    from einstellungen import CRS, ZEITPUNKTE, DATEIEN

Wer hier etwas ändert, ändert es für alle -> vorher in der Gruppe absprechen!

ÜBERSICHT: Welches Notebook macht was und übergibt welche Datei?

    00_bevoelkerung_bezirke.py  -> data/raw/bezirke_bevoelkerung.csv
    01_gehgeschwindigkeiten.py  -> data/processed/speeds.csv
    02_supermaerkte.py          -> data/processed/supermaerkte.gpkg
    03_netz_bevoelkerung.py     -> data/processed/walk_network_graz.graphml
                                   data/processed/bezirke.gpkg
                                   data/processed/wohngebaeude.gpkg
    04_erreichbarkeit.py        -> data/processed/ergebnis_gebaeude.gpkg
       (braucht 01, 02, 03)        data/processed/ergebnis_modelle.csv
                                   data/processed/sensitivitaet.csv
"""
import time
from datetime import datetime
from pathlib import Path

import osmnx as ox

# ----------------------------------------------------------------------------
# ORDNER
# ----------------------------------------------------------------------------
# Diese Datei liegt in <repo>/notebooks/ -> der Repo-Ordner ist eine Ebene höher.
# __file__ = Pfad dieser Datei; .resolve() = vollständiger Pfad;
# .parent = übergeordneter Ordner (1x: notebooks/, 2x: Repo-Ordner)
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"              # Rohdaten (nicht im Git, außer kleiner CSV)
PROCESSED = ROOT / "data" / "processed"  # Zwischen- und Endergebnisse (nicht im Git)
# Ordner anlegen, falls sie fehlen (parents=True: auch Zwischenordner,
# exist_ok=True: kein Fehler, wenn es sie schon gibt)
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

# Alle Dateien, die zwischen den Notebooks weitergegeben werden.
# Ein Notebook SCHREIBT eine Datei, ein späteres LIEST sie.
DATEIEN = {
    "bezirke_csv": RAW / "bezirke_bevoelkerung.csv",            # von 00
    "speeds": PROCESSED / "speeds.csv",                         # von 01
    "supermaerkte": PROCESSED / "supermaerkte.gpkg",            # von 02
    "netz": PROCESSED / "walk_network_graz.graphml",            # von 03
    "bezirke": PROCESSED / "bezirke.gpkg",                      # von 03
    "wohngebaeude": PROCESSED / "wohngebaeude.gpkg",            # von 03
    "ergebnis_gebaeude": PROCESSED / "ergebnis_gebaeude.gpkg",  # von 04
    "ergebnis_modelle": PROCESSED / "ergebnis_modelle.csv",     # von 04
    "sensitivitaet": PROCESSED / "sensitivitaet.csv",           # von 04
}

# ----------------------------------------------------------------------------
# RÄUMLICHE EINSTELLUNGEN
# ----------------------------------------------------------------------------
# Koordinatensystem für alle Berechnungen: UTM Zone 33N.
# WARUM: Koordinaten in METERN -> Distanzen, Flächen und Puffer direkt in m.
CRS = "EPSG:32633"

# Untersuchungsgebiet: Stadt Graz. Für Wegenetz und Supermärkte zusätzlich 2 km Puffer,
# damit Supermärkte knapp hinter der Stadtgrenze (Seiersberg, Raaba ...) mitzählen.
ORT = "Graz, Austria"
PUFFER_M = 2000

# ----------------------------------------------------------------------------
# MODELL-EINSTELLUNGEN
# ----------------------------------------------------------------------------
# Zeitpunkte für die Öffnungszeiten: ein normaler Dienstag (kein Feiertag).
# Paper: 17:00 und 06:00. In Österreich hat um 06:00 fast nichts offen -> 07:00.
# Der Schlüssel ("17", "07") taucht in Spaltennamen auf: offen_17, dist_07 ...
ZEITPUNKTE = {
    "17": datetime(2026, 11, 10, 17, 0),
    "07": datetime(2026, 11, 10, 7, 0),
}

# Supermärkte OHNE Öffnungszeiten in OSM:
#   False -> gelten als geschlossen (vorsichtig)   True -> gelten als offen (großzügig)
OH_FEHLT_ALS_OFFEN = False

# Verteilung der Bezirksbevölkerung auf Wohngebäude:
#   "flaeche" -> proportional zur Grundfläche   "gleich" -> jedes Gebäude gleich viele
GEWICHTUNG = "flaeche"

# Gehzeit-Grenzen für die Auswertung in Minuten (wie im Paper)
GRENZEN_MIN = [10, 15, 20]

# Messdaten der Gehgeschwindigkeiten (Original-Repo der Autor:innen, Apache 2.0)
SPEED_URL = ("https://raw.githubusercontent.com/DigitalGeographyLab/"
             "15_minute_city_for_all_article/HEAD/data/")

# ----------------------------------------------------------------------------
# OSMnx: CACHE und ROBUSTE DOWNLOADS
# ----------------------------------------------------------------------------
# use_cache: jede Antwort der OSM-Server wird in data/raw/osmnx_cache gespeichert.
# Beim nächsten Lauf wird die lokale Datei verwendet statt neu zu laden.
ox.settings.use_cache = True
ox.settings.cache_folder = str(RAW / "osmnx_cache")
ox.settings.requests_timeout = 600
ox.settings.log_console = False

# Die öffentlichen Overpass-Server (liefern die OSM-Daten) sind oft überlastet
# ("502 ... server is currently at capacity"). Dann probieren wir es erneut
# und weichen auf Spiegelserver mit denselben Daten aus.
OVERPASS_SERVER = [
    "https://overpass-api.de/api",                    # Hauptserver
    "https://maps.mail.ru/osm/tools/overpass/api",    # Spiegelserver
    "https://overpass.private.coffee/api",            # Spiegelserver
]


# *args / **kwargs nehmen beliebig viele weitere Argumente an und reichen sie
# unverändert an die OSMnx-Funktion weiter (z. B. das Polygon und tags={...}).
def osm_laden(funktion, *args, versuche_pro_server=2, **kwargs):
    """Ruft eine OSMnx-Downloadfunktion auf und wiederholt sie bei Serverfehlern.

    Beispiel:  osm_laden(ox.features_from_polygon, polygon, tags={"shop": "supermarket"})
    """
    letzter_fehler = None
    for server in OVERPASS_SERVER:
        ox.settings.overpass_url = server
        # Nur der Hauptserver hat den Status-Endpunkt, über den OSMnx Wartezeiten abfragt
        ox.settings.overpass_rate_limit = server.startswith("https://overpass-api.de")
        for versuch in range(versuche_pro_server):
            try:
                return funktion(*args, **kwargs)
            except Exception as fehler:       # Serverfehler, Zeitüberschreitung ...
                letzter_fehler = fehler
                print(f"  OSM-Server {server} nicht erreichbar ({type(fehler).__name__}),"
                      " neuer Versuch ...")
                # Wartezeit wächst mit jedem Versuch: 15 s, 30 s, ...
                time.sleep(15 * (versuch + 1))
    # Alle Server und Versuche erfolglos -> den letzten Fehler anzeigen
    raise letzter_fehler


def untersuchungsgebiet():
    """Stadtgrenze von Graz (aus OSM) und das Gebiet mit Puffer.

    Rückgabe:
        graz       GeoDataFrame der Stadtgrenze im Projekt-CRS (EPSG:32633)
        graz_wgs   Polygon der Stadt in WGS84    -> für OSM-Downloads im Stadtgebiet
        gebiet_wgs Polygon Stadt + Puffer, WGS84 -> für Downloads mit Puffer
    (OSMnx erwartet Polygone für Downloads in WGS84 = Längen-/Breitengrad.)
    """
    graz = ox.geocode_to_gdf(ORT).to_crs(CRS)
    gebiet = graz.buffer(PUFFER_M)               # Puffer in Metern -> geht nur im Meter-CRS
    graz_wgs = graz.to_crs(4326).geometry.iloc[0]
    gebiet_wgs = gebiet.to_crs(4326).iloc[0]
    return graz, graz_wgs, gebiet_wgs


def pruefe_eingabe(schluessel, notebook):
    """Bricht mit einer verständlichen Meldung ab, wenn eine Eingabedatei fehlt."""
    datei = DATEIEN[schluessel]
    if not datei.exists():
        raise FileNotFoundError(
            f"{datei.name} fehlt. Bitte zuerst Notebook {notebook} ausführen.")
    return datei
