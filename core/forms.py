from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Animal, AdoptionRequest

class AnimalForm(forms.ModelForm):
    type = forms.CharField(label="Type", max_length=50, help_text="Enter the species or breed name.")

    class Meta:
        model = Animal
        fields = ["name", "type", "age", "description", "image", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].widget.attrs.update({"placeholder": "e.g. Cat or Arabic name"})

    def clean_type(self):
        value = (self.cleaned_data.get("type") or "").strip()
        if not value:
            raise forms.ValidationError("Please provide an animal type.")
        return value

class AdoptionRequestForm(forms.ModelForm):
    class Meta:
        model = AdoptionRequest
        fields = ["message"] 

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
