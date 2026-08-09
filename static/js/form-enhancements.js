(function () {
    function markFilledFields(root) {
        root.querySelectorAll('input, select, textarea').forEach(function (el) {
            var update = function () {
                if (el.type === 'checkbox' || el.type === 'radio') {
                    el.classList.toggle('is-checked', el.checked);
                } else {
                    el.classList.toggle('is-filled', Boolean(el.value && String(el.value).trim()));
                }
            };
            update();
            el.addEventListener('input', update);
            el.addEventListener('change', update);
        });
    }

    function scrollToFirstError() {
        var target = document.querySelector('.form-errors-banner, .form-field--invalid');
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('form').forEach(markFilledFields);
        scrollToFirstError();
    });
})();
