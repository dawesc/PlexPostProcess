#!/usr/local/bin/bash

cd /mnt/PlexRecordings/sat/PlexPostProcess
echo Running PlexPostProcessDaemon "$@"
/usr/local/bin/python3.6 -m com.camding.plexpostprocess.PlexPostProcessDaemon "$@"
echo Running PlexPostProcessDaemon "$@" result "$?"