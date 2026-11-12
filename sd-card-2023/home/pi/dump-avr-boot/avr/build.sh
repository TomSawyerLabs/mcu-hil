#!/bin/bash

set -e

# cd to same dir as script
cd "$(dirname "$0")"

avr-gcc -mmcu=atmega8u2 -O2 --whole-program -o dump.elf main.cpp
avr-objcopy -j .text -j .data -O ihex dump.elf dump.hex