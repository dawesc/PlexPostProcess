from com.camding.plexpostprocess.Settings import Settings

class Metadata(object):
  '''
  classdocs
  '''
  def __init__(self, filename):
    '''
    Constructor
    '''
    self.__filenameAndPath = filename
    parts = filename.split("/")
    parts = parts[-3:]
    self.__show = parts[0][0:parts[0].rfind('(')].strip();
    self.__year = parts[0][parts[0].rfind('(')+1:parts[0].rfind('(')+5].strip();
    self.__season_str = parts[1].strip()
    parts = parts[2].split('-')
    self.__season = parts[1][parts[1].rfind('S')+1:parts[1].rfind('E')].strip()
    self.__episode = parts[1][parts[1].rfind('E')+1:].strip()
    self.__filename = parts[2][0:parts[2].rfind('.')].strip()
    
  def GetFilenameAndPath(self):
    return self.__filenameAndPath
    
  def GetFilename(self):
    return self.__filename
    
  def GetEpisode(self):
    return self.__episode
    
  def GetSeason(self):
    return self.__season
  
  def GetSeasonStr(self):
    return self.__season_str
  
  def GetYear(self):
    return self.__year
  
  def GetShow(self):
    return self.__show
  
  def GetIDCommand(self, tempFilename):
    return [
      Settings.GetConfig("Applications", "id3v2", '/usr/local/bin/id3v2') ,
      '--TYER',
      self.GetYear(), 
      '--TALB',
      self.GetShow(),
      '--TIT2',
      self.GetFilename(),
      '--TRCK',
      self.GetEpisode(), 
      '--TPOS',
      self.GetSeason(),
      '--TPE1',
      self.GetShow(),
      '--TPE2',
      self.GetShow(),
      '--TALB',
      self.GetSeasonStr(), 
      tempFilename
      ]

