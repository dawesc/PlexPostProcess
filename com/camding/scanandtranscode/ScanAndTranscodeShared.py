#!/opt/local/bin/python3
# encoding: utf-8
'''
com.camding.scanandtranscode.ScanAndTranscode -- This is used to parse the arguments

com.camding.scanandtranscode.ScanAndTranscode is a application used to 
make the system transcode all un-transcoded files

It defines classes_and_methods

@author:     chrisd

@copyright:  2017 Camding Ltd. All rights reserved.

@license:    BSD

@contact:    dawesc@me.com
@deffield    updated: 28 Oct 2017
'''

import sys
import os
import fcntl
import signal
from threading import Event
import time

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from com.camding.scanandtranscode.DatabaseInteraction import DatabaseInteraction
from com.camding.scanandtranscode.FileScanner import FileScanner
from com.camding.scanandtranscode.Transcoder import Transcoder

__all__ = []
__version__ = 0.1
__date__ = '2017-10-28'
__updated__ = '2017-10-28'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

wakeUp = Event()

def WakeUpNow(signo, _frame):
  wakeUp.set()

class ScanAndTranscodeShared():
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
    program_shortdesc = 'Scan and Transcode'
    program_license = '''%s

    Created by user_name on %s.
    Copyright 2017 organization_name. All rights reserved.

    Licensed under the 2-Clause BSD License
    Copyright 2017 Camding Ltd.

    Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
      parser.add_argument(dest="paths", help="paths to folder(s) with source file(s) [default: %(default)s]", metavar="path", nargs='+')

      # Process arguments
      args = parser.parse_args(argv)
      print(args)
      paths   = args.paths
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
        raise CLIError("include and exclude pattern are equal! Nothing will be processed.")
      fileScanner = FileScanner(recurse = recurse, paths = paths, inpat = inpat, expat = expat, verbose = verbose)
      with DatabaseInteraction() as databaseInteraction:
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
            transcoder = Transcoder(databaseInteraction)
            transcoder.DetermineFiletype()
            transcoder.Transcode()
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
