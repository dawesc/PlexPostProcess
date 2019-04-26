#!/opt/local/bin/python3
# encoding: utf-8

import datetime, locale, math, ntpath, os, pytz, sqlite3
from tzlocal import get_localzone
from com.camding.plexpostprocess.Settings import Settings

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])

class DetermineFilename(object):
  def __init__(self, plexPostProcess):
    self.__plexPostProcess = plexPostProcess
    self.__london = pytz.timezone('Europe/London') #This is where corrie is aired
    self.__ltz    = get_localzone()                #The servers timezone
    self.__ltz    = pytz.timezone('Europe/London')    #For some reason plex writes it in pacific time on freenas
    self.__tmpDir = Settings.GetConfig('Paths', 'backup', '/mnt/PlexRecordings/BackupMP2')
    self.__plexLibraryPath = "/usr/local/plexdata-plexpass/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"

  def GetPlexLibraryPath(self):
    return self.__plexLibraryPath

  def SetPlexLibraryPath(self, plexLibraryPath):
    self.__plexLibraryPath = plexLibraryPath

  def GetPlexPostProcess(self):
    return self.__plexPostProcess;

  def GetCorriePosibility(self, row):
    _epIx    = row[0]
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
    conn = sqlite3.connect(Settings.GetConfig("Paths", "plexLibrary", self.GetPlexLibraryPath()))
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

  def GetNewCoronationStreetFilename(self, baseFile, _queuedFile):
    fileExtension = baseFile[baseFile.rfind('.') + 1:]
    baseFile      = baseFile[0:baseFile.rfind('.')]
    if "Coronation Street" in baseFile:
      baseParts = baseFile.split(' - ')
      dtFormat = "%Y-%m-%d %H %M %S"
      locCreateDt = self.__ltz.localize(datetime.datetime.strptime(baseParts[1], dtFormat)).astimezone(self.__london)
      metaInfo = self.GetCorrieIndex(locCreateDt)
      baseParts[1] = locCreateDt.strftime(dtFormat)
      if "19 30" in baseParts[1]:
        baseParts[2] += " - pt1"
      if "20 30" in baseParts[1]:
        baseParts[2] += " - pt2"
      if metaInfo is not None:
        epInfo = 's' + str(metaInfo[2]) + 'e' + str(metaInfo[3])
        baseParts.insert(1, epInfo)
      baseFile = ' - '.join(baseParts);
    if Settings.GetConfig("Applications", "handbrake", "false").lower in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh', 'on' ]:
      return baseFile + ".mp4"
    else:
      return baseFile + ".done." + fileExtension

  def GetDestFilename(self, queuedFile):
    baseFile = ntpath.basename(queuedFile.GetFilename())
    if queuedFile.GetFiletype() == 'm4v':
      return os.path.join(os.path.dirname(os.path.abspath(queuedFile.GetFilename())),
                        self.GetNewCoronationStreetFilename(baseFile, queuedFile))
    else:
      return os.path.join(os.path.dirname(os.path.abspath(queuedFile.GetFilename())),
                        baseFile[0:baseFile.rfind('.')] + ".mp3")

  def GetTempFilename(self, queuedFile):
    if queuedFile.GetFiletype() == 'm4v':
      return os.path.join(self.__tmpDir, ntpath.basename(queuedFile.GetFilename()) + "." + str(queuedFile.GetId()) + ".mp4")
    else:
      return os.path.join(self.__tmpDir, ntpath.basename(queuedFile.GetFilename()) + "." + str(queuedFile.GetId()) + ".mp3")
