#!/bin/bash -e

# Load shared settings
source "/opt/action-scripts/shared.sh"

# if no args, do reset sequence
if [ $# -eq 0 ]
then
  $0 0
  $0 1
  releaseGPIO ${GPIO_Reset}
  exit 0
fi

# $1: Value to set
setGPIO ${GPIO_Reset} $1
sleep 0.05
