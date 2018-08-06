#!/bin/bash -l
set -e
# Install nvm
curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.32.1/install.sh | bash
source $HOME/.bashrc
install node.js v6
nvm install 6
NODE_VER=v6.11.0 npm install

# Cleanup
rm -rf build
mkdir build
mkdir -p build/static-nginx
mkdir -p build/static-nginx/app/static/build/default/src

cp -a static-nginx/app build/static-nginx
echo -e "var client_id = 'foobar';\nvar api_key = 'foobar';" > build/static-nginx/app/static/src/client-id.js

pushd build/static-nginx/app/static
npm install --no-spin bower
npm install --no-spin polymer
PATH=~/eclipse2017/node_modules/.bin:$PATH bower install
polymer build --preset es5-bundled --name default
popd

