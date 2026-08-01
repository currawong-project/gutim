import json
import pickle

from piano.model import (Note,GraceNote)

class PNote:
    def __init__(self, meas_num, e ):
        self.meas_num    = meas_num
        self.note_id     = e.id
        self.sec         = e.abs_time
        self.loc         = e.loc     
        self.base_oloc   = None  # oloc from the orignal score
        self.base_frag_id= None  # frag_id from the original score
        self.new_frag_id = None  #  

def form_score_note_list( score ):

    noteL = []
    for m in score.measures:
        for e in m.events:
            if isinstance(e,(Note,GraceNote)) and e.has_onset:
              noteL.append( PNote( m.number, e ) )
              
    return sorted(noteL,key=lambda x:x.sec)

def form_note_oloc_map( noteAttrD ):
    note_olocD = {}
    for _,d in noteAttrD.items():
        for n in d['noteL']:
            assert n['note_id'] not in note_olocD
            note_olocD[n['note_id']] = n['attr']['oloc']

    return note_olocD
            
def assign_base_oloc_to_note( noteL, note_olocD ):
    missing_note_cnt = 0

    for n in noteL:
        if n.note_id not in note_olocD:
            missing_note_cnt += 1
        else:
            n.base_oloc = note_olocD[ n.note_id ]

    print(f"{100.0*missing_note_cnt/len(noteL):5.2f}% missing oloc.")

def assign_base_frag_id( noteL, base_catalog ):
    
    def _form_oloc_frag_id_list( base_catalog ):
        return sorted([ (d['endLoc'],d['fragId']) for d in base_catalog['fragL'] ])

    def _oloc_to_frag_id( key_oloc, oloc_frag_idL ):
        beg_loc = 0
        for end_loc,frag_id in oloc_frag_idL:            
            if beg_loc <= key_oloc and key_oloc <= end_loc:
                return frag_id
            beg_loc = end_loc + 1
        return None
            
        
    oloc_frag_idL = _form_oloc_frag_id_list( base_catalog )

    missing_oloc_cnt = 0
    missing_frag_id_cnt = 0
    frag_idL = []
    for n in noteL:
        if n.base_oloc is None:
            missing_oloc_cnt += 1
        else:
            n.base_frag_id = _oloc_to_frag_id( n.base_oloc, oloc_frag_idL )
            if n.base_frag_id is None:
                missing_frag_id_cnt += 1
            else:
                frag_idL.append(n.base_frag_id)

    print("Notes:",len(noteL),"- Misssing oloc:",missing_oloc_cnt, "frag id", missing_frag_id_cnt)
    print(f"{len(set(frag_idL))} of {len(oloc_frag_idL)} base frags found.")
    
def assign_new_frag_id( noteL ):

    def _is_new_frag_boundary(n0,n1):
        # if the later note has a valid base_frag_id that is not the same as the earlier note
        return n1.base_frag_id is not None and (n0.base_frag_id is None or n0.base_frag_id != n1.base_frag_id)

    newFragL = [] # [ { new_frag_id:<>, base_frag_id:<>, new_frag_beg_loc:<> } ]
    new_frag_id = 0
    for i,n in enumerate(noteL):
        if i > 0:
            if _is_new_frag_boundary(noteL[i-1],n):
                n.new_frag_id = new_frag_id
                new_frag_id += 1
                assert n.base_frag_id is not None
                assert n.loc is not None
                newFragL.append( dict(new_frag_id=new_frag_id, base_frag_id=n.base_frag_id, new_frag_beg_loc=n.loc) )
                new_frag_id += 1

    print(f"New frag list length: {len(newFragL)}")
    return newFragL

def create_new_catalog(base_catalog,newFragL):

    def _get_base_preset_list( base_catalog, base_frag_id ):
        for frag in base_catalog['fragL']:
            if frag['fragId'] == base_frag_id:
                return frag['presetL']

        return None

    fragL = []
    for d in newFragL:
        new_frag_id = d['new_frag_id']
        base_frag_id = d['base_frag_id']
        new_beg_loc = d['new_frag_beg_loc']

        presetL = _get_base_preset_list( base_catalog, base_frag_id )
        
        fragL.append( dict(fragId=new_frag_id,
                           begLoc=new_beg_loc,
                           endLoc=None,
                           presetL=presetL,
                           presetN=len(presetL)) )

    return dict(fragN=len(fragL),
                masterWetInGain=1.5,
                masterWetOutGain=1.0,
                masterDryGain=1.0,
                masterSyncDelayMs=400.0,
                fragL=fragL)
        
def update_frag_cntD(noteL, frag_cntD):
    
    # track how many times each base fragment was referenced.
    for n in noteL:
        if n.base_frag_id is not None:
            if n.base_frag_id not in frag_cntD:
                frag_cntD[ n.base_frag_id ] = 0
            frag_cntD[n.base_frag_id ] += 1

        

        
def gen_catalog( base_catalog_json_fname, note_attr_json_fname, score_pkl_fname, out_catalog_json_fname, base_frag_cntD ):
    # Use note_attr to find the oloc for each sync'd note in the the derived score (score_pkl_fname).
    # Use the base preset catalog (base_catalog_json_fname) to determine which preset fragments the olocs fall in.
    # Then create a new preset catalog file (out_cataolog_json_fname) which place the same presets
    # at the equivalent location in the new score but with updated locations.
    # The result of this is a new preset catalog file adjusted to fit the derived score.
    
    with open(base_catalog_json_fname) as f:
        base_catalog = json.load(f)

    with open(note_attr_json_fname) as f:
        note_attrD = json.load(f)

    with open(score_pkl_fname,"rb") as f:
        score = pickle.load(f)


    # Use derived score to form: noteL = [ {sec, loc, note_id} ] and sort on sec
    noteL = form_score_note_list(score)

    # With note_attr form: note_olocD = { note_id:oloc }
    # Maps derived notes to oloc.
    note_olocD = form_note_oloc_map( note_attrD )

    # Use note_id to set oloc in noteL = [ {sec, loc, note_id, oloc} ]    
    assign_base_oloc_to_note( noteL, note_olocD )

    # Use base_catalog to lookup frag_id based on oloc to form noteL = [ {sec,loc,note_id,oloc,frag_id} ]
    # 'frag_id' says which base fragment is active at each note.
    assign_base_frag_id(noteL,base_catalog)

    # Generate fragL by scanning noteL for changed frag_id and update noteL = [{sec,loc,note_id,oloc,frag_id,new_frag_id}]
    # This locates the boundaries of each new preset fragment.
    newFragL = assign_new_frag_id(noteL)

    # Generate catalogD from fragL
    newCatalogD = create_new_catalog(base_catalog,newFragL)

    # Track how many times each base_frag_id is used
    update_frag_cntD(noteL,base_frag_cntD)

    
    # Write catalogD
    with open(out_catalog_json_fname,'w') as f:
        json.dump(newCatalogD,f)


if __name__ == "__main__":

    def print_fragment_deployment_report( base_frag_cntD ):
        # print the number of time each base preset fragment was
        # copied to the new catalog.
        max_frag_id = max([ frag_id for frag_id,_ in base_frag_cntD.items()])

        for i in range(1,max_frag_id+1):
            n = base_frag_cntD[i]  if i in base_frag_cntD else 0
            print(i,n)
        

    base_catalog_json_fname = "gutim_1/scores/m1_458_trans_5.txt"

    char_codeL = ['a','b','c']

    base_frag_cntD = {}

    for char_code in char_codeL:

        note_attr_json_fname   = f"gutim_2/{char_code}/editor/note_attr.json"
        score_pkl_fname        = f"gutim_2/{char_code}/output/cache/assign_sustain.pkl"
        out_catalog_json_fname = f"gutim_2/{char_code}/scores/catalog.json"
        
        gen_catalog( base_catalog_json_fname, note_attr_json_fname, score_pkl_fname, out_catalog_json_fname, base_frag_cntD )


    if False:
        print_fragment_deployment_report(base_frag_cntD)
        
