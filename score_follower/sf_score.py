import csv

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
            
