from django import forms 
from . import models
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from profanity import profanity
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import PasswordChangeForm

class CreateLikedBook(forms.ModelForm):
    class Meta:
        model = models.Book
        fields = ['title','authors','image_link','isbn','buy_link','genres']


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    name = forms.CharField(max_length=40)


    class Meta:
        model = CustomUser
        fields = ("email", "name", "password1", "password2")

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if profanity.contains_profanity(name):
            raise ValidationError("The Name field contains innapropriate language")
        return name
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.name = self.cleaned_data["name"]
        if commit:
            user.save()
        return user
    
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'name', 'is_active', 'is_staff')

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254)

class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, label="New Password")

class ChangeNameForm(forms.Form):
    new_name = forms.CharField(
        label="New Name",
        widget=forms.TextInput()
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ChangeNameForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['new_name'].widget.attrs['placeholder'] = user.name

class DeleteAccountForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        widget=forms.HiddenInput(),  
        initial=True,
    )

class ChangePasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter new password'})
    )