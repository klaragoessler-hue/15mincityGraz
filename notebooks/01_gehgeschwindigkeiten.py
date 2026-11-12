import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    # ------------------------------------------------------------------
    # BIBLIOTHEKEN UND GEMEINSAME EINSTELLUNGEN
    # ------------------------------------------------------------------
    # urllib -> Dateien aus dem Internet herunterladen
    # pandas -> Tabellen
    # einstellungen.py (im selben Ordner) -> Pfade und Dateinamen für alle Notebooks
    import marimo as mo
    import urllib.request

    import pandas as pd

    from einstellungen import DATEIEN, RAW, SPEED_URL
    return DATEIEN, RAW, SPEED_URL, mo, pd, urllib


@app.cell
def _(mo):
    mo.md(r"""
    # 01 – Gehgeschwindigkeiten

    **Eingabe:** Messdaten der Autor:innen (GitHub, wird automatisch geladen)
    **Ausgabe:** `data/processed/speeds.csv` → wird von Notebook 04 gelesen

    Die Autor:innen haben in Helsinki mit der Stoppuhr gemessen, wie lange Passant:innen
    für 20 m brauchen – bei trockenen Bedingungen und bei drei Winterzuständen
    (festgetretener Schnee, 2–8 cm Schnee, gestreutes Eis). Die Altersgruppe wurde nach
    Aussehen geschätzt. Diese **Rohdaten liegen im Original-Repo** – wir rechnen die
    Werte selbst nach, statt sie aus dem Paper abzuschreiben.

    **Regeln (wie im Paper):**
    - Nur die Gruppen **Adult** und **Elderly** („Young adult“ und „Kid“ fallen raus).
    - **Winterwert** = Mittelwert der **3 Winterzustände**: zuerst der Mittelwert pro
      Zustand, dann der Mittelwert dieser drei Werte.

    **Fund für die Kritik:** In der Winter-CSV steht ein Zustand einmal als
    „Compact snow“ und einmal als „Compact **S**now“. Python behandelt das als zwei
    verschiedene Kategorien – man bekommt **4 statt 3** Zustände. Die Tabelle unten zeigt,
    dass sich die im Originalcode fest eingetippten Winterwerte (4810 und 3890 m/h)
    genau so erklären lassen.
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
def _(RAW, SPEED_URL, pd, urllib):
    # ------------------------------------------------------------------
    # 1. MESSDATEN LADEN
    # ------------------------------------------------------------------
    # Beim ersten Lauf von GitHub herunterladen und in data/raw/ speichern,
    # danach nur noch die lokale Datei lesen.
    # Dictionary {"Dry": Tabelle, "Winter": Tabelle}
    messungen_roh = {}
    for _name in ["Dry", "Winter"]:
        _f = RAW / f"Walking_speed_measurements_EW_CH_{_name}.csv"
        if not _f.exists():
            # urlretrieve(adresse, ziel) lädt die Datei und speichert sie unter _f
            urllib.request.urlretrieve(SPEED_URL + _f.name, _f)
        # skiprows=1: In Zeile 1 steht nur ein Titel, die Spaltennamen erst in Zeile 2.
        # encoding="latin-1": Die Dateien sind nicht UTF-8 (Sonderzeichen in den Notizen).
        messungen_roh[_name] = pd.read_csv(_f, sep=";", skiprows=1, encoding="latin-1")

    # Ein Blick in die Daten: jede Zeile ist eine gemessene Person
    # .head() zeigt die ersten 5 Zeilen
    messungen_roh["Winter"].head()
    return (messungen_roh,)


@app.cell
def _(messungen_roh):
    # ------------------------------------------------------------------
    # 2. FILTERN UND BEREINIGEN
    # ------------------------------------------------------------------
    # Nur Erwachsene und Ältere, wie im Paper.
    # df[bedingung] behält nur die Zeilen, in denen die Bedingung True ist.
    # .isin([...]) ist True, wenn der Wert in der Liste vorkommt.
    messung_trocken = messungen_roh["Dry"][messungen_roh["Dry"]["Age"].isin(["Adult", "Elderly"])]
    messung_winter = messungen_roh["Winter"][
        messungen_roh["Winter"]["Age"].isin(["Adult", "Elderly"])
    ].copy()

    # Straßenzustand vereinheitlichen: Leerzeichen weg, alles klein geschrieben.
    # Dadurch werden "Compact Snow" und "Compact snow" zu EINER Kategorie.
    messung_winter["Zustand"] = messung_winter["Condition"].str.strip().str.lower()

    # Kontrolle: Wie viele Messungen pro Gruppe und Zustand? (vgl. Tabelle 1 im Paper)
    # groupby = in Gruppen aufteilen, size() = Zeilen je Gruppe zählen,
    # unstack() = die zweite Gruppierung (Zustand) als Spalten darstellen
    messung_winter.groupby(["Age", "Zustand"]).size().unstack()
    return messung_trocken, messung_winter


@app.cell
def _(messung_trocken, messung_winter, messungen_roh, pd):
    # ------------------------------------------------------------------
    # 3. DIE VIER GESCHWINDIGKEITEN BERECHNEN
    # ------------------------------------------------------------------
    _v = "Speed (km/h)"
    # groupby("Age")[spalte].mean() = Mittelwert der Geschwindigkeit je Altersgruppe
    # Ergebnis ist eine Reihe mit den Einträgen "Adult" und "Elderly"
    _trocken = messung_trocken.groupby("Age")[_v].mean()
    _pro_zustand = messung_winter.groupby(["Age", "Zustand"])[_v].mean()   # 3 Werte je Gruppe
    _winter = _pro_zustand.groupby("Age").mean()                         # Mittel dieser 3

    # float(...) macht aus dem pandas-Wert eine normale Zahl, round(..., 2) rundet
    SPEEDS_KMH = {
        "erw_trocken": round(float(_trocken["Adult"]), 2),
        "alt_trocken": round(float(_trocken["Elderly"]), 2),
        "erw_winter": round(float(_winter["Adult"]), 2),
        "alt_winter": round(float(_winter["Elderly"]), 2),
    }

    # --- Nachrechnen, wie die Werte im ORIGINALCODE entstanden sein könnten ------
    # OHNE Vereinheitlichung (4 Kategorien). Erwachsene: Mittel der 4 Mittelwerte,
    # Ältere: Mittel der 4 MEDIANE. Genau das ergibt 4,81 bzw. 3,89 km/h.
    _roh = messungen_roh["Winter"][messungen_roh["Winter"]["Age"].isin(["Adult", "Elderly"])]
    # _roh.Age ist dasselbe wie _roh["Age"] (Kurzschreibweise für Spalten)
    _code_erw = _roh[_roh.Age == "Adult"].groupby("Condition")[_v].mean().mean()
    _code_alt = _roh[_roh.Age == "Elderly"].groupby("Condition")[_v].median().mean()

    vergleich_speeds = pd.DataFrame({
        "Gruppe": ["Erwachsene trocken", "Ältere trocken", "Erwachsene Winter", "Ältere Winter"],
        "unser Wert (km/h)": list(SPEEDS_KMH.values()),
        "Paper (Tabelle 1 / Text)": ["5.15", "4.26", "Mittel der 3 Zustände", "Mittel der 3 Zustände"],
        "Originalcode (km/h)": [5.15, 4.26, 4.81, 3.89],
        "Code nachgerechnet (4 Kategorien)": ["", "", f"{_code_erw:.3f}", f"{_code_alt:.3f}"],
        "Anzahl Messungen": [
            # (Spalte == Wert) ergibt True/False; .sum() zählt die True = Anzahl Messungen
            int((messung_trocken.Age == "Adult").sum()),
            int((messung_trocken.Age == "Elderly").sum()),
            int((messung_winter.Age == "Adult").sum()),
            int((messung_winter.Age == "Elderly").sum()),
        ],
    })
    vergleich_speeds
    return SPEEDS_KMH, vergleich_speeds


@app.cell
def _(DATEIEN, SPEEDS_KMH, pd):
    # ------------------------------------------------------------------
    # 4. SPEICHERN -> Eingabe für Notebook 04
    # ------------------------------------------------------------------
    # list(dictionary) = Liste der Schlüssel, .values() = die Werte dazu
    speeds_tabelle = pd.DataFrame({"schluessel": list(SPEEDS_KMH),
                                   "kmh": list(SPEEDS_KMH.values())})
    speeds_tabelle.to_csv(DATEIEN["speeds"], sep=";", index=False)
    print("Gespeichert:", DATEIEN["speeds"])
    speeds_tabelle
    return (speeds_tabelle,)


if __name__ == "__main__":
    app.run()
