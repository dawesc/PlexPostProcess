'''
Created on 28 Oct 2017

@author: chrisd
'''

import pymysql.cursors
import os.path, re, time
from com.camding.plexpostprocess.ScannedFile import ScannedFile
from com.camding.plexpostprocess.Settings import Settings

class DatabaseInteraction(object):
  '''
  classdocs
  '''

  def __init__(self):
    self.__copyRegex = re.compile(r" \(copy [0-9]+\)\.")
  
  def __enter__(self):
    self.Reconnect()
    return self
    
  def Reconnect(self):
    dbConfig = Settings.GetConfig('Database')
    self.__connection = pymysql.connect(host=dbConfig['host'],
                             user=dbConfig['user'],
                             password=dbConfig['password'],
                             db=dbConfig['db'],
                             unix_socket='/tmp/mysql.sock',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
                             
  def VerifyTables(self):
    self.__connection.close();
    self.Reconnect()
    with self.__connection.cursor() as cursor:
      # Create a new record
      sql = '''CREATE TABLE IF NOT EXISTS `files` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `filename` varchar(10000) COLLATE utf8_bin NOT NULL,
    `state` varchar(255) COLLATE utf8_bin NOT NULL,
    `filetype` varchar(10) COLLATE utf8_bin NOT NULL DEFAULT '',
    `creationDate` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin
AUTO_INCREMENT=1 ;'''
      cursor.execute(sql)
      sql = '''CREATE TABLE IF NOT EXISTS `file_history` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `file_id` int(11) NOT NULL,
    `when` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `operation` varchar(255) COLLATE utf8_bin NOT NULL,
    `what_happened` LONGTEXT NOT NULL,
    PRIMARY KEY (`id`),
    FOREIGN KEY (`file_id`) REFERENCES files(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin
AUTO_INCREMENT=1 ;'''
      cursor.execute(sql)
      sql = '''SELECT COUNT(1) IndexIsThere FROM INFORMATION_SCHEMA.STATISTICS
  WHERE table_schema=DATABASE() AND table_name='files' AND index_name='IX_FILES_FILENAME';'''
      cursor.execute(sql)
      result = cursor.fetchone()
      if result["IndexIsThere"] == 0:
        sql = '''CREATE INDEX IX_FILES_FILENAME ON `files` (`filename`(1000));'''
        cursor.execute(sql)
        
  def RemoveFileExtension(self, toRemoveExtension):
    return ('.').join(toRemoveExtension.split('.')[:-1])
  
  def RemoveCopyStatement(self, toRemoveCopy):
    return self.__copyRegex.sub(r".", toRemoveCopy)
     
  def AllowDuplicates(self, filenameToCheck):
    return "Coronation Street" in filenameToCheck
    
  def InsertIfDoesntExist(self, fileToInsert, verbose):
    if verbose:
      print("InsertIfDoesntExist: " + fileToInsert)
    with self.__connection.cursor() as cursor:
      sql = '''SELECT COUNT(1) IndexIsThere FROM `files` WHERE `filename` like %s;'''
      
      reducedFilename = self.RemoveFileExtension(self.RemoveCopyStatement(fileToInsert)) + "%"
      
      cursor.execute(sql, (reducedFilename,))
      sqlResult = cursor.fetchone()
      
      duplicate = False
      if sqlResult["IndexIsThere"] != 0:
        sql = '''SELECT `filename`, `state` FROM `files` WHERE `filename` like %s;'''
        cursor.execute(sql, (reducedFilename,))
        sqlResult = cursor.fetchone()
        
        duplicate = True
        while sqlResult is not None:
          if sqlResult["filename"] == fileToInsert and not (sqlResult["state"] == 'SUCCESS' or sqlResult["state"] == 'DUPLICATE_DELETED'): 
            #OK so this is definitely not a duplicate as we are currently trying to handle it
            self.__connection.commit()
            return False   
          sqlResult = cursor.fetchone()
    
      initialState = 'INITIAL'
      if duplicate and not self.AllowDuplicates(fileToInsert):
        initialState = 'PENDING_DELETE_DUPLICATE'
      
      sql = '''INSERT INTO `files` (`filename`, `state`, `creationDate`) VALUES (%s,%s,%s);'''
      createTime = time.strftime("%Y:%m:%d %H:%M:%S", time.localtime(os.path.getctime(fileToInsert)))
      cursor.execute(sql, (fileToInsert,initialState,createTime))
      print("Adding to DB: " + fileToInsert + " in state " + initialState)
      
      self.__connection.commit()
      return True   
    
  def UpdateWithFiles(self, fileScanner):
    count = 0
    self.VerifyTables()
    for fileToInsert in fileScanner.GetScannedFiles():
      if self.InsertIfDoesntExist(fileToInsert, fileScanner.IsVerbose()) == True:
        count = count + 1
    
    return count
    
  def GetQueue(self):
    queue = []
    with self.__connection.cursor() as cursor:
      sql = '''SELECT `id`, `filename`, `state`, `filetype`, `creationDate` FROM `files` WHERE NOT `state` in ('ERROR','SUCCESS','DUPLICATE_DELETED') ORDER BY `id` ASC;'''
      cursor.execute(sql)
      row = cursor.fetchone()
      while row is not None:
        queue.append(ScannedFile(row))
        row = cursor.fetchone()
    
    return queue
  
  def UpdateQFState(self, queuedFile, operation, message):
    with self.__connection.cursor() as cursor:
      sql = '''INSERT INTO `file_history` (`file_id`, `operation`, `what_happened`) VALUES (%s,%s,%s);'''
      cursor.execute(sql, (queuedFile.GetId(), operation, message,))
      sql = '''UPDATE `files` SET `state`=%s WHERE `id`=%s;''';
      cursor.execute(sql, (queuedFile.GetState().name, queuedFile.GetId(),))
    self.__connection.commit()
  
  def UpdateQFFiletype(self, queuedFile, operation, message):
    with self.__connection.cursor() as cursor:
      sql = '''INSERT INTO `file_history` (`file_id`, `operation`, `what_happened`) VALUES (%s,%s,%s);'''
      cursor.execute(sql, (queuedFile.GetId(), operation, message,))
      sql = '''UPDATE `files` SET `filetype`=%s WHERE `id`=%s;''';
      cursor.execute(sql, (queuedFile.GetFiletype(), queuedFile.GetId(),))
    self.__connection.commit()
  
  def AddQFHistory(self, queuedFile, operation, message):
    with self.__connection.cursor() as cursor:
      sql = '''INSERT INTO `file_history` (`file_id`, `operation`, `what_happened`) VALUES (%s,%s,%s);'''
      cursor.execute(sql, (queuedFile.GetId(), operation, message,))
    self.__connection.commit()
    
  def __exit__(self, _exc_type, _exc_value, _traceback):
    self.__connection.close()
