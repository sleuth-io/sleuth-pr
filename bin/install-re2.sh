#!/bin/bash

wget https://github.com/google/re2/archive/2020-10-01.zip
unzip 2020-10-01.zip
cd re2-2020-10-01
make
make install