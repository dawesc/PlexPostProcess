#!/usr/bin/env python3.6
 
import sys, time

from com.camding.scanandtranscode.Daemon import Daemon
from com.camding.scanandtranscode.ScanAndTranscodeShared import ScanAndTranscodeShared
 
class ScanAndTranscodeDaemon(Daemon):
  def __init__(self, pidfile):
    Daemon.__init__(self, pidfile)
    self.__config = []
    if len(sys.argv) >= 3:
      configFile = sys.argv[2]
      with open(configFile, 'r+') as file:
        self.__config = file.read().splitlines()
        self.__config.append('--daemon')
            
  def run(self):
    ScanAndTranscodeShared().mainWithArgs(self.__config)
 
if __name__ == "__main__":
  daemon = ScanAndTranscodeDaemon('/tmp/scan_and_transcode.pid')
  if len(sys.argv) == 3:
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