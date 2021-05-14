<?php

// Load workflows helper
require_once('workflows.php');
$workflow = new Workflow();

// Parse timestamp (default to current time)
date_default_timezone_set('UTC');
$time = time();
if (!empty($query)) {
    $r = [
        'bedtime' => '10pm',
        'morning' => '7am',
        'last night' => 'yesterday 9pm',
        'tonight' => 'today 9pm',
        'night' => '9pm',
        'afternoon' => '3pm',
        'last week' => '-1 week',
        'next week' => '+1 week'
    ];
    if (is_numeric($query) && $query > 10000) {
        $time = intval($query);
    } else {
        $query = str_replace(array_keys($r), array_values($r), $query);
        $time = strtotime($query);
        if (!$time) {
            exit;
        }
    }
}

// Add unix and epoch timestamps
$v = $time;
$workflow->result('time.seconds' . rand(), $v, $v, 'Unix timestamp (s)');
$v = $time * 1000;
$workflow->result('time.miliseconds' . rand(), $v, $v, 'Epoch timestamp (ms)');

// UTC date formats
date_default_timezone_set('UTC');
$v = date('d-m-Y H:i:s', $time);
$workflow->result('time.simple' . rand(), $v, $v, 'Simple date (UTC)');
$v = str_replace('+00:00', 'Z', date('c', $time));
$workflow->result('time.iso8601' . rand(), $v, $v, 'ISO 8601 (UTC)');

// London date formats
date_default_timezone_set('Europe/London');
$v = date('d-m-Y H:i:s', $time);
$workflow->result('time.simple' . rand(), $v, $v, 'Simple date (London)');
$v = date('c', $time);
$workflow->result('time.iso8601' . rand(), $v, $v, 'ISO 8601 (London)');

// Output XML
$workflow->end();
