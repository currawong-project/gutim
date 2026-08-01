from gen_way_points import (parse_score_csv,find_unique_pitch_sequences)
from sf_perf import parse_perf_csv

class Matcher:
    # pairL = [ (loc,midi_pitch) ]
    def __init__( self, pairL ):
        self.pairL = sorted(pairL)
        self.pitchL = [ pitch for _,pitch in pairL]
        self.matchL = []
        self.reset()

    def min_loc( self ):
        return self.pairL[0][0]

    def max_loc(self):
        return self.pairL[-1][0]
    

    def reset( self ):
        self.matchL = []

    def is_in_range( self, loc ):
        return self.min_loc() <= loc and loc <= self.max_loc()

    def is_matched( self ):
        return len(self.matchL) == len(self.pairL)

    def on_new_note( self, midi_pitch ):
        matched_fl = False
        if not self.is_matched():
            idx = next((i for i,d1 in enumerate(self.pitchL)),None)
            if idx is None:
                self.matchL = []
            else:
                self.matchL.append(idx)

            matched_fl = self.is_matched()

        return matched_fl
    

class SegWayPointFollower:
    
    def __init__( self,  seg_id, way_pointL ):
        self.seg_id     = seg_id
        self.min_wp_idx = 0  # first possible WP
        self.wpL = sorted([ Matcher( pairL ) for pairL in way_pointL ], key=lambda x:x.min_loc() )        
        self.reset()
        

    def reset( self ):
        for wp in self.wpL:
            wp.reset()

    def locate( self, min_loc ):
        for i,wp in enumerate(self.wpL):
            if wp.min_loc() >= min_loc:
                self.min_wp_idx = i
                break
        
    def on_new_note( self, midi_pitch ):

        match_loc = None
        for i,wp in enumerate(self.wpL[self.min_wp_idx:]):
            if wp.on_new_note(midi_pitch):
                match_loc = wp.max_loc()
                self.min_wp_idx = self.min_wp_idx + i
                break

        return match_loc


    def match_pct( self ):
        return 100* sum((1 for wp in self.wpL if wp.is_matched()))/len(self.wpL)





def track_one( score_csv_fname, perf_csv_fname, beg_loc, end_loc ):
    max_wnd_cnt = 4
    
    # parse score
    scoreL = parse_score_csv(score_csv_fname)

    # given the beg/end loc's get way points
    way_pointL = find_unique_pitch_sequences(max_wnd_cnt, scoreL, beg_loc, end_loc )
    
    # parse the performance file
    perfL = parse_perf_csv( perf_csv_fname )


    #
    seg_id = 0
    sf = SegWayPointFollower(seg_id,way_pointL)

    for pr in perfL:
        match_loc = sf.on_new_note(pr['pitch'])

        # if match_loc is not None:
        #    print(match_loc)
        
    print(f"WP {sf.match_pct():5.2f} %")
