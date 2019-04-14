#!/opt/local/bin/python3
# encoding: utf-8
'''
com.camding.plexpostprocess.PlexPostProcess -- This is used to parse the arguments

com.camding.plexpostprocess.PlexPostProcess is a application used to 
make the system plexPostProcess all un-plexPostProcessd files

It defines classes_and_methods

@author:     chrisd

@copyright:  2017 Camding Ltd. All rights reserved.

@license:    MIT

@contact:    dawesc@me.com
@deffield    updated: 28 Oct 2017
'''

import sys
import os
import signal
from threading import Event
import time

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from com.camding.plexpostprocess.DatabaseInteraction import DatabaseInteraction
from com.camding.plexpostprocess.FileScanner import FileScanner
from com.camding.plexpostprocess.PlexPostProcessStateMachine import PlexPostProcessStateMachine
from com.camding.plexpostprocess.Settings import Settings
from com.camding.plexpostprocess.steps.DetermineFiletype import DetermineFiletype
from com.camding.plexpostprocess.steps.DetermineFilename import DetermineFilename

__all__ = []
__version__ = 0.1
__date__ = '2017-10-28'
__updated__ = '2017-10-28'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

wakeUp = Event()

def WakeUpNow(_signo, _frame):
  wakeUp.set()

class PlexPostProcessShared():
  def mainWithArgs(self, argv):
    global DEBUG
    global TESTRUN
    global PROFILE
    
    global __all__
    global __version__
    global __date__
    global __updated__
    
    global wakeUp

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = 'Scan and PlexPostProcess'
    program_license = '''%s %s

   MIT License

Copyright (c) 2018 Christopher Dawes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
  ''' % (program_shortdesc, str(__date__))

    try:
      # Setup argument parser
      parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
      parser.add_argument("-r", "--recursive", dest="recurse", action="store_true", help="recurse into subfolders [default: %(default)s]", default=True)
      parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]", default=0)
      parser.add_argument("-i", "--include", dest="include", help="only include paths matching this regex pattern. Note: exclude is given preference over include. [default: %(default)s]", metavar="RE", default="*.ts" )
      parser.add_argument("-e", "--exclude", dest="exclude", help="exclude paths matching this regex pattern. [default: %(default)s]", metavar="RE" )
      parser.add_argument('-V', '--version', action='version', version=program_version_message)
      parser.add_argument('-D', '--daemon', dest='daemon', action="store_true", help="Run in daemon mode [default: %(default)s]", default=False)
      parser.add_argument('-C', '--debug-corrie', dest='debugCorrie', action="store_true", help="Debug coronation street [default: %(default)s]", default=False)
      parser.add_argument(dest="paths", help="paths to folder(s) with source file(s) [default: %(default)s]", metavar="path", nargs='*')

      # Process arguments
      args = parser.parse_args(argv)
      print(args)
      paths   = args.paths + list(Settings.GetConfig('FileScanner').values())
      verbose = args.verbose > 0
      recurse = args.recurse
      inpat   = args.include
      expat   = args.exclude
      daemon  = args.daemon
      
      if daemon:
        signal.signal(signal.SIGUSR1, WakeUpNow)

      if verbose:
        print("Verbose mode on")
        if recurse:
          print("Recursive mode on")
        else:
          print("Recursive mode off")

      if inpat and expat and inpat == expat:
        raise Exception("include and exclude pattern are equal! Nothing will be processed.")
      fileScanner = FileScanner(recurse = recurse, paths = paths, inpat = inpat, expat = expat, verbose = verbose)
      with DatabaseInteraction() as databaseInteraction:
        if args.debugCorrie:
          x = DetermineFilename(PlexPostProcessStateMachine(databaseInteraction))
          print(x.GetNewCoronationStreetFilename("Coronation Street (1960) - 2018-11-30 20 30 00 - Episode 11-30.ts", None))
          return 0
        
        running = True
        first = True
        updateDb = True
        while running:
          nrNewFiles = 0
          if not first:
            updateDb = fileScanner.Rescan()
          if updateDb:
            print("Starting to update database...")
            nrNewFiles = databaseInteraction.UpdateWithFiles(fileScanner)
            print("Database update complete with " + str(nrNewFiles) + " new files.")
          if nrNewFiles > 0 or first:
            plexPostProcessr = PlexPostProcessStateMachine(databaseInteraction)
            DetermineFiletype(plexPostProcessr).DetermineFiletypes()
            plexPostProcessr.PlexPostProcess()
          if nrNewFiles == 0:
            wakeUp.clear()
            if wakeUp.wait(3600): #sleep for one hour
              time.sleep(5) #sleep for 5 seconds to prevent race condition on plex 
          running = daemon
          first = False
      
      return 0
    except KeyboardInterrupt:
      ### handle keyboard interrupt ###
      return 0
    except Exception as e:
      if DEBUG or TESTRUN:
        raise(e)
      indent = len(program_name) * " "
      sys.stderr.write(program_name + ": " + repr(e) + "\n")
      sys.stderr.write(indent + "  for help use --help")
      return 2
