#!/bin/bash --verbose

# Export all issues from a ditz database as XML and import them into a 
# Bugs Everywhere database.
#
# This script should be run in a directory containing:
#
# 1. a ditz database in a directory called .ditz
# 2. an initialized Bugs Everywhere database in a directory called .be
# 3. the ditz2be_xml.py script

set -e
set -x

./ditz2be_xml.py 2>&1 1>ditz-export.xml | tee ditz2be_xml.log

be import-xml -p -r $(ls -d .be/*-*-* | cut -d/ -f2) ditz-export.xml
