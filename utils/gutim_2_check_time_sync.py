import pickle

from piano.model import (Note,GraceNote,Rest,GraceRest)

def meas_dur_dict( fname ):

    with open(fname,'rb') as f:
        score = pickle.load(f)

    measTimeD = {}
    for m in score.measures:
        
        beg_timeL = []
        end_timeL = []
        for e in m.events:            
            if isinstance(e,(Note,GraceNote,Rest,GraceRest)):
                beg_timeL.append(e.abs_time)
                end_timeL.append(e.abs_time + e.duration_sec )
        measTimeD[m.number] = (min(beg_timeL),max(end_timeL) )

    return measTimeD

def compare_meas_dur(fnameL):

    measTimeD = {}
    beg_meas_num = 1
    end_meas_num = 0
    for fname in fnameL:
        mtD = meas_dur_dict( fname )
        for meas_num,(bsec,esec) in mtD.items():
            
            beg_meas_num = min(beg_meas_num,meas_num)
            end_meas_num = max(end_meas_num,meas_num)
            
            if meas_num not in measTimeD:
                measTimeD[meas_num] = []
            measTimeD[meas_num].append((bsec,esec))

    for meas_num in range(beg_meas_num,end_meas_num+1):
        bL = []
        eL = []
        dur_str = ""
        for bsec,esec in measTimeD[meas_num]:
            bL.append(bsec)
            eL.append(esec)
            dur_str += f"{esec-bsec:5.2f} "
            
        print(f"{meas_num} [ {dur_str}] {max(bL)-min(bL):5.2f} {max(eL)-min(eL):5.2f}" )
        
            
            
        


if __name__ == "__main__":

    char_codeL = [ 'a','b','c' ]

    fnameL = []
    fnameL = [ f"gutim_2/{c}/output/cache/assign_sustain.pkl" for c in char_codeL ]

    compare_meas_dur(fnameL)
