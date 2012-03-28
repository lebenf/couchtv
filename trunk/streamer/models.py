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

from mmc.mymc.models import File

class StreamProcess(models.Model):
    file = models.ForeignKey (File)
    pid = models.IntegerField( null = True, blank=True)
    port = models.IntegerField( null = True, blank=True)
    command = models.CharField(max_length=700, null = True, blank=True)
    starttime =  models.DateTimeField ( auto_now_add = True)
    endtime = models.DateTimeField (null = True, blank=True)
    lastmodified = models.DateTimeField ( auto_now = True)

    def __unicode__(self):
        return "%s %s"%( self.pid, self.port)
    