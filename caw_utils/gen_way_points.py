#
# Way Point Sequence Features:
# 1-4 notes that are unique to the segment and relatively: loud, long, and in low density areas
# Maximum time width of 2 seconds.

# 1. establish the avg. dynamic level of each measure - this will be used as the loudness reference.
# 2. Form a histogram of all 1,2,3,4 note sequences in the segment with a maximum width of 2 seconds.
# 3. Drop all sequences that are not unique.
# 4. Score the sequences on loudness, duration, density.
# 5. Pick the final sequences based on score and coverage.

import csv
import json
import types

from const import (SCORE_CSV_TITLES)

def parse_score_csv( fname ):

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
            for title,type_code in SCORE_CSV_TITLES:
                r[title] = _parse_value(r[title].strip(),type_code)

            # drop any rows that are not note-on
            if r['status'] is not None and r['status'] == 144:
                rowL.append(types.SimpleNamespace(**r))

    return rowL


        

def find_unique_triple_sequences( wnd_cnt, scoreL, bloc, eloc, use_dyn_criteria_fl = False ):

    def _get_score_index_span( scoreL, bloc, eloc ):
        
        # get index of first and last score rows in this segment
        bi   = next((i for i,r in enumerate(scoreL) if r.oloc == bloc),None)    
        ei   = next((i for i,r in enumerate(scoreL) if r.oloc == eloc),None)

        # advance to the last row that references eloc
        while ei<len(scoreL) and scoreL[ei] == eloc:
            ei += 1
        ei -= 1
        return bi,ei
        
    def _avg_dyn_level( scoreL ):        
         dynL = [ r.d1 for r in scoreL ]
         assert len(dynL) > 1
         return sum(dynL)/len(dynL)
    
    def _calc_dlevel( quad_seqL ):
        dlevelL = [ d1 for _,_,d1,_,_ in quad_seqL ]
        assert len(dlevelL) > 1
        return sum(dlevelL)/len(dlevelL)

    def _no_repeat_notes( quad_seqL ):
        noteSet = set([d0 for _,d0,_,_,_ in quad_seqL])
        return len(noteSet) == len(quad_seqL)

    def _grace_filter( quad_seqL ):
        graceN = len([ grace for _,_,_,grace,_ in quad_seqL ])
        # all notes are grace notes or no notes are grace notes
        return graceN == len(quad_seqL) or graceN == 0
    

    
    seqD = {}

    # get the beg/end index of the segment
    bi,ei = _get_score_index_span(scoreL,bloc,eloc)
    
    # get the avg. dyn level for this segment
    min_dlevel = _avg_dyn_level(scoreL[bi:ei+1])

    tripleSeqL = []
    # for successive window in the bi-ei range
    for si in range(bi,ei+1):
        # form a list [ (loc,d0,d1) ] for this window
        quad_seqL = [ (scoreL[i].oloc,scoreL[i].d0,scoreL[i].d1,scoreL[i].grace,scoreL[i].sec) for i in range(si,min(si+wnd_cnt,ei)) ]

        dlevel_fl = True
        if use_dyn_criteria_fl:
            dlevel_fl = len(quad_seqL) == wnd_cnt and _calc_dlevel(quad_seqL) > min_dlevel
        
        # filter out windows that are too short, too quiet, have repeated notes, or mix grace and non-grace notes
        if len(quad_seqL) == wnd_cnt and dlevel_fl and _no_repeat_notes(quad_seqL) and _grace_filter(quad_seqL):
            tripleSeqL.append([(loc,d0,sec) for loc,d0,_,_,sec in quad_seqL])

    vectD = {} # { vect:[] }

    # for each window
    for i,triple_seq in enumerate(tripleSeqL):

        # form a binary vector indicating the included notes
        vect = [0] * 128
        for _,midi_pitch,_ in triple_seq:
            vect[midi_pitch] = 1

        # vectD[] holds the tripleSeqL index associated with each vector pattern
        vect = tuple(vect)
        if vect not in vectD:
            vectD[ vect ] = []
        vectD[vect].append(i)

    # store the index of the triple sequences that are unique
    tripleSeqIdxL = [ idxL[0] for v,idxL in vectD.items() if len(idxL) == 1 ]
    
    # return only the unique sequences
    return [ dict(beg_loc=bloc, tripleL=tripleSeqL[i]) for i in tripleSeqIdxL ]

def is_unique( uniqueL, beg_loc, tripleL ):

    def _to_vect( tripleL ):
        vect = [0] * 128
        for _,d0,_ in tripleL:
            vect[d0] = 1
        return tuple(vect)
            
    def _form_vect_idx_map( uniqueL ):
        vectToIdxD = {}
        for i,d in enumerate(uniqueL):
            vect    = _to_vect(d['tripleL'])
            assert vect not in vectToIdxD
            vectToIdxD[vect] = i

        return vectToIdxD

    mod_fl     = False;
    vectToIdxD = _form_vect_idx_map(uniqueL)
    vect       = _to_vect(tripleL)

    # if the triple is unique
    if vect not in vectToIdxD:
        return True,True

    # the triple is not unique
    uniq_list_idx = vectToIdxD[vect]

    # if this 'beg_loc' is before the stored beg_loc
    # then the earlier beg_loc takes precedence
    if beg_loc < uniqueL[uniq_list_idx]['beg_loc']:
        uniqueL[uniq_list_idx]['beg_loc'] = beg_loc
        mod_fl = True
    
    return False,mod_fl
    
    

def find_unique_pitch_sequences( wnd_cnt, scoreL, bloc, eloc, use_dyn_criteria_fl = False, max_gap_sec = 2.0 ):

    def _find_gap_fill_search_locs( uniqueTripleL, max_gap_sec ):
        # Return a list of starting locations for new searches to fill in gaps in the unique list
        searchBegLocL = []
        gapDurL = []
        for i,d in enumerate(uniqueTripleL):
            
            triple0L = d['tripleL']
            triple1L = uniqueTripleL[i-1]['tripleL']
            
            if i > 0 and (triple0L[-1][2] - triple1L[-1][2]) > max_gap_sec:
                locL = sorted(triple1L) # sort on ascending location
                assert len(locL) >= 2
                # select the second location in the sorted list to start the gap fill search on 
                searchBegLocL.append( locL[1][0] )
                gapDurL.append( triple0L[-1][2] - triple1L[-1][2] )

        maxGapDurSec = 0 if len(gapDurL)==0 else max(gapDurL)
        return searchBegLocL,maxGapDurSec


    # find the set of sequences that are unique over the whole range
    uniqueL = find_unique_triple_sequences( wnd_cnt, scoreL, bloc, eloc )

    iterN = 0
    
    while True:    
        
        # Look for gaps longer than max_gap_sec in the sequence list and return the starting location
        # of a search that might fill it in. 
        searchLocL,maxGapDurSec = _find_gap_fill_search_locs( uniqueL, max_gap_sec )

        N = len(uniqueL)
        mod_cnt = 0
        
        # For each identified gap search starting location
        for beg_search_loc in searchLocL:
            
            # locate all unique sequeces beginning with beg_search_loc
            candUniqueL = find_unique_triple_sequences( wnd_cnt, scoreL, beg_search_loc, eloc )

            # it's possible that some candidates were found earlier - don't store them again
            for d in candUniqueL:

                # evaluate the uniqueness of tripleL and possibly modify the stored beg_loc if this beg_loc is earlier
                store_fl,mod_fl = is_unique(uniqueL,d['beg_loc'],d['tripleL'])

                # if the tripleL is unique then store it
                if store_fl:
                    uniqueL.append(d)
                    
                # if a previously stored beg_loc was modified
                if mod_fl:
                    mod_cnt += 1

        iterN += 1
                    
        # if uniqueL was not changed during this iteration then we are done
        if mod_cnt == 0 and len(uniqueL) == N:
            print(bloc,eloc,"N:",len(uniqueL)," gaps:",len(searchLocL),f"max gap:{maxGapDurSec:5.2f}","iter:",iterN)
            break

    # drop the 'sec' field from 'tripleL' to form 'pairL'.
    uniquePairL = [ dict(beg_loc=d['beg_loc'],pairL=[(loc,d0) for loc,d0,_ in d['tripleL']]) for d in uniqueL ]

    return uniquePairL
 

        

def gen_way_points_for_all_segments( cfg ):

    seg_wpD = {} # { seg_id:way_pointL }
    
    def _get_seg_loc_span( seg_r ):
        play_r = next((pr for pr in seg_r['cmdL'] if pr['type'] == 'play'),None)
        return seg_r['seg_id'],play_r['seg_label'],play_r['bloc'],play_r['eloc']

    # read the score
    scoreL = parse_score_csv(cfg.score_csv_fname )

    # read the pgm ctl file
    with open(cfg.pgm_ctl_json_fname) as f:
        pgmCtl = json.load(f)

    # for each segment
    for seg_r in pgmCtl['ctlL']:
        seg_id,seg_label,bloc,eloc = _get_seg_loc_span(seg_r)
        if bloc > 0 and eloc> 0:
            

            # get a list of way ponts as [ (loc,midi_pitch) ] for this segment
            uniqueSeqL = find_unique_pitch_sequences(cfg.wnd_max_cnt,scoreL,bloc,eloc)

            # store the seg_id:way point map
            seg_wpD[ seg_id ] = uniqueSeqL


            
    with open(cfg.way_point_json_fname,"w") as f:
        json.dump(seg_wpD,f,indent=2)
    


if __name__ == "__main__":

    pgm_ctl_json_fname = "gutim_1/caw/pgm_ctl.json"
    score_csv_fname    = "gutim_1/caw/score.csv"
    way_point_json_fname = "gutim_1/caw/way_point.json"
    
    cfgD = dict(pgm_ctl_json_fname=pgm_ctl_json_fname,
                score_csv_fname = score_csv_fname,
                way_point_json_fname = way_point_json_fname,
                wnd_min_cnt = 1,
                wnd_max_cnt = 4)

    cfg = types.SimpleNamespace(**cfgD)

    gen_way_points_for_all_segments(cfg)

    
