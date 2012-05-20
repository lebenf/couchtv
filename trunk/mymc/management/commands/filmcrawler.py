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

import os
import sys
import hashlib
import mmap
import sqlite3
import re
import types

from django.core.management.base import NoArgsCommand
try:
    import kaa.metadata as metadata 
except:
    metadata = None

from mymc.models import *


class TooManyFilesInFileError (EnvironmentError):
    pass

class IsNotAFileError (EnvironmentError):
    pass

class FileNotExistsError (EnvironmentError):
    pass

class IsNotADirectoryError (EnvironmentError):
    pass



class FileInfo:
    CHUNKSIZE = 1000000
    SIZELIMIT = 10000000
    CHUNKNO = 2
    
    YES = 1
    NO = 0

    def __init__ (self, filepath ):
        if not os.path.exists(filepath):
            raise FileNotExistsError
        if not os.path.isfile(filepath):
            raise IsNotAFileError
        self.filepath = filepath
        self.statfile = os.stat(self.filepath)
        self.name = os.path.basename(filepath)
        self.size = self.statfile.st_size

    def hashfile(self, md5 = 1, sha1 = 0, sha512 = 0 ):
        if not (md5 or sha1 or sha512) :
            raise RuntimeError
        if self.statfile.st_size == 0:
            self.md5 = ""
            self.sha1 = ""
            self.sha512 = ""
            return
        fd = open (self.filepath, 'rb')
        if self.statfile.st_size > self.SIZELIMIT and self.CHUNKNO >1:
            start = fd.read(self.CHUNKSIZE)
            fd.seek(self.statfile.st_size/self.CHUNKNO, os.SEEK_SET)
            mid = fd.read(self.CHUNKSIZE)
            fd.seek(self.statfile.st_size-self.CHUNKSIZE, os.SEEK_SET)
            end = fd.read(self.CHUNKSIZE)
            fdmap = start+mid+end
        else:
            fdmap = fd.read()
        self.md5 = None if not md5 else hashlib.md5(fdmap).hexdigest()
        self.sha1 = None if not sha1 else hashlib.sha1(fdmap).hexdigest()
        self.sha512 = None if not sha512 else hashlib.sha512(fdmap).hexdigest()
        
        return
        
    def __hashfilemmap(self, md5 = 1, sha1 = 0, sha512 = 0 ):
        if not (md5 or sha1 or sha512) :
            raise RuntimeError
        if self.statfile.st_size == 0:
            self.md5 = ""
            self.sha1 = ""
            self.sha512 = ""
            return
        
        fd = open (self.filepath, 'rb')
        try:
            fdmap = mmap.mmap(fd.fileno(),0)
        except:
            print self.filepath
            print self.statfile.st_size
            raise
        if self.statfile.st_size > self.SIZELIMIT and self.CHUNKNO >1:
            fdmap = (fdmap[:self.CHUNKSIZE]+ 
                    fdmap[self.statfile.st_size/self.CHUNKNO:(self.statfile.st_size/self.CHUNKNO)+self.CHUNKSIZE] +
                    fdmap[-self.CHUNKSIZE:])

        self.md5 = None if not md5 else hashlib.md5(fdmap).hexdigest()
        self.sha1 = None if not sha1 else hashlib.sha1(fdmap).hexdigest()
        self.sha512 = None if not sha512 else hashlib.sha512(fdmap).hexdigest()
        fd.close()
        return


class FillInfo:
    def __init__(self, storage):
        """ Prende in input un oggetto Storage definito nei modelli
        """
        self.storage = storage
        self.path = storage.localpath
        self.extensions = ['AVI', 'MKV', 'MP4', 'MPG','VOB', 'WMV',
        'MPEG','OGV','OGM','DIVX']
        self.relang = re.compile("\[(.*?)\]")
        self.langlist = {'IT':"Italian",
                         'EN':"English",
                         'ITA':"Italian",
                         'ENG':"English",
                         'DE':"German",
                         'FR':"French",
                         'JP':"Japanese",
                         }
        #self.filelist = DBConn()
        #self.filelist.cur.execute("""create table filelist (md5 , sha1, sha512, name, path, size)""")

    def __file_extractor(self, path):
        retval = {'container': None,
                  'quality': None,
                  'videocodec': None,
                  'audiocodec': None,
                  }
        if metadata:
            info = metadata.parse(path)
            if not info:
                return retval
            retval['container']=info.type
            try:
                hs = info.video[0].height
            except:
                hs = None
            if hs < 300:
                retval['quality']= 'L'
            elif hs < 500: 
                retval['quality']= 'S'
            elif hs < 800: 
                retval['quality']= 'H'
            elif hs < 1200: 
                retval['quality']= 'F'
            try:
                hs = info.video[0].codec
            except:
                pass
            else:
                retval['videocodec']= hs
            try:
                hs = info.audio[0].codec
            except:
                pass
            else:
                retval['audiocodec']= hs
            try:
                retval['length']=int(info.length)
            except:
                pass
        return retval
                    
            
#Out[14]:
#[(u'mimetype', u'video/x-msvideo'),
# (u'size', u'704x400'),
# (u'format', u'codec: xvid, 25 fps, 1407840 ms')]

    
    def __walk(self, path, action):
        if not os.path.isdir(path):
            raise IsNotADirectoryError
        lista = os.listdir(path)
        for l in lista:
            lpath = os.path.join(path,l)
            if os.path.isdir(lpath):
                diri = self.__walk (lpath, action)
            elif os.path.isfile(lpath):
                action(lpath)

    def __insert(self,lpath):
        if lpath.upper().split(".")[-1] in self.extensions:
            filei = FileInfo(lpath)
            filei.hashfile()
            info = self.__file_extractor(lpath)
            try:
                langs = self.__get_language(filei.name)
                self.__check_insert_lang(langs)
                ff = File(filename = filei.name,
                          path = filei.filepath.replace(self.path,""),
                          size = filei.statfile.st_size,
                          storage = self.storage,
                          hash = filei.md5,
                          hashtype = 'MP',
                          quality = info['quality'], 
                          container = info['container'],
                          videocodec = info['videocodec'],
                          audiocodec = info['audiocodec'],
                          length = info['length']
                          )
                ff.save()
                for l in Language.objects.filter(name__in = langs):
                    ff.language.add(l.id)
                ff.save()
            except:
                print (filei.md5, filei.sha1, filei.sha512, filei.name,
                                            filei.filepath,
                                            filei.statfile.st_size, )
                raise 
        return

    def __get_language(self, filename):
        langs = self.relang.findall(filename)
        #print langs
        retlist = []
        for l in langs:
            #if (type(l)==types.StringTypes 
            #    and 
            if l.upper() in self.langlist:#):
                #print "retlist"
                retlist.append (self.langlist[l.upper()])
        return retlist
    
    def __check_insert_lang(self, langs):
        for l in langs:
            ll = Language.objects.filter(name=l)
            if not ll:
                newl = Language(name=l)
                newl.save()
        
    def __update(self,lpath):
        #print "update"
        if lpath.upper().split(".")[-1] in self.extensions:
            filei = FileInfo(lpath)
            filei.hashfile()
            #info = self.__file_extractor(lpath)
            ff = File.objects.filter(#filename = filei.name,
                          path = filei.filepath.replace(self.path,""),
                          valid = True
                          )
            if len(ff)>1:
                raise TooManyFilesInFileError
            elif ff:
                if not (ff[0].hash == filei.md5 
                    and ff[0].hashtype == 'MP'):
                    info = self.__file_extractor(lpath)
                    ff[0].hash == filei.md5 
                    ff[0].hashtype == 'MP'
                    ff[0].quality = info['quality']
                    ff[0].container = info['container']
                    ff[0].videocodec = info['videocodec']
                    ff[0].audiocodec = info['audiocodec']
                    ff[0].save()
                    return
                #else:
                    #print info
                    #ff[0].quality = info['quality']
                    #ff[0].container = info['container']
                    #ff[0].videocodec = info['videocodec']
                    #ff[0].audiocodec = info['audiocodec']
                    #ff[0].save()
                    #it's already there
            else:
                langs = self.__get_language(filei.name)
                #print langs
                self.__check_insert_lang(langs)
                info = self.__file_extractor(lpath)
                try:
                    ff = File(filename = filei.name,
                              path = filei.filepath.replace(self.path,""),
                              size = filei.statfile.st_size,
                              storage = self.storage,
                              hash = filei.md5,
                              hashtype = 'MP',
                              quality = info['quality'], 
                              container = info['container'],
                              videocodec = info['videocodec'],
                              audiocodec = info['audiocodec'],
                              )
                    ff.save()
                    for l in Language.objects.filter(name__in = langs):
                        #print l
                        ff.language.add(l.id)
                    ff.save()
                except:
                    print (filei.md5, filei.sha1, filei.sha512, filei.name,
                                                filei.filepath,
                                                filei.statfile.st_size, )
                    raise 
        return
    
    def clean(self):
        ff = File.objects.all()
        for f in ff:
            if not f.file_exists():
                f.delete_and_merge()
    
    def fill (self):
        self.__walk(self.path, self.__insert)
    
    def update(self):
        self.__walk(self.path, self.__update)


class Command(NoArgsCommand):
    help = "Whatever you want to print here"
    option_list = NoArgsCommand.option_list 

    def handle_noargs(self, **options):
        stlist = Storage.objects.filter(support = 'L')
        for s in stlist:
            print s
            fi = FillInfo(s)
            print "Updating..."
            fi.update()
        for s in stlist:
            fi = FillInfo(s)
            print "cleanup"
            fi.clean()

