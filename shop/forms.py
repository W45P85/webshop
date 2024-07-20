from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import *

class CustomerCreationForm(UserCreationForm):
    email = forms.EmailField(label='Email', required=True)
    first_name = forms.CharField(label='Vorname', max_length=30, required=True)
    last_name = forms.CharField(label='Nachname', max_length=30, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'off'})
        self.fields['username'].label = 'Benutzername'
        self.fields['username'].help_text = 'Bitte geben Sie Ihren Vor- und Nachnamen ein.'
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].label = 'Passwort. Mindestens 8 Zeichen, davon 1 Sonderzeichen.'
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].label = 'Passwort wiederholen'
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].label = 'Email'
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].label = 'Vorname'
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].label = 'Nachname'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label='Benutzername')
    email = forms.EmailField(max_length=254, required=True, label='E-Mail')
    first_name = forms.CharField(max_length=100, required=True, label='Vorname')
    last_name = forms.CharField(max_length=100, required=True, label='Nachname')
    profile_picture = forms.ImageField(required=False, label='Profilbild', widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}))
    address = forms.CharField(max_length=200, required=True, label='Adresse')
    city = forms.CharField(max_length=200, required=True, label='Stadt')
    state = forms.CharField(max_length=200, required=True, label='Bundesland')
    zipcode = forms.CharField(max_length=200, required=True, label='Postleitzahl')
    country = forms.CharField(max_length=200, required=True, label='Land')
    is_default = forms.BooleanField(required=False, label='Als Standardadresse setzen')

    class Meta:
        model = Customer
        fields = ['username', 'email', 'first_name', 'last_name', 'profile_picture', 'address', 'city', 'state', 'zipcode', 'country', 'is_default']
    
    def save(self, user, commit=True):
        # Update user fields
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        
        # Update customer fields
        customer = super().save(commit=False)
        if 'profile_picture' in self.cleaned_data and self.cleaned_data['profile_picture']:
            customer.profile_picture = self.cleaned_data['profile_picture']
        customer.user = user
        if commit:
            customer.save()

        # Update address fields
        address_data = {
            'first_name': self.cleaned_data['first_name'],
            'last_name': self.cleaned_data['last_name'],
            'address': self.cleaned_data['address'],
            'city': self.cleaned_data['city'],
            'state': self.cleaned_data['state'],
            'zipcode': self.cleaned_data['zipcode'],
            'country': self.cleaned_data['country'],
            'is_default': self.cleaned_data['is_default'],
        }
        Adress.objects.update_or_create(
            customer=customer,
            defaults=address_data
        )
        return customer


class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=255,
        required=False,
        label='Suche',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Artikelname, Beschreibung oder Kategorie eingeben...'
        })
    )


class AddArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['name', 'description', 'price', 'img', 'category']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].label = 'Artikelname'

        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].label = 'Beschreibung'

        self.fields['price'].widget.attrs.update({'class': 'form-control'})
        self.fields['price'].label = 'Preis'

        self.fields['img'].widget.attrs.update({'class': 'form-control'})
        self.fields['img'].label = 'Bild'

        self.fields['category'].widget.attrs.update({'class': 'form-control'})
        self.fields['category'].label = 'Kategorie'


class EditArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['name', 'description', 'price', 'img', 'category']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].label = 'Artikelname'

        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].label = 'Beschreibung'

        self.fields['price'].widget.attrs.update({'class': 'form-control'})
        self.fields['price'].label = 'Preis'

        self.fields['img'].widget.attrs.update({'class': 'form-control'})
        self.fields['img'].label = 'Bild'

        self.fields['category'].widget.attrs.update({'class': 'form-control'})
        self.fields['category'].label = 'Kategorie'


class AddCategoryForm(forms.ModelForm):
    categories = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = Category
        fields = ['categories']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categories'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['categories'].label = 'Kategorien'
