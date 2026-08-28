import json

def gen_meas_maps(scoreL ):

    def _get_missing_measures(measD):
        measL = sorted([(meas,meas_loc) for meas,meas_loc in measD.items()])

        min_meas_num = measL[0][0]
        max_meas_num = measL[-1][0]
        missingL = []
        for meas_num in range(min_meas_num,max_meas_num+1):
            if meas_num not in measD:
                missingL.append(meas_num)

        return measL,missingL
        

    # form a gutim-meas to score (meas,loc) dict.
    measD = {}
    for r in scoreL:
        if r.src is not None and len(r.src)>0 and r.src=='gutim' and r.src_meas is not None and r.src_meas not in measD:
            measD[r.src_meas] = (r.meas,r.oloc)

    while True:

        # check for missing measures - we want the complete range of measures
        # from begin to end to be represented
        measL,missingL = _get_missing_measures(measD)

        if len(missingL) == 0:
            break

        # any missing measures should point to the next measure
        for miss_meas in missingL:
            next_meas = miss_meas+1
            while next_meas not in measD:
                next_meas += 1
            measD[miss_meas] = measD[next_meas]

    # create a measure and loc map.
    locL =  [ loc  for _,(_,loc)  in measL ]
    measL = [ meas for _,(meas,_) in measL ]

    # map measure 0 to measure 1
    locL = [ locL[0] ] + locL
    measL = [ measL[0] ] + measL 

    return measL,locL


def write_meas_maps(measL,locL,out_meas_meas_json_fname,out_meas_loc_json_fname):

    with open(out_meas_meas_json_fname,"w") as f:
        json.dump({ 'list':measL },f,indent=2)
    
    with open(out_meas_loc_json_fname,"w") as f:
        json.dump({ 'list':locL },f,indent=2)
