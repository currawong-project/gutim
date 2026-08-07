import tos
import types
from pathlib import Path

import gen_part_files as gpf

def get_part_1_cfg():

    cfg = dict(
        out_dir              = "gutim_1/caw",
        score_pkl_fname      = "gutim_1/output/cache/assign_sustain.pkl",
        seg_list_pkl_fname   = "gutim_1/output/cache/seg_list.pkl",
        base_score_csv_fname = "gutim_1/output/legacy_sf_score.csv",
        preset_json_fname    = "gutim_1/output/new_catalog.json",
        scriabin_scoreL      = [ dict(fname              = "scriabin_74_4/output/legacy_sf_score.csv",
                                      score_pkl_fname    = "scriabin_74_4/output/cache/assign_sustain.pkl",
                                      seg_list_pkl_fname = "scriabin_74_4/output/cache/seg_list.pkl",
                                      section_label      = "Scriabin-3_Op74_4",
                                      beg_meas_correct   = -1,  # transition meas number adjust
                                      end_meas_correct   = -1,
                                      beg_sec_correct    = -0.9, # transition time adjust
                                      end_sec_correct    = 0.5,
                                      rowL               = None ),
                                 dict(fname              = "scriabin_74_3/output/legacy_sf_score.csv",
                                      score_pkl_fname    = "scriabin_74_3/output/cache/assign_sustain.pkl",
                                      seg_list_pkl_fname = "scriabin_74_3/output/cache/seg_list.pkl",
                                      section_label      = "Scriabin-4_Op74_3",
                                      beg_meas_correct   = -1,  # transition meas number adjust
                                      end_meas_correct   = -1,
                                      beg_sec_correct    = -0.9, # transition time adjust
                                      end_sec_correct    = 0.5,
                                      rowL               = None ) 
                                ],
        
        
        out_score_csv_fname      = "score.csv",
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


def get_part_2_cfg(char_code):

    cfg = dict(
        out_dir              = f"gutim_2/{char_code}/caw",
        score_pkl_fname      = f"gutim_2/{char_code}/output/cache/assign_sustain.pkl",
        seg_list_pkl_fname   = f"gutim_2/{char_code}/output/cache/seg_list.pkl",
        base_score_csv_fname = f"gutim_2/{char_code}/output/legacy_sf_score.csv",
        preset_json_fname    = f"gutim_2/{char_code}/output/new_catalog.json",
        scriabin_scoreL      = [],
        
        out_score_csv_fname      = "score.csv",
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


if __name__ == "__main__":

    # cfg = get_part_1_cfg()
    # cfg = get_part_2_cfg('a')
    # cfg = get_part_2_cfg('b')
    cfg = get_part_2_cfg('c')

    # Insert scriabin sections which must be score followed
    # and update the oloc and meas numbers to reflect the inserted material.
    # locMapD = {<src>}{ old_loc:new_loc } holds a map of old->new score locations.
    # New locations needed to be generated to account for the score-follwed Scriabin
    # sections that were inserted in the score.
    # The <src> field is a score source (e.g. gutim, Scriabin-3_Op74_4, ...)
    locMapD, _ = gpf.gen_sf_score(cfg)

    # Generate a new preset file with updated locations.
    gpf.update_preset_catalog(cfg,locMapD['gutim'])

    # Generate a multi-player file containing one 'player' for each segment
    segPlayerMapD = gen_multi_player(cfg,locMapD)

    gpf.print_mp_directory(cfg.out_mult_play_json_fname,segPlayerMapD)

    # gen_pgm_ctl_file(cfg.out_mult_play_json_fname, segPlayerMapD, cfg.out_ctl_json_fname)

    
