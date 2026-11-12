# Load shared settings
source "$(dirname "$0")/shared.sh"

# Get GPIO (and lock)
while [ true ]
do
    echo ${GPIO_Lock} > ${SYS_GPIO}/export 2> /dev/null && break
    [ -z "$first" ] && first=1 && echo "Waiting for lock..."
    sleep 1
done
echo "Lock acquired"
waitExport && setGPIO ${GPIO_Lock} 1 &
trap wait EXIT

# Enable power to AVR
setGPIO ${GPIO_VCC} 1 &
setGPIO ${GPIO_UVCC} 1 &

# Enable bootloader
setGPIO ${GPIO_HWB} 0 &
setGPIO ${GPIO_HWB_Pull} 0 &

# Set Reset Pull
setGPIO ${GPIO_Reset_Pull} 1 &

# Enable SPI/ISP interface driver
setGPIO ${GPIO_SPI_Disable} 0 &

# Enable Serial interface driver
setGPIO ${GPIO_Serial_Disable} 0 &

# TODO: Other setup stuff
# TODO: Reset flash?

# echo AVRUDE: $AVRDUDE

# echo Target: $TARGET
