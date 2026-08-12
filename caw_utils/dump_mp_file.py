import sys
import os
import json

from const import (PIANO_MAP,MIDI_NOTE_ON_STATUS,MIDI_NOTE_OFF_STATUS)

def parse_mp_file( fname ):

    def _parse_id( evt_id ):

        def _sci_pitch(s):
            if s[1] == 's':
                s = '#'.join(s.split('s'))
            return s
        
        voice_fl = False
        type_label = None
        
        if evt_id[:2] == 'dp':
            meas_idx = 2
            type_label = "damp"
            
        elif evt_id [:2] == 'sp':
            meas_idx = 2
            type_label = "sost"
            
        elif evt_id[:2] == 'ng':
            meas_idx = 2
            voice_fl = True
            type_label = "grace"
            
        elif evt_id[:1] == 'n':
            meas_idx = 1
            voice_fl = True
            type_label = "note"
        
        else:
            print("Unknown event id prefix:",evt_id)
            assert False

        prefix = evt_id.split("_")
        # print(evt_id,prefix)
        meas_num  = int(prefix[0][meas_idx:])
        voice_id  = None
        sci_pitch = None
        rval      = None
        if voice_fl:
            voice_id = int(prefix[1][0:1])
            sci_pitch = _sci_pitch(prefix[1][1:-1])
            rval      = prefix[1][-1]
            
        return type_label,meas_num,voice_id,sci_pitch,rval
        

    with open(fname) as f:
        mpD = json.load(f)

    for label,segD in mpD.items():
        for i,msg in enumerate(segD['msgL']):
            type_label,meas_num,voice_id,sci_pitch,rval = _parse_id(msg['evt_id'])
            msg['type_label'] = type_label
            msg['meas_num'] = meas_num
            msg['voice_id'] = voice_id
            msg['sci_pitch'] = sci_pitch
            msg['rval']      = rval

            #print(msg['evt_id'],meas_num,voice_id,sci_pitch,rval)
            
    return mpD

def print_mp_file(mpD,skip_note_off_fl):

    def is_note_off(m):
        return (m['status'] == MIDI_NOTE_ON_STATUS and m['d1']==0) or (m['status']==MIDI_NOTE_OFF_STATUS)
    
    pianoMap = { v:k for k,v in PIANO_MAP.items() }
    
    for seg_label,segD in mpD.items():
        print(f"player: {segD['player_id']} sect: {seg_label} {pianoMap[segD['port_id']]} ")

        meas_num = -1
        for m in segD['msgL']:
            if m['meas_num'] > meas_num:
                print("meas:",m['meas_num'])
                meas_num = m['meas_num']

            if is_note_off(m) and skip_note_off_fl:
                continue
            
            note_info = ""
            if m['type_label'] in ['note','grace']:
                rval = " " if is_note_off(m) else m['rval']
                note_info = f"v{m['voice_id']} {m['sci_pitch']:3} {m['rval']}"
                
            d1 = "" if is_note_off(m) else m['d1']
                
            print(f"{m['type_label']:5} {m['sec']:6.3f} ch:{m['ch']:1} {m['status']:3} {m['d0']:3} {d1:3} : {note_info} ")
                
        

    
if __name__ == "__main__":

    skip_note_off_fl = True
    ifn_param = None
    if len(sys.argv) > 1:
        ifn_param = sys.argv[1]
        

    if ifn_param is None:
        print("No input file name.")

    else:

        mpD = parse_mp_file(ifn_param)

        print_mp_file(mpD,skip_note_off_fl)
        
    
