# Cleanup script for GitHub Actions Runner
# Also mush unlock lock file
# We use gpio26 as the "lock file"

source "$(dirname "$0")/shared.sh"

# if ${GPIO_Path} doesn't exit, something is wrong. Exit with a message
if [ ! -d ${GPIO_Path} ]
then
    echo "GPIO not open. Something is wrong."
    exit 1
fi

# Release lock (and GPIO)
echo "Releasing lock"
setGPIO ${GPIO_Lock} 0 2> /dev/null || :
echo ${GPIO_Lock} > ${SYS_GPIO}/unexport
