# ============================================================================
# KOMMENTIERTE KOPIE des Originalskripts
#   WalkingAccessibilityRoutingTEMPORAL.py
# aus https://github.com/DigitalGeographyLab/15_minute_city_for_all_article
# (Willberg, Fink & Toivonen 2023, Lizenz: Apache 2.0)
#
# Der ORIGINALCODE IST UNVERÄNDERT. Ergänzt wurden nur Kommentarzeilen.
# Die unveränderte Originaldatei liegt in ./original/
#
# Hinweis: Im Original-Repo liegt dieses ROUTING-Skript im Ordner
# 'visualisation/' und das Abbildungs-Skript im Ordner 'processing/'.
# Die Ordnernamen sind also vertauscht.
#
# Legende der Kommentare:
#   ERKLÄRUNG  = was dieser Abschnitt macht
#   PROBLEM    = Fehler oder Unklarheit im Original (Material für die Kritik)
#   GRAZ       = was wir für Graz anders machen
#
# DIESES SKRIPT LÄUFT SO NICHT: leerer Pfad (os.chdir), fehlende Eingabedaten,
# Syntaxfehler im letzten Block, veraltete OSMnx-Funktionen und KeyErrors.
# Es dient nur zum Nachlesen der Methode.
#
# Ablauf in Kurzform:
#   1. Wegenetz, Raster und Supermärkte (17 Uhr / 6 Uhr) einlesen
#   2. Rasterzellen und Supermärkte dem nächsten Netzknoten zuordnen
#   3. Distanz von JEDER Zelle zu JEDEM Supermarkt berechnen (Pandana)
#   4. Pro Zelle die kleinste Distanz nehmen = nächster Supermarkt
#   5. Distanz / Gehgeschwindigkeit = Gehzeit für die 8 Modelle
#   6. Ergebnis als GeoPackage speichern
#   7. Einzugsgebiete (15 min) ab einem Startpunkt für Abb. 6
# ============================================================================

# ERKLÄRUNG: Bibliotheken. Pandana rechnet die vielen kürzesten Wege (Teil 1),
#             OSMnx + NetworkX werden nur für die Einzugsgebiete am Ende gebraucht.
#             fiona und seaborn werden in diesem Skript nicht wirklich genutzt.
# GRAZ:      Kein Pandana (unter Windows oft schwer zu installieren). Wir nehmen
#             nur osmnx, networkx, geopandas, pandas.
import os
import pandas as pd
import geopandas as gpd
import pandana
import seaborn as sns
import networkx as nx
import osmnx as ox
import fiona
from shapely.geometry import mapping, Point, LineString, Polygon
# PROBLEM:   ox.config() gibt es in aktuellen OSMnx-Versionen (2.x) nicht mehr.
# GRAZ:      ox.settings.use_cache = True   und   ox.settings.log_console = True
ox.config(log_console=True, use_cache=True)
ox.__version__


#### FUNCTIONS #####


# ERKLÄRUNG: Ordnet jedem Punkt (Rasterzelle oder Supermarkt) die ID des nächsten
#             Knotens im Pandana-Netz zu. 'network' ist eine globale Variable, die
#             erst weiter unten erzeugt wird.
#             Achtung: Der Weg vom Punkt bis zum Knoten wird später NICHT zur
#             Distanz addiert (methodische Vereinfachung, im Bericht erwähnen).
# GRAZ:      pop['node'] = ox.distance.nearest_nodes(G, pop.geometry.x, pop.geometry.y)
#             (G muss dafür projiziert sein, z. B. EPSG:32633, Koordinaten in Metern)
# FUNCTION 1: Add neareast nodeID as column
def nearestNodeID(df):
    df['x'] = df.geometry.x
    df['y'] = df.geometry.y
    df["node_id"] = network.get_node_ids(df['x'], df['y']).values

    return df

# ERKLÄRUNG: Liefert jede Knoten-ID nur einmal, auch wenn mehrere Rasterzellen oder
#             Supermärkte am selben Knoten hängen. Spart Rechenzeit bei Pandana.
# GRAZ:      Brauchen wir nicht: Der Multi-Source-Dijkstra (siehe unten) rechnet
#             ohnehin für jeden Knoten nur einmal.
# FUNCTION 2: Get unique nodes
def getUniqueNodes (df):
    nodes_unique_population = df.groupby(['node_id']).first().reset_index()
    nodes_unique_population = nodes_unique_population["node_id"]

    return nodes_unique_population

# ERKLÄRUNG: Gehzeit in Minuten = Distanz [m] / Geschwindigkeit [m/h] * 60.
#             Das passiert für 41 Geschwindigkeiten: 3000, 3100, ... 7000 m/h
#             (= 3,0 bis 7,0 km/h). Ergebnisspalten: tt_3000, tt_3100, ...
# PROBLEM:   Die Spalte 'distance_17' ist fest eingetippt. Weiter unten wird die
#             Funktion aber auch auf die 6-Uhr-Tabelle angewendet, die nur
#             'distance_06' hat -> KeyError, das Skript bricht dort ab.
# GRAZ:      Spaltenname als Parameter übergeben, z. B.
#             def gehzeiten(df, dist_spalte): ...
#             Die Schleife über viele Geschwindigkeiten ist genau das, was wir für
#             die SENSITIVITÄTSANALYSE brauchen (z. B. 3,0 bis 6,0 km/h).
#FUNCTION 3: Walk time calculator
def calculateWalkingTimes(df):
    speed = 3000
    for i in range(41):
        df["tt_"+str(speed)] = df["distance_17"] / speed * 60
        speed += 100
    return df

# ERKLÄRUNG: Zählt pro Startpunkt, wie viele Supermärkte in <= 15 min erreichbar
#             sind, und mittelt das über alle Startpunkte - für jede der 41
#             Geschwindigkeiten. (Wird im Paper nicht als Abbildung gezeigt.)
# PROBLEM:   Gruppiert nach 'id_nro' (Spalte des Bevölkerungsrasters). In der
#             aktiven Variante des Codes heißt die ID-Spalte aber 'YKR_ID'
#             -> KeyError.
# GRAZ:      Optional. Wenn gewünscht: nach der ID unserer Rasterzellen gruppieren.
def calculateReachableStores(df):
    identifier = 3000
    resultDF = pd.DataFrame(columns=["speed", "count"])
    for i in range(41):
        under15 = df.loc[df["tt_"+str(identifier)]<=15]
        under15Count = under15.groupby(["id_nro"]).count().reset_index()
        resultDF.loc[len(resultDF.index)] = [identifier, under15Count["groceryID"].mean()]
        identifier += 100
    return resultDF

#### MAIN #####


# ============================================================================
# HAUPTTEIL
# ============================================================================
# PROBLEM:   os.chdir() ohne Pfad -> TypeError, das Skript startet nicht.
# GRAZ:      Kein chdir. Relative Pfade zum Repo verwenden, z. B. mit pathlib:
#             DATA = Path(__file__).parents[1] / 'data'
os.chdir() #ADD PATH

# ERKLÄRUNG: Das Fußwegnetz wurde vorher einmal aus OSM geladen und als Knoten-
#             und Kantentabelle (CSV) gespeichert (siehe auskommentierten Download
#             unten bei PART 1).
# PROBLEM:   nodes22.csv und edges22.csv sind NICHT im Repo.
# GRAZ:      G = ox.graph_from_polygon(graz_mit_2km_puffer, network_type='walk')
#             G = ox.project_graph(G, to_crs='EPSG:32633')
#             Einmal laden und speichern: ox.save_graphml(G, 'data/raw/walk.graphml')
#Read road network
nodes = pd.read_csv('Data\\nodes22.csv', index_col=0)
edges = pd.read_csv('Data\\edges22.csv', index_col=[0,1])

# ERKLÄRUNG: Zwei Raster werden geladen:
#             1) population_Grid / population_PkSeutu_2020: offizielles 250-m-
#                Bevölkerungsraster von Statistics Finland (Polygone + Mittelpunkte),
#                Spalten u. a. he_vakiy (Einwohner gesamt), he_65_69 ... (Alter).
#             2) metropAccessGrid: das YKR-Raster des Helsinki-Projekts
#                MetropAccess (gleiche 250-m-Zellen, aber OHNE Einwohnerzahlen).
#             Weiter unten wird mit Raster 2 gerechnet, die Abbildungen brauchen
#             aber Raster 1 (siehe Hinweise unten).
# PROBLEM:   Keine dieser Dateien ist im Repo.
# GRAZ:      Statt beider Raster: GHSL-Bevölkerungsraster (GHS-POP R2023A, 100 m),
#             auf Graz + Puffer zuschneiden, nach EPSG:32633 umprojizieren,
#             Zellen ohne Einwohner entfernen, Zellmittelpunkte als Startpunkte.
#             Spalte 'einwohner' statt 'he_vakiy'. Keine Altersspalten (Szenario-
#             Ansatz: 'wenn alle so langsam gingen wie Ältere').
#Read population and POIs data
population_Grid_PkSeutu = gpd.read_file('Data\\rttk20_250m_shp\\HKI_Region2020_YKR_population_populatedOnly.shp')
metropAccessGrid_PkSeutu = gpd.read_file('Data\\MetropAccess_YKR_grid\\MetropAccess_YKR_grid_EurefFIN.shp')

population_PkSeutu_2020 = gpd.read_file('Data\\rttk20_250m_shp\\HKI_Region2020_YKR_population_populatedOnlyCENTROIDS.shp')
metropAccessCentroids_PkSeutu = gpd.read_file('Data\\MetropAccess_YKR_grid\\MetropAccess_YKR_grid_EurefFIN_Centroids.shp')

# ERKLÄRUNG: Supermärkte (OSM: shop=supermarket + shop=convenience, ohne Kioske),
#             bereits AUFGETEILT in: offen um 17 Uhr ('5pm') und offen um 6 Uhr ('6am').
# PROBLEM:   WICHTIGSTER FEHLENDER SCHRITT: Wie aus allen Supermärkten die beiden
#             Dateien entstanden sind (Quelle der Öffnungszeiten, Umgang mit
#             fehlenden Angaben), steht weder im Code noch genau im Paper.
#             Genau dieser Faktor (Uhrzeit) hat laut Paper den größten Effekt.
# GRAZ:      Das bauen wir selbst (Notebook 02):
#             shops = ox.features_from_polygon(graz_puffer,
#                       tags={'shop': ['supermarket', 'convenience']})
#             -> Polygone zu Punkten, Drogerien/Imbisse entfernen,
#             -> OSM-Tag 'opening_hours' auslesen (z. B. humanized_opening_hours),
#             -> Spalten offen_17 und offen_07 für einen festen Dienstag.
#             7 Uhr statt 6 Uhr, weil in Österreich um 6 Uhr fast nichts offen hat.
groceries_PKSeutu_2022_17 = gpd.read_file('Data\\Kaupat2022_5pm_WGS84.gpkg')
groceries_PKSeutu_2022_06 = gpd.read_file('Data\\Kaupat2022_6am_WGS84.gpkg')

# ERKLÄRUNG: Die selbst gemessenen Gehgeschwindigkeiten (das einzige, was im Repo
#             liegt). Spalten u. a.: 'Speed (km/h)', 'Age' (Adult/Elderly),
#             'Condition' (nur Winter: Straßenzustand), 'Place'.
#             Achtung: In der CSV steht in Zeile 1 ein Titel, die Spaltennamen erst
#             in Zeile 2 -> beim Einlesen skiprows=1 nötig.
# GRAZ:      Übernehmen wir. Mittelwerte selbst berechnen (Notebook 01) und mit
#             Tabelle 1 im Paper sowie den Werten weiter unten vergleichen.
walkingSpeedMeasurementsDRY = pd.read_csv('Data\\Walking_speed_measurements_EW_CH_Dry.csv', sep=";")
walkingSpeedMeasurementsWINTER= pd.read_csv('Data\\Walking_speed_measurements_EW_CH_Winter.csv', sep=";", encoding='latin-1')

# ERKLÄRUNG: Ein einzelner Punkt im Helsinkier Stadtteil Vallila. Startpunkt für die
#             15-Minuten-Einzugsgebiete am Ende des Skripts (Abb. 6 im Paper).
# GRAZ:      Ein zentraler Punkt in Graz, z. B. Jakominiplatz oder Hauptplatz.
serviceAreaStartPointVALLILA = gpd.read_file("Data\\ServiceAreaStartPointVALLILA_UTM35N.gpkg")

# ERKLÄRUNG: Alles nach WGS84 (EPSG:4326, Grad), weil das Pandana-Netz in Grad vorliegt.
# PROBLEM:   Die Variable heißt danach 'population_grid_PkSeutu' (kleines g),
#             vorher 'population_Grid_PkSeutu' (großes G) - zwei verschiedene Variablen.
# GRAZ:      Alles in EPSG:32633 (UTM 33N, Meter). Für Distanzen und Puffer besser.
# Reproject population and grocery store data
population_grid_PkSeutu = population_Grid_PkSeutu.to_crs(epsg=4326)
population_PkSeutu_2020 = population_PkSeutu_2020.to_crs(epsg=4326)
metropAccessGrid_PkSeutu = metropAccessGrid_PkSeutu.to_crs(epsg=4326)
metropAccessCentroids_PkSeutu = metropAccessCentroids_PkSeutu.to_crs(epsg=4326)

groceries_PKSeutu_2022_17 = groceries_PKSeutu_2022_17.to_crs(epsg=4326)
groceries_PKSeutu_2022_06 = groceries_PKSeutu_2022_06.to_crs(epsg=4326)


################# PART 1 -  ROUTING  #######################

# ERKLÄRUNG: Der auskommentierte Block zeigt, wie das Netz ursprünglich geladen
#             wurde: mit dem Paket 'osmnet' (Präfix osm.) über eine Bounding Box
#             um die Region Helsinki. 'osm' wird oben aber gar nicht importiert.
# GRAZ:      Siehe oben: ox.graph_from_polygon(..., network_type='walk').
#Read walking network from OSM
'''
network = osm.pdna_network_from_bbox(60.0, 24.0, 60.5, 25.3, network_type='walk')  # Helsinki region
network.nodes_df.to_csv('nodes.csv')
network.edges_df.to_csv('edges.csv')
'''
# ERKLÄRUNG: Entfernt von Hand ~20 Knoten und ~18 Kanten, die nicht mit dem
#             restlichen Netz verbunden sind ('Inseln'). Von dort wäre kein
#             Supermarkt erreichbar.
# PROBLEM:   Die IDs sind fest eingetippt und gelten nur für genau diesen Download.
#             Zudem prüft z. B. (from != A) & (to != B) nicht 'diese eine Kante',
#             sondern entfernt ALLE Kanten mit from == A ODER to == B.
# GRAZ:      Entfällt. ox.graph_from_polygon behält standardmäßig nur die größte
#             zusammenhängende Komponente (retain_all=False).
#Remove unconnected edges
nodes = nodes.loc[nodes.index != 1503720022] #Unconnected node
nodes = nodes.loc[nodes.index != 1732975079] #Unconnected node
nodes = nodes.loc[nodes.index != 4210318680] #Unconnected node
nodes = nodes.loc[nodes.index != 4209636546] #Unconnected node
nodes = nodes.loc[nodes.index != 1366882580] #Unconnected node
nodes = nodes.loc[nodes.index != 1366882584] #Unconnected node
nodes = nodes.loc[nodes.index != 618337110] #Unconnected node
nodes = nodes.loc[nodes.index != 6138893747] #Unconnected node
nodes = nodes.loc[nodes.index != 6138893748] #Unconnected node
nodes = nodes.loc[nodes.index != 6138893757] #Unconnected node
nodes = nodes.loc[nodes.index != 6138893752] #Unconnected node
nodes = nodes.loc[nodes.index != 6138893755] #Unconnected node
nodes = nodes.loc[nodes.index != 6138893750] #Unconnected node
nodes = nodes.loc[nodes.index != 4574848710] #Unconnected node
nodes = nodes.loc[nodes.index != 4574848712] #Unconnected node
nodes = nodes.loc[nodes.index != 3635805273] #Unconnected node
nodes = nodes.loc[nodes.index != 4574848479] #Unconnected node
nodes = nodes.loc[nodes.index != 4574848478] #Unconnected node
nodes = nodes.loc[nodes.index != 4574848480] #Unconnected node
nodes = nodes.loc[nodes.index != 3639506569] #Unconnected node
nodes = nodes.loc[nodes.index != 3639506573] #Unconnected node

edges = edges.loc[(edges["from"] != 1503720022) & (edges["to"] != 1732975079)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 4210318680) & (edges["to"] != 4209636546)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 1366882580) & (edges["to"] != 1366882584)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 1366882584) & (edges["to"] != 1366882580)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 1366882580) & (edges["to"] != 618337110)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 618337110) & (edges["to"] != 1366882584)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 6138893755) & (edges["to"] != 6138893750)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 6138893752) & (edges["to"] != 6138893755)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 6138893757) & (edges["to"] != 6138893752)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 6138893757) & (edges["to"] != 6138893748)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 6138893748) & (edges["to"] != 6138893747)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 3639506573) & (edges["to"] != 4574848479)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 4574848479) & (edges["to"] != 4574848478)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 4574848478) & (edges["to"] != 4574848480)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 3639506569) & (edges["to"] != 4574848480)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 4574848712) & (edges["to"] != 4574848478)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 4574848712) & (edges["to"] != 3635805273)] #Connecting edge between unconnected nodes
edges = edges.loc[(edges["from"] != 4574848710) & (edges["to"] != 4574848712)] #Connecting edge between unconnected nodes

# ERKLÄRUNG: Auskommentierter Hilfsblock: Netz als GeoDataFrame/CSV exportieren.
#             Wird nicht gebraucht. GRAZ: entfällt (ox.graph_to_gdfs(G) kann das).
'''
# IF NEEDED Make Geodataframes both from edges and nodes using the x and y coordinate columns. Write as csv
nodes_gdf = gpd.GeoDataFrame(nodes, geometry=gpd.points_from_xy(nodes.x, nodes.y))
nodes_gdf.reset_index(inplace=True)
edges_gdf = edges.merge(nodes_gdf[["id", "geometry"]], how='left', left_on="from", right_on="id")
edges_gdf = edges_gdf.merge(nodes_gdf[["id", "geometry"]], how='left', left_on="to", right_on="id")
edges_gdf['geom'] =edges_gdf.apply(lambda row: LineString([row['geometry_x'], row['geometry_y']]), axis=1) #Create a linestring column
edges_gdf.drop(["id_x", "id_y", "geometry_x", "geometry_y"], 1, inplace=True)

outfp_nodes_gdf = "nodes_gdf.csv"
outfp_edges_gdf = "edges_gdf.csv"

nodes_gdf.to_csv(outfp_nodes_gdf, sep=";")
edges_gdf.to_csv(outfp_edges_gdf, sep=";")
'''
# ERKLÄRUNG: Baut das Pandana-Netz: Knoten (x, y), Kanten (from, to), Gewicht =
#             Länge in Metern. Pandana arbeitet intern mit Contraction Hierarchies
#             und ist dadurch sehr schnell für Millionen von Routen.
# GRAZ:      Wir verwenden den NetworkX-Graphen G direkt, Gewicht = 'length'.
#Make the graph (network) file
network = pandana.Network(nodes['x'], nodes['y'], edges['from'], edges['to'], edges[['distance']])

# ERKLÄRUNG: Wendet Funktion 1 an: Jede Zelle und jeder Supermarkt bekommt node_id.
#             Beide Raster-Varianten (Bevölkerung und MetropAccess) werden zugeordnet.
# GRAZ:      pop['node']   = ox.distance.nearest_nodes(G, pop.geometry.x, pop.geometry.y)
#             shops['node'] = ox.distance.nearest_nodes(G, shops.geometry.x, shops.geometry.y)
#Search the nearest node id for every population centroid and grocery store
population_PkSeutu_2020 = nearestNodeID(population_PkSeutu_2020)
metropAccessCentroids_PkSeutu = nearestNodeID(metropAccessCentroids_PkSeutu)

groceries_PKSeutu_2022_17 = nearestNodeID(groceries_PKSeutu_2022_17)
groceries_PKSeutu_2022_06 = nearestNodeID(groceries_PKSeutu_2022_06)

# ERKLÄRUNG: Wendet Funktion 2 an: eindeutige Knoten für Start und Ziel.
# Create two new dataframes with unique population and grocery store node ids
nodes_unique_population2020 = getUniqueNodes(population_PkSeutu_2020)
nodes_unique_metropAccessCentroids = getUniqueNodes(metropAccessCentroids_PkSeutu)

nodes_unique_groceries_2022_17 = getUniqueNodes(groceries_PKSeutu_2022_17)
nodes_unique_groceries_2022_06 = getUniqueNodes(groceries_PKSeutu_2022_06)

# ERKLÄRUNG: Auskommentiert: dieselbe Rechnung mit dem BEVÖLKERUNGSRASTER.
#             Aktiv ist darunter die Variante mit dem MetropAccess-Raster.
# PROBLEM:   Das Abbildungs-Skript liest aber die Ergebnisse der Bevölkerungs-
#             Variante (rttk2020_...gpkg). Der Code im Repo ist also NICHT der
#             Stand, mit dem die Abbildungen im Paper erzeugt wurden.
'''
# Create a list of origin node ids and destination node ids
origsGrocery_2022_17 = [o for o in nodes_unique_population2020 for d in nodes_unique_groceries_2022_17]
destsGrocery_2022_17 = [d for o in nodes_unique_population2020 for d in nodes_unique_groceries_2022_17]

origsGrocery_2022_06 = [o for o in nodes_unique_population2020 for d in nodes_unique_groceries_2022_06]
destsGrocery_2022_06 = [d for o in nodes_unique_population2020 for d in nodes_unique_groceries_2022_06]
'''
# Create a list of origin node ids and destination node ids
# ERKLÄRUNG: Bildet ALLE Kombinationen Startknoten x Supermarktknoten:
#             origs = [Start1, Start1, ..., Start2, Start2, ...]
#             dests = [Markt1, Markt2, ..., Markt1, Markt2, ...]
#             Bei ~13.000 Zellen x 395 Märkten sind das ~5 Mio. Paare.
origsGrocery_2022_17 = [o for o in nodes_unique_metropAccessCentroids for d in nodes_unique_groceries_2022_17]
destsGrocery_2022_17 = [d for o in nodes_unique_metropAccessCentroids for d in nodes_unique_groceries_2022_17]

origsGrocery_2022_06 = [o for o in nodes_unique_metropAccessCentroids for d in nodes_unique_groceries_2022_06]
destsGrocery_2022_06 = [d for o in nodes_unique_metropAccessCentroids for d in nodes_unique_groceries_2022_06]

# ERKLÄRUNG: HERZSTÜCK: Pandana berechnet für jedes Paar die kürzeste Weglänge
#             im Fußwegnetz (in Metern). Danach wird daraus eine Tabelle
#             from_id | to_id | distance_17 (bzw. distance_06).
# PROBLEM:   Sehr rechenintensiv, obwohl nur der NÄCHSTE Supermarkt gebraucht wird.
# GRAZ:      Eine einzige Suche, die von ALLEN offenen Supermärkten gleichzeitig
#             startet. Liefert für jeden Netzknoten die Distanz zum nächsten Markt:
#             dist_17 = nx.multi_source_dijkstra_path_length(
#                           G, set(shops.loc[shops.offen_17, 'node']), weight='length')
#             pop['dist_17'] = pop['node'].map(dist_17)
#             Gleiches Ergebnis wie hier (Fußwege sind in beide Richtungen begehbar),
#             aber viel schneller. Für 07 Uhr analog.
# Find the shortest distance between all the population centroids and all different grocery locations. Make origin-destaination dataframe of the result
routesGrocery_2022_17 = network.shortest_path_lengths(origsGrocery_2022_17, destsGrocery_2022_17)
routesDF_Grocery_2022_17 = pd.DataFrame(list(zip(origsGrocery_2022_17, destsGrocery_2022_17, routesGrocery_2022_17)))
routesDF_Grocery_2022_17.rename(columns={0: "from_id", 1:"to_id", 2:"distance_17"},inplace=True)

routesGrocery_2022_06 = network.shortest_path_lengths(origsGrocery_2022_06, destsGrocery_2022_06)
routesDF_Grocery_2022_06 = pd.DataFrame(list(zip(origsGrocery_2022_06, destsGrocery_2022_06, routesGrocery_2022_06)))
routesDF_Grocery_2022_06.rename(columns={0: "from_id", 1:"to_id", 2:"distance_06"},inplace=True)

# ERKLÄRUNG: Auskommentiert: Verknüpfung für die Bevölkerungsraster-Variante.
'''
# Join the population data, grocery and accessibility data  to the origin-destination dataframe. Filter and rename columns
routesDF_Grocery_2022_17_joined = population_PkSeutu_2020.merge(routesDF_Grocery_2022_17, how='outer', left_on="node_id", right_on="from_id")
routesDF_Grocery_2022_17_joined = routesDF_Grocery_2022_17_joined.merge(groceries_PKSeutu_2022_17, how='left', left_on="to_id", right_on="node_id")
routesDF_Grocery_2022_17_joined = routesDF_Grocery_2022_17_joined[["id_nro", "id",  'name', 'shop',"distance_17"]]
routesDF_Grocery_2022_17_joined.rename(columns={"id":"groceryID","name":"shopName", "shop":"shopType"}, inplace=True)

routesDF_Grocery_2022_06_joined = population_PkSeutu_2020.merge(routesDF_Grocery_2022_06, how='outer', left_on="node_id", right_on="from_id")
routesDF_Grocery_2022_06_joined = routesDF_Grocery_2022_06_joined.merge(groceries_PKSeutu_2022_06, how='left', left_on="to_id", right_on="node_id")
routesDF_Grocery_2022_06_joined = routesDF_Grocery_2022_06_joined[["id_nro", "id",  'name', 'shop',"distance_06"]]
routesDF_Grocery_2022_06_joined.rename(columns={"id":"groceryID","name":"shopName", "shop":"shopType"}, inplace=True)
'''

# Join the metropAccess data, grocery and accessibility data  to the origin-destination dataframe. Filter and rename columns
# ERKLÄRUNG: Verknüpft die Routentabelle mit den Rasterzellen (über den Startknoten)
#             und mit den Supermärkten (über den Zielknoten), behält nur ID, Name,
#             Typ und Distanz.
# GRAZ:      Entfällt, weil der Multi-Source-Dijkstra die Distanz direkt pro Knoten
#             liefert und wir sie per .map() an die Zellen hängen.
routesDF_Grocery_2022_17_joined = metropAccessCentroids_PkSeutu.merge(routesDF_Grocery_2022_17, how='outer', left_on="node_id", right_on="from_id")
routesDF_Grocery_2022_17_joined = routesDF_Grocery_2022_17_joined.merge(groceries_PKSeutu_2022_17, how='left', left_on="to_id", right_on="node_id")
routesDF_Grocery_2022_17_joined = routesDF_Grocery_2022_17_joined[["YKR_ID", "id",  'name', 'shop',"distance_17"]]
routesDF_Grocery_2022_17_joined.rename(columns={"id":"groceryID","name":"shopName", "shop":"shopType"}, inplace=True)

routesDF_Grocery_2022_06_joined = metropAccessCentroids_PkSeutu.merge(routesDF_Grocery_2022_06, how='outer', left_on="node_id", right_on="from_id")
routesDF_Grocery_2022_06_joined = routesDF_Grocery_2022_06_joined.merge(groceries_PKSeutu_2022_06, how='left', left_on="to_id", right_on="node_id")
routesDF_Grocery_2022_06_joined = routesDF_Grocery_2022_06_joined[["YKR_ID", "id",  'name', 'shop',"distance_06"]]
routesDF_Grocery_2022_06_joined.rename(columns={"id":"groceryID","name":"shopName", "shop":"shopType"}, inplace=True)

# ERKLÄRUNG: Auskommentiert: Minimum pro Zelle für die Bevölkerungsraster-Variante.
'''

#See if the results are correct
minDistPop_Grocery_17 = routesDF_Grocery_2022_17_joined.groupby(["id_nro"]).min().reset_index()
minDistPop_Grocery_06 = routesDF_Grocery_2022_06_joined.groupby(["id_nro"]).min().reset_index()
'''

#See if the results are correct
# ERKLÄRUNG: Pro Rasterzelle die kleinste Distanz = Weg zum nächsten Supermarkt.
# PROBLEM:   groupby().min() nimmt das Minimum JEDER SPALTE EINZELN. Die Distanz
#             stimmt, aber shopName/groceryID sind dann das alphabetisch kleinste,
#             nicht das tatsächlich nächste Geschäft.
# GRAZ:      Entfällt (siehe oben). Wenn ihr das nächste Geschäft wissen wollt:
#             nx.multi_source_dijkstra liefert zusätzlich die Pfade.
minDistPop_Grocery_17 = routesDF_Grocery_2022_17_joined.groupby(["YKR_ID"]).min().reset_index()
minDistPop_Grocery_06 = routesDF_Grocery_2022_06_joined.groupby(["YKR_ID"]).min().reset_index()

# ERKLÄRUNG: Sucht Routen > 100 km. Pandana gibt für nicht erreichbare Ziele einen
#             sehr großen Wert zurück.
# PROBLEM:   Die Ausreißer werden nur angesehen, NICHT entfernt.
# GRAZ:      Zellen ohne Distanz (NaN nach .map()) = nicht erreichbar.
#             Zählen, im Bericht nennen, bewusst entscheiden, wie sie zählen.
# See if there's outliers
outliers_Grocery_17 = routesDF_Grocery_2022_17_joined.loc[routesDF_Grocery_2022_17_joined["distance_17"] >100000]
outliers_Grocery_06 = routesDF_Grocery_2022_06_joined.loc[routesDF_Grocery_2022_06_joined["distance_06"] >100000]

# ERKLÄRUNG: Auskommentiert: Median der Gehgeschwindigkeiten und Histogramme.
#             Interessant: Hier wird der MEDIAN berechnet, im Paper steht MITTELWERT.
# GRAZ:      In Notebook 01 Mittelwert UND Median berechnen und vergleichen.
'''
# Walking speed tests
walkingSpeedMeasurementsDRY["Speed (km/h)"].loc[walkingSpeedMeasurementsDRY["Age"]== "Adult"].median()
walkingSpeedMeasurementsDRY["Speed (km/h)"].loc[walkingSpeedMeasurementsDRY["Age"]== "Elderly"].median()
walkingSpeedMeasurementsWINTER["Speed (km/h)"].loc[walkingSpeedMeasurementsWINTER["Age"]== "Adult"].median()
walkingSpeedMeasurementsWINTER["Speed (km/h)"].loc[(walkingSpeedMeasurementsWINTER["Age"]== "Elderly") & (walkingSpeedMeasurementsWINTER["Condition"]== "Gritted ice")].median()

walkingSpeedMeasurementsWINTER["Speed (km/h)"].loc[(walkingSpeedMeasurementsWINTER["Age"]== "Elderly") & (walkingSpeedMeasurementsWINTER["Condition"]== "Gritted ice")].hist()

walkingSpeedMeasurementsDRY["Speed (km/h)"].loc[walkingSpeedMeasurementsDRY["Age"]== "Elderly"].hist()
walkingSpeedMeasurementsDRY["Speed (km/h)"].loc[walkingSpeedMeasurementsDRY["Age"]== "Adult"].hist()
'''

'''
#Join distances to population centroids
population_Grid_PkSeutu_17 = population_grid_PkSeutu.merge(minDistPop_Grocery_17[["id_nro", "distance_17"]], how='left', left_on="id_nro", right_on="id_nro")
population_Grid_PkSeutu_06 = population_grid_PkSeutu.merge(minDistPop_Grocery_06[["id_nro", "distance_06"]], how='left', left_on="id_nro", right_on="id_nro")

#Calculate travel times for certain walking speeds
population_Grid_PkSeutu_17["Adult_speed_dry"] = population_Grid_PkSeutu_17["distance_17"] / 5150 *60
population_Grid_PkSeutu_17["Old_speed_dry"] = population_Grid_PkSeutu_17["distance_17"] / 4260*60
population_Grid_PkSeutu_17["Adult_speed_winter"] = population_Grid_PkSeutu_17["distance_17"] / 4810*60
population_Grid_PkSeutu_17["Old_speed_winter"] = population_Grid_PkSeutu_17["distance_17"] / 3890*60

population_Grid_PkSeutu_06["Adult_speed_dry"] = population_Grid_PkSeutu_06["distance_06"] / 5150 *60
population_Grid_PkSeutu_06["Old_speed_dry"] = population_Grid_PkSeutu_06["distance_06"] / 4260*60
population_Grid_PkSeutu_06["Adult_speed_winter"] = population_Grid_PkSeutu_06["distance_06"] / 4810*60
population_Grid_PkSeutu_06["Old_speed_winter"] = population_Grid_PkSeutu_06["distance_06"] / 3890*60
'''

#Join distances to population centroids
# ERKLÄRUNG: Hängt die kleinste Distanz an die Rasterpolygone (für Karten, Abb. 5).
#             Darüber auskommentiert: dasselbe für das Bevölkerungsraster.
metropAccessGrid_PkSeutu_17 = metropAccessGrid_PkSeutu.merge(minDistPop_Grocery_17[["YKR_ID", "distance_17"]], how='left', left_on="YKR_ID", right_on="YKR_ID")
metropAccessGrid_PkSeutu_06 = metropAccessGrid_PkSeutu.merge(minDistPop_Grocery_06[["YKR_ID", "distance_06"]], how='left', left_on="YKR_ID", right_on="YKR_ID")

#Calculate travel times for certain walking speeds
# ERKLÄRUNG: DIE 8 MODELLE: Gehzeit [min] = Distanz [m] / Geschwindigkeit [m/h] * 60
#               Adult_speed_dry    5150 m/h  (Erwachsene, trocken)
#               Old_speed_dry      4260 m/h  (über 65, trocken)
#               Adult_speed_winter 4810 m/h  (Erwachsene, Winter)
#               Old_speed_winter   3890 m/h  (über 65, Winter)
#             x 2 Uhrzeiten (_17 und _06) = 8 Modelle.
# PROBLEM:   Laut Paper ist der Winterwert der Mittelwert der 3 Winterzustände.
#             Aus Tabelle 1: Erwachsene ca. 4790 (einfach) bzw. 4890 (gewichtet),
#             Ältere ca. 3980 bzw. 4100 m/h. Hier stehen 4810 und 3890.
#             -> Mit den CSVs nachrechnen und in der Kritik erwähnen.
# GRAZ:      Werte aus unserem Notebook 01 (speeds.csv), als Schleife statt
#             8 kopierter Zeilen:
#             for zeit in ['17', '07']:
#                 for name, kmh in speeds.items():
#                     pop[f'min_{name}_{zeit}'] = pop[f'dist_{zeit}'] / (kmh * 1000 / 60)
metropAccessGrid_PkSeutu_17["Adult_speed_dry"] = metropAccessGrid_PkSeutu_17["distance_17"] / 5150 *60
metropAccessGrid_PkSeutu_17["Old_speed_dry"] = metropAccessGrid_PkSeutu_17["distance_17"] / 4260*60
metropAccessGrid_PkSeutu_17["Adult_speed_winter"] = metropAccessGrid_PkSeutu_17["distance_17"] / 4810*60
metropAccessGrid_PkSeutu_17["Old_speed_winter"] = metropAccessGrid_PkSeutu_17["distance_17"] / 3890*60

metropAccessGrid_PkSeutu_06["Adult_speed_dry"] = metropAccessGrid_PkSeutu_06["distance_06"] / 5150 *60
metropAccessGrid_PkSeutu_06["Old_speed_dry"] = metropAccessGrid_PkSeutu_06["distance_06"] / 4260*60
metropAccessGrid_PkSeutu_06["Adult_speed_winter"] = metropAccessGrid_PkSeutu_06["distance_06"] / 4810*60
metropAccessGrid_PkSeutu_06["Old_speed_winter"] = metropAccessGrid_PkSeutu_06["distance_06"] / 3890*60

# ERKLÄRUNG: Wendet Funktion 3 an (Gehzeiten für 3,0-7,0 km/h).
# PROBLEM:   Für die 06-Tabelle -> KeyError (siehe Funktion 3).
# GRAZ:      Für unsere Sensitivitätsanalyse: Anteil der Bevölkerung <= 15 min
#             für jede Geschwindigkeit von 3,0 bis 6,0 km/h -> eine Kurve.
#Calculate travel times for  walking speeds ranging nfrom 3.0 to 7.0 at 0.1 interval
calculateWalkingTimes(routesDF_Grocery_2022_17_joined)
calculateWalkingTimes(routesDF_Grocery_2022_06_joined)

# ERKLÄRUNG: Wendet Funktion 4 an (mittlere Anzahl Märkte in 15 min).
# PROBLEM:   KeyError 'id_nro' (siehe Funktion 4).
reachableUnder15_17 = calculateReachableStores(routesDF_Grocery_2022_17_joined)
reachableUnder15_06 = calculateReachableStores(routesDF_Grocery_2022_06_joined)

# ERKLÄRUNG: Zurück ins finnische Koordinatensystem ETRS-TM35FIN (EPSG:3067).
# GRAZ:      Wir bleiben durchgehend in EPSG:32633.
#Convert coordinate system back to original
'''
population_Grid_PkSeutu_17 = population_Grid_PkSeutu_17.to_crs(epsg=3067)
population_Grid_PkSeutu_06 = population_Grid_PkSeutu_06.to_crs(epsg=3067)
'''
metropAccessGrid_PkSeutu_17 = metropAccessGrid_PkSeutu_17.to_crs(epsg=3067)
metropAccessGrid_PkSeutu_06 = metropAccessGrid_PkSeutu_06.to_crs(epsg=3067)

# ERKLÄRUNG: Speichert die Ergebnisse als GeoPackage. Diese Dateien liest das
#             Abbildungs-Skript ein.
# GRAZ:      data/processed/results.gpkg (eine Datei, alle Modelle als Spalten).
# Write Oot
'''
population_Grid_PkSeutu_17.to_file("Data\\rttk2020_grocery_22_17.gpkg", driver="GPKG")
population_Grid_PkSeutu_06.to_file("Data\\rttk2020_grocery_22_06.gpkg", driver="GPKG")
'''
metropAccessGrid_PkSeutu_17.to_file("Data\\metropAccessGrid_grocery_22_17.gpkg", driver="GPKG")
metropAccessGrid_PkSeutu_06.to_file("Data\\metropAccessGrid_grocery_22_06.gpkg", driver="GPKG")



# ============================================================================
# TEIL 2: EINZUGSGEBIETE (Abb. 6 im Paper), optional für Graz
# ============================================================================
# ERKLÄRUNG: Ab einem Startpunkt wird gezeigt, wie weit man in 15 min kommt -
#             für 8 Geschwindigkeiten (20./40./60./80. Perzentil von Erwachsenen
#             trocken und Älteren im Winter).
# PROBLEM:   Der folgende Block ist EINGERÜCKT, ohne if/def davor ->
#             IndentationError. Wegen dieses Fehlers lässt sich das GESAMTE
#             Skript nicht starten, auch nicht Teil 1.
#### Service area analysis with osmnx and networkx ####
# From here
    # PROBLEM:   network_type = 'all' (alle Wege inkl. Straßen), oben in Teil 1 aber
    #             ein reines Fußwegnetz -> zwei verschiedene Netze in einer Studie.
    # GRAZ:      Unser G aus Teil 1 wiederverwenden (network_type='walk').
    place = 'Helsinki, Finland'
    network_type = 'all'
    trip_times =  [15] #in minutes
    # ERKLÄRUNG: Perzentile der gemessenen Geschwindigkeiten in km/h, fest eingetippt.
    # GRAZ:      Selbst aus den CSVs berechnen:
    #             dry.loc[dry.Age == 'Adult', 'Speed (km/h)'].quantile([.2, .4, .6, .8])
    travel_speed_Adult_20_summer = 4.50 #walking speed in km/hour
    travel_speed_Adult_40_summer = 4.97
    travel_speed_Adult_60_summer = 5.33
    travel_speed_Adult_80_summer = 5.85
    travel_speed_Old_20_winter = 3.43
    travel_speed_Old_40_winter = 4.00
    travel_speed_Old_60_winter =4.24
    travel_speed_Old_80_winter = 4.74

    # download the street network
    # ERKLÄRUNG: Lädt das Netz für Helsinki neu aus OSM.
    G = ox.graph_from_place(place, network_type=network_type)

    # find the centermost node and then project the graph to UTM
    gdf_nodes = ox.graph_to_gdfs(G, edges=False)
    # ERKLÄRUNG: Berechnet den Mittelpunkt aller Knoten - wird danach aber gar nicht
    #             verwendet (Startpunkt ist Vallila).
    # PROBLEM:   unary_union ist in neueren geopandas-Versionen veraltet (union_all()).
    x, y = gdf_nodes['geometry'].unary_union.centroid.xy
    # ERKLÄRUNG: Nächster Knoten zum Startpunkt Vallila (Achtung: (y, x)-Reihenfolge).
    # PROBLEM:   ox.get_nearest_node gibt es in OSMnx 2.x nicht mehr.
    # GRAZ:      start = ox.distance.nearest_nodes(G, x, y)  (Reihenfolge x, y!)
    startNode = ox.get_nearest_node(G, (serviceAreaStartPointVALLILA.iloc[0].geometry.y, serviceAreaStartPointVALLILA.iloc[0].geometry.x))
    G = ox.project_graph(G)

    # add an edge attribute for time in minutes required to traverse each edge
    # ERKLÄRUNG: Jede Kante bekommt eine Gehzeit in Minuten als Attribut 'time'.
    # PROBLEM:   Die Geschwindigkeit ist fest eingetippt. Für jede der 8 Varianten
    #             wurde offenbar die Zeile von Hand geändert und neu ausgeführt.
    # GRAZ:      Schleife über die 8 Geschwindigkeiten.
    meters_per_minute = travel_speed_Old_80_winter * 1000 / 60 #km per hour to m per minute
    for u, v, k, data in G.edges(data=True, keys=True):
        data['time'] = data['length'] / meters_per_minute

    # ERKLÄRUNG: Erzeugt das Einzugsgebiet als Polygon:
    #             1) nx.ego_graph: alle Knoten, die innerhalb von trip_time Minuten
    #                (Gewicht 'time') vom Startknoten erreichbar sind
    #             2) Knoten (node_buff) und Kanten (edge_buff = 25 m) puffern
    #             3) alles vereinigen; infill=True füllt Löcher im Polygon
    #             Das ist fast 1:1 ein Beispiel aus den OSMnx-Tutorials (Isochronen).
    # GRAZ:      Kann weitgehend übernommen werden. unary_union -> union_all(),
    #             G.get_edge_data(...)[0] funktioniert weiterhin.
    def make_iso_polys(G, edge_buff=25, node_buff=50, infill=False):
        isochrone_polys = []
        for trip_time in sorted(trip_times, reverse=True):
            subgraph = nx.ego_graph(G, startNode, radius=trip_time, distance='time')

            node_points = [Point((data['x'], data['y'])) for node, data in subgraph.nodes(data=True)]
            nodes_gdf = gpd.GeoDataFrame({'id': subgraph.nodes()}, geometry=node_points)
            nodes_gdf = nodes_gdf.set_index('id')

            edge_lines = []
            for n_fr, n_to in subgraph.edges():
                f = nodes_gdf.loc[n_fr].geometry
                t = nodes_gdf.loc[n_to].geometry
                edge_lookup = G.get_edge_data(n_fr, n_to)[0].get('geometry', LineString([f, t]))
                edge_lines.append(edge_lookup)

            n = nodes_gdf.buffer(node_buff).geometry
            e = gpd.GeoSeries(edge_lines).buffer(edge_buff).geometry
            all_gs = list(n) + list(e)
            new_iso = gpd.GeoSeries(all_gs).unary_union

            # try to fill in surrounded areas so shapes will appear solid and blocks without white space inside them
            if infill:
                new_iso = Polygon(new_iso.exterior)
            isochrone_polys.append(new_iso)
        return isochrone_polys

    isochrone_polys = make_iso_polys(G, edge_buff=25, node_buff=0, infill=True)

    # ERKLÄRUNG: Speichert das Polygon. CRS 'EPSG:32635' = UTM 35N (Helsinki).
    # GRAZ:      EPSG:32633 (UTM 33N) für Graz.
    for polygon in isochrone_polys:
        gdf = gpd.GeoDataFrame(index=[0], crs='EPSG:32635', geometry=[polygon])
        gdf.to_file("Data\\ServiceAreaVALLILA_"+str(travel_speed_Old_80_winter)+".gpkg", driver="GPKG")


#If need to create a geopackage of the graph
# ERKLÄRUNG: Exportiert das Netz als GeoPackage (z. B. zum Ansehen in QGIS).
# GRAZ:      ox.save_graph_geopackage(G, 'data/processed/walk_network.gpkg')
ox.io.save_graph_geopackage(G, filepath="Data\\OSMNX_graph.gpkg", encoding='utf-8', directed=False) 
