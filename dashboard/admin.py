from django.contrib import admin

from .models import MethodologyBreak, Metric, Observation, Row, Segment, Table


class RowInline(admin.TabularInline):
    model = Row
    extra = 0
    fields = ["position", "label", "data"]


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ["source_id", "year", "page", "table_number", "title", "ocr"]
    list_filter = ["year", "ocr"]
    search_fields = ["source_id", "table_number", "title"]
    inlines = [RowInline]


@admin.register(Row)
class RowAdmin(admin.ModelAdmin):
    list_display = ["table", "position", "label"]
    list_filter = ["table__year"]
    search_fields = ["label", "table__source_id"]
    list_select_related = ["table"]


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "market", "direction", "unit"]
    list_filter = ["market", "unit"]


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ["dimension", "value", "position"]
    list_filter = ["dimension"]


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    # Reviewers tick `verified` here after checking a value against the source PDF page.
    list_display = ["metric", "segment", "fiscal_year", "value", "raw_value", "report_year",
                    "source_table", "is_preferred", "verified"]
    list_editable = ["verified"]
    list_filter = ["metric", "is_preferred", "verified", "report_year", "segment__dimension"]
    list_select_related = ["metric", "segment", "source_table"]
    raw_id_fields = ["source_table"]


@admin.register(MethodologyBreak)
class MethodologyBreakAdmin(admin.ModelAdmin):
    list_display = ["fiscal_year", "title"]
    filter_horizontal = ["metrics"]
