#!/bin/sh

# Get and extract raw data from original source.
# This is a large file, be sure you have at least 16GB available.

wget --output-file='r4.2.tar.bz2' https://kilthub.cmu.edu/ndownloader/files/24856766
tar -xjvf 'r4.2.tar.bz2'

# The result is a folder, r4.2, containing the CSVs. Move them into the root of the repository
# for the original script to work.
