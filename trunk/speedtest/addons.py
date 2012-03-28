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

import random
import string
from datetime import *

from django.db.models import Avg

from mmc.speedtest.models import *

DWNSIZE = 500*1024

jsfunction = """
<script type="text/javascript">
function loaddate ()
{
   $.post('/event/',
       {pageid: '%(pageid)s', size: $('html').html().length, event: 'L',
       prevt:'%(prevt)s', width:screen.width, height:screen.height}, 
       function(data){});
   $.post('/event/',
       {pageid: '%(pageid)s', size: $('html').html().length, event: 'P',
       width:screen.width, height:screen.height}, 
       function(data){}); 
}
function testspeed ()
{
   $.post('/event/',
       {pageid: '%(pageid)s', event: 'B', width:screen.width,
       height:screen.height}, 
       function(data){});
   $.get('/rnddownload/', function(data){x=data;});
   $.post('/event/',
       {pageid: '%(pageid)s', event: 'E', width:screen.width,
       height:screen.height}, 
       function(data){}); 
}
</script>
"""
myprintables = string.ascii_letters+string.digits

tot_seconds = lambda td: ((td.microseconds + (td.seconds + td.days * 24.0 * 3600) * 10**6) / 10**6)

def speedtoken(request):
    """
    """
    pageid = "".join([random.choice(myprintables) for x in xrange(32)] ) 
#    cs = Client.objects.filter(sessionkey = request.COOKIES['sessionid'])
#    if not cs:
#        cs= Client(sessionkey = request.COOKIES['sessionid'])
#        cs.save()
#    else:
#        cs = cs[0]
#    pg = Page(client = cs, page = pageid)
#    pg.save()
#    ev = PageEvent(page = pg, event = 'S' )
#    ev.save()
    return {'speed_token': jsfunction%{'pageid':pageid, 'prevt': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}, 
            'onload_speed': """onload="loaddate()" """,
            'test_speed': """<a onclick="testspeed()" href="#">TestSpeed</a> """,
            }

def update_client(sessionid):
    cs = Client.objects.filter(sessionkey = sessionid)
    if cs:
        cs= cs[0]
    else:
        return
    aggr = Page.objects.filter(client = cs).aggregate(avg_speed=Avg('speed'), avg_latency=Avg('latency'))
    cs.speed = aggr['avg_speed']
    cs.latency = aggr['avg_latency']
    cs.save()    

def update_client_dwnl(sessionid):
    cs = Client.objects.get(sessionkey = sessionid)
    if not cs:
        return
    send = ClientEvent.objects.filter(client = cs, event = 'B')
    finish = ClientEvent.objects.filter(client = cs, event = 'E')
    if send and finish:
        cs.realspeed =  1.0*DWNSIZE/tot_seconds(finish[0].creation-send[0].creation)
        cs.save()
        send[0].delete() 
        finish[0].delete() 
        
def update_page(pageid):
    pg = Page.objects.filter(page = pageid)
    if pg:
        pg = pg[0]
    else:
        return
    send = PageEvent.objects.get(page = pg, event = 'S')
    load = PageEvent.objects.get(page = pg, event = 'L')
    ping = PageEvent.objects.get(page = pg, event = 'P')
    if send and load and ping:
        pg.latency = tot_seconds(ping.creation - load.creation)
        pg.speed = 1.0*pg.pagesize/(tot_seconds(load.creation -
            send.creation)-pg.latency)
        pg.save()
        send.delete()
        load.delete()
        ping.delete()
        update_client(pg.client.sessionkey)


