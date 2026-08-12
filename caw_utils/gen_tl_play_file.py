import json
import types
import pickle
from piano.model import (Note,GraceNote,Rest,GraceRest)
from const import (PLAYER_MAP,PIANO_MAP,MIDI_CTL_STATUS,MIDI_NOTE_ON_STATUS,MIDI_NOTE_OFF_STATUS,MIDI_DAMPER_D0,MIDI_SOST_D0,MIDI_MAX_CTL_VALUE,DAMPER_CLEAR_OFFSET_SEC)

_PC_OFFSET  = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_ACC_OFFSET = {'s': 1, 'b': -1, '': 0}

INVALID_LOC = -1
INVALID_SCI_PITCH = ""

def get_meas_msg_dict( score_pkl_fname, seg_list_pkl_fname, outMeasStartSecD, scoreMeasStartSecD ):

    def _get_pedal_list( score_pkl_fname ):
        with open(score_pkl_fname,"rb") as f:
            score = pickle.load(f)

        return [ pe for pe in score.pedal_events if not pe.deleted ]
            
    def _form_meas_event_dict( seg_list_pkl_fname ):

        with open(seg_list_pkl_fname,"rb") as f:
            segList = pickle.load(f)

        msgD = {} # { meas_num:[msg] }
        for seg in segList.segments:
            for sect in seg.section_list:
                for se in sect.event_list:
                    
                    if se.meas_numb not in msgD:
                        msgD[se.meas_numb] = []
                        
                    if se.event is not None and isinstance(se.event,(Note,GraceNote,Rest,GraceRest)):
                        msgD[se.meas_numb].append( dict(event=se.event, pedal=None, player=sect.player, piano=sect.piano, section_label=sect.section_label ))
        return msgD
        
    def _attach_pedal_events( measEvtD, pedalL ):

        def _form_id_to_meas_event_index_map( measEvtD ):
            idToMeasEvtIdxMapD = {}
            for meas_num,eventL in measEvtD.items():
                for i,e in enumerate(eventL):
                    idToMeasEvtIdxMapD[ e['event'].id ] = (meas_num, i )
                    
            return idToMeasEvtIdxMapD

        
        idToMeasEvtIdxMapD = _form_id_to_meas_event_index_map(measEvtD)
        for pe in pedalL:
            if pe.position_id in idToMeasEvtIdxMapD:
                meas_numb,evt_idx = idToMeasEvtIdxMapD[ pe.position_id ]
                measEvtD[ meas_numb ][ evt_idx ]['pedal'] = pe
            else:
                print("The pedal event ",pe.id,"was not found.")
                
            

    def _load_msg_list( measEvtD, outMeasStartSecD, scoreMeasStartSecD ):

        def _form_event_msg_list(eventD, meas_numb, out_meas_start_sec, score_meas_start_sec):

            def _midi_pitch( e ):
                return (e.octave + 1) * 12 + _PC_OFFSET[e.pitch_class] + _ACC_OFFSET[e.accidental]

            def _sci_pitch( e ):
                return f"{e.pitch_class}{e.accidental}{e.octave}"

            def _pedal_event_to_midi_ctl(pe):
                
                return { 'dp':MIDI_DAMPER_D0, 'sp':MIDI_SOST_D0 }[ pe.id[:2] ]

            def _pedal_event_depth_to_midi(pe):
                if pe.depth == 0.0:
                    return 0
                elif pe.depth == 1.0:
                    return MIDI_MAX_CTL_VALUE
                elif pe.depth == 0.5:
                    return MIDI_DAMPER_HALF_VALUE

                print("Unexpected pedal depth value:",pe.depth,"on event",pe.id)

                return max(0,min(MIDI_MAX_CTL_MAX,int( pe.depth * MIDI_MAX_CTL_MAX )))

            def _calc_secs( abs_time ):
                if score_meas_start_sec > abs_time:
                    print("Event start time:",abs_time,"less than meas start time:",score_meas_start_sec,"d:",score_meas_start_sec - abs_time)
                    # this event must be close to the start of the measure so place it on the measure
                    return out_meas_start_sec
                    
                    
                    
                return out_meas_start_sec + (abs_time - score_meas_start_sec)


            msgL          = []
            e             = eventD['event']
            pe            = eventD['pedal']
            player_id     = PLAYER_MAP[eventD['player']]['id']
            port_id      = PIANO_MAP[eventD['piano']]
            section_label = eventD['section_label']
            
            is_note_fl = e is not None and isinstance(e,(Note,GraceNote))
            is_rest_fl = e is not None and isinstance(e,(Rest,GraceRest))
            
            
            # if this is a note
            if is_note_fl and e.has_onset:

                #print(score_meas_start_sec,e.abs_time,e.id)
                
                n0 = dict(loc           = INVALID_LOC if e.loc is None else e.loc,
                          meas_numb     = meas_numb,
                          sec           = _calc_secs(e.abs_time) ,
                          ch            = 0,
                          status        = MIDI_NOTE_ON_STATUS,
                          d0            = _midi_pitch(e),
                          d1            = e.dlevel,
                          evt_id        = e.id,
                          sci_pitch     = _sci_pitch(e),
                          player_id     = player_id,
                          port_id       = port_id,
                          section_label = section_label)

                if n0['d1'] is None:
                    print("port id:",port_id,"NO VEL:",e.id)

                n1 = dict(loc           = INVALID_LOC,
                          meas_numb     = meas_numb,
                          sec           = _calc_secs(e.abs_time + e.art_dur_sec),
                          ch            = 0,
                          status        = MIDI_NOTE_OFF_STATUS,
                          d0            = n0['d0'],
                          d1            = 0,
                          sci_pitch     = INVALID_SCI_PITCH,
                          evt_id        = e.id + "_off",
                          player_id     = player_id,
                          port_id       = port_id,
                          section_label = section_label )

                msgL = [n0,n1]

            # if this event has a pedal
            if pe is not None and (is_note_fl or is_rest_fl):

                clear_offset_sec = 50/1000.0
                
                if hasattr(pe,'clear_depth') and pe.clear_depth is not None:
                    clear_offs_sec = DAMPER_CLEAR_OFFSET_SEC if pe.clear_depth == 0 else 0.0

                    p0 = dict(loc           = INVALID_LOC,
                              meas_numb     = meas_numb,
                              sec           = _calc_secs(e.abs_time + clear_offs_sec),
                              ch            = 0,
                              status        = MIDI_CTL_STATUS,
                              d0            = _pedal_event_to_midi_ctl(pe),
                              d1            = _pedal_event_depth_to_midi(pe),
                              sci_pitch     = INVALID_SCI_PITCH,
                              evt_id        = pe.id + "_clear",
                              player_id     = player_id,
                              port_id       = port_id,
                              section_label = section_label)

                    msgL.append(p0)

                p1 = dict(loc           = INVALID_LOC,
                          meas_numb     = meas_numb,
                          sec           = _calc_secs(e.abs_time),
                          ch            = 0,
                          status        = MIDI_CTL_STATUS,
                          d0            = _pedal_event_to_midi_ctl(pe),
                          d1            = _pedal_event_depth_to_midi(pe),
                          sci_pitch     = INVALID_SCI_PITCH,
                          evt_id        = pe.id,
                          player_id     = player_id,
                          port_id       = port_id,
                          section_label = section_label )

                msgL.append(p1)

            return msgL

        
        # for each measure
        measMsgD = {} # {meas_num:[ msg ]}
        for meas_num,eventL in measEvtD.items():

            out_meas_start_sec   = outMeasStartSecD[meas_num]
            score_meas_start_sec = scoreMeasStartSecD[meas_num]

            msgL = []
            # for each event in the section
            for e in eventL:
                # convert the event to it's MIDI form

                msgL += _form_event_msg_list(e,meas_num,out_meas_start_sec,score_meas_start_sec)

            # sort msgL on ascending time
            measMsgD[meas_num] = sorted(msgL,key=lambda x:x['sec'])

        return measMsgD
            

            
                
    pedalL   = _get_pedal_list( score_pkl_fname )
    measEvtD = _form_meas_event_dict( seg_list_pkl_fname )
    _attach_pedal_events(measEvtD,pedalL)
    measMsgD = _load_msg_list(measEvtD,outMeasStartSecD,scoreMeasStartSecD)
    
    return measMsgD


def form_meas_time_dict( cfgL ):

    def _get_meas_end_times( cfgL ):
        
        def _get_score_meas_end_times( score ):
            # get the end time for each measure in the score
            measEndTimeD = {}

            for m in score.measures:
                end_timeL = []
                for e in m.events:            
                    if isinstance(e,(Note,GraceNote,Rest,GraceRest)):
                        end_timeL.append(e.abs_time + e.duration_sec )

                measEndTimeD[ m.number ] = max(end_timeL)

            return measEndTimeD

        pianoMeasEndTimeD = { cfg.piano_id:None for cfg in cfgL }
        
        for cfg in cfgL:

            score_fname = cfg.score_pkl_fname
            piano_id    = cfg.piano_id
            
            # open the score file
            with open(score_fname,'rb') as f:
                score = pickle.load(f)

            # get the end time for each measure in this score
            pianoMeasEndTime[piano_id] = _get_score_meas_end_times(score)

        return pianoMeasEndTimeD
            

    def _form_meas_start_times( pianoMeasEndTIme ):

        
        
        # calculate each measures start time as the max end time of the previous meas across all scores
        measStartTimeD = {}  # { meas_numb:start_time }
        last_meas_numb = max(measEndTimeD.keys())

        measStartTimeD[1] = 0.0
        
        for meas_numb in range(2,last_meas_numb+1):
            measStartTimeD[meas_numb] = max(measEndTimeD[meas_numb-1])
            
        return measStartTimeD
    

    # measEndTimeD = { meas:[ end_meas_time_sec ] }
    measEndTimeD   = _get_meas_end_times(score_pkl_fnameL)
    measStartTimeD = _form_meas_start_times(measEndTimeD)
        
    return measStartTimeD

def form_meas_time_dict( cfgL ):

    def _meas_start_tick_zero( score_pkl_fname ):
        measD = {}
        
        with open(score_pkl_fname,'rb') as f:
            score = pickle.load(f)

        for m in score.measures:
            for e in m.events:
                if e.tick is not None and e.tick == 0:
                  measD[ m.number ] = e.abs_time
                  break
                  
        return measD
            
    
    def _meas_start_from_end_time( seg_list_pkl_fname ):

        measD = {}
        with open(seg_list_pkl_fname,'rb') as f:
            segList = pickle.load(f)

        
        for seg in segList.segments:
            for sect in seg.section_list:
                for se in sect.event_list:
                    if se.meas_numb not in measD:
                        measD[ se.meas_numb ] = []
                        
                    if isinstance(se.event,(Note,GraceNote)) and se.event.has_onset:
                        measD[ se.meas_numb ].append( se.event.abs_time + se.event.duration_sec )
                    
        for meas_num,endSecL in measD.items():
            measD[meas_num] = max(endSecL) if len(endSecL)>0 else 0

        startMeasD = { 1:0.0 }
        for meas_num,end_time_sec in measD.items():
            if meas_num+1 in measD:
                startMeasD[ meas_num+1 ] = end_time_sec

        return startMeasD
    
    def _meas_start_sec_dict( piano_measTimeD ):

        def _form_measure_list( piano_measTimeD ):
            measL = []
            for piano_id,d in piano_measTimeD.items():
                for meas_num,secL in d.items():
                    measL.append(meas_num)

            return list(set(measL))

        measL = _form_measure_list(piano_measTimeD)
        pianoL = [ piano_id for piano_id,_ in piano_measTimeD.items() ]
        
        assert len(pianoL) == 3

        outMeasStartD = {}
        for meas_num in measL:
            outMeasStartD[meas_num] =  max([piano_measTimeD[piano_id][meas_num] for piano_id in pianoL ])
            
        return outMeasStartD
            
    def _print_compare( measStartSecD, measEstStartD ):

        for meas_num,start_sec in measStartSecD.items():
            est_start_sec = measEstStartD[meas_num]
            assert start_sec is not None
            print(meas_num,start_sec,est_start_sec,start_sec-est_start_sec)

    pianoMeasTimeD = {}
    for cfg in cfgL:
        # determine the start time of each measure based on tick==0
        measStartSecD    = _meas_start_tick_zero(cfg.score_pkl_fname)
        # determine the start time of each measure based on the end time of the previous measure
        measEstStartSecD = _meas_start_from_end_time(cfg.seg_list_pkl_fname)
        
        # _print_compare( measStartSecD, measEstStartSecD )
        
        pianoMeasTimeD[ cfg.piano_id ] = measStartSecD

    # determine the start time of each measure of the output file (max. start time of each meas. across all pianos)
    outMeasStartSecD = _meas_start_sec_dict(pianoMeasTimeD)


    return outMeasStartSecD, pianoMeasTimeD
        

def get_messages(cfgL, outMeasStartSecD):

    measMsgD = {}
    # for each score/seg_list form meas_num,msgL
    for cfg in cfgL:

        # append the msgs for each measure into measMsgD
        for meas_num,msgL in get_meas_msg_dict( cfg.score_pkl_fname, cfg.seg_list_pkl_fname, outMeasStartSecD, cfg.measStartSecD ).items():
            if meas_num not in measMsgD:
                measMsgD[meas_num] = []
            measMsgD[meas_num] += msgL

    # sort the messages in each measure into time order    
    for meas_num,msgL in measMsgD.items():
        measMsgD[meas_num] = sorted(measMsgD[meas_num],key=lambda x:x['sec'])
        
    return measMsgD
                    

def create_toc_dict(cfgL,measMsgD):

    
    def _get_section_start( measMsgD, port_id, section_id ):
        start_sec = None
        beg_loc   = None
        section_label = None
        for meas_num,msgL in measMsgD.items():
            for m in msgL:
                if m['port_id']==port_id and m['section_label'] == section_id:
                    start_sec = m['sec']
                    section_label = m['section_label']
                    
                if m['port_id']==port_id and start_sec is not None and m['section_label'] == section_label and m['loc'] is not None and m['loc'] != INVALID_LOC:
                    beg_loc = m['loc']

                    return start_sec,beg_loc
                

        print(f"The section start time for piano:{port_id} and section:{section_id} was not found.")
        return None,None

    def _get_note_start(  measMsgD, port_id, note_id ):
        start_sec = None
        beg_loc = None
        section_label = None
        for meas_num,msgL in measMsgD.items():
            for m in msgL:
                if m['port_id']==port_id and m['evt_id'] == note_id:
                    start_sec = m['sec']
                    section_label = m['section_label']
                    
                if m['port_id']==port_id and start_sec is not None and m['section_label'] == section_label and m['loc'] is not None and m['loc'] != INVALID_LOC:
                    beg_loc = m['loc']

                    return start_sec,beg_loc

        print(f"The note start time for piano:{port_id} and note:{note_id} was not found.")
        return None,None
    
    def _get_note_loc(  measMsgD, port_id, note_id ):
        loc = None
        for meas_num,msgL in measMsgD.items():
            for m in msgL:
                if m['port_id']==port_id and m['evt_id'] == note_id:
                    return m['loc']
                    

        print(f"The loc for piano:{port_id} and note:{note_id} was not found.")
        return loc

    def _are_all_section_ids_unique(tocL):

        sect_idL = [ sect_id for toc in tocL for sect_id in toc['sectL']  ]

        fl = len(set(sect_idL)) == len(sect_idL)

        label = " " if fl else " NOT "

        print(f"All section id's are{label}unique.")
        
    def _form_toc_list( toc_json_fname ):
        with open(toc_json_fname) as f:
            tocL = json.load(f)

        outL = []
        for toc in tocL:
            port_id = PIANO_MAP[toc['piano']]
            player_id = PLAYER_MAP[toc['player']]['id']
            beg_note_id = toc['beg_sf_note_id']
            for section_id in toc['sectL']:
                if section_id[-1].isdigit():
                    section_start_sec, section_beg_loc = _get_section_start(measMsgD,port_id,section_id)
                else:
                    section_start_sec, section_beg_loc = _get_note_start(measMsgD,port_id,beg_note_id)

                    
                section_end_loc = _get_note_loc(measMsgD,port_id,toc['end_sf_note_id'])

                outL.append( dict(port_id=port_id,
                                  player_id=player_id,
                                  section_id=section_id,
                                  start_sec=section_start_sec,
                                  beg_loc=section_beg_loc,
                                  end_loc=section_end_loc ))


        return outL

    tocL = []
    for cfg in cfgL:
        tocL += _form_toc_list( cfg.toc_json_fname )

        
    tocL = sorted(tocL,key=lambda x:(x['start_sec'],x['port_id']))

    return tocL
    

def write_output(measMsgD,tocL,measStartSecD,out_fname):

    msgL = []
    measL = []
    for meas_numb,meas_msgL in measMsgD.items():
        measL.append(dict( number    = meas_numb,
                           start_sec = measStartSecD[meas_numb],
                           msg_idx   = len(msgL),
                           msg_cnt   = len(meas_msgL)))
        msgL += meas_msgL
    
    #
    # tocL  = [ {port_id,player_id,section_id,start_sec,beg_loc,end_loc} ]
    # measL = [ {meas_numb, start_sec, msgL=[{sec,meas_numb,ch,status,d0,d1,sci_pitch,evt_id,player_id,port_id,section_label}] }
    
    with open(out_fname,"w") as f:
        json.dump(dict(tocL=tocL,measL=measL,msgL=msgL),f,indent=2)
        



if __name__ == "__main__":

    char_codeL = ['a','b','c']
    src_dir    = "gutim_2"

    # 1. get measure dur from apply_sustain.pkl
    # 2. get notes from seg_list.pkl
    # 3. get TOC from output/caw_toc.json
    # 4. use TOC to blank out Spirio sections
    # 5. build up a measure a time - select the start time of each measure as the latest start time for that measure  across all scores
    # 6. review multi-player
    # 7. include section and measure markers in the output file
    # 8. messages must have abs_sec,ch,status,d0,d1,loc,evt_id,sci_pitch
    # 9. generate a TOC so that player can print 'cur sect/player, next sec/player, and measure)
    #    consider adding time tagged messages to the output

    out_json_fname      = "gutim_2/tl_play.json"
    cfgL = []

    for c in char_codeL:
        cfgL.append( types.SimpleNamespace(**dict( piano_id           = PIANO_MAP[c.upper()],
                                                   score_pkl_fname    = f"{src_dir}/{c}/output/cache/assign_sustain.pkl",
                                                   seg_list_pkl_fname = f"{src_dir}/{c}/output/cache/seg_list.pkl",
                                                   toc_json_fname     = f"{src_dir}/{c}/output/caw_toc.json",
                                                   measStartSecD      = {} )))
        

    
        


    # determine the start time of each output measure
    outMeasStartSecD, pianoMeasTimeD = form_meas_time_dict( cfgL )

    for cfg in cfgL:
        cfg.measStartSecD = pianoMeasTimeD[ cfg.piano_id ]
    

    # assign messages to each measure
    measMsgD = get_messages(cfgL, outMeasStartSecD )

    tocL = create_toc_dict(cfgL,measMsgD)
        
    write_output(measMsgD,tocL,outMeasStartSecD,out_json_fname)

    
        
