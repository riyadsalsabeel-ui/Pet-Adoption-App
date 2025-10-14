from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import BooleanField, Case, CharField, Exists, IntegerField, OuterRef, Subquery, Value, When
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import AdoptionRequestForm, AnimalForm, SignUpForm
from .models import AdoptionRequest, Animal, AnimalStatus, RequestStatus


def home(request: HttpRequest) -> HttpResponse:
    """Homepage listing available animals with optional type filter."""
    status_priority = Case(
        When(status=AnimalStatus.AVAILABLE, then=0),
        When(status=AnimalStatus.PENDING, then=1),
        default=2,
        output_field=IntegerField(),
    )
    animals = Animal.objects.all().annotate(status_priority=status_priority).order_by("status_priority", "-created_at")
    requested_type = (request.GET.get("type") or "").strip()
    normalized_requested_type = requested_type.lower()
    if requested_type and normalized_requested_type != "all":
        animals = animals.filter(type__iexact=requested_type)

    if request.user.is_authenticated:
        user_requests = AdoptionRequest.objects.filter(user=request.user, animal=OuterRef("pk"))
        animals = animals.annotate(
            has_requested=Exists(user_requests),
            request_status=Subquery(user_requests.values("status")[:1]),
        )
    else:
        animals = animals.annotate(
            has_requested=Value(False, output_field=BooleanField()),
            request_status=Value("", output_field=CharField(max_length=10)),
        )

    animals = animals.order_by("status_priority", "-created_at").select_related("created_by")

    request_form = AdoptionRequestForm()

    available_types = list(
        Animal.objects.order_by("type").values_list("type", flat=True).distinct()
    )
    type_options = ["all", *[t for t in available_types if t]]
    if requested_type and normalized_requested_type != "all" and requested_type not in type_options:
        type_options.append(requested_type)

    context = {
        "animals": animals,
        "filter_type": "all" if not requested_type or normalized_requested_type == "all" else requested_type,
        "type_options": type_options,
        "request_form": request_form,
    }
    return render(request, "animals/list.html", context)


def signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("core:home")
        messages.error(request, "Please fix the highlighted errors and try again.")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


class CozyLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        messages.success(self.request, "Welcome back! You are logged in.")
        return super().form_valid(form)


def cozy_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.success(request, "You are logged out. See you soon!")
    return render(request, "registration/logged_out.html") 


def _can_manage_animal(animal: Animal, user) -> bool:
    return user.is_authenticated and (user.is_staff or animal.created_by_id == user.id)


def animal_detail(request: HttpRequest, pk: int) -> HttpResponse:
    animal = get_object_or_404(Animal, pk=pk)
    confirm_delete = request.GET.get("confirm") == "1"

    existing_request = None
    if request.user.is_authenticated:
        existing_request = AdoptionRequest.objects.filter(user=request.user, animal=animal).first()

    context = {
        "animal": animal,
        "confirm_delete": confirm_delete,
        "existing_request": existing_request,
        "can_manage": _can_manage_animal(animal, request.user),
    }
    return render(request, "animals/detail.html", context)


@login_required
def animal_manage_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        messages.error(request, "Only staff members can manage animals.")
        return redirect("core:home")

    animals = Animal.objects.select_related("created_by").order_by("-created_at")
    return render(request, "animals/manage_list.html", {"animals": animals})


@login_required
def animal_create(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        messages.error(request, "Only staff members can add animals.")
        return redirect("core:home")

    if request.method == "POST":
        form = AnimalForm(request.POST, request.FILES)
        if form.is_valid():
            animal = form.save(commit=False)
            animal.created_by = request.user
            animal.save()
            messages.success(request, f"{animal.name} added successfully.")
            return redirect("core:animal_detail", pk=animal.pk)
    else:
        form = AnimalForm()

    return render(request, "animals/form.html", {"form": form, "mode": "add"})


@login_required
def animal_update(request: HttpRequest, pk: int) -> HttpResponse:
    animal = get_object_or_404(Animal, pk=pk)
    if not _can_manage_animal(animal, request.user):
        messages.error(request, "You do not have permission to edit this animal.")
        return redirect("core:animal_detail", pk=pk)

    if request.method == "POST":
        form = AnimalForm(request.POST, request.FILES, instance=animal)
        if form.is_valid():
            form.save()
            messages.success(request, f"{animal.name} updated successfully.")
            return redirect("core:animal_detail", pk=pk)
    else:
        form = AnimalForm(instance=animal)

    return render(request, "animals/form.html", {"form": form, "mode": "edit", "animal": animal})


@login_required
def animal_delete(request: HttpRequest, pk: int) -> HttpResponse:
    animal = get_object_or_404(Animal, pk=pk)
    if not _can_manage_animal(animal, request.user):
        messages.error(request, "You do not have permission to delete this animal.")
        return redirect("core:animal_detail", pk=pk)

    if request.method == "POST":
        animal_name = animal.name
        animal.delete()
        messages.success(request, f"{animal_name} deleted.")
        return redirect("core:home")

    url = f"{reverse('core:animal_detail', args=[pk])}?confirm=1"
    return redirect(url)


@login_required
def request_create(request: HttpRequest, animal_id: int) -> HttpResponse:
    animal = get_object_or_404(Animal, pk=animal_id)

    if request.user.is_staff:
        messages.error(request, "Admins manage adoptions and cannot submit requests.")
        return redirect("core:animal_detail", pk=animal.pk)

    if animal.created_by_id == request.user.id:
        messages.error(request, "You cannot request adoption for an animal you created.")
        return redirect("core:animal_detail", pk=animal.pk)

    if animal.status == AnimalStatus.ADOPTED:
        messages.error(request, "This animal has already been adopted.")
        return redirect("core:animal_detail", pk=animal.pk)

    existing = AdoptionRequest.objects.filter(user=request.user, animal=animal).first()
    if existing:
        messages.info(request, "You already submitted a request for this animal.")
        return redirect("core:animal_detail", pk=animal.pk)

    if request.method == "POST":
        form = AdoptionRequestForm(request.POST)
        if form.is_valid():
            adoption_request = form.save(commit=False)
            adoption_request.user = request.user
            adoption_request.animal = animal
            adoption_request.save()
            if animal.status == AnimalStatus.AVAILABLE:
                animal.status = AnimalStatus.PENDING
                animal.save(update_fields=["status"])
            messages.success(request, "Adoption request submitted.")
            return redirect("core:my_requests")
    else:
        form = AdoptionRequestForm()

    return render(
        request,
        "requests/form.html",
        {"form": form, "animal": animal},
    )


@login_required
def my_requests(request: HttpRequest) -> HttpResponse:
    if request.user.is_staff:
        messages.info(request, "Use the request dashboard to manage adoptions.")
        return redirect("core:manage_requests")

    pending_requests = (
        AdoptionRequest.objects.filter(user=request.user)
        .select_related("animal")
    )
    return render(request, "requests/list.html", {"requests": pending_requests})


@login_required
def manage_requests(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        messages.error(request, "Only admins can access the request manager.")
        return redirect("core:home")

    requests_qs = (
        AdoptionRequest.objects.select_related("animal", "user")
        .order_by("-created_at")
    )

    if request.method == "POST":
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")
        adoption_request = get_object_or_404(AdoptionRequest, pk=request_id)
        animal = adoption_request.animal

        if action == "approve":
            adoption_request.status = RequestStatus.APPROVED
            adoption_request.save(update_fields=["status"])
            animal.status = AnimalStatus.ADOPTED
            animal.save(update_fields=["status"])
            AdoptionRequest.objects.filter(animal=animal).exclude(pk=adoption_request.pk).update(
                status=RequestStatus.REJECTED
            )
            messages.success(request, f"{animal.name} marked as adopted.")
        elif action == "reject":
            adoption_request.status = RequestStatus.REJECTED
            adoption_request.save(update_fields=["status"])
            if not AdoptionRequest.objects.filter(animal=animal, status=RequestStatus.APPROVED).exclude(
                pk=adoption_request.pk
            ).exists():
                if AdoptionRequest.objects.filter(animal=animal, status=RequestStatus.PENDING).exclude(
                    pk=adoption_request.pk
                ).exists():
                    animal.status = AnimalStatus.PENDING
                else:
                    animal.status = AnimalStatus.AVAILABLE
                animal.save(update_fields=["status"])
            messages.info(request, f"Request from {adoption_request.user.username} rejected.")
        elif action == "reset":
            adoption_request.status = RequestStatus.PENDING
            adoption_request.save(update_fields=["status"])
            animal.status = AnimalStatus.PENDING
            animal.save(update_fields=["status"])
            AdoptionRequest.objects.filter(animal=animal).exclude(pk=adoption_request.pk).update(
                status=RequestStatus.PENDING
            )
            messages.success(request, f"{animal.name} request reset to pending.")
        else:
            messages.error(request, "Unknown action.")

        return redirect("core:manage_requests")

    return render(
        request,
        "requests/manage.html",
        {"requests": requests_qs},
    ) 
