import pickle

from piano.model import (Note,Rest,GraceNote,GraceRest,SectionBoundary,MeasureBoundary,MetronomeMarking,DynamicDirection,Arrow)

class Ele:
    def __init__( self, meas_numb, type_label, event, ms_ref_evt=None, pedal=None, xmark=None ):
        self.event     = event
        self.pedal     = pedal
        self.xmark     = xmark
        
        self.meas_numb  = meas_numb
        self.ms         = self._ms(ms_ref_evt) if ms_ref_evt is not None else self._ms(event)
        self.type_label = type_label
        self.order_id   = self._order_id(type_label)
        
    def _ms( self,evt ):
        QUANTIZE_MS = 5
        return  QUANTIZE_MS * int(round((evt.abs_time * 1000)/QUANTIZE_MS))

    def _order_id(self,type_label):
        return { 'section':0,'xmark':1,'meas':2,'metro':3, 'pedal':4,'note':5}[type_label]

    def ms(self):
        return _ms
    
    def id(self):
        ident = None
        if self.xmark is not None:
            ident = self.xmark.span.marker_id
        elif self.pedal is not None:
            ident = self.pedal.id
        elif self.event is not None:
            ident = self.event.id            
        else:
            assert False
        return ident
        

    def report(self):
        if self.type_label == 'section':
            s = f"section:{self.event.section_id}"
        elif self.type_label == 'xmark':
            s = f"xmark:{self.id()}-{self.xmark.marker_type}:{self.xmark.attached_event.id}"
        elif self.type_label == 'meas':
            s = f"meas:{self.event.meas_numb}"
        elif self.type_label == 'metro':
            s = f"metro:{self.event.bpm}"
        elif self.type_label == 'pedal':
            s = self._pedal_report()
        elif self.type_label == 'note':
            s = self._note_report()
        else:
            assert False

        return s

    def _pedal_report(self):
        ped_type = { "dp":"damp","sp":"sost"}[ self.pedal.id[0:2] ]
        depth    = { 0.0:"up",0.5:"half",1.0:"down" }[ self.pedal.depth ]
        clear    = { None:'',0.0:'clr',0.5:'hclr' }[ self.pedal.clear_depth ]
        return f"{ped_type} {clear} {depth}"

    def _note_report(self):
        onset = ''
        grace = ''
        if isinstance(self.event,(Rest,GraceRest)):
            pitch = "R"
        else:
            acc = {'s':'#','b':'b','':'',None:''}[ self.event.accidental ]
            pitch = f"{self.event.pitch_class}{acc}{self.event.octave}"
            onset = 'o' if self.event.has_onset else ''

        dots = 0
        if isinstance(self.event,(Note,Rest)):
            dots = self.event.dots            
        if isinstance(self.event,(GraceNote,GraceRest)):
            grace = 'g'
            
        return f"{onset:1}{grace:1} {pitch} {self.event.beat_unit}{'.'*dots}"

    
def main( fname ):

    def _form_global_ele_list( score ):
        eleL = []
        for m in score.measures:
            for e in m.events:
                ele = None
                if isinstance(e,(Note,GraceNote)):
                    ele = Ele(m.number, 'note', e)
                elif isinstance(e,(Rest,GraceRest)):
                    ele = Ele(m.number, 'note', e)
                elif isinstance(e,MetronomeMarking):
                    if e.anchor_note_id is None:
                        print("Metro w/ no anchor:",m.number,e.bpm)
                    else:
                        ele = Ele(m.number, 'metro', e, score.lookup(e.anchor_note_id))
                elif isinstance(e,SectionBoundary):
                    if e.first_note_id is None:
                        print("Section w/ no first note:",m.number,e.section_id)
                    else:
                        ele = Ele(m.number, 'section', e, score.lookup(e.first_note_id))
                elif isinstance(e,MeasureBoundary):
                    ele = Ele(m.number, 'meas', e )
                elif isinstance(e,(DynamicDirection,Arrow)):
                    pass
                else:
                    print("Unknown type:",type(e))

                if ele is not None:
                    eleL.append(ele)

        return eleL


    def _find_meas_numb( score, evt_id ):
        for m in score.measures:
            for e in m.events:
                if e.id == evt_id:
                    return m.number

        assert False
        return None
    
    def _add_pedal_events( score ):

        eleL = []
        for p in score.pedal_events:
            if p.deleted == False:
                if p.position_id is None:
                    print("Pedal w/o position id.",p.id)
                else:
                    if p.position_id is None:
                        print("Pedal event w/ no position id.")
                    else:
                        meas_num = _find_meas_numb(score,p.position_id)
                        ref_evt = score.lookup(p.position_id)
                        eleL.append( Ele(meas_num,'pedal',None,ref_evt,p) )

        return eleL

    def _add_xmark_events( score ):

        def _add_xmark(score,evt):
            meas_num = _find_meas_numb(score,evt.attached_event.id)
            return Ele(meas_num,'xmark',None,evt.attached_event,None,evt)
        
        eleL = []
        for xmark_span in score.external_marker_spans:
            eleL.append(_add_xmark(score,xmark_span.begin_marker))
            eleL.append(_add_xmark(score,xmark_span.end_marker))
            
        return eleL

    def _form_slice_list(eleL):
        sliceD = {}

        for ele in eleL:
            if ele.ms not in sliceD:
                sliceD[ele.ms] = []
            sliceD[ele.ms].append(ele)

        sliceD = { ms:sorted(sliceEleL,key=lambda x:x.order_id) for ms,sliceEleL in sliceD.items() }
        
        return sliceD

    def _print(sliceD):
        for i,(ms,eleL) in enumerate(sliceD.items()):
            for e in eleL:
                print(f"{i:5} {ms:8} {e.meas_numb:3} {e.id():20} {e.report()}")

    
    with open(fname,"rb") as f:
        score = pickle.load(f)

    eleL   = _form_global_ele_list(score)
    eleL  += _add_pedal_events(score)
    eleL  += _add_xmark_events(score)
    eleL   = sorted(eleL,key=lambda x:(x.meas_numb,x.ms))
    sliceD = _form_slice_list(eleL)
    print(len(eleL),len(sliceD))
    _print(sliceD)
            
                    
        
    
if __name__ == "__main__":

    seg_list_pkl_fname = "gutim_1/output/cache/assign_sustain.pkl"

    main(seg_list_pkl_fname)
