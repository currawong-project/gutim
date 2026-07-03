import os
import csv
import json
import yaml
import types
import logging
import sf_study_7 as sf7
from timeline import gen_svg_timeline as tl

def _loc_to_section( args, beg_loc, end_loc ):

    def _form_loc_section_map( args ):
        loc_sectionD = {}
        with open(args.score_csv_fname) as f:
            rdr = csv.DictReader(f)

            section = None
            for r in rdr:
                if r['section']:
                    section = r['section']
                    
                if r['oloc']:
                    loc_sectionD[ int(r['oloc']) ] = section
            
        return loc_sectionD


    loc_sectionD = _form_loc_section_map(args)
        
    # print(beg_loc,end_loc,loc_sectionD[beg_loc],loc_sectionD[end_loc])


def _form_perf_file_list( base_dir, takeD, midi_csv_fname, legacy_score_fmt_fl ):

    def _begin_perf_index( takeNum, editD):
        return editD[takeNum]['value'] if  takeNum in editD and editD[takeNum]['op'] == 'beg_perf_idx' else 0

    def _skip_flag( takeNum, editD):
        return editD[takeNum]['value'] if takeNum in editD and editD[takeNum]['op'] == 'skip' else False
    
    perf_fileL = []
    for sectionNum,d in enumerate(takeD['takeL']):

        min_take        = d['min_take'] if 'min_take' in d else None
        max_take        = d['max_take'] if 'max_take' in d else None
        exp_perf_noteN  = d['exp_perf_noteN']
        spurious_thresh = d['spurious_threshN']
        beg_loc         = d['beg_loc']
        end_loc         = d['end_loc' ]

        if min_take is not None and max_take is not None:
            takeL = [ i for i in range(min_take,max_take+1) ]
        else:
            takeL = d['takeL']
                
        for takeNum in takeL:

            beg_perf_idx = _begin_perf_index(takeNum,takeD['editD'])
            skip_fl      = _skip_flag(takeNum,takeD['editD'])

            if not skip_fl:
                perf_csv_fname = os.path.expanduser(os.path.join(base_dir,f"record_{takeNum}",midi_csv_fname))

                perf_fileL.append( (beg_perf_idx, beg_loc,end_loc,exp_perf_noteN,spurious_thresh,perf_csv_fname,takeNum,sectionNum+1) )

    return perf_fileL

def run_tracker( args, perf_fileL, player, sf_track_out_dir, timeline_out_dir, take_numb_arg ):

    loc0 = None

    trackL = []
    plotD = {}
    for beg_perf_idx, beg_loc,end_loc, exp_perf_note_N, spurious_thresh, perf_csv_fname, take_numb, section_numb in perf_fileL:
        if take_numb_arg is None or take_numb == take_numb_arg:

            if loc0 is None or loc0 != beg_loc:

                timeline_json_dir = os.path.join(timeline_out_dir,player,str(beg_loc),"json")
                timeline_svg_dir = os.path.join(timeline_out_dir,player,str(beg_loc),"svg")

                os.makedirs(timeline_json_dir,exist_ok=True)
                os.makedirs(timeline_svg_dir,exist_ok=True)
                
                plotD[beg_loc] = dict( end_loc=end_loc, svg_dir=timeline_svg_dir, svgD={} )

                _loc_to_section( args, beg_loc, end_loc )

                
            loc0 = beg_loc

            tl_fname_json = os.path.join(timeline_json_dir,f"timeline_{take_numb}.json")

            # trackedPerfL=[ { sec, loc, pitch, vel }  ]
            trackedPerfL = sf7.track_one(args, perf_csv_fname, beg_perf_idx, beg_loc, end_loc, tl_fname_json )

            plotD[beg_loc]['svgD'][f"{player}-{take_numb}"] = tl_fname_json

            trackL.append( dict(player=player, take_numb=take_numb, beg_loc=beg_loc, end_loc=end_loc, tracked_perfL=trackedPerfL) )


    for beg_loc,d in plotD.items():        
        tl.gen_file(d['svg_dir'], d['svgD'], beg_loc=beg_loc, end_loc=d['end_loc'], scale=500.0)


    os.makedirs(sf_track_out_dir,exist_ok=True);
    track_fname_yaml = os.path.join( sf_track_out_dir, f"{player}.yaml" )
    
    with open(track_fname_yaml,"w", encoding="utf-8") as f:
        f.write(yaml.dump(trackL, default_flow_style=False, allow_unicode=True))
                        
    

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    
    #score_csv_fname = "score_20240504.csv"
    score_csv_fname = "../gutim_1/output/legacy_sf_score.csv"
    src_data_dir = "~/src/currawong/projects/gutim/perf_data"

    vel_tbl = [1,3,5,7,8,9,12,15,19,21,25,29,31,35,39,43,47,51,55,59,61,67,73,77,80]
    
    argsD = dict(
        srate           = 48000.0,
        smp_per_cycle   = 64,
        limit_perf_N    = None,
        rpt_fl          = False,
        legacy_score_fmt_fl = False,
        score_csv_fname = score_csv_fname, # "score_20250619.csv",

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

        vel_tbl = vel_tbl,

        meas_perf_fl = False

    )

    
    perfD = {
        'shiau_uen1': {
            'data_dir':os.path.join(src_data_dir,"shiau_uen_1"),
            'midi_fname':'midi_am_sf.csv',
            'editD':{},
            'takeL':[
                dict(min_take=2 , max_take=5, beg_loc=120, end_loc=168,   exp_perf_noteN=50,  spurious_threshN=5),
                dict(min_take=6,  max_take=7, beg_loc=895, end_loc=935,  exp_perf_noteN=50,  spurious_threshN=5),
                dict(min_take=8, max_take=11, beg_loc=2296,end_loc=2463, exp_perf_noteN=200, spurious_threshN=30),
                dict(min_take=12,max_take=13, beg_loc=3786,end_loc=3905, exp_perf_noteN=150, spurious_threshN=10),
                dict(min_take=14,max_take=17, beg_loc=5440,end_loc=5526, exp_perf_noteN=80,  spurious_threshN=5),
                dict(min_take=18,max_take=23, beg_loc=6661,end_loc=6730, exp_perf_noteN=100, spurious_threshN=15)                
            ]
        },
        'shiau_uen2': {
            'data_dir':os.path.join(src_data_dir,"ding2"),
            'midi_fname':'midi_am_sf.csv',
            'editD':{},
            'takeL':[
                dict( min_take=14, max_take=18, beg_loc=120,  end_loc=168,  exp_perf_noteN=50,  spurious_threshN=5),
                dict( min_take=19, max_take=23, beg_loc=895,  end_loc=935,  exp_perf_noteN=50,  spurious_threshN=5),
                dict( min_take=0,  max_take=7,  beg_loc=2296, end_loc=2463, exp_perf_noteN=200, spurious_threshN=30),
                dict( min_take=8,  max_take=13, beg_loc=3786, end_loc=3905, exp_perf_noteN=150, spurious_threshN=10),
                dict( min_take=24, max_take=31, beg_loc=5440, end_loc=5526, exp_perf_noteN=80,  spurious_threshN=5),
                dict( min_take=32, max_take=42, beg_loc=6661, end_loc=6730, exp_perf_noteN=100, spurious_threshN=15)
            ]
        },
        
        'arseniy1': {
            'data_dir':os.path.join(src_data_dir,"arseniy1"),
            'midi_fname':"midi_am_sf.csv",
            'editD':{},
            'takeL':[
                dict( min_take=0,  max_take=6,  beg_loc=485,  end_loc=547,  exp_perf_noteN=50,  spurious_threshN=10 ),
                dict( min_take=7,  max_take=16, beg_loc=784,  end_loc=814,  exp_perf_noteN=40,  spurious_threshN=10 ),
                dict( min_take=17, max_take=26, beg_loc=2464, end_loc=2622, exp_perf_noteN=150, spurious_threshN=30 ),
                dict( min_take=27, max_take=35, beg_loc=3989, end_loc=4146, exp_perf_noteN=150, spurious_threshN=30 ),
                dict( min_take=36, max_take=46, beg_loc=6151, end_loc=6217,  exp_perf_noteN=70,  spurious_threshN=20 ),
                dict( min_take=47, max_take=51, beg_loc=7785, end_loc=7907,  exp_perf_noteN=250, spurious_threshN=50 ),
            ]
        },
        'han1': {
            'data_dir':os.path.join(src_data_dir,"han1"),
            'midi_fname':"midi_am_sf.csv",
            'editD':{},
            'takeL':[
                dict(min_take=0, max_take=9,  beg_loc=7506, end_loc=7651, exp_perf_noteN=50,  spurious_threshN=10),
                dict(min_take=10,max_take=23, beg_loc=4252, end_loc=4357, exp_perf_noteN=40,  spurious_threshN=10),
                dict(min_take=20,max_take=23, beg_loc=4252, end_loc=4357, exp_perf_noteN=40,  spurious_threshN=10),
                dict(min_take=24,max_take=39, beg_loc=6218, end_loc=6276, exp_perf_noteN=150, spurious_threshN=30),
            ]
        },
        'nicolas1': {
            'data_dir':os.path.join(src_data_dir,"nicolas1"),
            'midi_fname':'midi_am_sf.csv',
            'editD':{},
            'takeL':[
                # beg_loc=7276, end_loc=7426
                dict(takeL=[3,9,12,16], beg_loc=7354, end_loc=7505, exp_perf_noteN=175, spurious_threshN=40),
            ]
        },
        'nicolas2': {
            'data_dir':os.path.join(src_data_dir,"nicolas2"),
            'midi_fname':'midi_am_sf.csv',
            'editD':{ 29:dict(op='skip',value=True) },
            'takeL':[
                dict(min_take=1,  max_take=12, beg_loc=25,   end_loc=64,   exp_perf_noteN=40,  spurious_threshN=15),
                dict(min_take=13, max_take=18, beg_loc=1217, end_loc=1261, exp_perf_noteN=50,  spurious_threshN=10),
                dict(min_take=19, max_take=29, beg_loc=1868, end_loc=1955, exp_perf_noteN=50,  spurious_threshN=10),
                dict(min_take=36, max_take=43, beg_loc=3191, end_loc=3367, exp_perf_noteN=190, spurious_threshN=40),
                dict(min_take=30, max_take=35, beg_loc=4599, end_loc=4667, exp_perf_noteN=50,  spurious_threshN=15)
            ]
        },
        'han2':{
            'data_dir':os.path.join(src_data_dir,"han2"),
            'midi_fname':'midi_am_sf.csv',
            'editD':{ 2:dict(op='beg_perf_idx', value=8), 10:dict(op='skip', value=True), 19:dict(op='skip', value=True) },
            'takeL':[
                dict(min_take=0,  max_take=6, beg_loc=301,  end_loc=358,  exp_perf_noteN=50, spurious_threshN=10),
                dict(min_take=8, max_take=21, beg_loc=1180, end_loc=1217, exp_perf_noteN=30, spurious_threshN=10),
                dict(min_take=22,max_take=34, beg_loc=2200, end_loc=2295, exp_perf_noteN=50, spurious_threshN=10)
            ]
        }
    }
    

    sf_track_out_dir = "sf_track"
    timeline_out_dir = "tl"
    args = types.SimpleNamespace(**argsD)
    # player = 'arseniy1'
    take_numb = None

    os.makedirs(sf_track_out_dir,exist_ok=True)
    os.makedirs(sf_track_out_dir,exist_ok=True)


    playerL = ['arseniy1','han1', 'han2', 'nicolas1', 'nicolas2', 'shiau_uen1', 'shiau_uen2' ]
    playerL = ['nicolas1']
    for player in playerL:

        takeD = perfD[player]

        perf_fileL = _form_perf_file_list( takeD['data_dir'], takeD, takeD['midi_fname'], args.legacy_score_fmt_fl )
        
        run_tracker(args, perf_fileL, player, sf_track_out_dir, timeline_out_dir, take_numb )
    
