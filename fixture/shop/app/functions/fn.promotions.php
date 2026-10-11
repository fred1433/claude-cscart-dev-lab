<?php
// SYNTHETIC FIXTURE. Stands in for promotion and coupon rules.
function lab_coupon_is_valid($code)
{
    return in_array(strtoupper($code), array('WELCOME10'), true);
}
