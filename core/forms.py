from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .constants import ANIMAL_TYPE_CHOICES
from .models import Animal, AdoptionRequest

class AnimalForm(forms.ModelForm):
    type = forms.ChoiceField(choices=ANIMAL_TYPE_CHOICES, label="Type")

    class Meta:
        model = Animal
        fields = ["name", "type", "age", "description", "image", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_type = self.initial.get("type")
        if initial_type:
            self.initial["type"] = initial_type.lower()

    def clean_type(self):
        return self.cleaned_data["type"].lower()

class AdoptionRequestForm(forms.ModelForm):
    class Meta:
        model = AdoptionRequest
        fields = ["message"]

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
