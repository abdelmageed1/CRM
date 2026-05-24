from django import forms
from .models import CallsResponse

STATUS_CHOICES = [
    ('', '--- اختر الحالة ---'),
    ('Scheduled a meeting', 'Scheduled a meeting'),
    ('Not interested', 'Not interested'),
    ('Interested', 'Interested'),
]

TYPE_CHOICES = [
    ('', '--- اختر النوع ---'),
    ('External', 'External'),
    ('Internal', 'Internal'),
]

LOCATION_CHOICES = [
    ('', '--- اختر الموقع ---'),
    ('Sohag MP', 'Sohag MP'),
    ('Sohag', 'Sohag'),
    ('Cairo', 'Cairo'),
]
PROJECT_CHOICES = [
    ('', '--- اختر المشروع ---'),
    ('GA', 'GA'),
    ('GC', 'GC'),
    ('RJ', 'RJ'),
    ('other', 'other'),
]


class ClientForm(forms.Form):
    lead_owner = forms.CharField(
        label='Lead Owner',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Lead owner name',
            'readonly': 'readonly'
        })
    )
    phone_number = forms.CharField(
        label='Phone Number',
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'})
    )
    client_code = forms.CharField(
        label='Client Code',
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client code'})
    )
    client_name = forms.CharField(
        label='Client Name',
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client name'})
    )
    project_name = forms.ChoiceField(
         label='Project Name',
        required=True,
        choices=PROJECT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    project_unit = forms.CharField(
        label='Project Unit',
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project unit'}),
    )
    date = forms.DateField(
        label='Date',
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    email_address = forms.EmailField(
        label='Email Address',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'})
    )
    status = forms.ChoiceField(
        label='Status',
        required=True,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    location = forms.ChoiceField(
        label='Location',
        required=True,
        choices=LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    type = forms.ChoiceField(
        label='Type',
        required=False,
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        label='Notes',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'})
    )
    manager_comments = forms.CharField(
        label='Manager Comments',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Manager comments'})
    )
    broker_name = forms.CharField(
        label='Broker Name',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Broker name (optional)'})
    )
