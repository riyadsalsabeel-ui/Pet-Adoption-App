from django.contrib import admin
from .models import Animal, AdoptionRequest

@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "age", "status", "created_by", "created_at")
    list_filter = ("status", "type")
    search_fields = ("name", "description")
    autocomplete_fields = ("created_by",)

@admin.register(AdoptionRequest)
class AdoptionRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "animal", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("message", "animal__name", "user__username")
    autocomplete_fields = ("animal", "user")
