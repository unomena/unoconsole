'''
Created on 27 Feb 2015

@author: michaelwhelehan
'''
from django.views import generic as generic_views
from django.core.urlresolvers import reverse


from tunobase.console import mixins as console_mixins


class ConsoleHome(console_mixins.ConsoleUserRequiredMixin,
                  generic_views.TemplateView):
    pass
