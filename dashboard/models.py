from django.db import models


class Table(models.Model):
    source_id = models.CharField(max_length=32, unique=True)  # e.g. 2021-p020-1
    year = models.PositiveIntegerField(db_index=True)
    page = models.PositiveIntegerField()
    table_number = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=500, blank=True, db_index=True)
    columns = models.JSONField(default=list)
    ocr = models.BooleanField(default=False)  # True = read from scanned page

    class Meta:
        ordering = ["year", "page", "source_id"]

    def __str__(self):
        return (
            f"{self.source_id} | {self.year} p{self.page} "
            f"#{self.table_number} {self.title} | "
            f"cols={self.columns} | ocr={self.ocr}"
        ).strip()

class Row(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name="rows")
    position = models.PositiveIntegerField()
    label = models.CharField(max_length=500, blank=True)  # first column
    data = models.JSONField(default=dict)  # {codlumn: {"raw": "96%", "num": 96.0}}

    class Meta:
        ordering = ["table", "position"]
