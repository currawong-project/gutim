

# Run 'parse' through 'assign-sustain' to build a cached 'build' pipeline result.
python -m piano --config gutim_1/config.yaml build --clean

# Generate a Segmented list based on section_toc.txt and the cached 'build' pipeline result.
python -m piano --config gutim_1/config.yaml build-seg-list

# Generate Score features based for each section.
python -m piano --config gutim_1/config.yaml gen-score-features.

# Generate Preset features for the context preceeding each preset selection
python -m piano --config gutim_1/config.yaml gen-preset-features

# Generate the 'group-info' file containing sets of events that must be measured
# for certain attributes: dynamcs, tempo, evenness, grace notes, chords, etc.
# This is used by the performance feature generator
python -m piano --config gutim_1/config.yaml gen-group-info




