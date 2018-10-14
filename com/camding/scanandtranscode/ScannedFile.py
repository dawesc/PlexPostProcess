'''
Created on 28 Oct 2017

@author: chrisd
'''
from com.camding.scanandtranscode.TranscodeState import TranscodeState

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
    return TranscodeState[self.__state]
  
  def GetId(self):
    return self.__id
    
  def SetState(self, state):
    self.__state = state.name
  
  def SetFiletype(self, filetype):
    self.__filetype = filetype
    
  def GetCreationDate(self):
    return self.__creationDate
    
  def IsFinished(self):
    stateParsed = TranscodeState[self.__state]
    if stateParsed == TranscodeState.ERROR or stateParsed == TranscodeState.SUCCESS or stateParsed == TranscodeState.DUPLICATE_DELETED:
      return True
    return False