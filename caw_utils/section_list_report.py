import pickle

from piano.model import (Note,Rest,GraceNote,GraceRest,SectionBoundary,MeasureBoundary,MetronomeMarking,DynamicDirection,Arrow)

class Ele:
    def __init__( self, meas_numb, type_label, event, ms=None, loc=None, pedal=None, xmark=None ):
        self.event     = event
        self.pedal     = pedal
        self.xmark     = xmark
        self.meas_numb  = meas_numb
        self.ms         = self._parse_ms(event, ms)
        self.loc        = loc
        self.type_label = type_label # 'section','xmark-begin', 'xmark-end', 'meas', 'note', 'pedal', 'metro'
        self.order_id   = self._order_id(type_label)

    def _parse_ms( self, evt, ms ):
        if ms is not None:
            return ms

        QUANTIZE_MS = 5
        return  QUANTIZE_MS * int(round((evt.abs_time * 1000)/QUANTIZE_MS))
            
        
    def _order_id(self,type_label):
        return { 'xmark-end':0,'section':1,'meas':2,'metro':3, 'pedal':4,'note':5,'xmark-begin':6}[type_label]

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
        elif self.type_label == 'xmark-begin' or self.type_label == 'xmark-end':
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


def find_meas_numb( score, evt_id ):
    for m in score.measures:
        for e in m.events:
            if e.id == evt_id:
                return m.number

    assert False
    return None

def find_ele_ms( eleL, ele_id):
    for e in eleL:
        if e.id() == ele_id:
            return e.ms, e.loc

    print(ele_id," not found.")    
    return None,None
    
def form_ele_list(score):
    eleL = []

    for m in score.measures:
        for e in m.events:
            loc = e.loc if isinstance(e,(Note,GraceNote)) else None

            
            if isinstance(e,(Note,GraceNote,Rest,GraceRest)):
                eleL.append( Ele(m.number, "note", e, None, loc ))
            elif isinstance(e,MeasureBoundary):
                eleL.append( Ele(m.number, "meas", e, None, loc ))

    return eleL

def add_metro_eles(score,eleL):

    for m in score.measures:
        for e in m.events:
            if isinstance(e,MetronomeMarking):
                if e.anchor_note_id is None:
                    print("Metro w/o anchor id : meas:",m.number," bpm:",e.bpm)
                else:
                    ms,loc = find_ele_ms(eleL,e.anchor_note_id)
                    if ms is None:
                        print("Metro ref: ",e.anchor_note_id," not found.")
                    else:
                        eleL.append( Ele(m.number, "metro", e, ms, loc) )

def add_section_eles(score,eleL):

    for m in score.measures:
        for e in m.events:
            if isinstance(e,SectionBoundary):
                if e.first_note_id is None:
                    print("Section w/o first not id : meas:",m.meas_num," section_id:",e.section_id)
                else:
                    ms,loc = find_ele_ms(eleL,e.first_note_id)
                    if ms is None:
                        print("Section: ",e.section," first note: ",e.first_note_id," not found.")
                    else:
                        eleL.append( Ele(m.number, "section", e, ms, loc ) )
                
def add_pedal_eles( score, eleL ):

    for p in score.pedal_events:
        if p.deleted == False:
            if p.position_id is None:
                print("Pedal w/o position id.",p.id)
            else:
                if p.position_id is None:
                    print("Pedal event w/ no position id.")
                else:
                    meas_num = find_meas_numb(score,p.position_id)
                    ms,loc = find_ele_ms(eleL,p.position_id)
                    if ms is None:
                        print("Pedal: ",p.id," position id: ", p.position_id, " not found.")
                    else:
                        eleL.append( Ele(meas_num,'pedal',None,ms,loc,p) )

        
def add_xmark_eles( score, eleL ):

    def _add_xmark(score,evt):
        meas_num = find_meas_numb(score,evt.attached_event.id)
        ms,_ = find_ele_ms(eleL,evt.attached_event.id)
        if ms is None:
            print("Xmark ",evt.span.marker_id," ",evt.marker_type," ref evt not found.")
        else:
            eleL.append(Ele(meas_num,f'xmark-{evt.marker_type}',None,ms,evt.loc,None,evt))

    for xmark_span in score.external_marker_spans:
        _add_xmark(score,xmark_span.begin_marker)
        _add_xmark(score,xmark_span.end_marker)


def form_slice_list(eleL):

    sliceD = {}

    for ele in eleL:
        if ele.ms not in sliceD:
            sliceD[ele.ms] = []
        sliceD[ele.ms].append(ele)

    # sort eah slice by the element 'order_id'
    sliceD = { ms:sorted(sliceEleL,key=lambda x:x.order_id) for ms,sliceEleL in sliceD.items() }

    return sliceD

def check_cross_slice_locs( sliceD ):

    cnt = 0
    locD = {} # {loc:ms}
    for ms,eleL in sliceD.items():
        for e in eleL:
            if e.loc is not None:
                if e.loc not in locD:
                    locD[e.loc] = e.ms
                elif locD[e.loc] != ms:
                    # print("cross slice loc:",e.loc)
                    cnt += 1

    print("Cross slice loc check - loc count:",len(locD)," cross count:",cnt)
    return cnt
    
def build_section_dict( sliceD ):

    eleL = []
    for ms,eL in sliceD.items():
        eleL += eL
    

    temp_section_id = 0
    sectionD = {}
    cur_section_id = None
    for e in eleL:
        if e.type_label in ['xmark-begin','section']:
            assert e.id() not in sectionD
            sectionD[ e.id() ] = [e]
            cur_section_id = e.id()
        else:
            sectionD[ cur_section_id ].append(e)
            if e.type_label == 'xmark-end':
                cur_section_id = "_temp_" + f"{temp_section_id}"
                temp_section_id += 1
                sectionD[ cur_section_id ] = []

    return sectionD

def check_cross_section_locs( sectionD ):
    
    locD = {}
    for section_id,eleL in sectionD.items():
        for e in eleL:
            if e.loc is not None:
                if e.loc not in locD:
                    locD[e.loc] = section_id
                else:
                    if locD[e.loc] != section_id:
                        print("cross section loc:",e.loc,"id:",e.id(),"sections:",locD[e.loc],section_id)
                    
        
    

def print_slices(sliceD):
    for i,(ms,eleL) in enumerate(sliceD.items()):
        for e in eleL:
            print(f"{i:5} {ms:8} {e.meas_numb:3} {'' if e.loc is None else e.loc:4} {e.id():20} {e.report()}")

    
def main( fname ):

    with open(fname,"rb") as f:
        score = pickle.load(f)

    # Add notes,rests,measures
    eleL = form_ele_list(score)
    add_metro_eles(score,eleL)
    add_section_eles(score,eleL)
    add_pedal_eles(score,eleL)
    add_xmark_eles(score,eleL)
    eleL   = sorted(eleL,key=lambda x:(x.meas_numb,x.ms))
    sliceD = form_slice_list(eleL)
    print("Elements:",len(eleL),"Slices:",len(sliceD))
    check_cross_slice_locs(sliceD)
    print_slices(sliceD)
    sectionD = build_section_dict(sliceD)
    check_cross_section_locs(sectionD)

if __name__ == "__main__":

    seg_list_pkl_fname = "gutim_1/output/cache/assign_sustain.pkl"

    main(seg_list_pkl_fname)
