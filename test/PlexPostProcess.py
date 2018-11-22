#!/opt/local/bin/python3
# encoding: utf-8

import os, sys

from com.camding.plexpostprocess.steps.DetermineFilename import DetermineFilename
from com.camding.plexpostprocess.ScannedFile import ScannedFile

def main(): # IGNORE:C0111
  tmp = DetermineFilename(None)
  tmp2 = ScannedFile({
    'state': 'INITIAL',
    'filename': '/mnt/PlexRecordings/TV/Coronation Street (1960)/Season 2018/Coronation Street (1960) - 2018-11-21 11 30 00 - Episode 11-21.ts',
    'id': 3912,
    'filetype': 'm4v',
    'creationDate': '2018-11-21 19:59:56'
  })
  
  
  tmp.SetPlexLibraryPath(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "com.plexapp.plugins.library.db"))
  print(tmp.GetDestFilename(tmp2))
  
if __name__ == "__main__":
  sys.exit(main())
