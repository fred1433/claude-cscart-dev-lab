<?php
// SYNTHETIC FIXTURE. Stands in for the storefront checkout controller.
if ($mode === 'place_order') {
    $cart = lab_get_cart();
    $total = lab_cart_total($cart);
    lab_charge($cart, $total);
}
