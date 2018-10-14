#!/usr/bin/env python3.6
 
import sys

from com.camding.plexpostprocess.Daemon import Daemon
from com.camding.plexpostprocess.PlexPostProcessShared import PlexPostProcessShared
from com.camding.plexpostprocess.Settings import Settings
 
class PlexPostProcessDaemon(Daemon):
  def __init__(self, pidfile):
    Daemon.__init__(self, pidfile)
    self.__config = []
    if len(sys.argv) >= 3:
      configFile = sys.argv[2]
      with open(configFile, 'r+') as configFileStream:
        self.__config = configFileStream.read().splitlines()
    self.__config.append('--daemon')
            
  def run(self):
    PlexPostProcessShared().mainWithArgs(self.__config)
 
if __name__ == "__main__":
  daemon = PlexPostProcessDaemon(Settings.GetConfig('Paths','daemonLinePidFile','/tmp/daemon_plex_post_process.pid'))
  if len(sys.argv) > 1:
    if 'start' == sys.argv[1]:
      daemon.start()
    elif 'stop' == sys.argv[1]:
      daemon.stop()
    elif 'restart' == sys.argv[1]:
      daemon.restart()
    elif 'status' == sys.argv[1]:
      print('Current state: ' + daemon.status().name)
    else:
      print("Unknown command '" + sys.argv[1] + "'")
      sys.exit(2)
    sys.exit(0)
  else:
    print("usage: %s start|stop|restart|status" % sys.argv[0])
    sys.exit(2)