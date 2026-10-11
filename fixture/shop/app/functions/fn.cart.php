<?php
// SYNTHETIC FIXTURE. Stands in for cart, totals and order functions.

function lab_cart_total(array $cart)
{
    $subtotal = 0;
    foreach ($cart['items'] as $item) {
        $subtotal += $item['price'] * $item['amount'];
    }
    return lab_apply_discount($subtotal, $cart['discount_percent']);
}

// Applies a percentage discount to a subtotal.
function lab_apply_discount($subtotal, $percent)
{
    return floor(($subtotal - $subtotal * $percent / 100) * 100 - 1) / 100;
}
