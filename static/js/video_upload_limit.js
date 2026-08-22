/**
 * Bloque l'upload d'une vidéo qui dépasse data-max-mb (défini côté formulaire).
 */
(function () {
  function maxBytes(input) {
    var mb = parseInt(input.getAttribute('data-max-mb') || '70', 10);
    if (!mb || mb < 1) mb = 70;
    return mb * 1024 * 1024;
  }

  function checkInput(input) {
    var file = input.files && input.files[0];
    if (!file) return true;
    var limit = maxBytes(input);
    var maxMb = Math.round(limit / (1024 * 1024));
    if (file.size > limit) {
      var sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      var label = input.hasAttribute('data-file-limit') && !input.hasAttribute('data-video-limit')
        ? 'Fichier trop volumineux'
        : 'Vidéo trop volumineuse';
      window.alert(
        label + ' (' + sizeMb + ' Mo).\n' +
        'Taille maximale autorisée : ' + maxMb + ' Mo.'
      );
      input.value = '';
      return false;
    }
    return true;
  }

  function onChange(e) {
    var input = e.target;
    if (!input || !input.matches || !input.matches('input[type="file"][data-video-limit], input[type="file"][data-file-limit]')) {
      return;
    }
    checkInput(input);
  }

  function onSubmit(e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM') return;
    var inputs = form.querySelectorAll('input[type="file"][data-video-limit], input[type="file"][data-file-limit]');
    for (var i = 0; i < inputs.length; i++) {
      if (!checkInput(inputs[i])) {
        e.preventDefault();
        e.stopPropagation();
        return false;
      }
    }
  }

  document.addEventListener('change', onChange, true);
  document.addEventListener('submit', onSubmit, true);
})();
