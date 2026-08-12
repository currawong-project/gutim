import json

def add_field( fname ):

    with open(fname) as f:
        segL = json.load(f)

    segLabelSet = set()
    
    for seg in segL:

        seg_label = f"{seg['sectL'][0]}_{seg['piano']}_{seg['beg_meas_num']}_{seg['player']}"

        assert seg_label not in segLabelSet
        segLabelSet.add(seg_label)

        seg['seg_label'] = seg_label

    with open(fname,"w") as f:
        json.dump(segL,f,indent=2)


if __name__ == "__main__":
    caw_toc_json_fnameL = [ "ref_section_toc_a_1.json","ref_section_toc_b_1.json","ref_section_toc_c_1.json" ]

    for fname in caw_toc_json_fnameL:
        print(fname)
        add_field( fname )
