'''
Created on 02 Mar 2015

@author: michaelwhelehan
'''
from django.core.urlresolvers import reverse
from django import template
from django.contrib.admin.util import quote

register = template.Library()

@register.filter
def unoconsole_urlname(value, arg):
    return '%s_%s_%s' % (value.app_label, value.module_name, arg)


@register.filter
def unoconsole_urlquote(value):
    return quote(value)
