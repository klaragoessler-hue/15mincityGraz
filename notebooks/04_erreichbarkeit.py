import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # ------------------------------------------------------------------
    # BIBLIOTHEKEN UND GEMEINSAME EINSTELLUNGEN
    # ------------------------------------------------------------------
    # numpy     -> Zahlenreihen (z. B. Geschwindigkeiten 3,0 ... 6,0 km/h)
    # pandas    -> Tabellen
    # geopandas -> Geodaten lesen/schreiben
    # networkx  -> Graphen-Algorithmen, hier: kürzeste Wege (Dijkstra)
    # osmnx     -> Netz laden, nächsten Netzknoten finden
    import marimo as mo

    import numpy as np
    import pandas as pd
    import geopandas as gpd
    import networkx as nx
    import osmnx as ox
    import matplotlib.pyplot as plt

    from einstellungen import DATEIEN, GRENZEN_MIN, ZEITPUNKTE, pruefe_eingabe
    return DATEIEN, GRENZEN_MIN, ZEITPUNKTE, gpd, mo, np, nx, ox, pd, plt, pruefe_eingabe


@app.cell
def _(mo):
    mo.md(r"""
    # 04 – Erreichbarkeit: Gehzeit zum nächsten offenen Supermarkt

    **Eingabe** (aus den Notebooks 01–03):

    | Datei | von |
    |---|---|
    | `speeds.csv` – die 4 Gehgeschwindigkeiten | 01 |
    | `supermaerkte.gpkg` – Supermärkte mit `offen_17`, `offen_07` | 02 |
    | `walk_network_graz.graphml` – Fußwegnetz | 03 |
    | `wohngebaeude.gpkg` – Wohngebäude mit Einwohnern | 03 |
    | `bezirke.gpkg` – Bezirksgrenzen (nur für die Karte) | 03 |

    **Ausgabe** → für Notebook 05 (Abbildungen) und den Bericht:
    `ergebnis_gebaeude.gpkg`, `ergebnis_modelle.csv`, `sensitivitaet.csv`

    **Ablauf**
    1. Eingaben laden
    2. Gebäude und Supermärkte ans Wegenetz anhängen
    3. Routing: Distanz von jedem Wohngebäude zum nächsten offenen Supermarkt
    4. Gehzeiten für die 8 Modelle
    5. Ergebnis: Anteil der Bevölkerung mit Supermarkt in 10 / 15 / 20 min
    6. Sensitivitätsanalyse über die Gehgeschwindigkeit
    7. Kontrollkarte
    8. Speichern
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
def _(gpd, ox, pd, pruefe_eingabe):
    # ------------------------------------------------------------------
    # 1. EINGABEN LADEN (bricht verständlich ab, falls ein Notebook noch nicht lief)
    # ------------------------------------------------------------------
    _speeds = pd.read_csv(pruefe_eingabe("speeds", "01"), sep=";")
    # zip verbindet zwei Spalten paarweise, dict macht daraus {"erw_trocken": 5.16, ...}
    SPEEDS_KMH = dict(zip(_speeds["schluessel"], _speeds["kmh"]))

    shops = gpd.read_file(pruefe_eingabe("supermaerkte", "02"))
    G = ox.load_graphml(pruefe_eingabe("netz", "03"))
    wohngebaeude = gpd.read_file(pruefe_eingabe("wohngebaeude", "03"))
    bezirke = gpd.read_file(pruefe_eingabe("bezirke", "03"))

    print("Geschwindigkeiten (km/h):", SPEEDS_KMH)
    print(f"Supermärkte: {len(shops)}, Wohngebäude: {len(wohngebaeude):,},"
          f" Netz: {G.number_of_nodes():,} Knoten")
    return G, SPEEDS_KMH, bezirke, shops, wohngebaeude


@app.cell
def _(G, ox, shops, wohngebaeude):
    # ------------------------------------------------------------------
    # 2. ANS WEGENETZ ANHÄNGEN ("snapping")
    # ------------------------------------------------------------------
    # Routing geht nur von Knoten zu Knoten. Jedes Gebäude und jeder Supermarkt
    # bekommt deshalb den NÄCHSTGELEGENEN Netzknoten (Luftlinie).
    # return_dist=True liefert zusätzlich, wie weit dieser Knoten entfernt ist.
    # (Entspricht nearestNodeID() im Original. Funktioniert, weil Netz und Punkte
    #  im selben Koordinatensystem sind, EPSG:32633.)
    gebaeude_netz = wohngebaeude.copy()
    _n, _d = ox.distance.nearest_nodes(
        G, gebaeude_netz.geometry.x, gebaeude_netz.geometry.y, return_dist=True
    )
    # nearest_nodes gibt zwei Listen zurück: Knoten-IDs (_n) und Abstände (_d).
    # Beide werden in einem Schritt als neue Spalten gespeichert.
    gebaeude_netz["node"], gebaeude_netz["snap_m"] = _n, _d

    shops_netz = shops.copy()
    _n, _d = ox.distance.nearest_nodes(
        G, shops_netz.geometry.x, shops_netz.geometry.y, return_dist=True
    )
    shops_netz["node"], shops_netz["snap_m"] = _n, _d

    # Wie im Paper wird der Weg vom Gebäude bis zum Knoten NICHT zur Distanz addiert.
    # Zur Einordnung: Wie groß ist dieser Fehler typischerweise?
    print(f"Abstand Gebäude -> Netzknoten: Median {gebaeude_netz.snap_m.median():.0f} m,"
          # quantile(.95) = 95 % der Gebäude liegen näher als dieser Wert
          f" 95 % unter {gebaeude_netz.snap_m.quantile(.95):.0f} m")
    print(f"Abstand Supermarkt -> Netzknoten: Median {shops_netz.snap_m.median():.0f} m")
    return gebaeude_netz, shops_netz


@app.cell
def _(mo):
    mo.md(r"""
    ## Routing – das Herzstück

    **Original:** Pandana berechnet die Weglänge für **jede Kombination**
    Startpunkt × Supermarkt (in Helsinki ~5 Mio. Routen) und nimmt dann pro Startpunkt
    das Minimum.

    **Wir:** Ein **Multi-Source-Dijkstra**. Der Algorithmus startet **gleichzeitig von
    allen offenen Supermärkten** und breitet sich im Netz aus. Jeder Knoten wird genau
    einmal erreicht, und zwar vom nächstgelegenen Supermarkt aus. Ergebnis: für jeden
    Knoten die Distanz zum nächsten offenen Supermarkt – in **einem** Durchlauf.

    Das liefert dasselbe wie das Original, weil Fußwege in beide Richtungen begehbar sind
    (Weg Supermarkt → Gebäude = Weg Gebäude → Supermarkt).
    """)
    return


@app.cell
def _(G, ZEITPUNKTE, gebaeude_netz, nx, shops_netz):
    # ------------------------------------------------------------------
    # 3. ROUTING: Distanz jedes Wohngebäudes zum nächsten OFFENEN Supermarkt
    # ------------------------------------------------------------------
    routing = gebaeude_netz.copy()
    for _k in ZEITPUNKTE:
        # Startknoten = alle Supermärkte, die zu diesem Zeitpunkt offen sind.
        # set(...) entfernt doppelte Knoten (entspricht getUniqueNodes() im Original).
        # True/False-Spalte aus Notebook 02 (astype(bool) zur Sicherheit nach dem Einlesen)
        _offen = shops_netz[f"offen_{_k}"].astype(bool)
        _quellen = set(shops_netz.loc[_offen, "node"])

        # Dictionary {Knoten: Distanz in m} für alle erreichbaren Knoten
        # So arbeitet Dijkstra: Er startet bei den Quellen (Distanz 0) und nimmt immer
        # den noch nicht fertigen Knoten mit der kleinsten bekannten Distanz. Von dort
        # prüft er alle Nachbarn: Ist der Weg über diesen Knoten kürzer als bisher
        # bekannt, wird die Distanz verbessert. Weil immer der nächste Knoten zuerst
        # drankommt, ist jede Distanz endgültig, sobald ein Knoten fertig ist.
        # weight="length": Kantenlänge in Metern als Kosten.
        _dist = nx.multi_source_dijkstra_path_length(G, _quellen, weight="length")

        # Jedes Gebäude bekommt die Distanz seines Knotens.
        # Nicht erreichbare Knoten fehlen im Dictionary -> NaN
        # .map(dictionary): Für jedes Gebäude wird seine Knoten-ID im Dictionary
        # nachgeschlagen und durch die Distanz ersetzt:  Knoten 4711 -> 635.2 (m)
        routing[f"dist_{_k}"] = routing["node"].map(_dist)
        print(f"{_k} Uhr: {int(_offen.sum())} offene Supermärkte,"
              f" Median-Distanz {routing[f'dist_{_k}'].median():.0f} m,"
              f" nicht erreichbar: {routing[f'dist_{_k}'].isna().sum()} Gebäude")
    return (routing,)


@app.cell
def _(SPEEDS_KMH, pd, routing):
    # ------------------------------------------------------------------
    # 4. DIE 8 MODELLE: Gehzeit = Distanz / Geschwindigkeit
    # ------------------------------------------------------------------
    # Nummerierung wie im Paper (Fig. 2 / Fig. 4). "07" steht für früh morgens
    # (im Paper 06:00, für Graz 07:00 – siehe einstellungen.py).
    MODELLE = pd.DataFrame([
        # nr, Alter,        Saison,    Zeit, Schlüssel der Geschwindigkeit
        (1, "Erwachsene", "trocken", "17", "erw_trocken"),
        (2, "Ältere",     "trocken", "17", "alt_trocken"),
        (3, "Erwachsene", "Winter",  "17", "erw_winter"),
        (4, "Erwachsene", "trocken", "07", "erw_trocken"),
        (5, "Ältere",     "Winter",  "17", "alt_winter"),
        (6, "Ältere",     "trocken", "07", "alt_trocken"),
        (7, "Erwachsene", "Winter",  "07", "erw_winter"),
        (8, "Ältere",     "Winter",  "07", "alt_winter"),
    ], columns=["modell", "alter", "saison", "zeit", "speed"])
    # Zu jedem Modell die passende Geschwindigkeit aus Notebook 01 nachschlagen
    MODELLE["kmh"] = MODELLE["speed"].map(SPEEDS_KMH)

    modelle_ergebnis = routing.copy()
    # iterrows() geht die Tabelle Zeile für Zeile durch. Pro Zeile kommt (Index, Zeile)
    # zurück; den Index brauchen wir nicht -> "_". _m.kmh = Wert der Spalte "kmh".
    for _, _m in MODELLE.iterrows():
        _m_pro_min = _m.kmh * 1000 / 60          # km/h -> Meter pro Minute
        modelle_ergebnis[f"min_m{_m.modell}"] = modelle_ergebnis[f"dist_{_m.zeit}"] / _m_pro_min
    MODELLE
    return MODELLE, modelle_ergebnis


@app.cell
def _(GRENZEN_MIN, MODELLE, modelle_ergebnis, pd):
    # ------------------------------------------------------------------
    # 5. ERGEBNIS: Welcher Anteil erreicht in 10 / 15 / 20 min einen Supermarkt?
    # ------------------------------------------------------------------
    # Zwei Bezugsgrößen:
    #  - "Bevölkerung": alle Einwohner. So hat das Original tatsächlich gerechnet
    #    (Szenario: "wenn ALLE so gehen würden wie die Gruppe im Modell").
    #  - "65+": nur die über 65-Jährigen. So formuliert es das Abstract des Papers.
    # Nicht erreichbare Gebäude (NaN) zählen als "nicht erreicht".
    _ew = modelle_ergebnis["einwohner"]
    _ew65 = modelle_ergebnis["einwohner_65"]

    # Helsinki-Werte aus dem Original (15 min, Anteil der Gesamtbevölkerung)
    _helsinki_15 = {1: 93.4, 2: 88.5, 3: 91.8, 4: 45.0, 5: 85.9, 6: 38.0, 7: 42.2, 8: 34.4}

    _zeilen = []
    for _, _m in MODELLE.iterrows():
        _min = modelle_ergebnis[f"min_m{_m.modell}"]
        _z = {"Modell": _m.modell, "Alter": _m.alter, "Saison": _m.saison,
              "Uhrzeit": f"{_m.zeit}:00", "km/h": _m.kmh}
        for _g in GRENZEN_MIN:
            # _ew[_min <= _g]: Einwohner nur der Gebäude mit Gehzeit ≤ Grenze;
            # .sum() / _ew.sum() = Anteil an allen Einwohnern; × 100 = Prozent.
            # Gebäude ohne Distanz (NaN) sind bei "<=" automatisch False.
            _z[f"Bevölkerung ≤{_g} min (%)"] = round(100 * _ew[_min <= _g].sum() / _ew.sum(), 1)
        _z["65+ ≤15 min (%)"] = round(100 * _ew65[_min <= 15].sum() / _ew65.sum(), 1)
        _z["Helsinki ≤15 min (%)"] = _helsinki_15[_m.modell]
        _zeilen.append(_z)
    ergebnis_tabelle = pd.DataFrame(_zeilen)
    ergebnis_tabelle
    return (ergebnis_tabelle,)


@app.cell
def _(modelle_ergebnis, pd):
    # Ergebnis pro Bezirk (Anteil der Bevölkerung mit Supermarkt in ≤ 15 min)
    # -> zeigt, WO in Graz die Versorgung schlecht ist
    # Hilfsfunktion: Anteil der Einwohner mit Gehzeit ≤ 15 min in einer Teil-Tabelle d
    def _anteil(d, spalte):
        return 100 * d["einwohner"][d[spalte] <= 15].sum() / d["einwohner"].sum()

    # groupby("bezirk").apply(_anteil, "min_m1"): teilt die Gebäude nach Bezirk auf und
    # ruft _anteil(teiltabelle, "min_m1") für jeden Bezirk auf -> ein Wert je Bezirk.
    # include_groups=False: die Bezirksspalte selbst nicht an die Funktion mitgeben.
    ergebnis_bezirke = pd.DataFrame({
        "Modell 1 (%)": modelle_ergebnis.groupby("bezirk").apply(_anteil, "min_m1", include_groups=False),
        "Modell 8 (%)": modelle_ergebnis.groupby("bezirk").apply(_anteil, "min_m8", include_groups=False),
    }).round(0).sort_values("Modell 8 (%)")
    ergebnis_bezirke
    return (ergebnis_bezirke,)


@app.cell
def _(ZEITPUNKTE, modelle_ergebnis, np, pd):
    # ------------------------------------------------------------------
    # 6. SENSITIVITÄTSANALYSE: Wie stark hängt das Ergebnis von der Gehgeschwindigkeit ab?
    # ------------------------------------------------------------------
    # Entspricht der Idee von calculateWalkingTimes() im Original (3,0–7,0 km/h),
    # aber wir berechnen direkt das Hauptergebnis: Anteil der Bevölkerung ≤ 15 min.
    _ew = modelle_ergebnis["einwohner"]
    _zeilen = []
    # np.arange(3.0, 6.01, 0.1) = 3.0, 3.1, ..., 6.0 (Ende 6.01, damit 6.0 dabei ist);
    # np.round(..., 1) entfernt Rundungsfehler wie 3.3000000000000003
    for _kmh in np.round(np.arange(3.0, 6.01, 0.1), 1):
        _z = {"km/h": _kmh}
        for _k in ZEITPUNKTE:
            _min = modelle_ergebnis[f"dist_{_k}"] / (_kmh * 1000 / 60)
            _z[f"{_k} Uhr (%)"] = round(100 * _ew[_min <= 15].sum() / _ew.sum(), 1)
        _zeilen.append(_z)
    sensitivitaet = pd.DataFrame(_zeilen)
    sensitivitaet
    return (sensitivitaet,)


@app.cell
def _(bezirke, modelle_ergebnis, plt, shops_netz):
    # ------------------------------------------------------------------
    # 7. KONTROLLKARTE (keine fertige Abbildung, nur zum Prüfen!)
    # ------------------------------------------------------------------
    # Modell 1 (Erwachsene, trocken, 17 Uhr) vs. Modell 8 (Ältere, Winter, 7 Uhr).
    # Farbe = Gehzeit zum nächsten offenen Supermarkt, bei 30 min abgeschnitten.
    # Rote Punkte = zu diesem Zeitpunkt offene Supermärkte.
    # plt.subplots(1, 2): eine Abbildung mit 1 Zeile und 2 Karten nebeneinander
    _fig, _axes = plt.subplots(1, 2, figsize=(14, 7))
    # zip verbindet jede Karte (_ax) mit einem Modell (Nummer, Zeitpunkt, Titel)
    for _ax, (_nr, _zeit, _titel) in zip(_axes, [(1, "17", "Modell 1: Erwachsene, trocken, 17:00"),
                                                (8, "07", "Modell 8: Ältere, Winter, 07:00")]):
        bezirke.boundary.plot(ax=_ax, color="grey", linewidth=0.5)
        modelle_ergebnis.plot(ax=_ax, column=f"min_m{_nr}", cmap="viridis_r",
                              vmin=0, vmax=30, markersize=1, legend=True,
                              legend_kwds={"label": "Gehzeit (min)", "shrink": 0.6})
        shops_netz[shops_netz[f"offen_{_zeit}"].astype(bool)].plot(ax=_ax, color="red", markersize=8)
        # Kartenausschnitt auf Graz begrenzen (total_bounds = [xmin, ymin, xmax, ymax];
        # * verteilt die zwei Werte auf die zwei Parameter von set_xlim)
        _ax.set_xlim(*bezirke.total_bounds[[0, 2]])
        _ax.set_ylim(*bezirke.total_bounds[[1, 3]])
        _ax.set_title(_titel)
        _ax.set_axis_off()
    plt.tight_layout()
    _fig
    return


@app.cell
def _(DATEIEN, MODELLE, ergebnis_tabelle, modelle_ergebnis, sensitivitaet):
    # ------------------------------------------------------------------
    # 8. SPEICHERN -> Grundlage für Notebook 05 (Abbildungen) und den Bericht
    # ------------------------------------------------------------------
    # Liste der Spalten zum Speichern: feste Spalten + min_m1 ... min_m8 + Geometrie
    _spalten = (["building", "auswahl", "bezirk", "flaeche_m2", "einwohner", "einwohner_65",
                 "node", "snap_m", "dist_17", "dist_07"]
                + [f"min_m{n}" for n in MODELLE["modell"]] + ["geometry"])
    modelle_ergebnis[_spalten].to_file(DATEIEN["ergebnis_gebaeude"], driver="GPKG")
    ergebnis_tabelle.to_csv(DATEIEN["ergebnis_modelle"], sep=";", index=False)
    sensitivitaet.to_csv(DATEIEN["sensitivitaet"], sep=";", index=False)
    print("Gespeichert:", DATEIEN["ergebnis_gebaeude"].parent)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Abweichungen vom Original (für den Methodenteil)

    | Original (Helsinki) | Hier (Graz) | Grund |
    |---|---|---|
    | 250-m-Bevölkerungsraster | Wohngebäude aus OSM + Bezirksbevölkerung (dasymetrisch) | kein freies Raster für Graz |
    | 06:00 und 17:00 | 07:00 und 17:00 (Di, 10.11.2026) | in Österreich um 6 Uhr fast alles zu |
    | Öffnungszeiten: undokumentiert | OSM `opening_hours`, Parameter für fehlende Angaben | eigener, nachvollziehbarer Schritt |
    | Pandana, alle Start-Ziel-Paare | NetworkX, Multi-Source-Dijkstra | einfacher, gleiches Ergebnis |
    | Netz-Inseln von Hand gelöscht | größte Netzkomponente (OSMnx) | reproduzierbar |
    | Winter: 4,81 / 3,89 km/h (fest im Code) | selbst berechnet, 3 Zustände vereinheitlicht | Fehler im Original (Notebook 01) |
    | Prozentwerte händisch eingetippt | berechnet | Reproduzierbarkeit |

    ## Offene Entscheidungen für die Gruppe (in `einstellungen.py`)
    - `OH_FEHLT_ALS_OFFEN`: Supermärkte ohne Öffnungszeiten – offen oder geschlossen?
    - `GEWICHTUNG`: Bevölkerung nach Fläche oder gleichmäßig verteilen?
    - Ausschlussregeln bei den Supermärkten (Notebook 02, Tabelle „entfernt“ prüfen)
    - Weg vom Gebäude zum Netzknoten (`snap_m`) addieren? Das Paper tut es nicht.
    """)
    return


if __name__ == "__main__":
    app.run()
