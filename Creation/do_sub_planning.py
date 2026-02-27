# Created 9/4/23 by Adam Birchfield for building the new ei70k case
# Copied 5/27/24 by Adam Birchfield for building new ei70k case
# Edited 2/26/2026 by Sanjana K for building new Texas case

import os
from time import time
from numpy.random import random

from sklearn.cluster import KMeans
import geopandas as gpd

from gridworkbench.containers import Bus, Node
from gridworkbench.utils import geograph

from sgb_suite.syntheticgridbuilder import SyntheticGridBuilder
from sgb_suite.sub_planning import LoadFragment
from sgb_suite.sub_planning import GenFragment, GenUnit


tlap = time()
def lap(txt): global tlap; print(txt + f" | {time()-tlap} secs"); tlap=time()

def do_sub_planning_70k():

    sgb = SyntheticGridBuilder("texas_config.txt")


    # Read CSV Files
    #TODO: Change these to ERCOT inputs
    census2020_geo = sgb.read_csv(rf"{sgb.input_folder}\2022_Gaz_tracts_national\2022_Gaz_tracts_national.csv")
    census2020_pop = sgb.read_csv(rf"{sgb.input_folder}\DECENNIALDP2020.DP1_2023-08-29T115315\DECENNIALDP2020.DP1-Data-clean.csv")
    eia860_2022_plants = sgb.read_csv(rf"{sgb.input_folder}\eia8602022ER\2___Plant_Y2022_Early_Release.csv")
    eia860_2022_gens_operable = sgb.read_csv(rf"{sgb.input_folder}\eia8602022ER\3_1_Generator_Y2022_Early_Release-Operable.csv")
    eia860_2022_gens_planned = sgb.read_csv(rf"{sgb.input_folder}\eia8602022ER\3_1_Generator_Y2022_Early_Release-Planned.csv")
    #city_centers = sgb.read_csv(rf"{sgb.input_folder}\cities.csv")
    #mountain_bounds = sgb.read_csv(rf"{sgb.input_folder}\mountains.csv")

    # Read ShapeFiles
    db_lake_bounds = gpd.read_file(rf"{sgb.input_folder}\GL230521_lam\GL230521_lam.shp")
    db_lake_bounds.to_crs('epsg:4326', inplace=True)
    lake_bounds = []
    for i in range(db_lake_bounds.shape[0]):
        lake_bounds.append(db_lake_bounds.iloc[i]["geometry"])
    db_coasts = gpd.read_file(rf"{sgb.input_folder}\wb_coastlines_10m\WB_Coastlines_10m\WB_Coastlines_10m.shp")
    coasts = []
    for i in range(db_coasts.shape[0]):
        coasts.append(db_coasts.iloc[i]["geometry"])

    # Read KML File
    ei_boundary = []
    with open(rf"{sgb.input_folder}\EI_Boundary.kml") as f:
        while f.readline().strip() != "<coordinates>": continue
        while True:
            line = f.readline().strip()
            if line == "</coordinates>": break
            lineparts = line.split()
            for part in lineparts:
                coords = [float(x) for x in part.split(',')[:2]]
                ei_boundary.append(coords)

    lap("Files loaded in")

    # TODO: Change these to weather zones or load zones - check with Dr. B
    state_map = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", 
                "CA": "California", "CO": "Colorado", "CT": "Connecticut", 
                "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", 
                "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", 
                "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", 
                "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", 
                "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", 
                "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
                "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", 
                "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", 
                "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", 
                "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", 
                "PR": "Puerto Rico", "RI": "Rhode Island", "SC": "South Carolina", 
                "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", 
                "VT": "Vermont", "VA": "Virginia", "VI": "Virgin Islands", 
                "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", 
                "WY": "Wyoming", "AB": "Alberta", "BC": "British Columbia",
                "SK": "Saskatchewan", "MB": "Manitoba", "ON": "Ontario",
                "QC": "Quebec", "NB": "New Brunswick", "NL": "Newfoundland",
                "NS": "Nova Scotia", "PE": "Prince Edward Island"}

    # Create load fragments from input data
    sgb.load_frags = []
    #name_dict = {}
    for geo, pop in zip(census2020_geo, census2020_pop):
        #if len(sgb.load_frags) > 100: continue
        lf = LoadFragment()
        lf.lat = float(geo['INTPTLAT'])
        lf.lon = float(geo['INTPTLONG'])
        lf.area = state_map[geo["USPS"]]

        # Filter by EI boundary
        nright = 0
        for i in range(len(ei_boundary)-1):
            x1, y1 = ei_boundary[i]
            x2, y2 = ei_boundary[i+1]
            if lf.lat < min(y1, y2) or lf.lat > max(y1, y2) or lf.lon > max(x1, x2) \
                    or y1 == y2: continue
            lon2 = (lf.lat - y1) * (x2 - x1) / (y2 - y1) + x1
            if lon2 < lf.lon: continue
            nright += 1
        if nright % 2 == 0:
            continue

        lf.p = float(pop['DP1_0001C']) * 0.0021
        if lf.p < 0.25: continue
        name_parts = pop['NAME'].split(';')
        tract_num = name_parts[0].split()[-1]
        county_name = name_parts[1][:-7]
        lf.name = county_name + "-" + geo['USPS'] + '-' + tract_num
        sgb.load_frags.append(lf)

    lap(f"Created {len(sgb.load_frags)} USA load fragments")

    # Perhaps for larger ones, split into smaller fragments inside coastline bounds

    # Create generator fragments from input data
    plant_map = {}
    for plant in eia860_2022_plants:
        if plant["Latitude"] == "": continue
        gf = GenFragment(name=plant["Plant Name"],
            lat=float(plant["Latitude"]),
            lon=float(plant["Longitude"]),
            plant_code = plant["Plant Code"],
            area = state_map[plant["State"]],
            units = []
        )
        
        # Filter by EI boundary
        nright = 0
        for i in range(len(ei_boundary)-1):
            x1, y1 = ei_boundary[i]
            x2, y2 = ei_boundary[i+1]
            if gf.lat < min(y1, y2) or gf.lat > max(y1, y2) or gf.lon > max(x1, x2) \
                    or y1 == y2: continue
            lon2 = (gf.lat - y1) * (x2 - x1) / (y2 - y1) + x1
            if lon2 < gf.lon: continue
            nright += 1
        if nright % 2 == 0:
            continue

        plant_map[plant["Plant Code"]] = gf

    for gen in eia860_2022_gens_operable + eia860_2022_gens_planned:
        if gen["Plant Code"] not in plant_map: continue
        gf = plant_map[gen["Plant Code"]]
        tech = gen["Technology"]
        pmax = float(gen["Summer Capacity (MW)"].strip('"')) \
            if len(gen["Summer Capacity (MW)"]) != 0 \
                else float(gen["Nameplate Capacity (MW)"].strip('"'))
        has_pmin = "Minimum Load (MW)" in gen and len(gen["Minimum Load (MW)"]) > 0
        pmin = float(gen["Minimum Load (MW)"].strip('"')) if has_pmin else 0
        if "Current Year" in gen:
            if float(gen["Current Year"].strip('"')) >= 2024: continue
        else:
            if gen["Planned Retirement Year"] != "" and \
                    float(gen["Planned Retirement Year"].strip('"')) < 2024:
                continue
        genunit = GenUnit(fueltype=tech, pmax=pmax, pmin=pmin, 
            unit_id = gen["Generator ID"])
        gf.units.append(genunit)

    sgb.gen_frags = [g for g in plant_map.values() if len(g.units) > 0 
                     and sum(gu.pmax for gu in g.units) > 5]

    lap(f"Created {len(sgb.gen_frags)} USA gen fragments")

    print(f"Total gen units {sum(len(g.units) for g in sgb.gen_frags)}")
    gen_cap_total = sum(sum(gu.pmax for gu in g.units) for g in sgb.gen_frags)
    print(f"Total gen capacity {gen_cap_total}")

    # Pre-processing
    sgb.assign_load_q()
    for g in sgb.gen_frags:
        for gu in g.units: gu.sbase = round(gu.pmax/.9, 1)
    sgb.convert_gen_fuel()
    sgb.assign_gen_qlims()
    sgb.assign_gen_cost()

    # Correct areas from just the states
    #TODO: Change these to Texas areas
    area_split = {
        "Ontario": ["Lat", 44.2],
        "New York": ["Lat", 41.3, 43.5],
        "New Jersey": ["Lat", 40.15],
        "Pennsylvania": ["Lon", -79.2, -76],
        "Virginia": ["Lon", -78],
        "North Carolina": ["Lon", -80],
        "Georgia": ["Lat", 33.2],
        "Florida": ["Lat", 27, 29.55],
        "Alabama": ["Lat", 32.7],
        "Tennessee": ["Lon", -85.9],
        "Ohio": ["Lat", 40.4],
        "Michigan": ["Lat", 43.4],
        "Illinois": ["Lat", 41.2],
        "Minnesota": ["Lat", 45.3],
        "Missouri": ["Lon", -92.4]
    }
    for frag in sgb.gen_frags + sgb.load_frags:
        if frag.area == "Texas":
            if frag.lon < -98:
                frag.area = "New Mexico and Texas Panhandle"
            else:
                frag.area = "Far East Texas"
        if frag.area == "New Mexico":
            frag.area = "New Mexico and Texas Panhandle"
        if frag.area == "District of Columbia":
            frag.area = "Maryland"
        if frag.area == "Quebec":
            if frag.lon < -72:
                frag.area = "Ontario"
            else:
                frag.area = "New Brunswick"
        if frag.area == "Canada":
            if frag.lon < -95.1:
                frag.area = "Manitoba"
            elif frag.lon < -72:
                frag.area = "Ontario"
            else:
                frag.area = "New Brunswick"
        if frag.area == "Montana":
            frag.area = "North Dakota"
        if frag.area == "Alberta":
            frag.area = "Saskatchewan"
        if frag.area == "Newfoundland and Labrador":
            if frag.lon < -102:
                frag.area = "Saskatchewan"
            else:
                frag.area = "Manitoba"
        if frag.area in area_split:
            instr = area_split[frag.area]
            for i in range(1, len(instr)):
                if instr[0] == "Lat":
                    if frag.lat < instr[i]:
                        frag.area += f" {i}"
                        break
                else:
                    if frag.lon < instr[i]:
                        frag.area += f" {i}"
                        break
            else:
                frag.area += f" {len(instr)}"
        if frag.area == "Ontario 1":
            if frag.lon < -80: frag.area = "Ontario 3"
        if frag.area == "Ontario 2":
            if frag.lon < -77.85: frag.area = "Ontario 4"
        if frag.area == "New York 2":
            if frag.lon < -76.43: frag.area = "New York 4"
            elif frag.lon < -74.71: frag.area = "New York 5"

    sgb.create_areas()

    # Clustering into substations
    sgb.cluster_load_frags(18000) #TODO: what should the cluster load frags number be? - check with Dr. B
    sgb.create_subs_old()

    # Post-processing
    for sub in sgb.syn_subs: sub.kvs = [100]

    # Create power flow case with just substations
    sgb.create_case_old()

    # Kmeans to get EHV planning regions
    subs = sgb.wb.subs
    sub_coords = [(s.longitude, s.latitude) for s in subs]

    nc = 400 #TODO: what should the nc number be? - check with Dr. B

    class EHV_Cluster:
        def __init__(self):
            self.subs = []

    clusters = [EHV_Cluster() for _ in range(nc)]
    km = KMeans(n_clusters=nc, n_init=10).fit(sub_coords)
    lap("Kmeans clustering done")

    for s, c in zip(subs, km.labels_):
        s.is_ehv = False
        s.cluster = c
        clusters[c].subs.append(s)

    # Assign sub EHV identity based on cluster identification
    for c in clusters:
        gen_p = sum(g.pmax for s in c.subs for g in s.gens)
        load_p = sum(l.p for s in c.subs for l in s.loads)
        p = gen_p + load_p
        c.n_ehv = min(10, int(round(p/1500,0)), len(c.subs))
        if p < 1200: c.n_ehv = 0
        c.subs.sort(key=lambda s:sum(-g.pmax for g in s.gens))
        i_ehv = 0
        for sub in c.subs:
            if i_ehv == c.n_ehv: break
            if sum(g.pmax for g in sub.gens) < 300: break
            i_ehv += 1
            sub.is_ehv = True
        while i_ehv < c.n_ehv:
            s = c.subs[int(random()*len(c.subs))]
            if s.is_ehv: continue
            i_ehv += 1
            s.is_ehv = True

    # Specific area specifications - kv levels, regions, region load factor
    # TODO: Update based on Texas areas - check with Dr. B
    kv_areas = {"Indiana":(138,765), "Ohio 1":(138,765), "West Virginia":(138,765), "New Jersey 1":(161,500), "Alabama 1":(161,500), "Alabama 2":(161,500), "Arkansas":(161,500), "Far East Texas":(161,500), "Florida 1":(161,500), "Florida 2":(161,500), "Florida 3":(161,500), "Georgia 1":(161,500), "Georgia 2":(161,500), "Louisiana":(161,500), "Manitoba":(161,500), "Maryland":(161,500), "Minnesota 2":(161,500), "Mississippi":(161,500), "North Carolina 1":(161,500), "North Carolina 2":(161,500), "Ontario 1":(161,500), "Ontario 2":(161,500), "Ontario 3":(161,500), "Ontario 4":(161,500), "Pennsylvania 2":(161,500), "Pennsylvania 3":(161,500), "South Carolina":(161,500), "Tennessee 1":(161,500), "Tennessee 2":(161,500), "Virginia 1":(161,500), "Virginia 2":(161,500), "Connecticut":(138,345), "Delaware":(138,345), "Illinois 1":(138,345), "Illinois 2":(138,345), "Iowa":(138,345), "Kansas":(138,345), "Kentucky":(138,345), "Maine":(138,345), "Massachusetts":(138,345), "Michigan 1":(138,345), "Michigan 2":(138,345), "Minnesota 1":(138,345), "Missouri 1":(138,345), "Missouri 2":(138,345), "Nebraska":(138,345), "New Brunswick":(138,345), "New Hampshire":(138,345), "New Jersey 2":(138,345), "New Mexico and Texas Panhandle":(138,345), "New York 1":(138,345), "New York 2":(138,345), "New York 3":(138,345), "New York 4":(138,345), "New York 5":(138,345), "North Dakota":(138,345), "Nova Scotia":(138,345), "Ohio 2":(138,345), "Oklahoma":(138,345), "Pennsylvania 1":(138,345), "Prince Edward Island":(138,345), "Rhode Island":(138,345), "South Dakota":(138,345), "Vermont":(138,345), "Wisconsin":(138,345), "Saskatchewan":(138,345)}
    area_regions = {"Florida 1":"FLORIDA", "Florida 2":"FLORIDA", "Florida 3":"FLORIDA", "Connecticut":"NEWENG", "Maine":"NEWENG", "Massachusetts":"NEWENG", "New Hampshire":"NEWENG", "Rhode Island":"NEWENG", "Vermont":"NEWENG", "New Brunswick":"MARITIME", "Nova Scotia":"MARITIME", "Prince Edward Island":"MARITIME", "Manitoba":"CENTCAN", "Arkansas":"MIDWEST", "Far East Texas":"MIDWEST", "Illinois 1":"MIDWEST", "Iowa":"MIDWEST", "Louisiana":"MIDWEST", "Michigan 1":"MIDWEST", "Michigan 2":"MIDWEST", "Minnesota 1":"MIDWEST", "Minnesota 2":"MIDWEST", "Wisconsin":"MIDWEST", "New York 1":"NEWYORK", "New York 2":"NEWYORK", "New York 3":"NEWYORK", "New York 4":"NEWYORK", "New York 5":"NEWYORK", "Ontario 1":"ONTARIO", "Ontario 2":"ONTARIO", "Ontario 3":"ONTARIO", "Ontario 4":"ONTARIO", "Delaware":"MIDATL", "Illinois 2":"MIDATL", "Indiana":"MIDATL", "Kentucky":"MIDATL", "Maryland":"MIDATL", "New Jersey 1":"MIDATL", "New Jersey 2":"MIDATL", "Ohio 1":"MIDATL", "Ohio 2":"MIDATL", "Pennsylvania 1":"MIDATL", "Pennsylvania 2":"MIDATL", "Pennsylvania 3":"MIDATL", "Virginia 1":"MIDATL", "Virginia 2":"MIDATL", "West Virginia":"MIDATL", "Saskatchewan":"CENTCAN", "Missouri 1":"SEAST", "Missouri 2":"SEAST", "Tennessee 1":"SEAST", "Tennessee 2":"SEAST", "North Carolina 1":"SEAST", "North Carolina 2":"SEAST", "South Carolina":"SEAST", "Alabama 1":"SEAST", "Alabama 2":"SEAST", "Georgia 1":"SEAST", "Georgia 2":"SEAST", "Mississippi":"SEAST", "Kansas":"PLAINS", "Nebraska":"PLAINS", "New Mexico and Texas Panhandle":"PLAINS", "North Dakota":"PLAINS", "Oklahoma":"PLAINS", "South Dakota":"PLAINS" } 
    region_load_factor = {"FLORIDA": 2.47, "NEWENG": 1.63, "MARITIME": 2.7, "CENTCAN": 3.68, "MIDWEST": 3.31, "NEWYORK": 1.59, "ONTARIO": 1.74, "MIDATL": 2.04, "SEAST": 2.8, "PLAINS": 4.98}
    
    # Scale load by areas
    for s in subs:
        for l in s.loads:
            l.ps *= region_load_factor[area_regions[s.area.name]]/2.1
            l.p = l.ps
            l.qs *= region_load_factor[area_regions[s.area.name]]/2.1
            l.q = l.qs

    for s in subs:
        s.kv_levels = [kv_areas[s.area.name][0]]
        if s.is_ehv:
            s.kv_levels.append(kv_areas[s.area.name][1])

    # Add additional kv levels for cross-area connections
    gg = geograph.GeoGraph(subs)
    gg.Delaunay(1)
    for s in subs:
        for s2 in gg.g.neighbors(s):
            kv2 = s2.kv_levels[0]
            if kv2 in s.kv_levels: continue
            if kv2 >= s.kv_levels[0]: continue
            if random() < 0.1:
                s.kv_levels.append(kv2)
    ehv_subs = [s for s in subs if max(s.kv_levels) > 300]
    gg = geograph.GeoGraph(ehv_subs)
    gg.Delaunay(1)
    for u, v, a in list(gg.g.edges(data=True)):
        if a["dist"] > 250:  # Only keep smaller edges
            gg.g.remove_edge(u, v)
    for s in ehv_subs:
        for s2 in gg.g.neighbors(s):
            kv2 = max(s2.kv_levels)
            if kv2 in s.kv_levels: continue
            if kv2 >= max(s.kv_levels): continue
            if random() < 0.2:
                s.kv_levels.append(kv2)

    busnum = len(sgb.wb.buses)+1
    for s in subs:
        b0 = s.buses[0]
        b0.nominal_kv = s.kv_levels[0]
        b0.name = s.name + f"_{b0.nominal_kv}"
        for kv in s.kv_levels[1:]:
            b = Bus(s, busnum)
            busnum += 1
            b.nominal_kv = kv
            b.name = s.name + f"_{b.nominal_kv}"

    # Move many generators to highest voltage bus
    for s in subs:
        behv = max(s.buses, key=lambda b:b.nominal_kv)
        if behv.nominal_kv < 300: continue
        gens = list(s.gens)
        gens.sort(key=lambda g:g.pmax)
        total_g = 0
        for g in gens:
            total_g += g.pmax
            if total_g >= 300:
                if len(behv.nodes) == 0:
                    n = Node(behv, behv.number)
                    n.name = behv.name
                else:
                    n = behv.nodes[0]
                g.node = n

    # Tell GridWorkbench to push cluster # and EIA 860 data to custom fields
    sgb.wb.pw_instructions["sub.cluster"] = {"pwfield":["CustomInteger:0"],
                "import_from_aux": "int"}
    sgb.wb.pw_instructions["gen.eia860_plant"] = {"pwfield":["CustomString:0"],
                "import_from_aux": "string"}
    sgb.wb.pw_instructions["gen.eia860_generator"] = {"pwfield":["CustomString:1"],
                "import_from_aux": "string"}
    
    sgb.export_aux("Eastern70k_Subs.aux")
