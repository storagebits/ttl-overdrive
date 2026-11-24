#ifndef PLAYER_H
#define PLAYER_H
#include <gigatron/sys.h>
/* src/player.s: 4-channel music player (vCPU assembly), song data in src/song.s */
void player_init(void);
void player_tick(void);              /* once per frame */
extern __near int song_row;          /* rows since the start (16 a bar), -1 before the first */
extern __near byte song_hit;         /* drum hits since cleared: 0x10 kick, 0x20 snare, 0x40 other */
#endif
