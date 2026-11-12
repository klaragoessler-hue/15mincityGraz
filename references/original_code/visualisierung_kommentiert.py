# ============================================================================
# KOMMENTIERTE KOPIE des Originalskripts
#   WalkingAccessibilityRoutingVISUALIZATION.py
# aus https://github.com/DigitalGeographyLab/15_minute_city_for_all_article
# (Willberg, Fink & Toivonen 2023, Lizenz: Apache 2.0)
#
# Der ORIGINALCODE IST UNVERÄNDERT. Ergänzt wurden nur Kommentarzeilen.
# Die unveränderte Originaldatei liegt in ./original/
#
# Legende: ERKLÄRUNG / PROBLEM / GRAZ (siehe Routing-Skript)
#
# Ablauf in Kurzform:
#   1. Ergebnisse des Routing-Skripts einlesen (Gehzeiten pro Rasterzelle)
#   2. Kumulierte Bevölkerungsanteile berechnen (Abb. 4)
#   3. 2x4-Grafik der 8 Modelle zeichnen (Abb. 4)
#   4. Prozentwerte für 10/15/20 min ausgeben
#   5. Balkendiagramm (fest eingetippte Werte)
#   6. Verteilung der Gehgeschwindigkeiten (Abb. 3, Ridge Plot)
#   7. Balken: erreichte Supermärkte je Geschwindigkeit (Abb. 6)
#
# Die Karten (Abb. 5) wurden offenbar NICHT mit Python erstellt
# (vermutlich in QGIS aus den GeoPackages).
# ============================================================================

import os
import pandas as pd
import geopandas as gpd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

#### MAIN #####

# PROBLEM:   Leerer Pfad -> FileNotFoundError.
# GRAZ:      Relative Pfade im Repo (pathlib).
os.chdir("") #ADD PATH

sns.set()
sns.set_style("darkgrid", {'axes.grid' : True})

# ERKLÄRUNG: Liest die Ergebnisse des Routing-Skripts: Rasterpolygone mit
#             Gehzeiten (Spalten Adult_speed_dry usw.) für 17 und 6 Uhr.
# PROBLEM:   Die 'rttk2020_grocery_...'-Dateien schreibt nur die AUSKOMMENTIERTE
#             Variante des Routing-Skripts. Mit dem Code im Repo entstehen sie
#             also gar nicht. Die metropAccess-Dateien werden hier geladen,
#             aber nicht weiter verwendet.
# GRAZ:      results = gpd.read_file('data/processed/results.gpkg')
#Read population and POIs data
population_Grid_PkSeutu_17 = gpd.read_file("Data\\rttk2020_grocery_22_17.gpkg")
population_Grid_PkSeutu_06 = gpd.read_file("Data\\rttk2020_grocery_22_06.gpkg")

metropAccessGrid_PkSeutu_17 = gpd.read_file("Data\\metropAccessGrid_grocery_22_17.gpkg")
metropAccessGrid_PkSeutu_06 = gpd.read_file("Data\\metropAccessGrid_grocery_22_06.gpkg")

# ERKLÄRUNG: Aufbereitete Gehgeschwindigkeiten für den Ridge Plot (Abb. 3).
# PROBLEM:   WalkingSpeedsRidgePlot.csv ist NICHT im Repo, und wie sie aus den
#             beiden Mess-CSVs entstanden ist, steht nirgends.
# GRAZ:      Aus den beiden CSVs selbst bauen: zusammenfügen, eine Spalte
#             'age & road condition' bilden (z. B. 'Adult - Dry').
walkingSpeedData = pd.read_csv("Data\\WalkingSpeedsRidgePlot.csv", sep=";")

# ERKLÄRUNG: Anzahl erreichter Supermärkte in den Einzugsgebieten (Abb. 6).
# PROBLEM:   Nicht im Repo, Entstehung nicht dokumentiert (vermutlich in QGIS
#             gezählt: Punkte im Polygon).
# GRAZ:      Optional: shops.within(einzugsgebiet).sum() in geopandas.
serviceAreaGroceryCounts =pd.read_csv("ServiceAreaGroceryCounts.csv", sep=";")

# ERKLÄRUNG: Summiert die Altersspalten des finnischen Rasters zu 'he_+65'
#             (Einwohner ab 65). he_vakiy = alle Einwohner.
# GRAZ:      GHSL hat KEINE Altersangaben. Szenario-Ansatz: immer die
#             Gesamtbevölkerung zählen ('wenn alle so langsam gingen wie Ältere').
#             Optional: Anteil 65+ pro Grazer Bezirk zum Vergleich.
# Calculate how many 0ver 65-year-olds there are in the region
population_Grid_PkSeutu_17["he_+65"] = population_Grid_PkSeutu_17["he_65_69"] +population_Grid_PkSeutu_17["he_70_74"]+population_Grid_PkSeutu_17["he_75_79"] +population_Grid_PkSeutu_17["he_80_84"] + population_Grid_PkSeutu_17["he_85_"]
population_Grid_PkSeutu_06["he_+65"] = population_Grid_PkSeutu_06["he_65_69"] +population_Grid_PkSeutu_06["he_70_74"]+population_Grid_PkSeutu_06["he_75_79"] +population_Grid_PkSeutu_06["he_80_84"] + population_Grid_PkSeutu_06["he_85_"]

# ERKLÄRUNG: Für jede Kurve in Abb. 4: Zellen nach Gehzeit aufsteigend sortieren,
#             Einwohner aufsummieren (cumsum) und durch die Gesamtsumme teilen.
#             Ergebnis: 'X % der Bevölkerung erreichen in <= t Minuten einen Markt'.
#             cumu_vakiy_pros_m1 ... m8 = Modell 1 bis 8.
# GRAZ:      Für jedes Modell gleich, als Funktion statt 8 Kopien:
#             def kumuliert(df, zeit_spalte, pop_spalte='einwohner'):
#                 d = df.sort_values(zeit_spalte)
#                 return d[zeit_spalte], d[pop_spalte].cumsum() / d[pop_spalte].sum() * 100
# Values for cumulative curves
population_Grid_PkSeutu_17.sort_values(by= "Adult_speed_dry", ascending=True, inplace=True)
population_Grid_PkSeutu_17["cumu_vakiy_m1"] = population_Grid_PkSeutu_17["he_vakiy"].cumsum()
population_Grid_PkSeutu_17["cumu_vakiy_pros_m1"] = population_Grid_PkSeutu_17["cumu_vakiy_m1"] /population_Grid_PkSeutu_17["he_vakiy"].sum()*100 

# ERKLÄRUNG: Bei den Modellen mit Älteren (m2, m5, m6, m8) wird hier mit he_+65
#             summiert, also wirklich 'Anteil der Älteren'.
# PROBLEM:   In den print()-Ausgaben und im Balkendiagramm weiter unten wird aber
#             für ALLE Modelle he_vakiy (Gesamtbevölkerung) verwendet. Siehe dort.
population_Grid_PkSeutu_17.sort_values(by= "Old_speed_dry", ascending=True, inplace=True)
population_Grid_PkSeutu_17["cumu_vakiy_m2"] = population_Grid_PkSeutu_17["he_+65"].cumsum()
population_Grid_PkSeutu_17["cumu_vakiy_pros_m2"] = population_Grid_PkSeutu_17["cumu_vakiy_m2"] /population_Grid_PkSeutu_17["he_+65"].sum()*100

population_Grid_PkSeutu_17.sort_values(by= "Adult_speed_winter", ascending=True, inplace=True)
population_Grid_PkSeutu_17["cumu_vakiy_m3"] = population_Grid_PkSeutu_17["he_vakiy"].cumsum()
population_Grid_PkSeutu_17["cumu_vakiy_pros_m3"] = population_Grid_PkSeutu_17["cumu_vakiy_m3"] /population_Grid_PkSeutu_17["he_vakiy"].sum()*100

population_Grid_PkSeutu_06.sort_values(by= "Adult_speed_dry", ascending=True, inplace=True)
population_Grid_PkSeutu_06["cumu_vakiy_m4"] = population_Grid_PkSeutu_06["he_vakiy"].cumsum()
population_Grid_PkSeutu_06["cumu_vakiy_pros_m4"] = population_Grid_PkSeutu_06["cumu_vakiy_m4"] /population_Grid_PkSeutu_06["he_vakiy"].sum()*100

population_Grid_PkSeutu_17.sort_values(by= "Old_speed_winter", ascending=True, inplace=True)
population_Grid_PkSeutu_17["cumu_vakiy_m5"] = population_Grid_PkSeutu_17["he_+65"].cumsum()
population_Grid_PkSeutu_17["cumu_vakiy_pros_m5"] = population_Grid_PkSeutu_17["cumu_vakiy_m5"] /population_Grid_PkSeutu_17["he_+65"].sum()*100

population_Grid_PkSeutu_06.sort_values(by= "Old_speed_dry", ascending=True, inplace=True)
population_Grid_PkSeutu_06["cumu_vakiy_m6"] = population_Grid_PkSeutu_06["he_+65"].cumsum()
population_Grid_PkSeutu_06["cumu_vakiy_pros_m6"] = population_Grid_PkSeutu_06["cumu_vakiy_m6"] /population_Grid_PkSeutu_06["he_+65"].sum()*100

population_Grid_PkSeutu_06.sort_values(by= "Adult_speed_winter", ascending=True, inplace=True)
population_Grid_PkSeutu_06["cumu_vakiy_m7"] = population_Grid_PkSeutu_06["he_vakiy"].cumsum()
population_Grid_PkSeutu_06["cumu_vakiy_pros_m7"] = population_Grid_PkSeutu_06["cumu_vakiy_m7"] /population_Grid_PkSeutu_06["he_vakiy"].sum()*100

population_Grid_PkSeutu_06.sort_values(by= "Old_speed_winter", ascending=True, inplace=True)
population_Grid_PkSeutu_06["cumu_vakiy_m8"] = population_Grid_PkSeutu_06["he_+65"].cumsum()
population_Grid_PkSeutu_06["cumu_vakiy_pros_m8"] = population_Grid_PkSeutu_06["cumu_vakiy_m8"] /population_Grid_PkSeutu_06["he_+65"].sum()*100


# ============================================================================
# ABB. 4 IM PAPER: kumulierte Erreichbarkeit, 8 Felder
# ============================================================================
# FIGURE 1: Cumulative accessibility
mpl.rcParams['lines.linewidth'] = 2
mpl.rcParams['axes.titlesize'] = 30
mpl.rcParams['axes.titleweight'] = 'bold'
mpl.rcParams['axes.titlelocation'] = 'left'

# ERKLÄRUNG: 2 Zeilen x 4 Spalten = 8 Felder, ein Feld pro Modell.
fig, ax =  plt.subplots(2,4)
plt.subplots_adjust(top = 0.90, bottom=0.1, hspace=0.4, wspace=0.2)

# ERKLÄRUNG: In jedem Feld: schwarze gestrichelte Linie = Basismodell (m1),
#             farbige Linie = jeweiliges Modell. Senkrechte Linien bei 10/15/20 min.
f1 = population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[0,0],
                                linestyle='dashed', color = "black", legend=None)
f1.set(xlabel=None)
f1.tick_params(axis='both', which='major', labelsize=20)
# PROBLEM:   Die Prozentwerte ('81%', '93%', ...) und die Höhen der senkrechten
#             Linien (0.78, 0.90, ...) sind VON HAND EINGETIPPT, nicht berechnet.
#             Ändern sich die Daten, stimmt die Grafik nicht mehr.
# GRAZ:      Werte berechnen und einsetzen, z. B.
#             anteil = df.loc[df[spalte] <= 15, 'einwohner'].sum() / df['einwohner'].sum()
#             ax.text(15.3, 20, f'{anteil:.0%}')
#             Und: eine Schleife über die 8 Modelle statt 8 kopierter Blöcke.
f1.axvline(10,0,0.78, color='black', linestyle='dotted', linewidth=1.5)
f1.text(10.3,20, "81%", style='oblique', fontsize=18, weight='bold')
f1.axvline(15,0,0.90, color='black', linestyle='dotted', linewidth=1.5)
f1.text(15.3,20, "93%", style='oblique', fontsize=18, weight='bold')
f1.axvline(20,0,0.93, color='black', linestyle='dotted', linewidth=1.5)
f1.text(20.3,20, "97%", style='oblique', fontsize=18, weight='bold')

f21 = population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[0,1],
                                linestyle='dashed', color = "black", legend=None)
f22 = population_Grid_PkSeutu_17.plot(kind="line", x="Old_speed_dry", y="cumu_vakiy_pros_m2", ax=ax[0,1],
                                linestyle='dashed', color = "darkgreen", legend=None)
f22.set(xlabel=None)
f22.tick_params(axis='both', which='major', labelsize=20)
f22.axvline(10,0,0.71, color='black', linestyle='dotted', linewidth=1.5)
f22.text(10.3,20, "72%", style='oblique', fontsize=18, weight='bold')
f22.axvline(15,0,0.87, color='black', linestyle='dotted', linewidth=1.5)
f22.text(15.3,20, "88%", style='oblique', fontsize=18, weight='bold')
f22.axvline(20,0,0.94, color='black', linestyle='dotted', linewidth=1.5)
f22.text(20.3,20, "95%", style='oblique', fontsize=18, weight='bold')

f31= population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[0,2],
                                linestyle='dashed', color = "black", legend=None)
f32= population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_winter", y="cumu_vakiy_pros_m3", ax=ax[0,2],
                                linestyle='dashed', color = "dodgerblue", legend=None)
f32.set(xlabel=None)
f32.tick_params(axis='both', which='major', labelsize=20)
f32.axvline(10,0,0.76, color='black', linestyle='dotted', linewidth=1.5)
f32.text(10.3,20, "78%", style='oblique', fontsize=18, weight='bold')
f32.axvline(15,0,0.88, color='black', linestyle='dotted', linewidth=1.5)
f32.text(15.3,20, "92%", style='oblique', fontsize=18, weight='bold')
f32.axvline(20,0,0.94, color='black', linestyle='dotted', linewidth=1.5)
f32.text(20.3,20, "97%", style='oblique', fontsize=18, weight='bold')

f41= population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[0,3],
                                linestyle='dashed', color = "black", legend=None)
f42= population_Grid_PkSeutu_06.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m4", ax=ax[0,3],
                                linestyle='dashed', color = "darkblue", legend=None)
f42.set(xlabel=None)
f42.tick_params(axis='both', which='major', labelsize=20)
f42.axvline(10,0,0.30, color='black', linestyle='dotted', linewidth=1.5)
f42.text(10.3,20, "30%", style='oblique', fontsize=18, weight='bold')
f42.axvline(15,0,0.445, color='black', linestyle='dotted', linewidth=1.5)
f42.text(15.3,20, "45%", style='oblique', fontsize=18, weight='bold')
f42.axvline(20,0,0.565, color='black', linestyle='dotted', linewidth=1.5)
f42.text(20.3,20, "57%", style='oblique', fontsize=18, weight='bold')

f51 = population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[1,0],
                                linestyle='dashed', color = "black",legend=None)
f52 = population_Grid_PkSeutu_17.plot(kind="line", x="Old_speed_winter", y="cumu_vakiy_pros_m5", ax=ax[1,0],
                                linestyle='dashed', color = "darkmagenta", legend=None)
f52.set(xlabel=None)
f52.tick_params(axis='both', which='major', labelsize=20)
f52.axvline(10,0,0.67, color='black', linestyle='dotted', linewidth=1.5)
f52.text(10.3,20, "67%", style='oblique', fontsize=18, weight='bold')
f52.axvline(15,0,0.84, color='black', linestyle='dotted', linewidth=1.5)
f52.text(15.3,20, "85%", style='oblique', fontsize=18, weight='bold')
f52.axvline(20,0,0.91, color='black', linestyle='dotted', linewidth=1.5)
f52.text(20.3,20, "94%", style='oblique', fontsize=18, weight='bold')

f61 = population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[1,1],
                                linestyle='dashed', color = "black", legend=None)
f62 = population_Grid_PkSeutu_06.plot(kind="line", x="Old_speed_dry", y="cumu_vakiy_pros_m6", ax=ax[1,1],
                                linestyle='dashed', color = "darkorange", legend=None)
f62.set(xlabel=None)
f62.tick_params(axis='both', which='major', labelsize=20)
f62.axvline(10,0,0.25, color='black', linestyle='dotted', linewidth=1.5)
f62.text(10.3,20, "24%", style='oblique', fontsize=18, weight='bold')
f62.axvline(15,0,0.38, color='black', linestyle='dotted', linewidth=1.5)
f62.text(15.3,20, "38%", style='oblique', fontsize=18, weight='bold')
f62.axvline(20,0,0.495, color='black', linestyle='dotted', linewidth=1.5)
f62.text(20.3,20, "49%", style='oblique', fontsize=18, weight='bold')

f71 = population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[1,2],
                                linestyle='dashed', color = "black", legend=None)
f72 = population_Grid_PkSeutu_06.plot(kind="line", x="Adult_speed_winter", y="cumu_vakiy_pros_m7", ax=ax[1,2],
                                linestyle='dashed', color = "darkslategrey", legend=None)
f72.set(xlabel=None)
f72.tick_params(axis='both', which='major', labelsize=20)
f72.axvline(10,0,0.29, color='black', linestyle='dotted', linewidth=1.5)
f72.text(10.3,20, "28%", style='oblique', fontsize=18, weight='bold')
f72.axvline(15,0,0.42, color='black', linestyle='dotted', linewidth=1.5)
f72.text(15.3,20, "42%", style='oblique', fontsize=18, weight='bold')
f72.axvline(20,0,0.535, color='black', linestyle='dotted', linewidth=1.5)
f72.text(20.3,20, "54%", style='oblique', fontsize=18, weight='bold')

f81 = population_Grid_PkSeutu_17.plot(kind="line", x="Adult_speed_dry", y="cumu_vakiy_pros_m1", ax=ax[1,3],
                                linestyle='dashed', color = "black", legend=None)
f82 = population_Grid_PkSeutu_06.plot(kind="line", x="Old_speed_winter", y="cumu_vakiy_pros_m8", ax=ax[1,3],
                                linestyle='dashed', color = "darkred", legend=None)
f82.set(xlabel=None)
f82.tick_params(axis='both', which='major', labelsize=20)
f82.axvline(10,0,0.22, color='black', linestyle='dotted', linewidth=1.5)
f82.text(10.3,20, "21%", style='oblique', fontsize=18, weight='bold')
f82.axvline(15,0,0.35, color='black', linestyle='dotted', linewidth=1.5)
f82.text(15.3,20, "34%", style='oblique', fontsize=18, weight='bold')
f82.axvline(20,0,0.46, color='black', linestyle='dotted', linewidth=1.5)
f82.text(20.3,20, "46%", style='oblique', fontsize=18, weight='bold')

# ERKLÄRUNG: Gemeinsame Achsenbeschriftung, x-Achse auf 0-30 min begrenzt.
fig.text(0.5, 0.01, 'Walking time to the closest grocery store (min)', ha='center',fontsize=30)
fig.text(0.06, 0.5, 'Share of the population (%)', va='center', rotation='vertical', fontsize=30)

plt.setp(ax, xlim=(0,30))
fig.show()


# ============================================================================
# PROZENTWERTE FÜR 10 / 15 / 20 MIN
# ============================================================================
# ERKLÄRUNG: Gibt pro Modell die Summe der Einwohner aus, deren Gehzeit <= 10, 15
#             bzw. 20 min ist. Die Prozentwerte stehen als Kommentar am Zeilenende
#             (wurden also von Hand abgelesen und notiert).
# PROBLEM:   WICHTIG FÜR DIE KRITIK: Hier wird für ALLE Modelle 'he_vakiy'
#             (Gesamtbevölkerung) gezählt, auch für die Älteren-Modelle.
#             Modell 8: 400.996 / 1.166.567 = 34,4 % der GESAMTbevölkerung.
#             Im Abstract steht aber '34 % of the older population'.
#             Gemeint ist eigentlich: '34 % der Bevölkerung, WENN alle so langsam
#             gingen wie Ältere im Winter'.
#             Außerdem: .sum() summiert auch die Gehzeit-Spalte (sinnlos, aber
#             harmlos) und gibt absolute Zahlen aus, keine Prozente.
# GRAZ:      Genau dieser Szenario-Ansatz ist unser Vorgehen. Prozente direkt
#             berechnen und als Tabelle speichern (Modell x 10/15/20 min).
#Data preparaition for barplot
    #population_Grid_PkSeutu_17["he_vakiy"].sum() = 1166567
    #population_Grid_PkSeutu_17["he_+65"].sum() = 189506
    #10min
print(population_Grid_PkSeutu_17[["Adult_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Adult_speed_dry"]<=10].sum()) #, 80.97
print(population_Grid_PkSeutu_17[["Old_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Old_speed_dry"]<=10].sum()) #, 72.22
print(population_Grid_PkSeutu_17[["Adult_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Adult_speed_winter"]<=10].sum()) #, 77.87
print(population_Grid_PkSeutu_06[["Adult_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Adult_speed_dry"]<=10].sum()) #, 29.62
print(population_Grid_PkSeutu_17[["Old_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Old_speed_winter"]<=10].sum()) #, 66.99
print(population_Grid_PkSeutu_06[["Old_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Old_speed_dry"]<=10].sum()) #, 23.82
print(population_Grid_PkSeutu_06[["Adult_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Adult_speed_winter"]<=10].sum()) #,27.81
print(population_Grid_PkSeutu_06[["Old_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Old_speed_winter"]<=10].sum()) #, 20.73
    #15min
print(population_Grid_PkSeutu_17[["Adult_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Adult_speed_dry"]<=15].sum()) #, 93.44
print(population_Grid_PkSeutu_17[["Old_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Old_speed_dry"]<=15].sum()) #, 88.37
print(population_Grid_PkSeutu_17[["Adult_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Adult_speed_winter"]<=15].sum()) #, 91.80
print(population_Grid_PkSeutu_06[["Adult_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Adult_speed_dry"]<=15].sum()) #, 45.20
print(population_Grid_PkSeutu_17[["Old_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Old_speed_winter"]<=15].sum()) #, 85.41
print(population_Grid_PkSeutu_06[["Old_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Old_speed_dry"]<=15].sum()) #, 37.58
print(population_Grid_PkSeutu_06[["Adult_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Adult_speed_winter"]<=15].sum()) #,42.19
print(population_Grid_PkSeutu_06[["Old_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Old_speed_winter"]<=15].sum()) #, 33.97
    #20min
print(population_Grid_PkSeutu_17[["Adult_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Adult_speed_dry"]<=20].sum()) #, 97.14
print(population_Grid_PkSeutu_17[["Old_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Old_speed_dry"]<=20].sum()) #, 95.23
print(population_Grid_PkSeutu_17[["Adult_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Adult_speed_winter"]<=20].sum()) #, 96.63
print(population_Grid_PkSeutu_06[["Adult_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Adult_speed_dry"]<=20].sum()) #, 57.40
print(population_Grid_PkSeutu_17[["Old_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_17["Old_speed_winter"]<=20].sum()) #, 93.51
print(population_Grid_PkSeutu_06[["Old_speed_dry", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Old_speed_dry"]<=20].sum()) #, 49.15
print(population_Grid_PkSeutu_06[["Adult_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Adult_speed_winter"]<=20].sum()) #,54.20
print(population_Grid_PkSeutu_06[["Old_speed_winter", "he_vakiy"]].loc[population_Grid_PkSeutu_06["Old_speed_winter"]<=20].sum()) #, 45.64

# ERKLÄRUNG: Teilmengen nach Gemeinde ('kunta': 091 Helsinki, 092 Vantaa,
#             049 Espoo, 235 Kauniainen). Werden danach nicht verwendet.
# GRAZ:      Optional: Auswertung pro Grazer Bezirk (Bezirksgrenzen von
#             data.graz.gv.at oder OSM, admin_level 9).
population_Grid_PkSeutu_17HKI = population_Grid_PkSeutu_17.loc[population_Grid_PkSeutu_17["kunta"] == "091"]
population_Grid_PkSeutu_06HKI = population_Grid_PkSeutu_06.loc[population_Grid_PkSeutu_06["kunta"] == "091"]

population_Grid_PkSeutu_17VANTAA = population_Grid_PkSeutu_17.loc[population_Grid_PkSeutu_17["kunta"] == "092"]
population_Grid_PkSeutu_17ESPOO = population_Grid_PkSeutu_17.loc[population_Grid_PkSeutu_17["kunta"] == "049"]
population_Grid_PkSeutu_06ESPOO = population_Grid_PkSeutu_06.loc[population_Grid_PkSeutu_06["kunta"] == "049"]

population_Grid_PkSeutu_17KAUNIAINEN = population_Grid_PkSeutu_17.loc[population_Grid_PkSeutu_17["kunta"] == "235"]

# ERKLÄRUNG: Daten für ein Balkendiagramm 'Anteil mit 15-min-Zugang pro Modell'.
# PROBLEM:   Komplett VON HAND EINGETIPPT. barplotDictHKI ist eine exakte Kopie
#             von barplotDictALL (also nicht wirklich nur Helsinki).
#             Model 2 steht mit 88.53 drin, oben im print-Kommentar mit 88.37.
# GRAZ:      Aus unserer Ergebnistabelle erzeugen, nichts abtippen.
barplotDictALL = {'Model_name': ['Model 1', 'Model 2','Model 3','Model 4','Model 5','Model 6','Model 7','Model 8'],
                 'Pop': [1089902, 1032841,1070932,525219,1002048,443324,492226,400996],
                 'Pop%' : [93.43, 88.53,91.80,45.02,85.89,38.00,42.19,34.37]}

barplotDictHKI = {'Model_name': ['Model 1', 'Model 2','Model 3','Model 4','Model 5','Model 6','Model 7','Model 8'],
                 'Pop': [1089902, 1032841,1070932,525219,1002048,443324,492226,400996],
                 'Pop%' : [93.43, 88.53,91.80,45.02,85.89,38.00,42.19,34.37]}

barplotDF = pd.DataFrame(data=barplotDictALL)


# ============================================================================
# ABB. 3 IM PAPER: Verteilung der Gehgeschwindigkeiten
# ============================================================================
# ERKLÄRUNG: Ridge Plot: pro Kombination aus Alter und Straßenzustand eine
#             geglättete Verteilungskurve (kdeplot) übereinander gestapelt.
# GRAZ:      Kann fast 1:1 übernommen werden, mit unserer selbst gebauten
#             Tabelle aus den zwei Mess-CSVs. Einfachere Alternative:
#             sns.boxplot(data=speeds_long, x='Speed (km/h)', y='Gruppe')
#Ridge plot for walking speeds

pal = sns.cubehelix_palette(2, rot=-.25, light=.4)
g = sns.FacetGrid(walkingSpeedData, row="age & road condition", hue= "Age", aspect=15, height=1.5, palette=pal )
g.map(sns.kdeplot, "Speed",
      bw_adjust=.5, clip_on=False,
      fill=True, alpha=1, linewidth=1.5, gridsize =500)
g.map(sns.kdeplot, "Speed", clip_on=False, color="w", lw=2, bw_adjust=.5)
g.refline(y=0, linewidth=2, linestyle="-", color=None, clip_on=False)
g.set_xlabels("Walking speed (km/h)", fontsize=30)
g.set_xticklabels(fontsize=26)
g.set_ylabels("Density", fontsize=18)
g.set_yticklabels(fontsize=18)
plt.ylim(0, 0.6)
plt.xlim(0, 8)
plt.legend([],[], frameon=False)
plt.ion()


# ============================================================================
# ABB. 6 IM PAPER: erreichte Supermärkte je Geschwindigkeit
# ============================================================================
# ERKLÄRUNG: Zwei übereinander gelegte Balken: erreichte Märkte um 6 Uhr und
#             um 17 Uhr für die 8 Perzentil-Geschwindigkeiten.
# PROBLEM:   Beide Balken bekommen dasselbe Label; dark_background wird erst
#             NACH dem Erstellen der Figur gesetzt. Optik vermutlich nachbearbeitet.
# GRAZ:      Optional (nur wenn wir Teil 2 / Einzugsgebiete machen).
#Barplot on people reaching the closest grocery store in 15min
sns.set_style("darkgrid", {'axes.grid' : True})
mpl.interactive(True)
f, ax = plt.subplots(figsize=(6, 15))

palette= ["#e3c557","#fb9a07","#ed6925", "#cf4346", "#a52c60", "#781c6d", "#4b0c6b", "#240f58"]

sns.set_context(rc={"grid.linewidth": 1})
sns.set(style="ticks", context="talk")
plt.style.use("dark_background")
sns.set_palette(sns.color_palette(palette))

sns.barplot(x="Speed", y="6am_viz", data=serviceAreaGroceryCounts,
            label="Reached grocery stores")
sns.barplot(x = "Speed", y="5pm_viz", data=serviceAreaGroceryCounts, label = "Reached grocery stores")


# ERKLÄRUNG: Übrig gebliebene Zeile ohne Funktion (Farbliste, wird nicht
#             zugewiesen). Zeigt, dass das Skript nicht aufgeräumt wurde.
["#e3c557","#fb9a07","#ed6925", "#cf4346", "#a52c60", "#781c6d", "#4b0c6b", "#240f58"]
