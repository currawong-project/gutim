import csv
import json
import gen_part_2_files as gpf2

from const import (PIANO_MAP,PLAYER_MAP)

def read_toc( toc_txt_fname, sectNoteMapD ):
    
    from piano.build_seg_list import _parse_toc

    tocL = _parse_toc(toc_txt_fname)

    
    for toc in tocL:
        note_id = None
        
        if toc['section_label'] is None or toc['section_label'] == 'None':
            toc['section_label'] = toc['id']

        sect_name = toc['section_label']
        
        if sect_name not in sectNoteMapD:
            print("TOC ",sect_name, " missing in score.")
        else:
            note_id = sectNoteMapD[ sect_name ]

        toc['note_id'] = note_id

    return tocL

def form_scriabin_toc(tocL):

    scrTocD = {}
    
    for toc in tocL:
        if toc['type_id'] == 'X':
            scrTocD[ toc['section_label'] ] = dict(player=toc['player'],
                                                   piano=toc['piano'])

    return scrTocD


def read_score_file( score_csv_fname,prefixD, skip_sectD  ):

    def _is_string_valid( x ):
        return x is not None and len(x)>0
    
    scoreL = gpf2.read_caw_score_csv( score_csv_fname )

    noteSecMapD = {}   # note id       -> seconds,loc,sci_pitch,meas
    measNoteMapD = {}  # meas number   -> id of first note in each measure
    sectNoteMapD = {}  # section_label -> id of first note in each section

    cur_section = None
    for r in scoreL:
        
        # set the note_id prefix on each note
        if _is_string_valid(r.note_id) and _is_string_valid(r.src):            
            r.note_id = f"{prefixD[r.src]}_{r.note_id}"
            noteSecMapD[ r.note_id ] = (r.sec, r.oloc, r.sci_pitch, r.meas)

        # track the first note,sec in each measure
        if r.meas is not None and _is_string_valid(r.note_id):
            if r.meas not in measNoteMapD:
                measNoteMapD[r.meas] = (r.sec,r.note_id)
                
            if r.sec < measNoteMapD[r.meas][0]:                    
                measNoteMapD[r.meas] = (r.sec,r.note_id)

        # track the first note in each section
        if _is_string_valid(r.section):

            if r.section not in skip_sectD:
            
                # if the cur_section had no notes
                if cur_section is not None:
                    assert cur_section not in sectNoteMapD
                    sectNoteMapD[cur_section] = None

                cur_section = r.section

        # if there is a cur_section and this row has a valid note_id - then it will be the first valid note in the section
        elif cur_section is not None and _is_string_valid(r.note_id):
            assert cur_section not in sectNoteMapD
            sectNoteMapD[cur_section] = r.note_id  # set note_id for this section
            cur_section = None
            
            
    return scoreL,noteSecMapD,measNoteMapD,sectNoteMapD    


def form_mp_dict( fnameL  ):

    mpD = {}
    for (fname,prefix) in fnameL:
        with open(fname) as f:
            d = json.load(f)
            for k,v in d.items():
                assert k not in mpD

                # set a prefix on each 'evt_id' to distinguish scriabin from gutim
                for m in v['msgL']:
                    m['evt_id'] = f"{prefix}_{m['evt_id']}"
                
                mpD[k] = v

    print("total segments:",len(mpD))
    return mpD
            
def set_mp_time( mpD, noteSecMapD ):

    # for each MP segment
    for seg_label,hdrD in mpD.items():
        msgL = hdrD['msgL']

        # for each msg in this segment
        for i,m in enumerate(msgL):
            evt_id = m['evt_id']
            
            # if this evt is the first matching note in the segment
            if evt_id in noteSecMapD:
                start_sec,_,_,_ = noteSecMapD[evt_id]
                for m in msgL:
                    m['sec']      += start_sec
                    m['port_id']   = hdrD['port_id']
                    m['loc']       = noteSecMapD[m['evt_id']][1] if m['evt_id'] in noteSecMapD else -1
                    m['sci_pitch'] = noteSecMapD[m['evt_id']][2] if m['evt_id'] in noteSecMapD else ""
                    
                break

def concat_msg_list( mpD ):

    msgL = []
    for _,hdrD in mpD.items():
        msgL += hdrD['msgL']

    return sorted(msgL,key=lambda x:x['sec'])

def set_meas_numb( msgL, measNoteMapD ):

    noteToIdxD = { r['evt_id']:i for i,r in enumerate(msgL) }

    measL = []
    for meas_numb,(sec,note_id) in measNoteMapD.items():
        msg_idx = noteToIdxD[note_id]
        msgL[msg_idx]['meas_numb'] = meas_numb
        measL.append(dict(number=meas_numb,start_sec=sec,msg_idx=msg_idx))

    meas_num = 1
    for m in msgL:
        if 'meas_numb' not in m:
            m['meas_numb'] = meas_num
        elif m['meas_numb'] == meas_num+1:
            meas_num = meas_num+1

    return measL

def set_section_label(msgL,sectNoteMapD,noteSecMapD):

    noteSectMapD = { v:k for k,v in sectNoteMapD.items() }

    sectD = {}
    first_section_label = None

    # set the 'section_label' of the first event in each section
    for m in msgL:
        if m['evt_id'] in noteSectMapD:
            m['section_label'] = noteSectMapD[ m['evt_id'] ]
            assert m['section_label'] not in sectD

            if m['loc'] is None or m['loc'] == -1:
                print("Warning 'beg_loc' for section '",m['section_label'],"' is invalid.")

            _,_,_,beg_meas_numb = noteSecMapD[ m['evt_id'] ]
            
            sectD[ m['section_label'] ]= dict(port_id=None,
                                              player_id=None,
                                              section_id=m['section_label'],
                                              start_sec=m['sec'],
                                              beg_loc=m['loc'],
                                              end_loc=None,
                                              beg_sf_note_id=m['evt_id'],
                                              beg_meas_numb=beg_meas_numb,
                                              end_sf_note_id=None,
                                              end_meas_numb=None)
            if first_section_label is None:
                first_section_label = m['section_label']
            

    # fill in the section labels between the first events in each section
    cur_section_label = first_section_label
    for m in msgL:
        
        if 'section_label' not in m or m['section_label'] == cur_section_label:
            m['section_label'] = cur_section_label                            
        else:
            assert m['section_label'] is not None
            cur_section_label = m['section_label']
            

    max_loc = max([ m['loc'] for m in msgL if m['loc'] is not None and m['loc'] != -1 ])
    beg_locL = sorted([ d['beg_loc'] for _,d in sectD.items() if d['beg_loc'] is not None and d['beg_loc'] != -1 ])
    end_locL = [ beg_locL[i+1]-1 if i+1 < len(beg_locL) else max_loc  for i in range(len(beg_locL)) ]
    begEndMapD = { beg_loc:end_loc for beg_loc,end_loc in zip(beg_locL,end_locL) }
    locNoteMapD = { m['loc']:m['evt_id'] for m in msgL if m['loc'] is not None and m['loc'] != -1 }

    for _,d in sectD.items():

        d['end_loc'] = begEndMapD[d['beg_loc']]
        d['end_sf_note_id'] = locNoteMapD[ d['end_loc'] ]

        _,_,_,end_meas_numb = noteSecMapD[ d['end_sf_note_id'] ]        
        d['end_meas_numb'] = end_meas_numb

    return sectD


def report_sections( scoreL ):

    sectionL = []
    section = None
    for r in scoreL:
        if r.section is not None and len(r.section)>0:
            section = r.section
        if section is not None and r.note_id is not None and len(r.note_id)>0:
            sectionL.append(dict( section=section, note_id=r.note_id) )
            section = None

    for r in sectionL:
        print(r['section'],r['note_id'])


def set_port_and_player(tocL,msgL,tl_tocD):

    tocD = { d['section_label']:d for d in tocL }

    for m in msgL:
        m['port_id']   = PIANO_MAP[tocD[ m['section_label'] ]['piano']]
        m['player_id'] = PLAYER_MAP[tocD[ m['section_label'] ]['player']]['id']

    for sect_label,toc in tl_tocD.items():
        toc['port_id']   = PIANO_MAP[tocD[ toc['section_id'] ]['piano']]
        toc['player_id'] = PLAYER_MAP[tocD[ toc['section_id'] ]['player']]['id']
        toc['color']     = PLAYER_MAP[tocD[ toc['section_id'] ]['player']]['color']
        toc['player'] = tocD[ toc['section_id'] ]['player']
        toc['piano' ] = tocD[ toc['section_id'] ]['piano']
        toc['sectL' ] = [ sect_label ]
        toc['seg_label'] = sect_label

def drop_scriabin_from_score(scoreL):

    def _is_scriabin( d ):
        return d.section is not None and len(d.section)>0 and d.section[0:8] == "Scriabin"

    def _get_next_note_id( scoreL, idx ):
        for i in range(idx+1,len(scoreL)):
            r = scoreL[i]
            if r.note_id is not None and len(r.note_id)>0:
                return r.note_id
        assert False
        
    def _get_prev_note_id( scoreL, idx ):
        for i in range(idx-1,0,-1):
            r = scoreL[i]
            if r.note_id is not None and len(r.note_id)>0:
                return r.note_id
        assert False
        
    def _get_next_section_label( scoreL, idx):
        for i in range(idx+1,len(scoreL)):
            r = scoreL[i]
            if r.section is not None and len(r.section)>0:
                return r.section
        assert False

    scriabinMarkerL = []
    outL = []
    for i,d in enumerate(scoreL):
        if _is_scriabin(d):
            scriabinMarkerL.append(dict(label=d.section,
                                        next_note_id=_get_next_note_id(scoreL,i),
                                        prev_note_id=_get_prev_note_id(scoreL,i),
                                        next_section_label=_get_next_section_label(scoreL,i)))
        else:
            outL.append(d)
        
    return outL,scriabinMarkerL

def insert_scriabin_toc_markers(tl_tocD,scriabMarkL,skip_sectD, scriabinTocD ):

    def _form_mark_dict( scriabMarkL, skip_sectD ):
        markD = {}
        for mark in scriabMarkL:
            if mark['next_section_label'] in skip_sectD:
                section_label = skip_sectD[ mark['next_section_label'] ]
            else:
                section_label = mark['next_section_label']

            markD[section_label] = mark
            
        return markD

    markD = _form_mark_dict(scriabMarkL,skip_sectD);
    skip_sectD = { v:k for k,v in skip_sectD.items() }
    
    tocL = []
    scriab_cnt = 0
    for _,toc in tl_tocD.items():
        toc['type_id'] = 'gutim'
        if toc['section_id'] in markD:
            
            scriab_cnt +=1
            scriab_sect_label = markD[toc['section_id']]['label']

            if scriab_sect_label not in skip_sectD:

                mark = scriabinTocD[ scriab_sect_label ]

                tocL.append(dict(type_id='scriabin',
                                 section_id=scriab_sect_label,
                                 player=mark['player'],
                                 piano=mark['piano']))
        tocL.append(toc)

        
    print(scriab_cnt,"Scriabin sections located.")
    return tocL


def write_tl_player_file(msgL,tl_measL,tl_tocD, tl_json_fname ):

    tocL = sorted([ d for _,d in tl_tocD.items() ],key=lambda x:x['beg_loc'])
    
    hdr = dict(tocL=tocL,measL=tl_measL,msgL=msgL)

    with open(tl_json_fname,"w") as f:
        json.dump(hdr,f,indent=2)

def write_score_file( scoreL,out_score_csv_fname ):

    fieldnamesL = list(scoreL[0].__dict__.keys())

    with open(out_score_csv_fname,"w") as f:
        wtr = csv.DictWriter(f,fieldnamesL)

        wtr.writeheader()
        for r in scoreL:
            wtr.writerow(r.__dict__)
        
def write_caw_toc_file(tl_tocL,out_caw_toc_fname):

    tocL = []

    for seg_id,toc in enumerate(tl_tocL):
        if toc['type_id'] == 'gutim':
            tocL.append( dict(type_id=toc['type_id'],
                              seg_id=str(seg_id),
                              seg_label=toc['section_id'],
                              piano=toc['piano'],
                              color=toc['color'],
                              player=toc['player'],
                              beg_meas_num=toc['beg_meas_numb'],
                              end_meas_num=toc['end_meas_numb'],
                              beg_sf_note_id=toc['beg_sf_note_id'],
                              end_sf_note_id=toc['end_sf_note_id'],
                              sectL=toc['sectL']))
        elif toc['type_id'] == 'scriabin':
            toc['color']     = PLAYER_MAP[ toc['player'] ]['color']
            tocL.append(toc)

    with open(out_caw_toc_fname,"w") as f:
        json.dump(tocL,f,indent=2)


if __name__ == "__main__":

    # 0. DONE: use score to build a TOC: section,player_id,piano_id,start_note_id
    # 1. DONE: give each note_id in the MP player a prefix (gut|scr) based on it's section:
    # 2. DONE: give each note_id in the score a prefix based on it's source: 'gut','scr'
    # 3. DONE: get the note id of the start of each section in the MP player files
    # 4. DONE: get the time of each note_id from the score.
    # 4. DONE: find the start time of each MP player from the score.
    # 6. DONE: set the final time on each MP player message based on the section start time.
    # 7. DONE: concatenate the msgL from the three MP files into a single list and sort on time
    # 8. DONE: assign a measure numbers to messages
    # 9. DONE: assign player_id,port_id,section_label to messages based on the TOC

    out_tl_json_fname = "gutim_1/caw/tl_play.json"
    out_score_csv_fname = "gutim_1/caw/tl_score.csv"
    out_caw_toc_fname = "gutim_1/output/caw_toc.json"
    score_csv_fname   = "gutim_1/caw/score.csv"
    mp_json_fname     = "gutim_1/caw/multi_player.json"


    prefixD = { "Scriabin-4_Op74_3":"op3",
                "Scriabin-3_Op74_4":"op4",
                "gutim":"gut" }

    mp_json_fnameL = [
        ("gutim_1/caw/gutim_multi_play.json", "gut"),
        ("gutim_1/caw/Op74_3_multi_play.json","op3"),
        ("gutim_1/caw/Op74_4_multi_play.json", "op4")
        ]

    skip_sectD = { '1000':"Scriabin-3_Op74_4",'2000':"Scriabin-4_Op74_3" }
    
    # read the score and generate mappings
    scoreL,noteSecMapD,measNoteMapD,sectNoteMapD = read_score_file(score_csv_fname,prefixD,skip_sectD);


    #report_sections(scoreL)
    
    # read the TOC
    tocL = read_toc("gutim_1/scores/section_toc.txt",sectNoteMapD)

    scriabin_tocD = form_scriabin_toc(tocL)

    # read and concatenate the MP files for all sources
    mpD = form_mp_dict(mp_json_fnameL)

    # convert section times to global times in the MP player files
    # by shifting the start of each section to the start of the each section in the score
    # and set the score 'loc' on each event
    set_mp_time(mpD,noteSecMapD)

    # concatenate all the events into a single time ordered list
    msgL = concat_msg_list(mpD)

    # set the measure number on each event and generate the timeline player 'measL'
    tl_measL = set_meas_numb(msgL,measNoteMapD)

    # set the section label on each event and generate the timeline 'tocL'
    tl_tocD = set_section_label(msgL,sectNoteMapD,noteSecMapD)

    # set the port_id and player_id fields in the tc
    set_port_and_player(tocL,msgL,tl_tocD)

    # write the timeline_player control file
    write_tl_player_file(msgL,tl_measL,tl_tocD,out_tl_json_fname)

    # drop the scriabin markers from the score file and convert all section numbers to be numeric
    # (this is required by cwPianoScore.cpp)
    scoreL,scriabMarkL = drop_scriabin_from_score(scoreL)

    #for _,toc in tl_tocD.items():
    #    print(toc)

    # insert the scriabin sections into the toc as 'type_id'='scriabin'
    tl_tocL = insert_scriabin_toc_markers(tl_tocD, scriabMarkL, skip_sectD, scriabin_tocD)

    # write the score file
    write_score_file(scoreL,out_score_csv_fname)

    # write the toc file
    write_caw_toc_file(tl_tocL,out_caw_toc_fname)

    
