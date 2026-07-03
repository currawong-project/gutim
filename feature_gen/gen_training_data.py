import os
import csv
import json
import types
import pickle
import pandas as pd

def none_to_zero( x ):
    return 0 if x is None or x == "" else x
            
def generate_training_data( args ):

    def _parse_preset_features_csv( fname ):
        # Return: name_idx_mapD[<preset-label>:<preset-label-index>,  featL[{ csv-row }], labelL[{ csv-row }]
        
        def _form_label_ref_dict( r ):
            labelD = {}
            for key,_ in r.items():
                if 'label_' in key:
                    name = key.split('_')[1]
                    labelD[key] = dict(index=len(labelD),name=name)
            return labelD

        def _fill_label_vect( labelRefD, r ):
            labelV = [0] * len(labelRefD)
            for field,d in labelRefD.items():
                labelV[ d['index'] ] = int(r[field])
            return labelV
        
        featRowMapD = {}
        labelRefMapD = None
        psSectMapD = {}
        nonFeatL = []
        with open(fname) as f:
            rdr = csv.DictReader(f)
            for r in rdr:

                # if the label name->index map has not yet been created
                if labelRefMapD is None:
                    labelRefMapD = _form_label_ref_dict(r)
                    nonFeatL = [ 'preset_span_id','section_label' ] + list(labelRefMapD.keys())

                # extract the label information from this line
                labelV = _fill_label_vect(labelRefMapD,r)

                sect_lbl = r['section_label']
                section_numb = int(sect_lbl) if sect_lbl[-1].isdigit() else int(sect_lbl[0:-1])
                featV = { k:float(none_to_zero(v)) for k,v in r.items() if k not in nonFeatL }
                
                psSectMapD[ r['preset_span_id'] ] = dict( section_label=sect_lbl, section_numb=section_numb, featV=featV, labelV=labelV )


        label_vect_mapD = { d['name']:d['index'] for _,d in labelRefMapD.items() }
        return label_vect_mapD, psSectMapD

    def _parse_score_features_csv( fname ):
        # Return { <section_number>:<feat_dict> } for each score section.
        
        with open(fname) as f:
            rdr = csv.DictReader(f)

            featD = {}
            sect_cntD = {}
            for r in rdr:

                sect_lbl = r['section_id']
                section_numb = int(sect_lbl) if sect_lbl[-1].isdigit() else int(sect_lbl[0:-1])

                # form the score feature dictionary or this row
                featV = { k:float(none_to_zero(v)) for k,v in r.items() if k not in ['section_id'] }

                # if this is a split section (has an 'a' or 'b' suffix on the section label
                # then the section number may already have a feature vector
                # in this case we add this feature to the previous one and prepare to
                # take the average of the two  
                if section_numb in featD:
                    featD[ section_numb ] = { k:v + featD[section_numb][k] for k,v in featV.items() }
                    sect_cntD[ section_numb ] += 1
                else:
                    featD[ section_numb ] = featV
                    sect_cntD[ section_numb ] = 1

        # some variable should be summed rather than averaged
        sum_labelL = ['section_dur_sec','note_count'] 
        
        # take the sum or average of split sections
        for sect_numb,featV in featD.items():
            featD[sect_numb] = { k:v/ (1 if k in sum_labelL else sect_cntD[sect_numb]) for k,v in featV.items() }
            
        return featD

    def _parse_perf_features_csv( fname ):
        #  return { <section_numb>:{ player:<>, take_numb:<>, featV:{} }}
        with open(fname) as f:
            
            rdr      = csv.DictReader(f)
            sectD    = {}
            nonFeatL = [ "section_label","player","take_numb" ]
            
            for r in rdr:

                section_numb = int(r['section_label'])
                if section_numb not in sectD:
                    sectD[ section_numb ] = []

                featV = { k:float(none_to_zero(v)) for k,v in r.items() if k not in nonFeatL }
                    
                sectD[section_numb].append( dict(player=r['player'],take_numb=r['take_numb'],featV=featV) )
                

        return sectD

    def _combine_features( ps_sect_mapD, score_sect_mapD, perf_sect_mapD ):

        # Return [ { ps_span_id:<>, featV:{} } }

        featL = []
        labelL = []
        tocL = []
        fixedD = {}  # { <ps_span_id>:<fixed_featD> }
        fixedColMapD = None

        
        # for each preset span
        for ps_span_id,psD in ps_sect_mapD.items():

            # preset span section number
            ps_section_numb = psD['section_numb']
            
            # section number of features used to determine this preset
            feat_section_numb = ps_section_numb - 1

            # if score and perf. features exist for this section
            if feat_section_numb in score_sect_mapD and feat_section_numb in perf_sect_mapD:
                
                score_featV = score_sect_mapD[ feat_section_numb ]  # score features
                ps_featV    = psD['featV']                          # preset features
                fixed_featV = score_featV | ps_featV

                assert ps_span_id not in fixedD
                fixedD[ ps_span_id ] = fixed_featV

                if fixedColMapD is None:
                    fixedColMapD = {}
                    for i,(k,_) in enumerate(fixed_featV.items()):
                        if k in score_featV:
                            src = 'score'
                        elif k in ps_featV:
                            src = 'preset'
                        else:
                            assert False

                        fixedColMapD[k] = dict(index=i,src=src)
                    print(fixedColMapD)
                        

                # for each performance of this section
                for perf_featD in perf_sect_mapD[ feat_section_numb ]:

                    # store the features, labels, and TOC entries
                    featL.append( dict(ps_span_id=ps_span_id, featV=fixed_featV | perf_featD['featV']  ) )
                    
                    labelL.append( psD['labelV'] )
                    
                    tocL.append(dict(ps_span_id=ps_span_id,
                                     ps_section_numb=ps_section_numb,
                                     player=perf_featD['player'],
                                     take_numb=perf_featD['take_numb'],
                                     feat_section_numb=feat_section_numb))
                
        return featL,labelL,tocL,fixedD,fixedColMapD

    def _form_data_frame( all_featL ):

        df = pd.DataFrame([ f['featV'] for f in all_featL])

        # calc. means and standard deviations of the columns
        col_means = df.mean()
        col_stds = df.std(ddof=1) # ddof=1 uses sample std, use ddof=0 for population std

        # calc zscores
        df = (df - col_means) / col_stds

        # store the col means and stds in zscoreD
        zscoreD = {}
        for col_idx,label in enumerate(list(df.columns)):            
            zscoreD[ label ] = dict(col_index=col_idx,mean=col_means[label], std=col_stds[label])

        return df.values, zscoreD

    def _write_fixed_feat_dict(fname,fixedD,fixedColMapD):
        with open(fname,"w") as f:
            json.dump(dict(colMapD=fixedColMapD,featD=fixedD),f,indent=2)
            
    
    label_vect_mapD, ps_sect_mapD = _parse_preset_features_csv(args.preset_feat_fname)
    score_sect_mapD               = _parse_score_features_csv(args.score_feat_fname)
    perf_sect_mapD                = _parse_perf_features_csv(args.perf_feat_fname)
    all_featL,labelL,tocL,fixedD,fixedColMapD  = _combine_features(ps_sect_mapD, score_sect_mapD, perf_sect_mapD )
    featM,zscoreD                 = _form_data_frame(all_featL)

    _write_fixed_feat_dict(args.fixed_feat_fname,fixedD,fixedColMapD)
    
    with open(args.train_data_fname,"wb") as f:
        pickle.dump( dict(featM=featM,                    # feature mtx
                          labelL=labelL,                  # one label vector per feat mtx row
                          label_colMapD=label_vect_mapD,  # map preset names to labelV column indexes
                          fixed_comMapD=fixedColMapD,     # map 'fixed' feature names to columns and sources
                          zscoreD=zscoreD),f)             # zscore means and std's

        
            
    
if __name__ == "__main__":
    out_dir               = "output"
    train_data_fname      = "training_0.pkl"
    score_feat_csv_fname  = "../gutim_1/output/score_features.csv"
    preset_feat_csv_fname = "../gutim_1/output/preset_features.csv"
    perf_feat_csv_fname   = "output/perf_feat.csv"
    
    train_args = dict(
        score_feat_fname  = os.path.expanduser(score_feat_csv_fname),
        preset_feat_fname = os.path.expanduser(preset_feat_csv_fname),
        perf_feat_fname   = os.path.join(perf_feat_csv_fname),
        fixed_feat_fname  = os.path.join(out_dir,"fixed_feat.json"),    # used later for real-time inference
        train_data_fname  = os.path.join(out_dir,train_data_fname),    # fixed + perf features
        
    )

    train_args = types.SimpleNamespace(**train_args)
    
    generate_training_data( train_args )
