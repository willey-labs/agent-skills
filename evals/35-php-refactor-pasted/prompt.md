---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [php, refactor, none]
---
Here's our shipping rate calculator. Add an oversize surcharge: a parcel with any side longer than 120 cm costs 8.00 more, added before the express multiplier. The parcel data now also has `length_cm`, `width_cm` and `height_cm`. The `FREESHIP` coupon still makes domestic shipping free, surcharge included. Save the result as `src/Shipping/RateCalculator.php`.

```php
<?php

namespace App\Shipping;

class RateCalculator
{
    private array $arrZoneRates = ['domestic' => 4.50, 'eu' => 9.00, 'world' => 15.00];

    // calculate the shipping price for a parcel
    public function calculate(mixed $parcel, string $strZone, bool $bExpress, string $strCoupon = ''): float
    {
        $fltPrice = 0.0;
        try {
            $fltWeight = (float) $parcel['weight_kg'];
            var_dump($fltWeight);

            // start from the zone price
            $fltPrice = $this->arrZoneRates[$strZone];

            // every started kg over 2 kg costs 1.25
            if ($fltWeight > 2) {
                $fltPrice += ceil($fltWeight - 2) * 1.25;
            }

            if ($bExpress) {
                $fltPrice *= 1.5;
            }

            if ($strCoupon === 'FREESHIP' && $strZone === 'domestic') {
                $fltPrice = 0.0;
            }
        } catch (\Throwable $e) {
        }

        return round($fltPrice, 2);
    }
}
```
