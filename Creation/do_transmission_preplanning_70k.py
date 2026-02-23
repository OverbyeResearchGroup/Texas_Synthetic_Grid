import os
from time import time
from random import shuffle
import geopandas as gpd

from gridworkbench.utils.geograph import calc_intersection

from sgb_suite.syntheticgridbuilder import SyntheticGridBuilder

tlap = time()
def lap(txt): global tlap; print(txt + f" | {time()-tlap} secs"); tlap=time()

def do_transmission_preplanning_70k():
    start = time()

    sgb = SyntheticGridBuilder("ei70k_config.txt")

    # Load in old PW case
    sgb.wb.pw_instructions["gen.eia860_plant"] = {"pwfield":["CustomString:0"],
                "import_from_aux": "string"}
    sgb.wb.pw_instructions["gen.eia860_generator"] = {"pwfield":["CustomString:1"],
                "import_from_aux": "string"}
    sgb.wb.import_aux(rf"{sgb.output_folder}\Eastern70k_Subs.aux")
        
    lap("Files loaded in")

    area_regions = {"Florida 1":"FLORIDA", "Florida 2":"FLORIDA", "Florida 3":"FLORIDA", "Connecticut":"NEWENG", "Maine":"NEWENG", "Massachusetts":"NEWENG", "New Hampshire":"NEWENG", "Rhode Island":"NEWENG", "Vermont":"NEWENG", "New Brunswick":"MARITIME", "Nova Scotia":"MARITIME", "Prince Edward Island":"MARITIME", "Manitoba":"CENTCAN", "Arkansas":"MIDWEST", "Far East Texas":"MIDWEST", "Illinois 1":"MIDWEST", "Iowa":"MIDWEST", "Louisiana":"MIDWEST", "Michigan 1":"MIDWEST", "Michigan 2":"MIDWEST", "Minnesota 1":"MIDWEST", "Minnesota 2":"MIDWEST", "Wisconsin":"MIDWEST", "New York 1":"NEWYORK", "New York 2":"NEWYORK", "New York 3":"NEWYORK", "New York 4":"NEWYORK", "New York 5":"NEWYORK", "Ontario 1":"ONTARIO", "Ontario 2":"ONTARIO", "Ontario 3":"ONTARIO", "Ontario 4":"ONTARIO", "Delaware":"MIDATL", "Illinois 2":"MIDATL", "Indiana":"MIDATL", "Kentucky":"MIDATL", "Maryland":"MIDATL", "New Jersey 1":"MIDATL", "New Jersey 2":"MIDATL", "Ohio 1":"MIDATL", "Ohio 2":"MIDATL", "Pennsylvania 1":"MIDATL", "Pennsylvania 2":"MIDATL", "Pennsylvania 3":"MIDATL", "Virginia 1":"MIDATL", "Virginia 2":"MIDATL", "West Virginia":"MIDATL", "Saskatchewan":"CENTCAN", "Missouri 1":"SEAST", "Missouri 2":"SEAST", "Tennessee 1":"SEAST", "Tennessee 2":"SEAST", "North Carolina 1":"SEAST", "North Carolina 2":"SEAST", "South Carolina":"SEAST", "Alabama 1":"SEAST", "Alabama 2":"SEAST", "Georgia 1":"SEAST", "Georgia 2":"SEAST", "Mississippi":"SEAST", "Kansas":"PLAINS", "Nebraska":"PLAINS", "New Mexico and Texas Panhandle":"PLAINS", "North Dakota":"PLAINS", "Oklahoma":"PLAINS", "South Dakota":"PLAINS" } 
    region_subs = {}
    region_transfer2 = {"FLORIDA": -2000, "NEWENG": -2000, "MARITIME": 1000, "CENTCAN": 1000, "MIDWEST": -1000, "NEWYORK": -3000, "ONTARIO": -2000, "MIDATL": -2000, "SEAST": 5000, "PLAINS": 5000}
    for sub in sgb.wb.subs:
        reg = area_regions[sub.area.name]
        if reg not in region_subs: region_subs[reg] = [sub]
        else: region_subs[reg].append(sub)
        for g in sub.gens: g.dispatch_1 = g.dispatch_2 = 0
    for reg in region_subs:
        subs = region_subs[reg]
        shuffle(subs)
        isub = 0
        gen = sum(sum(g.pmax for g in s.gens) for s in subs)
        load = sum(sum(l.p for l in s.loads) for s in subs)
        print(f"{reg} -- {load} -- {gen}")
        if gen < load:
            print("ERROR!!")
        while load > 0:
            for g in subs[isub].gens:
                g.dispatch_1 = min(load, g.pmax)
                load -= g.dispatch_1
            isub = (isub + 1) % len(subs)
        load = sum(sum(l.p for l in s.loads) for s in subs)
        load += region_transfer2[reg] # For second dispatch, include transfers
        while load > 0:
            for g in subs[isub].gens:
                g.dispatch_2 = min(load, g.pmax)
                load -= g.dispatch_2
            isub = (isub + 1) % len(subs)
        
    # Write out the dispatches
    with open(fr"{sgb.output_folder}\GenDispatch1.csv", "w") as f:
        f.write("Gen\nNumber of Bus,ID,GenMW\n")
        for g in sgb.wb.gens:
            f.write(f"{g.bus.number},{g.id},{g.dispatch_1}\n")
    with open(fr"{sgb.output_folder}\GenDispatch2.csv", "w") as f:
        f.write("Gen\nNumber of Bus,ID,GenMW\n")
        for g in sgb.wb.gens:
            f.write(f"{g.bus.number},{g.id},{g.dispatch_2}\n")

    lap("Made dispatches")

    sgb.read_branchstats(rf"{sgb.input_folder}\branch_stats.csv")
    sgb.produce_candidates(combine_kvs=False)

    sgb.candidates = [c for c in sgb.candidates 
        if c.dela_dist==0 or c.row_dist<500] # Eliminate extra-large candidates

    lap("Produced candidates")

    # Read ShapeFiles for lakes and coast
    db_lake_bounds = gpd.read_file(rf"{sgb.input_folder}\GL230521_lam\GL230521_lam.shp")
    db_lake_bounds.to_crs('epsg:4326', inplace=True)
    water_segments = []
    for i in range(db_lake_bounds.shape[0]):
        print(i)
        coords = list(db_lake_bounds.iloc[i]["geometry"].exterior.coords)
        for j in range(len(coords)-1):
            water_segments.append((coords[j],coords[j+1]))
    db_coasts = gpd.read_file(rf"{sgb.input_folder}\wb_coastlines_10m\WB_Coastlines_10m\WB_Coastlines_10m.shp")
    db_coasts.to_crs('epsg:4326', inplace=True)
    ncoasts = db_coasts.shape[0]
    for i in range(db_coasts.shape[0]):
        if i%100 == 0: 
            print(f"{i}/{ncoasts}")
            # break
        coords = list(db_coasts.iloc[i]["geometry"].coords)
        for j in range(len(coords)-1):
            water_segments.append((coords[j],coords[j+1]))
    water_filtered = []
    for (x1,y1),(x2,y2) in water_segments:
        if min(x1,x2) > -50 or max(x1,x2) < -140 or min(y1,y2) > 59 or max(y1,y2) < 22: 
            continue
        water_filtered.append(((x1,y1),(x2,y2)))
    water_filtered.sort(key=lambda coords:min(coords[0][1],coords[1][1]))
    coord_starters = [0 for _ in range(8000)]
    iwater = 0
    for istarter in range(8000):
        y = istarter / 100
        while min(water_filtered[iwater][0][1], water_filtered[iwater][1][1]) < y:
            iwater += 1
            if iwater >= len(water_filtered): 
                iwater = len(water_filtered)-1
                break
        coord_starters[istarter] = iwater

    # Adjust candidate fixed cost by geographic features
    cf = sgb.config
    icount = 0
    for c in sgb.candidates:
        icount += 1
        if icount % 100 == 0: print(f"{icount}/{len(sgb.candidates)}")
        c.fixed_cost = c.row_dist*cf.cost_fixed_mi
        norm_dist = sgb.branchstats[c.kv].NormDist
        if c.row_dist > norm_dist:
            c.fixed_cost += (cf.miles_above_norm_mult-1) * (c.row_dist-norm_dist)
        if c.from_bus.area.number != c.to_bus.area.number: 
            c.fixed_cost *= cf.cost_ehv_interarea_mult
        if c.from_bus.nominal_kv != c.to_bus.nominal_kv:
            c.fixed_cost *= cf.cost_ehv_interkv_mult
        xc1,yc1 = c.from_bus.sub.longitude, c.from_bus.sub.latitude
        xc2,yc2 = c.to_bus.sub.longitude, c.to_bus.sub.latitude
        borders_left = 0
        int_fracts = [0,1]
        start_index = max(0, coord_starters[int((min(yc1,yc2)-.25)*100)]-5)
        end_index = min(len(water_filtered)-1, coord_starters[int((max(yc1,yc2)+.05)*100)]+5)
        for iwater in range(start_index, end_index):
            (x1,y1),(x2,y2) = water_filtered[iwater]
            if min(yc1,yc2) > max(y1,y2) or min(y1,y2) > max(yc1,yc2) \
                or min(x1,x2) > max(xc1,xc2): continue
            if yc1 >= min(y1,y2) and yc1 < max(y1,y2):
                xint = (yc1 - y1) * (x2 - x1) / (y2 - y1) + x1
                if xint < xc1: 
                    borders_left += 1
            intxy = calc_intersection(xc1,yc1,xc2,yc2,x1,y1,x2,y2)
            if intxy is None: continue
            if xc1 == xc2: int_fract = (intxy[1] - yc1) / (yc2-yc1)
            else: int_fract = (intxy[0] - xc1) / (xc2-xc1)
            int_fracts.append(int_fract)
        int_fracts.sort()
        start_water = borders_left % 2 == 0
        c.percent_water = 0
        for i in range(len(int_fracts)-1):
            if start_water and i%2 == 0:
                c.percent_water += int_fracts[i+1]-int_fracts[i]
            elif not start_water and i%2 == 1:
                c.percent_water += int_fracts[i+1]-int_fracts[i]
        c.fixed_cost = c.fixed_cost*(1-c.percent_water + 
            c.percent_water*cf.cost_ehv_water_mult)
        
    lap("Processed candidates")

    sgb.save_candidates(fr"{sgb.output_folder}\Candidates.csv")

    lap("Exported file")
    print(f"Total time {time()-start}")
