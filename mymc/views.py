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

import threading
import os
import sys, re

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response,get_object_or_404
from django.template import RequestContext
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import condition
from django.contrib.auth import logout
from django.core.servers.basehttp import FileWrapper
from django.db.models import Avg, Max, Min, Count
from django.contrib.sites.models import RequestSite
import mymc.imdbtools as imdbtools
from mymc.forms import remote_search_form, remote_select_form, remote_select_episodes, \
                        search_form, storage_form, file_form
from settings import *
import models
import utils

if 'LOCAL_IMDB_URI' not in vars().keys():
    LOCAL_IMDB_URI=''

@login_required
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse(index))
  

@login_required
def remote_search(request):
    error=''
    if request.method=='POST':
        f=remote_search_form(request.POST)
        if f.is_valid():
            title=f.cleaned_data['title']
            source=f.cleaned_data['source']
            if source=='I':
                remote=imdbtools.IMDBtools(source = IMDB_ACCESS_SYSTEM, 
                        dburi = LOCAL_IMDB_URI)
                res=remote.searchMovie(title)
                #TODO: IMDB Error handling
            else:
                raise ValueError,"Invalid source: %s"%source
            if not res:
                error="La ricerca non ha portato risultati"
            else:
                request.session['remote_res']=res
                return HttpResponseRedirect(reverse(remote_select))
        else:
            pass
    else:
        f=remote_search_form()
    data={'form':f,'error':error, 'path': request.path}
    return render_to_response('remotesearch.html',data,context_instance=RequestContext(request))


def import_movie(task,movie, request = None):
    task.pid=os.getpid()
    task.state="running"
    task.save()
    remote=imdbtools.IMDBtools(source = IMDB_ACCESS_SYSTEM,
                                    dburi = LOCAL_IMDB_URI)
    try:
        mm = remote.insertMovie(movie)
    except Exception,e:
        task.state='error'
        task.message+=str(sys.exc_info())+str(e)
    else:
        task.state="done"
    if request.session.has_key('fileref'):
        __filetitle(request.session['fileref'], mm.id)
        del(request.session['fileref'])    
    task.save()
    return

def update_movie(task,titleid, request = None):
    task.pid=os.getpid()
    task.state="running"
    task.save()
    remote=imdbtools.IMDBtools(source = IMDB_ACCESS_SYSTEM,
                                    dburi = LOCAL_IMDB_URI)
    try:
        mm = remote.updateTitle(titleid)
    except Exception,e:
        task.state='error'
        task.message+=str(sys.exc_info())+str(e)
    else:
        task.state="done"
    if request.session.has_key('fileref'):
        __filetitle(request.session['fileref'], mm.id)
        del(request.session['fileref'])    
    task.save()
    return

def import_episodes(task,series,episodes, request = None):
    task.pid=os.getpid()
    task.state="running"
    task.save()
    try:
        remote=imdbtools.IMDBtools(source = IMDB_ACCESS_SYSTEM,
                                        dburi = LOCAL_IMDB_URI)
        res=remote.insertMovie(series)
#        print "inserito Movie"
        for e in episodes:
#            print e
#            print "Insert Episode %s [%s:%s] "%(e['movie'],e['season'],e['episode'])
            ep = remote.insertEpisode(e['movie'],res.id,e['season'],e['episode'])
    
    except Exception,e:
        task.message+=str(sys.exc_info())+str(e)
        task.state='error'
    else:
        task.state="done"
    if request.session.has_key('fileref'):
        __filetitle(request.session['fileref'], ep.id)
        del(request.session['fileref'])    
    task.save()
    return


@login_required
def remote_select(request):
    #We need the data from the previous search
    if not request.session.get('remote_res',None):
        raise Http404
    #Build choices for the form select
##    print request.session['remote_res']
    movie_choices=[(x.getID(),''.join(('[tv series] ' if str(x['kind']) in ['tv series','tv mini series'] else '',
                                    "%s (%s)"%(x['title'],x['year'])))
#in (this) version of imdbpy library the "smart long imdb canonical title" is broken
                                    ) for x in request.session['remote_res']]
    error=''
    if request.method=='POST':
        f=remote_select_form(request.POST,movie_choices=movie_choices)
        if f.is_valid():
            movie_id=f.cleaned_data['movie']
            movie = [x for x in request.session['remote_res'] if str(x.getID())==movie_id][0]
            if not( str(movie['kind']) in ['tv series','tv mini series']):
                #no series just a movie
                task=models.RunningTask()
                task.state="init"
                task.message="Importing movie id:%s from IMDb"%movie_id
                task.session=request.COOKIES['sessionid']
                task.host="localhost"
                task.pid=0
                task.save()
                #spawn a thread to retreive the movie
                t = threading.Thread(target=import_movie,
                                     args=[task, movie, request]
                                  )
                t.daemon=True
                t.start()
                del(request.session['remote_res'])
                return HttpResponseRedirect(reverse(poll_task,args=[task.id]))
            else:
                #series
                request.session['remote_series']=movie
                remote=imdbtools.IMDBtools(source = IMDB_ACCESS_SYSTEM,
                                        dburi = LOCAL_IMDB_URI)
                request.session['remote_episodes']=remote.getSeries(movie)
                del(request.session['remote_res'])
                return HttpResponseRedirect(reverse(remote_select_episode))


        else:
            pass
    else:
        f=remote_select_form(movie_choices=movie_choices)
    data={'form':f,'error':error}
    return render_to_response('remoteselect.html',data,context_instance=RequestContext(request))


@login_required
def update_title(request,title_id):
    redirect_to = request.REQUEST.get('next', '')
    if 'I'=='I':
        task=models.RunningTask()
        task.state="init"
        task.message="Updating movie id:%s from IMDb"%(title_id)
        task.session=request.COOKIES['sessionid']
        task.host="localhost"
        task.pid=0
        task.save()
        #spawn a thread to retreive the movie
        t = threading.Thread(target=update_movie,
                             args=[task, title_id, request]
                             )
        t.daemon=True
        t.start()
    return HttpResponseRedirect(redirect_to)

@login_required
def remote_add_episode(request,title_id):
    title=get_object_or_404(models.Title,pk=title_id)
    #TODO: gestione fonte remota
    if 'I'=='I':
        remote=imdbtools.IMDBtools(source = IMDB_ACCESS_SYSTEM,
                                        dburi = LOCAL_IMDB_URI)
        movie=remote.searchMovie(imdbid=title.externalid)[0]
        if not movie:
            raise Http404,"Can't find movie"
        request.session['remote_series']=movie       
        request.session['remote_episodes']=remote.getSeries(movie)
        return HttpResponseRedirect(reverse(remote_select_episode))
    else:
        raise Http404
    


@login_required
def remote_select_episode(request):
    if not request.session.get('remote_series',None):
        raise Http404
    if not request.session.get('remote_episodes',None):
        raise Http404
    error=''
    series=request.session['remote_series']
    episodes=request.session['remote_episodes']
    episode_choices=[]
    episode_list=[]
    
    for season in sorted(episodes.keys()):
        for episode in sorted(episodes[season].keys()):
            episodes[season][episode]['mytitle']="%s S%s E%s"%(episodes[season][episode]['title'], season, episode)  
            episode_choices.append((episodes[season][episode].getID(),"[%s:%s] %s "%(season,episode,episodes[season][episode]['title'])))
            episode_list.append({'movie':episodes[season][episode],'season':season,'episode':episode})
    if request.method=='POST':
        f=remote_select_episodes(request.POST,episode_choices=episode_choices)
        if f.is_valid():
            ep=f.cleaned_data['episodes']
            chosen_episodes=[x for x in episode_list if str(x['movie'].getID()) in ep]
            task=models.RunningTask()
            task.state="init"
            task.message="Importing episodes id:%s from IMDb"%str(ep)
            task.session=request.COOKIES['sessionid']
            task.host="localhost"
            task.pid=0
            task.save()
            t = threading.Thread(target=import_episodes,
                                    args=[task,series ,chosen_episodes, request]
                                 )
            t.daemon=True
            t.start()
            del request.session['remote_series']
            del request.session['remote_episodes']
            return HttpResponseRedirect(reverse(poll_task,args=[task.id]))
        else:
            pass
    else:
        f=remote_select_episodes(episode_choices=episode_choices)
    data={'episodes':episodes,'error':error}
    return render_to_response('remoteselectepisodes.html',data,context_instance=RequestContext(request))

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


def show_title(request):
    from django.db.models import Q
    if request.method != 'GET':
        raise Http404
    filters = {"all": None,
               "filmandtv": ( Q(id__in = [x.parent_id for x in models.Relation.objects.filter(relation='T')]) |
                              ~Q(id__in = [x.title_id for x in models.Relation.objects.filter(relation='T')])
                            ),
               "film": ( ~Q(id__in = [x.parent_id for x in models.Relation.objects.all()]) &
                         ~Q(id__in = [x.title_id for x in models.Relation.objects.filter(relation='T')])
                        ),
               "tv": Q(id__in = [x.parent_id for x in models.Relation.objects.filter(relation='T')]),
               "tvandepisodes": ( Q(id__in = [x.parent_id for x in models.Relation.objects.filter(relation='T')]) |
                                  Q(id__in = [x.title_id for x in models.Relation.objects.filter(relation='T')])
                                  ),
               "episodes": Q(id__in = [x.title_id for x in models.Relation.objects.filter(relation='T')]),
               "playlists": Q(id__in = [x.parent_id for x in models.Relation.objects.all()])
               }
    if 'filter' in request.GET.keys():
        filter = request.GET['filter']
    else:
        filter = "filmandtv"
    all_genres = models.Genre.objects.all()
    genres=[]
    if 'genres' in request.GET.keys():
        if request.GET['genres'] :
            genres = [x for x in request.GET.getlist('genres')]
            genre_q = Q(id__in=[x['title_id'] for x in  models.TitleGenre.objects.filter(genre__name__in= genres ).values('title_id').annotate(n_titles=Count('genre')).filter(n_titles = len(genres))])
        else:
            genre_q = Q(id__isnull=False)
    else:
        genre_q = Q(id__isnull=False)
            
    if filters.get(filter):
        title_list=models.Title.objects.filter(filters[filter]&genre_q).order_by("titlesort")
    else:
        title_list=models.Title.objects.filter(genre_q).order_by("titlesort")
    files = __paginator(request, title_list)
    data={'title_list':files, 'filters':filters.keys(),'genres':[x.name for x in all_genres], 'filter':filter,'genre':genres}
    return render_to_response('showtitle.html',data,context_instance=RequestContext(request))

def view_title(request,title_id):
    title=get_object_or_404(models.Title,pk=title_id)
    relations_member=models.Relation.objects.filter(title=title.id)
    #title is part of a relation (child)
    relations_parent=models.Relation.objects.filter(parent=title.id)
    #title is part of a relation (parent)
    if relations_parent and relations_parent[0].relation == 'T':
        relations_season = utils.groupby(relations_parent, key=lambda x:getattr(x,'tvseason'))
    else:
        relations_season = {}
    directors=title.cast_set.filter(role='D')
    actors=title.cast_set.filter(role='A').order_by('id')
    akas=models.Aka.objects.filter(title=title.id)
    if request.user.is_anonymous():
        userdata=None
    else:
        userdata=title.get_userdata(request.user)
    #print userdata[0].tag
    data={'title':title,
          'relations_member':relations_member,
          'relations_parent':relations_parent,
          'relations_season':relations_season,
          'directors':directors,
          'userdata':userdata,
          'actors':actors,
          'akas':akas
          }
    return render_to_response('viewtitle.html',data,context_instance=RequestContext(request))

def view_file(request,file_id):
    fileo=get_object_or_404(models.File,pk=file_id)
    site_name = RequestSite(request).domain
    data={'file':fileo,"site_name":site_name, 'prefix':DOWNLOAD_PREFIX
          }
    return render_to_response('viewfile.html',data,context_instance=RequestContext(request))

@condition(etag_func=None)
def download_file(request,file_id):
    import mimetypes
    fileo=get_object_or_404(models.File,pk=file_id)
    if not fileo.valid:
        return Http404
    mime, encoding = mimetypes.guess_type( fileo.full_path())
    resp = HttpResponse(FileWrapper(file(fileo.full_path() )), 
                        mimetype = mime if mime else 'application/octet-stream' )
    resp['Content-Disposition'] = """attachment; filename="%s" """%(fileo.filename)
    resp['Content-Length'] = """%s"""%(fileo.size)
    return resp

def view_storage(request,stor_id):
    stor=get_object_or_404(models.Storage,pk=stor_id)
    data={'stor':stor
          }
    return render_to_response('viewstorage.html',data,context_instance=RequestContext(request))


def view_person(request,person_id):
    person=get_object_or_404(models.Person,pk=person_id)
    actor_for=person.cast_set.filter(role='A').exclude(title__type='episode')
    if not actor_for:
        actor_for=person.cast_set.filter(role='A')
    director_for=person.cast_set.filter(role='D')
    data={'person':person,
          'actor_for':actor_for,
          'director_for':director_for,
          }
    return render_to_response('viewperson.html',data,context_instance=RequestContext(request))

def search(request):
    if request.method!='POST':
        raise Http404
    f=search_form(request.POST)
    if f.is_valid():
        item=f.cleaned_data['item']
        #search fot titles titles
        titles = search_titles_akas (item)
        #search for person
        q=utils.get_query(item,['namesort'])
        people=[x for x in models.Person.objects.filter(q)]
        q=utils.get_query(item,['filename'])
        files=[x for x in models.File.objects.filter(q)]
        
        if not request.user.is_anonymous():
            q=utils.get_query(item,['tag'])
            tagtits = [x.title for x in models.UserTitle.objects.filter(user=request.user, 
                                                   tag__in=[x.id for x in models.Tag.objects.filter(q)]
                                                   )
                    ]
            titles=titles+tagtits
        data={'titles':set(titles),'people':set(people), 'files':set(files)}
        return render_to_response('showresult.html',data,context_instance=RequestContext(request))
    else:
        data={'titles':None,'people':None, 'files':None}
        return render_to_response('showresult.html',data,context_instance=RequestContext(request))

def search_title(request):
    #Search for a title: used in view_file to find the associated title
    # * searches in title and akas
    # * searches episodes with episode exx and season sxx
    if request.method!='POST':
        raise Http404
    
    f=search_form(request.POST)
    if f.is_valid():
        item=f.cleaned_data['item']# search string
        #search for titles titles
        titles = search_titles_akas (item)
        frm=remote_search_form(initial={'title': f.cleaned_data['item'] })
        #print request.POST['fileref']
        request.session['fileref'] = request.POST['fileref']
        data={'titles':titles, 'form': frm}
        return render_to_response('showresultft.html',data,context_instance=RequestContext(request))
    pass



def search_file_v(request):
    if request.method!='POST':
        raise Http404
    
    f=search_form(request.POST)
    if f.is_valid():
        item=f.cleaned_data['item']
        #search fot titles titles
        files= search_file(item)
        frm=remote_search_form(initial={'file': f.cleaned_data['item'] })
        request.session['titleref'] = request.POST['titleref']
        data={'files': files, 'form': frm}
        return render_to_response('showresulttf.html',data,context_instance=RequestContext(request))
    pass
 
def mass_match_file_title(request):
    """
    it should help in matching files to titles for tv series
    user must insert all needed episode titles before
    user have to write a search query for the titles and a search query for the files
    the results of the two searches is presented un the same page in two column
    titles are ordered by season episode name and have a ranking number, files are ordered ?
    and have a textbox on a side where user have to enter the right title number
    We should also provide a "preview" page in which titles and files with the same number are displayed on the same row
    """
    def number_titles (titles):
        return [[i, titles[i]] for i in xrange(len(titles))]
    def get_merger(post):
        #the matches are based on post name <fileid>_<titleid>_<number>
        titles = {}
        files = {}
        retitle = re.compile ("t_(\d+)")
        refile = re.compile ("f_(\d+)")
        for k in post.keys():
            ft = retitle.findall(k)
            if ft:
                if ft[0]:
                    titles[int(ft[0])] = post[k]
        for k in post.keys():
            ft = refile.findall(k)
            try:
                files[int(ft[0])] = int(post[k])
            except:
                pass
        return titles, files
    def do_merge (titles, files):
        for fi in files.keys():
#            print m
            f = models.File.objects.get(id=fi)
            try:
                f.title_id = titles[files[fi]]
            except:
                pass
            f.save()
    if request.method == 'POST':
        rtitles, rfiles = get_merger(request.POST)
#        print merger
        if rfiles:
            if request.POST.has_key('okgo'):
                if request.POST['okgo']=='ok':
                    do_merge(rtitles, rfiles)
        titlesearch = request.POST['titlesearch']
        filesearch = request.POST['filesearch']
        titles = search_titles_akas(titlesearch)
        if titles:
            titles.sort(lambda a, b: cmp(a.get_episode(), b.get_episode()))
            titles.sort(lambda a, b: cmp(a.get_season(), b.get_season()))
        files = search_file(filesearch)
        #files.sort(lambda x, y: x.filename<y.filename)
        ntitles = number_titles(titles)
        #try if there is some match with the old titles and old files from the POST
        #for the files and tiles that match and that where matched in the page py the user
        #reassign the same number (or at least re-match them)
        data = {'ntitles':ntitles, 'files':files, 'titlesearch':titlesearch, 'filesearch':filesearch}
    else:
        data = {'titlesfiles':{}, 'titlesearch':"", 'filesearch':""}
    return render_to_response('massmatch.html', data, context_instance=RequestContext(request))

@login_required
def push_user_title(request):
    if request.method!='POST':
        raise Http404
    ut = models.UserTitle.objects.filter(title =  models.Title.objects.get(id=int(request.POST['title'])),
                                         user = request.user)
    if not ut:
        ut = models.UserTitle(title= models.Title.objects.get(id=int(request.POST['title'])),
                              user = request.user
                               )
        ut.save()
    else:
        ut=ut[0]
    if 'rating' in request.POST.keys():
        ut.rating = float(request.POST['rating'])
    if 'note' in request.POST.keys():
        ut.note = request.POST['note']
    if 'tag' in request.POST.keys():
        for t in request.POST['tag'].split(): #aggiungo i tag nuovi
            tt = models.Tag.objects.filter(tag=t)
            if not tt:
                tt = models.Tag(tag=t)
                tt.save()
            else:
                tt = tt[0]
            if not (tt in ut.tag.all()):
                ut.tag.add(tt)
        for t in ut.tag.all():#tolgo le tag vecchie
            if t.tag not in  request.POST['tag']:
                ut.tag.remove(t)
        
    ut.save()
    return HttpResponseRedirect(reverse(view_title,args=[int(request.POST['title'])]))

@login_required
def link_file_title (request):
    if request.method!='POST':
        raise Http404
    
    __filetitle(fileid = int(request.session['fileref']), 
                titleid = int(request.POST['title']))
    ft = int(request.session['fileref'])
    del(request.session['fileref'])
    return HttpResponseRedirect(reverse(view_file, args=[ft]))

@login_required
def link_title_file (request):
    if request.method!='POST':
        raise Http404
    if  'files'  in request.POST.keys():
        for i in request.POST.getlist('files'):
            __filetitle(fileid = int(i), 
                    titleid = int(request.session['titleref']))
    tf = int(request.session['titleref'])
    del(request.session['titleref'])
    return HttpResponseRedirect(reverse(view_title,args=[tf]))


def __filetitle(fileid, titleid):
    #print fileid, titleid
    f = models.File.objects.get(id=fileid)
    t = models.Title.objects.get(id=titleid)
    f.title = t
    f.save()
    
def poll_task(request,task_id):
    task=get_object_or_404(models.RunningTask,pk=task_id)
    return render_to_response('polltask.html',{'task':task},context_instance=RequestContext(request))

def show_tasks(request):
    tasks=models.RunningTask.objects.all().order_by('-start_time')[:20]
    return render_to_response('showtasks.html',{'tasks':tasks},context_instance=RequestContext(request))

@login_required
def edit(request,id,model):
    import mymc.forms as forms
    obj=get_object_or_404(getattr(models,model),pk=id)
    if model.lower()+"_form" not in dir(forms):
        return HttpResponseNotFound("No edit form found")
    if request.method=='POST':
        f=getattr(forms,model.lower()+"_form")(request.POST,instance=obj)
        if f.is_valid():
            f.save()
            return HttpResponseRedirect(reverse(getattr(sys.modules[__name__],"show_"+model.lower())))
    else:     
        f=getattr(forms,model.lower()+"_form")(instance=obj)
    data={'form':f, 'model': model}
    return render_to_response('form.html',data,context_instance=RequestContext(request))

@login_required
def insert(request,model):
    import mymc.forms as forms
    #print request
    if model.lower()+"_form" not in dir(forms) or model.startswith("__"):
        return HttpResponseNotFound("No edit form found")
    
    if request.method == 'GET':
        try:
            dd = dict([(k,  int(request.GET[k]) ) for k in request.GET.keys()])
        except:
            dd = dict([(k,  request.GET[k]) for k in request.GET.keys()])
        try:
            mod = getattr(models, model) (**dd)
        except:
            mod = None       
    else: 
        mod = None
    
    if request.method=='POST':
        f=getattr(forms,model.lower()+"_form")(request.POST)
        if f.is_valid():
            f.save()
            return HttpResponseRedirect(reverse(getattr(sys.modules[__name__],"show_"+model.lower())))
    else:
        f=getattr(forms,model.lower()+"_form")(instance=mod)
    data={'form': f, 'model': model}
    return render_to_response('form.html',data,context_instance=RequestContext(request))

def show_relation(request):
   return HttpResponseRedirect(reverse(show_title)) 


def show_storage(request):
    storage_list=models.Storage.objects.all()
    data={'storage_list':storage_list}
    return render_to_response('showstorage.html',data,context_instance=RequestContext(request))

def show_file(request):
    file_list=models.File.objects.filter(valid=True).order_by('-title')
    files = __paginator(request, file_list)
   
    data={'file_list':files}
    return render_to_response('showfile.html',data,context_instance=RequestContext(request))


def index(request):
    last_titles=models.Title.objects.order_by('-lastmodified')[:9]
    return render_to_response('index.html',{'last_titles':last_titles},context_instance=RequestContext(request))

def search_file(searchstr):
    if not searchstr:
        return []
    q=utils.get_query(searchstr,['filename','path'])
    return [x for x in models.File.objects.filter(q).order_by("filename")]

def search_titles_akas (searchstr):
    def __get_season_episode(search):
        episodere = re.compile("[eE](\d+)")
        seasonre = re.compile("[sS](\d+)")
        episode = episodere.findall(search)
        search = episodere.sub("",search)
        season = seasonre.findall(search)
        search = seasonre.sub("",search)
        return (search.strip(), 
                episode[0] if episode else None,
                season[0] if season else None)
    
    def __search_genre(search):
        tg = models.TitleGenre.objects.filter(genre__name= search.strip())
        titles = [x.title for x in tg]
        return titles

    def __search_regex(search):
        #print search
        #reg =  "%r"%(search)
        reg = search
        titles=[x for x in models.Title.objects.filter(title__regex=reg)]
        return titles

    def __search_parent(item):
        from django.db.models import Q
        q = utils.get_query(item,['title'])
        titles=[x for x in models.Title.objects.filter(q)]
        q=utils.get_query(item,['akatitle'])
        titles=set([x.title for x in models.Aka.objects.filter(q)]+titles)
        q =Q(id__in = [x.title_id for x in models.Relation.objects.filter(parent__in=titles)])
        titles=[x for x in models.Title.objects.filter(q)]
        return list(titles)
          
    def __search_std(item):
        from django.db.models import Q
        item, episode, season = __get_season_episode(item)
        q = utils.get_query(item,['title','titlesort'])
        titles=[x for x in models.Title.objects.filter(q)]
        q=utils.get_query(item,['akatitle'])
        titles=set([x.title for x in models.Aka.objects.filter(q)]+titles)
        if episode and season:
            q =(Q(id__in = [x.title_id for x in models.Relation.objects.filter(tvseason = season, 
                                                                                    tvepisode=episode,
                                                                                    parent__in=titles)])
                | Q(id__in = [x.title_id for x in models.Relation.objects.filter(tvseason = season, 
                                                                                    tvepisode=episode,
                                                                                    title__in=titles)])
                 )
            titles=[x for x in models.Title.objects.filter(q)]
        elif season: #no episode but season
            q =(Q(id__in = [x.title_id for x in models.Relation.objects.filter(     tvseason=season,
                                                                                    parent__in=titles)])
                | Q(id__in = [x.title_id for x in models.Relation.objects.filter(   tvseason=season,
                                                                                    title__in=titles)])
                 )
            titles=[x for x in models.Title.objects.filter(q)]
        elif episode:#no season in search
            q =(Q(id__in = [x.title_id for x in models.Relation.objects.filter(     tvepisode=episode,
                                                                                    parent__in=titles)])
                | Q(id__in = [x.title_id for x in models.Relation.objects.filter(   tvepisode=episode,
                                                                                    title__in=titles)])
                 )
            titles=[x for x in models.Title.objects.filter(q)]
        return list(titles)
    
    if not searchstr:
        return []
    keywords = {'parent': __search_parent,
               'regex': __search_regex,
               'genre': __search_genre}
    for key, value in keywords.items():
        search = re.findall(r"%s:(.*)"%(key),searchstr)
        if search:
            return value(search[0])#runs the correct search function
    return __search_std(searchstr)

def playlist (request, file_id):
    fileo=get_object_or_404(models.File,pk=file_id)
    if not fileo.valid:
        return Http404
    site_name = RequestSite(request).domain
    resp = render_to_response('playlist_d.xspf',{"site_name":site_name, 'file':fileo, 'prefix':DOWNLOAD_PREFIX},context_instance=RequestContext(request))
    resp['Content-Disposition'] = """attachment; filename="playlist.xspf" """
    resp['Content-Type'] = 'application/xspf+xml'
    return resp


