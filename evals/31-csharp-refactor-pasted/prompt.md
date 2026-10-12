---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [csharp, refactor, csharp]
---
Here's our late-fee calculator. Finance wants a cap: the fee must never be more than a percentage of the invoice amount. The percentage depends on the customer's contract, so the caller passes it in (`10` means 10%). Apply the cap after the VIP discount and the minimum fee; when the cap is below the minimum fee, the cap wins. Save the result as `Billing/LateFeeCalculator.cs`.

```csharp
using System;

namespace Billing
{
    public class LateFeeCalculator
    {
        private readonly decimal m_decDailyRate = 0.001m;
        private readonly int m_intGraceDays = 3;

        // calculate the late fee for an invoice
        public dynamic Calculate(string strInvoiceId, decimal decAmount, DateTime dtDue, DateTime dtPaid, bool bIsVip, decimal decMinFee)
        {
            decimal decFee = 0;
            int intDaysLate = 0;
            try
            {
                // days late after the grace period
                intDaysLate = (dtPaid.Date - dtDue.Date).Days - m_intGraceDays;
                if (intDaysLate > 0)
                {
                    decFee = decAmount * m_decDailyRate * intDaysLate;
                    // VIPs pay half
                    if (bIsVip)
                    {
                        decFee = decFee / 2;
                    }
                    if (decFee < decMinFee)
                    {
                        decFee = decMinFee;
                    }
                }
            }
            catch (Exception)
            {
            }
            return new { InvoiceId = strInvoiceId, DaysLate = Math.Max(intDaysLate, 0), Fee = Math.Round(decFee, 2) };
        }
    }
}
```
