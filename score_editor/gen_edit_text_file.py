import sys
import json
import types
import pickle
from piano.model import (Note,GraceNote,GraceRest,Rest,MetronomeMarking,SectionBoundary)

def main(score_fname,attr_fname, out_fname):

    def _sci_pitch( e ):
        if isinstance(e,(Rest,GraceRest)):
            return 'R'

        acc = {'b':'b','s':'#','n':'','':''}[e.accidental]
        return f"{e.pitch_class}{acc}{e.octave}"
    
    def _rval( e ):
        dots = 0 if isinstance(e,(GraceNote,GraceRest)) else e.dots
        return f"{e.beat_unit}{'.'*dots}"

    def _has_onset( e ):
        if isinstance(e,(Rest,GraceRest)):
            return False
        return e.has_onset
    def _is_chord( e, evtL ):
        
        if isinstance(e,GraceNote):
            for ee in evtL:
                if isinstance(ee,(GraceNote)) and ee.tick == e.tick and ee.voice == e.voice and ee.id != e.id and (ee.is_chord or e.is_chord):
                    return True
        
        elif isinstance(e,Note):
            for ee in evtL:
                if isinstance(ee,(Note)) and ee.tick == e.tick and ee.voice == e.voice and ee.id != e.id:
                    return True

        return False
        

    def _tie_label( e ):
        if isinstance(e,(Rest,GraceRest)):
            return '--'
        
        return { (False,False):'--', (True,False):'tb', (True,True):'tc', (False,True):'te' }[ (e.tie_start,e.tie_stop) ]

    def _parse_score( score ):

        def _meas_sec( evtL ):
            for e in evtL:
                if e.tick == 0:
                    return e.abs_time
            assert False
        
        measL = []
        sectD = {}
        metroD = {}
        for m in score.measures:
            
            measL.append(types.SimpleNamespace(**dict(number=m.number,
                              total_ticks=m.total_ticks,
                              beat_cnt=m.beats,
                              ts_denom=m.beat_type,
                              evtL = [])))

            base_sec = _meas_sec(m.events)
            
            for e in m.events:
              if isinstance(e,SectionBoundary):
                  
                  if e.first_note_id is None:
                      print(f"{e.section_id} has no start note.")
                      
                  elif e.first_note_id in sectD:
                      print(sectD[e.first_note_id], e.section_id)
                      assert sectD[e.first_note_id] == e.section_id
                      
                  sectD[e.first_note_id] = e.section_id

              elif isinstance(e,MetronomeMarking):
                  if e.anchor_note_id is None:
                      print(f"Metro {e.id} has not anchor note.")
                  else:
                      label = f"{e.beat_unit}:{e.bpm}"
                      metroD[ e.anchor_note_id ] = dict(id=e.id,bpm=e.bpm,beat_unit=e.beat_unit,label=label)
                  
              elif isinstance(e,(Note,GraceNote,Rest,GraceRest)):
                                    
                  measL[-1].evtL.append(types.SimpleNamespace(**dict(id=e.id,
                                                                     tick=e.tick,
                                                                     sec=e.abs_time - base_sec,
                                                                     voice_id=e.voice,
                                                                     staff_id=e.staff,
                                                                     pitch=_sci_pitch(e),
                                                                     rval=_rval(e),
                                                                     tie_label=_tie_label(e),
                                                                     onset_fl=_has_onset(e),
                                                                     chord_fl=_is_chord(e,m.events),
                                                                     grace_fl=isinstance(e,(GraceNote,GraceRest)),
                                                                     dmark=None,
                                                                     pedL=[])))

        for m in measL:
            m.evtL = sorted(m.evtL,key=lambda x:(x.sec,x.voice_id))
            
        return measL,sectD,metroD

    def _parse_pedals( pedalEvtL ):

        def _pedal_type( e ):
            return { 'dp':'damp', 'sp':'sost' }[ e.id[0:2] ]

        def _up_down_label(e):
            if e.depth==0:
                return 'up'
            elif e.depth==1:
                return 'down'
            else:
                return f"down={e.depth}"

        def _clear_label(e):
            if e.clear_depth is None:
                return ''            
            elif e.clear_depth==0:
                return 'clear:'
            else:
                return f"clear:{e.clear_depth}"

        def _ramp_label(e):
            return ':ramp' if  e.transition == 'ramp' else ''
                
        pedalL = []
        for e in pedalEvtL:
            type_label = _pedal_type(e)
            ud_label = _up_down_label(e)
            clr_label = _clear_label(e)
            ramp_label= _ramp_label(e)
            label = f"{type_label}:{clr_label}{ud_label}{ramp_label}"
            pedalL.append(types.SimpleNamespace(**dict(id=e.id,position_id=e.position_id,label=label)))
            
        return pedalL

    
    def _assign_pedals_to_events( measL, pedalL ):
        def _find_event( measL, position_id ):
            for m in measL:
                for e in m.evtL:
                    if e.id == position_id:
                        return e
            return None
                    
        for p in pedalL:
            e = _find_event(measL,p.position_id)
            assert e is not None
            e.pedL.append(p)


    def _assign_dyn_to_events( measL, attr_fname ):
        def _get_note_attr_dict( attr_fname ):            
            with open(attr_fname) as f:
                sect_noteD = json.load(f)

            note_dynD = {}
            for sect_id,sectD in sect_noteD.items():
                for n in sectD['noteL']:
                    assert n['note_id'] not in note_dynD

                    note_dynD[n['note_id']] = n['attr']['dmark']
                              
            return note_dynD


        note_dynD = _get_note_attr_dict(attr_fname)
        
        for m in measL:
            for e in m.evtL:
                if e.id in note_dynD:
                    e.dmark = note_dynD[e.id]
                    
        
    def _print_file( out_fname, measL, sectD, metroD):
        text = ""
        for m in measL:
            s = f"meas:{m.number} {m.beat_cnt}/{m.ts_denom} ticks:{m.total_ticks}"

            text += f"{s}\n"
            
            for i,e in enumerate(m.evtL):

                sect_label  = f"section:{sectD[ e.id ]} "       if e.id in sectD  else ''
                metro_label = f"metro:{metroD[e.id]['label']} " if e.id in metroD else ''
                
                onset = "o" if e.onset_fl else "-"
                grace = 'g' if e.grace_fl else "-"
                chord = 'c' if e.chord_fl else "-"
                s = f"{i:3} {m.number:3} {e.sec:6.3f} v{e.voice_id} s{e.staff_id} t={e.tick:<4} {e.id:15} {e.pitch:3} {e.rval:4} {e.tie_label:2} {chord}{grace}{onset} | "

                s1 = " "
                if e.dmark is not None:
                    s1 += f"d:{e.dmark} "
                    
                for p in e.pedL:
                    s1 += f"{p.label} "
                    
                s += (s1 + sect_label + metro_label).strip()

                # print(s)
                text += f"{s}\n"

        with open(out_fname,"w") as f:
            f.write(text)

            
    def _write_link_file( link_out_fname, sectD, pedalL, metroD ):

        with open(link_out_fname,"w") as f:
            d = dict(sectD=sectD, metroD=metroD, pedalL=[x.__dict__ for x in pedalL ])
            json.dump(d,f,indent=2)
            

    
    with open(score_fname,"rb") as f:
        score = pickle.load(f)

    measL,sectD,metroD = _parse_score(score)
    print(len(sectD))
    pedalL = _parse_pedals(score.pedal_events)
    _assign_pedals_to_events( measL, pedalL )
    _assign_dyn_to_events( measL, attr_fname )
    _print_file( out_fname, measL, sectD, metroD )
    _write_link_file( link_out_fname, sectD, pedalL, metroD )

if __name__ == "__main__":

    cache_name = 'timing'

    if len(sys.argv)>1:
        cache_name = sys.argv[1]


    for c in ['a','b','c']:

        print("Processing piano:",c.upper())

        editor_dir = f"gutim_2/{c}/editor"

        score_fname    = f"gutim_2/{c}/output/cache/{cache_name}.pkl"
        attr_fname     = f"{editor_dir}/note_attr.json"
        out_fname      = f"{editor_dir}/piano_{c}_mod.txt"
        link_out_fname = f"{editor_dir}/link_{c}_mod.txt"
        

        main(score_fname,attr_fname,out_fname)
