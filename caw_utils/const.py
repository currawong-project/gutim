
SCORE_CSV_TITLES = [('meas','i'),('sec','f'),('art_dur_sec','f'),('status','i'),('d0','i'),('d1','i'),('oloc','i'),('section','s'),('sci_pitch','s'),('grace','s'),('even','s'),('even_target','s'),('dyn','s'),('dyn_target','s'),('tempo','s'),('tempo_target','s'),('note_id','s') ]

CAW_SCORE_CSV_TITLES = SCORE_CSV_TITLES + [('src','s'),('src_meas','i')]


PLAYER_MAP = {
    "HC":dict(id=0,color='rose'),
    "NN":dict(id=1,color='yellow'),
    "AG":dict(id=2,color='green'),
    "EP":dict(id=3,color='blue'),
    "AK":dict(id=4,color='purple'),
    "SP":dict(id=5,color='white')
}

PIANO_MAP = {
    "A":0,
    "B":1,
    "C":2
}

DYN_MAP = {
    's':     0,
    'pppp-': 1,
    'pppp':  2,
    'pppp+': 3,
    'ppp-':  4,
    'ppp':   5,
    'ppp+':  6,
    'pp-':   7,
    'pp':    8,
    'pp+':   9,
    'p-':   10,
    'p':    11,
    'p+':   12,
    'mp-':  13,
    'mp':   14,
    'mp+':  15,
    'mf-':  16,
    'mf':   17,
    'mf+':  18,
    'f-':   19,
    'f':    20,
    'f+':   21,
    'ff':   22,
    'ff+':  23,
    'fff':  24,
}

MIDI_NOTE_ON_STATUS = 0x90
MIDI_NOTE_OFF_STATUS = 0x80
MIDI_CTL_STATUS = 0xb0
MIDI_DAMPER_D0 = 0x41
MIDI_SOST_D0 = 0x42
MIDI_DAMPER_HALF_VALUE = 43
MIDI_PEDAL_DOWN_D1 = 64
MIDI_MAX_CTL_VALUE = 127

DAMPER_CLEAR_OFFSET_SEC = -50.0/1000.0
