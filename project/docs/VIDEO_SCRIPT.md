# 3-minute video script (hard limit: 3:00)

**0:00 to 0:15, title card (must show all five):** project title (Poltergeist), your name, your GitHub and edX usernames, your city and country, the date you recorded the video. Hold it for about 10 seconds.

**0:15 to 0:40, the problem (screen: demo_flawed.py and its passing test)**
"This pipeline passes its tests. Watch what happens when real-world dirty data shows up." Run `python demos/test_demo_flawed.py` and show `OK`.

**0:40 to 1:20, the haunting (screen: web app, flawed demo)**
Open the app, pick `demo_flawed.py`, click Haunt it. Let the rows surface. "Poltergeist corrupted the data 17 ways and ran the pipeline each time. 53% of the corruptions produced wrong output with no error."

**1:20 to 1:50, one example in detail (screen: expand a row)**
Expand `date_ambiguity`: "04/05/2026 became 5 April, silently." Then `null_spellings`: "Missing amounts became zero."

**1:50 to 2:25, the fix (screen: demo_hardened.py, then Compare)**
"After validating, normalising and quarantining bad rows the rate is 0%." Run the hardened demo, open History, Compare the two runs: show fixed rows in green.

**2:25 to 2:50, how it works (screen: file tree)**
"Mutators corrupt a clean CSV with a seeded random generator. The pipeline runs in a sandboxed subprocess. A judge compares each output to the clean run. Results go into SQLite."

**2:50 to 3:00, close**
"Poltergeist: find the bugs that fail silently." Show the repo URL.

Tips: record at 1080p, zoom the browser to 125%, rehearse once so you finish near 2:50, upload to YouTube as Unlisted (not Private), then put the URL in README.md.
