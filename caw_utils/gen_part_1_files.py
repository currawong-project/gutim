import os
import csv
import types
from pathlib import Path

import gen_part_files as gpf

SCRIABIN_VEL_TABLE = [ 1, 5,10,16,21,26,32,37,42,48,53,58,64,69,74,80,85,90,96,101,106,112,117,122,127 ]

def get_part_1_cfg( out_score_csv_fname ):

    
    cfg = dict(
        out_dir              = "gutim_1/caw",
        score_pkl_fname      = "gutim_1/output/cache/assign_sustain.pkl",
        seg_list_pkl_fname   = "gutim_1/output/cache/seg_list.pkl",
        base_score_csv_fname = "gutim_1/output/legacy_sf_score.csv",
        preset_json_fname    = "gutim_1/output/new_catalog.json",
        scriabin_scoreL      = [

                                 dict(fname              = "scriabin_74_4/output/legacy_sf_score.csv",
                                      score_pkl_fname    = "scriabin_74_4/output/cache/assign_sustain.pkl",
                                      seg_list_pkl_fname = "scriabin_74_4/output/cache/seg_list.pkl",
                                      section_label      = "Scriabin-3_Op74_4",
                                      beg_meas_correct   = -1,  # transition meas number adjust
                                      end_meas_correct   = -1,
                                      beg_sec_correct    = -0.9, # transition time adjust
                                      end_sec_correct    = 0.5,
                                      rowL               = None,
                                      vel_table          = SCRIABIN_VEL_TABLE),
                                 
                                 dict(fname              = "scriabin_74_3/output/legacy_sf_score.csv",
                                      score_pkl_fname    = "scriabin_74_3/output/cache/assign_sustain.pkl",
                                      seg_list_pkl_fname = "scriabin_74_3/output/cache/seg_list.pkl",
                                      section_label      = "Scriabin-4_Op74_3",
                                      beg_meas_correct   = -1,  # transition meas number adjust
                                      end_meas_correct   = -1,
                                      beg_sec_correct    = -0.9, # transition time adjust
                                      end_sec_correct    = 0.5,
                                      rowL               = None,
                                      vel_table          = SCRIABIN_VEL_TABLE)


                                ],
        
        
        out_score_csv_fname      = out_score_csv_fname,
        out_preset_json_fname    = "presets.json",
        out_mult_play_json_fname = "multi_player.json",
        out_ctl_json_fname       = "pgm_ctl.json",
        out_toc_json_fname       = "toc.json")        

    

    cfg = types.SimpleNamespace(**cfg)

    cfg.out_dir = Path(cfg.out_dir)
    cfg.out_score_csv_fname      = cfg.out_dir / cfg.out_score_csv_fname
    cfg.out_preset_json_fname    = cfg.out_dir / cfg.out_preset_json_fname
    cfg.out_mult_play_json_fname = cfg.out_dir / cfg.out_mult_play_json_fname
    cfg.out_ctl_json_fname       = cfg.out_dir / cfg.out_ctl_json_fname

    cfg.scriabin_scoreL = [ types.SimpleNamespace(**d) for d in cfg.scriabin_scoreL ]

    os.makedirs(cfg.out_dir,exist_ok=True)

    return cfg

def add_scriabin_to_cfg(cfg,section_labelL):

    
    for section_label in section_labelL:
        cfg.scriabin_scoreL.append( types.SimpleNamespace(**dict(fname              = "scriabin_74_3/output/legacy_sf_score.csv",
                                                                 score_pkl_fname    = "scriabin_74_3/output/cache/assign_sustain.pkl",
                                                                 seg_list_pkl_fname = "scriabin_74_3/output/cache/seg_list.pkl",
                                                                 section_label      = section_label,
                                                                 beg_meas_correct   = -1,  # transition meas number adjust
                                                                 end_meas_correct   = -1,
                                                                 beg_sec_correct    = -0.9, # transition time adjust
                                                                 end_sec_correct    = 0.5,
                                                                 rowL               = None,
                                                                 vel_table          = SCRIABIN_VEL_TABLE)))

        
    return cfg
                                 
def change_scriabin_section_numbers( section_labelL, score_csv_fname ):

    section_id = 3000
    outL = []
    with open(score_csv_fname) as f:
        rdr = csv.DictReader(f)

        for r in rdr:
            if r['src'] in section_labelL and r['section'].isdigit() and int(r['section'])==2000:
                r['section'] = section_id
                section_id += 100
            outL.append(r)

    with open(score_csv_fname,"w") as f:
        fieldnames = list(outL[0].keys())
        wtr = csv.DictWriter(f,fieldnames)

        wtr.writeheader()
        for r in outL:
            wtr.writerow(r)

            
        
                
                

def main( sf_or_all ):

    assert sf_or_all=='all' or sf_or_all == 'sf'

    section_labelL = ["Scriabin-1_Op74_1",
                      "Scriabin-2_Op74_2",
                      "Scriabin-5_Op65_1",
                      "Scriabin-6_Op67_2",
                      "Scriabin-7_Op74_5",
                      "Scriabin-8_Op65_2",
                      "Scriabin-9_Op51_2",
                      "Scriabin-10_Op65_3"]


    
    out_score_csv_fname = { "sf":"score_csv", "all":"timeline_all/all_score.csv" }[sf_or_all]

    cfg = get_part_1_cfg(out_score_csv_fname)

    if sf_or_all == 'all':
        add_scriabin_to_cfg(cfg,section_labelL)

    # Insert scriabin sections which must be score followed
    # and update the oloc and meas numbers to reflect the inserted material.
    # locMapD = {<src>}{ old_loc:new_loc } holds a map of old->new score locations.
    # New locations needed to be generated to account for the score-follwed Scriabin
    # sections that were inserted in the score.
    # The <src> field is a score source (e.g. gutim, Scriabin-3_Op74_4, ...)
    locMapD, _ = gpf.gen_sf_score(cfg)

    if sf_or_all == 'all':
        change_scriabin_section_numbers( section_labelL, cfg.out_score_csv_fname )
    
    if sf_or_all == 'sf':
        # Generate a new preset file with updated locations to 'gutim_1/presets.json'
        gpf.update_preset_catalog(cfg,locMapD['gutim'])


    gpf.gen_multi_play_simple( "gutim_1/output/cache/assign_sustain.pkl",
                               "gutim_1/output/cache/seg_list.pkl",
                               locMapD,
                               "gutim",
                               "gutim_1/caw/gutim_multi_play.json",
                               None)

    gpf.gen_multi_play_simple( "scriabin_74_4/output/cache/assign_sustain.pkl",
                               "scriabin_74_4/output/cache/seg_list.pkl",
                               locMapD,
                               "Scriabin-3_Op74_4",
                               "gutim_1/caw/Op74_4_multi_play.json",
                               SCRIABIN_VEL_TABLE)

    gpf.gen_multi_play_simple( "scriabin_74_3/output/cache/assign_sustain.pkl",
                               "scriabin_74_3/output/cache/seg_list.pkl",
                               locMapD,
                               "Scriabin-4_Op74_3",
                               "gutim_1/caw/Op74_3_multi_play.json",
                              SCRIABIN_VEL_TABLE)


if __name__ == "__main__":

    "sf:generate score for sections that need to be tracked only"
    "all: generate score for all sections including scriabin sections that do not need to be tracked."
    
    sf_or_all = "sf"
    main(sf_or_all)
