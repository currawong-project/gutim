
PLAYER_MAP = {
    "HC":dict(id=0,color='rose'),
    "NN":dict(id=1,color='yellow'),
    "AG":dict(id=2,color='green'),
    "EP":dict(id=3,color='blue'),
    "AK":dict(id=4,color='purple')    
}

PIANO_MAP = {
    "A":0,
    "B":1,
    "C":2
}

MIDI_NOTE_ON_STATUS = 0x90
MIDI_NOTE_OFF_STATUS = 0x80
MIDI_CTL_STATUS = 0xb0
MIDI_DAMPER_D0 = 0x41
MIDI_SOST_D0 = 0x42
MIDI_DAMPER_HALF_VALUE = 43
MIDI_MAX_CTL_VALUE = 127

DAMPER_CLEAR_OFFSET_SEC = -50.0/1000.0
