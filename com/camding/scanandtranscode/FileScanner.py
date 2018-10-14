'''
Created on 28 Oct 2017

@author: chrisd
'''

import fnmatch
import glob
import os


class FileScanner(object):
    '''
    classdocs
    '''

    def __init__(self, paths, inpat, expat, recurse, verbose):
        '''
        Constructor
        '''
        self.__paths = paths
        self.__inpat = inpat
        self.__expat = expat
        self.__recurse = recurse
        self.__scannedFiles = set()
        self.__scanned = False
        self.__verbose = verbose
        
    def GetPaths(self):
      return self.__paths
    
    def GetInpat(self):
      return self.__inpat
    
    def GetExpat(self):
      return self.__expat
    
    def IsRecurse(self):
      return self.__recurse

    def IsVerbose(self):
      return self.__verbose
    
    def GetScannedFiles(self):
      if not self.__scanned:
        self.Scan();
        self.__scanned = True
      
      return self.__scannedFiles
    
    def Rescan(self):
      print("Starting rescan...")
      oldLength = len(self.__scannedFiles)
      self.__scannedFiles = set()
      self.Scan()
      print("Old length " + str(oldLength) + " != " + str(len(self.__scannedFiles)) + ". Rescan complete.")
      return oldLength != len(self.__scannedFiles)
      
    def Scan(self):
      if self.IsVerbose():
        print("Starting scan...")
      for pathx in self.GetPaths():
        if self.IsVerbose():
          print("Starting scan of " + pathx)
        filesIn = []
        filesOut = []
        if self.IsRecurse():
          for root, dirnames, filenames in os.walk(pathx):
            for filename in fnmatch.filter(filenames, self.GetInpat()):
              if self.IsVerbose():
                print("Adding " + os.path.join(root, filename))
              filesIn.append(os.path.join(root, filename))
            if self.GetExpat() is not None:
              for filename in fnmatch.filter(filenames, self.GetExpat()):
                if self.IsVerbose():
                  print("Excluding " + os.path.join(root, filename))
                filesOut.append(os.path.join(root, filename))
            if '.grab' in dirnames:
              dirnames.remove('.grab')
        else:
          filesIn = glob.glob(os.path.join(pathx, self.GetInpat()))
          filesOut = glob.glob(os.path.join(pathx, self.GetExpat()))
        self.__scannedFiles = self.__scannedFiles | (set(filesIn) - set(filesOut))
      
      # Sort by date
      scannedFileByDate = []
      for scannedFile in self.__scannedFiles:
        scannedFileByDate.append({ 'filename': scannedFile, 'modified': os.path.getmtime(scannedFile) })
         
      self.__scannedFiles = []
      for scan in sorted(scannedFileByDate, key=lambda scan: scan["modified"]):
        self.__scannedFiles.append(scan['filename'])

      if self.IsVerbose():
        print("Scan completed, found " + str(len(self.__scannedFiles)))
