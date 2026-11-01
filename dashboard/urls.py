from django.urls import path

from . import overview_views, trend_views, views

urlpatterns = [
    path("", overview_views.overview, name="dashboard"),
    path("year/", overview_views.year_pick, name="year-pick"),
    path("year/<int:year>/", overview_views.year_detail, name="year-detail"),
    path("year/<int:year>/csv/", overview_views.year_csv, name="year-csv"),
    path("tables/", views.table_list, name="table-list"),
    path("tables/<int:pk>/", views.table_detail, name="table-detail"),
    path("reports/<int:year>.pdf", views.source_pdf, name="source-pdf"),
    path("trends/", trend_views.trends, name="trends"),
    path("trends/data/", trend_views.trend_data, name="trend-data"),
    path("trends/csv/", trend_views.trend_csv, name="trend-csv"),
]
