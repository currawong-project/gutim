import json
import pickle
import numpy as np

MIDI_NOTE_ON_STATUS = 0x90

NOTE_TYPE = 1         # 1=quarter 2=eigth 4=sixteenth
TICKS_PER_BEAT = 768
TICKS_PER_PERIOD = TICKS_PER_BEAT/NOTE_TYPE
MAX_PERIOD_DEV = 768/(5*NOTE_TYPE)

from piano.model import (Note, GraceNote)



def form_ref_port_dict(cfgD):

    def _form_meas_dict( score_pkl_fname ):
        # Return a dict which maps a measure number to measure info.
        
        with open(score_pkl_fname,"rb") as f:
            score = pickle.load(f)

        measD = {}
        abs_ticks = 0
        for m in score.measures:
            assert( m.events[0].tick == 0 )
            measD[m.number] = dict(beats=m.beats,
                                   beat_type=m.beat_type,
                                   abs_time=m.events[0].abs_time,
                                   abs_tick=abs_ticks,
                                   total_ticks=m.total_ticks)
            abs_ticks += m.total_ticks
            
        return measD

    def _form_note_abs_time_dict( score_pkl_fname ):
        # Return a dict which maps an event-id to the absolute time of a Note/Gracenote 
        with open(score_pkl_fname,"rb") as f:
            score = pickle.load(f)

        noteAbsTimeD = {}
        for m in score.measures:
            for e in m.events:
                if isinstance(e,(Note,GraceNote)):
                    noteAbsTimeD[ e.id ] = e.abs_time

        return noteAbsTimeD


    portD = {}
    for port,portCfgD in cfgD.items():
        score_pkl_fname            = portCfgD['score_pkl_fname']
        portCfgD['note_abs_timeD'] = _form_note_abs_time_dict( score_pkl_fname )
        portCfgD['measD']          = _form_meas_dict( score_pkl_fname )
        portD[port] = portCfgD

    return portD


def estimate_tempo( ref_portD, seqD ):

    def _get_ticks_and_secs( meas_note_refD, msgL ):
        tickL = []
        secL = []

        for m in msgL:
            if m['status'] == MIDI_NOTE_ON_STATUS:
                # If m['sec'] does not give absolute time, then lookup the absolute time in the reference
                # secL.append(  meas_note_refD['note_abs_timeD'][m['evt_id']] )
                secL.append( m['sec'] )
                tickL.append( meas_note_refD['measD'][ m['meas_num'] ]['abs_tick'] + m['tick'] )

        return tickL,secL

    def _calc_beat_index_dict( tickL, secL ):
        beat_idxD = {}
        for tick,sec in zip(tickL,secL):
            d_beat_tick = int(round(tick % TICKS_PER_PERIOD))
            if d_beat_tick < MAX_PERIOD_DEV:
                beat_idx = int(round(tick / TICKS_PER_PERIOD))
                if beat_idx not in beat_idxD:
                    beat_idxD[beat_idx] = []
                beat_idxD[beat_idx].append( sec )

        return beat_idxD
    
    def _estimate_period_secs( beat_idxD ):

        x = []
        y = []
        for beat_idx,secL in beat_idxD.items():
            for sec in secL:
                x.append(beat_idx)
                y.append(sec)

        slope = None
        bpm = None
        if sum(x)>0 and sum(y) > 0 and len(x) > 1 and len(beat_idxD)>1:
            slope, intercept = np.polyfit(x, y, 1)
            bpm = int(round(60/(slope*NOTE_TYPE)))
            print("PERIOD:",f"{slope:6.3f}","BPM:",bpm)

        return slope,bpm


        
    okN = 0
    tooShortN = 0
    for sect_label,d in seqD.items():
        port_id    = d['port_id']

        tickL,secL = _get_ticks_and_secs( ref_portD[port_id], d['msgL'] )
        beat_idxD  = _calc_beat_index_dict(tickL,secL)

        print(sect_label, "msgs:", len(d['msgL']), "notes:", len(tickL),  "beats:", len(beat_idxD), f"max sec: {max(secL):8.2f}" )
        period_sec,bpm = _estimate_period_secs(beat_idxD)
        if period_sec is not None:
            okN += 1
        else:
            if len(beat_idxD) <= 3:
                tooShortN += 1

        print("")

    print("Sections:",len(seqD.items()), "ok:", okN, "too short:", tooShortN )
    
    return seqD

def mod_tempo(tocD,seqD,out_spirio_mp_json_fname):

    def _mod_tempo( msgL, d_tempo_pct ):
        d_tempo_pct /= 100.0

        for m in msgL:
            sec = m['sec']
            m['sec'] = sec*d_tempo_pct

    for sect_label, d in tocD.items():
        _mod_tempo(seqD[sect_label]['msgL'],d['mod_tempo_pct'])
    
    with open(out_spirio_mp_json_fname,"w") as f:
        json.dump(seqD,f,indent=2)
        

if __name__ == "__main__":

    #spirio_mp_fname = "gutim_2/spirio_mp.json"
    spirio_mp_fname = "gutim_2/spirio_mp_mod_tempo.json"

    tocD ={
        "7063_A_90_SP":{ 'mod_tempo_pct':100.0 },
        "7126_A_171_SP":{ 'mod_tempo_pct':100.0 },
        "7128_A_175_SP":{ 'mod_tempo_pct':100.0 },
        "7139a_A_202_SP":{ 'mod_tempo_pct':100.0 },
        "7157_A_226_SP":{ 'mod_tempo_pct':100.0 },
        "7171_A_243_SP":{ 'mod_tempo_pct':100.0 },
        "7220_A_295_SP":{ 'mod_tempo_pct':100.0 },
        "7230a_A_304_SP":{ 'mod_tempo_pct':100.0 },
        "7250_A_328_SP":{ 'mod_tempo_pct':100.0 },
        
        "7024_B_39_SP":{ 'mod_tempo_pct':10.0 },
        "7034_B_55_SP":{ 'mod_tempo_pct':100.0 },
        "7063_B_90_SP":{ 'mod_tempo_pct':100.0 },
        "7079_B_122_SP":{ 'mod_tempo_pct':100.0 },
        "7086C_B_133_SP":{ 'mod_tempo_pct':100.0 },
        "7111_B_160_SP":{ 'mod_tempo_pct':100.0 },
        "7119_B_167_SP":{ 'mod_tempo_pct':100.0 },
        "7124_B_171_SP":{ 'mod_tempo_pct':100.0 },
        "7125b_B_178_SP":{ 'mod_tempo_pct':100.0 },
        "7141_B_204_SP":{ 'mod_tempo_pct':100.0 },
        "7163_B_234_SP":{ 'mod_tempo_pct':100.0 },
        "7184_B_255_SP":{ 'mod_tempo_pct':100.0 },   # 56-56
        "7212_B_290_SP":{ 'mod_tempo_pct':100.0 },   # 51-51
        "7217b_B_294_SP":{ 'mod_tempo_pct':100.0 },  
        "7225_B_299_SP":{ 'mod_tempo_pct':88.0 },   # 51->45
        "7238_B_314_SP":{ 'mod_tempo_pct':100.0 },
        "7246_B_325_SP":{ 'mod_tempo_pct':88.0 },  # 51->45
        "7250_B_328_SP":{ 'mod_tempo_pct':100.0 },
        
        "7136b_C_203_SP":{ 'mod_tempo_pct':100.0 },
        "7180_C_253_SP":{ 'mod_tempo_pct':100.0 },
        "7188_C_260_SP":{ 'mod_tempo_pct':100.0 },
        "7200_C_274_SP":{ 'mod_tempo_pct':100.0 },
        "7215_C_292_SP":{ 'mod_tempo_pct':100.0 },
        "7224_C_299_SP":{ 'mod_tempo_pct':100.0 },
        "7233_C_307_SP":{ 'mod_tempo_pct':100.0 },
        "7236_C_311_SP":{ 'mod_tempo_pct':100.0 },
        "7250_C_328_SP":{ 'mod_tempo_pct':100.0 },
    }

    cfgD= { 0:dict(score_pkl_fname="gutim_2/a/output/cache/assign_sustain.pkl"),
            1:dict(score_pkl_fname="gutim_2/b/output/cache/assign_sustain.pkl"),
            2:dict(score_pkl_fname="gutim_2/c/output/cache/assign_sustain.pkl") }

    ref_portD = form_ref_port_dict(cfgD)

    # read the Spirio MP JSON file 
    with open(spirio_mp_fname) as f:
        seqD = json.load(f)

    print(spirio_mp_fname)

    if False:
        estimate_tempo(ref_portD,seqD)

    if True:
        out_spirio_mp_json_fname = "gutim_2/spirio_mp_mod_tempo.json"
        mod_tempo(tocD,seqD,out_spirio_mp_json_fname);
    
