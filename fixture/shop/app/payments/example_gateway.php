<?php
// SYNTHETIC FIXTURE. Stands in for a payment processor script.
function lab_charge(array $cart, $total)
{
    return array('status' => 'test-only', 'amount' => $total);
}
