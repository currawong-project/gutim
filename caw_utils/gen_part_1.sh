
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
python caw_utils/gen_part_1_files.py

# generates gutim_1/tl_play.json, gutim_1/caw/tl_score.csv and gutim_1/output/caw_toc.json
python caw_utils/gen_part_1_tl_play_file.py

# generate gutim_1/caw/gutim_ctl.json and seg_menu.json
python caw_utils/gen_part_1_ctl_files.py

