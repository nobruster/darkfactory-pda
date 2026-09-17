# NO-GO — meeting-notes auto-formatter (calendar-impossible parking date)

<!-- The v0.4.0 seam: 2026-02-31 passes the ISO shape regex (month 02, day
     31) but February has no 31st. The python3 datetime check must FAIL this
     record; everything else here is a valid no-go. -->

**Date:** 2026-02-31
**Owner:** VP of Engineering
**The idea:** auto-format our meeting notes into the wiki template.
**Why it didn't clear:** the do-nothing answer, verbatim — "nothing, really;
formatting takes two minutes and nobody has complained."
**What would reopen it:** note volume grows past 20/week, or a downstream
consumer actually depends on the formatting.
