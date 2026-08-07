


export PYTHONPATH=$PWD/score_pipeline

python score_editor/sync_presets.py # generate (a/b/c)/scores/catalog.json

cp gutim_2/a/scores/catalog.json gutim_2/a/output/new_catalog.json
python -m piano --config gutim_2/a/config.yaml build --clean
python -m piano --config gutim_2/a/config.yaml build-seg-list
python -m piano --config gutim_2/a/config.yaml gen-legacy-sf-score-csv


python caw_utils/gen_part_2_files.py
