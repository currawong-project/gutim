This project contains data and utilities for transforming and visualizing GUTIM related data files.

Table Of Contents:

score_pipeline/
- Pipeline for converting MusicXML to structured data.
- This folder is a separate git repo.

score_follower/
- Score follow recorded performances.

feature_gen/
- Produce performance data features from score-followed recorded performances.
- Combine section based score features and preset trigger location feature with performance features to
  produce training data.

score_editor/
- Produce text 'edit' files that can be manually edited to refine the score.

caw_utils/
- Generate configuration files used by the caw real-time system.

perf_data/
- Recorded MIDI performance data 

gutim_1/
- Score,feature,caw data for GUTIM part 1

gutim_2/
- Score,feature,caw data for GUTIM part 2

  
  
Notes on setting up to run `caw_utils/gen_part_1_file.py` on gutim_2/a/b/c 
```
score_editor/apply_edit_file.py - creates attr_corrections.yaml
copy working/*/apply/attr_corrections.yaml gumim_2/*/edits/attr_corrections.yaml
python -m piano --config gutim_2/*/config.yaml build --clean
python -m piano --config gutim_2/*/config.yaml build-seg-list
rm gutim_2/*/output/legacy_sf_score.csv # must erase or next command will do nothing
python -m piano --config gutim_2/*/config.yaml  gen-legacy-sf-score-csv
copy score/catalog.json to output/new_catalog.json
python caw_utils/gen_part_1_files.py 
```
