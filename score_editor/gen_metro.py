import sys
import csv
import pickle
from piano.model import (Note,Rest,MetronomeMarking)


def main( score_fname, out_fname ):

    with open(score_fname,'rb') as f:
        score = pickle.load(f)

        evtL = []
    for m in score.measures:
        for e in m.events:
            if isinstance(e,(MetronomeMarking,Note,Rest)):
                assert e.tick is not None and e.seq_id is not None
                evtL.append((m.number,e))

    evtL = sorted(evtL,key=lambda x:(x[0],x[1].tick,x[1].seq_id))
    
    print(len(evtL))
    pairL = []
    n = 0
    for i,(_,e) in enumerate(evtL):        
        if isinstance(e,MetronomeMarking):
            for _,ee in evtL[i:]:
                if isinstance(ee,(Note,Rest)):
                    pairL.append((e,ee))
                    break

    print(n,len(pairL))
    with open(out_fname,"w") as f:
        for metro,evt in pairL:
            f.write(f"{metro.id}: {evt.id}\n")

if __name__ == "__main__":

    cache_name = 'apply_arrows'

    if len(sys.argv) > 1:
        cache_name = sys.argv[1]
        

    for c in ['a','b','c']:
        score_fname    = f"gutim_2/{c}/output/cache/{cache_name}.pkl"
        out_fname      = f"gutim_2/{c}/edits/metronome.yaml"

        main(score_fname,out_fname)
