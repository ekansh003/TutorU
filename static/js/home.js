document.addEventListener("DOMContentLoaded", function () {
  const completeButtons = document.querySelectorAll(".complete-task");

  completeButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const scheduleId = this.dataset.scheduleId;
      const taskType = this.dataset.taskType;
      const taskItem = this.closest(".task-item");

      fetch("/mark_task_completed", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          schedule_id: scheduleId,
          task_type: taskType,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            taskItem.classList.add("task-completing");
            button.disabled = true;

            setTimeout(() => {
              taskItem.remove();

              const remainingTasks = document.querySelectorAll(".task-item");

              if (remainingTasks.length === 0) {
                const queue = document.querySelector(".learning-queue");

                if (queue) {
                  queue.innerHTML = `
                    <div class="tasks-empty">
                      <div class="tasks-empty-mark">✓</div>

                      <div>
                        <h3>You're all caught up.</h3>

                        <p>
                          No incomplete tasks for today.
                          Come back tomorrow to continue learning.
                        </p>
                      </div>
                    </div>
                  `;
                }
              }
            }, 300);
          } else {
            alert("Failed to mark task as completed. Please try again.");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("An error occurred. Please try again.");
        });
    });
  });
});
