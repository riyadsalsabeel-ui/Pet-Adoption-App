from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.CozyLoginView.as_view(), name="login"),
    path("logout/", views.cozy_logout, name="logout"),
    path("signup/", views.signup, name="signup"),
    path("animal/<int:pk>/", views.animal_detail, name="animal_detail"),
    path("animal/add/", views.animal_create, name="animal_create"),
    path("animal/<int:pk>/edit/", views.animal_update, name="animal_update"),
    path("animal/<int:pk>/delete/", views.animal_delete, name="animal_delete"),
    path("adopt/<int:animal_id>/", views.request_create, name="request_create"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("manage/requests/", views.manage_requests, name="manage_requests"),
]
