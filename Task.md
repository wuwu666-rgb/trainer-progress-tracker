# Repbook Team Task Checklist

[Update task progress in the GitHub Issue](https://github.com/wuwu666-rgb/trainer-progress-tracker/issues/1). This file records the checklist at publication.

Owners follow the Project Plan. Checked items are available in the shared starter.

## 0. Shared starter · Shi Wei Wu Wu (setup and delivery)

- [x] **0.1** Set up the Flask and SQLite app for local development.
- [x] **0.2** Separate clients, planning, recording, and history into modules with a shared page layout.
- [x] **0.3** Apply the Repbook name, English interface, and purple theme.
- [x] **0.4** Verify the demo workflow: select a client, save one set, and find it in history.
- [x] **0.5** Push the starter to GitHub main and document local setup and module ownership.

- [ ] **0.6** Agree on the shared database schema and API contracts for profiles, plans, sessions, and set results. Define how to migrate or reset the starter demo database. **Owners:** all four team members.

## 1–3. Accounts, client profiles, and permissions · Giorgi Nebieridze

- [ ] **1.1** Implement trainer and client registration, role storage, and password hashing.
- [ ] **1.2** Implement login and route users to their role-specific home page.
- [ ] **1.3** Implement logout.
- [x] **2.1** Display a client list with a preloaded sample client.
- [ ] **2.2** Let trainers create profiles with a required name and optional training goals.
- [ ] **2.3** Let trainers edit their own client profiles while preserving workout history.
- [ ] **3.1** Let trainers invite clients using their registered email addresses.
- [ ] **3.2** Let clients accept or decline invitations and enforce one trainer per client.
- [ ] **3.3** Enforce server-side permissions for profiles, plans, and records.

- [ ] **3.4** Enforce unique email addresses, validate registration, and return clear errors for duplicate accounts or invalid credentials.
- [ ] **3.5** Protect signed-in requests with session cookies and CSRF checks. Test that guessing a client or workout ID does not grant access.

## 4–5. Workout templates and assignments · Shi Wei Wu Wu

- [x] **4.1** Add the Workout plans navigation link and landing page.
- [ ] **4.2** Build a template list and creation form with a name, exercises, target sets, and target reps.
- [ ] **4.3** Let trainers edit their own templates, including exercise order and targets.
- [ ] **5.1** Create a workout plan from a template and preserve assigned plans when the template changes.
- [ ] **5.2** Let trainers create a workout plan from scratch for a client.
- [ ] **5.3** Let trainers assign a plan to a selected client.
- [ ] **5.4** Let clients sign in and view their assigned plans.

- [ ] **5.5** Validate plan and template names, at least one named exercise, and positive whole-number target sets and reps. Keep custom plans separate from reusable templates.

## 6–7. Workout recording, past entries, and corrections · Salman Doria

- [x] **6.1** Open the recorder from the sample client and enter actual reps and weight for one set.
- [x] **6.2** Validate the date, exercise, reps, and weight, and save valid records to SQLite.
- [ ] **6.3** Support multiple exercises and sets in one workout.
- [ ] **6.4** Let trainers start a coached workout from a plan or start a blank workout and add exercises.
- [ ] **6.5** Let clients start an assigned workout, record results, and complete the session.
- [ ] **6.6** Show planned exercises in order with their target sets and reps. Store actual results separately and restrict recording to the designated trainer or client.
- [ ] **6.7** Require at least one valid set to complete a workout. Keep the original plan unchanged, make the completed workout available in history, and prevent duplicate records on save retry.
- [x] **7.1** Allow a single set to be entered for a past date.
- [ ] **7.2** Let trainers enter a full past workout with multiple exercises and sets.
- [ ] **7.3** Let the original recorder correct the date, exercises, reps, and weight of a saved workout.

- [ ] **7.4** Validate full workout entries and corrections on the server. Reject future dates and invalid set values while preserving previously saved results after a failed update.

## 8–10. Workout history, body weight, and deployment · Yusuf Doria

- [x] **8.1** Show the sample client's saved sets by date with exercise, reps, and weight.
- [ ] **8.2** Group history by workout and show each exercise and set in the detail view.
- [ ] **8.3** Enforce access permissions when trainers and linked clients view history.
- [ ] **9.1** Let trainers record one body-weight measurement per client per day.
- [ ] **9.2** Let trainers correct the date and value of a client's measurement.
- [ ] **9.3** Let trainers and linked clients view dated body-weight history.
- [ ] **9.4** Validate positive body weight, reject future dates, and prevent duplicate dates when adding or correcting measurements.
- [ ] **10.1** Deploy to a shared HTTPS address and verify that saved data survives a restart.
- [ ] **10.2** Test login, plan assignment, recording, and history on iPhone Safari and Android Chrome. **Participants: Giorgi Nebieridze, Shi Wei Wu Wu, Salman Doria, and Yusuf Doria.**

- [ ] **10.3** Verify phone readability without zooming or horizontal scrolling, and test that saved online records remain available after reopening the app. **Owners:** all four team members.
- [ ] **10.4** Prepare demo accounts and sample data, update launch instructions, and rehearse the trainer-to-client workflow. **Owners:** all four team members.

## Deferred for this release · Yusuf Doria (original Project Plan owner)

- Record and save workout results offline.
- Restore an unfinished offline workout after closing the page.
- Sync results after reconnecting and prevent duplicate uploads.

## Beyond the MVP

- **F8 · Progress comparison:** Compare exercise results across workouts and show body-weight trends.
- **F9 · History search and filters:** Find workouts by exercise and date range.
