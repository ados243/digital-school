from django import forms


class FormControlMixin:
    """Applique la classe form-control à tous les champs du formulaire."""

    checkbox_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.RadioSelect):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "form-control")
                widget.attrs.setdefault("rows", widget.attrs.get("rows", 3))
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-control")
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", "form-control")
            else:
                widget.attrs.setdefault("class", "form-control")

    def __getitem__(self, name):
        # aria-invalid après is_valid() uniquement — ne jamais lire self.errors
        # dans __init__ (cela lance full_clean avant la fin du __init__ enfant,
        # ex. self.ecole pas encore défini → AttributeError).
        bound = super().__getitem__(name)
        errors = getattr(self, "_errors", None)
        if errors is not None and name in errors:
            bound.field.widget.attrs["aria-invalid"] = "true"
        return bound
