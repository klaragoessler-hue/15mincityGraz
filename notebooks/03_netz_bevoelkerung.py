import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # ------------------------------------------------------------------
    # BIBLIOTHEKEN UND GEMEINSAME EINSTELLUNGEN
    # ------------------------------------------------------------------
    # pandas    -> Tabellen
    # geopandas -> Tabellen mit Geometrie, Projektionen, räumliche Joins
    # osmnx     -> lädt Daten aus OpenStreetMap (Wegenetz, Gebäude, Bezirksgrenzen)
    import marimo as mo

    import pandas as pd
    import geopandas as gpd
    import osmnx as ox

    from einstellungen import (CRS, DATEIEN, GEWICHTUNG, osm_laden, pruefe_eingabe,
                               untersuchungsgebiet)
    return CRS, DATEIEN, GEWICHTUNG, gpd, mo, osm_laden, ox, pd, pruefe_eingabe, untersuchungsgebiet


@app.cell
def _(mo):
    mo.md(r"""
    # 03 – Fußwegnetz, Bezirke und Bevölkerung

    **Eingabe:** OpenStreetMap (automatisch) und `data/raw/bezirke_bevoelkerung.csv` (Notebook 00)
    **Ausgabe** → werden von Notebook 04 gelesen:

    - `data/processed/walk_network_graz.graphml` – das Fußwegnetz
    - `data/processed/bezirke.gpkg` – die 17 Bezirke mit Einwohnern
    - `data/processed/wohngebaeude.gpkg` – Wohngebäude als Punkte mit geschätzten Einwohnern

    **Abweichung vom Paper:** Das Paper startet von den Mittelpunkten eines offiziellen
    250-m-Bevölkerungsrasters. Für Graz gibt es so ein Raster nicht frei. Wir nehmen
    deshalb **Wohngebäude aus OSM** als Startpunkte und verteilen die **Bevölkerung jedes
    Bezirks** auf seine Wohngebäude („dasymetrische Kartierung“).
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## So liest du dieses Notebook (marimo-Grundlagen)

    - **Zellen:** Jede Zelle ist eine kleine Python-Funktion `def _(...)`.
      In den Klammern stehen die Variablen, die die Zelle **von anderen Zellen braucht**.
      Mit `return (...)` am Ende gibt sie Variablen **an andere Zellen weiter**.
      Daraus erkennt marimo selbst, in welcher Reihenfolge die Zellen laufen müssen.
    - **Reaktiv:** Ändert man eine Zelle, rechnet marimo automatisch alle Zellen neu,
      die davon abhängen (anders als Jupyter, wo man selbst in der richtigen Reihenfolge ausführt).
    - **Unterstrich `_name`:** Variablen mit `_` am Anfang gelten **nur in ihrer Zelle**.
      So können mehrere Zellen z. B. `_k` oder `_zeilen` verwenden, ohne sich zu stören.
      Ohne `_` darf ein Variablenname nur in **einer einzigen** Zelle festgelegt werden.
    - **`.copy()`:** Eine Zelle soll Daten einer anderen Zelle nicht verändern
      (marimo bemerkt solche Änderungen nicht und rechnet sonst nicht richtig neu).
      Deshalb wird zuerst kopiert und dann die Kopie verändert.
    - **Anzeige:** Steht in der letzten Zeile einer Zelle nur ein Name (z. B. eine Tabelle),
      zeigt marimo sie unter der Zelle an. Ausgaben von `print(...)` erscheinen ebenfalls dort.
    - **`f"..."`-Texte:** In einem f-String wird `{x}` durch den Wert von `x` ersetzt.
      `{x:,}` setzt Tausendertrennzeichen, `{x:.1f}` eine Nachkommastelle, `{x:.1%}` Prozent.
    - **Als Skript:** `uv run python notebooks/<datei>.py` führt alle Zellen nacheinander aus.
    """)
    return


@app.cell
def _(untersuchungsgebiet):
    # ------------------------------------------------------------------
    # 1. UNTERSUCHUNGSGEBIET (Funktion aus einstellungen.py)
    # ------------------------------------------------------------------
    # graz = Stadtgrenze in Metern, graz_wgs / gebiet_wgs = Polygone für OSM-Downloads
    graz, graz_wgs, gebiet_wgs = untersuchungsgebiet()
    # .area = Fläche in m² (weil Meter-Koordinaten), / 1e6 = in km² (1e6 = 1.000.000)
    # .iloc[0] = erste (und einzige) Zeile
    print(f"Fläche Graz: {graz.area.iloc[0] / 1e6:.1f} km²")
    return gebiet_wgs, graz, graz_wgs


@app.cell
def _(CRS, DATEIEN, gebiet_wgs, osm_laden, ox):
    # ------------------------------------------------------------------
    # 2. FUSSWEGNETZ aus OpenStreetMap
    # ------------------------------------------------------------------
    # Ein Netz besteht aus KNOTEN (Kreuzungen, Wegpunkte) und KANTEN (Wegstücke).
    # Jede Kante hat das Attribut "length" = Länge in Metern -> Gewicht fürs Routing.
    #
    # network_type="walk": alle Wege, die zu Fuß begehbar sind (Gehsteige, Fußwege,
    # Wohnstraßen, Stiegen ...), ohne Autobahnen. Alle Kanten sind in BEIDE Richtungen
    # begehbar (zu Fuß gibt es keine Einbahnen) -> wichtig für das Routing in Notebook 04.
    #
    # Inseln: OSMnx behält standardmäßig nur das größte zusammenhängende Netz
    # (retain_all=False). Das Original musste ~20 Knoten von Hand löschen.
    #
    # Gebiet mit 2 km Puffer: Wege zu Supermärkten knapp hinter der Stadtgrenze.
    if DATEIEN["netz"].exists():
        G = ox.load_graphml(DATEIEN["netz"])   # schon einmal geladen -> von der Festplatte
    else:
        # graph_from_polygon macht intern: Wege aus OSM laden -> jeder OSM-Punkt wird
        # Knoten, jedes Wegstück Kante -> Zwischenpunkte, die keine Kreuzung sind,
        # entfernen (simplify) -> Länge jeder Kante in m berechnen -> Inseln entfernen.
        G = osm_laden(ox.graph_from_polygon, gebiet_wgs, network_type="walk")
        G = ox.project_graph(G, to_crs=CRS)    # Knoten-Koordinaten in Metern
        ox.save_graphml(G, DATEIEN["netz"])

    print(f"Fußwegnetz: {G.number_of_nodes():,} Knoten, {G.number_of_edges():,} Kanten")
    return (G,)


@app.cell
def _(CRS, DATEIEN, graz_wgs, osm_laden, ox, pd, pruefe_eingabe):
    # ------------------------------------------------------------------
    # 3. BEZIRKE + EINWOHNER
    # ------------------------------------------------------------------
    # Die 17 Grazer Bezirke sind in OSM Verwaltungsgrenzen mit admin_level = 9.
    # Wir fragen direkt nach admin_level=9 (nicht nach allen Verwaltungsgrenzen),
    # sonst würde OSMnx auch die riesigen Grenzen von Österreich und der Steiermark laden.
    _grenzen = osm_laden(ox.features_from_polygon, graz_wgs, tags={"admin_level": "9"})
    _grenzen = _grenzen.reset_index()
    # Zwei Bedingungen mit & (UND) verknüpft, jede in eigenen Klammern:
    #  - admin_level ist "9" (in OSM ist das ein Text, keine Zahl)
    #  - die Geometrie ist eine Fläche (Polygon) und keine Linie
    # Danach nur Name und Geometrie behalten, "name" in "bezirk" umbenennen.
    _bezirke_geo = _grenzen[
        (_grenzen["admin_level"] == "9")
        & _grenzen.geom_type.isin(["Polygon", "MultiPolygon"])
    ][["name", "geometry"]].rename(columns={"name": "bezirk"}).to_crs(CRS)

    # Einwohner und Altersdaten aus Notebook 00 (Stadt Graz, Stand 1.1.2026)
    _csv = pd.read_csv(pruefe_eingabe("bezirke_csv", "00"), sep=";")

    # Zusammenführen über den Namen (die Namen in der CSV sind an OSM angepasst)
    # how="inner": nur Bezirke behalten, die in BEIDEN Tabellen vorkommen
    bezirke = _bezirke_geo.merge(_csv, on="bezirk", how="inner")

    # Kontrolle: Es müssen genau 17 sein, sonst passt ein Name nicht zusammen
    assert len(bezirke) == 17, f"Nur {len(bezirke)} Bezirke zugeordnet – Namen prüfen!"
    bezirke.to_file(DATEIEN["bezirke"], driver="GPKG")
    bezirke.drop(columns="geometry").sort_values("bezirk_nr")
    return (bezirke,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Wohngebäude und Bevölkerung

    In OSM haben ~60 % der Grazer Gebäude keinen genauen Typ (`building=yes`).
    Als **Wohngebäude** zählen deshalb:

    - **dabei:** eindeutige Wohntypen (`apartments`, `house`, `detached`, `residential`, …)
    - **dabei:** `building=yes` **mit Hausnummer** und ohne Hinweis auf Geschäft/Büro/Gewerbe
    - **nicht dabei:** Garagen, Schuppen, Gewerbe, Industrie, Büros, …

    Dann wird die **Bevölkerung jedes Bezirks auf seine Wohngebäude verteilt**,
    standardmäßig proportional zur Grundfläche (`GEWICHTUNG` in `einstellungen.py`):

    $$\text{Einwohner}_\text{Gebäude} = \text{Hauptwohnsitze}_\text{Bezirk} \cdot
    \frac{\text{Fläche}_\text{Gebäude}}{\sum \text{Fläche aller Wohngebäude im Bezirk}}$$

    Ältere pro Gebäude = Einwohner × Anteil 65+ des Bezirks.
    Wir verwenden die **Hauptwohnsitze**, weil es nur für sie Altersdaten gibt.
    """)
    return


@app.cell
def _(CRS, DATEIEN, GEWICHTUNG, bezirke, gpd, graz_wgs, osm_laden, ox, pd):
    # ------------------------------------------------------------------
    # 4. WOHNGEBÄUDE + BEVÖLKERUNGSVERTEILUNG
    # ------------------------------------------------------------------
    # Alle Gebäude im Stadtgebiet (OHNE Puffer: Bevölkerungszahlen gibt es nur für Graz)
    _alle = osm_laden(ox.features_from_polygon, graz_wgs, tags={"building": True}).reset_index()
    # Nur Flächen (manche Gebäude sind in OSM nur als Punkt eingetragen -> ohne Fläche)
    _alle = _alle[_alle.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(CRS)

    def _sp(name):
        """Spalte oder leere Spalte, falls OSM das Tag gar nicht liefert."""
        return _alle[name] if name in _alle.columns else pd.Series(pd.NA, index=_alle.index)

    # Gebäudetypen, die eindeutig Wohngebäude sind (OSM-Wiki: Key:building)
    _wohntypen = {"apartments", "house", "detached", "residential", "semidetached_house",
                  "terrace", "bungalow", "dormitory", "farm"}
    _typ = _sp("building")
    _ist_wohntyp = _typ.isin(_wohntypen)

    # building=yes mit Hausnummer, aber ohne Hinweis auf Geschäft/Büro/Gewerbe
    # Startwert: bei allen Gebäuden "keine Nutzung gefunden" (False).
    # |= heißt "ODER gleich": wird für irgendein Tag eine Angabe gefunden, wird es True.
    _nutzung = pd.Series(False, index=_alle.index)
    for _tag in ["shop", "amenity", "office", "craft", "tourism", "industrial"]:
        _nutzung |= _sp(_tag).notna()
    _ist_adresse = (_typ == "yes") & _sp("addr:housenumber").notna() & ~_nutzung

    _wohn = _alle.loc[_ist_wohntyp | _ist_adresse, ["building", "geometry"]].copy()
    _wohn["flaeche_m2"] = _wohn.geometry.area                # Grundfläche in m²
    # Vermerk, nach welcher Regel das Gebäude ausgewählt wurde (für die Kontrolle unten)
    _wohn["auswahl"] = _ist_wohntyp[_wohn.index].map({True: "Wohntyp", False: "yes+Hausnummer"})
    _wohn["geometry"] = _wohn.geometry.representative_point()   # Gebäude -> Punkt

    # Räumlicher Join: in welchem Bezirk liegt jedes Gebäude?
    # sjoin = "spatial join": verbindet Tabellen nicht über eine Spalte, sondern über die Lage.
    #   predicate="within": ein Gebäudepunkt bekommt die Daten des Bezirks, IN dem er liegt
    #   how="inner": Gebäude, die in keinem Bezirk liegen, fallen weg
    # sjoin fügt eine Hilfsspalte "index_right" hinzu, die wir gleich wieder löschen.
    _wohn = gpd.sjoin(
        _wohn,
        bezirke[["bezirk", "einwohner_hws", "anteil_65plus", "geometry"]],
        predicate="within", how="inner",
    ).drop(columns="index_right")

    # Gewicht pro Gebäude und Verteilung der Bezirksbevölkerung
    # Kurzform von if/else: Gewicht = Fläche, wenn GEWICHTUNG "flaeche" ist, sonst 1
    _wohn["gewicht"] = _wohn["flaeche_m2"] if GEWICHTUNG == "flaeche" else 1.0
    # groupby("bezirk")["gewicht"].transform("sum"): Summe der Gewichte im Bezirk.
    # Anders als .sum() (17 Werte, einer pro Bezirk) schreibt transform die Summe
    # ZU JEDEM GEBÄUDE, damit man direkt Zeile für Zeile teilen kann:
    #   Gebäude  Bezirk  gewicht  _summe
    #   A        Lend    200      90000
    #   B        Lend    800      90000
    _summe = _wohn.groupby("bezirk")["gewicht"].transform("sum")
    # Einwohner im Gebäude = Einwohner im Bezirk × (Gewicht des Gebäudes / Summe im Bezirk)
    # -> Summe über alle Gebäude eines Bezirks ergibt wieder genau die Bezirksbevölkerung
    _wohn["einwohner"] = _wohn["einwohner_hws"] * _wohn["gewicht"] / _summe
    _wohn["einwohner_65"] = _wohn["einwohner"] * _wohn["anteil_65plus"]

    wohngebaeude = _wohn[["building", "auswahl", "bezirk", "flaeche_m2",
                          "einwohner", "einwohner_65", "geometry"]].reset_index(drop=True)
    wohngebaeude.to_file(DATEIEN["wohngebaeude"], driver="GPKG")

    print(f"OSM-Gebäude gesamt: {len(_alle):,} -> Wohngebäude: {len(wohngebaeude):,}")
    print(f"Verteilte Einwohner: {wohngebaeude['einwohner'].sum():,.0f}"
          f" (Soll: {bezirke['einwohner_hws'].sum():,})")
    print("Gespeichert:", DATEIEN["wohngebaeude"])

    # Kontrolle: Pro Bezirk muss die Summe wieder die Bezirksbevölkerung ergeben
    # .agg(neuer_name=(spalte, funktion), ...) berechnet mehrere Kennzahlen je Bezirk.
    # Die lambda-Funktion zählt, wie viele Gebäude über die Regel "Wohntyp" kamen.
    wohngebaeude.groupby("bezirk").agg(
        gebaeude=("einwohner", "size"),
        davon_wohntyp=("auswahl", lambda s: int((s == "Wohntyp").sum())),
        einwohner=("einwohner", "sum"),
        einwohner_65=("einwohner_65", "sum"),
    ).round(0)
    return (wohngebaeude,)


if __name__ == "__main__":
    app.run()
