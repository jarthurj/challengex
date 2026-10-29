from django.contrib import admin
from django.urls import path
from . import views
from . import trend_views
urlpatterns = [
    path('', views.dashboard, name='dashboard'), 
    path("tables/", views.table_list, name="table-list"),
    path("tables/<int:pk>/", views.table_detail, name="table-detail"),
    path("trends/", views.trends, name="trends"),
]
