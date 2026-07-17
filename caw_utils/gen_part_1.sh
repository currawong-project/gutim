
export PYTHONPATH=$PWD/score_pipeline
python -m piano --config gutim_1/config.yaml build --clean
python -m piano --config gutim_1/config.yaml build-seg-list
python -m piano --config gutim_1/config.yaml gen-legacy-sf-score-csv

python -m piano --config scriabin_74_4/config.yaml build --clean
python -m piano --config scriabin_74_4/config.yaml build-seg-list
python -m piano --config scriabin_74_4/config.yaml gen-legacy-sf-score-csv

python caw_utils/gen_part_1_files.py
