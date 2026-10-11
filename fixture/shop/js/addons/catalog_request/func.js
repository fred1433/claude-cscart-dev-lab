/* Catalog request form checks. SYNTHETIC FIXTURE written for this lab. */
(function () {
    'use strict';
    var form = document.querySelector('form[name="catalog_request_form"]');
    if (!form) {
        return;
    }
    form.addEventListener('submit', function (event) {
        var zip = form.querySelector('#cr_zip');
        // Accepts 5-digit or ZIP+4 codes.
        if (zip && !/^\d{5}(-\d{4})?$/.test(zip.value.trim())) {
            event.preventDefault();
            zip.focus();
        }
    });
})();
