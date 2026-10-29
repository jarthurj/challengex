from django.urls import path
from . import views, trend_views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tables/", views.table_list, name="table-list"),
    path("tables/<int:pk>/", views.table_detail, name="table-detail"),

    path("trends/", trend_views.trends, name="trends"),
    path("trends/data/", trend_views.trend_data, name="trend-data"),
]
