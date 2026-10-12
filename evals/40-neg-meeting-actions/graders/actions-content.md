---
type: llm
focus:
  source: file
  path: actions.md
---
The user pasted meeting notes and asked for an action-item list. The notes hold exactly five action items:

- Marcus: bisect the Android 14 crash between 3.1.4 and 3.2.0 and report back, by Thursday.
- Dana: update the App Store privacy label and resubmit 3.2.1, by Friday.
- Leo: write the analytics event spec for the new onboarding screens, before the 21st.
- No owner: renew the Apple developer certificate before it expires on 30 Oct.
- Priya: send the onboarding prototype link to the support team, today.

PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. All five items appear.
2. Each item names the owner given above, and the certificate renewal is marked unassigned or as needing an owner rather than given to a named person.
3. Each item carries the deadline given above, in any wording.
4. Nothing else appears as an action item: staying on React Native 0.74, the slow CI runners and the next sync moving to Wednesday are not listed as tasks. A separate section noting decisions or other points is fine.
