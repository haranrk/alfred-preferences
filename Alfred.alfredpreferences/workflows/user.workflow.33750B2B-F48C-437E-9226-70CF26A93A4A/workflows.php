<?php

class Workflow
{

    private $results = [];

    public function result($uid, $arg, $title, $sub)
    {
        $this->results[] = [
            'uid' => $uid,
            'arg' => $arg,
            'title' => $title,
            'subtitle' => $sub
        ];
    }

    public function end()
    {
        $items = new SimpleXMLElement("<items></items>");
        foreach ($this->results as $result) {
            $c = $items->addChild('item');
            $c->addAttribute('valid', 'yes');
            foreach (array_keys($result) as $key) {
                if ($key == 'uid') {
                    $c->addAttribute('uid', $result[$key]);
                } elseif ($key == 'arg') {
                    $c->addAttribute('arg', $result[$key]);
                } else {
                    $c->$key = $result[$key];
                }
            }
        }

        echo $items->asXML();
    }

}
