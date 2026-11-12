import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # ------------------------------------------------------------------
    # BIBLIOTHEKEN UND GEMEINSAME EINSTELLUNGEN
    # ------------------------------------------------------------------
    # pandas    -> Tabellen
    # osmnx     -> lädt Daten aus OpenStreetMap
    # humanized_opening_hours -> liest das OSM-Tag "opening_hours" und sagt,
    #                            ob ein Geschäft zu einem Zeitpunkt offen ist
    import marimo as mo
    import warnings

    import pandas as pd
    import osmnx as ox

    # Das Öffnungszeiten-Paket ist älter und gibt beim Import harmlose
    # "SyntaxWarning"s aus -> ausblenden, damit die Ausgabe sauber bleibt.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        import humanized_opening_hours as hoh

    from einstellungen import (CRS, DATEIEN, OH_FEHLT_ALS_OFFEN, ZEITPUNKTE,
                               osm_laden, untersuchungsgebiet)
    return (CRS, DATEIEN, OH_FEHLT_ALS_OFFEN, ZEITPUNKTE, hoh, mo, osm_laden, ox, pd,
            untersuchungsgebiet)


@app.cell
def _(mo):
    mo.md(r"""
    # 02 – Supermärkte und Öffnungszeiten

    **Eingabe:** OpenStreetMap (wird automatisch geladen)
    **Ausgabe:** `data/processed/supermaerkte.gpkg` → wird von Notebook 04 gelesen

    **Wie im Paper:** OSM-Tags `shop=supermarket` und `shop=convenience`, **ohne Kioske**,
    groß und klein werden nicht unterschieden. Gebiet: Graz **+ 2 km Puffer**, damit
    Supermärkte knapp hinter der Stadtgrenze mitzählen.

    **Zusätzliche Bereinigung** (eigene Entscheidung, im Bericht nennen):
    Drogerien (dm, BIPA, Müller) und Imbisse, die in OSM fälschlich als Supermarkt bzw.
    Nahversorger eingetragen sind, fliegen raus. Die entfernten Einträge werden unten
    angezeigt, damit ihr sie kontrollieren könnt.

    **Öffnungszeiten** kommen aus dem OSM-Tag `opening_hours`, z. B.
    `Mo-Fr 07:00-19:15; Sa 07:15-18:00`. Für jeden Zeitpunkt aus `einstellungen.py`
    bekommt jedes Geschäft eine Spalte `offen_17`, `offen_07` (True/False).
    **Dieser Schritt fehlt im Originalcode komplett** – dort werden fertige Dateien
    „5pm“ und „6am“ eingelesen, ohne dass dokumentiert ist, wie sie entstanden sind.
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
def _(CRS, osm_laden, ox, untersuchungsgebiet):
    # ------------------------------------------------------------------
    # 1. SUPERMÄRKTE LADEN
    # ------------------------------------------------------------------
    # Die Funktion gibt 3 Werte zurück; wir brauchen hier nur das Gebiet mit Puffer.
    # Die anderen beiden bekommen einen _ -> gelten nur in dieser Zelle.
    _graz, _graz_wgs, gebiet_wgs = untersuchungsgebiet()

    # features_from_polygon holt alle OSM-Objekte mit diesen Tags im Gebiet.
    # Ergebnis: Punkte (Geschäft als Punkt eingetragen) UND Polygone (als Gebäude).
    _roh = osm_laden(
        ox.features_from_polygon, gebiet_wgs, tags={"shop": ["supermarket", "convenience"]}
    )
    # reset_index(): OSMnx liefert (element, id) als Index, z. B. ("node", 12345).
    #   Danach sind das normale Spalten "element" und "id".
    # to_crs(CRS): von Längen-/Breitengrad in Meter-Koordinaten umrechnen
    shops_roh = _roh.reset_index().to_crs(CRS)

    # Polygone -> ein Punkt im Inneren. representative_point() liegt garantiert IN der
    # Fläche (anders als der Schwerpunkt "centroid" bei z. B. L-förmigen Gebäuden).
    shops_roh["geometry"] = shops_roh.geometry.representative_point()
    print(f"Geladen: {len(shops_roh)} Geschäfte")
    return (shops_roh,)


@app.cell
def _(pd, shops_roh):
    # ------------------------------------------------------------------
    # 2. BEREINIGEN
    # ------------------------------------------------------------------
    def _spalte(df, name):
        """Gibt die Spalte zurück oder eine leere, falls OSM sie nicht liefert."""
        return df[name] if name in df.columns else pd.Series(pd.NA, index=df.index)

    # Name und Marke zu einem kleingeschriebenen Text zusammenfügen, damit die Suche
    # unten Groß-/Kleinschreibung ignoriert. fillna("") ersetzt fehlende Werte durch "".
    _name = _spalte(shops_roh, "name").fillna("").astype(str)
    _brand = _spalte(shops_roh, "brand").fillna("").astype(str)
    _text = (_name + " " + _brand).str.lower()

    # Ausschlussregeln (bei Bedarf erweitern!)
    # str.contains(muster) = enthält der Text das Muster? -> True/False je Geschäft
    # \b = Wortgrenze: findet "dm" als eigenes Wort, aber nicht in "Admiral"
    # (?:a|b|c) = a oder b oder c
    _drogerie = _text.str.contains(r"\b(?:dm|bipa|müller)\b", regex=True)
    _kiosk = _text.str.contains(r"kiosk|trafik", regex=True)
    # Imbisse haben oft zusätzlich ein amenity- oder cuisine-Tag (z. B. fast_food, kebab)
    _imbiss = _spalte(shops_roh, "amenity").notna() | _spalte(shops_roh, "cuisine").notna()
    # | = ODER (je Zeile): raus, wenn mindestens eine Regel zutrifft
    _raus = _drogerie | _kiosk | _imbiss

    shops_entfernt = shops_roh.loc[_raus, ["name", "brand", "shop"]].copy()
    # ~ = NICHT: alle Zeilen, die NICHT rausfliegen
    shops_bereinigt = shops_roh.loc[~_raus].copy()
    print(f"Entfernt: {len(shops_entfernt)}, verbleibend: {len(shops_bereinigt)} Geschäfte")

    # Kontrolle: Welche Einträge wurden entfernt? Passt das?
    shops_entfernt
    return (shops_bereinigt,)


@app.cell
def _(OH_FEHLT_ALS_OFFEN, ZEITPUNKTE, hoh, pd, shops_bereinigt):
    # ------------------------------------------------------------------
    # 3. ÖFFNUNGSZEITEN AUSWERTEN
    # ------------------------------------------------------------------
    def ist_offen(oh_text, zeitpunkt):
        """True/False: offen zum Zeitpunkt? None: keine oder unlesbare Öffnungszeiten."""
        if not isinstance(oh_text, str) or not oh_text.strip():
            return None
        # try/except: Falls das Lesen fehlschlägt (Tippfehler im OSM-Tag), stürzt das
        # Notebook nicht ab, sondern es geht im except-Teil weiter.
        try:
            return bool(hoh.OHParser(oh_text).is_open(zeitpunkt))
        except Exception:      # unlesbares Format in OSM
            return None

    shops = shops_bereinigt.copy()
    _oh = shops["opening_hours"] if "opening_hours" in shops else pd.Series(None, index=shops.index)
    _stat = []
    for _k, _zeit in ZEITPUNKTE.items():
        # .apply(funktion) ruft die Funktion für JEDES Geschäft einzeln auf.
        # lambda t, z=_zeit: ist_offen(t, z) ist eine Mini-Funktion ohne Namen:
        #   t = Öffnungszeiten-Text des jeweiligen Geschäfts,
        #   z=_zeit legt den Zeitpunkt fest ("z=" sorgt dafür, dass jede Runde der
        #   Schleife ihren eigenen Zeitpunkt verwendet).
        # Ergebnis: eine Spalte mit True / False / None je Geschäft.
        _werte = _oh.apply(lambda t, z=_zeit: ist_offen(t, z))
        _unbekannt = _werte.isna()
        # fehlende Angaben je nach Einstellung als offen oder geschlossen werten
        # where(bedingung, ersatz): behält den Wert, wo die Bedingung True ist,
        # sonst wird er durch den Ersatz ersetzt -> unbekannte werden False oder True.
        shops[f"offen_{_k}"] = _werte.where(~_unbekannt, OH_FEHLT_ALS_OFFEN).astype(bool)
        _stat.append({
            "Zeitpunkt": _zeit.strftime("%a %d.%m. %H:%M"),
            # (== True).sum() zählt die True-Werte. "noqa" sagt dem Prüfprogramm, dass
            # "== True" hier Absicht ist (None soll NICHT mitgezählt werden).
            "offen": int((_werte == True).sum()),          # noqa: E712
            "geschlossen": int((_werte == False).sum()),   # noqa: E712
            "unbekannt": int(_unbekannt.sum()),
            "als Ziel verwendet": int(shops[f"offen_{_k}"].sum()),
        })
    oeffnungs_statistik = pd.DataFrame(_stat)
    oeffnungs_statistik
    return ist_offen, oeffnungs_statistik, shops


@app.cell
def _(shops):
    # Kontrolle: Supermärkte OHNE Öffnungszeiten (gelten je nach Einstellung als zu/offen).
    # Stichproben mit Google Maps / Website der Kette vergleichen!
    # .loc[zeilen, spalten]: Zeilen ohne Öffnungszeiten (.isna() = fehlt), nur 3 Spalten
    shops.loc[shops["opening_hours"].isna(), ["name", "brand", "shop"]]
    return


@app.cell
def _(DATEIEN, ZEITPUNKTE, shops):
    # ------------------------------------------------------------------
    # 4. SPEICHERN -> Eingabe für Notebook 04
    # ------------------------------------------------------------------
    # Nur die benötigten Spalten (OSM liefert sonst hunderte Tag-Spalten, teils mit
    # Listen, die sich nicht als GeoPackage speichern lassen).
    # "List Comprehension": nimm nur die Spalten aus der Liste, die es wirklich gibt
    _spalten = [c for c in ["id", "name", "brand", "shop", "opening_hours"] if c in shops]
    _spalten += [f"offen_{k}" for k in ZEITPUNKTE] + ["geometry"]
    # to_file(..., driver="GPKG") speichert als GeoPackage (Geodatenformat, z. B. für QGIS)
    shops[_spalten].to_file(DATEIEN["supermaerkte"], driver="GPKG")
    print("Gespeichert:", DATEIEN["supermaerkte"])
    return


if __name__ == "__main__":
    app.run()
