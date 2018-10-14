#!/opt/local/bin/python3
# encoding: utf-8

import sys
import os
import fcntl

from com.camding.scanandtranscode.ScanAndTranscodeShared import ScanAndTranscodeShared
from com.camding.scanandtranscode.ScanAndTranscodeShared import DEBUG
from com.camding.scanandtranscode.ScanAndTranscodeShared import TESTRUN
from com.camding.scanandtranscode.ScanAndTranscodeShared import PROFILE

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    ScanAndTranscodeShared().mainWithArgs(argv)

pid_file = 'scan_and_transcode.pid'
fp = open(pid_file, 'w')
try:
    fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # another instance is running
    sys.exit(0)
    
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
        profile_filename = 'com.camding.scanandtranscode.ScanAndTranscode_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())
