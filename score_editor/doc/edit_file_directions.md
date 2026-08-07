# Score Editor Files

Score File Editing Introduction
-------------------------------
Score edit files are derived from a Sibelius score and are used to set the location and values of certain score attributes
which are not otherwise available with sufficient precision.

Obtain the score editor files from each of these links.

- [Part A](https://github.com/currawong-project/gutim/blob/main/gutim_2/a/editor/piano_a_mod.txt)
- [Part B](https://github.com/currawong-project/gutim/blob/main/gutim_2/b/editor/piano_b_mod.txt)
- [Part C](https://github.com/currawong-project/gutim/blob/main/gutim_2/c/editor/piano_c_mod.txt)

Use the download button (Hover text: _Download Raw File_ ) button in the upper right to obtain a local copy of the file for editing.
Use a text file editor to edit the files, DO NOT use a standard word processor like MS Word. 

The attributes that available to edit are:
- __Section Markers__ 
- __Pedal Directions__
- __Metronome Mark Location__
- __Dynamics Directions__
- __Grace Note Location__

Detailed directions regarding each of these attributes is included below.


Score editor file layout
-------------------------

The score editor file is organized into measures consisting of time orderd _event_ lines which describe notes and rests.
Event lines are divided into a right and left part by a '|' character.
The left part of the line should never be modified, all of the editing is done on the right part.

Here is an example event line:

```
index meas time        tick   id           pitch  val tie flag   editable attributes       notes
----- ---- ----- -- -- ------ -----------  -----  --- --- ----   ------------------------- ---------------
 27    88  3.433 v1 s1 t=2304 ng88_1C7e_0     C7  e.   tb  cgo | d:mp section:1234 damp:up # notes go here
```

- The pitch value of rests is shown as 'R'.
- Tie values: tb=tie begin, tc=tie continue, te=tie end
- v1 is the voice id. Valid voice id's are v1,v2,v5,v6
- s1 is id of the top staff, s2 is the id of the bottom staff.
- The tick value of a grace note does not reflect the time order of the notes.


Note value abbreviations:

| Values | Description    |
|:------:|:---------------|
| M      | measure        |
| w      | whole          |
| h      | half           |
| q      | quarter        |
| e      | eighth         |
| s      | sixteenth      |
| t      | thirtysecond   |
| x      | sixtyfourth    |

Flag field codes:

| Flags | Descripiton                             |
|:-----:|:----------------------------------------|
|   c   | This note is part of a chord            |
|   g   | This is a grace note or rest            |
|   o   | This note has an onset                  |


## 1. Section Markers:

Section markers look like this `section:1234`. Where 1234 indicates a section id.

Verify that the section markers are assigned to the first event in the section
and move them if necessary.  Once the section marker is correctly positioned
add the suffix ':ok' to the marker.

## 2. Pedal Markers:

Most pedal markers look like this: `damp:down`,`damp:up`,`sost:down`,`sost:up`, however
more complex variants are possible such as:

| Pedal Examples      |  Description                                             |
|:----------          | :--------------------------------------------------------|
| `damp:clear:down`   | Quickly clear the pedal before depressing it again.      |
| `damp:depth=0.5`    | Half pedal                                               |
| `damp:depth=0:ramp` | Gradually press the pedal down to the depth of the next pedal event. |

Verify that the pedal markers are assigned to a reference note which occurs at the same time as the event.
If the existing pedal event is assigned to the wrong note then move it the correct one.
Once the pedal marker is at the correct location and contains the correct values then
add the suffix ':ok' to indicate that the pedal marker was reviewed.

If a note or rest is not at exactly the correct location then leave the note '# pedal offset'
on the line with the pedal marker.

| More Pedal Examples     | Description                                      |
| ------------------------|--------------------------------------------------|
| damp:down               | Damper pedal down                                |
| damp:up                 | Damper pedal up                                  |
| damp:down=0.5           | Half pedal                                       |
| damp:depth=1.0          | Same as pedal down                               |
| damp:clear:down         | Release and re-apply pedal                       |
| damp:clear=0.5:down     | Half release and re-apply pedal                  |
| damp:down:ramp          | Full down then gradually move to next pedal depth. |
| `down:up:ramp`          | Full up then gradually move to next pedal depth.   |

Sostenuto Pedal Commands:

| Legal Sostenuto Commands | Description                                     |
| -------------------------|-------------------------------------------------|
| sost:down                | Sostenuto down                                  |
| sost:up                  | Sostenuto up                                    |


## 3. Metronome Markers:

Metronome markers look like this: `metro:q:65`.  The BPM values are already
verified to be correct however the marker may have to moved to the first note in the new tempo regime.
Add the suffix ':ok' to indicate that the marker was reviewed.


## 4. Dynamics Markers:

Every note that has an 'o' flag requires an explicit dynamics
value. Scan the score and choose from one of the 25 possible dynamics
values shown in the table below. The dynamics may be entered one note
at a time or in automatically interpolated sequences.  Use _sequence entry_ to insert dynamic fork values
automatically without having to do manual interpolation.

Individual dynamics markers look like this: `d:ff`, `d:p+`, `d:s`. Note that `d:s` indicates a 'silent' note.

Sequences of dynamic markers can be entered by just entering the starting and ending marks and then
letting the system interpolate the values in between.  These markers look like this:

```
d:fff:>   # start a sequence at fff
...       # (multiple event lines here)
d:>:ppp   # end a sequence at ppp
```
In this case the dynamics will decrease from fff to ppp.

__WARNING: Sequence markers may not overlap. 
THIS EXAMPLE WILL NOT WORK BECAUSE THE SEQUENCE MARKERS OVERLAP.__
```
d:fff:>   # start a sequence at fff
...
d:ppp:>   # start another sequence at ppp
..
d:>:ppp   # end a sequence at ppp
d:>:ff-   # end the second sequence at ff-
```

The system will only insert dynamic values automatically on
notes which do not already have dynamic mark already.  If a note
between the begin/end markers already has an dynamic mark then that
note will not recieve an interpolated value. This means that any notes
which should be set by the system must have any existing dynamic value
removed. This approach has the advantage of creating long sequences of
automatically generated dynamic marks while also allowing exceptions to be
placed mid-sequence by simply inserting a literal dynamic mark.

For example given the following event lines:
```
 19   5  1.662 v1 s2 t=1702 n5_1Cs2t_6      C#2 t    -- --o | 
 20   5  1.745 v5 s2 t=1787 n5_5A2t_7       A2  t    -- --o | d:pp
 21   5  1.828 v1 s2 t=1872 n5_1Cs2t_7      C#2 t    -- --o | d:mf
 22   5  1.911 v5 s2 t=1957 n5_5Fs1s_2      F#1 s    -- --o | 
 23   5  2.078 v1 s2 t=2128 n5_1A2t_8       A2  t    -- --o | d:pp+
 24   5  2.161 v5 s2 t=2213 n5_5Cs2t_8      C#2 t    -- --o | d:ff
 25   5  2.244 v1 s2 t=2298 n5_1A2t_9       A2  t    -- --o | d:p-
 26   5  2.327 v5 s2 t=2383 n5_5Fs1t_3      F#1 t    -- --o | 
 27   5  2.410 v1 s2 t=2468 n5_1Cs2t_9      C#2 t    -- --o | d:mf-
```

Apply a fork to the notes in voice 1, while setting the notes in voice 5 to specific values:

```
 19   5  1.662 v1 s2 t=1702 n5_1Cs2t_6      C#2 t    -- --o | d:mf:>
 20   5  1.745 v5 s2 t=1787 n5_5A2t_7       A2  t    -- --o | d:pp
 21   5  1.828 v1 s2 t=1872 n5_1Cs2t_7      C#2 t    -- --o | 
 22   5  1.911 v5 s2 t=1957 n5_5Fs1s_2      F#1 s    -- --o | d:pp
 23   5  2.078 v1 s2 t=2128 n5_1A2t_8       A2  t    -- --o | 
 24   5  2.161 v5 s2 t=2213 n5_5Cs2t_8      C#2 t    -- --o | d:pppp
 25   5  2.244 v1 s2 t=2298 n5_1A2t_9       A2  t    -- --o | 
 26   5  2.327 v5 s2 t=2383 n5_5Fs1t_3      F#1 t    -- --o | d:pppp
 27   5  2.410 v1 s2 t=2468 n5_1Cs2t_9      C#2 t    -- --o | d:>:f+
```

Notice that the previously existing dynamic marks on voice 1 were removed to indicate
that the system should fill these dynamics automatically. 
 

It is also possible to set sequences of dynamics to the same value
by setting the begin and end sequence marker to the same dynamic level
Like this:

```
d:mf+:>
...
d:>:mf+
```
In this case all unmarked notes between the two markers will be set to `mf+`.

Keep in mind when using the sequence markers that begin or end on simultaneous notes (chords) that 
in general the begin marker should be on the first row of the first note of the chord and the
end marker should be on the last row of the last note of the chord.  The other notes in the
chord will automatically be assigned the correct dynamic level.

Here is an example:
```
  7 305  0.588 v1 s1 t=384  n305_1Ab1e      Ab1 e    -- c-o | d:pp:>
  8 305  0.588 v1 s1 t=384  n305_1C4e       C4  e    -- c-o |
  9 305  0.588 v1 s1 t=384  n305_1G4e       G4  e    -- c-o | 
 10 305  0.783 v5 s2 t=511  n305_5D2t_1     D2  t.   -- --o | 
 11 305  0.979 v5 s2 t=639  n305_5G5t       G5  t.   -- --o | 
 12 305  1.176 v1 s1 t=768  n305_1Bb5h      Bb5 h    -- --o | 
 13 305  1.176 v5 s2 t=768  n305_5Ab3h      Ab3 h    -- c-o | 
 14 305  1.176 v5 s2 t=768  n305_5C4h       C4  h    -- c-o | 
 15 305  1.176 v5 s2 t=768  n305_5Gb4h      Gb4 h    -- c-o | d:>:ff
```
Notice that this fork begins on a chord and ends on a chord and that 
the begin marker is placed on the first row of the starting chord
and the end marker is placed on the last row of the ending chord.
The other notes in the chord will automatically be assigned the
correct dynamic values.


| Legal Dynamics Marks|
|:--------------------|
| d:s (silent note)   |
| d:pppp-             |
| d:pppp              |
| d:pppp+             |
| d:ppp-              |
| d:ppp               |
| d:ppp+              |
| d:pp-               |
| d:pp                |
| d:pp+               |
| d:p-                |
| d:p                 |
| d:p+                |
| d:mp-               |
| d:mp                |
| d:mp+               |
| d:mf-               |
| d:mf                |
| d:mf+               |
| d:f-                |
| d:f                 |
| d:f+                |
| d:ff                |
| d:ff+               |
| d:fff               |


## 5. Grace Notes:

In some cases grace notes are not correctly sequenced relative to the notes around them.
In this case the grace note lines should be moved to the correct location and sequence.
In moving the lines do not edit any of the content to the left of the '|' marker.
The system can only notice the reordering and apply the correct updates if the content to the left of the '|' is unaltered.


## 6. More Notes:

1. Only edit to right of '|' marker
2. move and add 'ok' to each section boundary.
3. insert/move/correct and add 'ok' to pedal markers
4. insert/correct dynamic markers on all events that have 'o' markers.
5. Add free form text on right most side after '#' marker
6. Multiple markers can be assigned to the same event line by including a space between them.





