import os
import csv
import json
import types
from pathlib import Path

import gen_part_files as gpf

from const import (CAW_SCORE_CSV_TITLES, PLAYER_MAP, PIANO_MAP)


def read_caw_score_csv( fname ):
        def _parse_value( s, type_code ):
            """ Convert a string to a value based on 'type_code'. """
            s =  None if s==None or len(s)==0 else s
            
            if type_code == 'i':
                return None if s is None else int(s)
            elif type_code == 'f':
                return None if s is None else float(s)
            elif type_code == 's':
                return s
            else:
                assert False

        rowL = []
        with open(fname) as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                for title,type_code in CAW_SCORE_CSV_TITLES:
                    r[title] = _parse_value(r[title].strip(),type_code)
                rowL.append(types.SimpleNamespace(**r))

        return rowL

def gen_part_2_ctl_file( cfg ):
    # Generate the JSON file for the gutim_2_sf_ctl.
    
    def _read_toc_json( fname ):
        with open(fname) as f:
            tocL = json.load(f)
        return tocL

    def _gen_sf_ctl( tocL, scoreL ):

        ctlL = []
        
        scoreD = { d.note_id:d.oloc for d in scoreL }

        for toc in tocL:
            assert toc['color'] == PLAYER_MAP[ toc['player'] ]['color']
            # print( toc['seg_id'], scoreD[ toc['beg_sf_note_id'] ], scoreD[ toc['end_sf_note_id'] ] )
            assert scoreD[ toc['beg_sf_note_id'] ] <= scoreD[ toc['end_sf_note_id'] ]
            ctlL.append( dict( beg_loc = scoreD[ toc['beg_sf_note_id'] ],
                               end_loc = scoreD[ toc['end_sf_note_id'] ],
                               player_id = PLAYER_MAP[ toc['player'] ]['id'],
                               player_label = toc['player'],
                               color = toc['color'],
                               piano_id = PIANO_MAP[ toc['piano'] ] ))
        return ctlL

    def _write_sf_ctl_file( fname, sf_ctlL ):
        with open(fname,"w") as f:
            json.dump(sf_ctlL,f,indent=2)
    
        
    scoreL  = read_caw_score_csv(cfg.out_score_csv_fname)
    tocL    = _read_toc_json(cfg.toc_json_fname)
    sf_ctlL = _gen_sf_ctl( tocL, scoreL )

    _write_sf_ctl_file( cfg.out_sf_ctl_json_fname, sf_ctlL )
    

def get_part_2_cfg(char_code):

    cfg = dict(
        out_dir              = f"gutim_2/{char_code}/caw",
        score_pkl_fname      = f"gutim_2/{char_code}/output/cache/assign_sustain.pkl",
        seg_list_pkl_fname   = f"gutim_2/{char_code}/output/cache/seg_list.pkl",
        base_score_csv_fname = f"gutim_2/{char_code}/output/legacy_sf_score.csv",
        preset_json_fname    = f"gutim_2/{char_code}/output/new_catalog.json",
        toc_json_fname       = f"gutim_2/{char_code}/output/caw_toc.json",
        scriabin_scoreL      = [],
        
        out_score_csv_fname      = "score.csv",
        out_preset_json_fname    = "presets.json",
        out_mult_play_json_fname = "multi_player.json",
        out_ctl_json_fname       = "pgm_ctl.json",
        out_sf_ctl_json_fname    = "sf_ctl.json")

    

    cfg = types.SimpleNamespace(**cfg)

    cfg.out_dir = Path(cfg.out_dir)
    cfg.out_score_csv_fname      = cfg.out_dir / cfg.out_score_csv_fname
    cfg.out_preset_json_fname    = cfg.out_dir / cfg.out_preset_json_fname
    cfg.out_mult_play_json_fname = cfg.out_dir / cfg.out_mult_play_json_fname
    cfg.out_ctl_json_fname       = cfg.out_dir / cfg.out_ctl_json_fname
    cfg.out_sf_ctl_json_fname    = cfg.out_dir / cfg.out_sf_ctl_json_fname

    cfg.scriabin_scoreL = [ types.SimpleNamespace(**d) for d in cfg.scriabin_scoreL ]

    os.makedirs(cfg.out_dir,exist_ok=True)

    return cfg

    
    


if __name__ == "__main__":

    cfg = get_part_2_cfg('a')
    # cfg = get_part_2_cfg('b')
    # cfg = get_part_2_cfg('c')

    # locMapD = {<src>}{ old_loc:new_loc } holds a map of old->new score locations - which should not have
    # changed since no material was inserted (cfg.scriabin_scoreL[]) is empty)
    locMapD, _ = gpf.gen_sf_score(cfg)

    # Generate a new preset file with updated locations.
    gpf.update_preset_catalog(cfg,locMapD['gutim'])

    # Generate a multi-player file containing one 'player' for each segment
    segPlayerMapD = gpf.gen_multi_player(cfg,locMapD)

    gpf.print_mp_directory(cfg.out_mult_play_json_fname,segPlayerMapD)

    gen_part_2_ctl_file( cfg )
    # gen_pgm_ctl_file(cfg.out_mult_play_json_fname, segPlayerMapD, cfg.out_ctl_json_fname)
