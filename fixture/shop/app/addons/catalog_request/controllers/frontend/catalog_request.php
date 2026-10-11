<?php
// SYNTHETIC FIXTURE. Receives the catalog request form and queues an email.
// It never touches carts, orders, prices or payments.
if ($mode === 'send' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    lab_queue_mail('catalog_request', $_REQUEST['request']);
}
