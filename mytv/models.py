# -*- coding: utf-8 -*-
#Copyright 2010 Lorenzo Benfenati
#This file is part of MMC.
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

import random
from datetime import *

from django.db import models
from django.db.models import Avg, Max, Min, Count, Variance

from mmc.mymc.models import File, Title
from mmc.streamer.models import StreamProcess


class Pool (models.Model):
    """Group of file or titles
    """
    PLAY_MODE = (  ('R', 'Random'),
                   ('S', 'Sequence')
                   )
    LINK_MODE = (('F','File Mode'),
                ('T','Title Mode'))
    name = models.CharField(max_length=255)
    searchstr = models.CharField(max_length=255, null = True, blank=True)
    descr = models.CharField(max_length=700, null = True, blank=True)
    playmode = models.CharField (max_length=1, choices=PLAY_MODE)
    linktitle = models.ForeignKey (Title, null = True, blank=True)
    linkmode = models.CharField (max_length=1, choices=LINK_MODE, default='T')
    autoupdate = models.BooleanField(default=False)
    lastelementplayed = models.IntegerField(null = True, blank=True)
    avgduration = models.FloatField(null = True, blank=True)
    
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)
    
    def __unicode__(self):
        return self.name
   
    def save(self):
        self.update_avg()
        super(Pool, self).save()

    def update_avg(self):
        pe = PoolElement.objects.filter(pool = self)
        if pe:
            avgd = pe.aggregate(Avg('duration'))
            self.avgduration = avgd['duration__avg']
        else:
            self.avgduration = 0

    def first_element(self):
        pe = PoolElement.objects.filter(pool = self)
        if pe:
            pe = pe.order_by('order')
            return pe[0]
        return 0
    def next_order(self):
        pe = PoolElement.objects.filter(id = self.lastelementplayed)
        if pe:
            nextp =  PoolElement.objects.filter(pool=self, order__gt=pe[0].order)
            if nextp:
                nextp = nextp.order_by('order')
                return nextp[0].order
        pe = self.first_element()
        if pe:
            return pe.order
        return 0
    
    def last_played (self):
        lastpe = PoolElement.objects.filter(id = self.lastelementplayed)
        if (lastpe 
            ):
            return lastpe[0]
        else:
            return self.first_element() 

    def now_playing (self):
        lastpe = PoolElement.objects.filter(id = self.lastelementplayed)
        if (lastpe 
            and lastpe[0].lastplayed 
            and (lastpe[0].lastplayed+timedelta(minutes=lastpe[0].duration*0.9))>datetime.now()
            ):
            #The element is still playing
            return lastpe[0]
        else:
            return None

    def next_element(self):
        """Next element:
        if playmode = 'R' just get a random element 
        if playmode = 'S' returns: None if lastelementplayed is the last element in the pool, 
                                    else it returns the next element in PoolElement.order
        """
        if self.playmode == 'R':
            ep = PoolElement.objects.filter(pool=self)
            return ep[random.randint(0, len(ep)-1)]
        elif self.playmode == 'S':
            lastpe = PoolElement.objects.filter(id = self.lastelementplayed)
            if lastpe:
                ep = PoolElement.objects.filter(pool=self, order__gt=lastpe[0].order)
            else:
                ep = PoolElement.objects.filter(pool=self)
            if ep:
                return ep.order_by("order")[0]
            else: 
                return None
        return
    
    def update_link(self):
        if self.linktitle:
            if self.linkmode == 'T':
                eplist = self.linktitle.get_episodes_titles()
                pelist = [x.title for x in PoolElement.objects.filter(pool=self)]
                for ep in eplist:
                    if ep not in pelist:
                        e = ep.get_episode()
                        s = ep.get_season()
                        max_order = PoolElement.objects.filter(pool = self).aggregate(Max("order")) 
                        newpe = PoolElement(pool = self, 
                                            title = ep,
                                            order = max_order['order__max'] if not e else (100 if not s else 100*s) + e,
                                            duration = 30 if not ep.runtime else ep.runtime
                                            )
                        newpe.save()



class PoolElement(models.Model):
    """Element of a pool.
    Can be a File or Title.
    It can be specified a duration different to the video duration in order to postpone the start of the next video
    """
    pool = models.ForeignKey (Pool)
    title = models.ForeignKey (Title, null = True, blank=True)
    file = models.ForeignKey (File, null = True, blank=True)
    order = models.IntegerField( null = True, blank=True)
    duration = models.IntegerField( default = 30, blank=True)
    lastplayed =  models.DateTimeField (null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s %s: %s %s"%(self.pool, self.order, self.title, self.file)

    
class Channel (models.Model):
    PLAY_MODE = (  ('RR', 'Random'),
                   ('AS', 'Alternate'),
                   ('AC', 'Alternate Continuous')
                   )
    name = models.CharField(max_length=255)
    descr = models.CharField(max_length=700, null = True, blank=True)
    logo = models.ImageField( upload_to = 'usermedia/mytv', null = True, blank=True)
    start = models.TimeField()
    playmode = models.CharField (max_length=2, choices=PLAY_MODE)
    lastpoolplayed = models.IntegerField ( null = True, blank=True)
    streamprocess = models.ForeignKey (StreamProcess, null = True, blank=True)
    reservedport = models.IntegerField( null = True, blank=True)
    creation =  models.DateTimeField ( auto_now_add = True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return self.name
    
    def start_string(self):
        return self.start.strftime("%H:%M")
    def next_order(self):
        cp = ChannelPool.objects.filter(channel=self)
        if cp:
            cp =cp.order_by('-order')
            return cp[0].order+1
        return 1

    def first_pool(self):
        ep = ChannelPool.objects.filter(channel=self)
        if ep:
            return ep.order_by("order")[0]
        else: 
            return None
    
    def now_playing(self):
        if (self.playmode == 'AS'):
            ep = ChannelPool.objects.filter(channel=self)
            today = date.today()
            start = datetime.combine(today, self.start)
            for i in ep:
                if (datetime.now()>=start+timedelta(minutes = int(i.sumavgduration-i.pool.avgduration)) 
                    and datetime.now()<=start+timedelta(minutes = int(i.sumavgduration))):
                    self.lastpoolplayed = i.id
                    self.save()
                    return i
        else:
            lastp = ChannelPool.objects.filter(id=self.lastpoolplayed)
            if lastp and lastp[0].pool.now_playing():
                return lastp[0]
        return None

    def save(self):
        self.update_cp_duration()
        super (Channel,self).save()

    def update_cp_duration(self):
        cp = ChannelPool.objects.filter(channel=self)
        if cp:
            cp = cp.order_by("order")
            for c in cp:
                c.update_avg_duration()
                c.save()
    
    def last_played (self):
        lastp = ChannelPool.objects.filter(id=self.lastpoolplayed)
        return lastp[0] if lastp else self.first_pool()

    def next_pool (self):
        """Next pool:
        if playmode = 'R' just get a random pool (random channels are virtually endless)
        if playmode = 'SS' returns: the current pool (lastpoolplayed) if the current element in pool (lastelementplayed) is not the last element in the pool, 
                                    else it returns the next pool in ChannelPool.order
        if playmode = 'AS' returns next pool in ChannelPool.order
        playmode 'AC' and 'SC' 
        """
        def next_or_none():
            lastp = ChannelPool.objects.filter(id=self.lastpoolplayed)
            ep=None
            if lastp:
                ep = ChannelPool.objects.filter(channel=self, order__gt=lastp[0].order)
            if ep:
                return ep.order_by("order")[0]
            else: 
                return None
        
        if self.playmode == 'RR':
            cp = ChannelPool.objects.filter(channel=self)
            return cp[random.randint(0, len(cp)-1)]
        else:
            cp = next_or_none()
            #if (self.playmode == 'AS'): 
                #TODO: Real alternate
            #    return cp if cp else self.first_pool() 
            #elif (self.playmode == 'AC'): 
                #or (self.playmode == 'SC' 
                #    and not lastp[0].pool.next_element())#last element of pool
                #):
            toplay =  cp if cp else self.first_pool()
            self.lastpoolplayed = toplay.id
            self.save()
            return toplay
            #elif (self.playmode in ('SS', 'SC') 
            #      and lastp[0].pool.next_element()):
            #    return lastp[0]
        return

    
class ChannelPool (models.Model):
    channel = models.ForeignKey (Channel)
    pool = models.ForeignKey (Pool)
    order = models.IntegerField(null = True, blank=True)
    lastplayed = models.DateTimeField (null = True, blank=True)
    sumavgduration = models.FloatField (default=0.0,blank=True )
    creation = models.DateTimeField (auto_now_add = True)
    lastmodified = models.DateTimeField (auto_now = True)
        
    def __unicode__(self):
        return "%s %s: %s"%(self.channel, self.order, self.pool)

#    def save(self):
#        self.update_avg_duration()
#        super(ChannelPool, self).save()

    def update_avg_duration (self):
        cp = ChannelPool.objects.filter(channel = self.channel, order__lt=self.order)
        if cp:
            cp = cp.order_by('-order')
            self.sumavgduration = self.pool.avgduration + cp[0].sumavgduration
        else:
            self.sumavgduration = self.pool.avgduration


