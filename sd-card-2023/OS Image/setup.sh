#!/bin/bash

# If any error happens, why try to continue. Bubble the error.
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

PREFIX="${GREEN}SETUP${NC}"

function debug {
	echo -e "${PREFIX}" "$@"
}

function error {
	echo -e "${PREFIX}" "${RED}ERROR ABOVE${NC}"
	echo -e "${PREFIX}" "Maybe we ran out of space??"
	df -h /
}

function addPackages {
	PACKAGES+=" $@"
}

trap error ERR

# Enable SSHD, without passwords
debug "Enable SSH, without password logins..."
systemctl enable ssh
echo PasswordAuthentication no >> /etc/ssh/sshd_config

debug "Installing Node.js..."
# TODO: Fully respect optional `NODE_VERSION` environment variable
NODE_DOWNLOAD_NODESOURCE_URL=https://deb.nodesource.com/setup_lts.x

if $NODE_USE_NODESOURCE_INSTALL_SCRIPT
then
  debug "Using official Nodesource installer script"
  curl -sL ${NODE_DOWNLOAD_NODESOURCE_URL} --retry 1 | bash -
else
  debug "Manually adding Nodesource to apt"
  if [[ -z "$NODE_VERSION" ]]
	then
    NODE_VERSION=$(curl -sL ${NODE_DOWNLOAD_NODESOURCE_URL} --retry 1 | grep NODEREPO= | sed -E 's/^NODEREPO="([^"]+)"$/\1/g')
  fi

  curl -sL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | gpg --dearmor > /usr/share/keyrings/nodesource.gpg
  cat <<- EOF_NODE > /etc/apt/sources.list.d/nodesource.list
    deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/${NODE_VERSION} buster main
    deb-src [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/${NODE_VERSION} buster main
EOF_NODE

  addPackages nodejs
fi

if $PYTHON3_INSTALL
then
	addPackages python3{,-pip}
fi

addPackages libusb-dev git build-essential

# Update
debug "Update"
apt-get -qq update

debug "Upgrade"
apt-get -qq upgrade -y --auto-remove

# Install Essentials
debug "Installing Packages: ${PACKAGES}"
apt-get -qq install -y --auto-remove ${PACKAGES}
debug "Update Npm"
npm install --global npm

debug "apt clean"
# apt-get -qq clean

debug "Done!"

df -h /