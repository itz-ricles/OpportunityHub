# Manual test checklist (browsers and screen sizes)

Automated tests cover logic, permissions and HTML structure. They cannot see layout, so do this by hand
and record results in the table at the bottom.

## Setup
Run `flask --app app run --debug`. Create an admin with `flask --app app create-admin` and a student through the sign-up page.
To test on a real phone: run `flask --app app run --host 0.0.0.0`, then open `http://<your-laptop-IP>:5000` on a phone
on the same Wi-Fi (allow Python through the firewall; stop the server afterwards).

## Screen widths (Chrome DevTools > device toolbar)
320, 375 (iPhone), 412 (Android), 768 (tablet), 1024 (laptop), 1440 (desktop).

For EACH width and EACH page (home, login, register, opportunities, details, dashboard, saved, tracker, account, admin, admin form, students):
- [ ] No horizontal scrolling of the whole page (tables may scroll inside their own box)
- [ ] Menu button works at phone widths; all links reachable
- [ ] Text is readable without zooming; buttons are easy to tap (about 44px tall)
- [ ] Cards stack to 1 column on phones, 2 on tablets, 3-4 on desktop
- [ ] Filter form and hero search bar don't overflow

## Keyboard and accessibility
- [ ] Tab through every page: order is logical, focus ring always visible
- [ ] "Skip to content" appears on first Tab press
- [ ] Forms can be completed and submitted with the keyboard only
- [ ] Zoom to 200%: nothing is cut off
- [ ] Run Lighthouse (DevTools) Accessibility on home, opportunities and tracker: aim for 90+

## Browsers
Latest Chrome, Firefox, Edge, Safari/iPhone Safari, Chrome on Android.
- [ ] Fonts load (DM Sans), date picker works on the admin form, confirm dialog appears when deleting

## Workflow spot-checks (two browsers: one student, one admin in a private window)
- [ ] Register, log in, search, filter, save, track, change status, log out
- [ ] Admin: add draft, publish, edit, deactivate, delete; student view updates accordingly
- [ ] Student visiting /admin sees "Access denied"
- [ ] Back button after logout does not show private pages

## Results log
| Date | Browser / device | Width | Pages checked | Issues found | Fixed? |
|---|---|---|---|---|---|
