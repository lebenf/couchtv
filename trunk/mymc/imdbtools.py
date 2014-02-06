# -*- coding: utf-8 -*-
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

import types
import imdb
from mymc.models import *
from django.db import transaction
from django.core.files.images import ImageFile
import re
import urllib
from settings import *

listdilemma = lambda x: x if (type(x) != types.ListType ) else None if len(x)==0 else x[0]
def floatdilemma (num):
    try:
        res = float(num)
    except:
        return None
    return res

if 'QUICK_INSERTS_IMDB' not in vars().keys():
    if 'sqlite2' in DATABASES['default']['ENGINE']:
        QUICK_INSERTS_IMDB = 1
    else:
        QUICK_INSERTS_IMDB = 0


CONTENT_EXTENSION = {'image/png': ".png",
                     'image/jpeg': ".jpg" }

class Movie(dict):
    def __init__(self, dicti, **kwargs):
        super(Movie,self).__init__(dicti, **kwargs)
        self.movieID = self.get('movieid', None)
    def getID(self):
        self.movieID = self.get('movieid', None)
        return self.movieID


class IMDBtools:

    def __init__(self, proxy=None, source = 'http', dburi = ''):
        if source == 'http':
            self.con = imdb.IMDb(accessSystem=source)
        else:
            self.con = imdb.IMDb(accessSystem=source, uri = dburi)
        if proxy:
            self.con.set_proxy(proxy)
        self.res = None
    
    def _imdb_to_movie(self, imdbmovie):
        episodes=[]
        for e in imdbmovie.get('episodes', []):
            episodes.append(Movie({'movieid': imdbmovie.movieID,
                   'title': imdbmovie.get('title'),
                   'canonical title': imdbmovie.get('canonical title'),
                   'kind': listdilemma(imdbmovie.get('kind')),
                   'year': listdilemma(imdbmovie.get('year')),
                   'akas': imdbmovie.get('akas', []),
                   'episodes': imdbmovie.get('episodes', []),
                   'plot': listdilemma(imdbmovie.get('plot')),
                   'plot outline': listdilemma(imdbmovie.get('plot')),
                   'rating': floatdilemma(listdilemma(imdbmovie.get('rating'))),
                   'color info': listdilemma(imdbmovie.get('color info')),
                   'runtimes': listdilemma(imdbmovie.get('runtimes',None)),
                   'languages': imdbmovie.get('languages'),
                   'country': imdbmovie.get('country'),
                   'season': imdbmovie.get('season'),
                   'episode': imdbmovie.get('episode'),
                   }) )
            
        mm= Movie({'movieid': imdbmovie.movieID,
                   'title': imdbmovie.get('title'),
                   'canonical title': imdbmovie.get('canonical title'),
                   'kind': listdilemma(imdbmovie.get('kind')),
                   'year': listdilemma(imdbmovie.get('year')),
                   'akas': imdbmovie.get('akas', []),
                   'episodes': episodes,
                   'plot': listdilemma(imdbmovie.get('plot')),
                   'plot outline': listdilemma(imdbmovie.get('plot')),
                   'rating': floatdilemma(listdilemma(imdbmovie.get('rating'))),
                   'color info': listdilemma(imdbmovie.get('color info')),
                   'runtimes': listdilemma(imdbmovie.get('runtimes',None)),
                   'languages': imdbmovie.get('languages'),
                   'country': imdbmovie.get('country'),
                   'season': imdbmovie.get('season'),
                   'episode': imdbmovie.get('episode'),
                   })
        return mm
        
        
        
    
    def searchMovie (self, title = None , imdbid = None):
        if not (title or imdbid):
            raise RuntimeError("IMDButils.searchMovie need title or imdbid")
        if imdbid:
            movie = self.con.get_movie(imdbid)
            return  [self._imdb_to_movie(movie)]
        else:
            self.searchres = self.con.search_movie(title)
            return [self._imdb_to_movie(x) for x in self.searchres]


#    @transaction.commit_on_success
#    def insertSerie(self, sresult, serie, tit):
#        self.con.update(sresult, "episodes")
#        for e in sresult['episode'][serie]:
#            self.insertEpisode(sresult, serie,e, tit)

    def getSeries(self, sresult):
        sresult = self.con.get_movie(sresult['movieid'])
        self.con.update(sresult, "episodes")
        retval = {} 
        for season in sorted(sresult['episodes'].keys()):
            retval[season] = {}
            for episode in sorted(sresult['episodes'][season].keys()):
                retval[season][episode] = self._imdb_to_movie(sresult['episodes'][season][episode])
        return retval


    @transaction.commit_on_success
    def insertEpisode(self, ep, parentid, season = None, episode=None):
        """primo parametro id imdb dell'episodio,
        secondo parametro id "interno" della serie (già inserita quindi nel db),
        terzo e quarto numero serie e episodio """
        parent = Title.objects.filter(id=int(parentid))
#        print parent
        #ep = sresult[serie][episode]
        #self.con.update(ep)

        newep = self.insertMovie(ep)
        er = Relation.objects.filter(parent = parent[0],
                                    title = newep)

        try:
            season=int(season)
        except:
            season=ep['season']
        try:
            episode=int(episode)
        except:
            episode=ep['episode']
        if not er:
            rel = Relation(parent = parent[0],
                            title = newep,
                            relation= 'T',
                            tvseason = season,
                            tvepisode = episode)
            rel.save()
        else:
            #If relation already exists we update it
            er[0].tvseason = season
            er[0].tvepisode = episode
            er[0].save()
        return newep


    @transaction.commit_on_success
    def insertMovie (self, sresult):
        tit = Title.objects.filter(externalid=sresult.movieID, source = 'I')
        if tit:
            #print tit
            return tit[0]
#        print " sto per inserire "
        sresult = self.con.get_movie(sresult['movieid'])
        self.con.update(sresult)
        tit = self.insertTitle(sresult)
#        print "inserito"
        for a in  sresult.get('cast', []):
            try: 
                a.currentRole
            except:
#                print a.keys()
##                print a
                a = DumbPerson()
            pers = self.insertPerson(a)
            if pers:
                if hasattr(a.currentRole, '__add__'):
                    for role in a.currentRole:
                        r = self.insertRole(tit, pers, role.get('name'), 'A')
                else:
                    r = self.insertRole(tit, pers, a.currentRole.get('name'), 'A')
        for d in sresult.get('director',[]):
            pers = self.insertPerson(d)
            r = self.insertRole(tit, pers, None , 'D')
        for p in sresult.get('producer',[]):
            pers = self.insertPerson(p)
            r = self.insertRole(tit, pers, None , 'P')
        for w in sresult.get('writer',[]):
            pers = self.insertPerson(w)
            r = self.insertRole(tit, pers, None , 'W')
        for m in sresult.get('original music',[]):
            pers = self.insertPerson(m)
            r = self.insertRole(tit, pers, None , 'M')


        return tit

    def insertTitle (self, sresult):
        rerun = re.compile("\d+")
        runtime = listdilemma(sresult.get('runtimes',None))
        if runtime:
            allrun = rerun.findall(runtime)
            runtime = allrun[0] if allrun else runtime

        #print sresult
#        if type(sresult.get('runtimes',[None])[0]) == types.IntType:
#            runtime = sresult['runtimes'][0]
#        else:
#            runtime = None
        #print sresult.get('color info')
        title = sresult.get('episode title',"").encode('utf-8') if not( sresult.get('episode title',"") and sresult['kind']=='episode') else sresult.get('title',"??").encode('utf-8')
        t = Title(title = sresult.get('title',"??").encode('utf-8')[:255],
            year = listdilemma(sresult.get('year', None)),
            type = listdilemma(sresult.get('kind', None)),
            titlesort = listdilemma(sresult.get('canonical title', ""))[:255],
            #aka = "; ".join(sresult.get('akas', None)),
            externalid = sresult.movieID,
            source = 'I',
            plot = listdilemma(sresult.get('plot', None)),
            plotoutline = sresult.get('plot outline', None),
            rating = floatdilemma(listdilemma(sresult.get('rating', None))),
            runtime = runtime,
            color = listdilemma(sresult.get('color info', None)) ,
            coverurl = listdilemma(sresult.get('cover url', None))
            )
        if listdilemma(sresult.get('cover url', None)):
            tc = urllib.urlopen(listdilemma(sresult.get('cover url', None)))
            ic = ImageFile(tc)
            ic.size = int(tc.info().dict['content-length'])
            ext = CONTENT_EXTENSION.get(tc.info().dict['content-type'], "")
            t.cover.save("%s%s"%(str(sresult.movieID), ext), ic)
        try:
            t.save()
        except :
            #print sresult.values
            raise
        if 'akas' in sresult.keys():
            self._insertAkas(t, sresult['akas'])
        if 'languages' in sresult.keys():
            self._insertLanguage(t, sresult['languages'])
        if 'country' in sresult.keys():
            self._insertCountry(t, sresult['country'])
        if 'genres' in sresult.keys():
            self._insertGenre(t, sresult['genres'])
        return t

    def updateTitle (self, titleid):
        try:
            t = Title.objects.get(id=titleid)
        except:
            return
        if t.source == 'I':
            sresult = self.con.get_movie(t.externalid) 
        else:
            return 
        rerun = re.compile("\d+")
        runtime = listdilemma(sresult.get('runtimes',None))
        if runtime:
            allrun = rerun.findall(runtime)
            runtime = allrun[0] if allrun else runtime
        #title = sresult.get('episode title',"").encode('utf-8') if not( sresult.get('episode title',"") and sresult['kind']=='episode') else sresult.get('title',"??").encode('utf-8')
        title = sresult.get('title',"??").encode('utf-8')
        t.title = title
        t.year = listdilemma(sresult.get('year', None))
        t.type = listdilemma(sresult.get('kind', None))
        t.titlesort = listdilemma(sresult.get('canonical title', None))
        #aka = "; ".join(sresult.get('akas', None)),
        t.source = 'I'
        t.plot = listdilemma(sresult.get('plot', None))
        t.plotoutline = sresult.get('plot outline', None)
        t.rating = floatdilemma(listdilemma(sresult.get('rating', None)))
        t.runtime = runtime
        t.color = listdilemma(sresult.get('color info', None)) 
        try:
            t.save()
        except :
            return 
        return t

#    def __savecover (self, url, cover, name):
#        tc = urllib.urlopen(listdilemma(sresult.get('cover url', None)))
#        ic = ImageFile(tc)
#        ic.size = int(tc.info().dict['content-length'])
#        ext = CONTENT_EXTENSION.get(tc.info().dict['content-type'], "")
#        cover.save("%s%s"%(name, ext), ic)



    def _insertAkas(self, titleid, akas):
        if type(akas) == types.ListType:
            for a in akas:
                try:
                    self._insertAka(titleid, a )
                except:
                    #print akas
                    raise
        else :
            try:
                self._insertAka(titleid, akas)
            except:
                #print akas
                raise

    def _insertAka (self, titleid, aka):
        akp = Aka.objects.filter(title=titleid.id, akatitle=aka)
        if akp:
            return akp[0]
        akn = Aka (title = titleid, akatitle = aka[:255])
        akn.save()
        return akn

    def _insertLanguage(self, title, langlist):
        for l in langlist:
            ll = Language.objects.filter(name=l)
            if not ll:
                ll = Language(name = l)
                ll.save()
            else:
                ll = ll[0]
            tl = TitleLanguage.objects.filter(title = title,
                                              language = ll)
            #print tl
            if not tl:
                tl = TitleLanguage(title = title,
                                   language = ll,
                                   source = 'I')
                tl.save()
    def _insertCountry(self, title, countrylist):
        for c in countrylist:
            lc = Country.objects.filter(name=c)
            if not lc:
                lc = Country(name = c)
                lc.save()
            else:
                lc = lc[0]
            tc = TitleCountry.objects.filter(title = title,
                                              country = lc)
            #print tc
            if not tc:
                tc = TitleCountry(title = title,
                                              country = lc,
                                              source = 'I')
                tc.save()

    def _insertGenre(self, title, genrelist):
        for g in genrelist:
            lg = Genre.objects.filter(name=g)
            if not lg:
                lg = Genre(name = g)
                lg.save()
            else:
                lg = lg[0]
            tg = TitleGenre.objects.filter(title = title,
                                              genre = lg,
                                              source = 'I')
            #print tg
            if not tg:
                tg = TitleGenre(title = title,
                                              genre = lg)
                tg.save()


    def insertPerson(self, pers):
        try:
            pers.personID
        except AttributeError:
            #PERS is not a valid pbject, maybe a imdblib error
            pers =DumbPerson()
        act = Person.objects.filter(externalid= pers.personID, source = 'I')
        if act:
            #print "ip ", act
            return act[0]
        if not QUICK_INSERTS_IMDB :
            try:
               self.con.update(pers)
            except:
                raise
        act = Person(
            name = pers.get('name', "")[:255],
            namesort = pers.get('canonical name', "")[:255],
            birthstr = pers.get('birth date', None) ,
            deathstr = pers.get('death date', None),
            bio = listdilemma(pers.get('mini biography', None)),
            birthname = pers.get('birth name', "")[:255],
            externalid = pers.personID,
            source = 'I',
            imgurl = pers.get('headshot', None),
            )
        if pers.get('headshot', None):
            ph = urllib.urlopen(pers.get('headshot'))
            ih = ImageFile(ph)
            ih.size = int(ph.info().dict['content-length'])
            ext = CONTENT_EXTENSION.get(ph.info().dict['content-type'], "")
            act.img.save("%s%s"%(str(pers.personID), ext), ih )
        act.save()
        return act

    def insertRole (self, title, person, name, type):
        cast = Cast(
                title = title ,
                person = person,
                name = name,
                role = type,
                source = 'I'
                )
        try:
            cast.save()
        except:
            #print title
            #print person
            #print name
            #print type
            raise
        return cast

class DumbRole:
    def get(self, obj, default=None):
        if obj == 'name':
            return "No One"
        return default

class DumbPerson:
    personID="noone"
    currentRole = DumbRole()
    def get(self, obj, default=None):
        if obj == 'name':
            return "No One"
        return default



