#VCPUv4
# 4-channel music player in vCPU assembly (glcc/glink syntax, ROM v4).
#
# Everything is unrolled per channel so every field has a constant zero-page address.
# Per frame and channel: envelope (or release), wavA = vol ^ 127 (clip level = volume),
# wavX (noise channels reshuffle the top bits from the entropy bytes), arpeggio step,
# key from the note table; vibrato on channel 1. Every SONG_SPEED frames: next row.
#
# Channel block in zero page (12 bytes): vol rel note rows wav flg env:2 arp:2 pat:2
# Cold block in RAM (4 bytes):           ord:2 trans inst

SONG_SPEED = 6                                     # must match tools/song.py

T, W, P, Q, D = 0x30, 0x32, 0x34, 0x36, 0x38       # loader area: free once the program runs
RELSTEP = [6, 4, 10, 8]
ENTROPY = 0x06
SOUNDTIMER = 0x2c

def scope():

    def Z(k, o):
        return v('pl_zp') + 12 * k + o

    def C(k, o):
        return v('pl_cold') + 4 * k + o

    def hot(k):
        vol, rel, note, wav, flg, env, arp = [Z(k, o) for o in (0, 1, 2, 4, 5, 6, 8)]
        L = lambda s: f'.{s}{k}'
        # volume: envelope step (0xff = hold) or linear release
        LD(rel); _BNE(L('r'))
        LDW(env); PEEK(); ST(T); XORI(255); _BEQ(L('vd'))
        LD(T); ST(vol); INC(env); _BRA(L('vd'))
        label(L('r'))
        LD(vol); SUBI(RELSTEP[k]); _BGE(L('r1')); LDI(0)
        label(L('r1')); ST(vol)
        label(L('vd'))
        # wavA:wavX
        LD(vol); XORI(127); ST(W)
        LD(flg); ANDI(1); _BEQ(L('nn'))
        LD(ENTROPY); ANDI(0xfc); _BRA(L('wx'))
        label(L('nn')); LD(wav)
        label(L('wx')); ST(W + 1)
        LDWI(0x1fa + 0x100 * k); STW(P); LDW(W); DOKE(P); INC(P); INC(P)
        # arpeggio: semitones per frame, 0x80|d = jump back d bytes
        LDW(arp); PEEK(); ST(T); ANDI(0xc0); XORI(0x80); _BNE(L('an'))
        LD(T); ANDI(0x3f); STW(Q); LD(arp); SUBW(Q); ST(arp); LDW(arp); PEEK(); ST(T)
        label(L('an')); INC(arp)
        LD(T); ADDW(note); ANDI(255); LSLW(); STW(Q); LDWI('ntab'); ADDW(Q); DEEK()
        if k == 0:
            # vibrato after 16 frames: +-(keyH>>2) or twice that, on the 15-bit key
            STW(W)
            LD(flg); ANDI(2); _BEQ('.novib')
            LD(v('pl_age')); SUBI(16); _BLT('.novib')
            LD(v('pl_age')); ANDI(3); _BEQ('.novib')
            LD(W + 1); ORI(3); ST(Q); LDI(7); ST(Q + 1); LDW(Q); PEEK(); STW(D)   # keyH >> 2 (sawtooth table)
            LD(v('pl_age')); ANDI(1); _BNE('.v1'); LDW(D); LSLW(); STW(D)
            label('.v1')
            LD(v('pl_age')); ANDI(4); _BEQ('.v2'); LDI(0); SUBW(D); STW(D)
            label('.v2')
            LD(W); ADDW(D); STW(Q); _BLT('.vneg')
            SUBI(128); _BLT('.vdone')
            ST(W); INC(W + 1); _BRA('.vdone')
            label('.vneg')
            ADDI(128); ST(W); LD(W + 1); SUBI(1); ST(W + 1); _BRA('.vdone')
            label('.novib')
            label('.vdone')
            INC(v('pl_age'))
            LDW(W)
        DOKE(P)

    def code_parse():
        # pl_parse: next event of one channel, shared by the 4 channels (runs once per note).
        # R16 = its zero-page block, R17 = its cold block, R21 = channel number.
        CP, CC, VAL, ADR, PP = R16, R17, R18, R19, R20
        def rdw(o): LDW(CP); ADDI(o); DEEK()
        def wr(o):  STW(VAL); LDW(CP); ADDI(o); STW(ADR); LDW(VAL); POKE(ADR)
        def wrw(o): STW(VAL); LDW(CP); ADDI(o); STW(ADR); LDW(VAL); DOKE(ADR)
        label('pl_parse')
        PUSH()
        label('.nx')
        rdw(10); STW(PP); PEEK(); ST(T); LDW(PP); ADDI(1); wrw(10)
        LD(T); XORI(255); _BNE('.ne')
        # end of pattern: next order entry (0xfe lo hi = continue at, 0xff = end of song)
        label('.o')
        LDW(CC); DEEK(); STW(Q); PEEK(); ST(D); XORI(0xfe); _BNE('.o2')
        LDW(Q); ADDI(1); DEEK(); DOKE(CC); _BRA('.o')
        label('.o2')
        LD(D); XORI(0xff); _BNE('.o3')
        LDWI('p_stop'); wrw(10); _BRA('.nx')
        label('.o3')
        LD(D); LSLW(); STW(D); LDWI('song_pats'); ADDW(D); DEEK(); wrw(10)
        LDW(CC); ADDI(2); STW(ADR); LDW(Q); ADDI(1); PEEK(); POKE(ADR)
        LDW(Q); ADDI(2); DOKE(CC)
        _BRA('.nx')
        label('.ne')
        LD(T); ANDI(0x80); _BEQ('.ev')
        LDW(CC); ADDI(3); STW(ADR); LD(T); ANDI(0x7f); POKE(ADR); _BRA('.nx')
        label('.ev')
        rdw(10); STW(PP); PEEK(); wr(3); LDW(PP); ADDI(1); wrw(10)
        LD(T); _BNE('.on')
        LDI(1); wr(1); _BRA('.end')
        label('.on')
        LDW(CC); ADDI(2); PEEK(); STW(D); LD(T); ADDW(D); wr(2)
        LDW(CC); ADDI(3); PEEK(); LSLW(); STW(Q)
        LDWI('ins_env'); ADDW(Q); DEEK(); wrw(6)
        LDWI('ins_arp'); ADDW(Q); DEEK(); wrw(8)
        LDWI('ins_wf'); ADDW(Q); DEEK(); wrw(4)
        LDI(0); wr(1)
        LD(R21); _BNE('.nz'); ST(v('pl_age'))
        label('.nz')
        LD(R21); XORI(3); _BNE('.end')
        LDW(CP); ADDI(5); PEEK(); ANDI(0xf0); ORW('song_hit'); ST('song_hit')
        label('.end')
        POP(); RET()

    def code_tick():
        label('player_tick')
        PUSH()                                  # long jumps between holes trash vLR
        LDI(255); ST(SOUNDTIMER)
        LD(v('pl_tick')); SUBI(1); ST(v('pl_tick')); _BNE('.frame')
        LDI(SONG_SPEED); ST(v('pl_tick'))
        LDW('song_row'); ADDI(1); STW('song_row')
        for k in range(4):
            LD(Z(k, 3)); SUBI(1); ST(Z(k, 3)); _BNE(f'.skip{k}')
            LDWI(Z(k, 0)); STW(R16); LDWI(C(k, 0)); STW(R17); LDI(k); STW(R21); _CALLJ('pl_parse')
            label(f'.skip{k}')
        label('.frame')
        for k in range(4):
            hot(k)
        tryhop(2); POP(); RET()

    def code_init():
        # BSS (zero page and cold blocks) is already cleared by the C runtime
        CP, CC, OP, A = R16, R17, R18, R19
        label('player_init')
        PUSH()
        LD('channelMask_v4'); ORI(3); ST('channelMask_v4')
        LDWI(v('pl_zp')); STW(CP); LDWI(v('pl_cold')); STW(CC); LDWI('song_ord0'); STW(OP)
        label('.i')
        LDW(OP); DEEK(); DOKE(CC)                                        # order list
        LDW(CP); ADDI(10); STW(A); LDWI('p_stop'); ADDI(2); DOKE(A)       # pattern: a 0xff
        LDW(CP); ADDI(6); STW(A); LDWI('e_kick'); ADDI(10); DOKE(A)       # envelope: 0 then hold
        LDW(CP); ADDI(8); STW(A); LDWI('a_kick'); DOKE(A)
        LDW(CP); ADDI(3); STW(A); LDI(1); POKE(A)                         # rows
        LDW(CP); ADDI(1); STW(A); LDI(1); POKE(A)                         # released
        LDW(CP); ADDI(12); STW(CP); LDW(CC); ADDI(4); STW(CC); LDW(OP); ADDI(2); STW(OP)
        LD(CP); XORI((v('pl_zp') + 48) & 255); _BNE('.i')
        LDI(1); ST(v('pl_tick'))
        LDWI(-1); STW('song_row')
        LDI(0); ST('song_hit')
        tryhop(2); POP(); RET()

    def bss_zp():
        label('pl_zp'); space(48)
    def bss_misc():
        label('pl_tick'); space(1)
        label('pl_age'); space(1)
    def bss_row():
        label('song_row'); space(2)
    def bss_hit():
        label('song_hit'); space(2)
    def bss_cold():
        label('pl_cold'); space(16)

    imports = [('IMPORT', x) for x in ('p_stop', 'song_pats', 'ins_env', 'ins_arp', 'ins_wf', 'ntab',
                                       'song_ord0', 'e_kick', 'a_kick', 'channelMask_v4')]
    return imports + [('EXPORT', 'player_tick'), ('CODE', 'player_tick', code_tick),
            ('CODE', 'pl_parse', code_parse),
            ('EXPORT', 'player_init'), ('CODE', 'player_init', code_init),
            ('BSS', 'pl_zp', bss_zp, 48, 1), ('PLACE', 'pl_zp', 0x00, 0xff),
            ('BSS', 'pl_tick', bss_misc, 2, 1), ('PLACE', 'pl_tick', 0x00, 0xff),
            ('EXPORT', 'song_row'), ('BSS', 'song_row', bss_row, 2, 1), ('PLACE', 'song_row', 0x00, 0xff),
            ('EXPORT', 'song_hit'), ('BSS', 'song_hit', bss_hit, 2, 1), ('PLACE', 'song_hit', 0x00, 0xff),
            ('BSS', 'pl_cold', bss_cold, 16, 1)]

module(code=scope(), name='player.s', cpu=4)

# Local Variables:
# mode: python
# indent-tabs-mode: ()
# End:
