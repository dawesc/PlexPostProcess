'''
Created on 28 Oct 2017

@author: chrisd
'''
from com.camding.scanandtranscode.Metadata import Metadata
from com.camding.scanandtranscode.TranscodeState import TranscodeState
from com.camding.scanandtranscode.DatabaseInteraction import DatabaseInteraction
import ntpath

import subprocess, shlex, os, tempfile, sys
from subprocess import DEVNULL, PIPE
from threading import Thread
from queue import Queue
import datetime, shutil, time, pytz
import locale, math, time, datetime, pytz, sqlite3

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])

class Transcoder(object):
  '''
  classdocs
  '''

  def __init__(self, databaseInteraction):
    '''
    Constructor
    '''
    self.__tmpDir = '/mnt/PlexRecordings/BackupMP2'
    self.__databaseInteraction = databaseInteraction
    self.__queue = self.GetDatabaseInteraction().GetQueue();
    self.__london = pytz.timezone('Europe/London')
    self.__la     = pytz.timezone('America/Los_Angeles')
  
  
  def GetQueue(self):
    return self.__queue
  
  def GetDatabaseInteraction(self):
    return self.__databaseInteraction;
  
  def DetermineFiletype(self):
    queue = self.GetQueue()
    for i in range(0, len(queue)):
      queuedFile = queue[i]
      if queuedFile.GetFiletype() == '':
        self.DetermineFiletypeForFile(i, queuedFile)
    
  def DetermineFiletypeForFile(self, i, queuedFile):
    if queuedFile.GetState() == TranscodeState.PENDING_DELETE_DUPLICATE:
      return
    
    print(' Determining filetype for ' + str(i) + queuedFile.GetFilename() + ' in state ' + queuedFile.GetState().name)
    self.GetDatabaseInteraction().AddQFHistory(queuedFile, "Transcode", "  Determine file type for " + queuedFile.GetFilename());
    
    command = [
      '/usr/local/bin/ffprobe', 
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
    process = self.RunProcess(command, None, sys.stdin, PIPE, PIPE)
  
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
        databaseInteraction.AddQFHistory(queuedFile, "Transcode", line)
        if "codec_type=video" in line.decode("utf-8"):
          texts.append(line.decode("utf-8"))
  
    texts = []
    # Launch a thread for reading stdout, reading stderr, and writing the logfile
    stdout_thread = Thread(target=read_handler, args=(process.stdout, sys.stdout, logfile_queue))
    stderr_thread = Thread(target=read_handler, args=(process.stderr, sys.stderr, logfile_queue))
    logfile_thread = Thread(target=write_handler, args=(logfile_queue, queuedFile, self.GetDatabaseInteraction(), texts))
  
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
      self.GetDatabaseInteraction().UpdateQFFiletype(queuedFile, "Transcode", "Determined output format as " + queuedFile.GetFiletype())
    else:
      queuedFile.SetState(TranscodeState.ERROR)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Transcode", "ffprobe error " + str(process.returncode))
    
    
  def Transcode(self):
    queue = self.GetQueue()
    print('I have ' + str(len(queue)) + ' files to handle!')
    for i in range(0, len(queue)):
      queuedFile = queue[i]
      while not queuedFile.IsFinished():
        self.ProcessQueuedFile(i, queuedFile)
        
  def ProcessQueuedFile(self, i, queuedFile):
    print(' Processing ' + str(i) + queuedFile.GetFilename() + ' in state ' + queuedFile.GetState().name)
    if queuedFile.GetState() == TranscodeState.INITIAL:
      if queuedFile.GetFiletype() == 'm4v':
        queuedFile.SetState(TranscodeState.COMMSKIP)
        self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Startup", "Started commskip")
      else:
        queuedFile.SetState(TranscodeState.TRANSCODING)
        self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Comskip", "Started processing")
    elif queuedFile.GetState() == TranscodeState.COMMSKIP:
      self.Commskip(i, queuedFile)
    elif queuedFile.GetState() == TranscodeState.TRANSCODING:
      self.TranscodeFile(i, queuedFile)
    elif queuedFile.GetState() == TranscodeState.ADD_META:
      self.AddMeta(i, queuedFile)
    elif queuedFile.GetState() == TranscodeState.MOVING_FILES:
      self.MoveFiles(i, queuedFile)
    elif queuedFile.GetState() == TranscodeState.DELETING_ORIGINAL_FILE:
      self.DeleteOriginalFile(i, queuedFile)
    elif queuedFile.GetState() == TranscodeState.PENDING_DELETE_DUPLICATE:
      self.DeleteDuplicateFile(i, queuedFile)
    else:
      raise Exception("Damn, invalid state " + queuedFile.GetState().name)
    
  def GetTempFilename(self, queuedFile):
    if queuedFile.GetFiletype() == 'm4v':
      return os.path.join(self.__tmpDir, ntpath.basename(queuedFile.GetFilename()) + "." + str(queuedFile.GetId()) + ".mp4")
    else:
      return os.path.join(self.__tmpDir, ntpath.basename(queuedFile.GetFilename()) + "." + str(queuedFile.GetId()) + ".mp3")
  
  def GetCorriePosibility(self, row):
    epIx    = row[0]
    epTitle = row[1]
    epGuid  = row[2]
    
    epSeries = row[2].replace('com.plexapp.agents.thetvdb://71565/', '')
    epSeries = epSeries[:epSeries.index('/')]
    epNr     = row[2].replace('com.plexapp.agents.thetvdb://71565/' + epSeries + '/', '')
    epNr     = epNr[0:epNr.index('?')]  
    epPart   = None
    
    if "Part" in epTitle:
      epPartIx = epTitle.index("Part ") + 5
      epPart = int(epTitle[epPartIx:epPartIx + 1])
    
    return [epGuid,epTitle,int(epSeries),int(epNr),epPart]

  def GetCorrieIndex(self, locCreateDt):
    locale.setlocale(locale.LC_TIME, "en_GB.UTF-8")
    conn = sqlite3.connect("/usr/local/plexdata-plexpass/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db")
    c = conn.cursor()
    formattedDate = locCreateDt.strftime("%A,%%" + ordinal(locCreateDt.day) + " %B %Y")
    sql = "select \"index\",title,guid from metadata_items where library_section_id=17 and guid like '%/71565/%' and metadata_type = 4 and title like '%" + formattedDate + "%';"
    
    possibilities = []
    for row in c.execute(sql):
      possibilities.append(self.GetCorriePosibility(row))
    
    conn.close()
    if len(possibilities) == 0:
      return None
      
    hasPart = False
    for posibility in possibilities:
      hasPart = hasPart or posibility[4] != None
      
    if hasPart:
      desired = possibilities[0][4]
      if locCreateDt.hour == 19:
        desired = 1
      elif locCreateDt.hour == 20:
        desired = 2
          
      if possibilities[0][4] != desired:
        possibilities[0][3] = possibilities[0][3] - possibilities[0][4] + desired
        possibilities[0][4] = desired
    
    return possibilities[0]

  def GetNewCoronationStreetFilename(self, baseFile, queuedFile):
    baseFile = baseFile[0:baseFile.rfind('.')]
    if "Coronation Street" in baseFile:
      baseParts = baseFile.split(' - ')
      format = "%Y-%m-%d %H %M %S"
      locCreateDt = self.__la.localize(datetime.datetime.strptime(baseParts[1], format)).astimezone(self.__london)
      metaInfo = self.GetCorrieIndex(locCreateDt)
      baseParts[1] = locCreateDt.strftime(format)
      if "19 30" in baseParts[1]:
        baseParts[2] += " - pt1"
      if "20 30" in baseParts[1]:
        baseParts[2] += " - pt2"
      if metaInfo is not None:
        epInfo = 's' + str(metaInfo[2]) + 'e' + str(metaInfo[3])
        baseParts.insert(1, epInfo)
      baseFile = ' - '.join(baseParts);
   
    return baseFile + ".mp4"
    
  def GetDestFilename(self, queuedFile):
    baseFile = ntpath.basename(queuedFile.GetFilename())
    if queuedFile.GetFiletype() == 'm4v':
      return os.path.join(os.path.dirname(os.path.abspath(queuedFile.GetFilename())), 
                        self.GetNewCoronationStreetFilename(baseFile, queuedFile))
    else:
      return os.path.join(os.path.dirname(os.path.abspath(queuedFile.GetFilename())), 
                        baseFile[0:baseFile.rfind('.')] + ".mp3")
  
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

  def Commskip(self, i, queuedFile):
    print("  Commskip to " + self.GetTempFilename(queuedFile));
    self.GetDatabaseInteraction().AddQFHistory(queuedFile, "Commskip", "  Commskip to " + self.GetTempFilename(queuedFile));

    if "The X Factor (2004)" in queuedFile.GetFilename():
      queuedFile.SetState(TranscodeState.TRANSCODING)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Comskip", "XFactor cannot be comskipped; it's too much like an advert ;)")
      return
      
    command = [
        '/usr/local/bin/bash', 
        '/mnt/PlexRecordings/post_process.sh',
        queuedFile.GetFilename()
        ]

    logfile_queue = Queue()
    logfile_queue.put(" ".join(command).encode('utf-8'))
    sys.stdout.write(" ".join(command))
    sys.stdout.flush()
  
    # Launch the process with PIPE stdout and stderr
    process = self.RunProcess(command, None, sys.stdin, PIPE, PIPE)
  
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
        databaseInteraction.AddQFHistory(queuedFile, "Commskip", line)
  
    # Launch a thread for reading stdout, reading stderr, and writing the logfile
    stdout_thread = Thread(target=read_handler, args=(process.stdout, sys.stdout, logfile_queue))
    stderr_thread = Thread(target=read_handler, args=(process.stderr, sys.stderr, logfile_queue))
    logfile_thread = Thread(target=write_handler, args=(logfile_queue, queuedFile, self.GetDatabaseInteraction()))
  
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
      queuedFile.SetState(TranscodeState.TRANSCODING)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Comskip", "Started processing")
    else:
      queuedFile.SetState(TranscodeState.TRANSCODING)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Comskip", "Error " + str(process.returncode))
    
  def TranscodeFile(self, i, queuedFile):
    print("  Transcode to " + self.GetTempFilename(queuedFile));
    self.GetDatabaseInteraction().AddQFHistory(queuedFile, "Transcode", "  Transcode to " + self.GetTempFilename(queuedFile));
    
    command = []
    
    if queuedFile.GetFiletype() == 'm4v':
      command = [
        '/usr/local/bin/HandBrakeCLI', 
        '--preset-import-file', 
	'/mnt/PlexRecordings/preset.json',
        '-i',
        queuedFile.GetFilename(),
        '-o',
        self.GetTempFilename(queuedFile),
        '--preset',
        'Super HQ 1080p30 Surround MP3',
        '--decomb',
        'bob']
    else:
      command = [
        '/usr/local/bin/ffmpeg', 
        '-i',
        queuedFile.GetFilename(),
        '-vn',
        '-acodec',
        'copy',
        self.GetTempFilename(queuedFile)]
  
    logfile_queue = Queue()
    logfile_queue.put(" ".join(command).encode('utf-8'))
    sys.stdout.write(" ".join(command))
    sys.stdout.flush()
  
    # Launch the process with PIPE stdout and stderr
    process = self.RunProcess(command, None, sys.stdin, PIPE, PIPE)
  
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
        databaseInteraction.AddQFHistory(queuedFile, "Transcode", line)
  
    # Launch a thread for reading stdout, reading stderr, and writing the logfile
    stdout_thread = Thread(target=read_handler, args=(process.stdout, sys.stdout, logfile_queue))
    stderr_thread = Thread(target=read_handler, args=(process.stderr, sys.stderr, logfile_queue))
    logfile_thread = Thread(target=write_handler, args=(logfile_queue, queuedFile, self.GetDatabaseInteraction()))
  
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
      if queuedFile.GetFiletype() == 'm4v':
        queuedFile.SetState(TranscodeState.MOVING_FILES)
      else:
        queuedFile.SetState(TranscodeState.ADD_META)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Transcode", "Finished transcoding with success !")
    else:
      queuedFile.SetState(TranscodeState.ERROR)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Transcode", "Error " + str(process.returncode))
      
  def AddMeta(self, i, queuedFile):
    print("  Add metadata to " + self.GetTempFilename(queuedFile));
    self.GetDatabaseInteraction().AddQFHistory(queuedFile, "Metadata", "  Metadata to " + self.GetTempFilename(queuedFile));
    
    command = Metadata(self.GetDestFilename(queuedFile)).GetIDCommand(self.GetTempFilename(queuedFile))
    
    logfile_queue = Queue()
    logfile_queue.put(" ".join(command).encode('utf-8'))
    sys.stdout.write(" ".join(command))
    sys.stdout.flush()
  
    # Launch the process with PIPE stdout and stderr
    process = self.RunProcess(command, None, sys.stdin, PIPE, PIPE)
  
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
    logfile_thread = Thread(target=write_handler, args=(logfile_queue, queuedFile, self.GetDatabaseInteraction()))
  
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
      queuedFile.SetState(TranscodeState.MOVING_FILES)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Metadata", "Finished metadata with success !")
    else:
      queuedFile.SetState(TranscodeState.ERROR)
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Metadata", "Error " + str(process.returncode))
    
  def MoveFiles(self, i, queuedFile):
    self.GetDatabaseInteraction().AddQFHistory(queuedFile, "Move Files", "Moving from '" + self.GetTempFilename(queuedFile) + "' to '" + self.GetDestFilename(queuedFile) + "'")
    try:
      shutil.move(self.GetTempFilename(queuedFile), self.GetDestFilename(queuedFile))
    except:
      queuedFile.SetState(TranscodeState.ERROR)
      die ('bad')
      self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Move Files", "Error " + str(sys.exc_info()[0]))
      return;
    queuedFile.SetState(TranscodeState.DELETING_ORIGINAL_FILE)
    self.GetDatabaseInteraction().UpdateQFState(queuedFile, "Move Files", "Finished moving files with success!")
    
  def DeleteFile(self, deleteType, successState, errorState, i, queuedFile):
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
    self.DeleteFile("Delete Original", TranscodeState.SUCCESS, TranscodeState.ERROR, i, queuedFile)
    
  def DeleteDuplicateFile(self, i, queuedFile):
    self.DeleteFile("Delete Duplicate", TranscodeState.DUPLICATE_DELETED, TranscodeState.ERROR, i, queuedFile)
    

if __name__ == "__main__":
  with DatabaseInteraction() as databaseInteraction:
    x = Transcoder(databaseInteraction)
    print(x.GetNewCoronationStreetFilename("Coronation Street (1960) - 2018-10-12 11 30 00 - Episode 10-12.mp4", None))
