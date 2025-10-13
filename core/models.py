from django.db import models
from django.contrib.auth.models import User

class AnimalStatus(models.TextChoices):
    AVAILABLE = "Available"
    PENDING = "Pending"
    ADOPTED = "Adopted"

class Animal(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50)  # e.g., Dog, Cat, Bird
    age = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="animals/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=AnimalStatus.choices, default=AnimalStatus.AVAILABLE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

class RequestStatus(models.TextChoices):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class AdoptionRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="requests")
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "animal")  # prevent duplicate requests by same user for same animal
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.animal.name} ({self.status})"
