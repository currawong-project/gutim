import json

def write_spirio_mp_file( out_json_fname, src_fileL ):

    mpD      = {}
    label_id = 0
    
    for fname in src_fileL:
        
        with open(fname) as f:
            smD = json.load(f)

        for label,d in smD.items():
            assert label not in mpD
            d['label_id']  = label_id
            mpD[label]     = d
            label_id      += 1

    with open(out_json_fname,"w") as f:
        json.dump(mpD,f,indent=2)


        
if __name__ == "__main__":

    char_codeL = ['a','b','c']

    out_json_fname = f"gutim_2/spirio_mp.json"

    src_fileL = []
    for c in char_codeL:
        src_fileL.append( f"gutim_2/{c}/caw/spirio_mp.json")
        
    
    write_spirio_mp_file( out_json_fname, src_fileL )

    
