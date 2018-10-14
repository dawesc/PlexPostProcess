#!/opt/local/bin/python3
# encoding: utf-8

import fcntl, os, shutil, subprocess, sys

from com.camding.plexpostprocess.PlexPostProcessState import PlexPostProcessState
from com.camding.plexpostprocess.PlexPostProcessShared import PlexPostProcessShared
from com.camding.plexpostprocess.PlexPostProcessShared import DEBUG
from com.camding.plexpostprocess.PlexPostProcessShared import TESTRUN
from com.camding.plexpostprocess.PlexPostProcessShared import PROFILE
from com.camding.plexpostprocess.Settings import Settings
from com.camding.plexpostprocess.steps.AddMeta import AddMeta
from com.camding.plexpostprocess.steps.Transcode import Transcode
from com.camding.plexpostprocess.steps.Commskip import Commskip
from com.camding.plexpostprocess.steps.DetermineFilename import DetermineFilename

class PlexPostProcess(object):
  def __init__(self, databaseInteraction):
    self.__tmpDir = Settings.GetConfig('Paths', 'backup', '/mnt/PlexRecordings/BackupMP2')
    self.__databaseInteraction = databaseInteraction
    self.__queue = self.GetDatabaseInteraction().GetQueue();
  
  def GetQueue(self):
    return self.__queue
  
  def GetDatabaseInteraction(self):
    return self.__databaseInteraction;
  
  def PlexPostProcess(self):
    queue = self.GetQueue()
    print('I have ' + str(len(queue)) + ' files to handle!')
    for i in range(0, len(queue)):
      queuedFile = queue[i]
      while not queuedFile.IsFinished():
        self.ProcessQueuedFile(i, queuedFile)
        
  def ProcessQueuedFile(self, i, queuedFile):
    print(' Processing ' + str(i) + queuedFile.GetFilename() + ' in state ' + queuedFile.GetState().name)
    if queuedFile.GetState() == PlexPostProcessState.INITIAL:
      if queuedFile.GetFiletype() == 'm4v':
        queuedFile.SetState(PlexPostProcessState.COMMSKIP)
        self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Startup", "Started commskip")
      else:
        queuedFile.SetState(PlexPostProcessState.TRANSCODING)
        self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Comskip", "Started processing")
    elif queuedFile.GetState() == PlexPostProcessState.COMMSKIP:
      Commskip(self).Commskip(i, queuedFile)
    elif queuedFile.GetState() == PlexPostProcessState.TRANSCODING:
      Transcode(self).Transcode(i, queuedFile)
    elif queuedFile.GetState() == PlexPostProcessState.ADD_META:
      AddMeta(self).AddMeta(i, queuedFile)
    elif queuedFile.GetState() == PlexPostProcessState.MOVING_FILES:
      self.MoveFiles(i, queuedFile)
    elif queuedFile.GetState() == PlexPostProcessState.DELETING_ORIGINAL_FILE:
      self.DeleteOriginalFile(i, queuedFile)
    elif queuedFile.GetState() == PlexPostProcessState.PENDING_DELETE_DUPLICATE:
      self.DeleteDuplicateFile(i, queuedFile)
    else:
      raise Exception("Damn, invalid state " + queuedFile.GetState().name)
    
  def RunProcess(self, command, env=None, stdin=None, stdout=None, stderr=None):
    """ Run command with specified env and I/O handles, return process """
  
    # merge specified env with OS env
    myenv = os.environ.copy()
    if env is not None:
      myenv.update(env)
  
    try:
      process = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr, env=myenv, bufsize=0)
      return process
    except:
      print("Unexpected error when launching process:")
      print("  ", command)
      print("  ", env)
      raise

  def MoveFiles(self, _i, queuedFile):
    filenameHandler = DetermineFilename(self)
    self.GetDatabaseInteraction().AddQFHistory(queuedFile, "Move Files", "Moving from '" + filenameHandler.GetTempFilename(queuedFile) + "' to '" + filenameHandler.GetDestFilename(queuedFile) + "'")
    try:
      shutil.move(filenameHandler.GetTempFilename(queuedFile), filenameHandler.GetDestFilename(queuedFile))
    except:
      queuedFile.SetState(PlexPostProcessState.ERROR)
      sys.exit(2)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Move Files", "Error " + str(sys.exc_info()[0]))
      return;
    queuedFile.SetState(PlexPostProcessState.DELETING_ORIGINAL_FILE)
    self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Move Files", "Finished moving files with success!")
    
  def DeleteFile(self, deleteType, successState, errorState, _i, queuedFile):
    self.GetDatabaseInteraction().AddQFHistory(queuedFile, deleteType, "Deleting '" + queuedFile.GetFilename() + "'")
    try:
      os.remove(queuedFile.GetFilename())
    except:
      queuedFile.SetState(errorState)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, deleteType, "Error " + str(sys.exc_info()[0]))
      return;
    queuedFile.SetState(successState)
    self.GetDatabaseInteraction().UpdateQFState(queuedFile, deleteType, "Finished deleting files with success!")
    
  def DeleteOriginalFile(self, i, queuedFile):
    self.DeleteFile("Delete Original", PlexPostProcessState.SUCCESS, PlexPostProcessState.ERROR, i, queuedFile)
    
  def DeleteDuplicateFile(self, i, queuedFile):
    self.DeleteFile("Delete Duplicate", PlexPostProcessState.DUPLICATE_DELETED, PlexPostProcessState.ERROR, i, queuedFile)
    

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

pid_file = Settings.GetConfig('Paths','cmdLinePidFile','cmd_plex_post_process.pid')
fp = open(pid_file, 'w')
try:
    fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    # another instance is running
    sys.exit(0)