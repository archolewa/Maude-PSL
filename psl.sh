#!/bin/bash

if [ $# -eq 0 ] 
then
    echo "Usage: ./psl.sh FILENAME.psl"
else
    pslFile=$1
    ./psl.py $pslFile
    maudeExtension="maude"
    pslExtension=".psl"
    maudeFile="${pslFile/psl/$maudeExtension}"
    echo "./maude27 -no-prelude prelude.maude maude-npa.maude $maudeFile"
    ./maude27 -no-prelude prelude.maude maude-npa.maude $maudeFile
fi
