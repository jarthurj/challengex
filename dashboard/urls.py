from django.urls import path

from . import ai_views, overview_views, settings_views, trend_views, views, welcome_views

urlpatterns = [
    path("", overview_views.overview, name="dashboard"),
    path("welcome/", welcome_views.welcome, name="welcome"),
    path("ai/", ai_views.ai_summaries, name="ai-summaries"),
    path("ai/generate/", ai_views.ai_generate, name="ai-generate"),
    path("ai/export.txt", ai_views.ai_export, name="ai-export"),
    path("ai/<slug:section>/<str:key>/", ai_views.ai_summary_detail, name="ai-summary"),
    path("ai/<slug:section>/<str:key>/review/", ai_views.ai_review, name="ai-review"),
    path("year/", overview_views.year_pick, name="year-pick"),
    path("year/<int:year>/", overview_views.year_detail, name="year-detail"),
    path("year/<int:year>/csv/", overview_views.year_csv, name="year-csv"),
    path("tables/", views.table_list, name="table-list"),
    path("tables/<int:pk>/", views.table_detail, name="table-detail"),
    path("reports/<int:year>.pdf", views.source_pdf, name="source-pdf"),
    path("trends/", trend_views.trends, name="trends"),
    path("trends/data/", trend_views.trend_data, name="trend-data"),
    path("trends/csv/", trend_views.trend_csv, name="trend-csv"),
    path("settings/", settings_views.settings_page, name="settings"),
]
