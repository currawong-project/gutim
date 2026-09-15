import json

def parse_preset( fn, piano_id, port_id ):
    with open(fn) as f:
        psD = json.load(f)

    psLocL = []
    for f in psD['fragL']:
        beg_loc = f['begLoc']
        end_loc = f['endLoc']
        psL = []
        labelL = [(d['order'],d['preset_label']) for d in f['presetL'] if d['order']>0]
        
        psLocL.append(dict(beg_loc=beg_loc,end_loc=end_loc,labelL=labelL,piano_id=piano_id,port_id=port_id,meas=None,sec=None,pitch=None))
        
    return psLocL              

def parse_tl_play_file( fn ):

    with open(fn) as f:
        tlD = json.load(f)

    portLocD={0:{},1:{},2:{}}
    for m in tlD['msgL']:
        if m['loc'] >= 0 and m['status']==144 and m['d1']>0:
            
            if m['loc'] not in portLocD[ m['port_id' ] ]:
                portLocD[ m['port_id' ] ][ m['loc'] ] = dict(meas=m['meas_numb'],
                                                              sec=m['sec'],
                                                              sci_pitchL=[ m['sci_pitch'] ])
            else:
                portLocD[ m['port_id' ] ][ m['loc'] ]['sci_pitchL'].append( m['sci_pitch'])
                
                                        
    return portLocD

def get_tl_info_from_loc( portLocD, port_id, loc ):

    if loc not in portLocD[port_id]:
        print(f"loc:{loc} not found for piano:{port_id}.")
    else:
        meas = portLocD[port_id][loc]['meas']
        sec  = portLocD[port_id][loc]['sec']
        pitch= " ".join(portLocD[port_id][loc]['sci_pitchL'])

        return meas,sec,pitch

if __name__ == "__main__":

    char_codeL = [ ('a',0),('b',1),('c',2)]
    tl_fname = "gutim_2/tl_play.json"

    portLocD = parse_tl_play_file(tl_fname)

    fullPsL = []
    for c,port_id in char_codeL:
        preset_fn = f"gutim_2/{c}/caw/presets.json"

        psLocL = parse_preset(preset_fn,c.upper(),port_id)

        for ps in psLocL:
            meas,sec,pitch = get_tl_info_from_loc(portLocD,port_id,ps['beg_loc'])

            ps['meas'] = meas
            ps['sec'] = sec
            ps['pitch'] = pitch


        fullPsL += psLocL

    fullPsL = sorted(fullPsL,key=lambda x:x['sec'])
    for ps in fullPsL:
        ps_str = " ".join([f"{order}:{label}" for order,label in ps['labelL']])
        print(f"{ps['meas']:3} {ps['piano_id']}  {ps['beg_loc']} {ps['sec']:6.2f} {ps_str:30} {ps['pitch']}")

            
        
