import pickle

from piano.model import (MetronomeMarking)

def read_metro_dict( fname ):
    
    metroD = {} # { metro_mark_id:tick }
    
    with open(fname,"rb") as f:
        score = pickle.load(f)
    
    for m in score.measures:
        for e in m.events:
            if isinstance(e,MetronomeMarking):
                metroD[e.id] = score.lookup(e.anchor_note_id).tick

    return metroD

def compare_metro_tick( label0, m0D, label1, m1D ):
    print(label0,"->",label1)
    for mid,tick in m0D.items():
        # all metro marksing in m0D must exist in m1D
        if mid not in m1D:
            print(mid," not in ",label1 )
        else:
            # check that the tick of matching metro marksing are the same
            if int(m1D[mid]) != int(tick):
                print(mid," : ",label0,tick," != ",label1,m1D[mid]," delta:", m1D[mid] - tick )
                
def report( metroD ):
    for i,(mid,tick) in enumerate(metroD.items()):
        print(i,mid,tick)
        if i > 10:
            break
    

if __name__ == "__main__":
    a_fname = "gutim_2/a/output/cache/timing.pkl"
    b_fname = "gutim_2/b/output/cache/timing.pkl"
    c_fname = "gutim_2/a/output/cache/timing.pkl"

    metro_aD = read_metro_dict(a_fname)
    metro_bD = read_metro_dict(b_fname)
    metro_cD = read_metro_dict(c_fname)

    # compare A->B and B->A to notice all possible missing metronome markings
    compare_metro_tick("A",metro_aD,"B",metro_bD)
    compare_metro_tick("B",metro_aD,"A",metro_bD)
    compare_metro_tick("A",metro_aD,"C",metro_bD)
    compare_metro_tick("C",metro_aD,"A",metro_bD)
    compare_metro_tick("B",metro_aD,"C",metro_bD)
    compare_metro_tick("C",metro_aD,"B",metro_bD)

    
