'''
Created on 16 Jan 2013

@author: euan
'''
from optparse import make_option

from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    """
    Command to clear message queue
    """
    option_list = BaseCommand.option_list + (
        make_option('--app_label',
            type='string',
            action='store',
            dest='app_label',
            default=None,
            help='App label for model in app'
        ),

        make_option('--model',
            type='string',
            action='store',
            dest='model',
            default=None,
            help='Name of model'
        ),
    )

    def handle(self, *args, **options):
        if 'app_label' not in options or not options['app_label']:
            print 'app_label not provided'
            return
        if 'model' not in options or not options['model']:
            print 'model not provided'
            return
        content_type = ContentType.objects.get(
            app_label=options['app_label'],
            model=options['model']
        )
        model_class = content_type.model_class()
        for obj in model_class.objects.all():
            model_class.objects.add_version(obj)
