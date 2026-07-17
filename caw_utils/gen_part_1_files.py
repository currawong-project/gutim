import os
import csv
import json
import types
import pickle
import warnings
from pathlib import Path

from piano.model import (Note, GraceNote, Rest, GraceRest)

CSV_TITLES = [('meas','i'),('sec','f'),('status','i'),('d0','i'),('d1','i'),('oloc','i'),('section','s'),('sci_pitch','s'),('even','s'),('even_target','s'),('dyn','s'),('dyn_target','s'),('tempo','s'),('tempo_target','s') ]

from const import (PLAYER_MAP,
                   PIANO_MAP,
                   MIDI_NOTE_ON_STATUS,
                   MIDI_NOTE_OFF_STATUS,
                   MIDI_CTL_STATUS,
                   MIDI_DAMPER_D0,
                   MIDI_SOST_D0,
                   MIDI_DAMPER_HALF_VALUE,
                   MIDI_MAX_CTL_VALUE,
                   DAMPER_CLEAR_OFFSET_SEC )
                   


_PC_OFFSET  = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_ACC_OFFSET = {'s': 1, 'b': -1, '': 0}

def gen_sf_score( cfg ):
    def _read_score_csv( fname ):
        
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
                for title,type_code in CSV_TITLES:
                    r[title] = _parse_value(r[title].strip(),type_code)
                r['src'] = None
                r['src_meas'] = None
                rowL.append(types.SimpleNamespace(**r))

        return rowL

    def _insert_scriabin( cfg, rowBaseL ):

        def _section_to_index( cfg, rowL ):
            ss_indexL = []
            for ss in cfg.scriabin_scoreL:
                for i,r in enumerate(rowL):
                    if r.section is not None and r.section == ss.section_label:
                        ss_indexL.append((i,ss))

            return sorted(ss_indexL,key=lambda x:x[0])
                        
        def _insert_row( outL, r, locMap, src, next_loc, meas_offset, sec_offset ):
            """Insert a row into the output list."""
            
            meas_numb = r.meas
            next_sec = r.sec

            # if the oloc is not None then we need to map it's new value
            if r.oloc is not None:

                # store the old->new oloc map entry
                if r.oloc not in locMap[src]:
                    locMap[src][r.oloc] = next_loc                    
                    next_loc += 1

                # update the oloc value for the inserted event
                r.oloc     = locMap[src][r.oloc]
                
            r.src      = src     # keep track of the source of this event 
            r.src_meas = r.meas  # and the measure it originated from

            # update the measure number
            if r.meas is not None:
                r.meas += meas_offset

            if r.sec is not None:
                r.sec += sec_offset
                    
            outL.append(r)

            return next_loc,meas_numb,next_sec
        
        outL = []
        
        # Sort the cfg.scriabin_scoreL[] by the index at which the scriabin score will be inserted
        # This guarantees that a single pass through the base score will pass through the insertion
        # points in order.
        ss_indexL = _section_to_index(cfg,rowBaseL)

        # The locMapD{} has a loc mapping dict. for each possible source score
        # (e.g. gutim,scriabin_74_1,scriabin_74_2, ...).
        locMapD = { sr.section_label:{} for _,sr in ss_indexL }
        locMapD['gutim'] = {}


        si          = 0  # index into ss_indexL[] of the next scriabin score to insert
        next_loc    = 0  # next avail loc value 
        meas_offset = 0  # measure number offset
        sec_offset  = 0.0

        # for each base row
        for ri,r in enumerate(rowBaseL):

            # insert the base row into the output list
            next_loc,_,_ = _insert_row(outL,r,locMapD,"gutim",next_loc,meas_offset,sec_offset)

            # if this is the point of scriabin insertion
            if si < len(ss_indexL) and ri == ss_indexL[si][0]:
                
                assert r.section == ss_indexL[si][1].section_label

                # get the scriabin score cfg record
                scriab_score = ss_indexL[si][1]

                # calc. the meas offset for the first measure
                meas_offset = next((r.meas for r in reversed(outL) if r.meas is not None),None)
                sec_offset  = next((r.sec  for r in reversed(outL) if r.sec is not None),None)

                # beg/end_meas_correct is used to manually adjust the measure number at the begin and end of the insertion
                # (this is required for mid-measure insertions)
                meas_offset += scriab_score.beg_meas_correct
                sec_offset  += scriab_score.beg_sec_correct
                
                                
                # insert each scriabin row into the output list
                for sr in scriab_score.rowL:
                    next_loc,next_meas,next_sec = _insert_row(outL,sr,locMapD,r.section,next_loc,meas_offset,sec_offset)

                meas_offset = next_meas + scriab_score.end_meas_correct
                sec_offset  = next_sec  + scriab_score.end_sec_correct
                
                si += 1

        if si != len(ss_indexL):
            print("All scriabin scores were not inserted.")

        return outL,locMapD    

    def _write_score(cfg,outL):

        print(cfg.out_score_csv_fname)
        titleL = [ title for title,_ in CSV_TITLES ] + ['src','src_meas']
        with open(cfg.out_score_csv_fname,"w") as f:
            wtr = csv.DictWriter(f,fieldnames=titleL)
            wtr.writeheader()
            for r in outL:
                wtr.writerow(r.__dict__)
                
    rowBaseL = _read_score_csv( cfg.base_score_csv_fname )
    for scriab_cfgD in cfg.scriabin_scoreL:
        scriab_cfgD.rowL = _read_score_csv( scriab_cfgD.fname )
    outL,locMapD = _insert_scriabin( cfg, rowBaseL )

    _write_score(cfg,outL)

    return locMapD

def update_preset_catalog( cfg, locMapD ):

    with open(cfg.preset_json_fname) as f:
        pc = json.load(f)
        
    for frag in pc['fragL']:
        frag["beg_loc"] = locMapD[ frag["beg_loc"] ]
        frag["end_loc"] = locMapD[ frag["end_loc"] ]

    with open(cfg.out_preset_json_fname,"w") as f:
        json.dump(pc,f)


def _gen_multi_player( score_pkl_fname, seg_list_pkl_fname, locMapD, locMapSrc ):

    def _get_pedal_list( score_pkl_fname ):
        with open(score_pkl_fname,"rb") as f:
            score = pickle.load(f)

        return [ pe for pe in score.pedal_events if not pe.deleted ]
            
    def _form_section_note_dict( sect ):
        noteD = {}
        for se in sect.event_list:
            if se.event is not None and isinstance(se.event,(Note,GraceNote,Rest,GraceRest)):
                noteD[ se.event.id ] = dict(event=se,pedal=None)

        return noteD

    def _form_mp_segment_list( seg_list_pkl_fname):
        mpSegL  = []
        with open(seg_list_pkl_fname,"rb") as f:
            segList = pickle.load(f)

        for seg in segList.segments:
            mpSegD = dict( id=seg.id, label=None, player_id=None, port_id=None, noteD={}, sectL=[], msgL=[] )
            for i,sect in enumerate(seg.section_list):
                if i == 0:
                    mpSegD['label']     = sect.section_label
                    mpSegD['player_id'] = PLAYER_MAP[sect.player]['id']
                    mpSegD['port_id']   = PIANO_MAP[sect.piano]
                mpSegD['sectL'].append(sect.section_label)
                mpSegD['noteD'].update( _form_section_note_dict(sect) )
                
            mpSegL.append(mpSegD)
            
        return mpSegL

    def _attach_pedal_events( mpSegL, pedalL ):
        for pe in pedalL:
            found_fl = False
            for mpSegD in mpSegL:
                if pe.position_id in mpSegD['noteD']:
                    mpSegD['noteD'][pe.position_id]['pedal'] = pe
                    found_fl = True
                    break
                
            if not found_fl:
                print("The pedal event ",pe.id,"was not found.")
            

    def _load_msg_list( mpSectL, locMapD, locMapSrc ):

        # uid,sec,ch,status,d0,d1
        def _form_event_msg_list(eventD):

            def _midi_pitch( e ):
                return (e.octave + 1) * 12 + _PC_OFFSET[e.pitch_class] + _ACC_OFFSET[e.accidental]

            def _pedal_event_to_midi_ctl(pe):
                
                return { 'dp':MIDI_DAMPER_D0, 'sp':MIDI_SOST_D0 }[ pe.id[:2] ]

            def _pedal_event_depth_to_midi(pe):
                if pe.depth == 0.0:
                    return 0
                elif pe.depth == 1.0:
                    return MIDI_MAX_CTL_VALUE
                elif pe.depth == 0.5:
                    return MIDI_DAMPER_HALF_VALUE

                print("Unexpected pedal depth value:",pe.depth,"on event",pe.id)

                return max(0,min(MIDI_MAX_CTL_MAX,int( pe.depth * MIDI_MAX_CTL_MAX )))


            msgL = []
            e    = eventD['event'].event
            pe   = eventD['pedal']
            is_note_fl = e is not None and isinstance(e,(Note,GraceNote))
            is_rest_fl = e is not None and isinstance(e,(Rest,GraceRest))
            
            # if this is a note
            if is_note_fl and e.has_onset:

                #print(e.id,e.loc)
                
                n0 = dict(uid    = locMapD[locMapSrc][e.loc],
                          sec    = e.abs_time,
                          ch     = 0,
                          status = MIDI_NOTE_ON_STATUS,
                          d0     = _midi_pitch(e),
                          d1     = e.dlevel)


                n1 = dict(uid    = None,
                          sec    = e.abs_time + e.art_dur_sec,
                          ch     = 0,
                          status = MIDI_NOTE_OFF_STATUS,
                          d0     = n0['d0'],
                          d1     = 0)

                msgL = [n0,n1]

            # if this event has a pedal
            if pe is not None and (is_note_fl or is_rest_fl):

                clear_offset_sec = 50/1000.0
                
                if hasattr(pe,'clear_depth') and pe.clear_depth is not None:
                    clear_offs_sec = DAMPER_CLEAR_OFFSET_SEC if pe.clear_depth == 0 else 0.0

                    p0 = dict(uid = None,
                              sec = e.abs_time + clear_offs_sec,
                              ch  = 0,
                              status = MIDI_CTL_STATUS,
                              d0 = _pedal_event_to_midi_ctl(pe),
                              d1 = _pedal_event_depth_to_midi(pe) )

                    msgL.append(p0)

                p1 = dict(uid = None,
                          sec = e.abs_time,
                          ch  = 0,
                          status = MIDI_CTL_STATUS,
                          d0 = _pedal_event_to_midi_ctl(pe),
                          d1 = _pedal_event_depth_to_midi(pe) )

                msgL.append(p1)

            return msgL

        
        # for each section
        for mpSegD in mpSegL:
            # for each event in the section
            for _,e in mpSegD['noteD'].items():
                # convert the event to it's MIDI form
                mpSegD['msgL'] += _form_event_msg_list(e)

            # sort msgL on time
            mpSegD['msgL'] = sorted(mpSegD['msgL'],key=lambda x:x['sec'])
            

            
                
    pedalL  = _get_pedal_list( score_pkl_fname )
    mpSegL = _form_mp_segment_list( seg_list_pkl_fname )
    _attach_pedal_events(mpSegL,pedalL)
    _load_msg_list(mpSegL,locMapD,locMapSrc)
    return mpSegL



def gen_multi_player(cfg,locMapD):

    def _insert_scriabin_section( mpSectL, ssMpSectL, section_label ):

        for ssMpSectD in ssMpSectL:
            for i,mpSectD in enumerate(mpSectL):
                if mpSectD['label'] == section_label:
                    ssMpSectD['label'] = section_label
                    del mpSectL[i]
                    mpSectL.insert(i,ssMpSectD)
                    break

    def _write_mp_file(fname, mpSegL):
        outD = {}
        for mpSegD in mpSegL:
            outD[mpSegD['label']] = dict(player_id = mpSegD['player_id'],
                                         label     = mpSegD['label'],
                                         port_id   = mpSegD['port_id'],
                                         sectL     = mpSegD['sectL'],
                                         msgL      = mpSegD['msgL'])
                 
        with open(fname,"w") as f:
            json.dump(outD,f,indent=2)
    

    # get the base segments
    mpSegL = _gen_multi_player( cfg.score_pkl_fname,
                                cfg.seg_list_pkl_fname,
                                locMapD, 'gutim' )

    # for each of the scriabin segments
    for scriabin_score in cfg.scriabin_scoreL:
        ssMpSegL = _gen_multi_player( scriabin_score.score_pkl_fname,
                                      scriabin_score.seg_list_pkl_fname,
                                      locMapD,
                                      scriabin_score.section_label )
        # insert the scriabin segment
        _insert_scriabin_section(mpSegL,ssMpSegL,scriabin_score.section_label)

    # write the MP player json file
    _write_mp_file(cfg.out_mult_play_json_fname,mpSegL)

def print_mp_directory(mp_json_fname):

    def _beg_loc( seg ):
        return next(( d['uid'] for d in seg['msgL'] if d['uid'] is not None ),None)
    
    def _end_loc( seg ):
        return next(( d['uid'] for d in reversed(seg['msgL']) if d['uid'] is not None ),None)

    playerMap = { v['id']:k for k,v in PLAYER_MAP.items() }
    pianoMap  = { v:k for k,v in PIANO_MAP.items() }

    print(pianoMap)
    
    with open(mp_json_fname) as f:
        mpSegD = json.load(f)

    for label,seg in mpSegD.items():
        player = playerMap[seg['player_id']]
        piano  = pianoMap[seg['port_id']]
        
        print(label,player,piano,_beg_loc(seg),_end_loc(seg),end=" ")
        for sect_label in seg['sectL']:
            print(sect_label,end=" ")
        print("")
            
def gen_pgm_ctl_file( mult_play_json_fname, out_ctl_json_fname ):

    player_map  = { v['id']:k for k,v in PLAYER_MAP.items() }
    player_cntD = { v['id']:0 for _,v in PLAYER_MAP.items() }

    def _beg_loc( seg ):
        return next(( d['uid'] for d in seg['msgL'] if d['uid'] is not None ),None)
    
    def _end_loc( seg ):
        return next(( d['uid'] for d in reversed(seg['msgL']) if d['uid'] is not None ),None)

    def _player_seg_num( player_id ):
        player_cntD[player_id] += 1
        return player_cntD[player_id]
    
    def _next_bloc_eloc_on_piano(mpSegD,cur_seg_id,piano_id):
        for seg_id,(label,seg) in enumerate(mpSegD.items()):
            if seg_id > cur_seg_id and seg['port_id'] == piano_id:
                return _beg_loc(seg), _end_loc(seg)

        return None,None
            
    with open(mult_play_json_fname) as f:
        mpSegD = json.load(f)

    ctlL = []
    
    for seg_id,(label,seg) in enumerate(mpSegD.items()):
        beg_loc = _beg_loc(seg)
        end_loc = _end_loc(seg)
        cur_piano_id = seg['port_id']
        cur_player_id = seg['player_id']

        # Get the current segment details
        playD = {'type':'play',
                 'seg_type':'simul',
                 'seg_label':seg['label'],
                 'seg_id':seg_id,
                 'piano_id':cur_piano_id,
                 'player_label':player_map[cur_player_id],
                 'player_seg_num':_player_seg_num(cur_player_id),
                 'bloc':beg_loc,
                 'eloc':end_loc}
                 
        ctlD = dict(loc_id=beg_loc, seg_id=seg_id, active_sf_id=cur_piano_id, cmdL=[ playD ])

        # Set the score-follower ctl records to the next location where they will be active
        for _,piano_id in PIANO_MAP.items():
            if piano_id != cur_piano_id:
                bloc,eloc = _next_bloc_eloc_on_piano(mpSegD,seg_id,piano_id)
                if bloc is not None:
                    ctlD['cmdL'].append( { 'type':'sf', 'sf_id':piano_id, 'bloc':bloc, 'eloc':eloc, 'enable_fl':True } )
                

        

        ctlL.append(ctlD)

    with open(out_ctl_json_fname,"w") as f:
        json.dump( { 'ctlL':ctlL }, f, indent=2 )

        
def gen_toc( mp_play_json_fname, score_csv_fname, toc_fname ):
    """ Generate an association file that links segments, sections, measures, locations """
    # dict(seg_id=None,seg_label,sectL=[],beg_meas,end_meas,beg_loc,end_loc, src, src_beg_meas, src_end_meas, src_beg_loc, src_end_Loc)
    # sectD = dict(label,beg_meas,end_meas,beg_loc,end_loc,src,src_beg_meas, src_end_meas, src_beg_loc, src_end_Loc)
         
    pass

def get_cfg():

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


if __name__ == "__main__":

    cfg = get_cfg()

    # Insert scriabin sections which must be score followed
    # and update the oloc and meas numbers to reflect the inserted material
    locMapD = gen_sf_score(cfg)

    # Generate a new preset file with updated locations.
    update_preset_catalog(cfg,locMapD['gutim'])

    # Generate a multi-player file containing one 'player' for each segment
    gen_multi_player(cfg,locMapD)

    print_mp_directory(cfg.out_mult_play_json_fname)

    gen_pgm_ctl_file(cfg.out_mult_play_json_fname,cfg.out_ctl_json_fname)

    
