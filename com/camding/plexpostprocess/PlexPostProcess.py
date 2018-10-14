#!/opt/local/bin/python3
# encoding: utf-8

import fcntl, sys

from com.camding.plexpostprocess.PlexPostProcessShared import PlexPostProcessShared
from com.camding.plexpostprocess.PlexPostProcessShared import DEBUG
from com.camding.plexpostprocess.PlexPostProcessShared import TESTRUN
from com.camding.plexpostprocess.PlexPostProcessShared import PROFILE
from com.camding.plexpostprocess.Settings import Settings

def main(argv=None): # IGNORE:C0111
  '''Command line options.'''

  if argv is None:
      argv = sys.argv
  else:
      sys.argv.extend(argv)
  PlexPostProcessShared().mainWithArgs(argv)
    
if __name__ == "__main__":
  if DEBUG:
      sys.argv.append("-v")
      sys.argv.append("-r")
  if TESTRUN:
      import doctest
      doctest.testmod()
  if PROFILE:
      import cProfile
      import pstats
      profile_filename = 'com.camding.plexpostprocess.PlexPostProcess_profile.txt'
      cProfile.run('main()', profile_filename)
      statsfile = open("profile_stats.txt", "wb")
      p = pstats.Stats(profile_filename, stream=statsfile)
      stats = p.strip_dirs().sort_stats('cumulative')
      stats.print_stats()
      statsfile.close()
      sys.exit(0)
  sys.exit(main())

pid_file = Settings.GetConfig('Paths','cmdLinePidFile','/tmp/cmd_plex_post_process.pid')
fp = open(pid_file, 'w')
try:
    fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # another instance is running
    sys.exit(0)