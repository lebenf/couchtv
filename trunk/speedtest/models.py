# -*- coding: utf-8 -*-
#Copyright 2010 Lorenzo Benfenati
#This file is part of Speedtest4MMC.
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
#along with MyMovieCollection. If not, see <http://www.gnu.org/licenses/>from django.db import models

#from  django.contrib.sessions.models import Session 
import re

from django.db import models


class Client(models.Model):
    sessionkey = models.CharField(max_length=500)
    speed = models.FloatField( null = True, blank=True)
    realspeed = models.FloatField( null = True, blank=True)
    latency = models.FloatField( null = True, blank=True)
    screenheight = models.IntegerField( null = True, blank=True)
    screenwidth = models.IntegerField( null = True, blank=True)
    useragent = models.CharField(max_length=500, null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s (%s), %s"%(self.sessionkey, self.speed, self.creation)
    
    def rightquality(self):
        """Valuta nel suo insiemela velocita' di connessione, la dimensione
        dello schermo e il tipo di client e ritorna un valore: 
         ('L', 'Low'),
         ('S', 'Standard (480p)'),
         ('H', 'HD (720p)'),
         ('F', 'Full HD (1080p)'),
         T - test
         """
        mobile_list = re.compile(".*?((Android)|(iPod)|(iPhone)|(Palm)|(webOS)|(MIDP)|(Maemo)|(SymbianOS)).*")
        if (self.screenwidth < 800 
                or mobile_list.match(self.useragent)
                or self.realspeed < 500000):
            #il client ha uno schermo molto piccolo, non se ne fa niente di
            #un'alta qualita'
            #oppure 
            #e' telefono
            #oppure
            #la velocita' connessione e' bassa
            return 'L'
        if (self.screenwidth < 1280
            or self.realspeed < 800000):
            #il client ha uno schermo abbastanza piccolo 
            #oppure
            #la connessione non sopporterebbe qualcosa di meglio
            return 'S'
        if (self.screenwidth < 1920
            or self.realspeed < 4000000):
            return 'H'
        if not self.realspeed:
            return 'T'
        return 'F'
    
    def guessedrightquality(self):
        """Valuta nel suo insiemela velocita' di connessione, la dimensione
        dello schermo e il tipo di client e ritorna un valore: 
         ('L', 'Low'),
         ('S', 'Standard (480p)'),
         ('H', 'HD (720p)'),
         ('F', 'Full HD (1080p)'),
         T - test
         """
        mobile_list = re.compile(".*?((Android)|(iPod)|(iPhone)|(Palm)|(webOS)|(MIDP)|(Maemo)|(SymbianOS)).*")
        if (self.screenwidth < 800 
                or mobile_list.match(self.useragent)
                or self.speed < 10000):
            #il client ha uno schermo molto piccolo, non se ne fa niente di
            #un'alta qualita'
            #oppure 
            #e' telefono
            #oppure
            #la velocita' connessione e' bassa
            return 'L'
        if (self.screenwidth < 1280
            or self.speed < 20000):
            #il client ha uno schermo abbastanza piccolo 
            #oppure
            #la connessione non sopporterebbe qualcosa di meglio
            return 'S'
        if (self.screenwidth < 1920
            or self.speed < 30000):
            return 'H'
        return 'F'




class Page(models.Model):
    client = models.ForeignKey(Client)
    page = models.CharField(max_length = 33)
    pagesize = models.IntegerField(null= True, blank = True)
    speed = models.FloatField( null = True, blank=True)
    latency = models.FloatField( null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s (%s), %s"%(self.page, self.client, self.speed)

class PageEvent(models.Model):
    EVENT_CHOICES = (
        ('S', 'Send'),
        ('L', 'Page Load'),
        ('P', 'Ping'),
    )
    page = models.ForeignKey(Page)
    event = models.CharField(max_length = 1)
    creation =  models.DateTimeField ()
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s (%s), %s"%(self.page, self.event, self.creation)

class ClientEvent(models.Model):
    EVENT_CHOICES = (
        ('B', 'Download start'),
        ('E', 'Download end')
    )
    client = models.ForeignKey(Client)
    event = models.CharField(max_length = 1)
    creation =  models.DateTimeField ( )
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s (%s), %s"%(self.client, self.event, self.creation)

