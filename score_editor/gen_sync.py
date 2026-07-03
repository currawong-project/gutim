import os
import sys
import csv
import json
import types
import pickle
from piano.model import (Note,GraceNote,Rest,GraceRest,SectionBoundary)
from Smith_waterman import smith_waterman


def form_sect_note_map( fname ):
    #
    # { section_id:[ {'uid':<>, 'tick':<>, 'midi':<>, sci_pitch:<> } ] }
    #
    
    def _midi_pitch( e ):
        acc = {'':0,'s':1,'b':-1}[e.accidental]
        return (e.octave+1) * 12 + {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[e.pitch_class] + acc
    
    def _sci_pitch( e ):
        acc = {'':'','s':'#','b':'b'}[e.accidental]
        return f"{e.pitch_class}{acc}{e.octave}"

    def _section_note_list( noteL, first_note_id, end_note_id ):

        seqL = []
        fl = False
        for n in noteL:
            if not fl and n['uid'] == first_note_id:
                fl = True
                seqL.append(n)
            elif fl:
                if n['uid'] == end_note_id:
                    break
                seqL.append(n)

        return seqL

    def _get_attributes( e ):
        return dict(oloc=e.oloc, dmark=e.dmark, dlevel=e.dlevel, dyn=e.dyn, even=e.even, tempo=e.tempo)
    
    with open(fname,"rb") as f:
        score = pickle.load(f)

    sectL = []
    noteL = []
    for m in score.measures:
        for e in m.events:
            if isinstance(e,SectionBoundary):
                sectL.append(dict(section_id=e.section_id, first_note_id=e.first_note_id))
            elif isinstance(e,(Note,GraceNote)):
                noteL.append(dict(uid=e.id,meas=m.number,tick=e.tick,midi=_midi_pitch(e),sci_pitch=_sci_pitch(e), onset_fl=e.has_onset, attrD=_get_attributes(e)))
            elif isinstance(e,(Rest,GraceRest)):
                noteL.append(dict(uid=e.id,meas=m.number,tick=e.tick,midi=0,sci_pitch="R", onset_fl=False, attrD=None))

    sectL = sorted( sectL, key=lambda x:x['section_id'])
    noteL = sorted( noteL, key=lambda x:(x['meas'],x['tick'],x['midi']))

    sectNoteD = {}
    for i,s in enumerate(sectL):
        if s['first_note_id'] is None:
            print(f"The section:{s['section_id']} has no anchor note.")
        else:
            next_sect_note_id = None if i+1>=len(sectL) else sectL[i+1]['first_note_id']
            nL = _section_note_list( noteL, s['first_note_id'], next_sect_note_id )
            if len(nL) == 0:
                print(f"No notes found for section:{s['section_id']} first note id:{s['first_note_id']}.")
                
            sectNoteD[ s['section_id'] ] = nL
        
    return sectNoteD

def parse_sect_map( fname, piano_char ):

    def _parse_csv( fname, piano_char ):

        outL = []
        with open(fname) as f:
            rdr = csv.DictReader(f)

            for r in rdr:
                if r['piano'].upper() == piano_char.upper():

                    new_id_str = ''.join([ c for c in r['new_id'] if c.isdigit() ])

                    orig_id = None if not r['orig_id'].isdigit() else r['orig_id']

                    outL.append( dict( meas=r['meas'],
                                       new_id=new_id_str,
                                       piano=r['piano'],
                                       orig_id=orig_id,
                                       octave=r['octave'],
                                       note=r['note'] ) )
        return outL

    csvL = _parse_csv(fname,piano_char)
    
    sectMap = {}
    for r in csvL:
        if r['orig_id'] is None or len(r['orig_id'])==0:
            print(f"An invalid base score id ({r['orig_id']}) was encountered. The new section {r['new_id']} is not being synced to base.")
        else:
            sectMap[int(r['new_id'])] = dict(orig_id=int(r['orig_id']), octave=int(r['octave']))
            
    return sectMap

def sync_sections( sectMap, base_sect_pitchD, ileav_sect_pitchD ):

    wndN = 15

    syncL = []
    
    # for each section pair
    for i_sect_id, d in sectMap.items():

        b_sect_id = d['orig_id']
        octave    = d['octave']
        
        if i_sect_id not in  ileav_sect_pitchD:
            print(f"The section id '{i_sect_id}' not found in the interleaved score. No sync. possible for this section.")            
        elif b_sect_id not in base_sect_pitchD:
            print(f"The section id '{b_sect_id}' not found in the base score.");
        else:

            # get the complete set of MIDI pitches for the interleaved and base section
            i_pitchL = [ d['midi']                 for d in ileav_sect_pitchD[i_sect_id] if d['midi']>0 ]
            b_pitchL = [ d['midi'] + (octave * 12) for d in  base_sect_pitchD[b_sect_id] if d['midi']>0 ]

            # it's possible that the length of the section could be less than the window length
            wN = min(wndN,min(len(b_pitchL),len(i_pitchL)))

            # Get the interleaved score section to slide against the base score section
            iSeqL = i_pitchL[0:wN]

            max_score = None
            max_idx   = None

            # slide iSeqL[] again b_pitchL[]
            for bi in range(0,len(b_pitchL)-wN):

                bSeqL = b_pitchL[bi:bi+wN]
                score,_ = smith_waterman(iSeqL,bSeqL)
                if max_score is None or score > max_score:
                    max_score = score
                    max_idx  = bi

            if max_score is None:
                print(f"{i_sect_id} {b_sect_id} Window ({wndN}) too long for sequence.")
            else:
                syncL.append( types.SimpleNamespace(**dict(i_sect_id=i_sect_id, b_sect_id=b_sect_id, octave_offset=octave, max_score=max_score, max_idx=max_idx) ))

    return syncL



def sync_print( syncL ):
    for d in syncL:
        if  d.max_score < 10:
            print(d.i_sect_id,d.b_sect_id,'dist:',d.max_score,'idx:',d.max_idx)

def get_synced_attributes( syncL, sectMap, base_sect_pitchD, ileav_sect_pitchD ):

    isect_attrD = {}
    total_mismatch = 0
    for s in syncL:        
        
        # get the complete set of Notes for the interleaved and base section
        i_idxL = [ i           for i,d in enumerate(ileav_sect_pitchD[s.i_sect_id])             if d['onset_fl'] and d['midi']>0 ]
        b_idxL = [ i+s.max_idx for i,d in enumerate( base_sect_pitchD[s.b_sect_id][s.max_idx:]) if d['onset_fl'] and d['midi']>0 ]

        # select the match window to be the shorter of the two sequences
        wndN = min(len(i_idxL),len(b_idxL))

        if wndN == 0:
            # if s.i_sect_id == 7023:
            #    breakpoint()
                
            print(f"{s.i_sect_id} {s.b_sect_id}. Zero length match window encountered. Skipping")
            continue

        # trim the index list to the window length
        i_idxL = i_idxL[:wndN]
        b_idxL = b_idxL[:wndN]

        # get the MIDI pitches for the two ileav and base sequences
        i_pitchL = [ ileav_sect_pitchD[s.i_sect_id][i]['midi']                          for i in i_idxL ]
        b_pitchL = [ base_sect_pitchD[ s.b_sect_id][i]['midi'] + (s.octave_offset * 12) for i in b_idxL ]

        # align the two sequences
        score,i_to_b_mapL = smith_waterman(i_pitchL,b_pitchL)

        assert len(i_to_b_mapL) == len(i_pitchL[:wndN])

        bNoteL = []
        mismatchN = 0
        
        # for each note in the i_leav section
        for i,i_note_idx in enumerate(i_idxL):

            # get the i_note
            i_note = ileav_sect_pitchD[s.i_sect_id][i_note_idx]

            # if this note was mapped to a b_note
            if i_to_b_mapL[i] is not None:

                # compute the b_note index
                b_note_idx = b_idxL[i_to_b_mapL[i]]

                # get the b_note
                b_note = base_sect_pitchD[s.b_sect_id][b_note_idx]

                # it's possible that mismatches will occur within an alignment
                if b_note['midi'] != i_note['midi']:
                    mismatchN += 1
                else:
                    # store the b_note attributes for eventual assignment to the i_note.
                    bNoteL.append(dict(note_id=i_note['uid'], base_id=b_note['uid'], attr=b_note['attrD']) )
            
        isect_attrD[s.i_sect_id] = dict(score=score/(2*wndN), mismatchN=mismatchN, noteL=bNoteL)
        total_mismatch += mismatchN
        score_pct = score/(2*wndN)
        print(f"{s.i_sect_id} {s.b_sect_id} len:{len(i_idxL):3} mis:{mismatchN:3} score:{score:3} pct:{score_pct:4.3f}  b_offset:{s.max_idx}")

    print("total mismatch:",total_mismatch)
    return isect_attrD
    

def main( base_score_fname, piano_char, ileav_score_fname, sect_map_csv_fname, out_fname):
    
    ileav_sect_pitchD = form_sect_note_map(ileav_score_fname)
    base_sect_pitchD  = form_sect_note_map(base_score_fname)
    sectMap           = parse_sect_map(sect_map_csv_fname, piano_char)
    
    syncL = sync_sections( sectMap, base_sect_pitchD, ileav_sect_pitchD )
    sync_print(syncL)

    isect_attrD = get_synced_attributes( syncL, sectMap, base_sect_pitchD, ileav_sect_pitchD )

    with open(out_fname,"w") as f:
        json.dump(isect_attrD,f,indent=2)

    

if __name__ == "__main__":

    base_score_fname     = "gutim_1/output/cache/assign_sustain.pkl"
    section_map_fname    = "gutim_2/gutim_2_sync_sheet_edited.csv"
    cache_name           = "timing"
    
    if len(sys.argv)>1:
        cache_name = sys.argv[1]

    for c in ['a','b','c']:
        ileav_score_fname    = f"gutim_2/{c}/output/cache/{cache_name}.pkl"
        out_dir              = f"gutim_2/{c}/editor"
        note_attr_json_fname = f"{out_dir}/note_attr.json"
        os.makedirs(out_dir,exist_ok=True)
        

        print(f"{c.upper()}:")
        main( base_score_fname, c, ileav_score_fname, section_map_fname, note_attr_json_fname)

    
