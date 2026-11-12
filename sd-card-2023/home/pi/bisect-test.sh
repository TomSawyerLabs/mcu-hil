#!/bin/bash

set -e

git clean -dfqx
./bootstrap.sh
./configure --disable-libusb_1_0
make clean
make -j4

pushd /home/action/runner/_work/dfu-programmer/dfu-programmer
trap popd EXIT


bash /opt/action-scripts/before.sh
function cleanup {
    bash /opt/action-scripts/after.sh
    popd
}
trap cleanup EXIT

DFU=/home/pi/dfu-programmer/src/dfu-programmer npm test usb

