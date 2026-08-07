import yaml

def filter_sections( sect_yaml_fname, toc_txt_fname, out_sect_yaml_fname ):

    def _parse_toc( toc_txt_fname ):
        toc_sectionL = []
        with open(toc_txt_fname) as f:
            for line in f:
                tokL = line.split(' ')
                tokL = [ tok for tok in tokL if len(tok.strip())>0 ]
                meas_num = int(tokL[0])
                type_id = tokL[1]
                if type_id == 'S':
                    section_id = int(tokL[2])
                    toc_sectionL.append(section_id)

        return toc_sectionL
                    
    def _parse_sections_yaml( sect_yaml_fname ):
        outD = {}
        with open(sect_yaml_fname) as f:
            sectionD = yaml.safe_load(f)

        for section_id, note_id in sectionD.items():
            tokL = section_id.split('_')
            section_num_id = int(tokL[1])
            outD[section_num_id] = dict(section_id=section_id, note_id=note_id)
            
        return outD

    def _filter_section_list( sectionD, toc_sectionL ):
        filt_sectL = []

        for section_id,d in sectionD.items():
            if section_id not in toc_sectionL:
                d['note_id'] = 'null'
                
            filt_sectL.append( d )

        return filt_sectL
            
    def _write_output_file( out_sect_yaml_fname, filt_sectL ):        
        with open(out_sect_yaml_fname,'w') as f:
            for d in filt_sectL:
                f.write(f"{d['section_id']}: {d['note_id']}\n")

    toc_sectionL = _parse_toc( toc_txt_fname )
    sectionD     = _parse_sections_yaml( sect_yaml_fname )    
    filt_sectL   = _filter_section_list( sectionD, toc_sectionL )
    _write_output_file( out_sect_yaml_fname, filt_sectL )
    
if __name__ == "__main__":

    char_codeL = ['b','c']
    
    for c in char_codeL:
        toc_txt_fname       = f"gutim_2/{c}/scores/section_toc.txt"
        sect_yaml_fname     = f"gutim_2/{c}/edits/section_no_edits.yaml"
        out_sect_yaml_fname = f"gutim_2/{c}/edits/sections.yaml"
        
        filter_sections( sect_yaml_fname, toc_txt_fname, out_sect_yaml_fname )
