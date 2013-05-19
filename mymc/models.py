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


import datetime
import os
from itertools import *

from django.db import models
from django.contrib.auth.models import User

from mymc.utils import FileToKeys

SOURCE_CHOICES = (
                   ('I', 'IMDB'),
                   ('U', 'USER')
                   )

# Create your models here.
class Title(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, null = True, blank=True)
    year = models.IntegerField( null = True, blank=True)
    type = models.CharField(max_length=15, null = True, blank=True)
    titlesort = models.CharField(max_length=255, null = True, blank=True)
    externalid = models.CharField(max_length=15, null = True, blank=True)
    source = models.CharField (max_length=1, choices=SOURCE_CHOICES, default= 'U')
    plot = models.TextField( null = True, blank=True)
    plotoutline = models.TextField( null = True, blank=True)
    rating = models.FloatField( null = True, blank=True)
    runtime = models.IntegerField( null = True, blank=True)
    color = models.CharField(max_length=100,  null = True, blank=True)
    coverurl = models.URLField( null = True, blank=True)
    cover = models.ImageField( upload_to = 'usermedia/title', null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return u"%s (%s) - %s"%(self.title, self.year, self.externalid)
    
    def is_series(self):
        return True if self.get_episodes_titles() else False
    
    def is_episode(self):
        return True if self.get_series_title() else False
    
    def get_series_title(self):
        rel = Relation.objects.filter(relation='T', title = self)
        if rel:
            return rel[0].parent
        else:
            return None

    def get_episodes_titles(self):
        return [x.title for x in Relation.objects.filter(relation='T', parent= self)]

    def get_episode(self):
        title = Relation.objects.filter(relation='T', title = self) 
        return None if not title else  title[0].tvepisode

    def get_season(self):
        title = Relation.objects.filter(relation='T', title = self)
        return None if not title else  title[0].tvseason
    
    def get_files(self):
        return File.objects.filter(title = self)

    def get_languages(self):
        return TitleLanguage.objects.filter(title = self)

    def get_genres(self):
        return TitleGenre.objects.filter(title = self)

    def get_countries(self):
        return TitleCountry.objects.filter(title = self)
    
    def get_userdata(self, user):
        return UserTitle.objects.filter(title = self, user = user)    
    
    class Meta:
        unique_together = (("externalid", "source"),)
        
    def save(self, *args, **kwargs):
        self.externalid=self.externalid if self.externalid else None
        self.titlesort=self.titlesort if self.titlesort else self.title
        super(Title, self).save(*args, **kwargs) 
        

class Aka (models.Model):
    title = models.ForeignKey (Title)
    akatitle = models.CharField(max_length=255)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

#a cosa serve?
#class Serie (models.Model):
#    title = models.CharField(max_length=255)
#    subtitle = models.CharField(max_length=255, null = True, blank=True)
#    year = models.IntegerField( null = True, blank=True)
#    plot = models.TextField( null = True, blank=True)
#    plotoutline = models.TextField( null = True, blank=True)
#    rating = models.FloatField( null = True, blank=True)
#    source = models.CharField (max_length=1, choices=SOURCE_CHOICES)
#    creation =  models.DateTimeField ( auto_now_add = True)
#    lastmodified = models.DateTimeField ( auto_now = True)


class Relation (models.Model):
    REL_CHOICES = (
                   ('T', 'TV Series'),
                   ('S', 'Saga'),
                   ('A', 'See Also'),
                   ('F', 'Special Feature'),
                   ('P', 'Playlist'),
                   ('C', 'Collection'),
                   )
    parent = models.ForeignKey (Title, related_name = "parent")
    title = models.ForeignKey (Title, related_name = "child")
    relation = models.CharField (max_length=1, choices=REL_CHOICES)
    tvseason = models.IntegerField( null = True, blank=True)
    tvepisode = models.IntegerField( null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        #parent = Title.objects.filter(id=self.parent)
        #titleid = Title.objects.filter(id=self.titleid)
        return u"%s - S%s E%s %s"%(self.parent, self.tvseason, self.tvepisode,
                self.title)

class Genre(models.Model):
    name =  models.CharField(max_length=100)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

class Language (models.Model):
    name =  models.CharField(max_length=100)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)
    def __unicode__(self):
        return u"%s"%self.name

class TitleGenre (models.Model):
    title = models.ForeignKey(Title)
    genre= models.ForeignKey(Genre)
    source = models.CharField (max_length=1, choices=SOURCE_CHOICES, default= 'U')
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

class TitleLanguage (models.Model):
    title = models.ForeignKey(Title)
    language = models.ForeignKey(Language)
    source = models.CharField (max_length=1, choices=SOURCE_CHOICES, default= 'U')
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

class Country (models.Model):
    name =  models.CharField(max_length=100)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

class TitleCountry (models.Model):
    title = models.ForeignKey(Title)
    country = models.ForeignKey(Country)
    source = models.CharField (max_length=1, choices=SOURCE_CHOICES, default= 'U')
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

class Tag (models.Model):
    tag = models.CharField(max_length=255)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

class UserTitle (models.Model):
    title = models.ForeignKey(Title)
    user = models.ForeignKey(User)
    rating = models.FloatField( null = True, blank=True)
    tag = models.ManyToManyField(Tag, null = True, blank=True)
    note = models.TextField( null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)


class Person(models.Model):
    name = models.CharField(max_length=255)
    namesort = models.CharField(max_length=255, null = True, blank=True)
    birth = models.DateTimeField('date of birth', null = True, blank=True)
    birthstr = models.CharField(max_length=50, null = True, blank=True)
    death = models.DateTimeField('date of birth', null = True, blank=True)
    deathstr = models.CharField(max_length=50, null = True, blank=True)
    bio = models.TextField( null = True, blank=True)
    birthname = models.CharField(max_length=255, null = True, blank=True)
    externalid = models.CharField(max_length=15, null = True, blank=True)
    source = models.CharField (max_length=1, choices=SOURCE_CHOICES, default= 'U')
    imgurl =  models.URLField( null = True, blank=True)
    img = models.ImageField( upload_to = 'usermedia/people', null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s %s"%(self.name,self.externalid)
    class Meta:
        unique_together = (("externalid", "source"),)
 
class Cast(models.Model):
    ROLE_CHOICES = (
        ('D', 'Director'),
        ('A', 'Actor'),
        ('W', 'Writer'),
        ('P', 'Producer'),
        ('M', 'Original Music'),
    )
    title = models.ForeignKey(Title)
    person = models.ForeignKey(Person)
    name = models.CharField(max_length=255,  null = True, blank=True )
    role = models.CharField(max_length=1, choices=ROLE_CHOICES)
    source = models.CharField (max_length=1, choices=SOURCE_CHOICES, default= 'U')
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s (%s), %s"%(self.name, self.person, self.role)

class Storage  (models.Model):
    SUPPORT_CHOICES = (
                   ('L', 'Local'),
                   ('R', 'Removable'),
                   ('N', 'Network')
                   )
    name = models.CharField(max_length=30)
    size = models.IntegerField( null = True, blank=True)
    support = models.CharField(max_length=1, choices=SUPPORT_CHOICES)
    localpath = models.CharField(max_length=1000)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)
    def __unicode__(self):
        return "%s (%s)"%(self.name, self.localpath)

class File (models.Model):
    
    HASHTYPE_CHOICES = (
                        ('MC', 'MD5 Complete'),
                        ('MP', 'MD5 Partial'),
                        ('1C', 'SHA1 Complete'),
                        ('1P', 'SHA1 Partial'),
                        ('5C', 'SHA512 Complete'),
                        ('5P', 'SHA512 Partial'),
                        )
    QUALITY_CHOICES = (
                        ('L', 'Low'),
                        ('S', 'Standard (480p)'),
                        ('H', 'HD (720p)'),
                        ('F', 'Full HD (1080p)'),
                        ('S', 'SHD (4k)'),
                        )
#    usertitle = models.ManyToManyField(UserTitle)
    title = models.ForeignKey(Title, null = True,blank=True)
    filename = models.CharField(max_length = 255)
    path = models.CharField(max_length=1000) #relative path to storage
    storage = models.ForeignKey(Storage)
    size = models.BigIntegerField( null = True, blank=True)
    hash = models.CharField(max_length = 1024, null = True,blank=True)
    hashtype = models.CharField(max_length=2, choices=HASHTYPE_CHOICES, null = True,blank=True)
    quality = models.CharField(max_length=1, choices=QUALITY_CHOICES, null = True,blank=True)
    container = models.CharField(max_length = 255,null = True,blank=True)
    videocodec = models.CharField(max_length = 255,null = True,blank=True)
    audiocodec = models.CharField(max_length = 255,null = True,blank=True)
    language = models.ManyToManyField(Language,null=True,blank=True)
    length = models.IntegerField( null = True, blank=True)
    valid = models.BooleanField(default = True)
    #mimetpe?
    creation = models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    
    def search_keys (self):
        sk = FileToKeys()
        return sk.get_keys(self)
    
    def full_path (self):
        return "%s%s"%(self.storage.localpath, self.path)
    
    def file_exists (self):
        return os.path.exists(self.full_path())
    
    def if_no_title_merge_same_file(self):
        if not self.title:
            others = File.objects.filter(hash = self.hash, hashtype = self.hashtype)
            titles = [x.title   for x in others]
            titles.sort()
            unique = [k for k,g in groupby(titles)]
            unique.remove(None)
            if len(unique) == 1:
                self.title = unique[0]
                self.save()
    def if_title_merge_same_file(self):
        if self.title:
            others = File.objects.filter(hash = self.hash, 
                                         hashtype = self.hashtype)
            for o in others:
                o.title = self.title
                o.save()

        
    def delete_and_merge(self):
        self.if_title_merge_same_file()
        self.valid=False
        self.save()
            
    
    def __unicode__(self):
        sk = self.search_keys()
        if sk['type'] == 'film':
            return "%s (%s %s)"%(self.path, sk['type'], " ".join(sk['keys']) )
        else:
            return "%s (%s %s s:%s e:%s)"%(self.path, sk['type'], " ".join(sk['keys']),
                                           sk['season'], sk['episode'] )
#        sk = self.search_keys()
#        return "%s (%s)"%(self.path, str(sk['type']) )
            

class RunningTask(models.Model):
    start_time=models.DateTimeField(auto_now_add=True)
    message=models.TextField()
    state=models.CharField(max_length=64)
    pid=models.IntegerField()
    host=models.CharField(max_length=255)
    user=models.ForeignKey(User,null=True)
    session=models.CharField(max_length=255,null=True)
