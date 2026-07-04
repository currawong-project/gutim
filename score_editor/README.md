Generate the score editor file:
================================

Given the MusicXML score alone we need to bootstrap the `score_pipeline` to
the point where we can run the 'timing' stage, from there the score edit file can be created
with 'gen_text_edit_file.py'

Given the manually updated score edit file the pipeline edit files `section.yaml`,`pedal.yaml`
and `attr_correction.yaml` are then generated from `apply_edit_file.py`

The pipeline can then be re-run on gutim_2 a/b/c to generate the complete pipline score.

[Directions for editing the score editor files can be found here.](https://github.com/currawong-project/gutim/blob/main/score_editor/doc/edit_file_directions.md)


```
cd ~/src/curawong/projects/gutim
export PYTHONPATH=$HOME/src/currawong/projects/gutim/score_pipeline

# clean the cache
rm gutim_2/a/output/cache/*.pkl
rm gutim_2/b/output/cache/*.pkl
rm gutim_2/c/output/cache/*.pkl

# Basic XML parse and save output to 'a.txt' and create an  initial.
python -m piano --config gutim_2/a/config.yaml parse > temp.txt
python -m piano --config gutim_2/b/config.yaml parse > temp.txt
python -m piano --config gutim_2/c/config.yaml parse > temp.txt

# Manually create gutim_2/*/edits/tie_corrections.yaml and run
# apply-tie-corrections until all errors are solved
python -m piano --config gutim_2/a/config.yaml apply-tie-corrections > temp.txt
python -m piano --config gutim_2/b/config.yaml apply-tie-corrections > temp.txt
python -m piano --config gutim_2/c/config.yaml apply-tie-corrections > temp.txt


# Generate gutim_2/*/edits/sections.yaml based on the current section boundary locations.
# These locations will later need to be verified as part of the editing process.
python score_editor/gen_sections.py

# Manually create gutim_2/*/edits/arrows.yaml
python -m piano --config gutim_2/a/config.yaml apply-arrows
python -m piano --config gutim_2/b/config.yaml apply-arrows
python -m piano --config gutim_2/c/config.yaml apply-arrows

# Generate gutim_2/*/edits/metronome.yaml based in gutim_2/a/output/cache/apply_arrows.pkl
python score_editor/gen_metro.py

# Add the ending metronome marker to gutim_2/*/metronome.yaml
missing_marker_1:
  measure:        348
  bpm:            35
  beat_unit:      q
  reference_note: re348_1Rh # Piano A
  reference_note: n348_1A4h # Piano B
  reference_note: re348_1Rh # Piano C

# Generate gutim_2/*/edits/apply-metronome.pkl
python -m piano --config gutim_2/a/config.yaml apply-metronome
python -m piano --config gutim_2/b/config.yaml apply-metronome
python -m piano --config gutim_2/c/config.yaml apply-metronome

# Generate the ritard spans template editing file gutim_2/*/edits/rit_spans.yaml.
# DON'T DO THIS IF A VALID gutim_2/*/edits/rit_spans.yaml FILE ALREADY EXISTS IT WILL OVERWRITE THE EXISTING FILE
python score_editor/gen_ritard.py

# Manually edit gutim_2/*/edits/rit_spans.yaml to place the ritard spans

# Generate gutim_2/a/edits/apply-rit-spans.pkl
python -m piano --config gutim_2/a/config.yaml apply-rit-spans
python -m piano --config gutim_2/b/config.yaml apply-rit-spans
python -m piano --config gutim_2/c/config.yaml apply-rit-spans

# Generate gutim_2/a/edits/timing.pkl
python -m piano --config gutim_2/a/config.yaml timing
python -m piano --config gutim_2/b/config.yaml timing
python -m piano --config gutim_2/c/config.yaml timing

# Use the gutim-1/output/cache/apply_sustain.pkl, gutim_2/*/output/cache/timing.pkl, and gutim_2/gutim_2_sync_sheet_edited.csv.
# to create gutim_2/*/editor/note_attr.json [ { <new_section_id>:{score:<>,mismatchN:<>,noteL:[note_id:<>, base_id:<>, attr:{oloc,dmark,dlevel}  ]}}]
# The output data structure specifies the element from the gutim_1 score which maps to each matching element in the gutim_2.
# Uses Smith_waterman.py to align gutim_2 score to gutim_1 score.
python score_editor/gen_sync.py

# Usee gutim_2/*/output/cache/timing.pkl and gutim_2/*/editor/note_attr.json to generate a text 'edit' file
# gutim_2/*/editor/piano_*_mod.txt and gutim_2/*/editor/link_*_mod.json which can be used to
# enter manual corrections to the score.
python score_editor/gen_edit_text_file.py

# Use the updated edit file to create sections.yaml, pedal.yaml, and attr_corrections.yaml
python score_editor/apply_edit_file.py
```




Notes on sections
-----------------
* A 7023 5927 zero length
* B 7025 unk  found at 5974
* B 7039 5980 zero length
* A 7042 5931 zero length
  C 7044      missing from score
* B 7051      no anchor - (this section is in A, remove from B)
* B 7052      no anchor - (this section id is not being found by 'extract_sections.py' and must be put into sections.yaml manually : sb79_7052: ng79_1A6e)
* B 7058                  (this section is in A, remove from B)
* B 7059      no anchor - (this section is in A, remove from B)
* C 7064 5995 zero length
* C 7067 5995 zero length
  A 7189 6048 Window (15) too long for sequence
  B 7191 unk (very short) ignore
    7193 
* B 7209 5995 zero length


