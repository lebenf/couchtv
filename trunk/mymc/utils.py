#Copyright 2010 Lorenzo Benfenati, Andrea Zucchelli
#This file is part of MyMovieCollection.
#
#MyMovieCollection is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License version 3 as published by
#the Free Software Foundation.
#
#MyMovieCollection is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with MyMovieCollection. If not, see <http://www.gnu.org/licenses/>
__copyright__ = "Copyright 2010,  Lorenzo Benfenati, Andrea Zucchelli"
__license__ = "AGPL v3"

import re

from django.db.models import Q


def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
#THANKS to Julien Phalip 
# http://www.julienphalip.com/blog/2008/08/16/adding-search-django-site-snap/
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:
        
        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    
    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
    '''
    query = None # Query to search for every search term        
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    #query = query | Q(**{"%s__icontains" % field_name: query_string})
    return query

class FileToKeys:
    import re
    
    #from mymc.models import *
    
    def __init__(self):
        self.relist = ["\[.*?\]", "\.+", "HDTV","XVID","-","FQM","2HD",'AVI','MKV', 'MP4', 'MPG',
                       'VOB', 'WMV', "DVDSCR", "MSPAINT", "XII", "NOTV", "AAF", 'PROPER', 'DVDRIP', "SAINS", "LOL",
                    "PDTV", "XOR", "SILENT", "BDRIP", "FFT", "_", "DONE"]
        self.reseries = re.compile("(.*?)((S(\d+).*?E(\d+))|((\d+)X(\d+)))")
        self.renome = re.compile("|".join("(%s)"%(x) for x in self.relist ))
        self.respaces = re.compile("(\s+)")
        self.reseason = re.compile (".*?SEASON.*")
        self.reseasonno = re.compile (".*?SEASON\s*(\d+)")
        self.reseriebad = re.compile("((\d)(\d{2}))|((\d{2})(\d{2}))|((\d+).{1,3}(\d+))|(SEASON\s*(\d+)\s*EPISODE\s*(\d+))")
        self.reonlyseason = re.compile ("SEASON.*")
        self.reepisode = re.compile ("(\d\d)|(\d)")
    
    def __get_keys_episode (self, subbed, file):
        serie = self.reseries.findall(subbed)
        #print subbed
        #print serie
        keyslist = serie[0][0]
        if not keyslist:
            #no keylist, maybe the name of the series is in the full path
            psplit = file.path.upper().split("/")
            pfirst = psplit[-2] #directory containing episodes, may be "Season x"
            psecond = psplit[-3] #if pfirst is "Season x" this should be the series name
            if self.reonlyseason.match(pfirst):
                #pfirst is "Season x"
                keyslist = self.renome.sub(" ",psecond)
            else:
                keyslist = self.renome.sub(" ",pfirst)
            keyslist = self.reonlyseason.sub(" ", keyslist)#eventually remove "Season" from the search keys
            keyslist = self.respaces.sub(" ", keyslist)
        keyslist = keyslist.split()
        skeys = {'type': 'episode',
                'keys': keyslist,
                'season': int(serie[0][3] or serie[0][6]),
                'episode': int(serie[0][4] or serie[0][7]) }
        return skeys
        
    def __get_keys_episode_bad (self, subbed, file):
        film = self.reseriebad.findall(subbed)
        if film:
            season =  film[0][1] or film[0][4] or film[0][7] or film[0][10]
            episode = film[0][2] or film[0][5] or film[0][8] or film[0][11]
        else:
            psplit = file.path.upper().split("/")
            sse = self.reseasonno.findall(psplit[-2])
            season = "" if not sse else sse[0][0]
            sep = self.reepisode.findall (subbed)
            episode = "" if not sep else sep[0][0]
        #print "season", season
        #print "episode", episode
        psplit = file.path.upper().split("/")
        pfirst = psplit[-2] #directory containing episodes, may be "Season x"
        psecond = psplit[-3] #if pfirst is "Season x" this should be the series name
        if self.reonlyseason.match(pfirst):
            #pfirst is "Season x"
            keyslist = self.renome.sub(" ",psecond)
        else:
            keyslist = self.renome.sub(" ",pfirst)
        keyslist = self.reonlyseason.sub(" ", keyslist)#eventually remove "Season" from the search keys
        keyslist = self.respaces.sub(" ", keyslist)
        keyslist = keyslist.split()
        skeys = {'type': 'episode',
                'keys': keyslist,
                'season': season if not season else int(season),
                'episode': episode if not episode else int(episode) }
        return skeys
            
    def get_keys(self, file):
        subbed = self.renome.sub(" ",file.filename.upper())
        subbed = self.respaces.sub(" ", subbed)
        #print file 
        #print subbed
        if "VTS " in subbed:
            #dvd file
            psplit = file.path.upper().split("/")
            if "VIDEO_TS" == psplit[-2]:
                keyslist = self.renome.sub(" ", psplit[-3]) #if psplit[-2] is "VIDEO_TS" this should be the movie name
            else:
                keyslist = self.renome.sub(" ", psplit[-2])
            keyslist = self.reonlyseason.sub(" ", keyslist)#eventually remove "Season" from the search keys
            keyslist = self.respaces.sub(" ", keyslist)
            keyslist = keyslist.split()
            skeys ={'type': 'film',
                'keys': keyslist
                }
            return skeys        
        elif self.reseason.match(file.path.upper()):
            #it's a series for sure
            if self.reseries.match(subbed):
                return self.__get_keys_episode(subbed, file)
            else:
                return self.__get_keys_episode_bad (subbed, file)
        elif self.reseries.match(subbed):
            return self.__get_keys_episode(subbed, file)
                
        else:
            return {'type': 'film',
                'keys': subbed.split()
                }
        return 

class groupby(dict):
    """Thanks to Raimond Hettinger
    http://code.activestate.com/recipes/259173/
    """
    def __init__(self, seq, key=lambda x:x):
        for value in seq:
            k = key(value)
            self.setdefault(k, []).append(value)
    __iter__ = dict.iteritems


class FileIterWrapper(object):
    """Thanks to Dan Farina (fdr) 
    http://metalinguist.wordpress.com/2008/02/12/django-file-and-stream-serving-performance-gotcha/
    """
    def __init__(self, flo, chunk_size = 1024**2):
      self.flo = flo
      self.chunk_size = chunk_size

    def next(self):
      data = self.flo.read(self.chunk_size)
      if data:
        return data
      else:
        raise StopIteration

    def __iter__(self):
      return self


