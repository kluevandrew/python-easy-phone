#!/bin/bash

cd /tmp
wget http://www.pjsip.org/release/2.7.2/pjproject-2.7.2.tar.bz2
tar xjvf pjproject-2.7.2.tar.bz2
cd /tmp/pjproject-2.7.2
./configure CFLAGS='-O3 -fPIC'
make dep && make && make install
cd /tmp/pjproject-2.7.2/pjsip-apps/src/python
python ./setup.py install
rm -f /tmp/pjproject-2.7.2.tar.bz2
rm -rf /tmp/pjproject-2.7.2