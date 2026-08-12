import csv
import json
import pickle

from piano.model import (Note,GraceNote,Rest,GraceRest)

def drop_trailing_rests( seg_list_pkl_fname, out_json_fname, piano ):

    with open(seg_list_pkl_fname,'rb') as f:
        seg_list = pickle.load(f)

    segL = []
    for seg in seg_list.segments:
        eventL = []
        sectL = []
        color  = seg.section_list[0].player_color
        player = seg.section_list[0].player
        piano  = seg.section_list[0].piano
        
        for sect in seg.section_list:
            eventL += [se for se in sect.event_list]
            sectL.append(sect.section_label)

        if len(eventL) > 0:
            # id of first note/rest
            beg_se = next((se for se in eventL           if isinstance(se.event,(Note,GraceNote,Rest,GraceRest))),None)
            beg_evt_id = beg_se.event.id
            beg_meas_num = beg_se.meas_numb

            # id of first sounding note - or None if there is no sounding notes
            beg_se = next((se for se in eventL           if isinstance(se.event,(Note,GraceNote)) and se.event.has_onset),None)
            beg_note_id = None if beg_se is None else beg_se.event.id
            beg_meas_num = None if beg_se is None else beg_se.meas_numb

            # id of last note/rest
            end_se = next((se for se in reversed(eventL) if isinstance(se.event,(Note,GraceNote,Rest,GraceRest))),None)
            end_evt_id = end_se.event.id

            # id of last sounding note or None if there is no sounding notest
            end_se = next((se for se in reversed(eventL) if isinstance(se.event,(Note,GraceNote)) and se.event.has_onset),None)
            end_note_id = None if end_se is None else end_se.event.id
            end_meas_num = None if end_se is None else end_se.meas_numb

            # either both beg/end_note_id is None or neither is None.
            assert beg_note_id is not None and end_note_id is not None or (beg_note_id is None and end_note_id is None)

            segL.append(dict(seg_id=seg.id,
                             piano=piano.upper(),
                             color=color,
                             player=player,
                             beg_meas_num=beg_meas_num,
                             end_meas_num=end_meas_num,                             
                             beg_evt_id=beg_evt_id,
                             end_evt_id=end_evt_id,
                             beg_note_id=beg_note_id,
                             end_note_id=end_note_id,
                             sectL=sectL ))
            

    with open(out_json_fname,"w") as f:        
        json.dump(segL,f,indent=2)

def gen_toc( char_codeL, toc_csv_fname ):

    outL = []
    for c in char_codeL:
        fname = f"ref_section_toc_{c}.json"
        print(fname)
        with open(fname) as f:
            segL = json.load(f)

            outL += segL

    outL = sorted(outL,key=lambda x: x['beg_meas_num'])

    with open(toc_csv_fname,"w") as f:
        wtr = csv.DictWriter(f,fieldnames=['beg_meas_num','end_meas_num','seg_id','piano','color','player','beg_evt_id','end_evt_id','beg_note_id','end_note_id'])

        for d in outL:
            wtr.writerow(d)
        
        
if __name__ == "__main__":

    char_codeL = ['a','b','c']

    char_codeL = ['b','c']


    if True:
        for c in char_codeL:
            seg_list_pkl_fname = f"gutim_2/{c}/output/cache/seg_list.pkl"
            out_json_fname = f"ref_section_toc_{c}_1.json"

            drop_trailing_rests(seg_list_pkl_fname, out_json_fname, c)
        
    
    # gen_toc(char_codeL,"temp_toc.csv")
