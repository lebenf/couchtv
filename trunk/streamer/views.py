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

import threading, re, datetime, os, subprocess

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response,get_object_or_404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.template import RequestContext

from couchtv.mymc.models import File
from couchtv.streamer.runcommand import RunCommand
from couchtv.settings import *
from couchtv.mymc.views import view_file
from couchtv.streamer.models import StreamProcess



if 'VLC_BIN' not in vars().keys():
    VLC_BIN='cvlc'

if 'VLC_OPTS' not in vars().keys():
    VLC_OPTS=['--http-host %(host):port']

if 'PORT_POOL' not in vars().keys():
    PORT_POOL=['8888']


def stream_file(request, file_id):
    port = None
    for i in PORT_POOL:
        st = StreamProcess.objects.filter(port = i, endtime__isnull = True )
        st2 = StreamProcess.objects.filter(port = i, endtime__gte = datetime.datetime.now() )
        if not (st or st2):
            port = i
            break
    if port:
        fileo=get_object_or_404(File,pk=file_id)
        length = fileo.length 
        if not length and fileo.title:
            length = fileo.title.runtime
        if not length:
            length = 240 #set default duration to 4 hours
        st = StreamProcess(file= fileo , 
                           command = "%s %s"%(VLC_BIN, " ".join([fileo.full_path() , "--sout", "#std{access=http,mux=ts,dst=0.0.0.0:%s}"%(port),
                               "--extraintf", "http", "--http-host", "0.0.0.0:9888"])),
                           endtime=datetime.datetime.now()+datetime.timedelta(seconds=length*60),
                           port = port)
        st.save()
        t = threading.Thread(target=__stream_file,
                            args=[st, fileo, port]
                            )
        t.daemon=True
        t.start()
        host =  re.findall("([^:]*)",request.get_host())
        host = "" if not host else host[0]
        resp = render_to_response('playlist.xspf',{'port':port, 'ip':host},context_instance=RequestContext(request))
        resp['Content-Disposition'] = """attachment; filename="playlist.xspf" """
        resp['Content-Type'] = 'application/xspf+xml'
        return HttpResponseRedirect(reverse(control_process, args=[st.id]))
    else:
        return render_to_response('errorprocess.html',{},context_instance=RequestContext(request))

def playlist (request, proc_id):
    proco=get_object_or_404(StreamProcess,pk=proc_id)
    host =  re.findall("([^:]*)",request.get_host())
    host = "" if not host else host[0]
    resp = render_to_response('playlist.xspf',{'port':proco.port, 'ip':host},context_instance=RequestContext(request))
    resp['Content-Disposition'] = """attachment; filename="playlist.xspf" """
    resp['Content-Type'] = 'application/xspf+xml'
    return resp


def __stream_file ( process, fileo, port):
    #TODO: non far partire due stream sulla stessa porta
    vlc = RunCommand(VLC_BIN)
    vlc.runcommand([fileo.full_path() , "--sout", "#std{access=http,mux=ts,dst=0.0.0.0:%s}"%(port),
        "--play-and-exit","--extraintf", "http", "--http-host", "0.0.0.0:%s"%(port+1) ] )
    process.pid = vlc.go.pid
    process.save()
    os.waitpid(vlc.go.pid,0)
    process.endtime = datetime.datetime.now()
    process.save()

def show_process(request):
    p_list=StreamProcess.objects.all()
    p_list=p_list if not p_list else p_list.order_by('-starttime')
    paginator = Paginator(p_list, 50)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    
    try:
        proc = paginator.page(page)
    except (EmptyPage, InvalidPage):
        proc = paginator.page(paginator.num_pages)
    
    data={'p_list':proc}
    return render_to_response('showprocess.html',data,context_instance=RequestContext(request))

def control_process(request,proc_id):
    proco=get_object_or_404(StreamProcess,pk=proc_id)
    host =  re.findall("([^:]*)",request.get_host())
    host = "" if not host else host[0]
    port = proco.port+1                
    data={'proc':proco, 'host': host, 'port':port
          }
    return render_to_response('controlprocess.html',data,context_instance=RequestContext(request))

def view_process(request,proc_id):
    proco=get_object_or_404(StreamProcess,pk=proc_id)
    data={'proc':proco
          }
    return render_to_response('viewprocess.html',data,context_instance=RequestContext(request))

def restart_process(request,proc_id):
    import signal
    proco=get_object_or_404(StreamProcess,pk=proc_id)
    if _check_process_alive(proco.pid):
        try: 
            os.kill(proco.pid, signal.SIGKILL)
        except:
            pass
            #raise
    port = proco.port
    fileo=proco.file
    length = fileo.length 
    if not length and fileo.title:
            length = fileo.title.runtime
    if not length:
            length = 240 #set default duration to 4 hours
    proco.starttime = datetime.datetime.now()
    proco.endtime = datetime.datetime.now()+datetime.timedelta(seconds=length*60)
    proco.save()
    t = threading.Thread(target=__stream_file,
                            args=[proco, fileo, port]
                            )
    t.daemon=True
    t.start()
    return HttpResponseRedirect(reverse(control_process, args=[proc_id]))

def kill_process(request,proc_id):
    import signal
    proco=get_object_or_404(StreamProcess,pk=proc_id)
    if _check_process_alive(proco.pid):
        try: 
            os.kill(proco.pid, signal.SIGKILL)
        except:
            pass
            #raise
    proco.endtime = datetime.datetime.now()
    proco.save()
    return HttpResponseRedirect(reverse(show_process))

def _check_process_alive(pid):
    cc = subprocess.Popen(["/bin/ps", "a", str(pid)], shell = False, stdout= subprocess.PIPE,close_fds=True)
    pslist = [x[4] for x in re.findall("(.+?)\s+(.*?)\s+(.*?)\s+(.*?)\s+(.*)",cc.stdout.read())]
    for ps in pslist:
        if "vlc" in ps:
            return True
    return False


