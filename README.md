# Magnus dealer CRM

## Put it on Render

1. Create a new empty GitHub repo named magnus-crm.
2. Upload this folder (not the zip wrapper) so app.py is at the repo root.
3. In Render: New > Blueprint, or New > Web Service, and connect that repo.
4. If you use Web Service instead of the blueprint:
   - Runtime: Python
   - Build: pip install -r requirements.txt
   - Start: gunicorn app:app --bind 0.0.0.0:$PORT
5. Deploy. The first boot loads Companies, Activity, Reminders, and Prospects from data/.

The free disk resets on some Render plans. For a CRM you will keep editing, add a Render disk mounted at /var/data and set DATABASE_PATH=/var/data/crm.db.

## What this app does

- Lists active dealers, buy groups, big box, and distributors, quietest first.
- Shows overdue callbacks from the spreadsheet.
- Lets you log a call, email, or Wispr note. A name that is not already a company is saved as a prospect.

## What it does not do yet

Outlook and CIN7 are not called from this app. Those stay in Prime Bolt until you add API keys as Render environment variables and a scheduled job. Do not commit keys.
