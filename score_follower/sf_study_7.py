import os
import csv
import json
import math
import types
import logging
import numpy as np
from tqdm import tqdm
from matplotlib import pyplot as plt

log = logging.getLogger(os.path.basename(__file__).split('.')[0])


class Loc:
    def __init__(self,loc,meas,sec):
        self.loc_id = loc
        self.meas = meas
        self.sec = sec
        self.pitch_list_idxL = []  # index into score.pitchL[] of each note at this loc

    def min_pitch_list_index(self):
        return min(self.pitch_list_idxL)

    def pitch_count(self):
        return len(self.pitch_list_idxL)

    def __str__(self):
        return 'id:' + str(self.loc_id) + ' meas:' +str(self.meas) + ' sec:' + str(self.sec) + ' ' +str(self.pitch_list_idxL)

class Note:
    def __init__(self,uid,loc,meas,pitch,vel,map_vel,sci_pitch):
        self.uid = uid
        self.loc_id = loc
        self.meas = meas
        self.pitch = pitch
        self.vel = vel
        self.map_vel = map_vel
        self.sci_pitch=sci_pitch

    def __str__(self):
        return 'uid:' + str(self.uid) + ' loc:' +str(self.loc_id) + ' meas:' +str(self.meas) + ' pitch:' + str(self.pitch) + ' vel:' +str(self.vel)
        
class Score:
    def __init__(self, fname_csv,vel_tbl):

        self.sectionL = None  # [ { section_id:<>, beg_loc_id:<>, end_oloc_id:<>} ]
        self.eGroupL  = None  # [ { section_id:<>, olocL:[], target_section_id:<> } ]
        self.tGroupL  = None  # [ { section_id:<>, olocL:[], target_section_id:<> } ]
        self.dGroupL  = None  # [ { section_id:<>, olocL:[], target_section_id:<> } ]
        self.barL     = None  # [ (meas_num,loc_id) ]
                
        scoreD = self._parse_score_csv(fname_csv)

        pitch_uid = 0
        
        self.pitchL = []  # [ Note( uid:<>, loc_id:<>, meas:<>, pitch:<>, vel:<> ) ]  # pitch list in time order
        self.locL   = []  # [ Loc loc:<>, sec:<>, meas:<>, pitch_list_idxL:<> )]      # pitch list at location
        self.locMapD= {}  # { loc_id:loc_list_idx }


        for loc,d in scoreD.items():
            new_loc = Loc(loc,d['meas'],d['sec'])

            for r in d['noteL']:
                map_vel = vel_tbl[ r['vel'] ]
                self.pitchL.append( Note(pitch_uid,loc,d['meas'],r['pitch'],r['vel'],map_vel,r['sci_pitch']) )
                new_loc.pitch_list_idxL.append(pitch_uid)
                pitch_uid += 1

            self.locL.append(new_loc)

        self._validate_sequential_locations()

        # sort both lists in time order
        self.pitchL = sorted(self.pitchL,key=lambda x:x.loc_id)
        self.locL   = sorted(self.locL,  key=lambda x:x.loc_id)
        
        # set the loc.pitch_idxL[] to the index into pitchL[] of the associated note
        # (we can't do this earlier because pitchL[] is resorted after being formed.)
        for i,r in enumerate(self.locL):
            self.locMapD[r.loc_id] = i
            for i,uid in enumerate(r.pitch_list_idxL):
                r.pitch_list_idxL[i] = next((j for j, d in enumerate(self.pitchL) if d.uid == uid))
                
            r.pitch_list_idxL = sorted(r.pitch_list_idxL)


    def get_groups(self, beg_loc_id, end_loc_id ):
        """
        return group location lists of the form:
        [ { section_id:<>, target_section_id:<>, olocL:[] } ]
        """

        def _rpt_groups( label, gL ):
            for d in gL:
                print(f"{label} : sec:{d['section_id']} tgt:{d['target_section_id']} : ",end="")
                for loc_id in d['olocL']:
                    print(f"{loc_id:4} ",end=" ")
                print("")
        
        def _get_groups( groupL, beg_loc_id, end_loc_id ):
            gL = []
            for d in groupL:
                if beg_loc_id <= d['olocL'][0] and d['olocL'][-1] <= end_loc_id:
                    gL.append(d)
                    
            return gL
        
        egL = _get_groups(self.eGroupL,beg_loc_id,end_loc_id)
        tgL = _get_groups(self.tGroupL,beg_loc_id,end_loc_id)
        dgL = _get_groups(self.dGroupL,beg_loc_id,end_loc_id)

        if False:
            _rpt_groups("even ",egL)
            _rpt_groups("tempo",tgL)
            _rpt_groups("dynam",dgL)

        return egL,tgL,dgL
    
    def min_loc_id(self):
        return self.locL[0].loc_id
                       
    def max_loc_id(self):
        return self.locL[-1].loc_id

    def get_loc(self,loc):
        return self.locL[ locD[loc] ]

    def note_count( self, beg_loc, end_loc ):
        # Return the count of notes including the two locations
        n = 0
        for p in self.pitchL:
            if beg_loc <= p.loc_id and p.loc_id <= end_loc:
                n += 1

        return n

    def report(self,beg_loc=None,end_loc=None):
        if beg_loc is None:
            beg_loc = self.min_loc_id();
            
        if end_loc is None:
            end_loc = self.max_loc_id();
            
        bli = self.locMapD[beg_loc]
        eli = self.locMapD[end_loc]

        print("loc    sec  pch")
        print("---- ------ ---")
        
        for loc in self.locL[bli:eli+1]:
            for pi in loc.pitch_list_idxL:
                pr = self.pitchL[ pi ]
                print(f"{pr.loc_id:4} {self.locL[ self.locMapD[pr.loc_id] ].sec:6.2f} {pr.pitch:3}")

    def _parse_score_csv( self, score_csv_fname ):

        def _parse_numbers( r ):
            for k,v in r.items():
                if v.strip():
                    if k in ['oloc','meas','status','d0','d1']:
                        r[k] = int(v.strip())
                    elif k in ['sec']:
                        r[k] = float(v.strip())
                    elif k in ['section','sci_pitch']:
                        r[k] = v.strip()
                        

        def _parse_group(groupL,section_id,oloc,token,codeL,target_section_id=None):

            # if the previous even group is closed then start a new one
            if len(groupL) == 0 or groupL[-1]['target_section_id'] is not None:
                groupL.append( dict(section_id=section_id, olocL=[], target_section_id=target_section_id ) )
                
            groupL[-1]['olocL'].append(oloc)

            if target_section_id is None:
                s = token.strip()
                i =  None if s not in codeL else codeL.index(s)
                if i is None:
                    groupL[-1]['target_section_id'] = int(s[1:].strip())
                elif i == 0:
                    pass
                elif i == 1:
                    # temporarily set the target to the beg. section id
                    groupL[-1]['target_section_id'] = groupL[-1]['section_id']
                else:
                    assert 0
                
                
        def _set_group_target_sections(groupL):

            assert groupL[-1]['section_id'] != groupL[-1]['target_section_id']
            
            tgt_sect_id = groupL[-1]['target_section_id']
            sect_id     = groupL[-1]['section_id']
            
            for g in reversed(groupL):

                if g['section_id'] == sect_id:
                    g['target_section_id'] = tgt_sect_id
                else:
                    sect_id     = g['section_id']
                    tgt_sect_id = g['target_section_id']
            
        
        # Return [ {loc:<> meas:<>, noteL:[{ pitch:<>, vel:<>} ] }]
        scoreD = {}
        self.sectionL = []
        self.eGroupL = []
        self.tGroupL = []
        self.dGroupL = []
        self.barL   = []  # [ (meas_num,loc_id) ]
        
        meas_num = 0
        
        with open(score_csv_fname) as f:
            rdr = csv.DictReader(f)

            for i,r in enumerate(rdr):

                _parse_numbers(r)

                # if this is the begin of a new section
                if r['section']:
                    self.sectionL.append( dict(section_id=r['section'], beg_oloc=None, end_oloc=None) )                    
                    
                # if this is a note-on
                if r['status'] and r['status'] == 0x90 and r['d1'] > 0:

                    if r['meas'] is not None and r['meas'] != meas_num:
                        self.barL.append( (r['meas'],r['oloc']) )
                        meas_num = r['meas']

                    
                    if r['oloc'] not in scoreD:
                        scoreD[ r['oloc'] ] = { 'loc':r['oloc'], 'meas':r['meas'], 'sec':r['sec'],'noteL':[] }

                    scoreD[ r['oloc'] ]['noteL'].append( dict(pitch=r['d0'], vel=r['d1'],sci_pitch=r['sci_pitch'] ) )

                    # track the last loc in the section
                    self.sectionL[-1]['end_oloc'] = r['oloc']

                    # if this is the first note in the section
                    if self.sectionL[-1]['beg_oloc'] is None:
                        self.sectionL[-1]['beg_oloc'] = r['oloc']

                    # if this note is marked for 'evenness'
                    if r['even']:
                        even_tgt = None if 'even_target' not in r else r['even_target']
                        _parse_group(self.eGroupL,self.sectionL[-1]['section_id'],r['oloc'],r['even'].strip(),['e','E'],even_tgt)

                    # if this note is marked for 'tempo'
                    if r['tempo']:
                        tempo_tgt = None if 'tempo_target' not in r else r['tempo_target']
                        _parse_group(self.tGroupL,self.sectionL[-1]['section_id'],r['oloc'],r['tempo'].strip(),['t','T'],tempo_tgt)

                    # if this note ismarked for 'dynamics'
                    if r['dyn']:
                        dyn_tgt = None if 'dyn_target' not in r else r['dyn_target']
                        _parse_group(self.dGroupL,self.sectionL[-1]['section_id'],r['oloc'],r['dyn'].strip(),['d','D'],dyn_tgt)

                        

                        
                #if r['onset'] and not r['status']:
                #    print("missing status:",i,r['oloc'])

            # set the target section id in each group
            _set_group_target_sections(self.eGroupL)
            _set_group_target_sections(self.tGroupL)
            _set_group_target_sections(self.dGroupL)
            
        return scoreD

    def _validate_sequential_locations( self ):

        loc_id0 = None
        sec0    = None
        lpassN = 0
        lfailN = 0
        tpassN = 0
        tfailN = 0
        
        for loc in self.locL:
            if loc_id0 is None:
                loc_id0 = loc.loc_id
            else:
                if loc.loc_id < loc_id0:
                    print("Loc Fail:",loc.loc_id," < ", loc_id0)
                    lfailN += 1
                else:
                    lpassN += 1
                    
                    

            if sec0 is None:
                sec0 = loc.sec
            else:
                if loc.sec < sec0:
                    print("Time Fail",loc.sec,sec0)
                    tfailN += 1
                else:
                    tpassN += 1
                    
            loc_id0 = loc.loc_id
            sec0 = loc.sec
            

class Follower:
    def __init__(self,sf):
        self.sf = sf

        self.new_note_idx = 0
        
        self.exp_loc_idx = None
        self.prv_loc_idx = None

        # count of times this pitch has been matched: 
        self.pitch_match_cntL = [ 0 for _ in range(len(self.sf.score.pitchL)) ]
        self.loc_match_cntL   = [ 0 for _ in range(len(self.sf.score.locL)) ]        
        self.expV             = [ 0 for _ in range(len(self.sf.score.pitchL)) ]
        
        self.search_bpi = None
        self.search_epi = None

        self.beg_score_sec  = None # score time of the first match
        self.beg_perf_sec   = None # perf time of the first match
        self.time_delta_sum = 0.0  # score_time * time_fact = perf_time
        self.time_delta_cnt = 0
        self.time_fact      = 1.0

        self.prev_match_perf_sec = None
        self.decay_cnt = 0

    def reset( self, beg_loc_id ):
        
        assert len(self.pitch_match_cntL) == len(self.expV)

        self.new_note_idx = 0

        #print("reset expV:",beg_loc_id)
        
        for i in range(len(self.pitch_match_cntL)):
            self.pitch_match_cntL[i] = 0
            self.expV[i] = 0

        for i in range(len(self.loc_match_cntL)):
            self.loc_match_cntL[i] = 0

        self.exp_loc_idx = self.sf.score.locMapD[ beg_loc_id ]
        self.search_bpi = None
        self.search_epi = None
        
        self.beg_score_sec  = None # score time of the first match
        self.beg_perf_sec   = None # perf time of the first match
        self.time_delta_sum = 0.0  # score_time * time_fact = perf_time
        self.time_delta_cnt = 0
        self.time_fact      = 1.0

        self.prev_perf_sec = None
        self.prev_match_perf_sec = None

        self.loc_cost  = 0
        self.time_cost = 0

        self.decay_cnt = 0

        
        # apply the affinity window because the likelihood of getting the first note wrong is low
        self._apply_affinity(beg_loc_id)
        
        
    def on_new_note(self, sec, pitch, vel, rpt_fl ):

        def report_dbg(pitch,vel,loc_idx):

            loc_id = self.sf.score.locL[ loc_idx ].loc_id
            
            print(f"loc:{loc_id} pitch:{pitch} vel:{vel} bpi:{self.search_bpi} epi:{self.search_epi}")

            for i,n in enumerate(self.pitch_match_cntL[self.search_bpi:self.search_epi+1]):
                fl = self.sf.score.pitchL[ self.search_bpi+i ].loc_id == loc_id
                p0="(" if fl else ""
                p1=")" if fl else " "
                print(f"{p0}{n:4}{p1}",end="")
            print("")
            
            for i,e in enumerate(self.expV[self.search_bpi:self.search_epi+1]):
                fl = self.sf.score.pitchL[ self.search_bpi+i ].loc_id == loc_id
                p0="(" if fl else ""
                p1=")" if fl else " "
                print(f"{p0}{e:4.2f}{p1}",end="")
            print("")
            
            for i,p in enumerate(self.sf.score.pitchL[self.search_bpi:self.search_epi+1]):
                fl = self.sf.score.pitchL[ self.search_bpi+i ].loc_id == loc_id
                p0="(" if fl else ""
                p1=")" if fl else " "
                print(f"{p0}{p.pitch:4}{p1}",end="")
            print("")


        end_fl           = False        
        rpt_status       = "spurious"
        match_loc_id     = None
        d_match_perf_sec = None
        d_match_score_sec= None
        d_loc_id         = None        
        exp_loc_id       = None
        exp_sec          = None
        d_exp_sec        = None
        
        d_sec            = 0.0
        d_sec_err        = 0.0
        
        exp_loc_id       = None if self.exp_loc_idx is None else self.sf.score.locL[ self.exp_loc_idx ].loc_id
        prev_loc_id      = None if self.prv_loc_idx is None else self.sf.score.locL[ self.prv_loc_idx ].loc_id
        prev_sec         = None if self.prv_loc_idx is None else self.sf.score.locL[ self.prv_loc_idx ].sec

        d_perf_sec = self.prev_perf_sec is not None and (sec - self.prev_perf_sec)

        # get the search window
        li,self.search_bpi,self.search_epi = self.sf.loc_wndL[ self.exp_loc_idx ]
        assert li == self.exp_loc_idx


        # locate the matching pitch with the maximum expectation and which was not matched previously
        match_pi  = None
        match_val = None
        
        for pi in range(self.search_bpi,self.search_epi+1):            
            if self.pitch_match_cntL[pi]==0 and self.sf.score.pitchL[pi].pitch == pitch and (match_val is None or self.expV[pi]>match_val):
                match_pi = pi
                match_val = self.expV[pi]
                
        # there is not match for this pitch
        if match_pi is None:
            #if self.new_note_idx == 88:
            #    breakpoint()
            pass
        
        else:
            match_loc_id = self.sf.score.pitchL[match_pi].loc_id
            match_loc_idx = self.sf.score.locMapD[match_loc_id]
            match_sec     = self.sf.score.locL[ match_loc_idx ].sec

            # count of loc's between expected and actual
            d_loc_id = None if exp_loc_id is None else (match_loc_id - exp_loc_id)

            # if this is the first matched location since a reset then record the score and perf. time
            if self.beg_score_sec is None:
                self.beg_score_sec = match_sec
                self.beg_perf_sec = sec

            # delta score time between this match and previous match
            d_match_score_sec      = None if prev_sec is None else match_sec - prev_sec

            # delta perf time between this match and previous match
            d_match_perf_sec = None if self.prev_match_perf_sec is None else sec - self.prev_match_perf_sec

            # given the delta time between this matched event and the previous matched event
            # in both score seconds and performance seconds
            if d_match_score_sec and d_match_perf_sec:

                # correct the score seconds to match the performed tempo
                d_corr_match_score_sec = d_match_score_sec / self.time_fact

                # diff between perf. elapsed time and the score's corrected elapsed time 
                d_sec = d_match_perf_sec - d_corr_match_score_sec
                d_sec_err = abs(d_sec)


            stats_0_fl = d_loc_id is not None and 0 <= d_loc_id and d_loc_id < self.sf.args.d_loc_stats_thresh
            stats_1_fl = d_match_perf_sec and d_match_score_sec and d_perf_sec < 1.0 and d_match_perf_sec / d_match_score_sec < 2
                
            # if the d_loc is positive and less than 'd_loc_stats_thresh' ....
            if stats_0_fl and stats_1_fl :

                # ... and if the current time is sane relative to the first match time
                # ... then this is probably a good match - update the 'time_fact'                                
                if sec - self.beg_perf_sec > 0 and (match_sec - self.beg_score_sec) > 0:
                    self.time_delta_sum += (match_sec - self.beg_score_sec)/(sec - self.beg_perf_sec)
                    self.time_delta_cnt += 1
                    self.time_fact = self.time_delta_sum / self.time_delta_cnt


            dloc_fail_fl = lambda x,thresh : (x is not None) and (abs(x)>thresh)

            lo_thresh_sec_fl = d_sec_err > self.sf.args.d_sec_err_thresh_lo
            lo_thresh_loc_fl = dloc_fail_fl(d_loc_id,self.sf.args.d_loc_thresh_lo)
            hi_thresh_sec_fl = (d_loc_id>=self.sf.args.d_loc_thresh_lo and d_sec_err > self.sf.args.d_sec_err_thresh_hi)
            hi_thresh_loc_fl = dloc_fail_fl(d_loc_id,self.sf.args.d_loc_thresh_hi)
            
            # if the location or time jump to the matched location was too great then reject this match
            #if (d_sec_err > self.sf.args.d_sec_err_thresh_lo and dloc_fail_fl(d_loc_id,self.sf.args.d_loc_thresh_lo)) or dloc_fail_fl(d_loc_id,self.sf.args.d_loc_thresh_hi) or (d_loc_id>0 and d_sec_err > self.sf.args.d_sec_err_thresh_hi):
            if (lo_thresh_sec_fl and lo_thresh_loc_fl) or hi_thresh_loc_fl or hi_thresh_sec_fl:
                
                match_pi   = None
                rpt_status = f"reject ({lo_thresh_loc_fl} and {lo_thresh_sec_fl}) or {hi_thresh_loc_fl} or {hi_thresh_sec_fl} : {stats_0_fl} {stats_1_fl} )"

                # if the loc jump is large and postive
                if d_loc_id > self.sf.args.d_loc_thresh_hi:
                    self.loc_cost += 1
                    
                # if the time jump is large and positive
                if d_sec > self.sf.args.d_sec_err_thresh_hi:
                    self.time_cost += 1
                    
            else:

                self.loc_cost  = max(0,self.loc_cost - 0.5)
                self.time_cost = max(0,self.time_cost - 0.5 )
                
                self.prev_match_perf_sec               = sec
                self.prv_loc_idx                       = match_loc_idx            
                self.loc_match_cntL[ match_loc_idx  ] += 1
                self.pitch_match_cntL[match_pi]       += 1

                if self.sf.score.locL[ match_loc_idx ].loc_id > self.sf.end_loc_id:
                    end_fl = True

                else:
                    # estimate the next expected location by advancing to the next location that has not been matched
                    exp_loc_idx = match_loc_idx
                    while exp_loc_idx < len(self.sf.score.locL) and self.loc_match_cntL[ exp_loc_idx ] >= len(self.sf.score.locL[exp_loc_idx].pitch_list_idxL):
                        exp_loc_idx += 1

                    if exp_loc_idx > len(self.sf.score.locL):
                        if rpt_fl:
                            log.info("The end of score was encountered while advancing the next expected location.")
                        end_fl = True
                    else:
                        exp_loc_id = self.sf.score.locL[ exp_loc_idx ].loc_id

                        self._apply_affinity( exp_loc_id )            
                        self.exp_loc_idx = self.sf.score.locMapD[ exp_loc_id ]

                    rpt_status = ""

            
                if self.exp_loc_idx is not None:            
                    exp_loc_id = self.sf.score.locL[ self.exp_loc_idx ].loc_id
                    exp_sec    = self.sf.score.locL[ self.exp_loc_idx ].sec
                    d_exp_sec  = None if prev_sec is None else exp_sec - prev_sec


        ff   = lambda x: "      " if x is None else f"{x:6.3f}"
        fid  = lambda x: "    " if x is None else f"{x:4}"

        if vel < 5:
            rpt_status += f" vel({vel})"

        if rpt_fl:
            print(f"{self.new_note_idx:4} pitch:{pitch:3} vel:{vel:3} : LOC: prv:{prev_loc_id} match:{match_loc_id if match_loc_id else '****'} exp:{exp_loc_id} : dLoc:{fid(d_loc_id)} | Match dsec score:{ff(d_match_score_sec)} perf:{ff(d_match_perf_sec)} corr:{ff(d_sec)} : ({self.time_delta_sum} {self.time_delta_cnt} {self.time_fact}) : {rpt_status}")

        self.new_note_idx += 1
        self.prev_perf_sec = sec

        return match_pi,end_fl
    
    def do_decay(self):

        if self.search_bpi is not None and self.search_epi is not None:
            
            #print("decay:",self.search_bpi,self.search_epi)
            self.decay_cnt += 1
            
            for pi in range(self.search_bpi,self.search_epi+1):
                self.expV[pi] = self.sf.args.decay_coeff * self.expV[pi]


    def _apply_affinity( self, loc_id  ):

        loc_idx = self.sf.score.locMapD[ loc_id ]
        
        li,bpi,affL = self.sf.loc_affL[loc_idx]
        
        assert li == loc_idx

        #print("apply:",loc_id,loc_idx," : ",bpi,bpi+len(affL)-1, " decay:",self.decay_cnt)
        self.decay_cnt = 0;
        
        for i,pi in enumerate(range(bpi,bpi+len(affL))):
            self.expV[pi] += affL[i]
            

    
class ScoreFollower:
    def __init__(self, args, score):

        self.args = args
        self.score = score
        self.beg_loc_id = None
        self.end_loc_id = None

        # Affinity window for each location: (li,[])
        self.loc_affL = self._calc_affinity(args.pre_affinity_sec,args.post_affinity_sec,args.min_affinity_loc_cnt)

        # Find begin/end pitch index search window 
        self.loc_wndL = self._calc_search_wnd(args.pre_wnd_sec,args.post_wnd_sec,args.min_wnd_loc_cnt)

        self.pitch_match_cntL = [ 0 for _ in range(len(self.score.pitchL)) ]

        self.fL = []
        for i in range(2):
            self.fL.append( types.SimpleNamespace(**dict(f=Follower(self),age=-1) ))

    def reset( self, beg_loc_id=0, end_loc_id=None ):

        self.beg_loc_id = beg_loc_id
        self.end_loc_id = self.score.max_loc_id() if end_loc_id is None else end_loc_id
        
        assert self.score.min_loc_id() <= beg_loc_id and beg_loc_id <= self.score.max_loc_id()

        for i in range(len(self.pitch_match_cntL)):
            self.pitch_match_cntL[i] = 0

        for i,r in enumerate(self.fL):
            if i == 0:
                r.f.reset(beg_loc_id)
                r.age = 0
            else:
                r.age = -1
        
    def on_new_note(self, sec, pitch, vel, rpt_fl ):

        end_fl = False
        match_pi = None
        cost = 0
        n = 0
        resultL = []
        for i,r in enumerate(self.fL):
            if r.age>=0:
                match_pi,end_fl = r.f.on_new_note(sec,pitch,vel,rpt_fl)
                cost = r.f.loc_cost + r.f.time_cost
                r.age += 1
                resultL.append((i,match_pi,end_fl,cost,r.age))
                n += 1
            
                
        if match_pi is not None:
            self.pitch_match_cntL[match_pi] += 1
        
        return match_pi,end_fl
        
    def do_decay(self):

        for r in self.fL:
            if r.age>=0:
                r.f.do_decay()

                
    def _calc_affinity( self, pre_wnd_sec, post_wnd_sec, min_loc_cnt ):

        def affinity_func( t0, t1, wnd_dur_sec ):
            # for post affinity: t0 <= t1
            # for pre affinty:   t0 > t1

            #assert abs(t1-t0) <= wnd_dur_sec

            return (wnd_dur_sec-abs(t1-t0))/wnd_dur_sec
            
        
        def calc_pre_affinity(li, t0_sec, wnd_dur_sec, min_loc_cnt ):
            affL = []
            locN = 0
            while li >= 0 and (t0_sec - self.score.locL[li].sec < wnd_dur_sec or locN<min_loc_cnt):
                assert( t0_sec - self.score.locL[li].sec >= 0 )
                affL.append((li, affinity_func(t0_sec,self.score.locL[li].sec, wnd_dur_sec)))
                li -= 1
                locN += 1

            return sorted(affL,key=lambda x:x[0])

        def calc_post_affinity(li, t0_sec, wnd_dur_sec, min_loc_cnt):
            affL = []
            locN = 0
            while li < len(self.score.locL) and (self.score.locL[li].sec - t0_sec < wnd_dur_sec or locN<min_loc_cnt):
                assert( self.score.locL[li].sec - t0_sec >= 0 )
                affL.append((li, affinity_func(t0_sec,self.score.locL[li].sec, wnd_dur_sec) ))
                li += 1
                locN += 1
                
            return affL


        pitch_affL = []
        for li,loc in enumerate(self.score.locL):

            bli = None
            eli = None
            
            # calculate the affinity function for locations preceding li
            affL0 = calc_pre_affinity( li-1,loc.sec, pre_wnd_sec, min_loc_cnt)

            # bli is the starting window location
            bli = None if len(affL0)==0 else affL0[0][0]
            eli = None if len(affL0)==0 else affL0[-1][0]
            
            # calculate the affinity function for locations at and after li
            affL1 = calc_post_affinity(li,  loc.sec, post_wnd_sec, min_loc_cnt)
            if bli is None:
                bli = None if len(affL1)==0 else affL1[0][0]

            if len(affL1)>0:
                eli = affL1[-1][0]
            
            # verify that affL1 starts exactly after affL0
            assert len(affL0)== 0 or len(affL1)==0 or affL0[-1][0] + 1 == affL1[0][0]

            
            affL = []
            bpi  = None
            
            # the affinity list is not empty
            if len(affL0) + len(affL1) > 0:

                # get the starting pitch index
                bpi = self.score.locL[bli].pitch_list_idxL[0]

                # fill in the pitch index
                for i,v in  affL0 + affL1:
                    for pi in self.score.locL[ i ].pitch_list_idxL:
                        affL.append( v )
                        assert self.score.pitchL[pi].loc_id == self.score.locL[i].loc_id
                    
                    assert len(affL)!=1 or len(affL)==1 and self.score.locL[ i ].pitch_list_idxL[0] == bpi

                
            # li  = center window location index - location associated with this affL
            # bpi = starting window pitch index
            # affL = affinity function associated with events begining at pitchL[bpi]
            pitch_affL.append((li,bpi,affL))

        return pitch_affL
            
    def _calc_search_wnd( self, pre_wnd_sec, post_wnd_sec, min_loc_cnt ):
        wndL = []
        for li,loc in enumerate(self.score.locL):
            
            bli = li  # search window begin location
            eli = li  # search window end location

            # backup from li to locate the begin of window - extend the pre-wnd-sec until at least 2 loc's exist prior to li
            locN=0
            while bli-1>=0 and (loc.sec - self.score.locL[bli-1].sec <= pre_wnd_sec or locN<min_loc_cnt):
                bli -= 1
                locN += 1

            # advance from li to locate end of window  - extend the pre-wnd-sec until at least 2 loc's exist prior to li
            locN = 0
            while eli+1<len(self.score.locL) and (self.score.locL[eli+1].sec - loc.sec <= post_wnd_sec or locN<min_loc_cnt):
                eli += 1
                locN += 1

            assert bli <= eli

            # bpi/epi seach window begin/end pitch indexes
            bpi = self.score.locL[bli].pitch_list_idxL[0]
            epi = self.score.locL[eli].pitch_list_idxL[-1]

            assert  bpi <= epi
            wndL.append((li,bpi,epi))

        return wndL

    def search_wnd_stats(self):
        
        nV = [ (epi-bpi)+1 for _,bpi,epi in self.loc_wndL ]
        nD = { n:0 for n in set(nV) }
        for n in nV:
            nD[n] += 1

        x,y = zip(*[(k,v) for k,v in nD.items()])
        _,ax = plt.subplots()
        ax.bar(x,y)
        ax.set_xlabel("search window note count")
        ax.set_ylabel("occurences")
        plt.show()

    def affinity_wnd_stats(self):

        nV = [ len(valL) for _,_,valL in self.loc_affL ]
        nD = { n:0 for n in set(nV) }
        for n in nV:
            nD[n] += 1

        x,y = zip(*[(k,v) for k,v in nD.items()])
        _,ax = plt.subplots()
        ax.bar(x,y)
        ax.set_xlabel("affinty window pitch count")
        ax.set_ylabel("occurences")
        plt.show()

    def affinity_report(self,N=10):
        for i in range(N):
            li,bpi,envL = self.loc_affL[i]

            print(li,bpi,len(envL),envL)
            
        

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


def summary_results( sf, trackL, last_pi, rpt_fl = True ):

    pi_2_perfD = { pi:perf_idx for pi,perf_idx in trackL if pi is not None }

    tot_spuriousN = 0
    tot_missedN = 0
    tot_matchedN = 0

    beg_pi = sf.score.locL[ sf.score.locMapD[sf.beg_loc_id] ].pitch_list_idxL[0]
    end_pi = sf.score.locL[ sf.score.locMapD[sf.end_loc_id] ].pitch_list_idxL[-1]

    # ordered on pi
    resultL = []  # (pi,perf_idx)  (pi=pitch_index) spurious:pi=None miss:perf_idx=None

    if last_pi is not None:

        # for each pitch in the score
        for i,matchN in enumerate(sf.pitch_match_cntL[beg_pi:min(last_pi,end_pi)]):

            pi = beg_pi + i
            perf_idx = None if matchN==0 else pi_2_perfD[pi]
            resultL.append((pi,perf_idx))

            tot_matchedN += matchN>0
            tot_missedN  += matchN==0

        #print(len(resultL),last_pi)

        # for each perf_idx that did not match the score
        for pi,perf_idx0 in trackL:
            if pi is None:

                tot_spuriousN += 1

                min_i = None
                min_v = None

                # scan forward to the perf_idx just before the one that did not match
                for i,(pi,perf_idx) in enumerate(resultL):
                    if perf_idx is not None and (perf_idx > perf_idx0):
                        resultL.insert(i,(None,perf_idx0))
                        break


                    
    if rpt_fl:
        print(f"Matched:{tot_matchedN} Missed:{tot_missedN} Spurious:{tot_spuriousN}")
                    
    return resultL, tot_matchedN, tot_missedN, tot_spuriousN

def midi_to_sci_pitch( midi ):
    pcD = {0:'C',1:'C#',2:'D',3:'D#',4:'E',5:'F',6:'F#',7:'G',8:'G#',9:'A',10:'A#',11:'B'}

    # 0=-1 12=0 24=1 36=2 48=3 60=4

    return f"{pcD[ midi % 12 ]}{ int(midi/12)-1 }"

def gen_timeline_json_input( sf, perfL, trackL, fname_json ):

    resultD = { 'score':{}, 'perf':[] }  # score:{ loc:{ meas:<>, sec:<> noteL:[ {pitch:<>} ] } }
                                         # perf:[ { sec:<>, noteL:[ { loc:<>, pitch:<> }] } ]

    # create the score representaiton
    for loc in sf.score.locL:
        noteL = [ dict(pitch=sf.score.pitchL[p_uid].pitch,sci_pitch=sf.score.pitchL[p_uid].sci_pitch) for p_uid in loc.pitch_list_idxL ]
        resultD['score'][ loc.loc_id ] = dict(meas=loc.meas, sec=loc.sec, noteL=noteL)

    # create a list of performed notes and the score loc they matched to
    perfNoteL = []
    for pi,perf_idx in trackL:
        if perf_idx is not None:
            sec   = perfL[perf_idx]['microsec']/1000000.0
            loc   = None if pi is None else sf.score.pitchL[pi].loc_id
            pitch = perfL[perf_idx]['pitch']
            perfNoteL.append( dict(sec=sec, loc=loc, pitch=pitch, sci_pitch=f"{perf_idx}:{midi_to_sci_pitch(pitch)}" ) )

            
    # sort the notes on performed time
    # perfNoteL = sorted(perfNoteL,key=lambda x:x['sec'])

    thresh_dsec = 0.1
    idx0        = None
    group_secL  = []

    
    # cluster notes performed at nearly the same time into chords
    for i,d in enumerate(perfNoteL):
        sec = d['sec']

        # if this is the end a group of notes that are all within thresh_dsec of one another
        if i==len(perfNoteL)-1 or len(group_secL)==0 or sec - group_secL[0] > thresh_dsec:

            if idx0 is not None:

                # form the chord note list
                k = i+1 if i == len(perfNoteL)-1 else i
                noteL = [ dict(loc=perfNoteL[j]['loc'], pitch=perfNoteL[j]['pitch'], sec=perfNoteL[j]['sec'], sci_pitch=perfNoteL[j]['sci_pitch']) for j in range(idx0,k) ]
                resultD['perf'].append( dict(sec=sum(group_secL)/len(group_secL),  noteL=noteL) )
                
            group_secL = [sec]
            idx0       = i
            
        else:
            assert sec - group_secL[0] <= thresh_dsec
            group_secL.append(sec)

    # write the result
    with open(fname_json,"w") as f:
        json.dump(resultD,f,indent=2)
        
def gen_sf_track_result( sf, perfL, trackL):
    
    # Return tracked performance as: [ { sec:<>, loc:<>, pitch:<>, vel:<> } ]

    trackedPerfL = []
    for pi,perf_idx in trackL:
        if perf_idx is not None:
            sec = perfL[perf_idx]['microsec']/1000000.0
            dur_sec = None if perfL[perf_idx]['dur_microsec'] is None else perfL[perf_idx]['dur_microsec']/1000000.0            
            loc = None if pi is None else sf.score.pitchL[pi].loc_id
            r = perfL[perf_idx]
            
            trackedPerfL.append( dict(sec=sec,
                                      dur_sec=dur_sec,
                                      loc=loc,
                                      pitch=r['pitch'],
                                      vel=r['vel'],
                                      damp_fl=r['sust_fl'],
                                      sost_fl=r['sost_fl'],
                                      soft_fl=r['soft_fl']))


    trackedPerfL = sorted(trackedPerfL,key=lambda x:x['sec'])
    sec0 = min((x['sec'] for x in trackedPerfL))
    for x in trackedPerfL:
        x['sec'] -= sec0
        
    return trackedPerfL
    
    

def print_results( sf, perfL, resultL ):

    print("loc  snote pidx pnote pvel Note")
    print("---- ----- ---- ----- ---- --------------------")
    loc_id = None
    for pi,perf_idx in resultL:

        if pi is not None:
            pr = sf.score.pitchL[pi]

            # print score loc_id
            if loc_id is None or pr.loc_id != loc_id:
                loc_id = pr.loc_id
                print(f"{loc_id:4} ",end="")
            else:
                print("     ",end="")

            # print score pitch 
            print(f"p:{pr.pitch:3} ", end="")

            # print the perf index
            # (this allows us to see how the performed sequence matches the score sequence)
            if perf_idx is None:
                print("        miss",end="")
            else:
                print(f"({perf_idx})",end="")
                
            print("")
            
        else: 

            print(f"           ({perf_idx}) p:{perfL[perf_idx]['pitch']} v:{perfL[perf_idx]['vel']} spurious")
                



            
def measure_performance( score, perfL, trackL, beg_loc_id, end_loc_id ):

    def _form_alignment_list( score, perfL, trackL ):
        miss_cnt = 0
        alignL = []

        for score_pi,perf_idx in trackL:

            # if this performed note was not matched
            if score_pi is None:
                miss_cnt += 1
                continue


            loc_id = score.pitchL[ score_pi ].loc_id;
            loc    = score.locL[ score.locMapD[ loc_id ] ]

            assert perfL[ perf_idx ]['pitch'] == score.pitchL[ score_pi ].pitch

            alignL.append( dict(score_loc_id = loc.loc_id,
                                score_sec    = loc.sec,
                                score_pitch  = score.pitchL[ score_pi ].pitch,
                                score_vel    = score.pitchL[ score_pi ].vel,
                                perf_sec     = perfL[ perf_idx ]['microsec']/1000000.0,
                                perf_vel     = perfL[ perf_idx ]['vel'] ))

        return alignL
    
    def _distance( aV, bV ):
        # Perform linear curve fit: fit b = m*a + c
        coeffs = np.polyfit(aV, bV, deg=1)
        m, c = coeffs

        #print(f"Slope (m): {m}")
        #print(f"Intercept (c): {c}")

        # Generate fitted values
        xV = m * aV + c

        mse = (np.square(xV - bV)).mean()

        return mse

    def _vel_diff( alignL ):
        aV,bV = zip(*[(d['perf_vel'],d['score_vel']) for d in alignL])
        return _distance(np.array(aV),np.array(bV))

    def _time_diff( alignL ):
        aV,bV = zip(*[(d['perf_sec'],d['score_sec']) for d in alignL])
        return _distance(np.array(aV),np.array(bV))

    def _evenness( egroup, alignL ):
        alignD = { d['score_loc_id']:d for d in alignL }

        secL = [] # one entry for each evenness location
        idxL = [] # indexes into secL of valid sec value
        for loc_id in egroup['olocL']:
            sec = None
            if loc_id in alignD:
                sec = alignD[loc_id]['perf_sec'] 
                idxL.append(len(secL))
                
            secL.append(sec)

        if len(idxL) < 2:
            assert 0

        dsecL = []
        for i1 in range(1,len(idxL)):
            i0 = i1-1
            idx0 = idxL[i0]
            idx1 = idxL[i1]

            assert idx1-idx0 >= 1 
            assert idx0<len(secL) and idx1<len(secL) 
            dsec = (secL[idx1] - secL[idx0]) / (idx1-idx0)
            dsecL.append(dsec)


        return np.std(dsecL)

    def _even_meas( egroupL, alignL ):

        x = 0;
        for egroup in egroupL:
            x += _evenness(egroup,alignL)

        return 0 if len(egroupL)==0 else  x/len(egroupL)

    def _tempo_meas( tgroupL, alignL ):
        
        x = 0
        for tgroup in tgroupL:
            x += _evenness(tgroup,alignL)

        return 0 if len(tgroupL)==0 else x/len(tgroupL)
    

    egL,tgL,dgL = score.get_groups(beg_loc_id, end_loc_id )

    alignL = _form_alignment_list(score,perfL,trackL)

    dVel = _vel_diff(alignL)
    dSec = _time_diff(alignL)
    even = 0 #_even_meas(egL,alignL)
    tempo = 0 #_tempo_meas(tgL,alignL)
    
    # print('dVel:',dVel,'dSec:',dSec,'evn',even,'tempo',tempo)

    return dVel,dSec,even,tempo


def run_tracker( sf, perfL, score,beg_loc, end_loc, args ):

    resultL       = []
    tot_matchedN  = 0
    tot_missedN   = 0
    tot_spuriousN = 0

    score_note_cnt = score.note_count(beg_loc,end_loc)

    if False:
        print("Score:")
        sf.score.report(beg_loc,end_loc)
    
    sf.reset(beg_loc,end_loc)

    #sf.search_wnd_stats()
    #sf.affinity_wnd_stats()
    #sf.affinity_report()
    

    if len(perfL) > 0:


        if False and args.limit_perf_N is not None:
            print("Performance:")
            report_perf(perfL,args.limit_perf_N)    

        args.smp_per_cycle = 64

        bsi      = 0
        perf_idx = 0
        trackL   = []      #[(matched_pitch_index into score.perfL[], perf_idx into perfL[])]
        end_fl   = False
        beg_micro = None

        pr = perfL[perf_idx]

        sample_n = perfL[-1]['sample_idx']
        last_matched_pi = None

        # for each sample cycle in the input performance
        while not end_fl and bsi <= sample_n and perf_idx < len(perfL) and (args.limit_perf_N is None or perf_idx<args.limit_perf_N):

            # if the next performed note is inside this sample frame
            while bsi <= pr['sample_idx'] and pr['sample_idx'] < bsi+args.smp_per_cycle:

                if beg_micro is None:
                    beg_micro = pr['microsec']

                # update the score follower with the performed note and return the matched pitch index from score.pitchL[]
                pi,end_fl = sf.on_new_note( pr['microsec']/1000000.0, pr['pitch'],pr['vel'],args.rpt_fl)

                # track the last matched pi for reporting results
                if pi is not None and (last_matched_pi is None or pi > last_matched_pi):
                    last_matched_pi = pi

                # record the status of the match
                trackL.append((pi,perf_idx))

                # advance the performance 
                perf_idx += 1

                if perf_idx >= len(perfL):
                    break

                pr = perfL[ perf_idx ]


            sf.do_decay()
            bsi += args.smp_per_cycle

        resultL, tot_matchedN, tot_missedN, tot_spuriousN = summary_results( sf, trackL, last_matched_pi, args.rpt_fl )

        dVel,dSec,even_meas,tempo_meas = measure_performance(score,perfL,trackL,beg_loc,end_loc)
        
        #print_results(sf,perfL,resultL)
        dVel,dSec = 0,0
    
    return score_note_cnt, len(perfL), tot_matchedN, tot_missedN, tot_spuriousN, dVel, dSec, even_meas, tempo_meas, trackL

def plot_time_tracking_result( ax, score, trackLL, beg_loc, end_loc, draw_bars_func, colorL ):

    def _get_score_xy( beg_loc, end_loc, score ):
        xL = []
        yL = []
        
        for pitch_idx,p in enumerate(score.pitchL):
            if beg_loc <= p.loc_id and p.loc_id <= end_loc:
                loc = score.locL[ score.locMapD[p.loc_id] ]
                xL.append(loc.loc_id)
                yL.append(loc.sec)
        
        yL = [ y-yL[0] for y in yL ]
        return xL,yL

    def _get_perf_xy( beg_loc, end_loc, score, perfL, trackL ):

        xL = []
        yL = []
        for pitch_idx, perf_idx in trackL:

            # if this is a missed score event then skip it
            if perf_idx is None or pitch_idx is None:
                continue

            sec = perfL[ perf_idx ]['microsec']/1000000.0
            loc_id = score.pitchL[ pitch_idx ].loc_id

            # skip notes that were matched out of order
            if len(yL) > 0 and sec < yL[-1] and yL[-1]-sec > 0.1:
                continue
            
            xL.append(loc_id)
            yL.append(sec)

        yL = [y-yL[0] for y in yL ]
        return xL,yL

    def _correct( sxL, syL, pxL, pyL ):

        aL = []
        bL = []
        for p_loc_id, p_sec in zip(pxL,pyL):
            si = sxL.index(p_loc_id)
            aL.append(p_sec)
            bL.append(syL[si])

        aV,bV = np.array(aL), np.array(bL)
        
        # Perform linear curve fit: fit b = m*a + c
        coeffs = np.polyfit(aV, bV, deg=1)
        m, c = coeffs

        #print(f"Slope (m): {m}")
        #print(f"Intercept (c): {c}")

        # Generate fitted values
        pyV = m * aV + c

        return pyV.tolist()
    
    sxL,syL = _get_score_xy(beg_loc,end_loc,score)

    draw_bars_func( ax, np.max(syL) )
    
    ax.plot(sxL,syL,'o',label='score')

    for i,(_,_,perfL,trackL) in enumerate(trackLL):    
        pxL,pyL = _get_perf_xy( beg_loc,end_loc,score,perfL,trackL)

        cyL = _correct(sxL,syL,pxL,pyL)

        raw_label = "meas." if i==0 else None
        fit_label = "fit"   if i==0 else None
        ax.plot(pxL,pyL,'-.',color=colorL[i % len(colorL)], label=raw_label)
        ax.plot(pxL,cyL,':.',color=colorL[i % len(colorL)], label=fit_label)

    ax.set_title(f"Time Fit.")
    ax.legend()
        
    ax.set_ylabel("Seconds")

def plot_vel_tracking_result( ax, score, trackLL, beg_loc, end_loc, draw_bars_func, colorL ):

    # trackLL = [ beg_loc,end_loc,perfL,trackL ]
    # perfL: [ {pitch:<>,vel:<>,microsec:<> ]
    # trackL = [ (pitch_index,perf_index) ]


    def _get_score_xy( beg_loc, end_loc, score):
        xL = []
        yL = []
        yMapL = []
        score_trackD = {}
        for pitch_idx,p in enumerate(score.pitchL):
            if beg_loc <= p.loc_id and p.loc_id <= end_loc:

                loc = score.locL[ score.locMapD[p.loc_id] ]
                i = loc.pitch_list_idxL.index( p.uid )

                vel_offs = int((1.0 if i%2==0 else -1.0)  * math.ceil(i/2))
                
                xL.append(p.loc_id)
                yL.append(p.vel + 0.25*vel_offs);
                yMapL.append(p.map_vel + 0.25*vel_offs)

                if p.loc_id not in score_trackD:
                    score_trackD[ p.loc_id ] = dict(chord_cnt=len(loc.pitch_list_idxL), match_cnt=0, vel=p.vel)
                

        max_vel =  np.max(yL)
        yV = np.array( yL )
        yV = yV/max_vel

        yMapV = np.array(yMapL)/max(yMapL)

        return np.array(xL),yV,yMapV,score_trackD,max_vel

    def _get_perf_xy( score, perfL, trackL, score_trackD ):

        def _calc_loc( beg_loc, end_loc, score, trackL, i ):
            # if the pitch_idx at trackL[i] is None then calculate
            # the location of the spurious note as midway between the
            # two known locations on either side of the unknown location
            loc0 = beg_loc
            loc1 = end_loc
            for pitch_idx,_ in trackL[i:]:
                if pitch_idx is not None:
                    loc1 = score.pitchL[pitch_idx].loc_id
                    break

            for i in range(i,-1,-1):
                pitch_index,_ = trackL[i]
                if pitch_index is not None:
                    loc0 = score.pitchL[pitch_idx].loc_id
                    break

            return loc0 + (loc1-loc0)/2.0
                
        def _split_and_scale( xyL, max_vel ):
            if len(xyL) == 0:
                return [],[]
            
            xL,yL = zip(*xyL)

            return np.array(xL), np.array(yL)/max_vel

        perfXYL     = []
        spuriousXYL = []
        max_vel     = 0
        pitchVelL   = []

        for i,(pitch_idx, perf_idx) in enumerate(trackL):

            # if this is a missed score event then skip it
            if perf_idx is None:
                continue

            perf_vel = perfL[ perf_idx ]['vel']
            perf_pitch = perfL[ perf_idx ]['pitch']
            max_vel = max(max_vel,perf_vel)

            # if this is a spurious note
            if pitch_idx is None:
                loc_id = _calc_loc(beg_loc,end_loc,score,trackL,i)
                spuriousXYL.append( (loc_id, perf_vel) )
            else:
                loc_id = score.pitchL[ pitch_idx ].loc_id
                score_trackD[ loc_id ]['match_cnt'] += 1

            if pitch_idx is not None:
                perfXYL.append( (loc_id, perf_vel) )
            pitchVelL.append( (perf_pitch,perf_vel) )

        print(spuriousXYL)
        sX,sY = _split_and_scale(spuriousXYL,max_vel)
        pX,pY = _split_and_scale(perfXYL,max_vel)
        
        return pX,pY,sX,sY,pitchVelL

    def _find_missed_notes( score_trackD, n, max_score_vel ):

        xL = []
        yL = []
        for loc_id,d in score_trackD.items():            
            if d['match_cnt'] / n == 0 : #< d['chord_cnt']:
                xL.append(loc_id)
                yL.append(d['vel']/max_score_vel)

        return xL,yL

    def _update_avg_xy_dict( avgPerfXyD, perfX, perfY ):

        for x,y in zip(perfX,perfY):
            if x not in avgPerfXyD:
                avgPerfXyD[x]=[]

            avgPerfXyD[x].append(y)

    def _fit_velocity( sc_loc_idL, sc_velL, perf_loc_idL, perf_velL ):

        aL = []
        bL = []
        fit_perf_loc_idL = []
        for p_loc_id,p_vel in zip(perf_loc_idL,perf_velL):
            bL.append( sc_velL[ sc_loc_idL.tolist().index(p_loc_id) ] )
            aL.append( p_vel )
            fit_perf_loc_idL.append(p_loc_id)

        aV,bV = np.array(aL),np.array(bL)

        # Perform linear curve fit: fit b = m*a + c
        coeffs = np.polyfit(aV, bV, deg=1)
        m, c = coeffs

        # Generate fitted values
        fit_perf_velV = m * aV + c

        mse = (np.square(fit_perf_velV - bV)).mean()


        return fit_perf_loc_idL, fit_perf_velV.tolist(),mse

    def _delta_velocity( sc_loc_idL, sc_velL, perf_loc_idL, perf_velL ):

        dL = []
        for p_loc_id,p_vel in zip(perf_loc_idL,perf_velL):
            sc_vel = sc_velL[ sc_loc_idL.tolist().index(p_loc_id) ]
            dL.append( (sc_vel - p_vel) * (sc_vel - p_vel) )

        return np.sqrt( sum(dL) )
        
    scoreX,scoreY,scoreMapY,score_trackD,max_score_vel = _get_score_xy( beg_loc, end_loc, score)

    avgPerfXyD = {}  # { <loc_id>:[] }

    draw_bars_func( ax, 1.0 )

    # plot score dynamics 
    ax.plot(scoreX,scoreY,'o',label="Score Dynamic")

    # plot score-piano velocities
    ax.plot(scoreX,scoreMapY,'o',color="grey",label="Score Velocity")

    # for each performance
    for i,(_,_,perfL,trackL) in enumerate(trackLL):    
        perfX,perfY,spuriousX,spuriousY,pitchVelL = _get_perf_xy( score, perfL, trackL, score_trackD )

        fit_perf_loc_idL,fit_perf_velL,p_mse = _fit_velocity( scoreX, scoreMapY, perfX, perfY )
        #fit_perf_dyn_loc_idL,fit_perf_dynL,d_mse = _fit_velocity( scoreX, scoreY,    perfX, perfY )

        dVel    = _delta_velocity( scoreX, scoreMapY, perfX, perfY )
        dFitVel = _delta_velocity( scoreX, scoreMapY, fit_perf_loc_idL, fit_perf_velL )
                                   
        #print("Perf MSE: ",p_mse,"Dyn MSE: ",d_mse)
        
        label = "Perf. "
        if len(trackLL) > 1:
            label = f"Perf. {i+1}"

        # plot performed velocities of spurious notes
        ax.plot(spuriousX, spuriousY,'x',color=colorL[i % len(colorL)],label= "Spurious" if i==0 else None)
            

        # plot performed velocities
        ax.plot(perfX,perfY,color=colorL[i % len(colorL)],label=label)

        # plot fit velocities
        if len(trackLL) == 1:
            ax.plot(perfX,fit_perf_velL,':.',color=colorL[i % len(colorL)],label= label + "Fit to Vel.")
            #ax.plot(perfX,fit_perf_dynL,'-.',color=colorL[i % len(clorL)],label= label + "Fit to Dyn.")


        # show pitch and vel for each performed note
        #for i,(pitch,vel) in enumerate(pitchVelL):
        #    ax.text( perfX[i], perfY[i], f"{i}:{pitch}:{vel}")            

        # track the avg
        _update_avg_xy_dict(avgPerfXyD, perfX, perfY)


    # show the average of multiple performances
    if len(trackLL) > 1:
        avgX = [ x for x,_ in avgPerfXyD.items() ]
        avgY = [ yL[0] if len(yL)==1 else np.median(yL) for _,yL in avgPerfXyD.items() ]
        avgXY = sorted( zip(avgX,avgY), key=lambda x: x[0] )
        avgX,avgY = zip(*avgXY)
        ax.plot(avgX,avgY,':.',color="black",label="median")

    # mark missed notes
    xL,yL = _find_missed_notes( score_trackD, len(trackLL), max_score_vel )
    ax.plot(xL,yL,'X',color="red",label="Missed")

    
    if len(trackLL) > 1:
        ax.set_title(f"Velocity Fit.")
        ax.legend()
        
    if len(trackLL) == 1:
        ax.set_title(f"Velocity Analysis: 'vel:{dVel:5.2f}' 'fit vel:{dFitVel:5.2f}'")
        ax.legend(bbox_to_anchor=(0.55,0.99),loc='upper left',borderaxespad=0)
        #ax.legend(loc='upper right')
        
    ax.set_ylabel("Velocity")
            
def plot_tracking_result(score,trackLL):

    def _get_beg_end_loc( trackLL):
        beg_loc = None
        end_loc = None
        for beg_loc0,end_loc0,_,_ in trackLL:
            if beg_loc is None or beg_loc0 < beg_loc:
                beg_loc = beg_loc0
            if end_loc is None or end_loc0 > end_loc:
                end_loc = end_loc0

        return beg_loc,end_loc

    def _gen_bar_lines( score, beg_loc, end_loc ):

        locL = []
        labelL = []
        meas0 = None
        for meas_num,loc_id in score.barL:
            if beg_loc<=loc_id and loc_id<=end_loc:
                locL.append(loc_id)
                labelL.append(str(meas_num))
                if meas0 is None:
                    meas0 = meas_num

        if score.locL[ score.locMapD[beg_loc] ].meas < meas0:
            locL = [ beg_loc ] + locL
            labelL = [ str(score.locL[ score.locMapD[beg_loc] ].meas) ] + labelL

        locL.append(end_loc+1)
        labelL.append(  str(score.locL[ score.locMapD[end_loc] ].meas+1) )
        
        return locL,labelL

    class BarLinesDrawer:
        def __init__( self, locL, labelL ):
            self.locL   = locL
            self.labelL = labelL
            
        def __call__( self, ax, max_y ):
            # draw bar lines
            ax.vlines(self.locL,ymin=0,ymax=max_y,color="black")
            for x,label in zip(self.locL,self.labelL):        
                ax.text(x,max_y,label )
        
    
    beg_loc,end_loc   = _get_beg_end_loc(trackLL)
    barLocL,barLabelL = _gen_bar_lines( score, beg_loc, end_loc )

    draw_bars_func = BarLinesDrawer(barLocL,barLabelL)

    _,axL = plt.subplots(2,1)

    #axL = [ axL]
        
    colorL = [ 'brown','darkorange','orangered','darksalmon']
    
    
    plot_vel_tracking_result(  axL[0], score, trackLL, beg_loc, end_loc, draw_bars_func, colorL )
    
    plot_time_tracking_result( axL[1], score, trackLL, beg_loc, end_loc, draw_bars_func, colorL )
    axL[1].set_xlabel("Score Location")
    
    plt.show()

def beck_taka():    
    if False:
        for meas_num,loc_id in score.barL:
            if beg_loc<=loc_id and loc_id<=end_loc:
                ax.vlines([loc_id],ymin=0,ymax=1,color="black")
                ax.text(loc_id,1.0,f"{meas_num}")
    

    beg_loc = 4232
    end_loc = 4707
    exp_perf_noteN = 600  # min count of performed notes required for a valid performance
    spurious_thresh = 100  # max. spurious note count for a valid performance
    folderL = ["beck1","beck2","taka1","taka2"]
    #folderL = ["nonken1","nonken2"]
    dirName = "/home/kevin/src/currawong/audio/workshop/"
    perf_fileL = []
    
    for folder in folderL:
        record_folderL = sorted(os.listdir(os.path.join(dirName,folder)),key=lambda x: int(x.split('_')[1]))
        for record_folder in record_folderL:
            
            perf_csv_fname = os.path.join(dirName,folder,record_folder,"midi.csv")

            perf_fileL.append((beg_loc,end_loc,exp_perf_noteN,spurious_thresh,perf_csv_fname))

    return perf_fileL



def _form_perf_file_list( base_dir, takeL, midi_csv_fname="midi.csv" ):
    perf_fileL = []
    for sectionNum,(min_take,max_take,exp_perf_noteN,spurious_thresh,(beg_loc,end_loc)) in enumerate(takeL):

        for takeNum in range(min_take,max_take+1):
            perf_csv_fname = os.path.join(base_dir,f"record_{takeNum}",midi_csv_fname)

            perf_fileL.append( (beg_loc,end_loc,exp_perf_noteN,spurious_thresh,perf_csv_fname,takeNum,sectionNum+1) )

    return perf_fileL
    
def shiau_uen_0():
    base_dir = os.path.expanduser("~/src/currawong/audio/shiau_uen")
    #takeL = [(1,5,(323,397)),(6,7,(2547,2687)),(8,11,(5361,5686)),(12,13,(8291,8553)),(14,17,(11456,11584)),(18,23,(13565,13728)) ]
    #takeL = [(2,5,(120,146)),(6,7,(888,929)),  (8,11,(2287,2454)),(12,13,(3765,3883)),(14,17,(5407,5491)),(18,23,(6608,6677)) ]
    takeL =  [(2 , 5,  50,  5, (120,146)),
              (6,  7,  50,  5, (888,929)),
              (8, 11, 200, 30, (2287,2454)),
              (12,13, 150, 10, (3765,3883)),
              (14,17,  80,  5, (5407,5491)),
              (18,23, 100, 15, (6608,6677))]

    return _form_perf_file_list(base_dir,takeL,"fix_midi.csv")

def shiau_uen_1():
    base_dir = os.path.expanduser("~/temp/ding2")
    takeL =  [(14,18,  50,  5, (120,  167)),
              (19,23,  50,  5, (888,  929)),
              ( 0, 7, 200, 30, (2287,2454)),
              ( 8,13, 150, 10, (3765,3883)),
              (24,31,  80,  5, (5407,5491)),
              (32,42, 100, 15, (6608,6677))]

    #takeL = [ (30,31,  80,  5, (5407,5491)) ]
    return _form_perf_file_list(base_dir,takeL,"midi_am_sf.csv")


def arseniy():
    base_dir = os.path.expanduser("~/temp/currawong/arseniy1")
    takeL = [
        ( 0,6,  50, 10, (481,540)),
        ( 7,16, 40, 10, (776,807)),
        (17,26,150, 30, (2455,2608)),
        (27,35,150, 30, (3967,4124)),
        (36,46, 70, 20, (6106,6167)),
        (47,51,250, 50, (7702,7825))
    ]

    takeL = [ (5,6,50,10,(481,540)) ]

    return _form_perf_file_list(base_dir,takeL,"midi_am_sf.csv")

def nicholas():
    base_dir = os.path.expanduser("~/temp/currawong/nicolas1")
    takeL = [
        (3,3, 175, 40, (7276, 7426)),
        (9,9, 175, 40, (7276, 7426)),
        (12,12, 175, 40, (7276, 7426)),
        (16,16, 175, 40, (7276, 7426))
             ]

    takeL = [
        (3,3, 175, 40, (7276, 7331)),
        (9,9, 175, 40, (7276, 7331)),
        (12,12, 175, 40, (7276, 7331)),
        #(16,16, 175, 40, (7276, 7331))
             ]
    
    return _form_perf_file_list(base_dir,takeL,"midi_am_sf.csv")

def han1():
    base_dir = os.path.expanduser("~/temp/currawong/han1")
    
    # min_take,max_take,exp_perf_noteN,spurious_thresh,(beg_loc,end_loc)
    
    takeL = [
        #( 0,9,   50, 10, (7427,7571)),
        #(10,23,  40, 10, (4232,4332)),
        (20,23,  40, 10, (4232,4332)),
        #(24,39, 150, 30, (6168,6226)),
    ]

    return _form_perf_file_list(base_dir,takeL,"midi_am_sf.csv")


def track_all(args, perf_fileL):
    
    rpt_fl  = False
    tot_missedN = 0
    tot_spuriousN = 0
    tot_passN = 0
    tot_failN = 0
    resultLL = []

    #perf_fileL = nicholas() #han1() #nicholas() #shiau_uen_1() # #nicholas() #arseniy() #beck_taka() + shiau_uen_0()

    score = Score(args.score_csv_fname,args.vel_tbl)

    for beg_loc,end_loc, exp_perf_note_N, spurious_thresh, perf_csv_fname, takeNumb, sectionNumb in perf_fileL:

        perfL = parse_perf_csv( perf_csv_fname, args.srate )

        #report_perf( perfL, N=None )

        sf = ScoreFollower(args,score)

        scoreNoteN, perfNoteN, matchedN, missedN, spuriousN, dVel, dSec, even_meas, tempo_meas, resultL = run_tracker( sf, perfL, score, beg_loc, end_loc, args )

        resultLL.append((beg_loc,end_loc,perfL,resultL))

        acc = 100.0*matchedN/perfNoteN
        
        print(f"{sectionNumb:2} Take:{takeNumb:2} Notes: score:{scoreNoteN} perf:{perfNoteN:4} Match: {matchedN:4} Missed:{missedN:4} Spurious:{spuriousN:4} acc:{acc:3.1f} dVel:{dVel:5.2f} dSec:{dSec:7.5f} even:{even_meas} tempo:{tempo_meas} {perf_csv_fname}",end="")

        # a valid perf. must have at least `exp_perf_note_N` notes and less than `spurious_thresh` spurious notes 
        if perfNoteN > exp_perf_note_N and spuriousN < spurious_thresh:

            tot_passN += 1
            tot_missedN += missedN
            tot_spuriousN += spuriousN
            print(" ok")
        else:
            tot_failN += 1
            print(" fail")
            

    dbz = lambda x,y : "   " if y==0 else f"{x/y:3.1f}"
    print(f"Total:{tot_missedN+tot_spuriousN:3}  missed:{tot_missedN:3} ({dbz(tot_missedN,tot_passN)}) spurious:{tot_spuriousN:3} ({dbz(tot_spuriousN,tot_passN)}) Pass:{tot_passN:3} Fail:{tot_failN:3}")

    #plot_tracking_result(score,resultLL)

def track_one( args, perf_csv_fname, beg_perf_idx, beg_loc, end_loc, timeline_fname_json="timeline/timeline.json" ):
    
    score = Score(args.score_csv_fname,args.vel_tbl)
    
    perfL = parse_perf_csv( perf_csv_fname, args.srate )

    perfL = perfL[beg_perf_idx:]

    sf = ScoreFollower(args,score)
    
    scoreNoteN, perfNoteN, matchedN, missedN, spuriousN, dVel, dSec, even_meas, tempo_meas, trackL = run_tracker( sf, perfL, score, beg_loc, end_loc, args )

    acc = 100.0*matchedN/perfNoteN
        
    print(f"Notes: score:{scoreNoteN} perf:{perfNoteN:4} Match: {matchedN:4} Missed:{missedN:4} Spurious:{spuriousN:4} acc:{acc:3.1f} dVel:{dVel:5.2f} dSec:{dSec:7.5f} even:{even_meas} tempo:{tempo_meas} {perf_csv_fname}")

    gen_timeline_json_input( sf, perfL, trackL, timeline_fname_json )

    return gen_sf_track_result( sf, perfL, trackL)

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    #score_csv_fname = "score_20240504.csv",
    vel_tbl = [1,3,5,7,8,9,12,15,19,21,25,29,31,35,39,43,47,51,55,59,61,67,73,77,80]
    
    argsD = dict(
        srate = 48000.0,
        smp_per_cycle = 64,
        limit_perf_N = None,
        rpt_fl = False,
        score_csv_fname = "score_20250619.csv",

        pre_affinity_sec     = 1.0,
        post_affinity_sec    = 3.0,
        min_affinity_loc_cnt = 2,     # min number of locations in the affinity pre/post window
        
        pre_wnd_sec       = 2.0,
        post_wnd_sec      = 5.0,
        min_wnd_loc_cnt   = 2,     # min number of locations in the search pre/post window
        
        decay_coeff       = 0.99,

        d_sec_err_thresh_lo = 0.4,  # reject if d_loc > d_loc_thresh_lod and d_time > d_time_thresh_lo
        d_loc_thresh_lo     = 3,    
        d_sec_err_thresh_hi = 1.5,  # reject if d_loc != 0 and d_time > d_time_thresh_hi
        d_loc_thresh_hi     = 4,    # reject if d_loc > d_loc_thresh_hi
        d_loc_stats_thresh  = 3,

        vel_tbl = vel_tbl

    )

    args = types.SimpleNamespace(**argsD)

    #
    # Results for: beck_taka()
    #
    # 4290 fail:6

    # 2280 fail:9
    #args.decay_coeff = 0.999

    # 3568 fail:6
    args.decay_coeff = 0.995

    # 2345 fail:9
    # args.decay_coeff = 0.999
    # args.post_affinity_sec = 5.0

    # 2153 fail:11
    #args.decay_coeff = 0.999
    #args.post_affinity_sec = 5.0
    #args.d_loc_thresh_hi     = 5    

    # 1744 fail:31
    #args.decay_coeff = 0.995
    #args.post_wnd_sec = 4    

    # 2450 fail:20
    #args.decay_coeff = 0.995
    #args.post_wnd_sec = 6.0
    #args.pct_err_thresh_hi = 2.0

    # 4849
    # args.pre_affinity_sec = 0.5
    # args.pre_wnd_sec = 1.5

    if False:
        score_csv_fname = "score_20250619.csv"
        parser_func  = parse_perf_csv

        if False:
            score = Score(score_csv_fname)
            score.report()

        if False:
            beg_loc = 481
            end_loc = 540
            args.rpt_fl = True
            perf_csv_fname = "/home/kevin/temp/arseniy_1/record_5/midi_am_sf.csv"

        if False:
            beg_loc = 3967
            end_loc = 4124
            args.rpt_fl = True
            perf_csv_fname = "/home/kevin/temp/arseniy_1/record_34/midi_am_sf.csv"
            
        if False:
            beg_loc = 4232
            end_loc = 4707
            args.rpt_fl = True

            perf_csv_fname = "/home/kevin/src/currawong/audio/workshop/taka1/record_6/midi.csv"

        if False:
            beg_loc = 4232
            end_loc = 4707

            d_sec_err_thresh_lo = 1.0,  # reject if d_loc > d_loc_thresh_lod and d_time > d_time_thresh_lo
            d_sec_err_thresh_hi = 2.5,  # reject if d_loc != 0 and d_time > d_time_thresh_hi
            
            args.rpt_fl = True
            perf_csv_fname = "/home/kevin/src/currawong/audio/workshop/nonken2/record_8/midi.csv"
            
        if False:
            beg_loc = 120
            end_loc = 146
            perf_csv_fname = "/home/kevin/src/currawong/audio/shiau_uen/record_5/midi.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 888
            end_loc = 929
            perf_csv_fname = "/home/kevin/src/currawong/audio/shiau_uen/record_7/midi.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 2287
            end_loc = 2454
            perf_csv_fname = "/home/kevin/src/currawong/audio/shiau_uen/record_11/midi.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 3765
            end_loc = 3883 
            perf_csv_fname = "/home/kevin/src/currawong/audio/shiau_uen/record_13/midi.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 5407
            end_loc = 5491
            perf_csv_fname = "/home/kevin/src/currawong/audio/shiau_uen/record_16/midi.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 6608
            end_loc = 6677
            perf_csv_fname = "/home/kevin/src/currawong/audio/shiau_uen/record_22/midi.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 120
            end_loc = 167
            perf_csv_fname = "/home/kevin/temp/ding2/record_42/midi_am_sf.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 7276 
            end_loc = 7426
            perf_csv_fname = "/home/kevin/temp/nicholas_1/record_3/midi_am_sf.csv"
            args.rpt_fl = True

        if False:
            beg_loc = 1526 
            end_loc = 1683
            score_csv_fname = "/home/kevin/src/currawong/projects/create_cult_event_score/score_cult_evt_20250929_5_a.csv"   
            perf_csv_fname = "/home/kevin/src/currawong/projects/cult_video/out/record_48/gutim_17-align.csv"
            args.rpt_fl = True
            parser_func  = parse_perf_csv_2


        if True:
            beg_loc = 7276
            end_loc = 7426
            score_csv_fname = "score_20240504.csv"
            perf_csv_fname = "/home/kevin/temp/currawong/nicholas_1/record_3/midi_am_sf.csv"
            args.rpt_fl = True
            
        score = Score(score_csv_fname,vel_tbl)
        score.report(beg_loc,end_loc)
        perfL = parser_func( perf_csv_fname, args.srate )
        
        sf = ScoreFollower(args,score)
        
        run_tracker( sf, perfL, score, beg_loc, end_loc, args )

    if True:

        args.d_loc_thresh_hi = 7
        args.decay_coeff = 0.995
        track_all(args)
    

#                         d_loc_id>x && d_sec_thresh_hi 
#       5           .99        0               Total:3785  missed:1815 (31.8) spurious:1970 (34.6) Pass: 57 Fail: 13
#       6           .99        0               Total:3777  missed:1811 (31.8) spurious:1966 (34.5) Pass: 57 Fail: 13
#       7           .99        0               Total:3777  missed:1811 (31.8) spurious:1966 (34.5) Pass: 57 Fail: 13
#       7           .995       0               Total:3771  missed:1808 (31.7) spurious:1963 (34.4) Pass: 57 Fail: 13
#       7           .995       3               Total:3777  missed:1813 (33.0) spurious:1964 (35.7) Pass: 55 Fail: 15
    
