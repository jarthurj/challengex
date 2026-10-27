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


# Clean, queryable layer built from Table/Row by `manage.py load_metrics`.
# Table/Row stay the raw source; every Observation points back to its Table.

class Metric(models.Model):
    MARKETS = [
        ("correspondence", "Correspondence"),
        ("transactions", "Transactions"),
        ("advertising", "Advertising"),
        ("periodicals", "Periodicals"),
        ("packages", "Packages"),
        ("total", "Total"),
    ]
    DIRECTIONS = [("received", "Received"), ("sent", "Sent"), ("total", "Total")]
    UNITS = [
        ("millions", "Millions of pieces"),
        ("per_household_year", "Pieces per household per year"),
        ("percent", "Percent"),
    ]

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    market = models.CharField(max_length=20, choices=MARKETS)
    direction = models.CharField(max_length=20, choices=DIRECTIONS)
    unit = models.CharField(max_length=30, choices=UNITS)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["market", "slug"]

    def __str__(self):
        return self.name


class Segment(models.Model):
    DIMENSIONS = [
        ("all", "All households"),
        ("age", "Age of householder"),
        ("income", "Household income"),
        ("education", "Education of householder"),
        ("tenure", "Homeownership"),
        ("msa", "MSA classification"),
    ]

    dimension = models.CharField(max_length=20, choices=DIMENSIONS)
    value = models.CharField(max_length=100)  # e.g. "65 and Over", "$150,000 and Over"
    position = models.PositiveIntegerField(default=0)  # display order within a dimension

    class Meta:
        ordering = ["dimension", "position"]
        constraints = [
            models.UniqueConstraint(fields=["dimension", "value"], name="unique_segment"),
        ]

    def __str__(self):
        return self.value if self.dimension == "all" else f"{self.get_dimension_display()}: {self.value}"


class Observation(models.Model):
    metric = models.ForeignKey(Metric, on_delete=models.CASCADE, related_name="observations")
    segment = models.ForeignKey(Segment, on_delete=models.PROTECT, related_name="observations")
    fiscal_year = models.PositiveIntegerField(db_index=True)
    value = models.FloatField()  # in metric.unit
    raw_value = models.CharField(max_length=50)  # cell text as extracted, e.g. "35,729"
    raw_unit = models.CharField(max_length=30)  # unit the source table reports in
    # Cascades: re-run load_metrics after load_tables.
    source_table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name="observations")
    report_year = models.PositiveIntegerField()  # which annual report published this value
    is_preferred = models.BooleanField(default=False)  # the one value to chart for this year
    verified = models.BooleanField(default=False)  # checked against the source PDF page; notes say how
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["metric", "segment", "fiscal_year", "-report_year"]
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "segment", "fiscal_year", "report_year"],
                name="unique_observation_per_report",
            ),
        ]

    def __str__(self):
        return f"{self.metric.slug} {self.segment} FY{self.fiscal_year} = {self.value} (FY{self.report_year} report)"


class MethodologyBreak(models.Model):
    """A survey or reporting change that makes values before and after a year not directly comparable."""

    fiscal_year = models.PositiveIntegerField()  # first year under the new method
    title = models.CharField(max_length=200)
    description = models.TextField()
    metrics = models.ManyToManyField(Metric, blank=True, related_name="breaks")  # empty = all metrics

    class Meta:
        ordering = ["fiscal_year"]

    def __str__(self):
        return f"FY{self.fiscal_year}: {self.title}"
