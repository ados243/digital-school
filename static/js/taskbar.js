(function () {
    var bar = document.getElementById('app-taskbar');
    if (!bar) return;

    function menus() {
        return bar.querySelectorAll('.ds-taskbar-app--menu');
    }

    function closeAll(except) {
        menus().forEach(function (app) {
            if (app === except) return;
            app.classList.remove('is-open');
            var btn = app.querySelector('.ds-taskbar-app__btn');
            if (btn) btn.setAttribute('aria-expanded', 'false');
        });
    }

    bar.addEventListener('click', function (e) {
        var btn = e.target.closest('.ds-taskbar-app--menu > .ds-taskbar-app__btn');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        var app = btn.parentElement;
        var willOpen = !app.classList.contains('is-open');
        closeAll(app);
        app.classList.toggle('is-open', willOpen);
        btn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    });

    document.addEventListener('click', function (e) {
        if (!e.target.closest('.ds-taskbar-app--menu')) closeAll();
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeAll();
    });
})();
