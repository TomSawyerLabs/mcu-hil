# Shared Settings for GitHub Action Runner Pre/Post Scripts

set -e

# cd to same dir as script
cd "$(dirname "$0")"

SYS_GPIO=/sys/class/gpio


Export_GPIO_Delay=0.05 # Maybe a little short?
Export_GPIO_Delay=0.07

GPIO_Lock=26
GPIO_VCC=27
GPIO_UVCC=18
GPIO_Reset=13
GPIO_Reset_Pull=19
GPIO_HWB=2
GPIO_HWB_Pull=3
GPIO_SPI_Disable=5
GPIO_Serial_Disable=8

function waitExport {
    sleep ${Export_GPIO_Delay}
}

function setGPIO {
    # Set GPIO to output and set value
    # $1: GPIO to set
    # $2: Value to set
    echo $1 > ${SYS_GPIO}/export 2> /dev/null && waitExport || :
    
    Path=${SYS_GPIO}/gpio${1}

    echo out > ${Path}/direction
    echo $2 > ${Path}/value
}

function releaseGPIO {
    # Release GPIO
    # $1: GPIO to release
    echo $1 > ${SYS_GPIO}/unexport 2> /dev/null && waitExport || :
}