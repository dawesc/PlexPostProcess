'''
Created on 28 Oct 2017

@author: chrisd
'''
from com.camding.plexpostprocess.PlexPostProcessState import PlexPostProcessState

class ScannedFile(object):
  '''
  classdocs
  '''
  def __init__(self, row):
    '''
    Constructor
    '''
    self.__state = row['state']
    self.__filename = row['filename']
    self.__id = row['id']
    self.__filetype = row['filetype']
    self.__creationDate = row['creationDate']
    
  def GetFilename(self):
    return self.__filename
    
  def GetFiletype(self):
    return self.__filetype
    
  def GetState(self):
    return PlexPostProcessState[self.__state]
  
  def GetId(self):
    return self.__id
    
  def SetState(self, state):
    self.__state = state.name
  
  def SetFiletype(self, filetype):
    self.__filetype = filetype
    
  def GetCreationDate(self):
    return self.__creationDate
    
  def IsFinished(self):
    stateParsed = PlexPostProcessState[self.__state]
    if stateParsed == PlexPostProcessState.ERROR or stateParsed == PlexPostProcessState.SUCCESS or stateParsed == PlexPostProcessState.DUPLICATE_DELETED:
      return True
    return False