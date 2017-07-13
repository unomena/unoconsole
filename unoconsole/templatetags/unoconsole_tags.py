'''
Created on 27 Feb 2015

@author: michaelwhelehan
'''
from django.template import Library
from django.utils.text import capfirst
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils import six
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _

register = Library()


@register.inclusion_tag('unoconsole/inclusion_tags/app_navigation.html',
                        takes_context=True)
def app_navigation(context):
    from unoconsole import console
    request = context['request']
    app_dict = {}
    user = request.user
    for title, url_cat in console._custom_registry.items():
        app_active = False
        model_active = False
        category = url_cat[1]
        perms = url_cat[2]
        if user.has_perm(perms):
            model_dict = {
                'name': title,
                'console_url': url_cat[0],
                'active': model_active
            }
            if category in app_dict:
                app_dict[category]['models'].append(model_dict)
            else:
                app_dict[category] = {
                    'name': category,
                    'has_module_perms': True,
                    'models': [model_dict],
                    'active': app_active
                }

    for model, model_admin_cat in console._registry.items():
        model_admin = model_admin_cat[0]
        category = model_admin_cat[1]
        app_label = model._meta.app_label
        has_module_perms = user.has_module_perms(app_label)
        app_active = False
        model_active = False

        if has_module_perms:
            perms = model_admin.get_model_perms(request)

            # Check whether user has any perm for this module.
            # If so, add the module to the model_list.
            if True in perms.values():
                info = (app_label, model._meta.module_name)
                console_url = reverse('%s_%s_changelist' % info)
                if console_url in request.path:
                    model_active = True
                    app_active = True
                model_dict = {
                    'name': capfirst(model._meta.verbose_name_plural),
                    'perms': perms,
                    'active': model_active
                }
                if perms.get('change', False):
                    try:
                        model_dict['console_url'] = console_url
                    except NoReverseMatch:
                        pass
                if perms.get('add', False):
                    try:
                        model_dict['add_url'] = reverse('%s_%s_add' % info)
                    except NoReverseMatch:
                        pass
                if category is not None:
                    if category in app_dict:
                        app_dict[category]['models'].append(model_dict)
                        if not app_dict[category]['active']:
                            app_dict[category]['active'] = app_active
                    else:
                        app_dict[category] = {
                            'name': category,
                            'has_module_perms': has_module_perms,
                            'models': [model_dict],
                            'active': app_active
                        }
                elif app_label in app_dict:
                    app_dict[app_label]['models'].append(model_dict)
                else:
                    app_dict[app_label] = {
                        'name': app_label.title(),
                        'app_url': reverse('admin:app_list', kwargs={'app_label': app_label}),
                        'has_module_perms': has_module_perms,
                        'active': app_active,
                        'models': [model_dict],
                    }

    # Sort the apps alphabetically.
    app_list = list(six.itervalues(app_dict))
    app_list.sort(key=lambda x: x['name'])

    # Sort the models alphabetically within each app.
    for app in app_list:
        app['models'].sort(key=lambda x: x['name'])

    context = {
        'app_list': app_list,
    }
    return context


@register.inclusion_tag('unoconsole/inclusion_tags/object_history.html',
                        takes_context=True)
def object_history(context):
    from django.contrib.admin.models import LogEntry
    try:
        obj = context['original']
        model = context['model']

        # Then get the history for this object.
        app_label = context['app_label']
        action_list = LogEntry.objects.filter(
            object_id=obj.id,
            content_type__id__exact=ContentType.objects.get_for_model(model).id
        ).select_related().order_by('action_time')

        context = {
            'title': _('Change history: %s') % force_text(obj),
            'action_list': action_list,
            'object': obj,
            'app_label': app_label,
        }
        return context
    except:
        return {}
