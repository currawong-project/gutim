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
    
    def _read_toc_json( fname, piano_id ):
        with open(fname) as f:
            tocL = json.load(f)

        
        return [toc for toc in tocL if PIANO_MAP[toc['piano']] == piano_id ]

    def _gen_sf_ctl_0( tocL, scoreL ):

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

    def _gen_sf_ctl_list( scoreL, piano_id, max_gap_dur_sec  ):
        def _find_segments(scoreL,max_gap_dur_sec):
            segL = [dict(piano_id=piano_id, beg_loc=0, end_loc=None, post_gap_dur_sec=-1)]
            sec0 = None
            for r in scoreL:
                sec1 = r.sec
                if sec0 is not None:
                    dsec = sec1 - sec0
                    if dsec > max_gap_dur_sec:
                        segL[-1]['end_loc']          = end_loc
                        segL[-1]['post_gap_dur_sec'] = dsec
                        segL.append(dict(piano_id=piano_id, beg_loc=r.oloc, end_loc=None, post_gap_dur_sec=-1))
                sec0    = sec1
                end_loc = r.oloc

            segL[-1]['end_loc'] = scoreL[-1].oloc
            return segL

        def _set_max_ioi(scoreL,segL):
            locSecD  = { r.oloc:r.sec     for r in scoreL }
            locNoteD = { r.oloc:r.note_id for r in scoreL }

            for seg in segL:
                max_dur_sec = None
                max_note_id = None
                sec0 = None
                for loc in range(seg['beg_loc'],seg['end_loc']+1):
                    sec1 = locSecD[loc]
                    if sec0 is not None:
                        dsec = sec1 - sec0
                        if max_dur_sec is None or dsec > max_dur_sec:
                            max_dur_sec = dsec
                            max_note_id = locNoteD[ loc ]

                    sec0 = sec1
                seg['max_dur_sec'] = max_dur_sec
                seg['max_note_id'] = max_note_id



                
        scoreL = [ r for r in scoreL if r.note_id is not None and len(r.note_id.strip())> 0 ]
        
        for r in scoreL:
            if r.sec is None or type(r.sec) != float:
                print(r)
        
        scoreL = sorted(scoreL,key=lambda x:x.sec)
        
        segL = _find_segments(scoreL,max_gap_dur_sec)
        _set_max_ioi(scoreL,segL)
        return segL
    

    def _gen_note_to_loc_map(scoreL):
        noteLocMapD = {}
        for r in scoreL:
            if r.note_id is not None and len(r.note_id.strip()) > 0 and r.oloc is not None:
                noteLocMapD[ r.note_id ] = r.oloc
        return noteLocMapD

    def _gen_meas_and_sect_loc_map(scoreL, noteLocMapD ):

        def _fill_in_missing_measures( mlD, max_meas_num ):
            for meas_num in range(1,max_meas_num+1):
                if str(meas_num) not in mlD:

                    for mn in range(int(meas_num)+1,max_meas_num+1):
                        if str(mn) in mlD:
                            loc = mlD[str(mn)]
                            break
                            
                    mlD[str(meas_num)] = loc
            return dict(sorted(mlD.items(),key=lambda x:int(x[0])))
                    
        
        measLocMapD = {}
        sectLocMapD = {}
        meas_num    = None
        section     = None
        max_meas_num = 0
        
        for r in scoreL:

            if r.bar is not None and len(r.bar.strip())>0:
                meas_num = r.bar
                if int(meas_num) > max_meas_num:
                    max_meas_num = int(meas_num)

                continue
            
            if r.section is not None and len(r.section.strip())>0:
                section = r.section
                continue

            if meas_num is not None and r.note_id is not None and len(r.note_id.strip())>0 and r.note_id in noteLocMapD:
                measLocMapD[ meas_num ] = noteLocMapD[r.note_id]
                meas_num = None

            if section is not None and r.note_id is not None and len(r.note_id.strip())>0 and r.note_id in noteLocMapD:
                sectLocMapD[ section ] = noteLocMapD[r.note_id]
                section = None

        measLocMapD = _fill_in_missing_measures(measLocMapD,max_meas_num)
        
        return measLocMapD, sectLocMapD
                
    def _refine_sect_loc_map( sectLocMapD, tocL, noteLocMapD ):
        # Force the section map to be based on the TOC rather than the score
        # since the TOC has been modified to have sections that may not
        # be in the score.  Note however that there are also sections
        # in the score that may not be in the TOC.  These are section
        # breaks where the player does not change.
        mapD = {}
        for toc in tocL:
            for section in toc['sectL']:
                if section in sectLocMapD:
                    mapD[section] = sectLocMapD[section]
                else:
                    mapD[section] = noteLocMapD[toc['beg_sf_note_id']]

        return mapD
        
    
    def _write_sf_ctl_file( fname, sf_ctlL, measLocMapD, sectLocMapD ):
        hdr = dict(sf_ctlL         = sf_ctlL,
                   meas_loc_map    = measLocMapD,
                   section_loc_map = sectLocMapD)
            
        with open(fname,"w") as f:
            json.dump(hdr,f,indent=2)
    

    # Read the score file.
    scoreL  = read_caw_score_csv(cfg.out_score_csv_fname)

    # Read the table-of-contents file
    tocL    = _read_toc_json(cfg.toc_json_fname,cfg.piano_id)

    noteLocMapD =  _gen_note_to_loc_map(scoreL)

    noteIdToLocD = _gen_note_to_loc_map(scoreL)
    
    # Create a section->loc and meas->loc maps
    measLocMapD, sectLocMapD = _gen_meas_and_sect_loc_map(scoreL, noteLocMapD)

    # Refine the section->loc map to account for manual sections in the TOC.
    sectLocMapD = _refine_sect_loc_map( sectLocMapD, tocL, noteLocMapD )

    # Create the SF control file
    # sf_ctlL = _gen_sf_ctl( tocL, scoreL )

    sf_ctlL = _gen_sf_ctl_list( scoreL, cfg.piano_id, cfg.max_gap_dur_sec )

    # Write the SF control file.
    _write_sf_ctl_file( cfg.out_sf_ctl_json_fname, sf_ctlL, measLocMapD, sectLocMapD )

def gen_spirio_multi_player( cfg, fullMpD, dropNoteL ):

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

    def _gen_spirio_mp_dict( fullMpD, tocL, dropNoteL ):

        def _apply_drop_note_list( piano_id, msgL, dropNoteL ):

            apply_cnt = 0
            # for each drop record
            for dropD in dropNoteL:
                # if the piano_id of this message list matches the piano id of the drop record
                if dropD['piano_id'] == piano_id:

                    # form a note_id to msgL index map of msgL
                    noteIdxMapD = { m['evt_id']:i for i,m in enumerate(msgL) }
                    
                    # is the first drop note_id in this msgL
                    if dropD['note_idL'][0] in noteIdxMapD:
                        # if the first drop note_id is in this msg list then they all must be
                        drop_idxL = [ noteIdxMapD[note_id] for note_id in dropD['note_idL'] ]

                        msgL = [ m for i,m in enumerate(msgL) if i not in drop_idxL ]
                        apply_cnt += 1
                        

            if apply_cnt > 0:
                print(apply_cnt,"Drop records applied.")
            return msgL
            
        outMpD = {}
        
        for toc in tocL:
            if toc['player'] == 'SP':

                msgL = _get_msg_list( fullMpD, toc['beg_mp_id'], toc['end_mp_id'] )

                piano_id = PIANO_MAP[ toc['piano'] ]
                msgL = _apply_drop_note_list( piano_id, msgL, dropNoteL )

                mp = dict(player_id = len(outMpD),
                          label     = toc['seg_label'],
                          port_id   = piano_id,
                          sectL     = [ toc['seg_label'] ],
                          msgL      = msgL)

                outMpD[toc['seg_label']] = mp
                   
        return outMpD

    def _write_spirio_mp_file( spirioMpD, fname ):
        with open(fname,"w") as f:
            json.dump(spirioMpD,f,indent=2)
        
    tocL      = _read_toc(cfg.toc_json_fname)    
    spirioMpD = _gen_spirio_mp_dict( fullMpD, tocL, dropNoteL )

            
    _write_spirio_mp_file( spirioMpD, cfg.out_spirio_mp_json_fname )

def merge_all_preset_catalogs( preset_json_fnameL, out_preset_json_fname ):

    segL = []
    for fname,piano_id in preset_json_fnameL:
        with open(fname) as f:
            r = json.load(f)

        r['port_id'] = piano_id
        segL.append(r)

    with open(out_preset_json_fname,"w") as f:
        json.dump(segL,f,indent=2)
        
        
    
    
def get_part_2_cfg(char_code):

    cfg = dict(
        max_gap_dur_sec      = 4.0,
        piano_id             = PIANO_MAP[ char_code.upper() ],
        out_dir              = f"gutim_2/{char_code}/caw",
        score_pkl_fname      = f"gutim_2/{char_code}/output/cache/assign_sustain.pkl",
        seg_list_pkl_fname   = f"gutim_2/{char_code}/output/cache/seg_list.pkl",
        base_score_csv_fname = f"gutim_2/{char_code}/output/legacy_sf_score.csv",
        preset_json_fname    = f"gutim_2/{char_code}/output/new_catalog.json",
        toc_json_fname       = f"gutim_2/{char_code}/output/caw_toc.json",
        full_preset_json_fname = "gutim_2/full_preset_catalog.json",
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

    dropNotesL = [ dict(piano_id=PIANO_MAP['B'], note_idL=[
        "n315_6Ds1h",
        "n315_6Ds1h_off",
        "n315_6E3h",
        "n315_6E3h_off",
        "n315_6Fs3h",
        "n315_6Fs3h_off",
        "n316_6Ds1h",
        "n316_6Ds1h_off",
        "n316_6E3h",
        "n316_6E3h_off",
        "n316_6Fs3h",
        "n316_6Fs3h_off",
        "n317_1Ds6t_0",
        "n317_1Ds6t_0_off",
        "n317_6E3q",
        "n317_6E3q_off",
        "n317_6Fs3q",
        "n317_6Fs3q_off",
        "n317_6C4q_0",
        "n317_6C4q_0_off" ])]

    
    char_codeL = ['a','b','c']

    preset_fnameL = []
    
    for c in char_codeL:

        cfg = get_part_2_cfg(c)

        # locMapD = {<src>}{ old_loc:new_loc } holds a map of old->new score locations - which should not have
        # changed since no material was inserted (cfg.scriabin_scoreL[]) is empty)
        locMapD, _ = gpf.gen_sf_score(cfg)

        # Generate a new preset file with updated locations.
        gpf.update_preset_catalog(cfg,locMapD['gutim'])

        # Generate a multi-player file containing one 'player' for each segment
        _,fullMpD = gpf.gen_multi_player(cfg,locMapD)

        # gpf.print_mp_directory(cfg.out_mult_play_json_fname,segPlayerMapD)

        gen_spirio_multi_player( cfg, fullMpD,dropNotesL )

        gen_part_2_ctl_file( cfg )
        # gen_pgm_ctl_file(cfg.out_mult_play_json_fname, segPlayerMapD, cfg.out_ctl_json_fname)

        preset_fnameL.append((cfg.out_preset_json_fname,cfg.piano_id))

    merge_all_preset_catalogs( preset_fnameL, cfg.full_preset_json_fname )
        
