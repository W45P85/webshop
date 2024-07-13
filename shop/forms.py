from django.contrib.auth.models import User, AbstractUser
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import *

class CustomerCreationForm(UserCreationForm):
    email = forms.EmailField(label='Email', required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }


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
