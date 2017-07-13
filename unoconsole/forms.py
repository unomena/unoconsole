'''
Created on 27 Feb 2015

@author: michaelwhelehan
'''
from django import forms
from django.forms.fields import FileField
from django.contrib.auth.forms import AdminPasswordChangeForm

from unoconsole.widgets import AdminSplitDateTime


class UnoconsoleModelForm(forms.ModelForm):

    class Meta:
        exclude = ['state', 'retract_at']

    def __init__(self, *args, **kwargs):
        super(UnoconsoleModelForm, self).__init__(*args, **kwargs)

        for key, field in self.fields.items():
            if not isinstance(field.widget, AdminSplitDateTime):
                if 'class' in field.widget.attrs:
                    previous_class = field.widget.attrs['class']
                    class_to_update = 'form-control %s' % previous_class
                else:
                    class_to_update = 'form-control'
                field.widget.attrs.update({
                    'class': class_to_update
                })
#             if field.required and not isinstance(field, FileField):
#                 field.widget.attrs.update({
#                     'required': ''
#                 })

    def clean(self):
        cleaned_data = super(UnoconsoleModelForm, self).clean()
        for key, val in cleaned_data.items():
            if val == '<p><br></p>':
                cleaned_data[key] = ''
        return cleaned_data


class UnoconsolePasswordChangeForm(AdminPasswordChangeForm):

    def __init__(self, *args, **kwargs):
        super(UnoconsolePasswordChangeForm, self).__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control'
        })
