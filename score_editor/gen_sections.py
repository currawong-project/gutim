import sys
import csv
import pickle
from piano.model import (Note,Rest,GraceNote,GraceRest,SectionBoundary)


def main( score_fname, out_fname ):

    with open(score_fname,'rb') as f:
        score = pickle.load(f)

    # fill evtL[] with all SectionBoundaries,Note,Rest,GraceNote,GraceRest events.
    evtL = []
    for m in score.measures:
        for e in m.events:
            if isinstance(e,(SectionBoundary,Note,Rest,GraceNote,GraceRest)):
                assert e.tick is not None and e.seq_id is not None
                evtL.append((m.number,e))

    # sort the event list on meas,tick,seq_id
    evtL = sorted(evtL,key=lambda x:(x[0],x[1].tick,x[1].seq_id))
    
    print(len(evtL))
    pairL = []
    n = 0
    # for each event 
    for i,(_,e) in enumerate(evtL):
        # if this is a SectionBoundary
        if isinstance(e,SectionBoundary):
            for _,ee in evtL[i:]:
                # get the next note,rest as the first event contained in the section
                if isinstance(ee,(Note,Rest,GraceNote,GraceRest)):
                    pairL.append((e,ee))
                    break

    print(n,len(pairL))
    
    # Generate the output YAML file
    with open(out_fname,"w") as f:
        for metro,evt in pairL:
            f.write(f"{metro.id}: {evt.id}\n")

if __name__ == "__main__":

    cache_name = 'apply_tie_corrections'

    if len(sys.argv) > 1:
        cache_name = sys.argv[1]
    
    for c in ['a','b','c']:
        score_fname    = f"gutim_2/{c}/output/cache/{cache_name}.pkl"
        out_fname      = f"gutim_2/{c}/edits/sections.yaml"

        main(score_fname,out_fname)
