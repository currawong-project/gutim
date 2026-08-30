import os
import csv
import json
import yaml
import const

def score_to_loc_pitch_map( score_csv_fname ):
    with open(score_csv_fname) as f:
        rdr = csv.DictReader(f)

        noteIdLocMapD = {}
        locPitchMapD  = {}
        for r in rdr:
            note_id = r['note_id']
            if note_id is not None and len(note_id.strip()) > 0:
                
                assert note_id not in noteIdLocMapD
                                
                loc = int( r['oloc'] )                    
                noteIdLocMapD[ note_id ] = loc

                if loc not in locPitchMapD:
                    locPitchMapD[ loc ] = []
                locPitchMapD[ loc ].append( int(r['d0']) )

    return noteIdLocMapD, locPitchMapD

def parse_monitor_state_yaml( fname, portNoteIdLocMapD, portLocPitchMapD ):


    def _parse_source( src ):
        
        attrSet = set(["note-on","note-off","damp-up","sost-up","all-keys-up","all-pedals-up"])
        
        port_id = const.PIANO_MAP[ src['piano'] ]

        if src['beg_primer'] not in portNoteIdLocMapD[port_id]:
            print(f"Begin note-id {src['beg_primer']} not in {port_id}.")
            return None
        
        if src['end_primer'] not in portNoteIdLocMapD[port_id]:
            print(f"End note-id {src['end_primer']} not in {port_id}.")
            return None

        # get the trigger primer range
        beg_loc   = portNoteIdLocMapD[port_id][ src['beg_primer'] ]
        end_loc   = portNoteIdLocMapD[port_id][ src['end_primer'] ]
        
        src_label = src['label']
        
        attrL   = []

        # get the trigger attribute flags
        for attr in src['trigger']:

            if attr not in attrSet:
                print(f"The attribute {attr} is not valid.")
                return None

            attrL.append(attr)

        # get the pitches assocated with all the notes in the primer range 
        pitchL = []
        for loc in range(beg_loc,end_loc+1):
            pitchL += portLocPitchMapD[port_id][loc]

        # get the min duration of the all-key-up and all-pedal-up state
        up_min_dur_ms = 0
        if 'up_min_dur_ms' in src:
            up_min_dur_ms = src['up_min_dur_ms']

        # get the length of time to delay firing the trigger event after the trigger is detected
        trig_delay_ms = 0
        if 'trig_delay_ms' in src:
            trig_delay_ms = src['trig_delay_ms']


        return dict(port_id        = port_id,
                    label          = src_label,
                    beg_primer_loc = beg_loc,
                    end_primer_loc = end_loc,
                    attrL          = attrL,
                    pitchL         = pitchL,
                    up_min_dur_ms  = up_min_dur_ms,
                    trig_delay_ms  = trig_delay_ms )
        

    outL = []
    tgt_label_set = set()
    with open(fname) as f:
        tgtL = yaml.safe_load(f)

        # for each target description
        for tgt in tgtL:

            src_label_set = set()
            target_label = tgt['target']
            
            if target_label in tgt_label_set:
                print("A duplicate target label:",target_label,"was encountered.")
                assert False
                
            tgt_label_set.add(target_label)
            
            # create a target record
            tgtD = dict( target_label = target_label,
                         id           = tgt['id'],
                         sourceL      = [] )


            # get each target trigger source
            for src in tgt['sources']:

                r = _parse_source(src)

                if r['label'] in src_label_set:
                    print("A duplicate 'source' label:",r['label']," was encountered in the target:",target_label)
                    assert False
                
                if r is not None:
                    tgtD['sourceL'].append( r )
                    
            outL.append(tgtD)

        return outL


def set_target_player_id(tgtL,mpD):

    for tgt in tgtL:

        fl = False;
        for mp_label,d in mpD.items():
            if tgt['target_label'] == mp_label:
                tgt['id'] = d['player_id']
                fl = True
                break

        if not fl:
            print(f"The target id for the target label {tgt['target_label']} was not found.")
            
                
    return tgtL
            
def concat_spirio_mp_files( src_fileL ):

    mpD      = {}
    label_id = 0
    
    for fname in src_fileL:
        
        with open(fname) as f:
            smD = json.load(f)

        for label,d in smD.items():
            assert label not in mpD
            d['player_id']  = label_id
            mpD[label]     = d
            label_id      += 1

    return mpD

def check_for_duplicate_target_labels(tgtL):

    labelSet = set()
    for tgt in tgtL:
        if tgt['target_label'] in labelSet:
            return False
        labelSet.add(tgt['target_label'])

    return True


def write_output_file( fname, tgtL ):
    with open(fname,'w') as f:
        json.dump(tgtL,f,indent=2)
        

def write_spirio_mp_file( fname, mpD ):
    with open(fname, 'w') as f:
        json.dump(mpD,f,indent=2);

def write_fallback_btn_array( targetL, fallback_json_fname, btn_array_json_fname ):

    def _target_label_to_id( tgtL, tgt_label ):
        return next((tgt['id'] for tgt in tgtL if tgt['target_label'] == tgt_label ),None)

    # open the fallback cfg file 
    with open(fallback_json_fname) as f:
        fallbackL = json.load(f)
        
    # add the trigger id that matches the target label
    outL = []
    for d in fallbackL:
        tgt_idL = [ _target_label_to_id( tgtL, tgt_label ) for tgt_label in d['labelL'] ]
            
        outL.append(dict(title=d['title'],
                         meas=d['meas'],
                         dis_idL=tgt_idL,
                         valueL=tgt_idL))

    # write the btn_array_json fname
    with open(btn_array_json_fname,"w") as f:
        json.dump(outL,f,indent=2)
    
if __name__ == "__main__":    
    spirio_json_fname        = "gutim_2/spirio_mp.json"
    fallback_cfg_json_fname  = "gutim_2/fallback.json"
    out_json_fname           = "gutim_2/monitor_state.json"
    out_btn_array_json_fname = "gutim_2/btn_array_cfg.json"
    

    char_codeL        = [ 'a','b','c']
    portNoteIdLocMapD = {}
    portLocPitchMapD  = {}
    spirio_json_fnameL= []
    tgtL              = []

    for c in char_codeL:
        # get the port_id associated with this piano
        port_id = const.PIANO_MAP[c.upper()]

        # read the score file
        score_csv_fname = f"gutim_2/{c}/caw/score.csv"

        # form a noteid-loc and loc-pitch map for each score (this is needed to map trigger note-id's to score locations)
        portNoteIdLocMapD[port_id], portLocPitchMapD[ port_id ] = score_to_loc_pitch_map( score_csv_fname )
    
    for c in char_codeL:

        # get the individual sprio_mp json file for this piano
        spirio_json_fnameL.append(f"gutim_2/{c}/caw/spirio_mp.json")

        # get the trigger yaml name for this piano
        trig_yaml_fname = f"gutim_2/{c}/output/trigger.yaml"
        
        if os.path.isfile(trig_yaml_fname):
            # parse the trigger file and add the result to the target list
            print("Processing:",trig_yaml_fname)
            tgtL  += parse_monitor_state_yaml(trig_yaml_fname, portNoteIdLocMapD, portLocPitchMapD)
        else:
            print(f"The 'trigger.yaml' file '{trig_yaml_fname}' was not found.")


    # check that there are no duplicate target labels in tgtL:[]
    assert check_for_duplicate_target_labels(tgtL)
    
    # Concatenate the sprio multi-player files from A,B and C
    mpD = concat_spirio_mp_files( spirio_json_fnameL )

    # Assign MP player_id's to each target by looking up the target label in the Spirio MP file
    tgtL  = set_target_player_id(tgtL,mpD)

    # Get the unique port id's
    portL = sorted(list(set([ s['port_id'] for t in tgtL for s in t['sourceL']])))

    # Form the output file header
    hdr   = dict(portL=portL, targetL=tgtL)

    # Write the KSM cfg. file
    print("Writing KSM file:",out_json_fname)
    write_output_file( out_json_fname, hdr )

    # Write the Sprio MP file
    write_spirio_mp_file( spirio_json_fname, mpD )

    # Write the fallback button array file
    write_fallback_btn_array(tgtL, fallback_cfg_json_fname, out_btn_array_json_fname)
