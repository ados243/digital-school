from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from common.form_mixins import FormControlMixin
from common.tenant import get_user_ecole
from grh.models import Personnel
from inscription.models import Classe
from inscription.tenant import classes_for_ecole
from .models import CreneauEmploiDuTemps, Matiere


class CreneauEmploiForm(FormControlMixin, forms.ModelForm):
    class Meta:
        model = CreneauEmploiDuTemps
        fields = ["jour", "heure_debut", "heure_fin", "matiere", "enseignant", "salle"]
        widgets = {
            "heure_debut": forms.TimeInput(attrs={"type": "time"}),
            "heure_fin": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, ecole=None, classe=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ecole is not None:
            matieres = Matiere.objects.filter(ecole=ecole)
            if classe is not None:
                matieres = matieres.filter(section=classe.section)
            self.fields["matiere"].queryset = matieres.order_by("libelle")
            self.fields["enseignant"].queryset = Personnel.objects.filter(ecole=ecole).order_by("nom")
        self.fields["matiere"].required = False
        self.fields["enseignant"].required = False


@login_required
def emploi_du_temps(request, classe_id=None):
    ecole = get_user_ecole(request)
    classes = classes_for_ecole(ecole).select_related("section").order_by("section__section", "classe")
    classe = None
    if classe_id:
        classe = get_object_or_404(classes, pk=classe_id)
    elif classes.exists():
        classe = classes.first()

    creneaux = []
    form = None
    if classe:
        creneaux = list(
            CreneauEmploiDuTemps.objects.filter(ecole=ecole, classe=classe)
            .select_related("matiere", "enseignant")
            .order_by("jour", "heure_debut")
        )
        if request.method == "POST":
            form = CreneauEmploiForm(request.POST, ecole=ecole, classe=classe)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.ecole = ecole
                obj.classe = classe
                obj.save()
                messages.success(request, "Créneau ajouté.")
                return redirect("pedagogie:emploi_du_temps_classe", classe_id=classe.pk)
        else:
            form = CreneauEmploiForm(ecole=ecole, classe=classe)

    par_jour = []
    for value, label in CreneauEmploiDuTemps.JOURS:
        par_jour.append({
            "jour": value,
            "label": label,
            "creneaux": [c for c in creneaux if c.jour == value],
        })

    return render(request, "pedagogie/emploi_du_temps.html", {
        "classes": classes,
        "classe": classe,
        "par_jour": par_jour,
        "form": form,
    })


@login_required
def creneau_delete(request, pk):
    ecole = get_user_ecole(request)
    creneau = get_object_or_404(CreneauEmploiDuTemps, pk=pk, ecole=ecole)
    classe_id = creneau.classe_id
    if request.method == "POST":
        creneau.delete()
        messages.success(request, "Créneau retiré.")
    return redirect("pedagogie:emploi_du_temps_classe", classe_id=classe_id)
