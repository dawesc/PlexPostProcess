import configparser, os, platform

class Settings:
  """Used to read in the settings"""

  @staticmethod
  def GetRootPath():
    #plexpostprocess
    configDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    #camding
    configDir = os.path.join(configDir, os.pardir) 
    #com
    configDir = os.path.join(configDir, os.pardir) 
    #PlexPostProcess Root
    configDir = os.path.join(configDir, os.pardir)
    configDir = os.path.abspath(configDir)
    return configDir
    
  @classmethod
  def __ClsInit(cls):
    if hasattr(cls, '__config'): 
      return cls.__config
    
    cls.__configFilename = '/etc/defaults/sat.conf'
    
    if platform.system() == 'Windows':
      cls.__configFilename = os.path.join(Settings.GetRootPath(), 'sat.ini')
    
    cls.__config = configparser.ConfigParser() 
    cls.__config.read(cls.__configFilename)
    
    return cls.__config
    
  @classmethod
  def GetConfig(cls, section = None, key = None, defaultVal = None):
    config = Settings.__ClsInit()
    if section is None:
      return config
    sectionObject = dict()
    if section in config:
      sectionObject = config[section]
      
    if key is None:
      return sectionObject
   
    retval = defaultVal
    if key in sectionObject:
      retval = sectionObject[key]
      
    return retval
  