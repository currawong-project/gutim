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

  