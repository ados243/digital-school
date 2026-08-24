"""Fil d'Ariane (breadcrumbs) pour toutes les pages de l'application."""

from django.urls import NoReverseMatch, reverse


# Racine de chaque module (label, url_name)
MODULE_ROOTS = {
    'grh': ('Ressources Humaines', 'grh:dashboard'),
    'inscription': ('Inscriptions & Élèves', 'inscription:dashboard'),
    'pedagogie': ('Pédagogie & Classes', 'pedagogie:dashboard'),
    'finances': ('Finances & Paiements', 'finances:dashboard'),
}

# Libellés des vues (namespace:url_name)
PAGE_LABELS = {
    # GRH
    'grh:dashboard': 'Synthèse',
    'grh:personnel_list': 'Personnel',
    'grh:personnel_create': 'Nouveau personnel',
    'grh:personnel_update': 'Modifier',
    'grh:personnel_delete': 'Supprimer',
    'grh:contrat_list': 'Contrats',
    'grh:contrat_create': 'Nouveau contrat',
    'grh:contrat_update': 'Modifier le contrat',
    'grh:conge_list': 'Congés',
    'grh:conge_create': 'Demande de congé',
    'grh:conge_approve': 'Approuver',
    'grh:conge_reject': 'Rejeter',
    'grh:presence_list': 'Présences',
    'grh:presence_record': 'Pointer',
    'grh:paie_list': 'Rémunération',
    'grh:paie_generate': 'Générer les paies',
    'grh:paie_detail': 'Bulletin de paie',
    # Inscription
    'inscription:dashboard': 'Synthèse',
    'inscription:eleve_list': 'Fiches élèves',
    'inscription:eleve_create': 'Nouvel élève',
    'inscription:eleve_update': 'Modifier l\'élève',
    'inscription:eleve_delete': 'Supprimer l\'élève',
    'inscription:tuteur_list': 'Tuteurs',
    'inscription:tuteur_create': 'Nouveau tuteur',
    'inscription:tuteur_update': 'Modifier le tuteur',
    'inscription:quartier_create': 'Nouveau quartier',
    'inscription:inscription_list': 'Inscriptions',
    'inscription:inscription_create': 'Inscrire',
    'inscription:inscription_update': 'Modifier l\'inscription',
    'inscription:classe_list': 'Classes & salles',
    'inscription:classe_create': 'Nouvelle classe',
    'inscription:classe_detail': 'Détail classe',
    'inscription:classe_update': 'Modifier la classe',
    'inscription:classe_delete': 'Supprimer la classe',
    # Pédagogie
    'pedagogie:dashboard': 'Synthèse',
    'pedagogie:matiere_list': 'Matières',
    'pedagogie:matiere_create': 'Nouvelle matière',
    'pedagogie:matiere_update': 'Modifier la matière',
    'pedagogie:matiere_delete': 'Supprimer la matière',
    'pedagogie:periodes_bulletin': 'Périodes bulletin',
    'pedagogie:affectations_classe': 'Enseignants de la classe',
    'pedagogie:emploi_du_temps': 'Emploi du temps',
    'pedagogie:emploi_du_temps_classe': 'Emploi du temps',
    'pedagogie:creneau_delete': 'Supprimer un créneau',
    # Finances
    'finances:dashboard': 'Synthèse',
    'finances:type_frais_list': 'Types de frais',
    'finances:type_frais_create': 'Nouveau type de frais',
    'finances:type_frais_update': 'Modifier le type',
    'finances:type_frais_delete': 'Supprimer le type',
    'finances:frais_scolaire_list': 'Frais scolaires',
    'finances:frais_scolaire_create': 'Nouveau frais',
    'finances:frais_scolaire_update': 'Modifier le frais',
    'finances:frais_scolaire_delete': 'Supprimer le frais',
    'finances:paiement_list': 'Paiements élèves',
    'finances:paiement_create': 'Encaisser un paiement',
    'finances:caisse_confirmer_mobile': 'Confirmer Mobile Money',
    'finances:paiement_update': 'Corriger le paiement',
    'finances:paiement_delete': 'Supprimer le paiement',
    'finances:paiement_print': 'Imprimer le reçu',
    'finances:classe_paiements': 'Paiements par classe',
    'finances:cloture_caisse': 'Clôture de journée',
    'finances:relances_impayes': 'Relances minerval',
    'finances:relances_impayes_envoyer': 'Envoyer les relances',
    'finances:budget_annuel': 'Suivi du budget',
    'finances:demandes_modification_list': 'Demandes de correction',
    'finances:demande_modification_create': 'Demander une correction',
    'finances:demande_modification_rejeter': 'Rejeter la demande',
    'finances:taux_change_list': 'Taux de change',
    'finances:whatsapp_config': 'WhatsApp central',
    'finances:whatsapp_test': 'Test WhatsApp',
    'finances:whatsapp_renvoyer': 'Renvoyer WhatsApp',
    'finances:salaires_list': 'Payer le personnel',
    'finances:salaire_payer': 'Payer un salaire',
    'finances:salaires_payer_lot': 'Payer la sélection',
    'finances:hoada_plan_comptable': 'Plan comptable',
    'finances:hoada_plan_comptable_create': 'Nouveau compte',
    'finances:hoada_journaux_list': 'Journaux',
    'finances:hoada_journaux_create': 'Nouveau journal',
    'finances:hoada_ecritures_list': 'Écritures',
    'finances:hoada_ecritures_create': 'Nouvelle écriture',
    'finances:hoada_grand_livre': 'Grand livre',
    'finances:hoada_balance': 'Balance',
    'finances:inscriptions_non_paye': 'Inscriptions non payées',
    # Direction / utilisateur back-office
    'utilisateur:direction_communication_list': 'Communications parents',
    'utilisateur:direction_communication_create': 'Nouvelle communication',
    'utilisateur:direction_communication_detail': 'Détail communication',
    'utilisateur:direction_communication_update': 'Modifier la communication',
    # Portail
    'utilisateur:portail': 'Mon espace',
    'utilisateur:profil': 'Mon profil',
    'utilisateur:password_reset': 'Mot de passe oublié',
    'utilisateur:password_reset_done': 'Code WhatsApp',
    'utilisateur:password_reset_confirm': 'Nouveau mot de passe',
    'utilisateur:password_reset_complete': 'Mot de passe mis à jour',
    'utilisateur:parent_enfant': 'Fiche enfant',
    'utilisateur:parent_payer_mobile': 'Payer par Mobile Money',
    'utilisateur:parent_annonces': 'Annonces',
    'utilisateur:parent_annonce_detail': 'Détail annonce',
    'utilisateur:enseignant_dashboard': 'Mes classes',
    'utilisateur:enseignant_classe': 'Classe',
    'utilisateur:travail_list': 'Travaux',
    'utilisateur:travail_create': 'Nouveau travail',
    'utilisateur:travail_update': 'Modifier le travail',
    'utilisateur:travail_delete': 'Supprimer le travail',
    'utilisateur:travail_notes': 'Notes',
    'utilisateur:cours_enseignant_list': 'Cours en ligne',
    'utilisateur:cours_enseignant_create': 'Nouveau cours',
    'utilisateur:cours_enseignant_detail': 'Détail du cours',
    'utilisateur:cours_enseignant_update': 'Modifier le cours',
    'utilisateur:cours_enseignant_delete': 'Supprimer le cours',
    'utilisateur:chapitre_enseignant_detail': 'Chapitre',
    'utilisateur:chapitre_enseignant_update': 'Modifier le chapitre',
    'utilisateur:chapitre_enseignant_delete': 'Supprimer le chapitre',
    'utilisateur:lecon_enseignant_update': 'Modifier la leçon',
    'utilisateur:lecon_enseignant_delete': 'Supprimer la leçon',
    'utilisateur:cours_eleve_list': 'Étudier en ligne',
    'utilisateur:cours_eleve_detail': 'Cours',
    'utilisateur:chapitre_eleve_detail': 'Chapitre',
    'utilisateur:lecon_eleve_detail': 'Leçon',
    'utilisateur:direct_enseignant_list': 'Cours en ligne',
    'utilisateur:direct_enseignant_create': 'Nouveau cours (visio)',
    'utilisateur:direct_enseignant_update': 'Modifier le cours',
    'utilisateur:direct_enseignant_salle': 'Salle de visioconférence',
    'utilisateur:direct_eleve_list': 'Cours en ligne',
    'utilisateur:direct_eleve_salle': 'Salle de visioconférence',
    'utilisateur:ressource_enseignant_list': 'Ressources',
    'utilisateur:ressource_enseignant_create': 'Partager un fichier',
    'utilisateur:ressource_enseignant_update': 'Modifier la ressource',
    'utilisateur:ressource_enseignant_delete': 'Supprimer la ressource',
    'utilisateur:ressource_eleve_list': 'Ressources',
    'utilisateur:ressource_eleve_detail': 'Ressource',
    'utilisateur:bulletin_classe': 'Bulletins',
    'utilisateur:evolution_classe': 'Évolution des élèves',
    'utilisateur:bulletin_eleve': 'Bulletin élève',
    'utilisateur:presence_list': 'Présences',
    'utilisateur:presence_classe': 'Appel de classe',
    'utilisateur:presence_recap': 'Récapitulatif',
    'utilisateur:messagerie_inbox': 'Messages',
    'utilisateur:messagerie_detail': 'Conversation',
    'utilisateur:messagerie_nouveau_parent': 'Nouveau message',
    'utilisateur:messagerie_nouveau_enseignant': 'Nouveau message',
}

# Parent liste pour les écrans détail / formulaire (namespace:url_name → parent)
PAGE_PARENTS = {
    'grh:personnel_create': 'grh:personnel_list',
    'grh:personnel_update': 'grh:personnel_list',
    'grh:personnel_delete': 'grh:personnel_list',
    'grh:contrat_create': 'grh:contrat_list',
    'grh:contrat_update': 'grh:contrat_list',
    'grh:conge_create': 'grh:conge_list',
    'grh:conge_approve': 'grh:conge_list',
    'grh:conge_reject': 'grh:conge_list',
    'grh:presence_record': 'grh:presence_list',
    'grh:paie_generate': 'grh:paie_list',
    'grh:paie_detail': 'grh:paie_list',
    'inscription:eleve_create': 'inscription:eleve_list',
    'inscription:eleve_update': 'inscription:eleve_list',
    'inscription:eleve_delete': 'inscription:eleve_list',
    'inscription:tuteur_create': 'inscription:tuteur_list',
    'inscription:tuteur_update': 'inscription:tuteur_list',
    'inscription:inscription_create': 'inscription:inscription_list',
    'inscription:inscription_update': 'inscription:inscription_list',
    'inscription:classe_create': 'inscription:classe_list',
    'inscription:classe_detail': 'inscription:classe_list',
    'inscription:classe_update': 'inscription:classe_list',
    'inscription:classe_delete': 'inscription:classe_list',
    'pedagogie:matiere_create': 'pedagogie:matiere_list',
    'pedagogie:matiere_update': 'pedagogie:matiere_list',
    'pedagogie:matiere_delete': 'pedagogie:matiere_list',
    'pedagogie:affectations_classe': 'inscription:classe_list',
    'pedagogie:emploi_du_temps_classe': 'pedagogie:emploi_du_temps',
    'pedagogie:creneau_delete': 'pedagogie:emploi_du_temps',
    'finances:type_frais_create': 'finances:type_frais_list',
    'finances:type_frais_update': 'finances:type_frais_list',
    'finances:type_frais_delete': 'finances:type_frais_list',
    'finances:frais_scolaire_create': 'finances:frais_scolaire_list',
    'finances:frais_scolaire_update': 'finances:frais_scolaire_list',
    'finances:frais_scolaire_delete': 'finances:frais_scolaire_list',
    'finances:paiement_create': 'finances:paiement_list',
    'finances:caisse_confirmer_mobile': 'finances:paiement_list',
    'finances:paiement_update': 'finances:demandes_modification_list',
    'finances:paiement_delete': 'finances:paiement_list',
    'finances:paiement_print': 'finances:paiement_list',
    'finances:classe_paiements': 'finances:paiement_list',
    'finances:cloture_caisse': 'finances:paiement_list',
    'finances:relances_impayes_envoyer': 'finances:relances_impayes',
    'finances:budget_annuel': 'finances:dashboard',
    'finances:demande_modification_create': 'finances:paiement_list',
    'finances:demande_modification_rejeter': 'finances:demandes_modification_list',
    'finances:whatsapp_test': 'finances:whatsapp_config',
    'finances:whatsapp_renvoyer': 'finances:whatsapp_config',
    'finances:salaire_payer': 'finances:salaires_list',
    'finances:salaires_payer_lot': 'finances:salaires_list',
    'finances:hoada_plan_comptable_create': 'finances:hoada_plan_comptable',
    'finances:hoada_journaux_create': 'finances:hoada_journaux_list',
    'finances:hoada_ecritures_create': 'finances:hoada_ecritures_list',
    'utilisateur:direction_communication_create': 'utilisateur:direction_communication_list',
    'utilisateur:direction_communication_detail': 'utilisateur:direction_communication_list',
    'utilisateur:direction_communication_update': 'utilisateur:direction_communication_list',
    'utilisateur:parent_enfant': 'utilisateur:portail',
    'utilisateur:parent_payer_mobile': 'utilisateur:parent_enfant',
    'utilisateur:profil': 'utilisateur:portail',
    'utilisateur:password_reset_done': 'utilisateur:password_reset',
    'utilisateur:password_reset_confirm': 'utilisateur:password_reset',
    'utilisateur:password_reset_complete': 'utilisateur:login',
    'utilisateur:parent_annonce_detail': 'utilisateur:parent_annonces',
    'utilisateur:enseignant_classe': 'utilisateur:enseignant_dashboard',
    'utilisateur:travail_create': 'utilisateur:travail_list',
    'utilisateur:travail_update': 'utilisateur:travail_list',
    'utilisateur:travail_delete': 'utilisateur:travail_list',
    'utilisateur:travail_notes': 'utilisateur:travail_list',
    'utilisateur:cours_enseignant_create': 'utilisateur:cours_enseignant_list',
    'utilisateur:cours_enseignant_detail': 'utilisateur:cours_enseignant_list',
    'utilisateur:cours_enseignant_update': 'utilisateur:cours_enseignant_list',
    'utilisateur:cours_enseignant_delete': 'utilisateur:cours_enseignant_list',
    'utilisateur:chapitre_enseignant_detail': 'utilisateur:cours_enseignant_list',
    'utilisateur:chapitre_enseignant_update': 'utilisateur:cours_enseignant_list',
    'utilisateur:chapitre_enseignant_delete': 'utilisateur:cours_enseignant_list',
    'utilisateur:lecon_enseignant_update': 'utilisateur:cours_enseignant_list',
    'utilisateur:lecon_enseignant_delete': 'utilisateur:cours_enseignant_list',
    'utilisateur:cours_eleve_detail': 'utilisateur:cours_eleve_list',
    'utilisateur:chapitre_eleve_detail': 'utilisateur:cours_eleve_list',
    'utilisateur:lecon_eleve_detail': 'utilisateur:cours_eleve_list',
    'utilisateur:direct_enseignant_create': 'utilisateur:direct_enseignant_list',
    'utilisateur:direct_enseignant_update': 'utilisateur:direct_enseignant_list',
    'utilisateur:direct_enseignant_salle': 'utilisateur:direct_enseignant_list',
    'utilisateur:direct_eleve_salle': 'utilisateur:direct_eleve_list',
    'utilisateur:ressource_enseignant_create': 'utilisateur:ressource_enseignant_list',
    'utilisateur:ressource_enseignant_update': 'utilisateur:ressource_enseignant_list',
    'utilisateur:ressource_enseignant_delete': 'utilisateur:ressource_enseignant_list',
    'utilisateur:ressource_eleve_detail': 'utilisateur:ressource_eleve_list',
    'utilisateur:bulletin_classe': 'utilisateur:enseignant_dashboard',
    'utilisateur:bulletin_eleve': 'utilisateur:enseignant_dashboard',
    'utilisateur:evolution_classe': 'utilisateur:enseignant_classe',
    'utilisateur:presence_classe': 'utilisateur:presence_list',
    'utilisateur:presence_recap': 'utilisateur:presence_list',
    'utilisateur:messagerie_detail': 'utilisateur:messagerie_inbox',
    'utilisateur:messagerie_nouveau_parent': 'utilisateur:messagerie_inbox',
    'utilisateur:messagerie_nouveau_enseignant': 'utilisateur:messagerie_inbox',
}

SKIP_URL_NAMES = {
    'login', 'logout', 'inscription', 'post_login', 'root',
}


def _safe_reverse(name, kwargs=None):
    try:
        return reverse(name, kwargs=kwargs or None)
    except NoReverseMatch:
        try:
            return reverse(name)
        except NoReverseMatch:
            return None


def _humanize(url_name):
    return (url_name or 'Page').replace('_', ' ').capitalize()


def _home_crumb(user):
    if not user.is_authenticated:
        return {'label': 'Accueil', 'url': _safe_reverse('utilisateur:login')}
    if getattr(user, 'is_caissier', False) and not user.is_superuser:
        return {'label': 'Paiements', 'url': _safe_reverse('finances:paiement_list')}
    if getattr(user, 'is_professeur', False) and not user.is_superuser:
        return {'label': 'Mes classes', 'url': _safe_reverse('utilisateur:enseignant_dashboard')}
    if getattr(user, 'is_parent', False) or getattr(user, 'is_eleve', False):
        return {'label': 'Mon espace', 'url': _safe_reverse('utilisateur:portail')}
    if getattr(user, 'is_directeur_etudes', False) and not user.is_superuser:
        return {'label': 'Accueil', 'url': _safe_reverse('pedagogie:dashboard')}
    if getattr(user, 'is_secretaire', False) and not user.is_superuser:
        return {'label': 'Accueil', 'url': _safe_reverse('inscription:dashboard')}
    if getattr(user, 'is_prefet', False) and not user.is_superuser:
        return {'label': 'Accueil', 'url': _safe_reverse('grh:dashboard')}
    return {'label': 'Accueil', 'url': _safe_reverse('finances:dashboard')}


def _label_for(key, url_name):
    return PAGE_LABELS.get(key) or _humanize(url_name)


def build_breadcrumbs(request):
    """Construit la liste [{label, url|None}, ...] pour la page courante."""
    match = getattr(request, 'resolver_match', None)
    if not match or not match.url_name:
        return []
    if match.url_name in SKIP_URL_NAMES:
        return []

    user = getattr(request, 'user', None)
    crumbs = []
    home = _home_crumb(user)
    if home.get('url'):
        crumbs.append(home)

    ns = match.namespace or ''
    name = match.url_name
    key = f'{ns}:{name}' if ns else name
    path = request.path or ''

    # Module racine (back-office)
    if ns in MODULE_ROOTS:
        mod_label, mod_url = MODULE_ROOTS[ns]
        # Évite Accueil > GRH > Synthèse redondant sur le dashboard GRH si home = GRH
        if not (home.get('url') and home['url'] == _safe_reverse(mod_url) and name == 'dashboard'):
            if name == 'dashboard':
                crumbs.append({'label': mod_label, 'url': None})
            else:
                crumbs.append({'label': mod_label, 'url': _safe_reverse(mod_url)})

    # Direction communications (hors namespace inscription mais sidebar inscription)
    if ns == 'utilisateur' and path.startswith('/direction/'):
        crumbs.append({
            'label': 'Inscriptions & Élèves',
            'url': _safe_reverse('inscription:dashboard'),
        })

    # Portail enseignant / parent : segment intermédiaire
    if ns == 'utilisateur' and path.startswith('/mon-espace/'):
        if getattr(user, 'is_professeur', False) and name != 'enseignant_dashboard':
            if home.get('url') != _safe_reverse('utilisateur:enseignant_dashboard'):
                crumbs.append({
                    'label': 'Espace enseignant',
                    'url': _safe_reverse('utilisateur:enseignant_dashboard'),
                })
        elif (getattr(user, 'is_parent', False) or getattr(user, 'is_eleve', False)) and name != 'portail':
            if home.get('url') != _safe_reverse('utilisateur:portail'):
                crumbs.append({
                    'label': 'Mon espace',
                    'url': _safe_reverse('utilisateur:portail'),
                })

    # Parent liste (ex. Paiements avant Modifier)
    parent_key = PAGE_PARENTS.get(key)
    if parent_key:
        parent_label = _label_for(parent_key, parent_key.split(':')[-1])
        crumbs.append({'label': parent_label, 'url': _safe_reverse(parent_key)})

    # Page courante (sans lien)
    current_label = _label_for(key, name)
    # Ne pas dupliquer si déjà le dernier crumb (dashboard module = label module)
    if not crumbs or crumbs[-1]['label'] != current_label or crumbs[-1].get('url'):
        # Sur dashboard module, le dernier crumb est déjà le module
        if not (ns in MODULE_ROOTS and name == 'dashboard' and crumbs and crumbs[-1]['label'] == MODULE_ROOTS[ns][0]):
            crumbs.append({'label': current_label, 'url': None})

    # Dédupliquer liens consécutifs identiques
    cleaned = []
    for crumb in crumbs:
        if cleaned and cleaned[-1].get('url') and cleaned[-1].get('url') == crumb.get('url') and cleaned[-1]['label'] == crumb['label']:
            continue
        cleaned.append(crumb)

    # Au moins 2 niveaux pour être utile ; sinon rien
    if len(cleaned) < 2:
        return cleaned
    return cleaned


def breadcrumbs(request):
    """Context processor."""
    try:
        return {'breadcrumbs': build_breadcrumbs(request)}
    except Exception:
        return {'breadcrumbs': []}
