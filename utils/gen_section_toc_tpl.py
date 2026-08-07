import csv

from piano.model import (SectionBoundary)

def gen_section_toc_tpl(src_pkl_fname,out_fname,piano):

    measSectL = []
    with open(src_pkl_fname,'rb') as f:
        score = pickle.load(f)

    for m in score.measures:
        for e in m.events:
            if isinstance(e,SectionBoundary):
                measSectL.append( (m.number,e.section_id) )

    with open(out_fname,"w") as f:
        for meas_numb,section_id in measSectL:
            f.write(f"{meas_numb} S {section_id} {section_id} {piano}\n")
                        

def parse_section_sync_sheet_csv(fname):
    section_pianoL = []
    with open(fname) as f:
        rdr = csv.DictReader(f)

        for r in rdr:
            piano = r['piano']
            if r['new_id'].isdigit():
                section_id = int(r['new_id'])
            else:
                section_id = int(r['new_id'][:-1])

            section_pianoL.append((r['meas'],section_id,piano))

    return section_pianoL
            
def gen_section_toc_tpl( char_code, section_pianoL, out_fname ):

    with open(out_fname,"w") as f:
        for meas,section_id,piano_id in section_pianoL:
            if char_code.upper() == piano_id:
                f.write(f"{meas} S {section_id} {section_id} {piano_id}\n")

    
            

if __name__ == "__main__":

    section_map_csv_fname = "gutim_2/gutim_2_sync_sheet_edited.csv"
    
    charL = [ 'a','b','c']

    section_pianoL = parse_section_sync_sheet_csv(section_map_csv_fname)

    for c in charL:
        out_fname    = f"gutim_2/{c}/scores/section_toc_tpl.txt"
        gen_section_toc_tpl(c,section_pianoL,out_fname)
