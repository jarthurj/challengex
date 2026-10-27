from django.contrib import admin

from .models import Table, Row


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
