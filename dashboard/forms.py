
from django import forms
from .models import Table, Row


class TableForm(forms.ModelForm):
    columns = forms.JSONField(
        required=False,
        initial=list,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "class": "form-control",
            "placeholder": '["Region", "Population", "Percentage"]',
        }),
    )

    class Meta:
        model = Table
        fields = [
            "source_id",
            "year",
            "page",
            "table_number",
            "title",
            "columns",
            "ocr",
        ]
        widgets = {
            "source_id": forms.TextInput(attrs={"class": "form-control"}),
            "year": forms.NumberInput(attrs={"class": "form-control"}),
            "page": forms.NumberInput(attrs={"class": "form-control"}),
            "table_number": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "ocr": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class RowForm(forms.ModelForm):
    data = forms.JSONField(
        required=False,
        initial=dict,
        widget=forms.Textarea(attrs={
            "rows": 6,
            "class": "form-control",
            "placeholder": '{"Population": {"raw": "96%", "num": 96.0}}',
        }),
    )

    class Meta:
        model = Row
        fields = [
            "table",
            "position",
            "label",
            "data",
        ]
        widgets = {
            "table": forms.Select(attrs={"class": "form-select"}),
            "position": forms.NumberInput(attrs={"class": "form-control"}),
            "label": forms.TextInput(attrs={"class": "form-control"}),
        }
