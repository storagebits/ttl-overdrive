/* TTL OVERDRIVE: a Gigatron demo. Timeline, scenes and glue; inner loops in fx.s,
   music in player.s/song.s, graphics in gfx.s (tools/gfx.py). */
#include <gigatron/sys.h>
#include "player.h"

#define VT ((byte*)0x100)
#define BLACK 0x1c
#define TEXT0 0x20                 /* text rows: pages 0x20-0x37 (visible part) */

extern void vt_blitn(const byte *src, byte *dst, byte n);
extern void vt_commit(byte band_y, byte band_n);
extern void band_words(const byte *pages, unsigned tab_phase, byte step, byte n, byte base);
#define WOB(phase) (0x500 | (byte)(phase))       /* the wobble table */
#define FLAT 0x1c00                              /* the black page: offsets 0 */
#define CENTER 0x500                             /* wob[0] = 48: the logo centred */
__near byte lag;                                 /* frames since the last music() */
extern byte lbuf[], bwbuf[];
extern void gen_strip(const byte *runs, const byte *pal, byte page, byte k);
extern const byte *gen_spans(const byte *prog);
extern void grid_rows(byte camz, int xv);
extern void twist_rows(unsigned ang, int tw, byte dphase);
extern void scroll_col(byte x, byte bits);
extern const byte sky_rows[], grid_lv[];
extern const byte *const sky_prog[], *const grid_prog[], *const twist_prog[];
extern void plasma_rows(const void *p1, const byte *p2);
extern const byte logo_pages[], wob[], bary[], fills[], pal32[], plasma_runs[], plasma_f2[];
extern const unsigned plasma_f1d[];
#define STRIPS 0x5c
#define LOGO_N 36
#define WHITE 0x1b
extern const byte *const bars[];

static byte last, t;
static byte band[40];
static const byte *gp;

/* wait for the next frame; the music catches up if a scene was late */
static void frame(void)
{
  byte f = frameCount;            /* always a fresh vertical blank: the commit must not */
  while (f == frameCount) ;       /* start in the middle of a frame */
}
static void music(void)
{
  lag = 0;
  while (last != frameCount) { last++; lag++; player_tick(); }
}
static void leds_hits(void)
{
  xoutMask = (xoutMask & 0xf0) | ((song_hit >> 4) & 15);
  song_hit = 0;
}
#define BAR (song_row >> 4)

/* ---------------------------------------------------------------- text (ROM font) */
static byte *cur;
static void put_char(char c)
{
  unsigned fp; byte i;
  if (c < 82) fp = 0x700 + (c - 32) * 5; else fp = 0x800 + (c - 82) * 5;
  for (i = 0; i < 5; i++) SYS_VDrawBits(0x3f00, SYS_Lup(fp + i), cur + i);
  SYS_VDrawBits(0, 0, cur + 5);
  cur += 6;
}

static const char *const boot[] = { "GIGATRON 32K, ROM V4.", "NO MICROPROCESSOR.", "LET'S OVERDRIVE IT.", 0 };

/* ---------------------------------------------------------------- scenes */
static void fill_pages(void)
{
  const byte *f;
  for (f = fills; *f; f += 2) SYS_SetMemory(160, f[1], (void*)(f[0] << 8));
}

static void scene_boot(void)
{
  byte line = 0, y;
  const char *s = boot[0];
  for (y = 0; y < 24; y++) SYS_SetMemory(160, 0, (void*)((TEXT0 + y) << 8));
  SYS_SetMemory(160, 0, (void*)(BLACK << 8));
  SYS_SetMemory(120, BLACK, lbuf);
  for (y = 0; y < 24; y++) band[y] = TEXT0 + y;
  cur = (byte*)((TEXT0 << 8) + 4);
  band_words(band, FLAT, 0, 24, 0);
  while (song_row < 64) {
    frame();
    vt_commit(48, 24);
    music();
    if (s && (t & 3) == 0) {
      if (*s) put_char(*s++);
      else { line++; s = boot[line]; cur = (byte*)(((TEXT0 + 8 * line) << 8) + 4); }
    }
    xoutMask = (xoutMask & 0xf0) | (1 << ((t >> 3) & 3));
    t++;
  }
}

static void scene_zoom(void)
{
  /* the logo unfolds from its middle line, 4 bars */
  byte h = 1, y, top = 40; unsigned acc, step;
  fill_pages();
  band_words(band, CENTER, 0, 1, 0);
  while (song_row < 128) {
    frame();
    vt_commit(top, h);
    music();
    leds_hits();
    h = (song_row - 64) * LOGO_N / 48; if (h > LOGO_N) h = LOGO_N; if (h < 1) h = 1;
    top = 60 - (h >> 1);
    step = (LOGO_N << 8) / h; acc = 0;
    for (y = 0; y < h; y++) { band[y] = logo_pages[acc >> 8]; acc += step; }
    band_words(band, CENTER, 0, h, 0);
    t++;
  }
}

/* a white flash while the 32 strips are generated (about 0.4 s), music kept running */
static void flash_strips(const byte *runs, const byte *pal)
{
  byte k;
  SYS_SetMemory(120, WHITE, lbuf);
  band_words(band, FLAT, 0, 0, 0);
  vt_commit(120, 0);
  for (k = 0; k < 32; k++) {
    gen_strip(runs, pal, STRIPS + k, k);
    music();
  }
}

static void white(void)
{
  SYS_SetMemory(120, WHITE, lbuf);
  band_words(band, FLAT, 0, 0, 0);
  vt_commit(120, 0);
}
static void spans(const byte *const *l)
{
  const byte *p;
  for (; *l; l++) for (p = *l; (p = gen_spans(p)); ) music();
}

static void bars8(void)
{
  byte i;
  SYS_SetMemory(120, BLACK, lbuf);
  for (i = 0; i < 8; i++) vt_blitn(bars[i & 3], lbuf + bary[(t + i * 5) & 63], 2);
}

/* ---------------------------------------------------------------- synthwave ground */
static void grid_level(byte L)
{
  const byte *g = grid_lv + (L << 2);
  unsigned sp = g[0] | (g[1] << 8), x, pg = (STRIPS + L) << 8;
  byte w = g[2], c = g[3];
  SYS_SetMemory(0, 0x10, (void*)pg);
  for (x = 128u << 8; x >= (128u << 8) && (x >> 8) + w <= 256; x += sp) SYS_SetMemory(w, c, (void*)(pg | (x >> 8)));
  for (x = (128u << 8) - sp; x < (128u << 8); x -= sp) SYS_SetMemory(w, c, (void*)(pg | (x >> 8)));
}

static void scene_grid(byte end)
{
  byte L, camz = 0; int xv = 0;
  white();
  spans(sky_prog);
  spans(grid_prog);
  for (L = 0; L < 24; L++) { grid_level(L); music(); }
  for (L = 0; L < 60; L++) lbuf[L] = sky_rows[L];
  while (BAR < end) {
    frame();
    grid_rows(camz, xv);
    music();
    leds_hits();
    camz -= 4;
    xv = (wob[t] - 48) << 2;
    t++;
  }
}

/* ---------------------------------------------------------------- twister */
static void scene_twist(byte end)
{
  unsigned ang = 0; int tw; byte d = 0, w;
  white();
  spans(twist_prog);
  while (BAR < end) {
    frame();
    w = wob[t];
    tw = ((w - 48) << 1) + (w - 48);
    twist_rows(ang, tw, d);
    music();
    leds_hits();
    ang += 0x0140; d += 2;
    t++;
  }
}

/* ---------------------------------------------------------------- greetings scroller */
/* about 210 characters: 12 px each at 120 px/s, it ends just before the scene does */
static const char *const text[] = {
  "TTL OVERDRIVE  ***  NO MICROPROCESSOR, JUST TTL AT 6.25 MHZ  ***  ",
  "THE VIDEO, THE SOUND AND THIS DEMO ARE ALL SOFTWARE  ***  ",
  "GREETINGS TO MARCEL & WALTER, AT67, LB3361, PHIL THOMAS ",
  "AND THE GIGATRON FORUM. STAY TTL!", 0 };

static void scene_scroll(byte end)
{
  byte k, cc = 5, scroll = 0, bits = 0, line = 0, by = 44, w; const char *p = text[0]; unsigned fa = 0;
  white();
  fill_pages();
  for (k = 0; k < 8; k++) SYS_SetMemory(0, 0, (void*)((STRIPS + k) << 8));
  for (k = 0; k < 32; k++) band[k] = STRIPS + 7 - (k >> 2);
  band_words(band, FLAT, 0, 32, 0);
  while (BAR < end) {
    frame();
    vt_commit(by, 32);
    music();
    leds_hits();
    for (k = lag; k; k--) {            /* 2 px per elapsed frame, whatever the frame rate */
      if (++cc >= 6) {
        char c = *p++;
        if (!c) { if (text[line + 1]) { p = text[++line]; c = *p++; } else { p--; c = ' '; } }
        cc = 0;
        fa = c < 82 ? 0x700 + (c - 32) * 5 : 0x800 + (c - 82) * 5;
      }
      bits = cc < 5 ? SYS_Lup(fa + cc) : 0;
      scroll += 2;
      scroll_col(scroll + 158, bits);
      scroll_col(scroll + 159, bits);
    }
    bars8();
    w = wob[(t << 1) & 255];
    by = ((w << 3) - w) >> 3;
    bwbuf[1] = scroll; bwbuf[65] = -scroll;    /* flat band: only the first and the closing dX move */
    t++;
  }
}

/* ---------------------------------------------------------------- the end */
static const char *const credits[] = { "TTL OVERDRIVE", "A GIGATRON DEMO, 2026", "DIRECTED BY STORAGEBITS", 0 };

static void scene_end(void)
{
  byte y, line = 0; const char *s;
  white();
  for (y = 0; y < 24; y++) SYS_SetMemory(160, 0, (void*)((TEXT0 + y) << 8));
  SYS_SetMemory(160, 0, (void*)(BLACK << 8));
  SYS_SetMemory(120, BLACK, lbuf);
  for (y = 0; y < 24; y++) band[y] = TEXT0 + y;
  band_words(band, FLAT, 0, 24, 0);
  s = credits[0]; cur = (byte*)((TEXT0 << 8) + 4);
  for (;;) {
    frame();
    vt_commit(48, 24);
    music();
    xoutMask = xoutMask & 0xf0;
    if (s) {
      if (*s) put_char(*s++);
      else { line++; s = credits[line]; cur = (byte*)(((TEXT0 + 8 * line) << 8) + 4); }
    }
    t++;
  }
}

static void scene_plasma(byte end)
{
  byte t1 = 0, t2 = 0;
  flash_strips(plasma_runs, pal32);
  while (BAR < end) {
    frame();
    plasma_rows((const byte*)plasma_f1d + (byte)(t1 << 1), plasma_f2 + t2);
    music();
    leds_hits();
    t1 += 1; t2 -= 3;
    t++;
  }
}

static void scene_copper(byte end)
{
  while (BAR < end) {
    frame();
    vt_commit(42, LOGO_N);
    music();
    leds_hits();
    bars8();
    band_words(logo_pages, WOB(t << 1), 1, LOGO_N, 0);
    t++;
  }
}

int main(void)
{
  *(byte*)0x2e = 1;               /* ledState_v2: we drive the LEDs */
  SYS_SetMode(2);
  player_init();
  last = frameCount;
  scene_boot();
  scene_zoom();
  scene_copper(16);
  scene_plasma(24);
  scene_grid(32);
  scene_twist(48);
  scene_scroll(64);
  scene_end();
  return 0;
}
