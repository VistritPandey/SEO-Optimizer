#!/bin/sh
set -eu
mkdir -p /tmp/portfolio
cp -R /workspace/. /tmp/portfolio/
ln -s /opt/portfolio/node_modules /tmp/portfolio/node_modules
cd /tmp/portfolio
export NODE_OPTIONS=--openssl-legacy-provider
export PUBLIC_URL=/
export CI=false
npm run build
if [ -d /output ]; then
  cp -R build/. /output/
fi
