from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.files.images import get_image_dimensions
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
    profile_picture = forms.ImageField(required=False, label='Profilbild', widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}))
    address = forms.CharField(max_length=200, required=False, label='Adresse')
    city = forms.CharField(max_length=200, required=False, label='Stadt')
    state = forms.CharField(max_length=200, required=False, label='Bundesland')
    zipcode = forms.CharField(max_length=200, required=False, label='Postleitzahl')
    country = forms.CharField(max_length=200, required=False, label='Land')
    is_default = forms.BooleanField(required=False, label='Als Standardadresse setzen')
    first_name = forms.CharField(max_length=30, required=False, label='Vorname')
    last_name = forms.CharField(max_length=30, required=False, label='Nachname')
    email = forms.EmailField(required=False)
    username = forms.CharField(max_length=150, required=False)

    class Meta:
        model = Customer
        fields = ['profile_picture', 'username', 'email', 'first_name', 'last_name', 'address', 'city', 'state', 'zipcode', 'country', 'is_default']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_picture'].widget.attrs.update({'class': 'form-control-file'})
        self.fields['profile_picture'].label = 'Profilbild'
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['username'].label = 'Benutzername'
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].label = 'Email'
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].label = 'Vorname'
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].label = 'Nachname'
        self.fields['address'].widget.attrs.update({'class': 'form-control'})
        self.fields['address'].label = 'Adresse'
        self.fields['city'].widget.attrs.update({'class': 'form-control'})
        self.fields['city'].label = 'Stadt'
        self.fields['state'].widget.attrs.update({'class': 'form-control'})
        self.fields['state'].label = 'Bundesland'
        self.fields['zipcode'].widget.attrs.update({'class': 'form-control'})
        self.fields['zipcode'].label = 'Postleitzahl'
        self.fields['country'].widget.attrs.update({'class': 'form-control'})
        self.fields['country'].label = 'Land'
        self.fields['is_default'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_default'].label = 'Als Standardadresse setzen'
    
    def save(self, user, commit=True):
        # Update customer fields
        customer = super().save(commit=False)
        customer.user = user
        if commit:
            customer.save()

        # Update address fields
        address_data = {
            'address': self.cleaned_data['address'],
            'city': self.cleaned_data['city'],
            'state': self.cleaned_data['state'],
            'zipcode': self.cleaned_data['zipcode'],
            'country': self.cleaned_data['country'],
            'is_default': self.cleaned_data['is_default'],
        }

        # Hole alle Adressen des Kunden und finde die zuletzt erstellte Adresse
        existing_addresses = Address.objects.filter(customer=customer).order_by('-date')
        latest_address = existing_addresses.first()

        if address_data['is_default']:
            # Wenn eine neue Adresse als Standardadresse markiert wird,
            # setze alle bisherigen Standardadressen auf nicht standard
            Address.objects.filter(customer=customer, is_default=True).update(is_default=False)

        if latest_address:
            if latest_address.is_default:
                # Wenn die letzte Adresse bereits die Standardadresse war, aktualisiere sie
                for field, value in address_data.items():
                    setattr(latest_address, field, value)
                latest_address.save()
            else:
                # Wenn die letzte Adresse nicht die Standardadresse war, füge die neue Adresse hinzu
                Address.objects.create(
                    customer=customer,
                    **address_data
                )
        else:
            # Wenn keine Adresse vorhanden ist, füge die neue Adresse hinzu
            Address.objects.create(
                customer=customer,
                **address_data
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
        fields = ['article_number', 'name', 'description', 'price', 'img', 'category', 'stock', 'length', 'width', 'height', 'weight']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['article_number'].widget.attrs.update({'class': 'form-control'})
        self.fields['article_number'].label = 'Artikelnummer (optional)'
        
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].label = 'Artikelname'

        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].label = 'Beschreibung'

        self.fields['price'].widget.attrs.update({'class': 'form-control'})
        self.fields['price'].label = 'Preis in €'

        self.fields['img'].widget.attrs.update({'class': 'form-control'})
        self.fields['img'].label = 'Bild'

        self.fields['category'].widget.attrs.update({'class': 'form-control'})
        self.fields['category'].label = 'Kategorie'

        self.fields['stock'].widget.attrs.update({'class': 'form-control'})
        self.fields['stock'].label = 'Lagerbestand in Stück'

        self.fields['length'].widget.attrs.update({'class': 'form-control'})
        self.fields['length'].label = 'Länge in cm'

        self.fields['width'].widget.attrs.update({'class': 'form-control'})
        self.fields['width'].label = 'Breite in cm'

        self.fields['height'].widget.attrs.update({'class': 'form-control'})
        self.fields['height'].label = 'Höhe in cm'
        
        self.fields['weight'].widget.attrs.update({'class': 'form-control'})
        self.fields['weight'].label = 'Gewicht in kg'


class EditArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['name', 'description', 'price', 'img', 'category', 'stock', 'length', 'width', 'height', 'weight']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].label = 'Artikelname'

        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].label = 'Beschreibung'

        self.fields['price'].widget.attrs.update({'class': 'form-control'})
        self.fields['price'].label = 'Preis in €'

        self.fields['img'].widget.attrs.update({'class': 'form-control'})
        self.fields['img'].label = 'Bild'

        self.fields['category'].widget.attrs.update({'class': 'form-control'})
        self.fields['category'].label = 'Kategorie'
        
        self.fields['stock'].widget.attrs.update({'class': 'form-control'})
        self.fields['stock'].label = 'Lagerbestand in Stück'

        self.fields['length'].widget.attrs.update({'class': 'form-control'})
        self.fields['length'].label = 'Länge in cm'

        self.fields['width'].widget.attrs.update({'class': 'form-control'})
        self.fields['width'].label = 'Breite in cm'

        self.fields['height'].widget.attrs.update({'class': 'form-control'})
        self.fields['height'].label = 'Höhe in cm'
        
        self.fields['weight'].widget.attrs.update({'class': 'form-control'})
        self.fields['weight'].label = 'Gewicht in kg'


class AddCategoryForm(forms.ModelForm):
    parent = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label='Keine übergeordnete Kategorie')

    class Meta:
        model = Category
        fields = ['name', 'parent']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['parent'].widget.attrs.update({'class': 'form-control form-control-sm'})


class TrackingNumberForm(forms.Form):
    order_id = forms.CharField(label='Berstellnummer', required=False)
    tracking_number = forms.CharField(label='Tracking Number', max_length=100, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order_id'].widget.attrs.update({'class': 'form-control'})
        self.fields['order_id'].label = 'Order ID'
        self.fields['tracking_number'].widget.attrs.update({'class': 'form-control'})
        self.fields['tracking_number'].label = 'Tracking Number'


class MarkDeliveredForm(forms.Form):
    order_id = forms.CharField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order_id'].widget.attrs.update({'class': 'form-control'})


class OrderSearchForm(forms.Form):
    search_term = forms.CharField(required=False, label='Suche Bestellungen', max_length=100)
    
    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['search_term'].widget.attrs.update({'class': 'form-control'})


class ComplaintForm(forms.ModelForm):
    reason = forms.CharField(label='Reklamationsgrund', widget=forms.Textarea(attrs={'rows': 3}), required=True)
    image = forms.ImageField(label='Bild der Reklamation', required=False)
    
    class Meta:
        model = Complaint
        fields = ['reason', 'image']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4}),
            'image': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.selected_order = kwargs.pop('selected_order', None)

        super().__init__(*args, **kwargs)
        self.fields['image'].widget.attrs.update({'class': 'form-control'})
        self.fields['image'].label = 'Bild der Reklamation'
        self.fields['reason'].widget.attrs.update({'class': 'form-control'})
        self.fields['reason'].label = 'Reklamationsgrund'

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Optional: Validierung für Bildgröße
            width, height = get_image_dimensions(image)
            if width > 2000 or height > 2000:
                raise forms.ValidationError('Das Bild ist zu groß. Maximal 2000x2000 Pixel.')
        return image


class ShippingForm(forms.Form):
    recipient_name = forms.CharField(label="Empfängername", max_length=100)
    street_address = forms.CharField(label="Straße und Hausnummer", max_length=200)
    city = forms.CharField(label="Stadt", max_length=100)
    postal_code = forms.CharField(label="Postleitzahl", max_length=20)
    country = forms.CharField(label="Land", max_length=100)
    
    shipping_method = forms.ChoiceField(
        label="Versandart",
        choices=[
            ('standard', 'Standardversand'),
            ('express', 'Expressversand'),
            ('overnight', 'Overnight')
        ]
    )
    
    insurance = forms.BooleanField(label="Versicherung hinzufügen", required=False)
    insurance_amount = forms.DecimalField(label="Versicherungsbetrag", max_digits=10, decimal_places=2, required=False)
    
    weight = forms.DecimalField(label="Gewicht (kg)", max_digits=5, decimal_places=2)
    length = forms.DecimalField(label="Länge (cm)", max_digits=5, decimal_places=1)
    width = forms.DecimalField(label="Breite (cm)", max_digits=5, decimal_places=1)
    height = forms.DecimalField(label="Höhe (cm)", max_digits=5, decimal_places=1)
    
    customs_declaration = forms.CharField(label="Zollerklärung", max_length=500, required=False)
    contents_description = forms.CharField(label="Beschreibung des Inhalts", max_length=500, required=False)
    goods_value = forms.DecimalField(label="Warenwert (€)", max_digits=10, decimal_places=2, required=False)
    
    pickup_date = forms.DateField(label="Abholdatum", required=False)
    pickup_time = forms.TimeField(label="Abholzeit", required=False)
    
    additional_notes = forms.CharField(
        label="Zusätzliche Hinweise", 
        widget=forms.Textarea, 
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bootstrap-Styling für alle Felder hinzufügen
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.Textarea)):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, (forms.DateInput, forms.TimeInput)):
                field.widget.attrs['class'] = 'form-control'


class MessageForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(queryset=User.objects.all(), required=True, empty_label="Empfänger auswählen")
    subject = forms.CharField(label="Betreff")
    body = forms.CharField(label="Text", widget=forms.Textarea(attrs={'rows': 3}))
    
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'body']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.Textarea)):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, (forms.DateInput, forms.TimeInput)):
                field.widget.attrs['class'] = 'form-control'


class MessageReplyForm(forms.ModelForm):
    body = forms.CharField(label="Text", widget=forms.Textarea(attrs={'rows': 3}))

    class Meta:
        model = Message
        fields = ['body']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].widget.attrs.update({'class': 'form-control'})

