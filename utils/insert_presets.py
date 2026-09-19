import json
import copy
def parse_tl_play_file( fn ):

    with open(fn) as f:
        tlD = json.load(f)

    sectLocD = {}
    for toc in tlD['tocL']:
        if (toc['section_id'],toc['port_id']) in sectLocD:            
            print("Duplicate section/piano:",toc['section_id'],toc['port_id'],toc['beg_loc'],toc['end_loc'],":",sectLocD[(toc['section_id'],toc['port_id'])] )
            
        sectLocD[(toc['section_id'],toc['port_id'])] = (toc['beg_loc'],toc['end_loc'])

    return sectLocD

def parse_preset( fn, piano_id, port_id ):
    with open(fn) as f:
        psD = json.load(f)

    return psD

def gen_new_frag( new_ps ):

    presetL = ['dry','a','b','c','d','f1','f2','f3','f4','g','ga','g1a','g1d'];
    
    psD = dict(fragId=None,
              begLoc=new_ps['beg_loc'],
              endLoc=new_ps['end_loc'],
              presetL=[ dict(order=0,alt_str="",preset_label=psl,play_fl=False) for psl in presetL ],
              presetN=len(presetL)  )

    for label,order,play_fl in new_ps['stateL']:
        ok_fl = False
        for ps in psD['presetL']:
            if ps['preset_label'] == label:
                ps['order'] = order
                ps['play_fl'] = play_fl
                ok_fl = True
                break

        if not ok_fl:
            print("The preset label ",label," was not found.")
            assert False

    return psD

def insert_preset( psD, new_ps ):
    # Insert 'new_ps' into the preset catalog psD and
    # remove or resize existing preset fragments
    # which may overlap with it
    
    new_bloc = ps['beg_loc']
    new_eloc = ps['end_loc']
    fragL = []
    for f in psD['fragL']:
        f_bloc = f['begLoc']
        f_eloc = f['endLoc']
        
        if f_eloc < new_bloc or f_bloc > new_eloc:
            pass # f does not overlap with new

        elif f_bloc >= new_bloc and f_eloc <= new_eloc:
            continue # f is inside of new - drop f

        elif f_bloc < new_bloc and f_eloc <= new_eloc:
            f['endLoc'] = new_bloc - 1  # end of f overlaps new, clip end of f

        elif f_bloc < new_eloc and f_eloc >= new_eloc:
            f['begLoc'] = new_eloc + 1  # begin of f overlaps with new, clip beg of f

        elif f_bloc < new_bloc and f_eloc > new_eloc:
            f['endLoc'] = new_bloc - 1  # new is inside f, split f into two parts
            
            f0 = copy.deepcopy(f)            
            f0['begLoc'] = new_eloc+1
            fragL.append(f0)
        else:
            
            print("The test for overlapping fragments is missing a case.",f_bloc,f_eloc,new_bloc,new_eloc)
            assert False
            
        fragL.append(f)

    fragL.append( gen_new_frag( new_ps ) )
    fragL = sorted(fragL,key=lambda x:x['begLoc'])
    for i,f in enumerate(fragL):
        f['fragId'] = i

    psD['fragL'] = fragL
    

if __name__ == "__main__":

    char_codeL = [ ('a',0),('b',1),('c',2)]
    tl_fname = "gutim_2/tl_play.json"

    # Create a new preset to be assigned to an entire section
    modL = [
        #                           label,order,play_fl
        dict(section="7147",port_id=2,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7149",port_id=2,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7151",port_id=0,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7156",port_id=2,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),        
        dict(section="7159",port_id=2,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),        
        dict(section="7163",port_id=1,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7165",port_id=0,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7167",port_id=0,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7168",port_id=2,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7170",port_id=2,stateL=[('dry',1,True)],beg_loc=None,end_loc=None),
        dict(section="7173",port_id=1,stateL=[('dry',1,True)],beg_loc=None,end_loc=None)        
    ]
    
    # Use the TL play file to associate sections with locations
    sectLocD = parse_tl_play_file(tl_fname)

    # Assign beg/end sections to the new presets
    for ps in modL:
        ps['beg_loc'],ps['end_loc'] = sectLocD[(ps['section'],ps['port_id'])]
        
        
    fullPsL = []
    for c,port_id in char_codeL:
        preset_fn = f"gutim_2/{c}/caw/presets.json"

        # get the presets for this piano
        psD = parse_preset(preset_fn,c.upper(),port_id)

        # for each new preset 
        for ps in modL:
            # if this new preset is on this piano
            if ps['port_id'] == port_id:
                insert_preset(psD,ps)

        out_preset_fn = f"gutim_2/{c}/caw/mod_presets.json"
        with open(out_preset_fn,'w') as f:
            json.dump(psD,f,indent=2)
        

