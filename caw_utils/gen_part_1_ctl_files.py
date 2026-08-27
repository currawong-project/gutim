import csv
import json
import types
from const import (PIANO_MAP,PLAYER_MAP)

def read_score( score_csv_fname ):

    from gen_part_2_files import read_caw_score_csv

    scoreL = read_caw_score_csv( score_csv_fname )

    noteLocMapD = {}
    for r in scoreL:
        if r.note_id is not None  and len(r.note_id)>0 and r.oloc is not None and r.oloc>=0:
            assert r.note_id not in noteLocMapD
            noteLocMapD[r.note_id] = r.oloc

    return scoreL,noteLocMapD

            
def read_toc( toc_json_fname ):
    
    with open(toc_json_fname) as f:
        tocL = json.load(f)

    for toc in tocL:
        toc['piano_id'] = PIANO_MAP[ toc['piano'] ]
    return tocL

def form_ctl_file( tocL, noteLocMapD, piano_refL ):

    player_seg_numD = { k:1 for k,_ in PLAYER_MAP.items() }

    def _incr_player_seg( player ):
        psn = player_seg_numD[ player ]
        player_seg_numD[ player ] += 1
        return psn
    
    def _make_sf_cmd( piano_id, b_loc, e_loc, enable_fl ):
        return dict(type='sf',
                    sf_id=piano_id,
                    bloc=b_loc,
                    eloc=e_loc,
                    enable_fl=enable_fl)

    def _form_non_active_sf_cmds( tocL, toc_idx, active_piano_id, piano_refL, noteLocMapD ):

        def _find_next_toc(toc_idx,piano_id):
            
            enable_fl = True
            
            if toc_idx+1 < len(tocL):
                for toc in tocL[toc_idx+1:]:                
                    if toc['type_id'] == 'scriabin':
                        # if we are crossing a Scriabin section on the same piano
                        # then disable the score follower
                        if toc['piano_id'] == piano_id:
                            enable_fl = False

                    elif toc['type_id'] == 'gutim':
                        if toc['piano_id'] == piano_id:
                            piano_id = toc['piano_id']
                            b_loc    = noteLocMapD[ toc['beg_sf_note_id'] ]
                            e_loc    = noteLocMapD[ toc['end_sf_note_id'] ]
                            sf_cmd   = _make_sf_cmd(piano_id, b_loc, e_loc, enable_fl )
                            return sf_cmd
                    else:
                        assert False

            # signal that this piano has no more TOC's following toc_idx
            return _make_sf_cmd(piano_id,None,None,False)


        sf_cmdL = []
        for piano_id in piano_refL:
            if piano_id != active_piano_id:
                sf_cmdL.append( _find_next_toc(toc_idx,piano_id) )

        return sf_cmdL



    ctlL = []
    cacheD = {}
    for toc_idx,toc in enumerate(tocL):
        
        if toc['type_id'] != 'gutim':
            continue
        
        b_loc        = noteLocMapD[ toc['beg_sf_note_id'] ]
        e_loc        = noteLocMapD[ toc['end_sf_note_id'] ]
        piano_id     = toc['piano_id']
        loc_id       = b_loc
        seg_id       = int( toc['seg_id'] )        
        active_sf_id = piano_id

        play_cmd = dict( type="play",
                         seg_type="simul",
                         seg_label=toc['seg_label'],
                         seg_id=seg_id,
                         piano_id=piano_id,
                         player_label = toc['player'],
                         player_seg_num = _incr_player_seg(toc['player'] ),
                         bloc=b_loc,
                         eloc=e_loc )

        # form the SF ctl records for the inactive pianos
        sf_cmdL       = _form_non_active_sf_cmds(tocL,toc_idx,piano_id,piano_refL,noteLocMapD)
        
        # append the SF control record for the active pianos
        sf_cmdL += [ _make_sf_cmd(piano_id,b_loc,e_loc,True) ]

        # Fix up the cmd's that have no next active state because the piano will not be used again.
        # Use the settings from the last active state on this piano and set the 'enable_fl' to False
        for sf_cmd in sf_cmdL:
            if sf_cmd['bloc'] is None:
                assert sf_cmd['eloc'] is None # if bloc is None so must eloc
                sf_cmd['bloc'] = cacheD[ sf_cmd['sf_id'] ]['bloc'] 
                sf_cmd['eloc'] = cacheD[ sf_cmd['sf_id'] ]['eloc'] 
            else:
                cacheD[ sf_cmd['sf_id'] ] = sf_cmd  # track the last active cmd

        # sort the commands by piano_id
        sf_cmdL = sorted(sf_cmdL,key=lambda x:x['sf_id'])

        # store the cmd in the ctl list
        ctlL.append(dict(loc_id=loc_id,
                         seg_id=seg_id,
                         active_sf_id=active_sf_id,
                         cmdL=[play_cmd] + sf_cmdL))
        
        
    return ctlL
        
def write_ctl_file(ctl,out_gutim_ctl_json_fname):

    hdr = dict(ctlL=ctlL)
    
    with open(out_gutim_ctl_json_fname,"w") as f:
        json.dump(hdr,f,indent=2)

def write_seg_menu_file(tocL,seg_menu_json_fname):

    def _form_section(s):
        if '_' not in s:
            return s

        return s[s.index('_')+1:]

    menuD = {}
    seg_id = None
    for toc in tocL:
        piano  = toc['piano']
        player = toc['player']
            
        if toc['type_id'] == 'gutim':
            seg_id = int(toc['seg_id'])
            meas   = toc['beg_meas_num']
            section= _form_section( toc['seg_label'] )
            label = f"{seg_id:3} m.{meas:3} {piano} {player} {section}"
        elif toc['type_id'] == 'scriabin':
            seg_id = seg_id + 1
            section = _form_section( toc['section_id'] )
            label = f"{seg_id} {piano} {player} {section}"
        else:
            assert False
            
        menuD[label] = seg_id

    with open(seg_menu_json_fname,"w") as f:
        json.dump(menuD,f,indent=2)

        
        
if __name__ == "__main__":

    
    
    caw_toc_json_fname       = "gutim_1/output/caw_toc.json"
    score_csv_fname          = "gutim_1/caw/tl_score.csv"
    out_gutim_ctl_json_fname = "gutim_1/caw/gutim_ctl.json"
    out_seg_menu_json_fname  = "gutim_1/caw/seg_menu.json"
    
    piano_refL          = [ 'A','B','C' ]

    piano_refL          = [ PIANO_MAP[label] for label in piano_refL ]
    tocL                = read_toc(caw_toc_json_fname)
    scoreL,noteLocMapD = read_score(score_csv_fname)
    

    ctlL = form_ctl_file(tocL,noteLocMapD,piano_refL)

    write_ctl_file(ctlL,out_gutim_ctl_json_fname)

    write_seg_menu_file(tocL,out_seg_menu_json_fname)
