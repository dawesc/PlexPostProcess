# encoding: utf-8

import sys

from subprocess import PIPE
from threading import Thread
from queue import Queue

from com.camding.plexpostprocess.PlexPostProcessState import PlexPostProcessState
from com.camding.plexpostprocess.Settings import Settings

class DetermineFiletype(object):
  def __init__(self, plexPostProcess):
    self.__plexPostProcess = plexPostProcess
  
  def GetPlexPostProcess(self):
    return self.__plexPostProcess;
  
  def DetermineFiletypes(self):
    queue = self.GetPlexPostProcess().GetQueue()
    for i in range(0, len(queue)):
      queuedFile = queue[i]
      if queuedFile.GetFiletype() == '':
        self.DetermineFiletypeForFile(i, queuedFile)
    
  def DetermineFiletypeForFile(self, i, queuedFile):
    if queuedFile.GetState() == PlexPostProcessState.PENDING_DELETE_DUPLICATE:
      return
    
    print(' Determining filetype for ' + str(i) + queuedFile.GetFilename() + ' in state ' + queuedFile.GetState().name)
    self.GetPlexPostProcess().GetDatabaseInteraction().AddQFHistory(queuedFile, "DetermineFiletype", "  Determine file type for " + queuedFile.GetFilename());
    
    command = [
      Settings.GetConfig('Applications', 'ffprobe', '/usr/local/bin/ffprobe'), 
      '-v',
      'quiet',
      '-show_streams',
      '-hide_banner',
      queuedFile.GetFilename()]
  
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
    def write_handler(in_queue, queuedFile, databaseInteraction, texts):
      while True:
        line = in_queue.get()
        if line is None: return
        databaseInteraction.AddQFHistory(queuedFile, "DetermineFiletype", line)
        if "codec_type=video" in line.decode("utf-8"):
          texts.append(line.decode("utf-8"))
  
    texts = []
    # Launch a thread for reading stdout, reading stderr, and writing the logfile
    stdout_thread = Thread(target=read_handler, args=(process.stdout, sys.stdout, logfile_queue))
    stderr_thread = Thread(target=read_handler, args=(process.stderr, sys.stderr, logfile_queue))
    logfile_thread = Thread(target=write_handler, args=(logfile_queue, queuedFile, self.GetPlexPostProcess().GetDatabaseInteraction(), texts))
  
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
      queuedFile.SetFiletype('m4v' if len(texts) > 0 else 'mp3')
      self.GetPlexPostProcess().GetDatabaseInteraction().UpdateQFFiletype(queuedFile, "DetermineFiletype", "Determined output format as " + queuedFile.GetFiletype())
    else:
      queuedFile.SetState(PlexPostProcessState.ERROR)
      self.GetPlexPostProcess().GetDatabaseInteraction().UpdateQFState(queuedFile, "DetermineFiletype", "ffprobe error " + str(process.returncode))
    