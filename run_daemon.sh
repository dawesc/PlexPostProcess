#!/usr/local/bin/bash

cd /mnt/PlexRecordings/sat/ScanAndTranscode
echo Running ScanAndTranscodeDaemon "$@"
/usr/local/bin/python3.6 -m com.camding.scanandtranscode.ScanAndTranscodeDaemon "$@" /etc/scan_and_transcode
echo Running ScanAndTranscodeDaemon "$@" result "$?"