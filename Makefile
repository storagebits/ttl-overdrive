# TTL OVERDRIVE: a Gigatron demo (32K, ROM v4).
# Needs glcc (https://github.com/lb3361/gigatron-lcc), built and installed somewhere:
#   gmake GLCC=/path/to/glcc ROM=/path/to/gigatron-lcc/gigatron/roms/v4.rom
# Python 3 with Pillow regenerates the graphics, pyserial sends to a real Gigatron.
GLCC ?= third_party/glcc-install/bin/glcc
ROM  ?= third_party/gigatron-lcc/gigatron/roms/v4.rom
PY   ?= python3
SENDFILE ?= third_party/gigatron-rom/Utils/sendFile.py
PORT ?= /dev/cu.usbmodem111301
SRCS  = main.c fx.s player.s song.s gfx.s
SHOT  = tools/gtshot

all: overdrive.gt1

overdrive.gt1: build/overdrive.gt1
	cp $< $@

src/song.s: tools/song.py
	$(PY) tools/song.py $@

src/gfx.s: tools/gfx.py
	$(PY) tools/gfx.py $@

build/overdrive.gt1: $(addprefix src/,$(SRCS)) src/demomap.py src/player.h
	mkdir -p build && cd src && ../$(GLCC) -rom=v4 -map=32k,./demomap.py -O $(SRCS) -o ../$@ --frags > ../build/overdrive.frags

$(SHOT): tools/gtshot.c
	cc -O2 -o $@ $<

# full capture: video with LEDs, 4-bit audio, muxed
video: build/overdrive.gt1 $(SHOT)
	mkdir -p media
	$(SHOT) $(ROM) build/overdrive.gt1 w0.3 Fbuild/v.mp4 abuild/a.wav w$(or $(SECS),116)
	ffmpeg -loglevel error -y -i build/v.mp4 -i build/a.wav -c:v copy -c:a aac -b:a 192k media/overdrive.mp4
	@ls -la media/overdrive.mp4

# send to the real Gigatron (Loader selected in the menu, BabelFish on the Arduino)
send: build/overdrive.gt1
	$(PY) $(SENDFILE) -p $(PORT) build/overdrive.gt1

.PHONY: all video send
