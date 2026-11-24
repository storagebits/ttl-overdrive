#!/usr/bin/env python3
"""The demo's music: an original 4-channel chiptune, compiled to C data for src/player.c.

Pattern bytes:  0x01..0x5f note (1 = C0) then a length in rows,
                0x00 rest (release) then a length, 0x80|i instrument i, 0xff end.
Order lists:    (pattern, transpose) pairs per channel, 0xff = end of song.
Instruments:    wave (wavX low bits, +4 = noise shuffle), envelope (volumes 0..63 per frame,
                0xff = hold), release step, arpeggio (semitones per frame, 0x80|k = loop to k),
                vibrato on/off.
"""
import sys

SPEED = 6          # frames per row (also SONG_SPEED in src/player.s): 60/6 = 10 rows/s, 4 rows a beat = 150 BPM

NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def note(s):
    n = NAMES[s[0]]
    i = 1
    if s[i] == '#':
        n += 1; i += 1
    elif s[i] == 'b':
        n -= 1; i += 1
    return 1 + 12 * int(s[i:]) + n


# ---------------------------------------------------------------- instruments
INSTR = {}   # name -> (index, wave, env, release, arp, vib)


def instr(name, wave, env, release=8, arp=(0, 0x80), vib=0):
    env = list(env) + ([] if env[-1] == 0xff else [0xff])
    INSTR[name] = (len(INSTR), wave, env, release, list(arp), vib)


SQ, SAW, TRI, NOISE = 2, 3, 1, 0 | 4
instr('lead',  SQ,  [63, 60, 56, 52, 48, 46, 44, 0xff], release=6, vib=1)
instr('soft',  TRI, [20, 36, 48, 56, 60, 0xff], release=3, vib=1)
instr('echo',  SQ,  [30, 28, 26, 24, 22, 0xff], release=3)
instr('arpm',  SQ,  [40, 36, 32, 30, 0xff], release=4, arp=[0, 0, 3, 3, 7, 7, 12, 12, 0x80])
instr('arpM',  SQ,  [40, 36, 32, 30, 0xff], release=4, arp=[0, 0, 4, 4, 7, 7, 12, 12, 0x80])
instr('arpd',  SQ,  [40, 36, 32, 30, 0xff], release=4, arp=[0, 0, 3, 3, 6, 6, 12, 12, 0x80])
instr('bass',  SAW, [63, 58, 54, 50, 48, 0xff], release=10)
instr('pluck', SAW, [63, 50, 40, 32, 26, 22, 0xff], release=6)
instr('kick',  TRI, [63, 63, 62, 58, 52, 44, 34, 24, 14, 6, 0], arp=[24, 17, 12, 8, 5, 3, 1, 0, 0x87])
instr('snare', NOISE, [63, 56, 48, 40, 33, 27, 21, 16, 11, 7, 4, 2, 0])
instr('hat',   NOISE, [44, 26, 12, 4, 0])
instr('ohat',  NOISE, [40, 34, 28, 22, 17, 12, 8, 5, 2, 0])
instr('tom',   TRI, [63, 60, 54, 46, 36, 26, 16, 8, 0], arp=[7, 5, 3, 2, 1, 0, 0x85])
instr('crash', NOISE, [63, 60, 56, 52, 48, 44, 40, 36, 33, 30, 27, 24, 21, 18, 16, 14, 12, 10, 8, 6, 4, 2, 0],)

# ---------------------------------------------------------------- patterns
PATS = {}    # name -> bytes


def pat(name, text, check=16):
    out, rows = [], 0
    for tok in text.split():
        if tok.startswith('@'):
            out.append(0x80 | INSTR[tok[1:]][0])
            continue
        n, _, ln = tok.partition(':')
        ln = int(ln or 1)
        out += [0 if n == '-' else note(n), ln]
        rows += ln
    if check and rows % check:
        sys.exit(f'pattern {name}: {rows} rows')
    PATS[name] = bytes(out + [0xff])


# chord roots in octave 2 for the bass (A2 = 110 Hz); patterns are written on A, transposed
pat('bass1', '@bass A1:2 A1:2 A2:2 A1:2 A1:2 A2:2 A1:2 A2:2')
pat('bass2', '@bass A1:3 A1:3 A2:2 A1:2 A2:2 A1:2 G1:2')
pat('bass3', '@pluck A1:2 A2:1 A1:1 A2:2 A1:2 A2:1 A1:1 A2:2 A1:2 A2:2')
pat('bassh', '@bass A1:16')
pat('arpm',  '@arpm A3:16')
pat('arpM',  '@arpM A3:16')
pat('arpd',  '@arpd A3:16')
pat('rest',  '-:16')
pat('drum0', '@hat A#7:2 @hat A#7:2 @ohat A#7:4 @hat A#7:2 @hat A#7:2 @ohat A#7:4')
pat('drum1', '@kick A1:2 @hat A#7:2 @snare C7:2 @hat A#7:2 @kick A1:2 @kick A1:2 @snare C7:2 @ohat A#7:2')
pat('drum2', '@kick A1:2 @hat A#7:2 @snare C7:2 @hat A#7:1 @kick A1:1 @kick A1:2 @hat A#7:2 @snare C7:2 @ohat A#7:2')
pat('drum4', '@kick A1:4 @kick A1:4 @kick A1:4 @kick A1:4')
pat('fill1', '@kick A1:2 @hat A#7:2 @snare C7:2 @kick A1:2 @snare C7:1 @snare C7:1 @tom A3:2 @tom F3:2 @tom D3:2')
pat('roll',  '@snare C7:2 ' * 4 + '@snare C7:1 ' * 8)
pat('crash', '@crash A7:4 @hat A#7:2 @hat A#7:2 @kick A1:2 @hat A#7:2 @snare C7:2 @ohat A#7:2')
pat('end',   '@crash A7:16')

# lead A over Am F C G | Am F C G
pat('leadA1', '@lead E5:4 A4:2 C5:2 E5:3 D5:1 C5:2 B4:2')
pat('leadA2', 'C5:6 A4:2 F4:4 A4:2 C5:2')
pat('leadA3', 'G5:4 E5:2 C5:2 E5:3 D5:1 C5:2 E5:2')
pat('leadA4', 'D5:8 B4:4 G4:2 B4:2')
pat('leadA5', 'E5:4 A4:2 C5:2 E5:3 F5:1 E5:2 D5:2')
pat('leadA6', 'C5:4 D5:2 C5:2 A4:4 F4:2 A4:2')
pat('leadA7', 'G4:2 C5:2 E5:2 G5:2 A5:3 G5:1 E5:2 C5:2')
pat('leadA8', 'D5:6 E5:2 B4:6 -:2')
# lead B over Dm Am Bb E | Dm Am Bb E
pat('leadB1', '@lead F5:4 E5:2 D5:2 A4:4 D5:2 F5:2')
pat('leadB2', 'E5:6 C5:2 A4:4 E5:2 C5:2')
pat('leadB3', 'D5:4 F5:2 A#5:2 A5:4 F5:2 D5:2')
pat('leadB4', 'G#5:6 E5:2 B4:4 G#4:2 B4:2')
pat('leadB5', 'F5:2 A5:2 F5:2 D5:2 A5:4 G5:2 F5:2')
pat('leadB6', 'E5:4 C5:2 E5:2 A5:6 G5:2')
pat('leadB7', 'F5:3 E5:1 D5:2 F5:2 A#5:4 A5:4')
pat('leadB8', 'G#5:8 B5:4 G#5:2 E5:2')
# soft intro / break line (triangle), slow
pat('softA', '@soft E5:8 C5:8 C5:8 A4:8 G4:8 E5:8 D5:8 B4:8', check=16)
pat('softB', '@soft A5:12 G5:4 F5:8 E5:8 E5:12 C5:4 D5:8 B4:8', check=16)
pat('outro', '@soft A4:16 E5:16 A5:32', check=16)

# ---------------------------------------------------------------- arrangement (in bars)
A_CH = [('m', 0), ('M', -4), ('M', 3), ('M', -2)] * 2          # Am F C G (roots A F C G)
B_CH = [('m', 5), ('m', 0), ('M', 1), ('M', 7)] * 2            # Dm Am Bb E
LEADA = [f'leadA{i}' for i in range(1, 9)]
LEADB = [f'leadB{i}' for i in range(1, 9)]


def arps(chords):
    return [('arp' + q, t) for q, t in chords]


def bass(chords, p='bass1'):
    return [(p, t) for _, t in chords]


song = {0: [], 1: [], 2: [], 3: []}   # ch1 lead, ch2 arps, ch3 bass, ch4 drums


def section(lead, arp, bas, drm):
    n = len(arp)
    for ch, part in enumerate((lead, arp, bas, drm)):
        part = list(part)
        assert len(part) == n, (ch, len(part), n)
        song[ch] += part


R = [('rest', 0)]
# intro: 8 bars. arps alone, then hats, then bass enters
section(R * 8, arps(A_CH), R * 4 + bass(A_CH[4:], 'bassh'), R * 4 + [('drum0', 0)] * 3 + [('roll', 0)])
# A: 16 bars, full groove, lead on the second half
section(R * 8 + [(p, 0) for p in LEADA], arps(A_CH) * 2, bass(A_CH) * 2,
        [('crash', 0)] + [('drum1', 0)] * 6 + [('fill1', 0)] + [('crash', 0)] + [('drum2', 0)] * 6 + [('fill1', 0)])
# B: 16 bars, new chords, lead B twice (second time with the pluck bass)
section([(p, 0) for p in LEADB] * 2, arps(B_CH) * 2, bass(B_CH, 'bass2') + bass(B_CH, 'bass3'),
        [('crash', 0)] + [('drum2', 0)] * 6 + [('fill1', 0)] + [('crash', 0)] + [('drum1', 0)] * 6 + [('roll', 0)])
# break: 8 bars, no drums then four-on-the-floor build
section([('softB', 0)] + R * 3 + [('softA', 0)] + R * 3, arps(B_CH[:4]) + arps(A_CH[:4]),
        bass(B_CH[:4], 'bassh') + bass(A_CH[:4], 'bassh'),
        R * 4 + [('drum4', 0)] * 3 + [('roll', 0)])
# C: 16 bars, climax: lead A an octave up then lead B
section([(p, 12) for p in LEADA] + [(p, 0) for p in LEADB], arps(A_CH) + arps(B_CH),
        bass(A_CH, 'bass3') + bass(B_CH, 'bass1'),
        [('crash', 0)] + [('drum2', 0)] * 6 + [('fill1', 0)] + [('crash', 0)] + [('drum2', 0)] * 6 + [('roll', 0)])
# outro: 4 bars on Am, then the end
section([('outro', 0)] + R * 3, arps([('m', 0)] * 4), bass([('m', 0)] * 4, 'bassh'),
        [('end', 0)] + R * 3)

BARS = len(song[0])

# ---------------------------------------------------------------- glcc asm output
FLAG_NOISE, FLAG_VIB = 1, 2
HIT = {'kick': 0x10, 'snare': 0x20}


def arp_bytes(arp):
    out = []
    for i, b in enumerate(arp):
        if b & 0x80 and (b & 0xc0) == 0x80:      # loop marker: 0x80 | target -> 0x80 | distance back
            out.append(0x80 | (i - (b & 0x3f)))
        else:
            out.append(b & 0xff)
    return out


def notes_table():
    """keyL | keyH << 8 for notes 0..95 (1 = C0), as in the ROM's notesTable at $0900."""
    out = [0]
    for n in range(1, 96):
        f = 16.3516 * 2 ** ((n - 1) / 12)
        k = round(f * 32768 / (6.25e6 / 200 / 4))
        out.append((k & 127) | (k >> 7) << 8)
    return out


def emit_s(f):
    names = list(PATS)
    frags = []        # (kind, name, body lines)

    def data(name, body):
        frags.append((name, body))

    for n in names:
        data('p_' + n, f"bytes({','.join(str(b) for b in PATS[n])})")
    data('p_stop', 'bytes(0,255,255)')
    data('song_pats', 'words(' + ','.join(f"'p_{n}'" for n in names) + ')')
    for ch in range(4):
        seq = []
        for p, t in song[ch]:
            seq += [names.index(p), t & 0xff]
        chunks = [seq[i:i + 92] for i in range(0, len(seq), 92)]
        for k, c in enumerate(chunks):
            tail = f"bytes(0xfe);words('o{ch}_{k + 1}')" if k + 1 < len(chunks) else 'bytes(0xff)'
            data(f'o{ch}_{k}', f"bytes({','.join(map(str, c))});{tail}")
    data('song_ord0', 'words(' + ','.join(f"'o{ch}_0'" for ch in range(4)) + ')')
    for name, (i, wave, env, rel, arp, vib) in INSTR.items():
        data('e_' + name, f"bytes({','.join(map(str, env))})")
        data('a_' + name, f"bytes({','.join(map(str, arp_bytes(arp)))})")
    ins = list(INSTR.items())
    data('ins_env', 'words(' + ','.join(f"'e_{n}'" for n, _ in ins) + ')')
    data('ins_arp', 'words(' + ','.join(f"'a_{n}'" for n, _ in ins) + ')')
    wf = []
    for n, (i, wave, env, rel, arp, vib) in ins:
        fl = (FLAG_NOISE if wave & 4 else 0) | (FLAG_VIB if vib else 0) | HIT.get(n, 0x40 if wave & 4 or n == 'tom' else 0)
        if n in ('lead', 'soft', 'echo', 'arpm', 'arpM', 'arpd', 'bass', 'pluck'):
            fl &= 0x0f
        wf.append((wave & 3) | fl << 8)
    data('ins_wf', 'words(' + ','.join(map(str, wf)) + ')')
    data('ntab', 'words(' + ','.join(map(str, notes_table())) + ')')

    w = f.write
    w('#VCPUv4\n# generated by tools/song.py: do not edit\n\n')
    w(f'SONG_SPEED = {SPEED}\n\n')
    for i, (name, body) in enumerate(frags):
        w(f'def d{i}():\n    label({name!r}); {body}\n')
    w('\ncode = [\n')
    for i, (name, body) in enumerate(frags):
        w(f"    ('EXPORT', {name!r}), ('DATA', {name!r}, d{i}, 0, 1),\n")
        if name == 'ntab':
            w("    ('PLACE', 'ntab', 0x0200, 0x02fa),\n")
    w(']\nmodule(code=code, name="song.s", cpu=4)\n')


if __name__ == '__main__':
    with open(sys.argv[1], 'w') as f:
        emit_s(f)
    print(f'{BARS} bars = {BARS * 16 * SPEED / 60:.1f} s, {len(PATS)} patterns, '
          f'{sum(len(p) for p in PATS.values())} pattern bytes')
