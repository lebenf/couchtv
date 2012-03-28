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
import string
from datetime import *
import random
import sys
import traceback

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
#from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response,get_object_or_404
from django.template import RequestContext
from django.http import Http404

from mmc.speedtest.models import *
from mmc.speedtest.addons import DWNSIZE
from mmc.mymc.models import File, Title
import addons


myprintables = string.ascii_letters+string.digits


def console_debug(f):
  def x(*args, **kw):
    try:
      ret = f(*args, **kw)
    except Exception, e:
      print >> sys.stderr, "ERROR:", str(e)
      exc_type, exc_value, tb = sys.exc_info()
      message = "Type: %s\nValue: %s\nTraceback:\n\n%s" % (exc_type, exc_value, "\n".join(traceback.format_tb(tb)))
      print >> sys.stderr, message
      raise
    else:
      return ret
  return x


def __client_event(sessionid, event, height, width, useragent):
    cs = Client.objects.filter(sessionkey = sessionid)
    if not cs:
        cs= Client(sessionkey = sessionid, screenheight = height,
                   screenwidth = width, useragent = useragent)
        cs.save()
    else:
        cs = cs[0]
    ev = ClientEvent(client = cs, event = event , creation = datetime.now())
    ev.save()
    
def __page_event(sessionid, pageid, event, pagesize, data, height, width,
        useragent):
    pg = Page.objects.filter(page = pageid)
    if not pg:
        cs = Client.objects.filter(sessionkey = sessionid)
        if not cs:
            cs = Client(sessionkey = sessionid, screenheight = height,
                    screenwidth = width, useragent = useragent)
            cs.save()
        else:
            cs = cs[0]
        pg = Page(client = cs, page = pageid, pagesize = pagesize)
        pg.save()
    else:
        pg = pg[0]
    ev = PageEvent(page = pg, event = event, creation = data)
    ev.save()
    
#@console_debug
def get_event(request):
    if request.is_ajax():
        if request.method == 'POST':
            message = 'OK'
            if request.POST['event'] in ['B','E']:
                __client_event(request.session.session_key,
                        request.POST['event'], request.POST['height'],
                        request.POST['width'], request.META['HTTP_USER_AGENT'] )
            elif request.POST['event'] == 'P':
                __page_event(request.session.session_key,request.POST['pageid'],
                        request.POST['event'], request.POST['size'],
                        datetime.now(), request.POST['height'],
                        request.POST['width'], request.META['HTTP_USER_AGENT'])
                addons.update_page(request.POST['pageid'])
            else:
                __page_event(request.session.session_key,request.POST['pageid'],
                        request.POST['event'], request.POST['size'], 
                        datetime.now(), request.POST['height'],
                        request.POST['width'], request.META['HTTP_USER_AGENT'])
                __page_event(request.session.session_key,request.POST['pageid'],  
                             'S', request.POST['size'],
                             datetime.strptime(request.POST['prevt'],"%Y-%m-%d %H:%M:%S.%f"), request.POST['height'],
                             request.POST['width'],
                             request.META['HTTP_USER_AGENT'])
            if request.POST['event'] == 'E':
                addons.update_client_dwnl(request.session.session_key)
        if request.method== 'GET':
            message = 'this is a post ajax view'
    else:
        message = "ajax view"
    return HttpResponse(message)

#@console_debug
def rnd_download(request):
    if request.is_ajax():
        if request.method == 'POST':
            return HttpResponse("")
        if request.method== 'GET':
            cs = Client.objects.filter(sessionkey = request.session.session_key)
            if not cs:
                cs= Client(sessionkey = request.session.session_key)
                cs.save()
            else:
                cs = cs[0]
            #ev = ClientEvent(client = cs, event = 'B' )
            #ev.save()
    else:
        return HttpResponse("")
    return HttpResponse("".join([random.choice(myprintables) for x in xrange(DWNSIZE)] ))

def download_smart (request, title_id):
    files = File.objects.filter(title = title_id)
    try:
        cl = Client.objects.get(sessionkey = request.session.session_key)
    except DoesNotExist:
        cl = None
    except:
        raise
    okfiles = []
    if cl:
        quality = cl.rightquality()
        if quality == 'T':
            quality = cl.guessedrightquality()
        for f in files:
            if f.quality == quality:
                okfiles.append(f)
    else:
        quality = 'T'
    if okfiles:
        data = {'files': okfiles, 'quality':quality, 'goodfile':True, 
                'title': title_id}
    else:
        data = {'files': files, 'quality':quality, 'goodfile':False, 
                'title': title_id }
    return render_to_response('download_smart.html',data,context_instance=RequestContext(request))



