#!/bin/bash

set -e

# cd to same dir as script
cd "$(dirname "$0")"

# build avr hex from main.c

avr-gcc -mmcu=atmega8u2 -O0 -o main.o -c main.c
avr-gcc -mmcu=atmega8u2 -o app.elf main.o
avr-objcopy -j .text -j .data -O ihex app.elf app.hex