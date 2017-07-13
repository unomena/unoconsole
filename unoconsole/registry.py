'''
Created on 27 Feb 2015

@author: michaelwhelehan
'''
from functools import update_wrapper

from django.db.models.base import ModelBase
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils import six
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from unoconsole import ModelAdmin, actions

system_check_errors = []


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class Console(object):

    def __init__(self):
        self.name = 'console'
        self._registry = {}  # model_class class -> admin_class instance
        self._custom_registry = {}
        self._actions = {'delete_selected': actions.delete_selected}
        self._global_actions = self._actions.copy()

    def register(self, model_or_iterable, admin_class=None, category=None,
                 allow_add=True, allow_delete=True, **options):
        """
        Registers the given model(s) with the given admin class.
        The model(s) should be Model classes, not instances.
        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.
        If a model is already registered, this will raise AlreadyRegistered.
        If a model is abstract, this will raise ImproperlyConfigured.
        """
        if not admin_class:
            admin_class = ModelAdmin

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model._meta.abstract:
                raise ImproperlyConfigured('The model %s is abstract, so it '
                      'cannot be registered with admin.' % model.__name__)

            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)

            # Ignore the registration if the model has been
            # swapped out.
            if not model._meta.swapped:
                # If we got **options then dynamically construct a subclass of
                # admin_class with those **options.
                if options:
                    # For reasons I don't quite understand, without a __module__
                    # the created class appears to "live" in the wrong place,
                    # which causes issues later on.
                    options['__module__'] = __name__
                    admin_class = type("%sAdmin" % model.__name__, (admin_class,), options)

#                 if admin_class is not ModelAdmin and settings.DEBUG:
#                     system_check_errors.extend(admin_class.check(model))

                # Instantiate the admin class to save in the registry
                self._registry[model] = [
                    admin_class(model, self), category, allow_add, allow_delete
                ]

    def register_custom_view(self, url, title, category, permission):
        self._custom_registry[title] = [url, category, permission]

    def unregister_custom_view(self, title):
        if title not in self._custom_registry:
            raise NotRegistered('The custom view %s is not registered' % title)
        del self._custom_registry[title]

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).
        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]

    def is_registered(self, model):
        """
        Check if a model class is registered with this `AdminSite`.
        """
        return model in self._registry

    def add_action(self, action, name=None):
        """
        Register an action to be available globally.
        """
        name = name or action.__name__
        self._actions[name] = action
        self._global_actions[name] = action

    def disable_action(self, name):
        """
        Disable a globally-registered action. Raises KeyError for invalid names.
        """
        del self._actions[name]

    def get_action(self, name):
        """
        Explicitly get a registered global action whether it's enabled or
        not. Raises KeyError for invalid names.
        """
        return self._global_actions[name]

    @property
    def actions(self):
        """
        Get all the enabled actions as an iterable of (name, func).
        """
        return six.iteritems(self._actions)

    @never_cache
    def login(self, request, extra_context=None):
        """
        Displays the login form for the given HttpRequest.
        """
        from django.contrib.auth.views import login
        context = {
            'title': _('Log in'),
            'app_path': request.get_full_path(),
            REDIRECT_FIELD_NAME: request.get_full_path(),
        }
        context.update(extra_context or {})

        defaults = {
            'extra_context': context,
            'current_app': self.name,
            'template_name': 'authentication/login.html',
        }
        return login(request, **defaults)

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        return request.user.is_active and request.user.is_staff

    def check_dependencies(self):
        """
        Check that all things needed to run the admin have been correctly installed.
        The default implementation checks that LogEntry, ContentType and the
        auth context processor are installed.
        """
        from django.contrib.admin.models import LogEntry
        from django.contrib.contenttypes.models import ContentType

        if not LogEntry._meta.installed:
            raise ImproperlyConfigured("Put 'django.contrib.admin' in your "
                "INSTALLED_APPS setting in order to use the admin application.")
        if not ContentType._meta.installed:
            raise ImproperlyConfigured("Put 'django.contrib.contenttypes' in "
                "your INSTALLED_APPS setting in order to use the admin application.")
        if not ('django.contrib.auth.context_processors.auth' in settings.TEMPLATE_CONTEXT_PROCESSORS or
            'django.core.context_processors.auth' in settings.TEMPLATE_CONTEXT_PROCESSORS):
            raise ImproperlyConfigured("Put 'django.contrib.auth.context_processors.auth' "
                "in your TEMPLATE_CONTEXT_PROCESSORS setting in order to use the admin application.")

    def admin_view(self, view, cacheable=False):
        """
        Decorator to create an admin view attached to this ``AdminSite``. This
        wraps the view and provides permission checking by calling
        ``self.has_permission``.
        You'll want to use this from within ``AdminSite.get_urls()``:
            class MyAdminSite(AdminSite):
                def get_urls(self):
                    from django.conf.urls import patterns, url
                    urls = super(MyAdminSite, self).get_urls()
                    urls += patterns('',
                        url(r'^my_view/$', self.admin_view(some_view))
                    )
                    return urls
        By default, admin_views are marked non-cacheable using the
        ``never_cache`` decorator. If the view can be safely cached, set
        cacheable=True.
        """
        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                if request.path == reverse('admin:logout',
                                           current_app=self.name):
                    index_path = reverse('admin:index', current_app=self.name)
                    return HttpResponseRedirect(index_path)
                return self.login(request)
            return view(request, *args, **kwargs)
        if not cacheable:
            inner = never_cache(inner)
        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(view, 'csrf_exempt', False):
            inner = csrf_protect(inner)
        return update_wrapper(inner, view)

    def get_urls(self):
        from django.conf.urls import patterns, url, include

        if settings.DEBUG:
            self.check_dependencies()

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        # Admin-site-wide views.
        urlpatterns = patterns('')

        # Add in each model's views.
        for model, model_admin_cat in six.iteritems(self._registry):
            model_admin = model_admin_cat[0]
            urlpatterns += patterns('',
                url(r'^%s/%s/' % (model._meta.app_label, model._meta.module_name),
                    include(model_admin.urls))
            )
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls()


console = Console()
