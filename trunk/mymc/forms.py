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

from django import forms
from django.forms import ModelForm
import models

class remote_search_form(forms.Form):
    title=forms.CharField(max_length=256)
    source=forms.ChoiceField(choices=(('I','ImDB'),),label='Sorgente')

class remote_select_form(forms.Form):
    movie=forms.ChoiceField(widget=forms.RadioSelect)
    #movie=forms.ChoiceField()
    def __init__(self,*args,**kwargs):
        movie_choices=None
        if 'movie_choices' in kwargs:
            movie_choices=kwargs['movie_choices']
            del(kwargs['movie_choices'])
        super(remote_select_form,self).__init__(*args,**kwargs)
        if movie_choices:
            self.fields['movie'].choices=movie_choices

class remote_select_episodes(forms.Form):
    episodes=forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)
    def __init__(self,*args,**kwargs):
        episode_choices=None
        if 'episode_choices' in kwargs:
            episode_choices=kwargs['episode_choices']
            del kwargs['episode_choices']
        super (remote_select_episodes,self).__init__(*args,**kwargs)
        if episode_choices:
            self.fields['episodes'].choices=episode_choices

class search_form(forms.Form):
    item=forms.CharField(max_length=256,label='cerca')
    
class storage_form(ModelForm):
    class Meta:
        model=models.Storage

class file_form(ModelForm):
    class Meta:
        model=models.File

class title_form(ModelForm):
    class Meta:
        model=models.Title

class relation_form(ModelForm):
    class Meta:
        model=models.Relation

class person_form(ModelForm):
    class Meta:
        model=models.Person
    