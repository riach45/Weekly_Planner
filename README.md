# Weekly Planner

Small beginner-friendly weekly planner built with plain Python.

## What it does

- Shows one week at a time from Monday to Sunday
- Uses a 7-column calendar-style layout
- Lets you add a task to a selected day
- Lets you add an optional time
- Lets you move between weeks
- Lets you edit a task inline
- Sorts tasks automatically by time inside each day
- Lets you drag tasks to another day in the current week
- Lets you mark a task as done
- Lets you delete a task
- Saves everything in `data/tasks.json`

## Files

- `app.py`:
  Runs the local web server and handles loading, saving, week navigation, adding, editing, completing, and deleting tasks.
- `templates/index.html`:
  The main web page layout, including the week navigation buttons and the quick-add form.
- `static/style.css`:
  The calendar styling, grid lines, colors, spacing, input bar design, and task edit styles.
- `static/app.js`:
  Handles drag and drop so you can move a task block to another day column.
- `data/tasks.json`:
  Your local task data file grouped by week.

## Tech stack

- Python standard library only
- HTML
- CSS
- JSON

## Data format

The app now stores tasks by week.

- `next_id`:
  Keeps the next task id number.
- `weeks`:
  Contains one entry per week.
- Each week key:
  Is the Monday date for that week, for example `2026-03-09`.
- Inside each week:
  There are seven day lists: Monday to Sunday.
- Each task:
  Has `id`, `text`, `time`, and `completed`.

## Run on Windows

1. Open PowerShell.
2. Go to the project folder:
   `cd C:\Users\riach\Codex\project1`
3. Start the app:
   `python app.py`
4. Open this address in your browser:
   `http://127.0.0.1:8000`
5. To stop the app, press `Ctrl + C`



