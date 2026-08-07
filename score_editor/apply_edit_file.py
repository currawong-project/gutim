import os
import json
import types
import pickle

from piano.model import MetronomeMarking


DYN_MAP = {
    's':0,
    'pppp-':1,
    'pppp':2,
    'pppp+':3,
    'ppp-':4,
    'ppp':5,
    'ppp+':6,
    'pp-':7,
    'pp':8,
    'pp+':9,
    'p-':10,
    'p':11,
    'p+':12,
    'mp-':13,
    'mp':14,
    'mp+':15,
    'mf-':16,
    'mf':17,
    'mf+':18,
    'f-':19,
    'f':20,
    'f+':21,
    'ff':22,
    'ff+':23,
    'fff':24,
    'fp': 25}


def parse_edit_file( edit_fname ):

    def _is_meas_row(r):
        return r[0:4]=='meas'
    
    def _meas_numb(r):
        return int(r.split(":")[1].split(' ')[0])

    def _parse_sost_pedal(meas_numb,ele_id,tokL):
        pedalD = dict(type='sost',depth=None)
        if tokL[0] == 'up':
            pedalD['depth'] = 0.0
        elif tokL[0] == 'down':
            pedalD['depth'] = 1.0
        else:
            print(f"meas:{meas_numb} id:{ele_id} : Unknown sostenuto pedal action:{tokL[0]}.")
            
        return pedalD

    def _parse_damp_pedal(meas_numb,ele_id,tokL):

        def _parse_depth(tok, depth ):
            if '='in tok:
                depth = float(tok.split('=')[1])
                assert depth in [0.0,0.5,1.0]
            return depth
        
        pedalD = dict(type='damp',depth=None,clear_depth=None,ramp_fl=False)

        for tok in tokL:
            if tok[:2] == 'up':
                pedalD['depth'] = _parse_depth(tok,0.0)
                
            elif tok[:4] == 'down':
                pedalD['depth'] = _parse_depth(tok,1.0)
                
            elif tok[:5] == 'clear':
                pedalD['clear_depth'] = _parse_depth(tok,0.0)
                
            elif tok == 'ramp':
                pedalD['ramp_fl'] = True

        return pedalD
        
    
    def _parse_pedal(meas_numb,ele_id,tokL):
        pedalD = None
        if tokL[0]=='damp':
            pedalD = _parse_damp_pedal(meas_numb,ele_id,tokL[1:])
        elif tokL[0]=='sost':
            pedalD = _parse_sost_pedal(meas_numb,ele_id,tokL[1:])
        else:
            print(f"meas:{meas_numb} id:{ele_id} : Unknown pedal type: {tokL[0]}.")

        # if tokL[-1] != 'ok':
        #    print(f"meas:{meas_numb} id:{ele_id} : {tokL[0]} pedal action not validated.")

        return pedalD
                                       
    def _parse_section(meas_numb, ele_id, tokL):
        assert tokL[0] == 'section'

        new_section_id = None
        
        if len(tokL) < 2:
            print(f"meas:{meas_numb} id:{ele_id} : Invalid section syntax.")
        else:    
            new_section_id =tokL[1]
        
        # if len(tokL)<3 or tokL[2].lower() != 'ok':
        #    print(f"meas:{meas_numb} id:{ele_id} : Section {new_section_id} not validated.")
            
        return new_section_id

    def _parse_metro(meas_numb, ele_id, tokL):
        assert tokL[0] == 'metro'

        metroD = None
        if len(tokL) != 4:
            print(f"meas:{meas_numb} id:{ele_id} : Invalid metro syntax. {':'.join(tokL)}")
        else:

            if tokL[-1] != 'ok':
                print(f"meas:{meas_numb} id:{ele_id} : Metro no 'ok'.")
            
            
            beat_unit = tokL[1]
            bpm       = int(tokL[2])

            assert beat_unit in ['h','q']
                            
            metroD = dict(beat_unit=beat_unit, bpm=bpm)

        return metroD
        

    def _parse_dyn(meas_numb, ele_id, tokL):
        assert tokL[0] == 'd'
        dmark = None

        # if this is a literal dynamic mark
        if len(tokL) == 2:
            if tokL[1] not in DYN_MAP:
                print(f"meas:{meas_numb} id:{ele_id} : Invalid dynamic mark:{tokL[1]}")
            else:
                dmark = tokL[1]

        # if this is a dyn. interpolator begin/end mark
        elif len(tokL) == 3:
            i = None
            prefix = None
            # if this is a begin marker
            if tokL[2] == '>':
                i = 1
                prefix = 'b'
            # if this is an end marker
            elif tokL[1] == '>':
                i = 2
                prefix = 'e'
            # if this marker is malformed
            else:
                print(f"meas:{meas_numb} id:{ele_id} : Syntax error : Invalid dynamic interpolator syntax.")

            # form the interpolator begin/end marker
            if i is not None:
                if tokL[i] not in DYN_MAP:
                    print(f"meas:{meas_numb} id:{ele_id} : Invalid dynamic mark:{tokL[1]}")

                # dmark = {b|e}_{dmark}
                dmark = f"{prefix}_{tokL[i]}"
                
        # If this dyn mark is malformed       
        else:
            print(f"meas:{meas_numb} id:{ele_id} : Syntax error : Invalid dynamic mark. {':'.join(tokL)}")

                
        return dmark

    def _parse_attributes(meas_numb, ele_id, line ):
        # Parse the editale attributes to the right of the '|' marker
        
        new_section_id = None
        dmark          = None
        pedalL         = []
        metroD         = None

        # strip off any EOL comments 
        line = line.split('#')[0].strip()
        
        for attr in line.split(' '):

            if len(attr.strip()) == 0:
                continue
        
            tokL = attr.split(":")

            if tokL[0] in ['damp','sost']:
                pedalD = _parse_pedal(meas_numb,ele_id,tokL)
                if pedalD is not None:
                    pedalL.append(pedalD)

            elif tokL[0] == 'section':
                new_section_id = _parse_section(meas_numb,ele_id,tokL)
            elif tokL[0] == 'metro':
                metroD = _parse_metro(meas_numb,ele_id,tokL)
            elif tokL[0] == 'd':
                dmark = _parse_dyn(meas_numb,ele_id,tokL)
            else:
                print(f"meas:{meas_numb} id:{ele_id} : Unknown attribute: {tokL[0]}.")
                
        return new_section_id, dmark, pedalL, metroD

    def _parse_const_fields( meas_numb, line ):

        def _parse_onset_flag( meas_numb, ele_id, tok ):
            onset_fl = None
            if len(tok) != 3 or tok[2] not in ['-','o']:
                print(f"meas:{meas_numb} id:{ele_id} : Syntax error invalid 'onset' flag: {tok}.")
            else:
                onset_fl = tok[2] == 'o'
            return onset_fl

        def _is_float(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        
        ele_id = None
        sec = None
        onset_fl = None
        
        tokL = [ t for t in line.split(" ") if t != '']

        if len(tokL) != 11:
            print(f"meas:{meas_numb} line:{line} : Syntax error : Invalid token count.")
        else:
            if tokL[6][0] not in [ 'n','r' ]:
                print(f"meas:{meas_numb} line:{line} : Syntax error : Invalid element id.")
            elif not _is_float(tokL[2]):
                print(f"meas:{meas_numb}, line:{line} : Syntax error : Invalid 'seconds' field: {tokL[2]}")
            else:
                onset_fl = _parse_onset_flag(meas_numb, tokL[6], tokL[10])
                if onset_fl is not None:
                    ele_id = tokL[6]
                    sec    = float(tokL[2])

        return ele_id, sec, onset_fl

    def _parse_event_line( meas_numb, line ):

        ele_id         = None
        sec            = None
        pedalL         = []
        new_section_id = None
        dmark          = None
        
        f0 = line.split("|")

        
        if len(f0) != 2:
            print(f"meas:{meas_numb} line:{line} : Syntax error: Invalid line split.")
        else:
            ele_id, sec, onset_fl = _parse_const_fields( meas_numb, f0[0] )

            if ele_id is not None:
                new_section_id, dmark, pedalL, metroD = _parse_attributes(meas_numb,ele_id,f0[1])

        
        return ele_id, sec, onset_fl, new_section_id, dmark, pedalL, metroD
        

    meas_numb = None
    attrL = []
    with open(edit_fname) as f:
        for line in f:

            # remove the trailing newline
            line = line.strip()

            # if this is a measure line
            if _is_meas_row(line):
                meas_numb = _meas_numb(line)
                
            else: # this must be an event line
                
                ele_id, sec, onset_fl, new_section_id, dmark, pedalL, metroD = _parse_event_line(meas_numb,line)
                
                attrL.append( dict(ele_id=ele_id,
                                   sec=sec,
                                   onset_fl=onset_fl,
                                   meas_numb=meas_numb,
                                   new_section_id=new_section_id,
                                   dmark=dmark,
                                   pedalL=pedalL,
                                   metroD=metroD))

    return attrL

def apply_dyn_interp( attrL ):

    def _form_interpolation_spans( attrL ):

        def _is_begin_mark(a):
            return a['dmark'] is not None and a['dmark'][0] == 'b'
        def _is_end_mark(a):
            return a['dmark'] is not None and a['dmark'][0] == 'e'
        
        spanL = []
        for i,attr in enumerate(attrL):
            if _is_begin_mark(attr):
                for j,a in enumerate(attrL[i+1:]):
                    if _is_end_mark(a):
                        spanL.append( (i, i+j+1) )
                        break
                    elif _is_begin_mark(a):
                        print(f"meas:{attr['meas_numb']} ele:{attr['ele_id']} : Begin dynamic interpolator marker missing end marker")
                        break

        return spanL

    def _apply_spans(attrL):
        def _dlevel_to_dmark( dlevel ):
            return { v:k for k,v in DYN_MAP.items() }[dlevel]
        
        for bi,ei in spanL:
            b_dmark  = attrL[bi]['dmark'].split("_")[1]
            e_dmark  = attrL[ei]['dmark'].split("_")[1]
            b_dlevel = DYN_MAP[b_dmark]
            e_dlevel = DYN_MAP[e_dmark]
            b_sec    = attrL[bi]['sec']
            e_sec    = attrL[ei]['sec']
            attrL[bi]['dmark'] = b_dmark
            attrL[ei]['dmark'] = e_dmark
            for a in attrL[bi+1:ei]:
                if a['onset_fl'] is not None and ['onset_fl'] and a['dmark'] is None:
                    sec = a['sec']
                    dlevel = int(round(b_dlevel + ((e_dlevel - b_dlevel)*(sec-b_sec))/(e_sec - b_sec)))

                    print(a['meas_numb'],a['ele_id'])
                    a['dmark'] = _dlevel_to_dmark(dlevel)
                
        return attrL
        
    spanL = _form_interpolation_spans(attrL)
    attrL = _apply_spans(attrL)

    return attrL

def write_section_correction_file( out_fname, attrL):

    sectD = {}

    for attr in attrL:
        
        new_section_id = attr['new_section_id']
        
        if new_section_id is not None:
            meas_numb = attr['meas_numb']
            ele_id    = attr['ele_id']
            sect_ele_id = f"sb{meas_numb}_{new_section_id}"
            sectD[ sect_ele_id ] = ele_id

    if out_fname is not None:
        with open(out_fname,"w") as f:
            for section_id,ele_id in sectD.items():
                f.write(f"{section_id}: {ele_id}\n")

def write_pedal_corrections_file( out_fname, link_fname, attrL ):

    def _read_link_file( link_fname ):
        pedalL = []

        with open(link_fname) as f:
            r = json.load(f)

        for p in r['pedalL']:
            if 'up' in p['label']:
                depth=0.0
            elif 'down' in p['label']:
                depth=1.0
            else:
                assert False
                
            pedalL.append(dict(id=p['id'], op='del', depth=depth, position=p['position_id'], ramp_fl=None, clear_depth=None))

        return pedalL

    def _new_pedal_recd_list( attrL ):

        def _gen_new_pedal_id( pedal_idD, ped_ele_id ):
            if ped_ele_id not in pedal_idD:
                pedal_idD[ ped_ele_id ] = 0
            else:
                pedal_idD[ ped_ele_id ] += 1

            return f"{ped_ele_id}_{pedal_idD[ ped_ele_id ]}"
        
        pedal_idD = {}
        pedalL    = []
        
        for attr in attrL:
            meas        = attr['meas_numb']
            position_id = attr['ele_id']

            for p in attr['pedalL']:
                id_prefix   = { 'damp':'dp', 'sost':'sp' }[ p['type'] ]
                action_char = { 0.0:'u', 0.5:'h', 1.0:'d' }[ p['depth'] ]
                ped_ele_id  = f"{id_prefix}{meas}_x{action_char}"
                ped_ele_id  = _gen_new_pedal_id(pedal_idD, ped_ele_id)
                depth       = p['depth']
                clear_depth = p['clear_depth'] if 'clear_depth' in p else None
                ramp_fl     = p['ramp_fl']     if 'ramp_fl'     in p else None
                d = dict(id=ped_ele_id, op="add", position=position_id, depth=depth, clear_depth=clear_depth, ramp_fl=ramp_fl)            
                pedalL.append(d)

        return pedalL

    def _write_pedal_yaml_file(out_fname,pedalL):

        if out_fname is not None:
            with open(out_fname,"w") as f:
                for p in pedalL:
                    s = f"- id: {p['id']}\n  op: {p['op']}\n  position: {p['position']}\n  depth: {p['depth']}\n"
                    if p['clear_depth']  is not None:
                        s += f"  clear_depth: {p['clear_depth']}\n"
                        
                        if p['ramp_fl']:
                            s += f"  transition: ramp\n"
                            
                        f.write(f"{s}\n")
    
    
    pedalL  = _read_link_file( link_fname )
    pedalL += _new_pedal_recd_list( attrL )

    _write_pedal_yaml_file(out_fname,pedalL)
            
                
def write_dyn_corrections_file( dyn_out_fname, default_dmark, attrL ):

    if dyn_out_fname is not None:
        with open(dyn_out_fname,"w") as f:
            for a in attrL:
                if a['onset_fl'] is not None and a['onset_fl']:
                    if a['dmark'] is None and default_dmark is None:                        
                        print(f"meas:{a['meas_numb']} id:{a['ele_id']} : Missing dynamic marking.")
                    else:
                        dmark = a['dmark']
                        if dmark is None:
                            print(f"meas:{a['meas_numb']} id:{a['ele_id']} : Missing dynamic marking applying default. {default_dmark}")
                            dmark = default_dmark

                        
                        dlevel = DYN_MAP[ dmark ] 
                        f.write(f"{a['ele_id']}:\n  dmark: {dmark}\n  dlevel: {dlevel}\n\n")

def write_metro_corections_file( score_fname, metro_out_fname, attrL ):

    def _read_existing_metro_markers( score_fname ):

        with open(score_fname,"rb") as f:
            score = pickle.load(f)

        metroRefD = {}
        for m in score.measures:
            for e in m.events:
                if isinstance(e,MetronomeMarking):
                   metroRefD[ e.id ] = e
        return metroRefD
    
    # get the existing score markers 
    metroRefD = _read_existing_metro_markers(score_fname )

    # if metro_out_fname is not None:
    #    with open(metro_out_fname,"w") as f:

    
    for a in attrL:
        if a['metroD'] is not None:
            new_bpm = a['metroD']['bpm']
            new_bu  = a['metroD']['beat_unit']
            new_metro_id = f"mm{a['meas_numb']}_{new_bpm}"
            new_anchor_id = a['ele_id']
            if new_metro_id not in metroRefD:
                print(f"The new metro {new_metro_id} was not found in the score.")
            else:
                if metroRefD[new_metro_id].anchor_note_id != a['ele_id']:
                    print(f"The metro marker {new_metro_id} changed position to {a['ele_id']}.")
                            
                        
    

def main( score_fname, edit_fname, out_dir, overwrite_fl, default_dmark, pedal_out_fname, section_out_fname, dyn_out_fname, metro_out_fname ):

    def _check_file( overwrite_fl, out_dir, fname ):
        fname = os.path.join(out_dir,fname)
        if os.path.isfile(fname) and not overwrite_fl:
            print(f"The output file {fname} exists and will not be overwritten.")
            fname = None
        return fname
    
    def _validate_output_files( overwrite_fl,
                                out_dir,
                                pedal_out_fname,
                                section_out_fname,
                                dyn_out_fname,
                                metro_out_fname ):

        out_dir = os.path.expanduser(out_dir)
        os.makedirs(out_dir,exist_ok=True)

        return types.SimpleNamespace(**dict(pedal_fname   = _check_file(overwrite_fl, out_dir,pedal_out_fname),
                                            section_fname = _check_file(overwrite_fl, out_dir,section_out_fname),
                                            dyn_fname     = _check_file(overwrite_fl, out_dir,dyn_out_fname),
                                            metro_fname   = _check_file(overwrite_fl, out_dir,metro_out_fname)))
    

    fnames = _validate_output_files( overwrite_fl,
                                     out_dir,
                                     pedal_out_fname,
                                     section_out_fname,
                                     dyn_out_fname,
                                     metro_out_fname)
                                     
    # parse the edit file
    attrL = parse_edit_file(edit_fname)

    # apply the dynamic spans
    attrL = apply_dyn_interp( attrL )

    # write sections.yaml correction file
    write_section_correction_file(fnames.section_fname,attrL)

    # write pedal.yaml correction file
    write_pedal_corrections_file( fnames.pedal_fname, link_fname, attrL )

    # write dynamics corrections file
    write_dyn_corrections_file( fnames.dyn_fname, default_dmark, attrL )

    # write metro corrections file
    write_metro_corections_file( score_fname, fnames.metro_fname, attrL )


    
if __name__ == "__main__":

    char_codeL = [ 'a','b','c' ]
    char_codeL = ['a']
    
    # Dynamic level to apply to notes that do not have an explicit dynamic level.
    # Set to None to not apply a default dynamic value, and leave the dynamic level blank.
    default_dmark = 'mp' 
    for c in char_codeL:

        score_fname       = f"gutim_2/{c}/output/cache/timing.pkl"
        edit_fname        = f"score_editor/working/{c}/editor/piano_{c}_mod_yurii_20260806.txt"
        link_fname        = f"score_editor/working/{c}/editor/link_{c}_mod.txt"
        out_dir           = f"score_editor/working/{c}/apply"
        pedal_out_fname   = "pedal.yaml"
        section_out_fname = "sections.yaml"
        dyn_out_fname     = "attr_corrections.yaml"
        metro_out_fname   = "metronome.yaml"
        overwrite_fl      = True

        os.makedirs(out_dir,exist_ok=True)

        main( score_fname, edit_fname, out_dir, overwrite_fl, default_dmark, pedal_out_fname, section_out_fname, dyn_out_fname, metro_out_fname )
