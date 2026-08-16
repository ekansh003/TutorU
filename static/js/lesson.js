document.addEventListener("DOMContentLoaded", function () {
  const chatContainer = document.getElementById("chatContainer");
  const questionInput = document.getElementById("questionInput");
  const askButton = document.getElementById("askButton");
  const lessonContent = document.getElementById("lessonContent");

  /* =========================================================
     Reading Time
     ========================================================= */

  if (lessonContent) {
    const text = lessonContent.textContent;
    const wordCount = text.trim().split(/\s+/).length;
    const readingTime = Math.max(1, Math.ceil(wordCount / 200));

    const readingTimeElement = document.getElementById("readingTime");

    if (readingTimeElement) {
      readingTimeElement.textContent = `${readingTime} min`;
    }
  }

  /* =========================================================
     Ask AI
     ========================================================= */

  function askQuestion() {
    const question = questionInput.value.trim();

    if (!question) return;

    addMessage("user", question);

    questionInput.value = "";

    addMessage(
      "assistant",
      `
        <div class="ai-thinking">
          <span></span>
          <span></span>
          <span></span>
        </div>
      `,
      true,
    );

    const lessonContentElement = document.getElementById("lessonContent");

    const rawContent = lessonContentElement
      ? lessonContentElement.textContent || lessonContentElement.innerText
      : "";

    fetch("/ask_question", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        question: question,
        course_name: window.TUTORU_COURSE_NAME,
        chapter_title: window.TUTORU_CHAPTER_TITLE,
        lesson_title: window.TUTORU_LESSON_TITLE,
        content: rawContent,
      }),
    })
      .then((response) => response.json())

      .then((data) => {
        const loadingMessages = chatContainer.querySelectorAll(".loading");

        loadingMessages.forEach((message) => {
          message.remove();
        });

        if (data.success) {
          addMessage(
            "assistant",
            formatAssistantResponse(data.answer, data.citation),
          );
        } else {
          addMessage(
            "assistant",
            `
              <p>
                Sorry, I couldn't process your question.
              </p>

              <p class="chat-error">
                ${data.error || "Unknown error"}
              </p>
            `,
          );
        }
      })

      .catch((error) => {
        console.error("Error:", error);

        const loadingMessages = chatContainer.querySelectorAll(".loading");

        loadingMessages.forEach((message) => {
          message.remove();
        });

        addMessage(
          "assistant",
          `
            <p>
              I couldn't connect right now.
              Please check your connection and try again.
            </p>
          `,
        );
      });
  }

  /* =========================================================
     Format AI Response
     ========================================================= */

  function formatAssistantResponse(content, citation) {
    let formatted = content
      .replace(/### (.*?)(?=\n|$)/g, "<h4>$1</h4>")
      .replace(/## (.*?)(?=\n|$)/g, "<h3>$1</h3>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/^- (.*?)(?=\n|$)/gm, "<li>$1</li>");

    formatted = formatted.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");

    formatted = formatted
      .split("\n\n")
      .map((paragraph) => {
        if (paragraph.trim() === "") {
          return "";
        }

        if (
          paragraph.includes("<h") ||
          paragraph.includes("<ul") ||
          paragraph.includes("<li")
        ) {
          return paragraph;
        }

        return `<p>${paragraph}</p>`;
      })
      .join("");

    if (citation) {
      formatted += `
        <div class="ai-citation">
          ${citation}
        </div>
      `;
    }

    return formatted;
  }

  /* =========================================================
     Chat Messages
     ========================================================= */

  function addMessage(role, content, isLoading = false) {
    const messageDiv = document.createElement("div");

    messageDiv.className = `chat-message ${role} ${isLoading ? "loading" : ""}`;

    if (role === "assistant" && !isLoading) {
      messageDiv.innerHTML = content;
    } else {
      messageDiv.textContent = content;
    }

    chatContainer.appendChild(messageDiv);

    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  /* =========================================================
     Events
     ========================================================= */

  if (askButton) {
    askButton.addEventListener("click", askQuestion);
  }

  if (questionInput) {
    questionInput.addEventListener("keypress", function (event) {
      if (event.key === "Enter") {
        askQuestion();
      }
    });
  }

  /* =========================================================
     Completion
     ========================================================= */

  const markCompleted = document.getElementById("markCompleted");

  if (markCompleted) {
    markCompleted.addEventListener("click", function () {
      this.disabled = true;

      this.innerHTML = `
          <span class="completion-spinner"></span>
          Updating...
        `;

      setTimeout(() => {
        this.innerHTML = `
            <span>✓</span>
            Completed
          `;

        this.classList.add("completed");

        const message = document.createElement("div");

        message.className = "completion-message";

        message.textContent =
          "Lesson marked as completed. You can continue to the next task.";

        this.parentNode.parentNode.appendChild(message);

        setTimeout(() => {
          message.remove();
        }, 3000);
      }, 1000);
    });
  }
  const refreshLesson = document.getElementById("refreshLesson");

  if (refreshLesson) {
    refreshLesson.addEventListener("click", function () {
      location.reload();
    });
  }
});
