{** Checkout customer info step. SYNTHETIC FIXTURE written for this lab. **}
<div class="ty-checkout-customer">
    <div class="ty-control-group">
        <label for="ck_email" class="ty-control-group__title cm-required">{__("email")}</label>
        <input id="ck_email" type="email" name="user_data[email]" class="ty-input-text" />
    </div>
    {hook name="checkout:customer_info_bottom"}{/hook}
</div>
