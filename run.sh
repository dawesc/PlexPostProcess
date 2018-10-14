#!/usr/local/bin/bash

cd /mnt/PlexRecordings
export MYPID=`ps auwwx | grep python | grep -v grep | awk '{ print $2 }'`
echo Start to scan PID "$MYPID"
#cd /mnt/PlexRecordings/sat/PlexPostProcess
#python3.6 -m com.camding.plexpostprocess.PlexPostProcess /mnt/PlexRecordings/Movies /mnt/PlexRecordings/TV
kill -USR1 $MYPID
echo Script complete
true
