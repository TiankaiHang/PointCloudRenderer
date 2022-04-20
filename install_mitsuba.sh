sudo apt-get update

# ref: https://mitsuba2.readthedocs.io/en/latest/src/getting_started/compiling.html
sudo apt-get install -y clang-9 libc++-9-dev libc++abi-9-dev cmake ninja-build
sudo apt-get install -y libz-dev libpng-dev libjpeg-dev libxrandr-dev libxinerama-dev libxcursor-dev
sudo apt-get install -y python3-dev python3-distutils python3-setuptools
sudo apt-get install -y python3-pytest python3-pytest-xdist python3-numpy
sudo apt-get install -y python3-sphinx python3-guzzle-sphinx-theme python3-sphinxcontrib.bibtex

export CC=clang-9
export CXX=clang++-9

git clone --recursive https://github.com/mitsuba-renderer/mitsuba2
cd mitsuba2/

mkdir build
cd build/

cmake -GNinja ..
ninja

cd dist/
export PATH=$PWD:$PATH