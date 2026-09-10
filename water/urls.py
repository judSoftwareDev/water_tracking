from django.urls import path

from . import views


app_name = "water"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("participants/", views.participant_list, name="participant_list"),
    path("participants/add/", views.participant_create, name="participant_create"),
    path("participants/<int:pk>/", views.participant_detail, name="participant_detail"),
    path("participants/<int:pk>/edit/", views.participant_edit, name="participant_edit"),
    path("purchases/", views.purchase_list, name="purchase_list"),
    path("purchases/add/", views.purchase_create, name="purchase_create"),
    path("purchases/<int:pk>/", views.purchase_detail, name="purchase_detail"),
    path("purchases/<int:pk>/delete/", views.purchase_delete, name="purchase_delete"),
    path("gallons/<int:pk>/status/", views.gallon_status_update, name="gallon_status_update"),
]
