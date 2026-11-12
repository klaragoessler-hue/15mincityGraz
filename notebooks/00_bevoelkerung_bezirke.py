import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # ------------------------------------------------------------------
    # BIBLIOTHEKEN
    # ------------------------------------------------------------------
    # re       -> "reguläre Ausdrücke": Muster in Text finden, z. B. eine Tabellenzeile
    #             "60 - 69 2.293 2.415 ..." im Text eines PDFs
    # urllib   -> Dateien aus dem Internet herunterladen
    # pypdf    -> Text aus PDF-Dateien auslesen
    # pandas   -> Tabellen
    import marimo as mo
    import re
    import urllib.request
    from pathlib import Path

    import pandas as pd
    from pypdf import PdfReader
    return Path, PdfReader, mo, pd, re, urllib


@app.cell
def _(mo):
    mo.md(r"""
    # Bevölkerung pro Grazer Bezirk (Einwohner und Alter)

    Dieses Notebook erzeugt die Datei **`data/raw/bezirke_bevoelkerung.csv`**, die das
    Routing-Notebook braucht, um die Bevölkerung auf die Wohngebäude zu verteilen.

    **Warum ein eigenes Notebook?** Die Stadt Graz veröffentlicht die Zahlen nur als
    **PDF**. Damit nachvollziehbar ist, wie aus den PDFs unsere Tabelle wird, steht jeder
    Schritt hier im Code – vom Download bis zur fertigen CSV. (Genau das fehlt im Original:
    Dort liegen Ergebnisse, aber nicht der Weg dorthin.)

    **Quellen** (Stadt Graz, Präsidialamt, Referat für Statistik, Stand 01.01.2026)

    1. *Grazer Bevölkerung pro Bezirk* – ein PDF mit der **anwesenden Bevölkerung**
       (Haupt- + Nebenwohnsitze + Obdachlose) aller 17 Bezirke
    2. *Bezirksauswertungen* – **ein PDF pro Bezirk** (`Bezirk_final_01.pdf` bis `_17.pdf`)
       mit Hauptwohnsitzen und **Altersgruppen in 10-Jahres-Schritten**

    **Ablauf**

    1. PDFs herunterladen (nur beim ersten Mal)
    2. Übersichts-PDF auslesen: anwesende Bevölkerung pro Bezirk
    3. Bezirks-PDFs auslesen: Hauptwohnsitze und Altersgruppen
    4. Anteil 65+ schätzen
    5. Kontrollen
    6. CSV schreiben
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
def _(Path, mo):
    # ------------------------------------------------------------------
    # 1. EINSTELLUNGEN
    # ------------------------------------------------------------------
    _nb_dir = mo.notebook_dir() or Path.cwd() / "notebooks"
    ROOT = Path(_nb_dir).resolve().parent
    PDF_ORDNER = ROOT / "data" / "raw" / "stadt_graz_pdfs"   # nicht im Git (data/raw)
    PDF_ORDNER.mkdir(parents=True, exist_ok=True)
    CSV_ZIEL = ROOT / "data" / "raw" / "bezirke_bevoelkerung.csv"

    # Übersicht: anwesende Bevölkerung pro Bezirk
    URL_UEBERSICHT = ("https://www.graz.at/cms/dokumente/10022937_7771507/8024c4a9/"
                      "Bev%C3%B6lkerung%20nach%20Bezirken_01.021.2026.pdf")
    # Bezirksauswertungen: {nr} = 01 ... 17
    URL_BEZIRK = ("https://www1.graz.at/statistik/Bev%C3%B6lkerung/Bezirksauswertungen/"
                  "Bezirk_final_{nr}.pdf")

    # Bezirksnamen GENAU wie in OpenStreetMap (sonst klappt der Join im Routing nicht).
    # Die PDFs schreiben z. B. "St.Leonhard", OSM "Sankt Leonhard".
    # Die Nummer ist die offizielle Bezirksnummer (I. Innere Stadt ... XVII. Puntigam).
    OSM_NAMEN = {
        1: "Innere Stadt", 2: "Sankt Leonhard", 3: "Geidorf", 4: "Lend", 5: "Gries",
        6: "Jakomini", 7: "Liebenau", 8: "Sankt Peter", 9: "Waltendorf", 10: "Ries",
        11: "Mariatrost", 12: "Andritz", 13: "Gösting", 14: "Eggenberg",
        15: "Wetzelsdorf", 16: "Straßgang", 17: "Puntigam",
    }

    # Altersgruppen, wie sie in den Bezirks-PDFs stehen
    ALTERSGRUPPEN = ["00 - 09", "10 - 19", "20 - 29", "30 - 39", "40 - 49",
                     "50 - 59", "60 - 69", "70 - 79", "80 - 89", "90 - 99", "100 +"]
    return ALTERSGRUPPEN, CSV_ZIEL, OSM_NAMEN, PDF_ORDNER, URL_BEZIRK, URL_UEBERSICHT


@app.cell
def _(OSM_NAMEN, PDF_ORDNER, URL_BEZIRK, URL_UEBERSICHT, urllib):
    # ------------------------------------------------------------------
    # 2. PDFs HERUNTERLADEN (nur wenn sie noch nicht lokal liegen)
    # ------------------------------------------------------------------
    def herunterladen(url, datei):
        """Lädt eine Datei, falls sie noch nicht existiert. Gibt den Pfad zurück."""
        if not datei.exists():
            # Manche Server lehnen Anfragen ohne Browser-Kennung ab -> User-Agent setzen
            _anfrage = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(_anfrage, timeout=60) as _antwort:
                datei.write_bytes(_antwort.read())
        # Kontrolle: Ist es wirklich ein PDF? (Kaputte Links liefern oft eine Webseite)
    # Jede PDF-Datei beginnt mit den 4 Zeichen "%PDF" (b"..." = Bytes statt Text).
    # assert prüft eine Bedingung. Ist sie falsch, bricht das Notebook ab und zeigt
    # den Text hinter dem Komma. So fallen Fehler sofort auf, statt später.
        assert datei.read_bytes()[:4] == b"%PDF", f"{datei.name} ist kein PDF – Link prüfen!"
        return datei

    pdf_uebersicht = herunterladen(URL_UEBERSICHT, PDF_ORDNER / "bevoelkerung_nach_bezirken_2026.pdf")
    # Dictionary {Bezirksnummer: Pfad zum PDF} für alle 17 Bezirke.
    # Schreibweise {schlüssel: wert for x in ...} = "Dictionary Comprehension",
    # eine kurze Form für eine Schleife, die ein Dictionary füllt.
    # f"{_nr:02d}" schreibt die Zahl zweistellig mit führender Null: 5 -> "05".
    pdf_bezirke = {
        _nr: herunterladen(URL_BEZIRK.format(nr=f"{_nr:02d}"),
                           PDF_ORDNER / f"Bezirk_final_{_nr:02d}.pdf")
        for _nr in OSM_NAMEN
    }
    print(f"{1 + len(pdf_bezirke)} PDFs bereit in {PDF_ORDNER}")
    return pdf_bezirke, pdf_uebersicht


@app.cell
def _(PdfReader):
    # ------------------------------------------------------------------
    # HILFSFUNKTIONEN
    # ------------------------------------------------------------------
    def pdf_text(datei):
        """Gesamter Text eines PDFs als ein String (alle Seiten hintereinander)."""
        # PdfReader(datei).pages = Liste der Seiten, extract_text() = Text einer Seite.
        # "\n".join(...) klebt die Texte aller Seiten mit Zeilenumbruch aneinander.
        return "\n".join(seite.extract_text() for seite in PdfReader(datei).pages)

    def zahl(text):
        """'30.780' -> 30780  (der Punkt ist im Deutschen das Tausender-Trennzeichen)"""
        return int(text.replace(".", ""))
    return pdf_text, zahl


@app.cell
def _(OSM_NAMEN, pd, pdf_text, pdf_uebersicht, re, zahl):
    # ------------------------------------------------------------------
    # 3. ÜBERSICHTS-PDF: anwesende Bevölkerung pro Bezirk
    # ------------------------------------------------------------------
    # Eine Zeile im PDF sieht so aus:
    #   "Lend 22.341 59% 6.104 16% 9.330 25% 37.775"
    #    Name  Österr.  %  EU      %  Nicht-EU %  Gesamt
    # Das Muster unten findet genau solche Zeilen. Wir brauchen den Namen und "Gesamt".
    #
    # So liest man das Muster ("regulärer Ausdruck"):
    #   ^                   Zeilenanfang
    #   (?P<name>[^\d\n]+?) Gruppe "name": beliebige Zeichen, aber keine Ziffern
    #   [\d.]+              eine Zahl mit Tausenderpunkt, z. B. 22.341
    #   \d+%                eine Prozentzahl, z. B. 59%
    #   (?P<gesamt>[\d.]+)  Gruppe "gesamt": die letzte Zahl der Zeile
    #   \s*$                eventuell Leerzeichen, dann Zeilenende
    # re.MULTILINE: ^ und $ gelten für JEDE Zeile, nicht nur für den ganzen Text.
    # r"..." = "raw string": Backslashes werden nicht als Sonderzeichen gelesen.
    _muster = re.compile(
        r"^(?P<name>[^\d\n]+?) [\d.]+ \d+% [\d.]+ \d+% [\d.]+ \d+% (?P<gesamt>[\d.]+)\s*$",
        re.MULTILINE,
    )
    # finditer findet ALLE passenden Zeilen. t["name"] liest später die Gruppe "name".
    _treffer = list(_muster.finditer(pdf_text(pdf_uebersicht)))
    assert len(_treffer) == 17, f"{len(_treffer)} statt 17 Bezirke gefunden"

    # Die Bezirke stehen im PDF in der offiziellen Reihenfolge 1 ... 17
    uebersicht = pd.DataFrame({
        "bezirk_nr": range(1, 18),
        "name_pdf": [t["name"].strip() for t in _treffer],
        "einwohner": [zahl(t["gesamt"]) for t in _treffer],
    })
    # .map(dictionary) ersetzt jeden Wert durch den passenden Eintrag: 2 -> "Sankt Leonhard"
    uebersicht["bezirk"] = uebersicht["bezirk_nr"].map(OSM_NAMEN)
    uebersicht
    return (uebersicht,)


@app.cell
def _(ALTERSGRUPPEN, pd, pdf_bezirke, pdf_text, re, zahl):
    # ------------------------------------------------------------------
    # 4. BEZIRKS-PDFs: Hauptwohnsitze und Altersgruppen
    # ------------------------------------------------------------------
    _zeilen = []
    for _nr, _datei in pdf_bezirke.items():
        _text = pdf_text(_datei)

        # a) Kopfzeile: "... im 5. Bezirk: Gries, Stand 01.01.2026"
        #    -> prüfen, dass wir das richtige PDF und den richtigen Stichtag haben
        #    Gruppen in (...): _kopf[1] = Nummer, _kopf[2] = Name, _kopf[3] = Datum
        _kopf = re.search(r"im (\d+)\. Bezirk: ([^,\n]+),\s+Stand (\S+)", _text)
        assert int(_kopf[1]) == _nr, f"PDF {_datei.name} gehört zu Bezirk {_kopf[1]}"

        # b) Tabelle "Anwesende Bevölkerung nach Wohnsitz und Geschlecht", Zeile "Gesamt":
        #    12 Zahlen = (Männer, Frauen, Gesamt) für HWS, NWS, Obdachlos, Gesamt
        #    -> Spalte 3 = Hauptwohnsitze gesamt, Spalte 12 = anwesend gesamt
        #    Muster: "Gesamt", dann 11 Zahlen mit Leerzeichen ((?:...){11}), dann die 12.
        #    [1] = Inhalt der Gruppe, .split() zerlegt an Leerzeichen in eine Liste.
        #    Python zählt ab 0: [2] = dritte Zahl, [11] = zwölfte Zahl.
        _gesamt = re.search(r"^Gesamt ((?:[\d.]+ ){11}[\d.]+)\s*$", _text, re.MULTILINE)[1].split()
        _hws, _anwesend = zahl(_gesamt[2]), zahl(_gesamt[11])

        # c) Tabelle "Hauptwohnsitzentwicklung nach Altersgruppen" (Jänner 2020 ... 2026):
        #    "60 - 69 2.293 2.415 2.501 2.521 2.643 2.696 2.765"
        #    -> 7 Zahlen, die LETZTE ist Jänner 2026
        #    Wir suchen nur im Text AB der Überschrift dieser Tabelle (text[start:]),
        #    damit Zeilen anderer Tabellen (z. B. eine andere "Gesamt"-Zeile) nicht stören.
        _abschnitt = _text[_text.index("Altersgruppen in 10-er"):]
        _alter = {}
        for _gruppe in ALTERSGRUPPEN:
            # re.escape: "100 +" enthält "+", das im Muster sonst eine Sonderbedeutung hätte
            # [-1] = letztes Element der Liste = Jänner 2026
            _z = re.search(r"^" + re.escape(_gruppe) + r"((?: [\d.]+){7})\s*$",
                           _abschnitt, re.MULTILINE)
            _alter[_gruppe] = zahl(_z[1].split()[-1])

        # Eine Zeile der Ergebnistabelle als Dictionary. **_alter fügt alle
        # Einträge des Dictionaries _alter ("00 - 09": ..., "10 - 19": ...) hier ein.
        _zeilen.append({"bezirk_nr": _nr, "name_pdf": _kopf[2].strip(), "stand": _kopf[3],
                        "einwohner_anwesend": _anwesend, "einwohner_hws": _hws, **_alter})

    # Liste von Dictionaries -> Tabelle (jedes Dictionary wird eine Zeile)
    bezirke_alter = pd.DataFrame(_zeilen)
    bezirke_alter
    return (bezirke_alter,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Anteil der über 65-Jährigen (Schätzung)

    Die Stadt Graz weist das Alter nur in **10-Jahres-Gruppen** aus. Eine Gruppe „65+“
    gibt es nicht. Wir schätzen sie so:

    $$\text{65+} \approx \text{70+} + \tfrac{1}{2} \cdot (\text{60–69})$$

    **Annahme:** Die 60- bis 69-Jährigen verteilen sich gleichmäßig auf die zehn Jahrgänge,
    also ist etwa die Hälfte 65 oder älter. In Wirklichkeit gibt es in dieser Gruppe meist
    etwas mehr Jüngere (60–64) als Ältere, die Schätzung liegt also eher leicht zu hoch.

    Bezugsgröße sind die **Hauptwohnsitze**, weil die Altersdaten nur für sie vorliegen.
    """)
    return


@app.cell
def _(ALTERSGRUPPEN, OSM_NAMEN, bezirke_alter, uebersicht):
    # ------------------------------------------------------------------
    # 5. ANTEIL 65+ BERECHNEN und KONTROLLEN
    # ------------------------------------------------------------------
    tabelle = bezirke_alter.copy()
    tabelle["bezirk"] = tabelle["bezirk_nr"].map(OSM_NAMEN)
    tabelle["alter_60_69"] = tabelle["60 - 69"]
    # sum(axis=1) = Summe ÜBER DIE SPALTEN, also pro Zeile (pro Bezirk).
    # (axis=0 wäre die Summe über alle Zeilen, also pro Spalte.)
    tabelle["alter_70plus"] = tabelle[["70 - 79", "80 - 89", "90 - 99", "100 +"]].sum(axis=1)
    tabelle["anteil_65plus"] = (
        (tabelle["alter_70plus"] + tabelle["alter_60_69"] / 2) / tabelle["einwohner_hws"]
    )

    # Kontrolle 1: Alle Altersgruppen zusammen = Hauptwohnsitze?
    _summe_alter = tabelle[ALTERSGRUPPEN].sum(axis=1)
    # (a == b) vergleicht Zeile für Zeile -> True/False je Bezirk; .all() = alle True?
    assert (_summe_alter == tabelle["einwohner_hws"]).all(), "Altersgruppen ≠ Hauptwohnsitze"

    # Kontrolle 2: Anwesende Bevölkerung aus Bezirks-PDF = Wert aus Übersichts-PDF?
    # merge = zwei Tabellen über eine gemeinsame Spalte verbinden (wie SVERWEIS in Excel)
    _vergleich = tabelle.merge(uebersicht[["bezirk_nr", "einwohner"]], on="bezirk_nr")
    assert (_vergleich["einwohner_anwesend"] == _vergleich["einwohner"]).all(), \
        "Bezirks-PDFs und Übersichts-PDF widersprechen sich"

    # Kontrolle 3: Alle PDFs haben denselben Stichtag
    # nunique() = Anzahl verschiedener Werte in der Spalte
    assert tabelle["stand"].nunique() == 1, "Unterschiedliche Stichtage!"

    _hws = tabelle["einwohner_hws"].sum()
    # Anzahl 65+ = Anteil × Hauptwohnsitze, pro Bezirk, dann über alle Bezirke summiert
    _65 = (tabelle["anteil_65plus"] * tabelle["einwohner_hws"]).sum()
    print("Alle Kontrollen bestanden. Stichtag:", tabelle["stand"].iloc[0])
    print(f"Graz gesamt: {tabelle['einwohner_anwesend'].sum():,} anwesend,"
          f" {_hws:,} Hauptwohnsitze, 65+ geschätzt {_65:,.0f} ({_65 / _hws:.1%})")
    tabelle[["bezirk_nr", "bezirk", "einwohner_anwesend", "einwohner_hws",
             "alter_60_69", "alter_70plus", "anteil_65plus"]]
    return (tabelle,)


@app.cell
def _(CSV_ZIEL, pd, tabelle):
    # ------------------------------------------------------------------
    # 6. CSV SCHREIBEN
    # ------------------------------------------------------------------
    # Spalten und Format genau so, wie das Routing-Notebook sie erwartet.
    csv_neu = pd.DataFrame({
        "bezirk_nr": tabelle["bezirk_nr"],
        "bezirk": tabelle["bezirk"],
        "einwohner": tabelle["einwohner_anwesend"],
        "einwohner_hws": tabelle["einwohner_hws"],
        "alter_60_69": tabelle["alter_60_69"],
        "alter_70plus": tabelle["alter_70plus"],
        "anteil_65plus": tabelle["anteil_65plus"].round(4),
    })

    # Falls die Datei schon existiert: vergleichen. Nur schreiben, wenn sich etwas ändert.
    # (Ist die CSV gerade in Excel geöffnet, sperrt Windows sie -> dann klappt Schreiben nicht.)
    # .equals() = sind beide Tabellen in Inhalt, Spalten und Datentypen gleich?
    # "and" prüft den zweiten Teil nur, wenn die Datei existiert (sonst Lesefehler).
    _gleich = CSV_ZIEL.exists() and pd.read_csv(CSV_ZIEL, sep=";").equals(csv_neu)
    if _gleich:
        print("Bestehende CSV ist identisch – nichts zu tun:", CSV_ZIEL)
    else:
        if CSV_ZIEL.exists():
            print("ACHTUNG: Die neuen Werte weichen von der bestehenden CSV ab -> wird ersetzt.")
        # sep=";"  -> Semikolon als Trenner (öffnet in deutschem Excel korrekt)
        # index=False -> die Zeilennummern von pandas nicht mitschreiben
        # float_format -> Kommazahlen immer mit 4 Nachkommastellen
        csv_neu.to_csv(CSV_ZIEL, sep=";", index=False, lineterminator="\n",
                       float_format="%.4f")
        print("Geschrieben:", CSV_ZIEL)
    csv_neu
    return (csv_neu,)


if __name__ == "__main__":
    app.run()
