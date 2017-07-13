from django.conf.urls import patterns, url

from unoconsole import views, forms, registry

urlpatterns = patterns('',
    url(r'^$',
        views.ConsoleHome.as_view(
            template_name='unoconsole/home.html',
        ),
        name='unoconsole_home'
    ),
)

urlpatterns += registry.console.urls
