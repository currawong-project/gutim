import os
import csv
import json
import types
from pathlib import Path

import gen_part_files as gpf

from const import (CAW_SCORE_CSV_TITLES, PLAYER_MAP, PIANO_MAP, MIDI_NOTE_ON_STATUS, MIDI_NOTE_OFF_STATUS, MIDI_CTL_STATUS, MIDI_DAMPER_D0, MIDI_SOST_D0, MIDI_PEDAL_DOWN_D1)


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

def gen_spirio_multi_player( cfg, fullMpD ):

    def _get_msg_list( fullMpD, beg_evt_id, end_evt_id ):

        def _make_midi_recd( sec, status, d0, d1 ):
            return dict(uid=-1,sec=sec,ch=0,status=status,d0=d0,d1=d1,evt_id=None)
        
        def _is_pedal_d1_down(d1):
            return d1 >= MIDI_PEDAL_DOWN_D1
        
        def _is_pedal_down(m):
            return (_is_damper(m) or _is_sostenuto(m)) and _is_pedal_d1_down(m['d1'])

        def _is_pedal_up(m):
            return (_is_damper(m) or _is_sostenuto(m)) and _is_pedal_d1_down(m['d1'])
        
        def _is_damper(m):
            return m['d0'] == MIDI_DAMPER_D0
        
        def _is_damper_up(m):
            return _is_damper(m) and _is_pedal_up(m)
        
        def _is_damper_down(m):
            return _is_damper(m) and _is_pedal_down(m) 

        def _is_sostenuto(m):
            return m['d0'] == MIDI_SOST_D0
        
        def _is_sostenuto_up(m):
            return _is_sostenuto(m) and _is_pedal_up(m)
        
        def _is_sostenuto_down(m):
            return _is_sostenuto(m) and _is_pedal_down(m)

        def _prepend_pedal_down(clipL, d0 ):
            r = _make_midi_recd(clipL[0]['sec'],MIDI_CTL_STATUS,d0,127);
            clipL.insert(0,r)
        
        def _prepend_damp_down(clipL):
            _prepend_pedal_down(clipL,MIDI_DAMPER_D0)
        
        def _prepend_sost_down(clipL):
            _prepend_pedal_down(clipL,MIDI_SOST_D0)
        
        def _append_pedal_up(clipL,d0):
            r = _make_midi_recd(clipL[-1]['sec'],MIDI_CTL_STATUS,d0,0)
            clipL.append(r)

        def _append_pedals_up(clipL,ctl_stateL):
            if _is_pedal_d1_down(ctl_stateL[ MIDI_DAMPER_D0 ]):
                _append_pedal_up(clipL,MIDI_DAMPER_D0)
                
            if _is_pedal_d1_down(ctl_stateL[ MIDI_SOST_D0 ]):
                _append_pedal_up(clipL,MIDI_SOST_D0)
                
        def _append_note_offs(clipL,key_stateL):
            for d0,n in enumerate(key_stateL):
                if n > 0:
                    sec = clipL[-1]['sec']
                    clipL.append(_make_midi_recd(sec,MIDI_NOTE_OFF_STATUS,d0,0))
        
        def _clip_spirio_section( msgL, beg_evt_id, end_evt_id ):
            clipL      = []        # 
            key_stateL = [0] * 128 #
            ctl_stateL = [0] * 128 # 
            gate_fl    = False     # true if we are inside the clip
            decay_fl   = False     # true if we are past the end of the clip waiting for note-offs
            done_fl    = False     # true if we located the end-note and achieved an all-notes off status before the end of the msgL
            damp_cnt   = 0         # count the number of damper up/down messages
            sost_cnt   = 0         # count the number of sostenuto up/down messages

            for m in msgL:
                # if this is the clip begin note
                if not gate_fl and m['evt_id'] == beg_evt_id:
                    gate_fl = True
                    
                # if this is the clip end note
                if gate_fl and m['evt_id'] == end_evt_id:
                    gate_fl = False
                    decay_fl = True

                # if we are inside the clip and this is a note-on msg
                if gate_fl and m['status'] == MIDI_NOTE_ON_STATUS:
                    clipL.append(m)
                    one = -1 if m['d1'] == 0 else 1
                    
                    if key_stateL[ m['d0'] ] + one >= 0:
                        key_stateL[ m['d0'] ] += one
                        
                    assert key_stateL[ m['d0'] ] >= 0
                # if we are inside/past the clip and this is a note-off msg
                elif (gate_fl or decay_fl) and m['status'] == MIDI_NOTE_OFF_STATUS:
                    clipL.append(m)
                    if key_stateL[ m['d0'] ] > 0:
                        key_stateL[ m['d0'] ] -= 1
                        
                    # if the end-note was found and there are no more keys down
                    if decay_fl and sum(key_stateL) == 0:
                        done_fl = True
                        break

                # if this is a control msg
                elif (gate_fl or decay_fl) and m['status'] == MIDI_CTL_STATUS:
                    clipL.append(m)
                    ctl_stateL[ m['d0'] ] = m['d1']

                    # track damper messages
                    if _is_damper(m):
                        # if the first damper down is a damper up then we need to prepend a damper down before the first note
                        if damp_cnt == 0 and _is_damper_up(m):
                            _prepend_damp_down(clipL)
                        damp_cnt += 1

                    # track sostenuto messages
                    elif _is_sostenuto(m):
                        # if the first sost down is a sost up then we need to prepend a sost down before the first note
                        if sost_cnt == 0 and _is_sostenuto_up(m):
                            _prepend_sost_down(clipL)
                        sost_cnt += 1

            # if we did not find the end-note and all the associated note-offs
            if not done_fl:
                print(f"Unexpected end of clip. Last note {end_evt_id} was not encountered.")

            # turn off hung notes
            _append_note_offs(clipL,key_stateL)
                
            # lift all the pedals
            _append_pedals_up(clipL,ctl_stateL)

            return clipL    
                
            

        for _,d in fullMpD.items():
            for msg in d['msgL']:
                if msg['evt_id'] == beg_evt_id:
                    return _clip_spirio_section( d['msgL'], beg_evt_id, end_evt_id )
                
        assert False
    
    def _read_toc( toc_json_fname ):
        with open(toc_json_fname) as f:
            tocL = json.load(f)


        # verify that all seg_id and seg_labels are unique
        labelD = []
        idD = []
        for toc in tocL:
            assert toc['seg_id'] not in idD
            idD.append(toc['seg_id'])
            assert toc['seg_label'] not in labelD
            labelD.append(toc['seg_label'])
            
            
        return tocL

    def _gen_spirio_mp_dict( fullMpD, tocL ):
        outMpD = {}
        
        for toc in tocL:
            if toc['player'] == 'SP':

                msgL = _get_msg_list( fullMpD, toc['beg_mp_id'], toc['end_mp_id'] )

                mp = dict(player_id = PLAYER_MAP[toc['player']],
                          label     = toc['seg_label'],
                          port_id   = PIANO_MAP[ toc['piano'] ],
                          sectL     = [ toc['seg_label'] ],
                          msgL      = msgL)

                outMpD[toc['seg_label']] = mp
                   
        return outMpD

    def _write_spirio_mp_file( spirioMpD, fname ):
        with open(fname,"w") as f:
            json.dump(spirioMpD,f,indent=2)
        
    tocL      = _read_toc(cfg.toc_json_fname)    
    spirioMpD = _gen_spirio_mp_dict( fullMpD, tocL )
            
    _write_spirio_mp_file( spirioMpD, cfg.out_spirio_mp_json_fname )

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
        out_sf_ctl_json_fname    = "sf_ctl.json",
        out_spirio_mp_json_fname = "spirio_mp.json")

    

    cfg = types.SimpleNamespace(**cfg)

    cfg.out_dir = Path(cfg.out_dir)
    cfg.out_score_csv_fname      = cfg.out_dir / cfg.out_score_csv_fname
    cfg.out_preset_json_fname    = cfg.out_dir / cfg.out_preset_json_fname
    cfg.out_mult_play_json_fname = cfg.out_dir / cfg.out_mult_play_json_fname
    cfg.out_ctl_json_fname       = cfg.out_dir / cfg.out_ctl_json_fname
    cfg.out_sf_ctl_json_fname    = cfg.out_dir / cfg.out_sf_ctl_json_fname
    cfg.out_spirio_mp_json_fname = cfg.out_dir / cfg.out_spirio_mp_json_fname

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
    _,fullMpD = gpf.gen_multi_player(cfg,locMapD)

    # gpf.print_mp_directory(cfg.out_mult_play_json_fname,segPlayerMapD)

    gen_spirio_multi_player( cfg, fullMpD )

    gen_part_2_ctl_file( cfg )
    # gen_pgm_ctl_file(cfg.out_mult_play_json_fname, segPlayerMapD, cfg.out_ctl_json_fname)
