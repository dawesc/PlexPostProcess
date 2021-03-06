#!/opt/local/bin/python3
# encoding: utf-8

import sys

from subprocess import PIPE
from threading import Thread
from queue import Queue

from com.camding.plexpostprocess.Metadata import Metadata
from com.camding.plexpostprocess.PlexPostProcessState import PlexPostProcessState
from com.camding.plexpostprocess.steps.DetermineFilename import DetermineFilename

class AddMeta(object):
  def __init__(self, plexPostProcess):
    self.__plexPostProcess = plexPostProcess
  
  def GetPlexPostProcess(self):
    return self.__plexPostProcess;
  
  def AddMeta(self, _i, queuedFile):
    filenameHandler = DetermineFilename(self.GetPlexPostProcess())
    print("  Add metadata to " + filenameHandler.GetTempFilename(queuedFile));
    self.GetPlexPostProcess().GetDatabaseInteraction().AddQFHistory(queuedFile, "Metadata", "  Metadata to " + filenameHandler.GetTempFilename(queuedFile));
    
    command = Metadata(filenameHandler.GetDestFilename(queuedFile)).GetIDCommand(filenameHandler.GetTempFilename(queuedFile))
    
    logfile_queue = Queue()
    logfile_queue.put(" ".join(command).encode('utf-8'))
    sys.stdout.write(" ".join(command))
    sys.stdout.flush()
  
    # Launch the process with PIPE stdout and stderr
    process = self.GetPlexPostProcess().RunProcess(command, None, sys.stdin, PIPE, PIPE)
  
    # Function for reader threads, echo lines from in_fh to out_fh and out_queue
    def read_handler(in_fh, out_fh, out_queue):
      while True:
        line = in_fh.readline()
        if not line: return
        out_fh.buffer.write(line)
        out_fh.flush()
        out_queue.put(line)
  
    # Function for writer thread, echo lines from in_queue to out_fh
    def write_handler(in_queue, queuedFile, databaseInteraction):
      while True:
        line = in_queue.get()
        if line is None: return
        databaseInteraction.AddQFHistory(queuedFile, "Metadata", line)
  
    # Launch a thread for reading stdout, reading stderr, and writing the logfile
    stdout_thread = Thread(target=read_handler, args=(process.stdout, sys.stdout, logfile_queue))
    stderr_thread = Thread(target=read_handler, args=(process.stderr, sys.stderr, logfile_queue))
    logfile_thread = Thread(target=write_handler, args=(logfile_queue, queuedFile, self.GetPlexPostProcess().GetDatabaseInteraction()))
  
    for thread in stdout_thread, stderr_thread, logfile_thread:
      thread.daemon = True
      thread.start()
  
    # Wait for the process to complete
    process.wait()
  
    # Wait for stdout and stderr threads to complete
    for thread in stdout_thread, stderr_thread:
      thread.join()
  
    # Signal and wait for the logfile thread to complete
    logfile_queue.put(None)
    logfile_thread.join()
  
    if process.returncode == 0:
      queuedFile.SetState(PlexPostProcessState.MOVING_FILES)
      self.GetPlexPostProcess().GetDatabaseInteraction().UpdateQFState(queuedFile, "Metadata", "Finished metadata with success !")
    else:
      queuedFile.SetState(PlexPostProcessState.ERROR)
      self.GetPlexPostProcess().GetDatabaseInteraction().UpdateQFState(queuedFile, "Metadata", "Error " + str(process.returncode))
    