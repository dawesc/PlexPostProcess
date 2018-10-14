'''
Created on 28 Oct 2017

@author: chrisd
'''

from enum import Enum

class PlexPostProcessState(Enum):
    ERROR = 1
    SUCCESS = 2
    INITIAL = 3
    TRANSCODING = 4
    MOVING_FILES = 5
    DELETING_ORIGINAL_FILE = 6
    ADD_META = 7
    COMMSKIP = 8
    PENDING_DELETE_DUPLICATE = 9
    DUPLICATE_DELETED = 10
        
