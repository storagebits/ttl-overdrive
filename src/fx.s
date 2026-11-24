#VCPUv4
# Effect inner loops in vCPU assembly (glcc/glink syntax, ROM v4).
#
# vt_blitn(src, dst, n): n Sprite6 chunks from src into the videoTable at dst. One chunk is
#   (page, dX) x 3 followed by 0xff: the ROM's SYS_Sprite6 copies 6 bytes natively and the
#   terminator steps dst by 6. The SYS instructions are unrolled: we jump into the block.
# vt_commit(...): see below. lbuf: one page byte per row, built by the scenes (Sprite6 works
#   there too: chunks of 6 rows).

T, U = 0x3a, 0x3c          # loader area (the player uses 0x30-0x39)
CNT, PREV = 0x3e, 0x40
STRIPS = 0x5c

def scope():

    def code_blit():
        label('vt_blitn')                     # R8 src, R9 dst, R10 n (1..40)
        PUSH()
        LDWI('SYS_Sprite6_v3_64'); STW('sysFn')
        LDW(R8); STW('sysArgs0')
        LD(R10); LSLW(); STW(T)
        LDWI('.sysend'); SUBW(T); STW(T)
        LDW(R9); CALL(T)
        POP(); RET()

    def code_block():
        nohop()
        label('.sysblock')
        for i in range(40):
            SYS(64)
        label('.sysend')
        RET()

    def code_band():
        # band_words(pages, table:phase, step, n, base): bwbuf[i] = pages[i] | dX << 8 for the
        # absolute offsets base + wob[phase + i*step], then bwbuf[n] high byte = the dX that takes
        # the offset back to 0 on the row after the band.
        BP = R13
        WW = R14
        label('band_words')                   # R8 pages, R9 table:phase, R10 step, R11 n, R12 base
        PUSH()
        LDWI('bwbuf'); STW(BP)
        LDW(R9); STW(U); LDI(0); STW(PREV)
        LD(R11); _BEQ('.bz')
        label('.bw')
        LDW(U); PEEK(); ADDW(R12); STW(T); SUBW(PREV); ST(WW + 1); LDW(T); STW(PREV)
        LDW(R8); PEEK(); ST(WW); INC(R8)
        LDW(WW); DOKE(BP); INC(BP); INC(BP)
        LD(U); ADDW(R10); ST(U)
        LD(R11); SUBI(1); ST(R11); _BNE('.bw')
        label('.bz')
        LDI(0); SUBW(PREV); ST(WW + 1); LDW(WW); DOKE(BP)
        POP(); RET()

    def code_commit():
        # vt_commit(band_y, band_n): the whole videoTable in one pass from the top, about as
        # fast as the beam, so started in vertical blank it stays ahead of it. Rows outside
        # the band: lbuf (page, dX = 0). Band rows: bwbuf. Next row: lbuf page, bwbuf[n] dX.
        V, LP, BP, E = R13, R14, R15, R12
        label('vt_commit')                    # R8 band_y, R9 band_n
        PUSH()
        LDWI(0x100); STW(V); LDWI('lbuf'); STW(LP); LDWI('bwbuf'); STW(BP); LDI(0); STW(E)
        def lrow():
            LDW(LP); PEEK(); DOKE(V); INC(LP); INC(V); INC(V)
        def brow():
            LDW(BP); DEEK(); DOKE(V); INC(BP); INC(BP); INC(V); INC(V); INC(LP)
        # rows above the band, two at a time
        LD(R8); _BEQ('.c1'); ANDI(1); _BEQ('.a0'); lrow()
        label('.a0')
        LD(R8); LSLW(); ST(E); LD(V); XORW(E); _BEQ('.c1')
        label('.a')
        lrow(); lrow()
        LD(V); XORW(E); _BNE('.a')
        label('.c1')
        # band rows
        LD(R9); _BEQ('.c2'); ANDI(1); _BEQ('.b0'); brow()
        label('.b0')
        LD(R9); LSLW(); ADDW(R8); ADDW(R8); ST(E); LD(V); XORW(E); _BEQ('.c2')
        label('.b')
        brow(); brow()
        LD(V); XORW(E); _BNE('.b')
        label('.c2')
        LD(V); XORI(0xf0); _BEQ('.done')
        LDW(BP); ADDI(1); PEEK(); ST(T + 1); LDW(LP); PEEK(); ST(T); LDW(T); DOKE(V); INC(LP); INC(V); INC(V)
        # the rest, two at a time
        LD(V); XORI(0xf0); _BEQ('.done'); ANDI(2); _BEQ('.d')
        lrow()
        label('.d')
        LD(V); XORI(0xf0); _BEQ('.done')
        lrow(); lrow(); _BRA('.d')
        label('.done')
        POP(); RET()

    def code_strip():
        # gen_strip(runs, pal, page, k): one 256-byte strip page from runs (len, level), 0-ended:
        # colour pal[(level + k) & 31], filled natively by SYS_SetMemory.
        label('gen_strip')                    # R8 runs, R9 pal, R10 page, R11 k
        PUSH()
        LDWI('SYS_SetMemory_v2_54'); STW('sysFn')
        LDI(0); ST(T)
        label('.g')
        LDW(R8); PEEK(); _BEQ('.gd'); ST('sysArgs0'); ST(U)
        INC(R8); LDW(R8); PEEK(); ADDW(R11); ANDI(31); ADDW(R9); PEEK(); ST('sysArgs1'); INC(R8)
        LD(T); ST('sysArgs2'); LD(R10); ST('sysArgs3')
        SYS(54)
        LD(T); ADDW(U); ST(T)
        _BRA('.g')
        label('.gd')
        POP(); RET()

    def code_plasma():
        # plasma_rows(p1, p2): every row = strip page f1[i] + f2[j], dX from f1 (word table);
        # all strips are full pages, so the cumulative offsets never show garbage.
        V, W = R13, R10
        label('plasma_rows')                  # R8 &f1d[i] (word table, page 0x7c), R9 &f2[j]
        PUSH()
        LDWI(0x100); STW(V)
        label('.p')
        LDW(R9); PEEK(); STW(W)
        LDW(R8); DEEK(); ADDW(W); DOKE(V)
        INC(R8); INC(R8); INC(R9); INC(V); INC(V)
        LD(V); XORI(0xf0); _BNE('.p')
        POP(); RET()

    def code_spans():
        # gen_spans(prog): one page of a span program, returns the next entry (0 at the end).
        # Entry: page, count (0 = 256), background, n, then n x (x, len, colour).
        P_, N_ = R8, R11
        label('gen_spans')                    # R8 prog
        PUSH()
        LDWI('SYS_SetMemory_v2_54'); STW('sysFn')
        LDW(P_); PEEK(); _BEQ('.sx'); ST(R10)          # page
        INC(P_); LDW(P_); PEEK(); ST('sysArgs0')
        INC(P_); LDW(P_); PEEK(); ST('sysArgs1')
        LDI(0); ST('sysArgs2'); LD(R10); ST('sysArgs3'); SYS(54)
        INC(P_); LDW(P_); PEEK(); ST(N_)
        label('.sl')
        LD(N_); _BEQ('.se')
        INC(P_); LDW(P_); PEEK(); ST('sysArgs2'); LD(R10); ST('sysArgs3')
        INC(P_); LDW(P_); PEEK(); ST('sysArgs0')
        INC(P_); LDW(P_); PEEK(); ST('sysArgs1'); SYS(54)
        LD(N_); SUBI(1); ST(N_); _BRA('.sl')
        label('.se')
        LDW(P_); ADDI(1); _BRA('.sr')
        label('.sx')
        LDI(0)
        label('.sr')
        POP(); RET()

    def code_grid():
        # grid_rows(camz, xv): rows 0-59 from lbuf (sky, dX 0), rows 60-119 the perspective
        # ground: a grid strip per row, or a line page when z + camz crosses a multiple of 32
        # between this row and the previous one; lateral shear xv (8.8) per row.
        V, LP, ZP, ACC, OLDZ, W = R13, R14, R15, R16, R17, R18
        label('grid_rows')                    # R8 camz, R9 xv
        PUSH()
        LDWI(0x100); STW(V); LDWI('lbuf'); STW(LP)
        label('.gs')
        LDW(LP); PEEK(); DOKE(V); INC(LP); INC(V); INC(V)
        LD(V); XORI(120); _BNE('.gs')
        LDWI('grid_z'); STW(ZP); LDWI(48 << 8); STW(ACC); LDI(0); STW(PREV)
        LDWI('grid_lev'); STW(LP); LDWI('grid_lin'); STW(R19)
        LDW(ZP); PEEK(); ADDW(R8); ST(OLDZ)
        label('.gr')
        LDW(ZP); PEEK(); ADDW(R8); ST(T); XORW(OLDZ); ANDI(0xe0); _BEQ('.gn')
        LDW(R19); PEEK(); _BRA('.gp')
        label('.gn')
        LDW(LP); PEEK()
        label('.gp')
        ST(W); LD(T); ST(OLDZ)
        LDW(ACC); ADDW(R9); STW(ACC); LD(ACC + 1); STW(T); SUBW(PREV); ST(W + 1); LDW(T); STW(PREV)
        LDW(W); DOKE(V); INC(V); INC(V); INC(ZP); INC(LP); INC(R19)
        LD(V); XORI(0xf0); _BNE('.gr')
        POP(); RET()

    def code_twist():
        # twist_rows(ang, tw, dphase): row y shows slice ((ang + y*tw) >> 8) & 31 (8.8 angles),
        # dX from the sway delta table at page 0x7f. Full pages: offsets never show garbage.
        V, W, DP = R13, R14, R15
        label('twist_rows')                   # R8 ang (8.8), R9 tw (8.8), R10 dphase
        PUSH()
        LDWI(0x100); STW(V); LD(R10); ST(DP); LDI(0x7f); ST(DP + 1)
        label('.tr')
        LD(R8 + 1); ANDI(31); ADDI(STRIPS); ST(W)
        LDW(DP); PEEK(); ST(W + 1); INC(DP)
        LDW(W); DOKE(V); INC(V); INC(V)
        LDW(R8); ADDW(R9); STW(R8)
        LD(V); XORI(0xf0); _BNE('.tr')
        POP(); RET()

    def code_col():
        # scroll_col(x, bits): one pixel column of the scroller, font rows 0-7 in strip pages
        # STRIPS..STRIPS+7, colour scroll_cols[r] where bit r is set, else black.
        A, CP, M = R13, R14, R15
        label('scroll_col')                   # R8 x, R9 bits
        PUSH()
        LD(R8); ST(A); LDI(STRIPS); ST(A + 1); LDWI('scroll_cols'); STW(CP); LDI(1); STW(M)
        label('.sc')
        LD(R9); ANDW(M); _BEQ('.s0')
        LDW(CP); PEEK()
        label('.s0')
        POKE(A); INC(A + 1); INC(CP); LDW(M); LSLW(); STW(M)
        LD(A + 1); XORI(STRIPS + 8); _BNE('.sc')
        POP(); RET()

    def bss_bw():
        label('bwbuf'); space(82)

    def bss_lbuf():
        label('lbuf'); space(132)

    return [('IMPORT', 'logo_pages'), ('IMPORT', 'wob'), ('IMPORT', 'grid_z'), ('IMPORT', 'grid_lev'),
            ('IMPORT', 'grid_lin'), ('IMPORT', 'scroll_cols'),
            ('EXPORT', 'vt_blitn'), ('CODE', 'vt_blitn', code_blit),
            ('CODE', '.sysblock', code_block),
            ('EXPORT', 'vt_commit'), ('CODE', 'vt_commit', code_commit),
            ('EXPORT', 'band_words'), ('CODE', 'band_words', code_band),
            ('EXPORT', 'gen_strip'), ('CODE', 'gen_strip', code_strip),
            ('EXPORT', 'gen_spans'), ('CODE', 'gen_spans', code_spans),
            ('EXPORT', 'grid_rows'), ('CODE', 'grid_rows', code_grid),
            ('EXPORT', 'twist_rows'), ('CODE', 'twist_rows', code_twist),
            ('EXPORT', 'scroll_col'), ('CODE', 'scroll_col', code_col),
            ('EXPORT', 'plasma_rows'), ('CODE', 'plasma_rows', code_plasma),
            ('EXPORT', 'bwbuf'), ('BSS', 'bwbuf', bss_bw, 82, 1),
            ('EXPORT', 'lbuf'), ('BSS', 'lbuf', bss_lbuf, 132, 1), ('PLACE', 'lbuf', 0x300, 0x3fa)]

module(code=scope(), name='fx.s', cpu=4)

# Local Variables:
# mode: python
# indent-tabs-mode: ()
# End:
