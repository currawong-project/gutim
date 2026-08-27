
export PYTHONPATH=$PWD/score_pipeline
python -m piano --config gutim_1/config.yaml build --clean
python -m piano --config gutim_1/config.yaml build-seg-list
python -m piano --config gutim_1/config.yaml gen-legacy-sf-score-csv

python -m piano --config scriabin_74_4/config.yaml build --clean
python -m piano --config scriabin_74_4/config.yaml build-seg-list
python -m piano --config scriabin_74_4/config.yaml gen-legacy-sf-score-csv

python -m piano --config scriabin_74_3/config.yaml build --clean
python -m piano --config scriabin_74_3/config.yaml build-seg-list
python -m piano --config scriabin_74_3/config.yaml gen-legacy-sf-score-csv

# generates MP files for gutim,74_3,74_4
# generates gutim_1/caw/score.csv with scriabin insertions
# generate gutim_1/caw/presets.json with loc's which account for scriabin insertions
# NOTE: SF locs do not change after this processig
python caw_utils/gen_part_1_files.py

# 
# generates:
# gutim_1/tl_play.json - timeline player file for piano simulation
# gutim_1/caw/tl_score.csv - score with appropriate for use with caw cwPianoScore
# gutim_1/output/caw_toc.json - TOC with markers for scriabin insertions
python caw_utils/gen_part_1_tl_play_file.py

# generates:
# gutim_1/caw/gutim_ctl.json - for use with gutim_pgm_ctl
# gutim_1/caw/seg_menu.json  - for use with label_value_list segment drop down menu
python caw_utils/gen_part_1_ctl_files.py

