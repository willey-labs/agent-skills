---
max_turns: 10
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob, Grep, Write]
model: opus
runs: 3
plugins: [../..]
tags: [negative]
---
Turn these meeting notes into an action-item list and save it as `actions.md`.

Mobile app weekly sync, Tuesday. Priya, Marcus, Dana, Leo.

- Android 14 crash rate is up to 1.8% since 3.2.0. Marcus thinks it's the new image cache. Marcus to bisect between 3.1.4 and 3.2.0 and report back by Thursday.
- App Store rejected 3.2.1 because the privacy label doesn't mention crash reporting. Dana will update the label and resubmit, by Friday.
- Decided: we stay on React Native 0.74 until after the holiday freeze. No upgrade work this quarter.
- Priya demoed the new onboarding flow, everyone liked it. Leo to write the analytics event spec for the new screens before design hands off on the 21st.
- The Apple developer certificate expires on 30 Oct and someone needs to renew it before then. Nobody took it.
- Marcus says the CI runners are slow again. General agreement it's annoying, nothing decided.
- Priya will send the onboarding prototype link to the support team today.
- Next sync moves to Wednesday because of the offsite.
