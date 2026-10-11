{** Catalog request form. SYNTHETIC FIXTURE written for this lab, not CS-Cart code. **}
<div class="ty-catalog-request">
    <h3 class="ty-catalog-request__title">{__("catalog_request.title")}</h3>
    <p class="ty-catalog-request__intro">{__("catalog_request.intro")}</p>
    <form action="{""|fn_url}" method="post" name="catalog_request_form" class="ty-catalog-request__form">
        <input type="hidden" name="dispatch" value="catalog_request.send" />
        <div class="ty-catalog-request__row">
            <div class="ty-control-group ty-catalog-request__field">
                <label for="cr_name" class="ty-control-group__title cm-required">{__("catalog_request.name")}</label>
                <input id="cr_name" type="text" name="request[name]" class="ty-input-text" />
            </div>
            <div class="ty-control-group ty-catalog-request__field">
                <label for="cr_company" class="ty-control-group__title">{__("catalog_request.company")}</label>
                <input id="cr_company" type="text" name="request[company]" class="ty-input-text" />
            </div>
            <div class="ty-control-group ty-catalog-request__field">
                <label for="cr_email" class="ty-control-group__title cm-required">{__("catalog_request.email")}</label>
                <input id="cr_email" type="email" name="request[email]" class="ty-input-text" />
            </div>
        </div>
        <div class="ty-catalog-request__row">
            <div class="ty-control-group ty-catalog-request__field ty-catalog-request__field--wide">
                <label for="cr_address" class="ty-control-group__title cm-required">{__("catalog_request.address")}</label>
                <input id="cr_address" type="text" name="request[address]" class="ty-input-text" />
            </div>
            <div class="ty-control-group ty-catalog-request__field">
                <label for="cr_zip" class="ty-control-group__title cm-required">{__("catalog_request.zip")}</label>
                <input id="cr_zip" type="text" name="request[zip]" class="ty-input-text" />
            </div>
        </div>
        <fieldset class="ty-catalog-request__choices">
            <legend class="ty-control-group__title">{__("catalog_request.interests")}</legend>
            <label><input type="checkbox" name="request[interests][]" value="print" /> {__("catalog_request.printed_catalog")}</label>
            <label><input type="checkbox" name="request[interests][]" value="flyer" /> {__("catalog_request.seasonal_flyer")}</label>
            <label><input type="checkbox" name="request[interests][]" value="samples" /> {__("catalog_request.sample_pack")}</label>
        </fieldset>
        {hook name="catalog_request:form_bottom"}{/hook}
        <div class="ty-catalog-request__buttons">
            <button class="ty-btn ty-btn__primary" type="submit">{__("catalog_request.send")}</button>
        </div>
    </form>
</div>
