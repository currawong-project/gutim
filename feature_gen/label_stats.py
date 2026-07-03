import pickle

def print_stats( fname ):

    with open(fname,'rb') as f:
        d = pickle.load(f)

        label_colMapD = d['label_colMapD']  
        labelL        = d['labelL']

        presetTypeN = len(label_colMapD)
        
        cntV = [0] * presetTypeN
        weightV = [0.0] * presetTypeN
        dry_only_cnt = 0
        dry_idx = label_colMapD['dry']

        for labelV in labelL:
            dry_fl = False
            sel_cnt = 0
            for i,order in enumerate(labelV):
                
                if order != 0:

                    if i == dry_idx:
                        dry_fl = True

                    sel_cnt += 1
                        
                    cntV[i] += 1
                    weightV[i] += 1.0/order


            assert sel_cnt != 0

            # if 'dry' was the only selected preset
            if sel_cnt == 1 and dry_fl:
                dry_only_cnt += 1
            

        print("Preset Spans:",len(labelL),"dry-only:",dry_only_cnt)

        for name,_ in label_colMapD.items():
            print(f"{name:4} ",end="")
        print("")
        
        for _,i in label_colMapD.items():
            print("---- ",end="")
        print("")
        
        for _,i in label_colMapD.items():
            print(f"{cntV[i]:4} ",end="")
        print("")
        
        for _,i in label_colMapD.items():
            x = int(round(100.0*weightV[i]/cntV[i]))
            print(f"{x:4} ",end="")
        print("")
        
    

if __name__ == "__main__":

    train_data_fname      = "output/training_0.pkl"

    print_stats(train_data_fname)
