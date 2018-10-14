#!/usr/local/bin/bash

export PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/games:/usr/local/sbin:/usr/local/bin:/root/bin:$PATH
export LD_LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib
unset LANG
unset LC_ALL
unset PLEX_MEDIA_SERVER_APPLICATION_SUPPORT_DIR
unset PLEX_MEDIA_SERVER_HOME
unset PLEX_MEDIA_SERVER_LOG_DIR
unset PLEX_MEDIA_SERVER_MAX_PLUGIN_PROCS
unset PLEX_MEDIA_SERVER_PIDFILE
unset PYTHONHOME
unset SCRIPTPATH
unset SUPPORT_PATH

realname=`echo "$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"`
filename=$(basename "$realname")

LogFile=/tmp/postProcessPlex.$filename.log
PlexCommskip=/usr/local/PlexComskip/PlexComskip.py  #Path to Plex Comskip python script
filenameCheck=`echo $1 | tail -c 5`
OriginalBackupLocation=/mnt/PlexRecordings/BackupMP2  # Location where you would want to have a backup of original file before comskip and handbrake
HandbrakeCLI=/usr/local/bin/HandBrakeCLI

# Remove Commercials
$PlexCommskip "$realname"

