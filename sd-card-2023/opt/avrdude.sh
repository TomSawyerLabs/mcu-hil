#!/bin/bash

set -e

#AVRDUDE="/home/pi/avrdude/build_linux/src/avrdude"
AVRDUDE="/usr/local/bin/avrdude"

part="atmega8u2"
programmer="avr-test-hat"

args=("-c" ${programmer} "-p" ${part})

# Override the default config file
# args+=("-C" "/home/pi/avrdude.conf")

# Fastest working bit clock
args+=("-B" "500kHz")

# TODO: Setup GPIO

function cleanup {
  # TODO: Cleanup GPIO
  :
}
trap cleanup EXIT

$AVRDUDE "${args[@]}" "$@"
