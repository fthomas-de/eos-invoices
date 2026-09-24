from django.urls import path

from . import views

app_name = "eos_invoices"

urlpatterns = [
    path("", views.index, name="index"),
    path("admin/", views.admin_overview, name="admin"),
    path("log/", views.payment_log, name="log"),
    path("log/<int:pk>/undo/", views.undo_marking, name="undo_marking"),
    path("sources/", views.sources, name="sources"),
    path("sources/add/", views.source_edit, name="source_add"),
    path("sources/fields/", views.source_fields, name="source_fields"),
    path("sources/<int:pk>/", views.source_edit, name="source_edit"),
    path("sources/<int:pk>/delete/", views.source_delete, name="source_delete"),
    path("sources/<int:pk>/mark-paid/", views.mark_paid, name="mark_paid"),
    path("mark-paid/", views.mark_selected_paid, name="mark_selected_paid"),
    path("settings/", views.settings, name="settings"),
]
