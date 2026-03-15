document.addEventListener("DOMContentLoaded", () => {
  let draggedTask = null;

  document.querySelectorAll(".task-block[draggable='true']").forEach((task) => {
    task.addEventListener("dragstart", () => {
      draggedTask = {
        week: task.dataset.week,
        fromDay: task.dataset.day,
        taskId: task.dataset.taskId,
      };
      task.classList.add("dragging");
    });

    task.addEventListener("dragend", () => {
      task.classList.remove("dragging");
    });
  });

  document.querySelectorAll(".day-body").forEach((column) => {
    column.addEventListener("dragover", (event) => {
      event.preventDefault();
      column.classList.add("drop-target");
    });

    column.addEventListener("dragleave", () => {
      column.classList.remove("drop-target");
    });

    column.addEventListener("drop", async (event) => {
      event.preventDefault();
      column.classList.remove("drop-target");

      if (!draggedTask) {
        return;
      }

      const toDay = column.dataset.day;
      if (draggedTask.fromDay === toDay) {
        return;
      }

      const body = new URLSearchParams({
        week: draggedTask.week,
        from_day: draggedTask.fromDay,
        to_day: toDay,
        task_id: draggedTask.taskId,
      });

      await fetch("/move", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: body.toString(),
      });

      window.location.search = `?week=${encodeURIComponent(draggedTask.week)}`;
    });
  });
});
