#!/usr/bin/env bash
# Download and Install Node Version Manager
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.6/install.sh | bash

# install node.js 24
nvm install 24
# use node.js 24
nvm use 24

# build, package and run pdf-to-audiobook on Bazzite Linux
#bash linux/bazzite.sh

# build, package and run pdf-to-audiobook on Mint Linux
bash linux/mint.sh
