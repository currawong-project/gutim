Generate the edit file:
=======================

Given the MusicXML score alone we need to bootstrap the score_pipeline to
the point where we can run the 'timing' stage, from there the 'edit' file can be created
with 'gen_text_edit_file.py'

Given the manually updated 'edit' file the pipeline edit files 'section.yaml','pedal.yaml'
and 'attr_correction.yaml' are then generated from 'apply_edit_file.py'

The pipeline can then be re-run on gutim_2 a/b/c to generate the final score.


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



Directions:

The goal of modifing an 'edit' file is to fine tune the location and values of certain attributes
that cannot be easily extracted from the Sibelius score.

The file is organized into measures consisting of time orderd 'event' lines indicating notes and rests.
Most event lines are divided with a '|' character into a left and right part.
The left part of the line should never be modified, all of the editing is done on the right part.


1. Section Markers.

Section markers look like this 'section:1234'. Where 1234 indicates a section id.

Verify that the section markers are assigned to the first event in the section
and move them if necessary.  Once the section marker is correctly positioned
add the suffix ':ok' to the marker.

2. Pedal Markers:

Most pedal markers look like this: 'damp:down','damp:up','sost:down','sost:up', however
more complex variants are possible such as:

'damp:clear:down'   : Quickly clear the pedal before depressing it again.
'damp:depth=0.5'    : Half pedal
'damp:depth=0:ramp' : Gradually press the pedal down to the depth of the next pedal event.d

Verify that the pedal markers are assigned to a reference note which occurs at the same time as the event.
If the existing pedal event is assigned to the wrong note then move it the correct one.
Once the pedal marker is at the correctl location and contains the correct attributes then
add the suffix ':ok' to indicate that the pedal marker was reviewed.

If a note or rest is not at exactly the correct location then leave the note '# pedal offset'
on the line with the pedal marker.

More Pedal Examples     |
------------------------|--------------------------------------------------
damp:down               | Damper pedal down
damp:up                 | Damper pedal up
damp:down=0.5           | Half pedal
damp:down=1.0           | Same as pedal down
damp:clear:down         | Release and re-apply pedal
damp:clear=0.5:down     | Half release and re-apply pedal
damp:down:ramp          | Full down gradually move to next pedal depth.
down:up:ramp            | Full up and gradually move to next pedal depth.

Legal Sostenuto Commands |
-------------------------|-------------------------------------------------
sost:down                | Sostenuto down
sost:up                  | Sostenuto up


3. Metronome Markers:

These markers look like this: 'metro:q:65'.  The BPM values are already
verified to be correct however the marker may have to moved to the first note in the new tempo regime.
Add the suffix ':ok' to indicate that the marker was reviewed.


4. Dynamics Markers:

Every note that has an 'o' marker requires an explicit dynamics
value. Scan the score and choose from one of the 25 possible dynamics
values shown in the table below. The dynamics may be entered one note
at a time or in blocks.  Entering in blocks allows dynamic fork values
to be automatically inserted without having to do manual
interpolation.

Individual dynamics markers look like this: 'd:ff', 'd:p+', 'd:s'. Note that 'd:s' indicates a 'silent' note.

Sequences of dynamic markers can be entered by just entering the starting and ending marks and then
letting the system interpolate the values in between.  These markers look like this:

d:fff:>   : start a sequence at fff
...       : (multiple event lines here)
d:>:ppp   : end a sequence at ppp

In this case the dynamics will decrease from fff to ppp.

NOTE: The system will only insert dynamic values automatically on notes which have no
dynamic mark already.  If a note between the begin/end markers already has an dynamic
mark then that note will not recieve an interpolated value. This means that any notes
which should be set by the system must have any existing dynamic value deleted.

This scheme has the advantage of allowing long sequences of automatically generated
dynamics but also allows exceptions to be placed mid-sequence by simply inserting a literal
dynamic mark.

Here's another example that interpolates from ppp to fff:

d:ppp:>
...
d:>:fff

In this exaple all notes in the sequence will be set to mf+.

d:mf+:>
...
d:>:mf+

5. Grace Notes:
---------------
It is possible that grace notes are not correctly sequenced relative to the notes around them.
In this case the grace note lines should be moved to the correct location and sequence.
In moving the lines do not edit any of the content to the left of the '|' marker.
The system can only notice the reordering and apply the correct updates if the content to the left of the '|' is unaltered.


General Notes:
----------------------
1. Only edit to right of '|' marker
2. move and add 'ok' to each section boundary.
3. insert/move/correct and add 'ok' to pedal markers
4. insert/correct dynamic markers on all events that have 'o' markers.
5. Add free form text on right most side after '#' marker
6. Multiple markers can be assigned to the same event line by including a space between them.

Parts of an event line:
-----------------------

index meas time        tick   id           pitch  val. tie flag   editable attributes       notes
----- ---- ----- -- -- ------ -----------  -----  ---- --- ----   ------------------------- -----------------------
 27    88  3.433 v1 s1 t=2304 ng88_1C7e_0     C7  e.   tb  cgo  | d:mp section:1234 damp:up # notes go here
                 |  |
		 |  + staff
		 + voice

flags  |
-------|-----------------------
   c   | chord
   g   | grace note/rest
   o   | This note is sounded


values |
-------|-----------------
M      | measure
w      | whole
h      | half
q      | quarter
e      | eighth 
s      | sixteenth
t      | thirtysecond
x      | sixtyfourth

Notes:
1. The tick value of grace notes does not reflect the time order of the notes.
2. The pitch value of rests is shown as 'R'.
3. Tie values: tb=tie begin, tc=tie continue, te=tie end
4. Flag values: c=chord,g=grace,o=onset
5. Add a '#' followed by any text to include a comment on any line



Legal Dynamics Marks
---------------------
d:s (silent note)
d:pppp-
d:pppp
d:pppp+
d:ppp-
d:ppp
d:ppp+
d:pp-
d:pp
d:pp+
d:p-
d:p
d:p+
d:mp-
d:mp
d:mp+
d:mf-
d:mf
d:mf+
d:f-
d:f
d:f+
d:ff
d:ff+
d:fff




