import os
import csv
import json
import yaml
import types
import numpy as np

TICKS_PER_QUARTER = 768


class SWLoc:
    def __init__( self, loc_id, locD, base_note_idx ):
        self.loc_id_    = loc_id        # score loc id
        self.meas_num_  = locD['meas']  # measure this loc is contained by
        self.sec_       = locD['sec']   # abs time of this location
        self.tick_      = locD['tick']  # metric tick of this location or None if it is not a metric event
        self.meas_ticks_ = locD['total_ticks'] # count of tick in meas
        self.dur_ticks_  = None
        self.beat_idx_   = None
        
        self.perf_loc_idx_ = None       # index of the tracked perf loc.

        # Set the indexes into SectionWarper.noteL of the notes at this location
        noteN = len(locD['noteD'])
        self.note_idxL_ = [ i for i in range(base_note_idx,base_note_idx + noteN) ]

    def meas(self):
        return self.meas_num_

    def sec(self):
        return self.sec_

    def tick(self):
        return self.tick_

    def meas_ticks(self):
        return self.meas_ticks_

    def loc_id(self):
        return self.loc_id_

    def set_perf_loc( self, perf_loc_idx ):
        assert self.perf_loc_idx_ is None or self.perf_loc_idx_ == perf_loc_idx # verify that SWLoc was reset before being set
        self.perf_loc_idx_ = perf_loc_idx

    def clear_perf_loc( self ):
        self.perf_loc_idx_ = None

    def perf_loc_idx(self):
        return self.perf_loc_idx_

    def set_dur_ticks( self, dur_ticks):
        self.dur_ticks_ = dur_ticks

    def dur_ticks( self ):
        return self.dur_ticks_

    def set_beat_idx( self, beat_idx ):
        assert self.beat_idx_ is None # beat_idx can only be in one beat group
        self.beat_idx_ = beat_idx

    def beat_idx( self ):
        return self.beat_idx_

    def is_chord( self ):
        return len(self.note_idxL_)>1

class SWNote:
    def __init__( self, loc_idx, note_id, noteD ):
        self.loc_idx_       = loc_idx
        self.note_id_       = note_id
        self.pitch_         = noteD['pitch']
        self.dlevel_        = noteD['dlevel']
        self.dlevel_fit_    = None
        self.dur_ticks_     = noteD['dur_ticks']
        self.dots_          = noteD['dots']
        self.beat_unit_     = noteD['beat_unit']
        self.perf_note_idx_ = None  # perf. note that tracked to this score note

    def loc_idx(self):
        return self.loc_idx_
    
    def note_id(self):
        return self.note_id_
    
    def pitch(self):
        return self.pitch_
    
    def dlevel(self):
        return self.dlevel_

    def dur_ticks(self):
        return self.dur_ticks_

    def set_perf_note(self, perf_note_idx ):
        assert self.perf_note_idx_ is None # verify that the record was reset before being reused
        self.perf_note_idx_ = perf_note_idx

    def clear_perf_note(self):
        self.perf_note_idx_ =  None
        self.dlevel_fit_ = None

    def perf_note_idx( self ):
        return self.perf_note_idx_

    def set_dlevel_fit( self, dlevel_fit ):
        assert self.dlevel_fit_ is None # verify that the record was reset before being reused
        self.dlevel_fit_ = dlevel_fit

    def dlevel_fit(self):
        return self.dlevel_fit_

        
class SWPerfNote:
    def __init__( self, loc_idx, note_idx, sec, pitch, vel ):
        self.loc_idx_ = loc_idx
        self.note_idx_ = note_idx
        self.sec_ = sec
        self.pitch_ = pitch
        self.vel_ = vel
        self.sec_fit_ = None
        self.vel_fit_ = None

    
    def loc_idx(self):
        return self.loc_idx_
    
    def note_idx(self):
        return self.note_idx_
    
    def sec(self):
        return self.sec_
    
    def vel(self):
        return self.vel_

    def set_fit( self, sec, vel ):
        self.sec_fit_ = sec
        self.vel_fit_ = vel

    def vel_fit(self):
        return self.vel_fit_


class SWPerfLoc:
    def __init__( self, loc_id, loc_idx ):
        self.loc_id_        = loc_id
        self.loc_idx_       = loc_idx
        self.secL_          = []
        self.perf_note_idxL = []
        
    def insert_note( self, perf_note_idx, sec ):
        self.perf_note_idxL.append( perf_note_idx )
        self.secL_.append(sec)

    def loc_id(self):
        return self.loc_id_

    def sec(self):
        assert len(self.secL_)>0
        return np.mean(self.secL_)

    def perf_note_idx_list(self):
        return self.perf_note_idxL

    def is_chord(self):
        return len(self.perf_note_idxL) > 1

    def ctr_sec(self):
        noteN = len(self.secL_)
        assert noteN > 0
        if noteN == 1:
            return self.secL_[0]

        elif noteN == 2:
            assert len(self.secL_)>0
            return np.mean(self.secL_)

        return np.median(self.secL_)

    def sec_spread(self):
        noteN = len(self.secL)
        assert noteN > 0
        if noteN == 1:
            return 0
        elif noteN == 2:
            assert len(self.secL)>0
            return max(self.secL) - np.mean(self.secL)
            
        return np.std(self.secL)
        
class SectionWarper:
    def __init__( self, section_label, sectD ):

        self.section_label_ = section_label    # section label
        self.beg_loc_id_    = sectD['beg_loc'] # begin location of this section in the score
        self.end_loc_id_    = sectD['end_loc'] # end      "      "   "     "     "  "    "
        self.bpm_estimate_  = sectD['bpm_estimate'] # score BPM estimate for this section (it is only an estimate insofar as it may average multiple labeled tempos)

        self.noteL          = []  # list of SWNote from score
        self.locL           = []  # list of SWLoc  from score
        
        # Feature groups from score
        self.graceGrpL = []  # [{ loc_idx:[ note_idx ] }] - list of grace groups
        self.evenGrpL  = []  # [{ loc_idx:[ note_idx ] }] - list of even groups
        self.tempoGrpL = []  # [{ loc_idx:[ note_idx ] }] - list of tempo groups
        self.dynGrpL   = []  # [{ loc_idx:[ note_idx ] }] - list of dynamics groups
        self.chordGrpL = []  # [{ loc_idx:[ note_idx ] }] - list of chord groups
        self.beatGrpL  = []  # [{ loc_idx:[ note_idx ] }] - list of beat groups

        self.perfNoteL      = []  # list of SWPerfNote from performance
        self.perfLocL       = []
        
        self.spurious_note_cnt = 0 # count of 'extra' notes that were not tracked

        
        self._init_loc_and_note_list(sectD)
        self._init_validate()
        self.perf_reset()

    def label(self):
        return self.section_label_
    
    def beg_loc_id(self):
        return self.beg_loc_id_
    
    def end_loc_id(self):
        return self.end_loc_id_

    def bpm_estimate(self):
        return self.bpm_estimate_

    def perf_note_count(self):
        return len(self.perfNoteL)

    def score_note_count(self):
        return len(self.noteL)

    def perf_reset( self ):

        # clear the performed locations and notes
        self.perfNoteL.clear()
        self.perfLocL.clear()

        self.spurious_note_cnt = 0

        # drop the perf. tracking information from the the score
        for r in self.locL:
            r.clear_perf_loc()
            
        for r in self.noteL:
            r.clear_perf_note()
        
    def insert_perf_note( self, loc_id, sec, pitch, vel ):

        # if the note was not tracked, or the loc is out of range.
        # (it's easy for an out of range note to arrive because the tracker may have crossed a section boundary more than once)
        if loc_id is None or loc_id < self.beg_loc_id() or loc_id > self.end_loc_id():
            self.spurious_note_cnt += 1
            return

        # validate the tracked loc_id - only notes that were tracked pass this point
        assert loc_id is not None
        assert self.beg_loc_id_ <= loc_id and loc_id <= self.end_loc_id_

        #  get the score locL[] index for this note
        loc_idx = loc_id - self.beg_loc_id_
        assert 0 <= loc_idx and loc_idx < len(self.locL)
        assert self.locL[loc_idx].loc_id() == loc_id

        # get the noteL[] index for this tracked pitch
        note_idx = next((ni for ni in self.locL[loc_idx].note_idxL_ if self.noteL[ni].pitch() == pitch),None)

        if note_idx is None:
            print(loc_id, sec, pitch, vel )
        
        assert 0 <= note_idx and note_idx < len(self.noteL)

        # store the performed note
        self.perfNoteL.append( SWPerfNote(loc_idx,note_idx,sec,pitch,vel) )

        # get the performed loc index for this pitch
        pli = next((i for i in range(len(self.perfLocL)) if self.perfLocL[i].loc_id()==loc_id ),None)

        # if the perf. location for this pitch has not yet been initialized ...
        if pli is None:
            # ... then initialize it
            pli = len(self.perfLocL)
            self.perfLocL.append( SWPerfLoc( loc_id, loc_idx ) )

        # insert the performed note in the perf. loc
        perf_note_idx = len(self.perfNoteL)-1
        self.perfLocL[pli].insert_note( perf_note_idx, sec )

        # connect the SWLoc to the SWPerfLoc
        self.locL[ loc_idx ].set_perf_loc( pli )
        # connect the SWNote to the SWPerfNote
        self.noteL[ note_idx ].set_perf_note(  perf_note_idx )
        
    def _warp_time_and_vel( self ):

        def _fit( xV, yV ):

            aV = yV
            bV = xV
            
            # Perform linear curve fit: fit b = m*a + c
            coeffs = np.polyfit(aV, bV, deg=1)
            m, c = coeffs

            # print(f"Slope (m): {m}")
            # print(f"Intercept (c): {c}")

            # Generate fitted values
            xV = m * aV + c

            mse = (np.square(xV - bV)).mean()

            return xV,m,mse

        
        def _scale_vel( v ):
            # scale the velocity to capture the shape while dropping the absolute values
            v -= min(v)

            mx = max(v)
            
            v /= 1 if mx==0 else mx

            return v
        
        perfNoteN = len(self.perfNoteL)
        xSecV = np.zeros((perfNoteN,) )
        ySecV = np.zeros((perfNoteN,) )
        xVelV = np.zeros((perfNoteN,) )
        yVelV = np.zeros((perfNoteN,) )

        for i,r in enumerate(self.perfNoteL):
            ySecV[i] = r.sec()                              # performed seconds
            xSecV[i] = self.locL[ r.loc_idx() ].sec()       # score seconds
            yVelV[i] = r.vel()                              # performed velocity
            xVelV[i] = self.noteL[ r.note_idx() ].dlevel()  # score velocity

        # fit perf. to score
        zSecV,time_fact,time_MSE = _fit(xSecV,ySecV)

        xVelV = _scale_vel(xVelV)
        yVelV = _scale_vel(yVelV)
        zVelV,dyn_fact,dyn_MSE = _fit(xVelV,yVelV)

        # set the 'fit' seconds and vel value for all performed notes
        for i,r in enumerate(self.perfNoteL):
            r.set_fit( zSecV[i], zVelV[i] )

            self.noteL[ r.note_idx() ].set_dlevel_fit( yVelV[i] )
        

        return time_fact,time_MSE,dyn_fact,dyn_MSE

    def _even_std(self):
        if len(self.evenGrpL) == 0:
            return None
        
        evenStdL = []
        # for each even group
        for grpD in self.evenGrpL:
            # take the std of the time between each note

            xL = [ self.perfLocL[ self.locL[loc_idx].perf_loc_idx() ].ctr_sec() for loc_idx,_ in grpD.items() if self.locL[loc_idx].perf_loc_idx() is not None ]

            if len(xL) <= 1:
                print("Even calc. failed. Note list too short.")
            else:            
                std = np.std(np.diff(xL))
                evenStdL.append(std)

        assert len(evenStdL)>0
        return np.mean(evenStdL)

    def _chord_std(self):

        dL = []
        for ploc in self.perfLocL:
            perfNoteN = len(ploc.perf_note_idxL)
            v = None
            if perfNoteN <= 1:
                continue
            elif perfNoteN == 2:
                v = abs(self.perfNoteL[1].sec() - self.perfNoteL[0].sec())/2
            else:
                v = np.std([self.perfNoteL[i].sec() for i in ploc.perf_note_idxL ])

            assert v is not None
            dL.append(v)

        return None if len(dL)==0 else np.mean(dL)
        
    def _tempo_estimate(self):

        if len(self.tempoGrpL) == 0:
            return None

        tempoL = []
        for grpD in self.tempoGrpL:
            dsecL = []
            sec0 = None
            mult0 = None
            
            # for each loc marked for tempo meas.
            for loc_idx,note_idxL in grpD.items():

                mult = 1.0
                dur_ticks = self.locL[loc_idx].dur_ticks()
                
                if dur_ticks is not None:
                    mult = TICKS_PER_QUARTER/dur_ticks

                # get the perfomed loc
                perf_loc_idx = self.locL[loc_idx].perf_loc_idx()
                sec = None
                if perf_loc_idx is not None:
                    sec = self.perfLocL[ perf_loc_idx ].sec()

                    if sec is not None and sec0 is not None:
                        dsecL.append( (sec - sec0) * mult0 )

                sec0 = sec
                mult0 = mult

            if len(dsecL) > 1:
                assert len(dsecL)>0
                beat_per_min = np.mean(dsecL) * 60
                #print(self.locL[loc_idx].meas(), "TEMPO:",beat_per_min,dsecL)

                tempoL.append( beat_per_min )

        return None if len(tempoL)==0 else np.mean(tempoL)

            
                

    def _dyn_mse(self):

        if len(self.dynGrpL) == 0:
            return None
        
        grpDVelL = []
        
        # for each dyn group
        for grpD in self.dynGrpL:
            dVelL = []
            for loc_idx,note_idxL in grpD.items():
                perf_loc_idx = self.locL[loc_idx].perf_loc_idx()

                # if the location was tracked
                if perf_loc_idx is not None:
                    for perf_note_idx in self.perfLocL[ perf_loc_idx ].perf_note_idx_list():
                        if self.perfNoteL[perf_note_idx].note_idx() in note_idxL:
                            perfNote = self.perfNoteL[ perf_note_idx ]
                            delta = perfNote.vel_fit() - self.noteL[ perfNote.note_idx() ].dlevel_fit()
                            dVelL.append( delta*delta )

            if len(dVelL) > 0:
                grpDVelL.append(np.mean(dVelL))

        if len(grpDVelL) == 0:
            return None

        assert len(grpDVelL)>0
        return np.mean(grpDVelL)

    def _beat_mse( self, args ):

        tempo_bpmL = []
        beat_stdL = []
        

        # for each beat group in this section
        for grpD in self.beatGrpL:

            dsecL = []
            sec0 = None
            idx0 = None

            # for each location in the beat group
            for loc_idx,_ in grpD.items():
                
                # get the tracked perf loc
                perf_loc_idx = self.locL[loc_idx].perf_loc_idx()

                sec = None
                idx = None
                
                # if loc was tracked 
                if perf_loc_idx is not None:

                    sec = self.perfLocL[ perf_loc_idx ].ctr_sec()
                    idx = self.locL[ loc_idx ].beat_idx()

                    # _init_beat_groups() should have dropped all locations that fall on the same beat index
                    assert idx != idx0
                    
                    if sec0 is not None:
                        # reduce the delta time between two successive loc's to approx. one beat
                        dsecL.append((sec - sec0)/(idx - idx0))

                sec0 = sec
                idx0 = idx


            score_sec_per_qrtr = 60.0/self.bpm_estimate()
            min_period_sec     = score_sec_per_qrtr *      args.tempo_period_error
            max_period_sec     = score_sec_per_qrtr * (1.0+args.tempo_period_error)
            tempo_dsecL        = [ dsec for dsec in dsecL if min_period_sec <= dsec and dsec <= max_period_sec ]
            
            
            # Store count of locs used to calc tempo for this group, and the tempo itself,
            # This will later be used to pick the tempo which represents this section.
            if len(tempo_dsecL) > args.tempo_min_period_count:
                tempo_bpmL.append( (len(tempo_dsecL), np.mean(tempo_dsecL) * 60, len(tempo_bpmL) ) )
                
            beat_stdL.append( np.std(dsecL) )


        beat_std = None
        tempo_bpm = None
        
        if len(beat_stdL) > 0:
            beat_std = np.mean(beat_stdL)
            
        if len(tempo_bpmL)>0:
            # select the tempo for this section from the tempo group with the most locations
            tempo_bpm = tempo_bpmL[ max(tempo_bpmL)[2] ][1]
        
        return beat_std, tempo_bpm

    def _calc_missed_pct( self ):
        return sum([1 for note in self.noteL if note.perf_note_idx() is None])/len(self.noteL)

    def _calc_perf_dur_sec( self ):        
        secL = [ pnote.sec() for pnote in self.perfNoteL ]
        return max(secL) - min(secL)

    def _chord_count( self ):
        score_chord_cnt = sum([ 1 for loc in self.locL if loc.is_chord() ])
        perf_chord_cnt = sum([ 1 for loc in self.perfLocL if loc.is_chord() ])

        print("chord count score:",score_chord_cnt,"perf:",perf_chord_cnt)
                    
    def calc_features( self, args ):
        
        feat = types.SimpleNamespace(**{
            "sect_dur_sec": None, # performed duration of this section
            "perf_note_cnt":None, # count of performed notes
            "tracked_pct": None,  # pct of score notes that were tracked
            "missed_pct":None,    # pct of score notes that were missed
            "spurious_pct":None,  # pct of performed notes that were spurious
            "time_fact":None,     # time stretch factor
            "dyn_fact":None,      # vel stretch factor
            "time_MSE":None,      # fitted time MSE
            "dyn_MSE":None,       # fitted vel MSE
            "even_grp_std":None,  # mean of even-groups std
            "dyn_grp_mse":None,   # measn of dyn-group mse
            "chord_std":None,     # std of chord onsets
            "tempo_bpm":None,     # tempo in BPM
            "beat_mse":None,      # mean beat period mse            
            })

        
        feat.sect_dur_sec  = self._calc_perf_dur_sec()
        feat.perf_note_cnt = len(self.perfNoteL)
        feat.tracked_pct   = len(self.perfNoteL)/len(self.noteL)
        feat.missed_pct    = self._calc_missed_pct()
        feat.spurious_pct  = self.spurious_note_cnt/len(self.perfNoteL)
                
        feat.time_fact,feat.time_MSE,feat.dyn_fact,feat.dyn_MSE = self._warp_time_and_vel()

        feat.chord_std    = self._chord_std()
        feat.even_grp_std = self._even_std()
        feat.dyn_grp_mse = self._dyn_mse()
        feat.tempo_bpm   = self._tempo_estimate()
        feat.beat_mse,feat.tempo_bpm    = self._beat_mse(args)

        if feat.tempo_bpm is None:
            feat.tempo_bpm = self.bpm_estimate()

        return feat.__dict__
        

    def _note_id_to_index(self, note_id ):
        return next((i for i,r in enumerate(self.noteL) if r.note_id()==note_id),None)

    def _parse_loc_note_group( self, groupD  ):
        ggD = {}  # { loc_idx:[ note_idx ] }
        
        # for each loc in the group
        for loc_id,note_idL in groupD.items():

            # for each note in the loc
            for note_id in note_idL:

                # get the score note index
                note_idx = self._note_id_to_index(note_id)
                assert note_idx is not None

                # get the score loc index
                loc_idx = self.noteL[ note_idx].loc_idx()
                if loc_idx not in ggD:
                    ggD[ loc_idx ] = []

                # add the note to the loc
                ggD[loc_idx].append(note_idx)

        return ggD


    def _init_loc_dur_ticks( self ):

        for swLoc in self.locL:
            for note_idx in swLoc.note_idxL_:
                if self.noteL[note_idx].dur_ticks() is not None:

                    if swLoc.dur_ticks() is not None and swLoc.dur_ticks() != self.noteL[note_idx].dur_ticks():
                        print("TEMPO ticks:",swLoc.dur_ticks(),self.noteL[note_idx].dur_ticks())
                    
                    swLoc.set_dur_ticks( self.noteL[note_idx].dur_ticks() )
                    break


    def _init_beat_groups( self ):

        # for each beat group in this section
        for grp_idx,grpD in enumerate(self.beatGrpL):

            meas0        = None
            mticks0      = None
            tick0        = None
            cur_tick     = 0
            beat_idx_set = set()
            newGroupD    = {}
            
            # for each loc in this beat group
            for i,(loc_idx,note_idxL) in enumerate(grpD.items()):

                loc = self.locL[loc_idx]

                if meas0 is not None:

                    if loc.meas() == meas0:
                        assert loc.tick() > tick0
                        cur_tick += loc.tick() - tick0
                    else:
                        assert mticks0 >= tick0
                        cur_tick += (mticks0 - tick0) + loc.tick()


                # calculate the beat number of this beat in this beat group
                beat_idx = int(round(cur_tick/TICKS_PER_QUARTER))

                # drop loc's that fall on the same beat index
                if beat_idx not in beat_idx_set:
                    beat_idx_set.add(beat_idx)
                    loc.set_beat_idx(beat_idx)
                    newGroupD[loc_idx] = note_idxL

                
                meas0   = loc.meas()
                mticks0 = loc.meas_ticks()
                tick0   = loc.tick()

            # 
            self.beatGrpL[grp_idx] = newGroupD
                
                    

                
    def _init_loc_and_note_list( self, sectD ):

        # for each possible score location id: loc_id
        for loc_id in range(self.beg_loc_id_,self.end_loc_id_+1):
            
            # get the score loc record from the 'all' group for 'loc_id'
            locD = sectD['all'][str(loc_id)]

            # create a SWLoc record to represent this location
            self.locL.append( SWLoc(loc_id, locD, len(self.noteL)) )

            # for each score note assigned to this location
            for note_id,noteD in locD['noteD'].items():                
                self.noteL.append( SWNote(loc_id-self.beg_loc_id_,note_id,noteD) )

        # for each grace group in this section
        for _,groupD in sectD['grace'].items():
            self.graceGrpL.append(self._parse_loc_note_group(groupD))

        # for each 'even' group in this section:
        for _,groupD in sectD['even'].items():
            self.evenGrpL.append(self._parse_loc_note_group(groupD))

        # for each 'tempo' group in this section
        for _,groupD in sectD['tempo'].items():
            self.tempoGrpL.append(self._parse_loc_note_group(groupD))

        # for each 'dyn' group in this section
        for _,groupD in sectD['dyn'].items():
            self.dynGrpL.append(self._parse_loc_note_group(groupD))

        # for each 'chord' group in this section
        for _,groupD in sectD['chord'].items():
            self.chordGrpL.append(self._parse_loc_note_group(groupD))

        # for each 'beat' group in this section
        for _,groupD in sectD['beat'].items():
            self.beatGrpL.append(self._parse_loc_note_group(groupD))
                    
        self._init_loc_dur_ticks()
        self._init_beat_groups()
                
    def _init_validate(self):
        for ni in range(len(self.noteL)):
            assert ni in self.locL[ self.noteL[ni].loc_idx_ ].note_idxL_
            
        
    
class ScoreSections:
    def __init__( self, score_group_fname ):
        with open(args.score_group_fname) as f:
            scoreGrpD = json.load(f)

        self.sectionL = [ SectionWarper( sect_label, sectD ) for sect_label,sectD in scoreGrpD.items() if not self._is_external_sect(sectD)  ]

        
    def _is_external_sect(self,sectD):
        return sectD['beg_loc'] is None
    
    def loc_to_warper( self, loc_id ):

        for swLoc in self.sectionL:
            if swLoc.beg_loc_id() <= loc_id and loc_id <= swLoc.end_loc_id():
                return swLoc
            
        print(f"Section warper not found for loc:{loc_id}.")

        
        
def process_one_take( args, ss, perfTakeD ):

    featL = []
    beg_loc = perfTakeD['beg_loc']
    perf_note_idx = 0

    # while there are performed sections to process in this take
    while beg_loc < perfTakeD['end_loc'] and perf_note_idx < len(perfTakeD['tracked_perfL']):

        spuriousN = 0

        # get the score-group info record that includes 'beg_loc'
        warper = ss.loc_to_warper( beg_loc )

        print( perfTakeD['player'], "take:",perfTakeD['take_numb'], "section:", warper.label(), "beg loc:", beg_loc, "end loc:",perfTakeD['end_loc'] )

        cont_fl = True

        # for each note in the performance
        while cont_fl and perf_note_idx < len(perfTakeD['tracked_perfL']):

            # get the perf. note 
            perf_note = types.SimpleNamespace(**perfTakeD['tracked_perfL'][perf_note_idx])

            # if the perf. note is past the end of the current warper
            if perf_note.loc is not None and perf_note.loc > warper.end_loc_id():
                # advance the performance beg_loc to the next score section
                beg_loc = warper.end_loc_id() + 1
                cont_fl = False

            else:
                warper.insert_perf_note( perf_note.loc, perf_note.sec, perf_note.pitch, perf_note.vel )
                perf_note_idx += 1

        # if the current warper has all perf. data
        if not cont_fl or perf_note_idx >= len(perfTakeD['tracked_perfL']):

            # if at least half of the notes of score section were played
            if warper.perf_note_count()>warper.score_note_count()/2:
                # print("Calc. Features.")
                featD = warper.calc_features(args)
                featD['player'] = perfTakeD['player']
                featD['take_numb'] = perfTakeD['take_numb']
                featD['section_label'] = warper.label()

                featL.append(featD)
            
            warper.perf_reset()
    
    return featL

def generate_perf_feature_file( args, perf_sf_fnameL ):

    def _gen_list_of_feature_vectors(args, perf_sf_fnameL):
        featL = []

        # for each score followed performance 
        for perf_sf_fname in perf_sf_fnameL:
            perf_sf_path = os.path.join(args.perf_sf_dir,perf_sf_fname)

            # open a score-followed performance file
            with open(perf_sf_path) as f:
                perfL = yaml.safe_load(f)

            # for each recorded take (which may contain multiple sections and therefore return mult. feat vectors)
            for perfTakeD in perfL:
                featL += process_one_take( args, ss, perfTakeD)

        return featL
        

    def _impute_missing_values( featL ):
        ok_fldL    = ['section_label','player','take_numb','sect_dur_sec','perf_note_cnt','tracked_pct','missed_pct','spurious_pct','time_fact','dyn_fact','time_MSE','dyn_MSE']
        check_fldL = ['even_grp_std','dyn_grp_mse','chord_std','tempo_bpm','beat_mse']
        
        for label in ok_fldL + check_fldL:
            update_idxL = []
            valueL = []
            for i,f in enumerate(featL):
                if label in ok_fldL:
                    assert f[label] is not None
                elif label in check_fldL:
                    if f[label] is None:
                       update_idxL.append(i)
                    else:
                        valueL.append(f[label])                    
                else:
                    assert False
                    
            if len(update_idxL) > 0:
                assert len(valueL)
                avg_val = np.mean(valueL)
                for i in update_idxL:
                    featL[i][label] = avg_val

        return featL
    
    # get the score group information - which the performance will be compared to
    ss = ScoreSections(args.score_group_fname)

    # generate a feature vector (dictionary) for each section in each recorded take
    featL = _gen_list_of_feature_vectors(args,perf_sf_fnameL)

    # fill in missing values 
    featL = _impute_missing_values(featL)
    
    # form the output file name
    out_fname = os.path.join(args.out_dir,f"{args.out_fname}.csv")

    # write a feature vector to each row of the CSV
    with open(out_fname,"w") as f:
        hdrL = ['section_label','player','take_numb']
        field_nameL = hdrL + [ x for x in list(featL[0].keys()) if x not in hdrL ]
        
        wtr = csv.DictWriter(f,field_nameL)
        wtr.writeheader()
        for featD in featL:
            wtr.writerow(featD)


                

if __name__ == "__main__":
    
    # Score group-info file
    # from python -m piano --config ../gutim_1/config.yaml gen-group-info
    score_group_fname = "../gutim_1/output/group_info.json"

    # Directory of tracked performance files from ../score_follower
    perf_sf_dir       = "../score_follow/sf_track"
    out_dir           = "output"
    out_fname         = "perf_feat"
    
    # Score tracked recording sessions.
    playerL           = [ "arseniy1.yaml", "han1.yaml", "han2.yaml", "nicolas1.yaml", "nicolas2.yaml", "shiau_uen1.yaml","shiau_uen2.yaml"]

    os.makedirs(out_dir,exist_ok=True)

    args = dict(
        score_group_fname=os.path.expanduser(score_group_fname),
        perf_sf_dir=os.path.expanduser(perf_sf_dir),
        out_dir=out_dir,
        out_fname=out_fname,
        tempo_period_error=0.5,
        tempo_min_period_count=2   
    )

    args = types.SimpleNamespace(**args)

    # Generate performance features into {out_dir}/{out_fname}.csv
    generate_perf_feature_file( args, playerL )

    # See gen_training_data.py for how to use the performane feature CSV to generate training data.
    
    
    
