import csv

def parse_perf_csv( perf_csv_fname, srate=48000.0 ):
    # Input: 'type':non|nof,ctl, 'D0':<>, 'D1':<>, 'amicro':<>
    # Returns: [ {pitch:<>,vel:<>,microsec:<>,sample_idx,sust_fl,sost_fl,soft_fl ]
    perfL = []

    def amicro_to_sample_index( amicro, srate ):
        return int((amicro * srate)/1000000)

    def find_note_duration_micros( rL, idx ):
        r0         = rL[idx]
        assert r0['type'].strip() == 'non'
        
        pitch      = r0['D0']
        nof          = next((r for r in rL[idx+1:] if r['type'].strip() == 'nof' and int(r['D0'])==r0['D0']),None)
        dur_micros = None
        if nof is None:
            print(f"No note-off for note on {r0['D0']} at index {idx}.")
            # breakpoint()
        else:
            assert float(nof['amicro']) >= float(r0['amicro'])
            dur_micros = float(nof['amicro']) - float(r0['amicro'])

        return dur_micros
        

    gateL = [0] * 128

    sust_fl = False
    soft_fl = False
    sost_fl = False

    
    with open(perf_csv_fname) as f:
        rdr = csv.DictReader(f)

        rL = [ r for r in rdr ]

        for ridx,r in enumerate(rL):

            sust0_fl = sust_fl
            soft0_fl = soft_fl
            sost0_fl = sost_fl
            
            r['D0'] = None if r['D0'] is None or not r['D0'].strip().isdigit() else int(r['D0'])
            r['D1'] = None if r['D1'] is None or not r['D1'].strip().isdigit() else int(r['D1'])

            if r['type'].strip() == 'non':

                # ignore double note-on's
                if gateL[ r['D0'] ] == 0:

                    perfL.append(dict(pitch=r['D0'],
                                      vel=r['D1'],
                                      microsec=int(r['amicro']),
                                      dur_microsec=find_note_duration_micros(rL,ridx),
                                      sample_idx=amicro_to_sample_index(int(r['amicro']),srate),
                                      sust_fl=sust_fl,
                                      sost_fl=sost_fl,
                                      soft_fl=soft_fl))
                    gateL[ r['D0'] ] = 1
                
            elif r['type'].strip() == 'nof':
                gateL[ r['D0'] ] = 0
            elif r['type'].strip() == 'ctl':
                if r['D0'] == 64:  # sustain
                    sust_fl = r['D1'] >= 64                    
                elif r['D0'] == 66:  # sostenuto
                    sost_fl = r['D1'] >= 64
                elif r['D0'] == 67:  # soft
                    soft_fl = r['D1'] >= 64
                elif r['D0'] is None:
                    pass
                else:
                    assert(0)
                

            if False:
                if sust_fl != sust0_fl:
                    print(f"Sust:{'down' if sust_fl else 'up'}")
                if soft_fl != soft0_fl:
                    print(f"Soft:{'down' if soft_fl else 'up'}")
                if sost_fl != sost0_fl:
                    print(f"Sost:{'down' if sost_fl else 'up'}")
                
    return perfL

def parse_perf_csv_2( perf_csv_fname, srate=48000.0 ):
    # Input: 'sec','status','d0','d1'
    # Returns: [ {pitch:<>,vel:<>,microsec:<> ]
    perfL = []

    def amicro_to_sample_index( amicro, srate ):
        return int((amicro * srate)/1000000)

    gateL = [0] * 128

    sust_fl = False
    soft_fl = False
    sost_fl = False

    
    with open(perf_csv_fname) as f:
        rdr = csv.DictReader(f)

        for r in rdr:

            sust0_fl = sust_fl
            soft0_fl = soft_fl
            sost0_fl = sost_fl
            
            r['d0'] = None if r['d0'] is None or not r['d0'].strip().isdigit() else int(r['d0'])
            r['d1'] = None if r['d1'] is None or not r['d1'].strip().isdigit() else int(r['d1'])
            sec = float(r['sec'])
            micros = int(sec*1000000.0)
            status = int(r['status'])

            if status == 144:

                # ignore double note-on's
                if gateL[ r['d0'] ] == 0:

                    perfL.append(dict(pitch=r['d0'],
                                      vel=r['d1'],
                                      microsec=micros,
                                      sample_idx=amicro_to_sample_index(micros,srate),
                                      sust_fl=sust_fl,
                                      sost_fl=sost_fl,
                                      soft_fl=soft_fl))
                    gateL[ r['d0'] ] = 1
                
            elif status == 128: # note-off
                gateL[ r['d0'] ] = 0
            elif status == 176: # ctl
                if r['d0'] == 64:  # sustain
                    sust_fl = r['d1'] >= 64                    
                elif r['d0'] == 66:  # sostenuto
                    sost_fl = r['d1'] >= 64
                elif r['d0'] == 67:  # soft
                    soft_fl = r['d1'] >= 64
                elif r['d0'] is None:
                    pass
                else:
                    assert(0)
                

            if False:
                if sust_fl != sust0_fl:
                    print(f"Sust:{'down' if sust_fl else 'up'}")
                if soft_fl != soft0_fl:
                    print(f"Soft:{'down' if soft_fl else 'up'}")
                if sost_fl != sost0_fl:
                    print(f"Sost:{'down' if sost_fl else 'up'}")
                
    return perfL

def report_perf( perfL, N=None ):
    
    for i,p in enumerate(perfL):
        print(i,p['pitch'],p['vel'])
        if N is not None and i>=N:
            break
