# Generated manually for budget rubriques

from django.db import migrations, models
import django.db.models.deletion


RUBRIQUES = (
    ("R_MINERVAL", "Minerval / frais de scolarité", "RECETTE", 10, "MINERVAL", "Capacité des classes × barème minerval"),
    ("R_INSCRIPTION", "Frais d'inscription", "RECETTE", 20, "INSCRIPTION", "Capacité × frais d'inscription par section"),
    ("R_EXAMEN", "Frais d'examen / compositions", "RECETTE", 30, "", ""),
    ("R_TENUE", "Tenues / uniformes", "RECETTE", 40, "", ""),
    ("R_LABO", "Laboratoire / informatique", "RECETTE", 50, "", ""),
    ("R_TRANSPORT", "Transport scolaire", "RECETTE", 60, "", ""),
    ("R_CANTINE", "Cantine / restauration", "RECETTE", 70, "", ""),
    ("R_COTI", "Cotisations / association des parents", "RECETTE", 80, "", ""),
    ("R_SUBVENTION", "Subventions / dons", "RECETTE", 90, "", ""),
    ("R_AUTRES", "Autres recettes", "RECETTE", 100, "", ""),
    ("D_SALAIRES", "Salaires du personnel", "DEPENSE", 10, "SALAIRES", "Somme des salaires de base des contrats actifs × 12 mois"),
    ("D_CHARGES_SOC", "Charges sociales (INSS / ONEM)", "DEPENSE", 20, "", ""),
    ("D_FOURNITURES", "Fournitures pédagogiques", "DEPENSE", 30, "", ""),
    ("D_DIDACTIQUE", "Matériel didactique / manuels", "DEPENSE", 40, "", ""),
    ("D_EAU_ELEC", "Eau et électricité", "DEPENSE", 50, "", ""),
    ("D_INTERNET", "Internet / télécommunications", "DEPENSE", 60, "", ""),
    ("D_ENTRETIEN", "Entretien et maintenance", "DEPENSE", 70, "", ""),
    ("D_CARBURANT", "Carburant / transport", "DEPENSE", 80, "", ""),
    ("D_SECURITE", "Sécurité / gardiennage", "DEPENSE", 90, "", ""),
    ("D_IMPOTS", "Impôts et taxes", "DEPENSE", 100, "", ""),
    ("D_ASSURANCE", "Assurances", "DEPENSE", 110, "", ""),
    ("D_FORMATION", "Formation / recyclage", "DEPENSE", 120, "", ""),
    ("D_INVEST", "Investissements / équipements", "DEPENSE", 130, "", ""),
    ("D_PARASCO", "Activités parascolaires", "DEPENSE", 140, "", ""),
    ("D_IMPREVUS", "Imprévus / divers", "DEPENSE", 150, "", ""),
)


def seed_rubriques(apps, schema_editor):
    RubriqueBudget = apps.get_model("finances", "RubriqueBudget")
    for code, libelle, nature, ordre, calcul_auto, description in RUBRIQUES:
        RubriqueBudget.objects.update_or_create(
            code=code,
            defaults={
                "libelle": libelle,
                "nature": nature,
                "ordre": ordre,
                "calcul_auto": calcul_auto,
                "description": description,
                "actif": True,
            },
        )


def unseed_rubriques(apps, schema_editor):
    RubriqueBudget = apps.get_model("finances", "RubriqueBudget")
    RubriqueBudget.objects.filter(code__in=[r[0] for r in RUBRIQUES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0015_budget_annuel"),
    ]

    operations = [
        migrations.CreateModel(
            name="RubriqueBudget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("libelle", models.CharField(max_length=255)),
                ("nature", models.CharField(choices=[("RECETTE", "Recette"), ("DEPENSE", "Dépense")], max_length=10)),
                ("ordre", models.PositiveIntegerField(default=100)),
                (
                    "calcul_auto",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "Saisie manuelle"),
                            ("MINERVAL", "Auto — capacité × minerval"),
                            ("INSCRIPTION", "Auto — capacité × frais d'inscription"),
                            ("SALAIRES", "Auto — salaires annuels (contrats × 12)"),
                        ],
                        default="",
                        max_length=20,
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=500)),
                ("actif", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Rubrique de budget",
                "verbose_name_plural": "Rubriques de budget",
                "ordering": ["nature", "ordre", "libelle"],
            },
        ),
        migrations.AddField(
            model_name="budgetannuel",
            name="total_depenses_cdf",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name="budgetannuel",
            name="total_depenses_usd",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name="budgetannuel",
            name="total_recettes_cdf",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name="budgetannuel",
            name="total_recettes_usd",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AlterModelOptions(
            name="lignebudget",
            options={
                "ordering": ["classe__section__section", "classe__classe"],
                "verbose_name": "Ligne de budget minerval",
                "verbose_name_plural": "Lignes de budget minerval",
            },
        ),
        migrations.CreateModel(
            name="PosteBudget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("montant_usd", models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ("montant_cdf", models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ("est_auto", models.BooleanField(default=False)),
                ("note", models.CharField(blank=True, max_length=255)),
                (
                    "budget",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="postes",
                        to="finances.budgetannuel",
                    ),
                ),
                (
                    "rubrique",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="postes",
                        to="finances.rubriquebudget",
                    ),
                ),
            ],
            options={
                "verbose_name": "Poste budgétaire",
                "verbose_name_plural": "Postes budgétaires",
                "ordering": ["rubrique__nature", "rubrique__ordre", "rubrique__libelle"],
            },
        ),
        migrations.AddConstraint(
            model_name="postebudget",
            constraint=models.UniqueConstraint(fields=("budget", "rubrique"), name="uniq_poste_budget_rubrique"),
        ),
        migrations.RunPython(seed_rubriques, unseed_rubriques),
    ]
