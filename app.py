import json
from datetime import date, datetime, timedelta
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "tasks.json"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TASK_COLORS = ["peach", "mint", "sky", "sand", "rose"]


def empty_week():
    return {day: [] for day in DAYS}


def current_monday():
    today = date.today()
    return today - timedelta(days=today.weekday())


def format_week_key(week_start):
    return week_start.isoformat()


def parse_week_key(value):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return current_monday()
    return parsed - timedelta(days=parsed.weekday())


def ensure_data_file():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        return

    initial_data = {
        "next_id": 1,
        "weeks": {
            format_week_key(current_monday()): empty_week(),
        },
    }
    DATA_FILE.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")


def normalize_old_data(raw_data):
    if "weeks" in raw_data and "next_id" in raw_data:
        return raw_data

    migrated_week = empty_week()
    highest_id = 0

    for day in DAYS:
        for item in raw_data.get(day, []):
            task_id = str(item.get("id", highest_id + 1))
            highest_id = max(highest_id, int(task_id))
            migrated_week[day].append(
                {
                    "id": task_id,
                    "text": item.get("text", "").strip(),
                    "time": item.get("time", ""),
                    "completed": bool(item.get("completed", False)),
                }
            )

    return {
        "next_id": highest_id + 1,
        "weeks": {
            format_week_key(current_monday()): migrated_week,
        },
    }


def load_data():
    ensure_data_file()
    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    normalized = normalize_old_data(raw_data)
    if normalized != raw_data:
        save_data(normalized)
    return normalized


def save_data(data):
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def get_week_dates(week_start):
    return {day: week_start + timedelta(days=index) for index, day in enumerate(DAYS)}


def get_week_tasks(data, week_key):
    weeks = data.setdefault("weeks", {})
    if week_key not in weeks:
        weeks[week_key] = empty_week()
    return weeks[week_key]


def sort_tasks(tasks):
    def sort_key(task):
        time_value = task.get("time", "").strip()
        has_time = 0 if time_value else 1
        return (has_time, time_value, int(task["id"]))

    tasks.sort(key=sort_key)


def build_query(params):
    clean_params = {key: value for key, value in params.items() if value}
    if not clean_params:
        return ""
    return "?" + urlencode(clean_params)


def build_navigation_url(week_key, edit_day="", edit_task_id=""):
    return "/" + build_query(
        {
            "week": week_key,
            "edit_day": edit_day,
            "edit_task_id": edit_task_id,
        }
    )


def render_task_view(task, day_name, week_key, color_class):
    task_id = escape(task["id"])
    task_text = escape(task["text"])
    safe_day_name = escape(day_name)
    time_html = f'<div class="task-time">{escape(task["time"])}</div>' if task.get("time") else ""

    return f"""
    <article
      class="task-block {color_class} {'done' if task['completed'] else ''}"
      draggable="true"
      data-week="{escape(week_key)}"
      data-day="{safe_day_name}"
      data-task-id="{task_id}"
    >
      {time_html}
      <div class="task-title">{task_text}</div>
      <div class="task-actions">
        <form method="post" action="/toggle" class="inline-form">
          <input type="hidden" name="week" value="{escape(week_key)}">
          <input type="hidden" name="day" value="{safe_day_name}">
          <input type="hidden" name="task_id" value="{task_id}">
          <button type="submit" class="action-button">{'Undo' if task['completed'] else 'Done'}</button>
        </form>
        <a class="action-button" href="{build_navigation_url(week_key, day_name, task['id'])}">Edit</a>
        <form method="post" action="/delete" class="inline-form">
          <input type="hidden" name="week" value="{escape(week_key)}">
          <input type="hidden" name="day" value="{safe_day_name}">
          <input type="hidden" name="task_id" value="{task_id}">
          <button type="submit" class="action-button delete-action">Delete</button>
        </form>
      </div>
    </article>
    """


def render_task_edit(task, day_name, week_key, color_class):
    task_id = escape(task["id"])
    safe_day_name = escape(day_name)
    return f"""
    <article class="task-block {color_class} editing">
      <form method="post" action="/edit" class="edit-form">
        <input type="hidden" name="week" value="{escape(week_key)}">
        <input type="hidden" name="day" value="{safe_day_name}">
        <input type="hidden" name="task_id" value="{task_id}">
        <label class="sr-only" for="edit-text-{task_id}">Task text</label>
        <input id="edit-text-{task_id}" type="text" name="text" value="{escape(task['text'])}" maxlength="120" required>
        <label class="sr-only" for="edit-time-{task_id}">Task time</label>
        <input id="edit-time-{task_id}" type="time" name="time" value="{escape(task.get('time', ''))}">
        <div class="task-actions">
          <button type="submit" class="action-button primary-action">Save</button>
          <a class="action-button" href="{build_navigation_url(week_key)}">Cancel</a>
        </div>
      </form>
    </article>
    """


def build_day_html(day_name, day_date, tasks, week_key, edit_day, edit_task_id):
    safe_day_name = escape(day_name)
    day_number = day_date.strftime("%d")
    short_month = day_date.strftime("%b")
    items_html = []

    for index, task in enumerate(tasks):
        color_class = TASK_COLORS[index % len(TASK_COLORS)]
        if day_name == edit_day and task["id"] == edit_task_id:
            items_html.append(render_task_edit(task, day_name, week_key, color_class))
        else:
            items_html.append(render_task_view(task, day_name, week_key, color_class))

    return f"""
    <section class="day-column">
      <header class="day-header">
        <div class="day-name">{safe_day_name}</div>
        <div class="day-date">{escape(day_number)} <span>{escape(short_month)}</span></div>
      </header>
      <div class="day-body" data-day="{safe_day_name}" data-week="{escape(week_key)}">
        <div class="day-grid-lines" aria-hidden="true"></div>
        <div class="task-stack">
          {''.join(items_html)}
        </div>
      </div>
    </section>
    """


def build_day_options():
    return "".join(f'<option value="{escape(day)}">{escape(day)}</option>' for day in DAYS)


def build_page(query):
    week_start = parse_week_key(query.get("week", [format_week_key(current_monday())])[0])
    week_key = format_week_key(week_start)
    data = load_data()
    week_tasks = get_week_tasks(data, week_key)
    for day in DAYS:
        sort_tasks(week_tasks[day])
    save_data(data)

    week_dates = get_week_dates(week_start)
    sunday = week_dates["Sunday"]
    edit_day = query.get("edit_day", [""])[0]
    edit_task_id = query.get("edit_task_id", [""])[0]
    planner_html = "".join(
        build_day_html(day, week_dates[day], week_tasks.get(day, []), week_key, edit_day, edit_task_id)
        for day in DAYS
    )

    previous_week = format_week_key(week_start - timedelta(days=7))
    next_week = format_week_key(week_start + timedelta(days=7))
    this_week = format_week_key(current_monday())

    template = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    return template.format(
        month_label=escape(week_start.strftime("%B %Y")),
        week_range=escape(f"{week_start.strftime('%d %b')} - {sunday.strftime('%d %b %Y')}"),
        planner_html=planner_html,
        day_options=build_day_options(),
        week_key=escape(week_key),
        previous_week_url=build_navigation_url(previous_week),
        next_week_url=build_navigation_url(next_week),
        today_url=build_navigation_url(this_week),
    ).encode("utf-8")


def read_form_data(handler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length).decode("utf-8")
    form_data = parse_qs(raw_body)
    return {key: values[0] for key, values in form_data.items()}


def redirect_url(week_key):
    return build_navigation_url(week_key)


def next_task_id(data):
    task_id = str(data.get("next_id", 1))
    data["next_id"] = int(task_id) + 1
    return task_id


def add_task(week_key, day, text, time_value):
    if day not in DAYS or not text.strip():
        return

    data = load_data()
    week_tasks = get_week_tasks(data, week_key)
    week_tasks[day].append(
        {
            "id": next_task_id(data),
            "text": text.strip(),
            "time": time_value.strip(),
            "completed": False,
        }
    )
    sort_tasks(week_tasks[day])
    save_data(data)


def find_task(tasks, task_id):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def toggle_task(week_key, day, task_id):
    data = load_data()
    week_tasks = get_week_tasks(data, week_key)
    task = find_task(week_tasks.get(day, []), task_id)
    if task:
        task["completed"] = not task["completed"]
        save_data(data)


def delete_task(week_key, day, task_id):
    data = load_data()
    week_tasks = get_week_tasks(data, week_key)
    week_tasks[day] = [task for task in week_tasks.get(day, []) if task["id"] != task_id]
    save_data(data)


def edit_task(week_key, day, task_id, text, time_value):
    if day not in DAYS or not text.strip():
        return

    data = load_data()
    week_tasks = get_week_tasks(data, week_key)
    task = find_task(week_tasks.get(day, []), task_id)
    if task:
        task["text"] = text.strip()
        task["time"] = time_value.strip()
        sort_tasks(week_tasks[day])
        save_data(data)


def move_task(week_key, from_day, to_day, task_id):
    if from_day not in DAYS or to_day not in DAYS:
        return

    data = load_data()
    week_tasks = get_week_tasks(data, week_key)
    source_tasks = week_tasks.get(from_day, [])
    task = find_task(source_tasks, task_id)
    if not task:
        return

    week_tasks[from_day] = [item for item in source_tasks if item["id"] != task_id]
    week_tasks[to_day].append(task)
    sort_tasks(week_tasks[to_day])
    save_data(data)


class PlannerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            page = build_page(parse_qs(parsed.query))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        if parsed.path == "/static/style.css":
            css = (BASE_DIR / "static" / "style.css").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Content-Length", str(len(css)))
            self.end_headers()
            self.wfile.write(css)
            return

        if parsed.path == "/static/app.js":
            script = (BASE_DIR / "static" / "app.js").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(script)))
            self.end_headers()
            self.wfile.write(script)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        form_data = read_form_data(self)
        week_key = form_data.get("week", format_week_key(current_monday()))

        if self.path == "/add":
            add_task(week_key, form_data.get("day", ""), form_data.get("text", ""), form_data.get("time", ""))
        elif self.path == "/toggle":
            toggle_task(week_key, form_data.get("day", ""), form_data.get("task_id", ""))
        elif self.path == "/delete":
            delete_task(week_key, form_data.get("day", ""), form_data.get("task_id", ""))
        elif self.path == "/edit":
            edit_task(
                week_key,
                form_data.get("day", ""),
                form_data.get("task_id", ""),
                form_data.get("text", ""),
                form_data.get("time", ""),
            )
        elif self.path == "/move":
            move_task(
                week_key,
                form_data.get("from_day", ""),
                form_data.get("to_day", ""),
                form_data.get("task_id", ""),
            )
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", redirect_url(week_key))
        self.end_headers()

    def log_message(self, format, *args):
        return


def run():
    ensure_data_file()
    server = HTTPServer(("127.0.0.1", 8000), PlannerHandler)
    print("Weekly planner running at http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
