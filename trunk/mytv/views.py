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
from datetime import *

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response,get_object_or_404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.template import RequestContext
from django.http import Http404

from couchtv.mymc.models import File, Title
from couchtv.streamer.runcommand import RunCommand
from django.contrib.auth.decorators import login_required
from couchtv.settings import *
from mymc.views import search_titles_akas, search_file, view_title, view_file, download_file
from mymc.views import view_title, view_file
from couchtv.mytv.models import Pool, PoolElement, Channel, ChannelPool

import re


if 'VLC_BIN' not in vars().keys():
    VLC_BIN='cvlc'

if 'PORT_POOL' not in vars().keys():
    PORT_POOL=['8888']

@login_required
def build_pool(request, pool_id=None):
    """
    it helps building a pool
    titles and file can be added to pools
    user have to write a search query for titles or files
    the results of the two searches is presented in the same column on the left
    on the right there are the files/titles already present in the pool 
    """
    def get_pool_el (pool):
        pe = PoolElement.objects.filter(pool = pool)
        return pe if not pe else pe.order_by("order")
    def modify_pool_el(post):
        delre = re.compile("delete_(\d+)")
        orderre = re.compile("poolorder_(\d+)")
        for k in post.keys():
            delete = delre.findall(k)
            newo = orderre.findall(k)
            if newo:
                pe = PoolElement.objects.get(id=int(newo[0]))
                try:
                    pe.order=int(post[k])
                    pe.save()
                except:
                    pass
            elif delete:
                pe = PoolElement.objects.get(id=int(delete[0]))
                pe.delete()
              
    def insert_pool (post,pool):
        titlere = re.compile("addtitle_(\d+)")
        filere = re.compile("addfile_(\d+)")
        for k in post.keys():
            files = filere.findall(k)
            titles = titlere.findall(k)
            if files:
                pe = PoolElement(pool = pool, file_id = int(files[0]))
                pe.order = pool.next_order()
                pe.save()
            if titles:
                pe = PoolElement(pool = pool, title_id = int(titles[0]))
                pe.order = pool.next_order()
                pe.save()

    if request.method == 'POST':
        if pool_id:
            #search is done or the pool has been modified or some titles/files has been added
            #update pool
            #return the search result in ...
            #and the pool content and the pool information
            p = get_object_or_404(Pool,pk=pool_id)
            p.name = request.POST['poolname']
            p.descr = request.POST['pooldescr']
            p.playmode = request.POST['playmode']
            p.save()
            modify_pool_el(request.POST)
            if request.POST.has_key('searchtoadd'):
                titles = search_titles_akas(request.POST['searchtoadd'])
                files = search_file(request.POST['searchtoadd'])
                ss = request.POST['searchtoadd']
            else:
                titles = []
                files = []
                ss = ""
            insert_pool(request.POST, p)
            data = {'titles':titles,'files':files, 'titlesearch':ss, 'pool':p, 'poolcontent':get_pool_el(p)}
            
        else:
            #new pool
            #create new pool from the form
            if request.POST.has_key('poolname') and request.POST.has_key('pooldescr'):
                p = Pool(name = request.POST['poolname'],
                         descr = request.POST['pooldescr'])
                p.save()
                data = {'titles':{},'files':{}, 'titlesearch':"", 'pool':p, 'poolcontent':get_pool_el(p)}
            else:
                raise Http404
            pass
    else:
        if pool_id:
            #show pool content
            p = get_object_or_404(Pool,pk=pool_id)
            data = {'titles':{},'files':{}, 'titlesearch':"", 'pool':p, 'poolcontent':get_pool_el(p)}
            pass
        else:
            #new pool
            #return empty everything 
            data = {'titles':{},'files':{}, 'titlesearch':"", 'pool':{}, 'poolcontent':[]}
    return render_to_response('buildpool.html', data, context_instance=RequestContext(request))

@login_required
def update_pool(request, pool_id):
    p = get_object_or_404(Pool, pk=pool_id)
    p.update_link()
    return HttpResponseRedirect(reverse(view_pool,args=[p.id])) 

@login_required
def series_to_pool(request, title_id):
    t = get_object_or_404(Title, pk=title_id)
    if t.is_series():
        p = Pool(name=t.title, playmode='S', linktitle_id = t.id)
        p.save()
        p.update_link()
    return HttpResponseRedirect(reverse(view_pool,args=[p.id])) 
#        for e in t.get_episodes_titles():
#            pe = PoolElement(pool = p, title = e, duration = e.runtime if e.runtime else t.runtime ) 
#            if e.get_season():
#                pe.order = int("%02d%02d"%(e.get_season() , e.get_episode()))
#            pe.save()
#        p.save()
#        return HttpResponseRedirect(reverse(view_pool,args=[p.id]))
#    else:
#        return
#    return

@login_required
def set_last_element(request, pool_id, element_id):
    p=None
    try:
        #pe = PoolElement.objects.get(id=element_id)
        p = Pool.objects.get(id=pool_id)
    except: 
        pass
    if p:
        p.lastelementplayed = element_id
        p.save()
    return HttpResponse("0", mimetype="text/plain")

@login_required
def play_pool(request, pool_id):
    p = get_object_or_404(Pool,pk=pool_id)
    now = p.now_playing()
    if not now:
        now = _next_pool(p)
    if now.title:
        return HttpResponseRedirect(reverse(view_title,args=[now.title_id]))
    elif now.file:
        return HttpResponseRedirect(reverse(view_file,args=[now.file_id]))
    return

@login_required
def play_pool_next(request, pool_id):
    p = get_object_or_404(Pool,pk=pool_id)
    now = _next_pool(p)
    if now.title:
        return HttpResponseRedirect(reverse(view_title,args=[now.title_id]))
    elif now.file:
        return HttpResponseRedirect(reverse(view_file,args=[now.file_id]))
    return

@login_required
def play_pool_replay(request, pool_id):
    p = get_object_or_404(Pool,pk=pool_id)
    now = p.last_played()
    if now.title:
        return HttpResponseRedirect(reverse(view_title,args=[now.title_id]))
    elif now.file:
        return HttpResponseRedirect(reverse(view_file,args=[now.file_id]))
    return


def _next_pool(pool_el):
    now = pool_el.next_element()
    if not now:
        now = pool_el.first_element()
    if not now:
        return
    now.pool.lastelementplayed = now.id
    now.pool.save()
    now.lastplayed = datetime.now()
    now.save()
    return now


def view_pool(request, pool_id):
    p = get_object_or_404(Pool,pk=pool_id)
    pe = PoolElement.objects.filter(pool = p)
    pe = pe if not pe else pe.order_by("order")
    data = {'pool':p, 'poolcontent':pe}
    return render_to_response('viewpool.html', data, context_instance=RequestContext(request))


def podcast_pool(request, pool_id):
    p = get_object_or_404(Pool,pk=pool_id)
    pe = PoolElement.objects.filter(pool = p)
    pe_last = p.last_played()
    pe = pe if not pe else pe.order_by("order")
    last_order = pe[len(pe)-1].order
    last_played = p.last_played()
    pl = {'title': p.name,
		    'pool_id':p.id,
        'description': p.descr,
        'link': request.build_absolute_uri(),
        'pubDate': datetime.now().isoformat(),
        'generator':'CouchTV V0.0.0.1',
        'item':[],}
    for this_pe in pe:
        item_pe = {}
        if this_pe.file:
	    item_pe ['title']= this_pe.file.filename
	    item_pe ['description']= this_pe.file.filename
	    item_pe ['guid']= this_pe.file.full_path()
	    item_pe ['enclosure']= this_pe.file
	    item_pe ['poolelement']= this_pe
	    item_pe ['pubDate']= datetime.now().isoformat()
	    item_pe ['sortorder'] = this_pe.order+ (0 if this_pe.order > last_played.order else last_order)
	    pl['item'].append(item_pe)
	elif this_pe.title:
	    files = this_pe.title.get_files()
	    if files:
	        item_pe ['title']= this_pe.title.title
	        item_pe ['description']= this_pe.title.subtitle
	        item_pe ['guid']= this_pe.title.titlesort
	        item_pe ['poolelement']= this_pe
	        item_pe ['enclosure']= files[0]
	        item_pe ['pubDate']= datetime.now().isoformat()
	        item_pe ['sortorder'] = this_pe.order+ (0 if this_pe.order > last_played.order else last_order)
		pl['item'].append(item_pe)
    pl['item'].sort(lambda a, b: cmp(a['sortorder'], b['sortorder']))
    return render_to_response('podcastpool.xml', pl, context_instance=RequestContext(request))

def play_pool_element(request, pool_elem):
    pe = get_object_or_404(PoolElement,pk=pool_elem)
    pe.pool.lastelementplayed = pe.id
    pe.pool.save()
    pe.lastplayed = datetime.now()
    pe.save()
 
    if pe.file:
        return HttpResponseRedirect(reverse(download_file,args=[pe.file.id]))
    elif pe.title:
	files = pe.title.get_files()
	for f in files:
	    if f.valid:
                return HttpResponseRedirect(reverse(download_file,args=[f.id]))
    raise Http404
    

def __paginator(request, itemlist, length = 20):
    paginator = Paginator(itemlist, length)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        retval= paginator.page(page)
    except (EmptyPage, InvalidPage):
        retval = paginator.page(paginator.num_pages)
    retval.previous_ten = page-10
    retval.next_ten = page+10
    retval.length = length
    return retval


def show_pool(request):
    pools=Pool.objects.order_by('name')
    pools = __paginator(request, pools)
    data={'pools':pools}
    return render_to_response('showpool.html',data,context_instance=RequestContext(request))

@login_required
def build_channel(request, channel_id=None):
    """
    it helps building a channel
    pools can be added to channels
    user have to write select pool to be added from the column to the left
    on the right there are the pools already present in the channel 
    """
    def get_channel_el (channel):
        ch = ChannelPool.objects.filter(channel = channel)
        return ch if not ch else ch.order_by("order")
    def modify_channel_el(post):
        delre = re.compile("delete_(\d+)")
        orderre = re.compile("channelorder_(\d+)")
        for k in post.keys():
            delete = delre.findall(k)
            newo = orderre.findall(k)
            if delete:
                pe = ChannelPool.objects.get(id=int(delete[0]))
                pe.delete()
            elif newo:
                pe = ChannelPool.objects.get(id=int(newo[0]))
                try:
                    pe.order=int(post[k])
                    pe.save()
                except:
                    pass
    def insert_channel (post,channel):
        poolre = re.compile("addpool_(\d+)")
        for k in post.keys():
            pools = poolre.findall(k)
            if pools:
                pe = ChannelPool(channel = channel, pool_id = int(pools[0]))
                pe.order = channel.next_order()
                pe.save()

    if request.method == 'POST':
        if channel_id:
            #search is done or the channel has been modified or some titles/files has been added
            #update channel
            #return the search result in ...
            #and the channel content and the channel information
            p = get_object_or_404(Channel,pk=channel_id)
            p.name = request.POST['channelname']
            p.descr = request.POST['channeldescr']
            p.playmode = request.POST['playmode']
            p.start = request.POST['start']
            p.save()
            modify_channel_el(request.POST)
            pools = Pool.objects.all()
            insert_channel(request.POST, p)
            p.save()
            data = {'pools':pools, 'channel':p, 'channelcontent':get_channel_el(p), 'playmode': Channel.PLAY_MODE, 
                    'startt':["%02d:%02d"%(x,y*10) for x in xrange(24) for y in xrange(6) ]}
        else:
            #new channel
            #create new channel from the form
            if request.POST.has_key('channelname') and request.POST.has_key('channeldescr'):
                p = Channel(name = request.POST['channelname'],
                         descr = request.POST['channeldescr'],
                         start = request.POST['start'])
                # p.start = p.string_in_start(request.POST['start'])
                p.save()
                data = {'pools':Pool.objects.all(), 'channel':p, 'channelcontent':get_channel_el(p), 'playmode': Channel.PLAY_MODE, 
                    'startt':["%02d:%02d"%(x,y*10) for x in xrange(24) for y in xrange(6) ]}
            else:
                raise Http404
    else:
        if channel_id:
            #show channel content
            p = get_object_or_404(Channel,pk=channel_id)
            data = {'pools':Pool.objects.all(), 'channel':p, 'channelcontent':get_channel_el(p), 'playmode': Channel.PLAY_MODE, 
                    'startt':["%02d:%02d"%(x,y*10) for x in xrange(24) for y in xrange(6) ]}
        else:
            #new channel
            #return empty everything 
            data = {'pools':{}, 'channel':{}, 'channelcontent':[], 'playmode': Channel.PLAY_MODE, 
                    'startt':["%02d:%02d"%(x,y*10) for x in xrange(24) for y in xrange(6) ]}
    return render_to_response('buildchannel.html', data, context_instance=RequestContext(request))

@login_required
def play_channel(request, channel_id):
    p = get_object_or_404(Channel,pk=channel_id)
    now = p.now_playing()
    if not now:
        now=p.next_pool()
        if not now:
            return HttpResponseRedirect(reverse(view_channel,args=[channel_id]))
        p.lastpoolplayed = now.id
        p.save()
    return HttpResponseRedirect(reverse(play_pool,args=[now.pool_id]))

@login_required
def play_channel_next(request, channel_id):
    p = get_object_or_404(Channel,pk=channel_id)
    now = p.next_pool()
    if not now:
        return HttpResponseRedirect(reverse(view_channel,args=[channel_id]))
    p.lastpoolplayed = now.id
    p.save()
    return HttpResponseRedirect(reverse(play_pool,args=[now.pool_id]))

@login_required
def play_channel_replay(request, channel_id):
    p = get_object_or_404(Channel,pk=channel_id)
    now = p.last_played()
    if not now:
        return HttpResponseRedirect(reverse(view_channel,args=[channel_id]))
    return HttpResponseRedirect(reverse(play_pool_replay,args=[now.pool_id]))

def view_channel(request, channel_id):
    p = get_object_or_404(Channel,pk=channel_id)
    pe = ChannelPool.objects.filter(channel = p)
    pe = pe if not pe else pe.order_by("order")
    data = {'channel':p, 'channelcontent':pe}
    return render_to_response('viewchannel.html', data, context_instance=RequestContext(request))

def show_channel(request):
    channels=Channel.objects.order_by('name')
    channels = __paginator(request, channels)
    data={'channels':channels}
    return render_to_response('showchannel.html',data,context_instance=RequestContext(request))





