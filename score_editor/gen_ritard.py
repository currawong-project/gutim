import sys
import pickle
from piano.model import (Note,Rest,MetronomeMarking)

def main(score_fname,out_fname):

    with open(score_fname,"rb") as f:
        score = pickle.load(f)

    with open(out_fname,"w") as f:
        for rs in score.rit_spans:            
            f.write(f"{rs.id}:\n  end_metronome: {rs.end_metronome_id}\n  first_note: {None}\n  interpolation: linear\n  restore_tempo: {False}\n\n")
        
    

if __name__ == "__main__":

    cache_name = 'apply_metronome'

    if len(sys.argv) > 1:
        cache_name = sys.argv[1]
        

    for c in ['a','b','c']:
        score_fname    = f"gutim_2/{c}/output/cache/{cache_name}.pkl"
        out_fname      = f"gutim_2/{c}/edits/rit_spans.yaml"

        main(score_fname,out_fname)
