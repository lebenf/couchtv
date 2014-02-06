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

from django.conf.urls.defaults import *
import settings
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^mmc/', include('mmc.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^$', 'mymc.views.index'),
    (r'^remotesearch/$', 'mymc.views.remote_search'),
    (r'^search/$', 'mymc.views.search'),
    (r'^searchtitle/$', 'mymc.views.search_title'),
    (r'^searchfile/$', 'mymc.views.search_file_v'),
    (r'^filetitle/$', 'mymc.views.link_file_title'),
    (r'^titlefile/$', 'mymc.views.link_title_file'),
    (r'^pushusertitle/$', 'mymc.views.push_user_title'),
    (r'^remoteselect/$', 'mymc.views.remote_select'),
    (r'^remoteselectepisode/$', 'mymc.views.remote_select_episode'),
    (r'^remoteaddepisode/(?P<title_id>\d+)/$', 'mymc.views.remote_add_episode'),
    (r'^polltask/(?P<task_id>\d+)/$','mymc.views.poll_task'),
    (r'^showtasks/$', 'mymc.views.show_tasks'),
    (r'^showtitle/$','mymc.views.show_title'),
    (r'^showrelation/$','mymc.views.show_relation'),
    (r'^viewtitle/(?P<title_id>\d+)/$','mymc.views.view_title_html'),
    (r'^api/title/(?P<title_id>\d+)/$','mymc.views.view_title_api'),
    (r'^updatetitle/(?P<title_id>\d+)/$','mymc.views.update_title'),
    (r'^viewfile/(?P<file_id>\d+)/$','mymc.views.view_file'),
    (r'^download/(?P<file_id>\d+)/$','mymc.views.download_file'),
    (r'^play/(?P<file_id>\d+)/$','mymc.views.playlist'),
    (r'^updatestorage/(?P<storage_id>\d+)/$','mymc.views.update_storage'),
    (r'^viewstorage/(?P<stor_id>\d+)/$','mymc.views.view_storage'),
    (r'^viewperson/(?P<person_id>\d+)/$','mymc.views.view_person'),
    (r'^showstorage/$','mymc.views.show_storage'),
    (r'^showfile/$','mymc.views.show_file'),
    (r'^logout/$', 'mymc.views.logout_view'),
    (r'^admin/', include(admin.site.urls)),
    (r'^media-site/(?P<path>.*)$', 'django.views.static.serve',{'document_root': settings.MEDIA_ROOT, 'show_indexes': True} ),
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^edit/(?P<model>.*?)/(?P<id>\d+)/$','mymc.views.edit'),
    (r'^insert/(?P<model>.*?)/$','mymc.views.insert'),
    (r'^event/$','speedtest.views.get_event'),
    (r'^rnddownload/$','speedtest.views.rnd_download'),
    (r'^smart_download/(?P<title_id>.*?)/$','speedtest.views.download_smart'),
    (r'^streamer/(?P<file_id>.*?)/$','streamer.views.stream_file'),
    (r'^viewprocess/(?P<proc_id>.*?)/$','streamer.views.view_process'),
    (r'^killprocess/(?P<proc_id>.*?)/$','streamer.views.kill_process'),
    (r'^controlprocess/(?P<proc_id>.*?)/$','streamer.views.control_process'),
    (r'^playlist/(?P<proc_id>.*?)/$','streamer.views.playlist'),
    (r'^restartprocess/(?P<proc_id>.*?)/$','streamer.views.restart_process'),
    (r'^showprocess/$','streamer.views.show_process'),
    (r'^massmatch/$','mymc.views.mass_match_file_title'),
    (r'^buildpool/(?P<pool_id>.*?)/$','mytv.views.build_pool'),
    (r'^buildpool/$','mytv.views.build_pool'),
    (r'^updatepool/(?P<pool_id>\d+)/$','mytv.views.update_pool'),
    (r'^viewpool/(?P<pool_id>\d+)/$','mytv.views.view_pool'),
    (r'^podcastpool/(?P<pool_id>\d+)/$','mytv.views.podcast_pool'),
    (r'^playpoolelement/(?P<pool_elem>\d+)/$','mytv.views.play_pool_element'),
    (r'^showpool/$','mytv.views.show_pool'),    
    (r'^seriestopool/(?P<title_id>\d+)/$','mytv.views.series_to_pool'),
    (r'^buildchannel/(?P<channel_id>.*?)/$','mytv.views.build_channel'),
    (r'^buildchannel/$','mytv.views.build_channel'),
    (r'^viewchannel/(?P<channel_id>\d+)/$','mytv.views.view_channel'),
    (r'^showchannel/$','mytv.views.show_channel'),    
    (r'^playpool/(?P<pool_id>\d+)/$','mytv.views.play_pool'),
    (r'^playnextpool/(?P<pool_id>\d+)/$','mytv.views.play_pool_next'),
    (r'^replaypool/(?P<pool_id>\d+)/$','mytv.views.play_pool_replay'),
    (r'^setlastelement/(?P<pool_id>\d+)/(?P<element_id>\d+)/$','mytv.views.set_last_element'),
    (r'^playchannel/(?P<channel_id>\d+)/$','mytv.views.play_channel'),
    (r'^playnextchannel/(?P<channel_id>\d+)/$','mytv.views.play_channel_next'),
    (r'^replaychannel/(?P<channel_id>\d+)/$','mytv.views.play_channel_replay'),
     )
