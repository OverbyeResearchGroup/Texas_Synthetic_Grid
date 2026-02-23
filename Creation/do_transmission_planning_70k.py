from time import time
from numpy.random import shuffle
from ctypes import c_int, c_double

from sgb_suite.transmission_iteration_3 import transmission_iteration_3, \
    read_gen_dispatches
from sgb_suite.syntheticgridbuilder import SyntheticGridBuilder

tlap = time()
def lap(txt): global tlap; print(txt + f" | {time()-tlap} secs"); tlap=time()

def do_transmission_planning_70k():

    # Read in pre-planning data and case
    sgb = SyntheticGridBuilder("ei70k_config.txt")
    sgb.wb.setup_engine()
    
    import_case_file = rf"{sgb.output_folder}\Eastern70k_Subs.aux"
    if sgb.config.tp_start == "warm":
        import_case_file = \
            rf"{sgb.output_folder}\Eastern70k_TransmissionPlanning.aux"
    
    sgb.wb.pw_instructions["gen.eia860_plant"] = {"pwfield":["CustomString:0"],
                "import_from_aux": "string"}
    sgb.wb.pw_instructions["gen.eia860_generator"] = {"pwfield":["CustomString:1"],
                "import_from_aux": "string"}
    sgb.wb.import_aux(import_case_file)

    sgb.read_branchstats(fr".\input\branch_stats.csv")

    sgb.read_candidates(rf"{sgb.output_folder}\Candidates.csv")

    read_gen_dispatches(sgb, rf"{sgb.output_folder}\GenDispatch1.csv", 
                            rf"{sgb.output_folder}\GenDispatch2.csv")
    
    # Divide into subnets (new file)
    sgb.create_syn_subnets()

    # Choose slack bus
    blist = list(sgb.wb.buses)
    blist.sort(key=lambda b:sum(g.pmax for g in b.gens))
    sgb.bslack = blist[-1]

    # Initialize sensitivity arrays
    ncand = len(sgb.candidates)
    sgb.mon = (c_int*(len(sgb.subnets)+1))()
    sgb.add1 = (c_int*ncand)()
    sgb.add2 = (c_int*ncand)()
    sgb.s = (c_double*ncand)()
    for i, b in enumerate(sgb.wb.buses): b.engine_i = i
    for i, c in enumerate(sgb.candidates):
        sgb.add1[i] = c.from_bus.engine_i
        sgb.add2[i] = c.to_bus.engine_i
        sgb.s[i] = 0
    
    # Initialize MST + random of D1 to make the total per subnet
    if sgb.config.tp_start == "cold":
        for c in sgb.candidates:
            if c.category == "transformer":
                c.activate()
        for sn in sgb.subnets.values():
            n_active_allow = int(2*len(sn.subs))
            d1_try = []
            for c in sn.candidates:
                if c.dela_dist == 0:
                    c.activate()
                    n_active_allow -= 1
                elif c.dela_dist == 1:
                    d1_try.append(c)
            shuffle(d1_try)
            for c in d1_try:
                if n_active_allow <= 0: break
                if sn.kv < 300 and c.fixed_cost > 300: continue
                c.activate()
                n_active_allow -= 1
    else:
        pass # Warm-start TODO need to set candidates active/values
    lap("Read files and Initialization")

    # MAIN LOOP of iterations
    t_start = time()
    sgb.wb.setup_engine()
    from datetime import datetime
    sgb.print(f"======= Beginning TP Iterations at {datetime.now()} for "
          + f"{sgb.config.time_out_minutes} minute maximum =======")
    for sgb.iTP in range(9999999):
        transmission_iteration_3(sgb)
        if time() - t_start > sgb.config.time_out_minutes*60:
            sgb.print(f"Ending on time out at {(time()-t_start)/60.0:14.1f} minutes")
            break
        try:
            if sgb.iTP % 20 == 0: sgb.wb.export_aux(
                fr"{sgb.output_folder}\temp_{sgb.iTP:04d}.aux")
        except: pass # Occasionally google drive doesn't allow it to write
    sgb.print("======================= FINISHED ITERATIONS =======================")

    sgb.export_aux("Eastern70k_TransmissionPlanning.aux")