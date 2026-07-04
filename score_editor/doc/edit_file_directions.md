The goal of modifing an _edit_ file is to fine tune the location and values of certain attributes
that cannot be easily extracted from the Sibelius score.

The file is organized into measures consisting of time orderd _event_ lines indicating notes and rests.
Most event lines are divided with a '|' character into a left and right part.
The left part of the line should never be modified, all of the editing is done on the right part.


Parts of an event line:
-----------------------

Here is an example event line:

```
index meas time        tick   id           pitch  val. tie flag   editable attributes       notes
----- ---- ----- -- -- ------ -----------  -----  ---- --- ----   ------------------------- -----------------------
 27    88  3.433 v1 s1 t=2304 ng88_1C7e_0     C7  e.   tb  cgo  | d:mp section:1234 damp:up # notes go here
                 |  | 
		         |  + staff
		         + voice
```

- The tick value of a grace note does not reflect the time order of the notes.
- The pitch value of rests is shown as 'R'.
- Tie values: tb=tie begin, tc=tie continue, te=tie end


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
|   o   | This note has an onset, it is not tied. |




1. Section Markers:
--------------------

Section markers look like this `section:1234`. Where 1234 indicates a section id.

Verify that the section markers are assigned to the first event in the section
and move them if necessary.  Once the section marker is correctly positioned
add the suffix ':ok' to the marker.

2. Pedal Markers:
-----------------

Most pedal markers look like this: `damp:down`,`damp:up`,`sost:down`,`sost:up`, however
more complex variants are possible such as:

`damp:clear:down`   : Quickly clear the pedal before depressing it again.
`damp:depth=0.5`    : Half pedal
`damp:depth=0:ramp` : Gradually press the pedal down to the depth of the next pedal event.d

Verify that the pedal markers are assigned to a reference note which occurs at the same time as the event.
If the existing pedal event is assigned to the wrong note then move it the correct one.
Once the pedal marker is at the correctl location and contains the correct attributes then
add the suffix ':ok' to indicate that the pedal marker was reviewed.

If a note or rest is not at exactly the correct location then leave the note '# pedal offset'
on the line with the pedal marker.

| More Pedal Examples     | Description                                      |
| ------------------------|--------------------------------------------------|
| damp:down               | Damper pedal down                                |
| damp:up                 | Damper pedal up                                  |
| damp:down=0.5           | Half pedal                                       |
| damp:down=1.0           | Same as pedal down                               |
| damp:clear:down         | Release and re-apply pedal                       |
| damp:clear=0.5:down     | Half release and re-apply pedal                  |
| damp:down:ramp          | Full down gradually move to next pedal depth.    |
| `down:up:ramp`          | Full up and gradually move to next pedal depth.  |

| Legal Sostenuto Commands | Description                                     |
| -------------------------|-------------------------------------------------|
| sost:down                | Sostenuto down                                  |
| sost:up                  | Sostenuto up                                    |


3. Metronome Markers:
---------------------

These markers look like this: 'metro:q:65'.  The BPM values are already
verified to be correct however the marker may have to moved to the first note in the new tempo regime.
Add the suffix ':ok' to indicate that the marker was reviewed.


4. Dynamics Markers:
--------------------

Every note that has an 'o' marker requires an explicit dynamics
value. Scan the score and choose from one of the 25 possible dynamics
values shown in the table below. The dynamics may be entered one note
at a time or in blocks.  Entering in blocks allows dynamic fork values
to be automatically inserted without having to do manual
interpolation.

Individual dynamics markers look like this: 'd:ff', 'd:p+', 'd:s'. Note that 'd:s' indicates a 'silent' note.

Sequences of dynamic markers can be entered by just entering the starting and ending marks and then
letting the system interpolate the values in between.  These markers look like this:

```
d:fff:>   : start a sequence at fff
...       : (multiple event lines here)
d:>:ppp   : end a sequence at ppp
```
In this case the dynamics will decrease from fff to ppp.

NOTE: The system will only insert dynamic values automatically on notes which have no
dynamic mark already.  If a note between the begin/end markers already has an dynamic
mark then that note will not recieve an interpolated value. This means that any notes
which should be set by the system must have any existing dynamic value deleted.

This scheme has the advantage of allowing long sequences of automatically generated
dynamics but also allows exceptions to be placed mid-sequence by simply inserting a literal
dynamic mark.

Here's another example that interpolates from ppp to fff:

```
d:ppp:>
...
d:>:fff
```

In this exaple all notes in the sequence will be set to mf+.

```
d:mf+:>
...
d:>:mf+
``
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


5. Grace Notes:
---------------
It is possible that grace notes are not correctly sequenced relative to the notes around them.
In this case the grace note lines should be moved to the correct location and sequence.
In moving the lines do not edit any of the content to the left of the '|' marker.
The system can only notice the reordering and apply the correct updates if the content to the left of the '|' is unaltered.


6. General Notes:
----------------------
1. Only edit to right of '|' marker
2. move and add 'ok' to each section boundary.
3. insert/move/correct and add 'ok' to pedal markers
4. insert/correct dynamic markers on all events that have 'o' markers.
5. Add free form text on right most side after '#' marker
6. Multiple markers can be assigned to the same event line by including a space between them.





