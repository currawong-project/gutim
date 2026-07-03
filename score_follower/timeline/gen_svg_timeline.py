#!/usr/bin/env python3
"""Generate an HTML/SVG timeline from score/performance JSON."""

import argparse
import json
import os
import sys

# Layout constants
BOX_W = 30
BOX_H = 20
LANE_PAD = 8       # vertical padding inside each lane (above and below note stacks)
LANE_GAP = 24      # vertical gap between score lane bottom and perf lane top
LEFT_MARGIN = 60   # space on left for lane labels
RIGHT_MARGIN = 30
TOP_MARGIN = 30    # space above score lane for measure labels
BOTTOM_MARGIN = 22 # space below perf lane for time labels

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_to_sci(pitch):
    return f"{NOTE_NAMES[pitch % 12]}{(pitch // 12) - 1}"


def parse_args():
    p = argparse.ArgumentParser(description='Generate HTML timeline from score/perf JSON')
    p.add_argument('json_file', nargs='?', default='timeline.json')
    p.add_argument('out_dir',  nargs='?', default='.')
    p.add_argument('--beg-loc', type=int, default=None, metavar='LOC',
                   help='First score location to display (default: first in score)')
    p.add_argument('--end-loc', type=int, default=None, metavar='LOC',
                   help='Last score location to display (default: last in score)')
    p.add_argument('--scale', type=float, default=100.0, metavar='PX_PER_SEC',
                   help='Pixels per second (default: 100)')
    return p.parse_args()


def nudge_chords(chords):
    """Shift chord display_x rightward to prevent box overlap."""
    min_next_center = -float('inf')
    for chord in sorted(chords, key=lambda c: c['display_x']):
        if chord['display_x'] < min_next_center:
            chord['display_x'] = min_next_center
        min_next_center = chord['display_x'] + BOX_W


def build_svg(data, beg_loc_id, end_loc_id, scale):
    score = data['score']
    perf_records = data['perf']

    all_locs = sorted(score.keys(), key=int)

    # When bounds are not specified, derive them from the perf data's referenced locs.
    if beg_loc_id is None or end_loc_id is None:
        perf_locs = [
            int(note['loc']) for rec in perf_records
            for note in rec['noteL'] if note.get('loc') is not None
        ]
        if perf_locs:
            if beg_loc_id is None:
                beg_loc_id = min(perf_locs)
            if end_loc_id is None:
                end_loc_id = max(perf_locs)
        else:
            if beg_loc_id is None:
                beg_loc_id = int(all_locs[0])
            if end_loc_id is None:
                end_loc_id = int(all_locs[-1])

    beg_loc = str(beg_loc_id)
    end_loc = str(end_loc_id)

    if beg_loc not in score:
        sys.exit(f"Error: --beg-loc {beg_loc} not found in score")
    if end_loc not in score:
        sys.exit(f"Error: --end-loc {end_loc} not found in score")

    beg_idx = all_locs.index(beg_loc)
    end_idx = all_locs.index(end_loc)
    if beg_idx > end_idx:
        sys.exit("Error: --beg-loc must not be after --end-loc")
    visible_locs = all_locs[beg_idx:end_idx + 1]

    score_t0 = score[beg_loc]['sec']
    score_t1 = score[end_loc]['sec']

    def score_x(t):
        return LEFT_MARGIN + (t - score_t0) * scale

    # Perf time origin: sec of the earliest matched perf note (any loc != None)
    perf_t0 = min(
        (note['sec'] for rec in perf_records for note in rec['noteL']
         if note.get('loc') is not None),
        default=perf_records[0]['sec'] if perf_records else 0.0
    )

    def perf_x(t):
        return LEFT_MARGIN + (t - perf_t0) * scale

    # --- Score chords ---
    score_chords = []
    for loc_key in visible_locs:
        rec = score[loc_key]
        notes = sorted(rec['noteL'], key=lambda n: -n['pitch'])  # high pitch on top
        tx = score_x(rec['sec'])
        score_chords.append({
            'loc': loc_key,
            'sec': rec['sec'],
            'meas': rec['meas'],
            'time_x': tx,
            'display_x': tx,
            'notes': [
                {'pitch': n['pitch'], 'sci_pitch': n['sci_pitch'], 'stack_idx': i}
                for i, n in enumerate(notes)
            ]
        })

    max_score_depth = max((len(c['notes']) for c in score_chords), default=1)
    nudge_chords(score_chords)

    # --- Perf chords ---
    perf_chords = []
    for rec in perf_records:
        notes = sorted(rec['noteL'], key=lambda n: n['sec'])  # earliest on top
        tx = perf_x(rec['sec'])
        perf_chords.append({
            'sec': rec['sec'],
            'time_x': tx,
            'display_x': tx,
            'notes': [
                {
                    'pitch': n['pitch'],
                    'sci_pitch': n['sci_pitch'],
                    'loc': n.get('loc'),
                    'sec': n['sec'],
                    'stack_idx': i,
                }
                for i, n in enumerate(notes)
            ]
        })

    max_perf_depth = max((len(c['notes']) for c in perf_chords), default=1)
    nudge_chords(perf_chords)

    # SVG width covers whichever lane is wider after nudging.
    score_right = max((c['display_x'] for c in score_chords), default=LEFT_MARGIN) + BOX_W / 2
    perf_right  = max((c['display_x'] for c in perf_chords),  default=LEFT_MARGIN) + BOX_W / 2
    svg_width = max(score_right, perf_right) + RIGHT_MARGIN

    # --- Lane geometry ---
    score_lane_h = LANE_PAD + max_score_depth * BOX_H + LANE_PAD
    perf_lane_h = LANE_PAD + max_perf_depth * BOX_H + LANE_PAD
    score_lane_top = TOP_MARGIN
    perf_lane_top = score_lane_top + score_lane_h + LANE_GAP
    lanes_bottom = perf_lane_top + perf_lane_h
    svg_height = lanes_bottom + BOTTOM_MARGIN

    def score_note_y(stack_idx):
        return score_lane_top + LANE_PAD + stack_idx * BOX_H

    def perf_note_y(stack_idx):
        return perf_lane_top + LANE_PAD + stack_idx * BOX_H

    # --- Determine which score notes are matched by a visible perf note ---
    matched_score = set()  # set of (loc_str, pitch)
    for chord in perf_chords:
        cx = chord['display_x']
        if cx + BOX_W / 2 < 0 or cx - BOX_W / 2 > svg_width:
            continue
        for note in chord['notes']:
            if note['loc'] is not None:
                matched_score.add((str(note['loc']), note['pitch']))

    # Score note lookup for connection lines: (loc_str, pitch) -> (chord, note_dict)
    score_note_lookup = {}
    for chord in score_chords:
        for note in chord['notes']:
            score_note_lookup[(chord['loc'], note['pitch'])] = (chord, note)

    # --- SVG element builder ---
    els = []

    def r(x, y, w, h, fill='white', stroke='#444', sw=1, rx=2):
        els.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>'
        )

    def t(x, y, s, anchor='middle', fs=8, fill='#222'):
        els.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-size="{fs}" fill="{fill}" font-family="monospace">{s}</text>'
        )

    def ln(x1, y1, x2, y2, stroke='#ccc', sw=1):
        els.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>'
        )

    # Background
    r(0, 0, f'{svg_width:.0f}', f'{svg_height:.0f}', fill='white', stroke='none', sw=0)

    # Lane backgrounds
    r(0, score_lane_top, f'{svg_width:.0f}', score_lane_h, fill='#fafaf4', stroke='none', sw=0)
    r(0, perf_lane_top,  f'{svg_width:.0f}', perf_lane_h,  fill='#f4f4fa', stroke='none', sw=0)

    # Time grid (every 5 seconds of score time)
    offset = 0.0
    while True:
        x = LEFT_MARGIN + offset * scale
        if x > svg_width:
            break
        ln(x, score_lane_top, x, lanes_bottom, stroke='#e0e0e0', sw=0.5)
        t(x, lanes_bottom + 14, f'{offset:.0f}s', fs=8, fill='#aaa')
        offset += 5.0

    # 1-second tick marks on the bottom border only, between 5-second grid lines
    sec_offset = 1.0
    while True:
        x = LEFT_MARGIN + sec_offset * scale
        if x > svg_width:
            break
        if sec_offset % 5 != 0:
            ln(x, lanes_bottom, x, lanes_bottom + 4, stroke='#bbb', sw=0.8)
        sec_offset += 1.0

    # Measure grid lines (at original time_x of first chord in each new measure)
    prev_meas = None
    for chord in sorted(score_chords, key=lambda c: c['sec']):
        if chord['meas'] != prev_meas:
            x = chord['time_x']
            ln(x, score_lane_top, x, lanes_bottom, stroke='#c0c0c0', sw=0.8)
            t(x, score_lane_top - 5, f'M{chord["meas"]}', fs=8, fill='#777')
            prev_meas = chord['meas']

    # Lane borders
    ln(0, score_lane_top,           svg_width, score_lane_top,           stroke='#bbb', sw=1)
    ln(0, score_lane_top + score_lane_h, svg_width, score_lane_top + score_lane_h, stroke='#bbb', sw=1)
    ln(0, perf_lane_top,            svg_width, perf_lane_top,            stroke='#bbb', sw=1)
    ln(0, lanes_bottom,             svg_width, lanes_bottom,             stroke='#bbb', sw=1)

    # Connection lines (drawn before boxes so boxes appear on top)
    for chord in perf_chords:
        for note in chord['notes']:
            if note['loc'] is None:
                continue
            key = (str(note['loc']), note['pitch'])
            if key not in score_note_lookup:
                continue
            sc, sn = score_note_lookup[key]
            px = chord['display_x']
            py = perf_note_y(note['stack_idx']) + BOX_H / 2
            sx = sc['display_x']
            sy = score_note_y(sn['stack_idx']) + BOX_H / 2
            ln(px, py, sx, sy, stroke='#b0b0b0', sw=0.8)

    # Score note boxes
    for chord in score_chords:
        for note in chord['notes']:
            key = (chord['loc'], note['pitch'])
            stroke = 'red' if key not in matched_score else '#444'
            bx = chord['display_x'] - BOX_W / 2
            by = score_note_y(note['stack_idx'])
            r(bx, by, BOX_W, BOX_H, fill='#fffff0', stroke=stroke)
            t(chord['display_x'], by + BOX_H * 0.72, note['sci_pitch'], fs=8)

    # Perf note boxes
    for chord in perf_chords:
        for note in chord['notes']:
            stroke = 'red' if note['loc'] is None else '#444'
            bx = chord['display_x'] - BOX_W / 2
            by = perf_note_y(note['stack_idx'])
            r(bx, by, BOX_W, BOX_H, fill='#f0f0ff', stroke=stroke)
            t(chord['display_x'], by + BOX_H * 0.72, note['sci_pitch'], fs=8)

    # Lane labels (centered vertically in the left margin area)
    t(LEFT_MARGIN / 2, score_lane_top + score_lane_h / 2, 'Score',
      anchor='middle', fs=10, fill='#666')
    t(LEFT_MARGIN / 2, perf_lane_top + perf_lane_h / 2, 'Perf',
      anchor='middle', fs=10, fill='#666')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_width:.0f}" height="{svg_height:.0f}" '
        f'viewBox="0 0 {svg_width:.0f} {svg_height:.0f}">\n'
        + '\n'.join(els)
        + '\n</svg>'
    )
    return svg, int(svg_width), int(svg_height)

def gen_file(out_dir, entries, beg_loc=None, end_loc=None, scale=100.0):
    """Generate one SVG per entry and a combined HTML wrapper.

    entries: { title: json_fname }
          or { title: {"json": json_fname, "beg_loc": N, "end_loc": N, "scale": N} }
    beg_loc/end_loc/scale are global defaults, overridden per entry when provided.
    """
    os.makedirs(out_dir, exist_ok=True)

    sections = []

    for title, entry in entries.items():
        if isinstance(entry, str):
            json_fname = entry
            e_beg_loc, e_end_loc, e_scale = beg_loc, end_loc, scale
        else:
            json_fname = entry['json']
            e_beg_loc = entry.get('beg_loc', beg_loc)
            e_end_loc = entry.get('end_loc', end_loc)
            e_scale   = entry.get('scale',   scale)

        with open(json_fname) as f:
            data = json.load(f)

        svg, w, h = build_svg(data, e_beg_loc, e_end_loc, e_scale)

        svg_fname = os.path.join(out_dir, f'{title}_timeline.svg')
        with open(svg_fname, 'w') as f:
            f.write(svg)

        sections.append((title, svg))
        print(f"Written {w}×{h}px → {svg_fname}")

    section_html = '\n'.join(
        f'<div class="entry">\n'
        f'  <div class="entry-title">{title}</div>\n'
        f'  <div class="scroll">{svg}</div>\n'
        f'</div>'
        for title, svg in sections
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Score/Perf Timeline</title>
<style>
  body        {{ margin: 0; padding: 10px; background: #fff; font-family: sans-serif; }}
  #toolbar    {{ display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
                 font-size: 13px; color: #444; }}
  .entry      {{ margin-bottom: 16px; }}
  .entry-title{{ font-size: 13px; font-weight: bold; color: #444; margin-bottom: 4px; }}
  .scroll     {{ overflow-x: auto; overflow-y: hidden; border: 1px solid #ddd; }}
</style>
</head>
<body>
<div id="toolbar">
  <label><input type="checkbox" id="lock"> Lock scroll</label>
</div>
{section_html}
<script>
(function () {{
  const lock = document.getElementById('lock');
  const divs = Array.from(document.querySelectorAll('.scroll'));
  let syncing = false;

  divs.forEach(function (div) {{
    div.addEventListener('scroll', function () {{
      if (!lock.checked || syncing) return;
      syncing = true;
      divs.forEach(function (other) {{
        if (other !== div) other.scrollLeft = div.scrollLeft;
      }});
      syncing = false;
    }});
  }});

  lock.addEventListener('change', function () {{
    if (lock.checked) {{
      divs.forEach(function (div) {{ div.scrollLeft = 0; }});
    }}
  }});
}})();
</script>
</body>
</html>"""

    html_fname = os.path.join(out_dir, 'timeline.html')
    with open(html_fname, 'w') as f:
        f.write(html)

    print(f"Written HTML → {html_fname}")


def main():
    args = parse_args()
    title = os.path.splitext(os.path.basename(args.json_file))[0]
    gen_file(args.out_dir, {title: args.json_file},
             beg_loc=args.beg_loc, end_loc=args.end_loc, scale=args.scale)
    



if __name__ == '__main__':
    main()
