from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import Personnel, Contrat, Conge, Presence, Paie
from .forms import PersonnelForm, ContratForm, CongeForm, PresenceForm, PaieForm
from .tenant import (
    get_user_ecole,
    personnel_for_ecole,
    contrats_for_ecole,
    conges_for_ecole,
    presences_for_ecole,
    paies_for_ecole,
)
from finances.models import Devise

@login_required
def dashboard(request):
    ecole = get_user_ecole(request)
    personnel_qs = personnel_for_ecole(ecole)
    contrats_qs = contrats_for_ecole(ecole)
    conges_qs = conges_for_ecole(ecole)
    paies_qs = paies_for_ecole(ecole)
    presences_qs = presences_for_ecole(ecole)

    total_personnel = personnel_qs.count()
    contrats_actifs = contrats_qs.filter(statut='ACTIF').count()
    conges_en_attente = conges_qs.filter(statut='EN_ATTENTE').count()
    
    # Calculate sum of payments (net_a_payer) for the current month/year
    today = date.today()
    paies_mois = paies_qs.filter(mois=today.month, annee=today.year)
    total_paie_mensuelle_usd = paies_mois.filter(devise__devise='USD').aggregate(total=Sum('net_a_payer'))['total'] or 0
    total_paie_mensuelle_cdf = paies_mois.filter(devise__devise='CDF').aggregate(total=Sum('net_a_payer'))['total'] or 0
    
    # Recent activities
    recent_conges = conges_qs.order_by('-id')[:5]
    recent_paies = paies_qs.order_by('-id')[:5]
    recent_personnel = personnel_qs.order_by('-id')[:5]
    
    # Today's attendance summary
    presences_aujourdhui = presences_qs.filter(date=today)
    nb_presents = presences_aujourdhui.filter(statut='PRESENT').count()
    nb_absents = presences_aujourdhui.filter(statut='ABSENT').count()
    nb_retards = presences_aujourdhui.filter(statut='RETARD').count()
    nb_conges = presences_aujourdhui.filter(statut='CONGE').count()
    
    context = {
        'total_personnel': total_personnel,
        'contrats_actifs': contrats_actifs,
        'conges_en_attente': conges_en_attente,
        'total_paie_mensuelle_usd': total_paie_mensuelle_usd,
        'total_paie_mensuelle_cdf': total_paie_mensuelle_cdf,
        'recent_conges': recent_conges,
        'recent_paies': recent_paies,
        'recent_personnel': recent_personnel,
        'nb_presents': nb_presents,
        'nb_absents': nb_absents,
        'nb_retards': nb_retards,
        'nb_conges': nb_conges,
        'today': today,
    }
    return render(request, 'grh/dashboard.html', context)

# --- Personnel CRUD ---
@login_required
def personnel_list(request):
    ecole = get_user_ecole(request)
    personnels = (
        personnel_for_ecole(ecole)
        .select_related('ecole')
        .order_by('nom', 'Post_nom', 'prenom')
    )
    return render(request, 'grh/personnel_list.html', {
        'personnels': personnels,
        'ecole': ecole,
    })

@login_required
def personnel_create(request):
    from inscription.forms import QuartierForm

    ecole = get_user_ecole(request)
    if request.method == 'POST':
        form = PersonnelForm(request.POST, request.FILES)
        if form.is_valid():
            personnel = form.save(commit=False)
            personnel.ecole = ecole
            personnel.save()
            messages.success(
                request,
                f"Membre du personnel ajouté avec succès (matricule {personnel.matricule}).",
            )
            return redirect('grh:personnel_list')
    else:
        form = PersonnelForm()
    return render(request, 'grh/personnel_form.html', {
        'form': form,
        'title': "Ajouter un membre du personnel",
        'quartier_form': QuartierForm(prefix='quartier_modal'),
        'quartier_create_url': reverse('inscription:quartier_create'),
    })

@login_required
def personnel_update(request, pk):
    from inscription.forms import QuartierForm

    ecole = get_user_ecole(request)
    personnel = get_object_or_404(Personnel, pk=pk, ecole=ecole)
    if request.method == 'POST':
        form = PersonnelForm(request.POST, request.FILES, instance=personnel)
        if form.is_valid():
            form.save()
            messages.success(request, "Informations du personnel mises à jour.")
            return redirect('grh:personnel_list')
    else:
        form = PersonnelForm(instance=personnel)
    return render(request, 'grh/personnel_form.html', {
        'form': form,
        'title': "Modifier le membre du personnel",
        'personnel': personnel,
        'quartier_form': QuartierForm(prefix='quartier_modal'),
        'quartier_create_url': reverse('inscription:quartier_create'),
    })

@login_required
def personnel_delete(request, pk):
    ecole = get_user_ecole(request)
    personnel = get_object_or_404(Personnel, pk=pk, ecole=ecole)
    if request.method == 'POST':
        personnel.delete()
        messages.success(request, "Membre du personnel supprimé.")
        return redirect('grh:personnel_list')
    return render(request, 'grh/personnel_confirm_delete.html', {'personnel': personnel})

# --- Contrats CRUD ---
@login_required
def contrat_list(request):
    ecole = get_user_ecole(request)
    contrats = (
        contrats_for_ecole(ecole)
        .select_related('personnel', 'personnel__ecole', 'devise')
        .order_by('personnel__nom', 'personnel__Post_nom', 'personnel__prenom')
    )
    return render(request, 'grh/contrat_list.html', {'contrats': contrats})

@login_required
def contrat_create(request):
    ecole = get_user_ecole(request)
    if request.method == 'POST':
        form = ContratForm(request.POST, ecole=ecole)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrat de travail créé avec succès.")
            return redirect('grh:contrat_list')
    else:
        form = ContratForm(ecole=ecole)
    context = {
        'form': form,
        'title': "Créer un contrat",
        'personnel_count': personnel_for_ecole(ecole).count(),
        'contrats_actifs_count': contrats_for_ecole(ecole).filter(statut='ACTIF').count(),
        'devises_count': Devise.objects.count(),
    }
    return render(request, 'grh/contrat_form.html', context)

@login_required
def contrat_update(request, pk):
    ecole = get_user_ecole(request)
    contrat = get_object_or_404(Contrat, pk=pk, personnel__ecole=ecole)
    if request.method == 'POST':
        form = ContratForm(request.POST, instance=contrat, ecole=ecole)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrat mis à jour.")
            return redirect('grh:contrat_list')
    else:
        form = ContratForm(instance=contrat, ecole=ecole)
    return render(request, 'grh/contrat_form.html', {'form': form, 'title': "Modifier le contrat"})

# --- Congés ---
@login_required
def conge_list(request):
    ecole = get_user_ecole(request)
    conges = (
        conges_for_ecole(ecole)
        .select_related('personnel')
        .order_by('-id')
    )
    return render(request, 'grh/conge_list.html', {'conges': conges})

@login_required
def conge_create(request):
    ecole = get_user_ecole(request)
    if request.method == 'POST':
        form = CongeForm(request.POST, ecole=ecole)
        if form.is_valid():
            form.save()
            messages.success(request, "Demande de congé enregistrée.")
            return redirect('grh:conge_list')
    else:
        form = CongeForm(ecole=ecole)
    context = {
        'form': form,
        'personnel_count': personnel_for_ecole(ecole).count(),
        'conges_en_attente_count': conges_for_ecole(ecole).filter(statut='EN_ATTENTE').count(),
        'conges_approuves_count': conges_for_ecole(ecole).filter(statut='APPROUVE').count(),
    }
    return render(request, 'grh/conge_form.html', context)

@login_required
def conge_approve(request, pk):
    ecole = get_user_ecole(request)
    conge = get_object_or_404(Conge, pk=pk, personnel__ecole=ecole)
    conge.statut = 'APPROUVE'
    conge.save()
    
    # Enregistrer automatiquement la présence comme congé pour ces dates
    current_date = conge.date_debut
    while current_date <= conge.date_fin:
        # Enregistrer ou modifier le pointage de présence
        Presence.objects.update_or_create(
            personnel=conge.personnel,
            date=current_date,
            defaults={'statut': 'CONGE', 'heure_arrivee': None, 'heure_depart': None}
        )
        current_date += timedelta(days=1)
        
    messages.success(request, f"La demande de congé de {conge.personnel.prenom} a été approuvée.")
    return redirect('grh:conge_list')

@login_required
def conge_reject(request, pk):
    ecole = get_user_ecole(request)
    conge = get_object_or_404(Conge, pk=pk, personnel__ecole=ecole)
    conge.statut = 'REJETE'
    conge.save()
    messages.warning(request, f"La demande de congé de {conge.personnel.prenom} a été rejetée.")
    return redirect('grh:conge_list')

# --- Présences ---
@login_required
def presence_list(request):
    ecole = get_user_ecole(request)
    today = date.today()
    date_str = request.GET.get('date', str(today))
    try:
        filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        filter_date = today

    presences = list(
        presences_for_ecole(ecole)
        .filter(date=filter_date)
        .select_related('personnel')
        .order_by('personnel__nom', 'personnel__Post_nom', 'personnel__prenom')
    )
    pointing_ids = [p.personnel_id for p in presences]
    personnel_a_arriver = (
        personnel_for_ecole(ecole)
        .exclude(id__in=pointing_ids)
        .order_by('nom', 'Post_nom', 'prenom')
    )
    presences_a_partir = [p for p in presences if p.en_attente_depart]
    now_time = timezone.localtime().strftime('%H:%M')

    context = {
        'presences': presences,
        'personnel_a_arriver': personnel_a_arriver,
        'presences_a_partir': presences_a_partir,
        'filter_date': filter_date,
        'now_time': now_time,
        'etape': request.GET.get('etape', 'arrivee'),
    }
    return render(request, 'grh/presence_list.html', context)


@login_required
def presence_record(request):
    ecole = get_user_ecole(request)
    if request.method != 'POST':
        return redirect('grh:presence_list')

    etape = (request.POST.get('etape') or 'arrivee').strip().lower()
    personnel_id = request.POST.get('personnel')
    date_str = request.POST.get('date') or str(date.today())
    redirect_url = f"{reverse('grh:presence_list')}?date={date_str}&etape={etape}"

    try:
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Date invalide.")
        return redirect('grh:presence_list')

    personnel = get_object_or_404(Personnel, id=personnel_id, ecole=ecole)
    presence, _ = Presence.objects.get_or_create(
        personnel=personnel,
        date=record_date,
        defaults={'statut': 'PRESENT'},
    )

    if etape == 'depart':
        if presence.statut in ('ABSENT', 'CONGE'):
            messages.warning(
                request,
                f"{personnel.prenom} est marqué {presence.get_statut_display()} — pas de départ à pointer.",
            )
            return redirect(f"{reverse('grh:presence_list')}?date={date_str}&etape=depart")
        if not presence.heure_arrivee:
            messages.error(
                request,
                f"Pointer d'abord l'arrivée de {personnel.prenom} avant le départ.",
            )
            return redirect(f"{reverse('grh:presence_list')}?date={date_str}&etape=arrivee")

        heure_dep = (request.POST.get('heure_depart') or '').strip()
        if not heure_dep:
            heure_dep = timezone.localtime().strftime('%H:%M')
        try:
            presence.heure_depart = datetime.strptime(heure_dep, "%H:%M").time()
        except ValueError:
            messages.error(request, "Heure de départ invalide.")
            return redirect(redirect_url)
        if presence.heure_arrivee and presence.heure_depart < presence.heure_arrivee:
            messages.error(request, "L'heure de départ doit être après l'arrivée.")
            return redirect(redirect_url)
        presence.save(update_fields=['heure_depart'])
        messages.success(
            request,
            f"Départ enregistré pour {personnel.prenom} à {presence.heure_depart.strftime('%H:%M')}.",
        )
        return redirect(f"{reverse('grh:presence_list')}?date={date_str}&etape=depart")

    # Étape arrivée
    statut = request.POST.get('statut') or 'PRESENT'
    if statut not in dict(Presence.STATUT_CHOICES):
        statut = 'PRESENT'

    if presence.heure_arrivee and presence.statut in ('PRESENT', 'RETARD'):
        messages.info(
            request,
            f"Arrivée déjà pointée pour {personnel.prenom} ({presence.heure_arrivee.strftime('%H:%M')}).",
        )
        return redirect(f"{reverse('grh:presence_list')}?date={date_str}&etape=depart")

    presence.statut = statut
    if statut in ('ABSENT', 'CONGE'):
        presence.heure_arrivee = None
        presence.heure_depart = None
        presence.save(update_fields=['statut', 'heure_arrivee', 'heure_depart'])
        messages.success(
            request,
            f"{personnel.prenom} marqué {presence.get_statut_display()} le {record_date:%d/%m/%Y}.",
        )
        return redirect(f"{reverse('grh:presence_list')}?date={date_str}&etape=arrivee")

    heure_arr = (request.POST.get('heure_arrivee') or '').strip()
    if not heure_arr:
        heure_arr = timezone.localtime().strftime('%H:%M')
    try:
        presence.heure_arrivee = datetime.strptime(heure_arr, "%H:%M").time()
    except ValueError:
        messages.error(request, "Heure d'arrivée invalide.")
        return redirect(redirect_url)
    # Ne pas effacer un départ déjà saisi
    presence.save(update_fields=['statut', 'heure_arrivee'])
    messages.success(
        request,
        f"Arrivée enregistrée pour {personnel.prenom} à {presence.heure_arrivee.strftime('%H:%M')}.",
    )
    return redirect(f"{reverse('grh:presence_list')}?date={date_str}&etape=depart")

# --- Paie ---
@login_required
def paie_list(request):
    ecole = get_user_ecole(request)
    paies = (
        paies_for_ecole(ecole)
        .select_related('personnel', 'devise')
        .order_by('-annee', '-mois', 'personnel__nom', '-id')
    )
    today = date.today()
    contrats_actifs_count = contrats_for_ecole(ecole).filter(statut='ACTIF').count()
    return render(request, 'grh/paie_list.html', {
        'paies': paies,
        'ecole': ecole,
        'contrats_actifs_count': contrats_actifs_count,
        'mois_courant': today.month,
        'annee_courante': today.year,
    })

@login_required
def paie_generate(request):
    ecole = get_user_ecole(request)
    if request.method != 'POST':
        return redirect('grh:paie_list')

    if not ecole:
        messages.error(
            request,
            "Aucune école n'est associée à votre compte. Impossible de générer les fiches de paie.",
        )
        return redirect('grh:paie_list')

    try:
        mois = int(request.POST.get('mois') or 0)
        annee = int(request.POST.get('annee') or 0)
    except (TypeError, ValueError):
        messages.error(request, "Mois ou année invalide.")
        return redirect('grh:paie_list')

    if mois < 1 or mois > 12 or annee < 2000:
        messages.error(request, "Veuillez choisir un mois et une année valides.")
        return redirect('grh:paie_list')

    # Un contrat actif par agent (le plus récent) pour éviter les doublons
    contrats_actifs = (
        contrats_for_ecole(ecole)
        .filter(statut='ACTIF')
        .select_related('personnel', 'devise')
        .order_by('personnel_id', '-date_debut', '-id')
    )
    if not contrats_actifs.exists():
        messages.warning(
            request,
            "Aucun contrat ACTIF trouvé pour votre école. "
            "Créez d'abord des contrats dans GRH → Contrats, puis relancez la génération.",
        )
        return redirect('grh:contrat_list')

    vus = set()
    generes = 0
    deja_existants = 0
    erreurs = 0

    for contrat in contrats_actifs:
        if contrat.personnel_id in vus:
            continue
        vus.add(contrat.personnel_id)

        if not contrat.devise_id:
            erreurs += 1
            messages.error(
                request,
                f"Le contrat de {contrat.personnel.prenom} {contrat.personnel.nom} n'a pas de devise.",
            )
            continue

        paie_existante = paies_for_ecole(ecole).filter(
            personnel=contrat.personnel, mois=mois, annee=annee
        ).exists()
        if paie_existante:
            deja_existants += 1
            continue

        try:
            Paie.objects.create(
                personnel=contrat.personnel,
                mois=mois,
                annee=annee,
                salaire_base=contrat.salaire_base or Decimal("0.00"),
                primes=Decimal("0.00"),
                deductions=Decimal("0.00"),
                devise=contrat.devise,
                statut_paiement='EN_ATTENTE',
            )
            generes += 1
        except Exception as exc:
            erreurs += 1
            messages.error(
                request,
                f"Erreur pour {contrat.personnel.prenom} {contrat.personnel.nom} : {exc}",
            )

    if generes > 0:
        messages.success(
            request,
            f"{generes} fiche(s) de paie générée(s) pour {mois:02d}/{annee}.",
        )
    if deja_existants > 0:
        messages.info(
            request,
            f"{deja_existants} fiche(s) existaient déjà pour {mois:02d}/{annee}.",
        )
    if generes == 0 and deja_existants == 0 and erreurs == 0:
        messages.warning(request, "Aucune fiche de paie n'a pu être générée.")

    return redirect('grh:paie_list')

@login_required
def paie_detail(request, pk):
    ecole = get_user_ecole(request)
    paie = get_object_or_404(Paie, pk=pk, personnel__ecole=ecole)
    # Calculer le nombre de jours de présence pour ce mois (approximatif)
    absences = Presence.objects.filter(personnel=paie.personnel, date__month=paie.mois, date__year=paie.annee, statut='ABSENT').count()
    presences = Presence.objects.filter(personnel=paie.personnel, date__month=paie.mois, date__year=paie.annee, statut__in=['PRESENT', 'RETARD']).count()

    from finances.paiement_utils import verifier_depense_contre_caisse

    # Formulaire rapide pour éditer les primes et déductions
    if request.method == 'POST':
        old_statut = paie.statut_paiement
        form = PaieForm(request.POST, instance=paie, ecole=ecole)
        if form.is_valid():
            nouveau_statut = form.cleaned_data.get('statut_paiement')
            if old_statut != 'PAYE' and nouveau_statut == 'PAYE':
                devise_code = str(paie.devise.devise) if paie.devise_id else ""
                ok_caisse, msg_caisse, _ = verifier_depense_contre_caisse(
                    ecole,
                    form.cleaned_data.get('net_a_payer') or paie.net_a_payer,
                    devise_code,
                    form.cleaned_data.get('mode_paiement') or paie.mode_paiement or "ESPECES",
                )
                if not ok_caisse:
                    messages.error(request, msg_caisse)
                    return redirect('grh:paie_detail', pk=pk)
            updated = form.save()
            if old_statut != 'PAYE' and updated.statut_paiement == 'PAYE':
                from finances.views import _hoada_auto_post_salary_to_entries
                try:
                    ok = _hoada_auto_post_salary_to_entries(updated)
                    if not ok:
                        messages.warning(
                            request,
                            "Statut PAYÉ enregistré, mais l'écriture comptable n'a pas pu être créée.",
                        )
                except Exception as exc:
                    messages.warning(request, f"Statut PAYÉ enregistré, erreur comptable : {exc}")
            messages.success(request, "Montants de la paie mis à jour.")
            return redirect('grh:paie_detail', pk=pk)
    else:
        form = PaieForm(instance=paie, ecole=ecole)

    devise_code = str(paie.devise.devise) if paie.devise_id else ""
    ok_caisse, msg_caisse, dispo_caisse = verifier_depense_contre_caisse(
        ecole, paie.net_a_payer, devise_code, paie.mode_paiement or "ESPECES"
    )

    context = {
        'paie': paie,
        'absences': absences,
        'presences': presences,
        'form': form,
        'caisse_ok': ok_caisse,
        'caisse_message': msg_caisse,
        'caisse_disponible': dispo_caisse,
    }
    return render(request, 'grh/paie_detail.html', context)

@login_required
def paie_pay(request, pk):
    ecole = get_user_ecole(request)
    paie = get_object_or_404(Paie, pk=pk, personnel__ecole=ecole)
    if request.method != 'POST':
        return redirect('grh:paie_detail', pk=pk)
    from finances.views import marquer_paie_payee
    result = marquer_paie_payee(paie)
    if result['payee'] and result['ecriture_ok']:
        messages.success(
            request,
            f"La fiche de paie de {paie.personnel.prenom} a été payée et comptabilisée.",
        )
    elif result['payee']:
        messages.warning(
            request,
            result['erreur']
            or "Paiement enregistré, mais l'écriture comptable n'a pas pu être créée.",
        )
    elif result['erreur']:
        messages.error(request, result['erreur'])
    else:
        messages.info(request, "Cette fiche était déjà payée.")
    return redirect('grh:paie_detail', pk=pk)
