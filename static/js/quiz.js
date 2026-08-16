document.addEventListener("DOMContentLoaded", function () {
  const questions = window.TUTORU_QUESTIONS || [];

  // Nothing to initialize if the quiz has no questions.
  if (!questions.length) {
    return;
  }

  let currentQuestion = 0;
  let answers = new Array(questions.length).fill(null);
  let submitted = false;

  const quizContainer = document.getElementById("quizContainer");

  const questionCounter = document.getElementById("questionCounter");

  const progressBar = document.getElementById("progressBar");

  const progressPercentage = document.getElementById("progressPercentage");

  const prevBtn = document.getElementById("prevBtn");

  const nextBtn = document.getElementById("nextBtn");

  const submitBtn = document.getElementById("submitBtn");

  const resultsModalElement = document.getElementById("resultsModal");

  const resultsModal = resultsModalElement
    ? new bootstrap.Modal(resultsModalElement)
    : null;

  /* =========================================================
     Load Question
     ========================================================= */

  function loadQuestion() {
    const question = questions[currentQuestion];

    if (!question) {
      return;
    }

    const progress = ((currentQuestion + 1) / questions.length) * 100;

    questionCounter.textContent = `Question ${currentQuestion + 1} of ${questions.length}`;

    progressBar.style.width = `${progress}%`;

    progressPercentage.textContent = `${Math.round(progress)}%`;

    /* Previous button */

    prevBtn.disabled = currentQuestion === 0;

    /* Next / Submit buttons */

    if (currentQuestion === questions.length - 1) {
      nextBtn.classList.add("d-none");
      submitBtn.classList.remove("d-none");
    } else {
      nextBtn.classList.remove("d-none");
      submitBtn.classList.add("d-none");
    }

    /* Question */

    quizContainer.innerHTML = `
      <section class="question-card">

        <div class="question-number">
          QUESTION ${String(currentQuestion + 1).padStart(2, "0")}
        </div>

        <h2 class="question-text">
          ${question.question}
        </h2>

        <div class="quiz-options">

          ${question.options
            .map(
              (option, index) => `
                <button
                  type="button"
                  class="quiz-option"
                  data-option="${escapeAttribute(option)}"
                >
                  <span class="option-letter">
                    ${String.fromCharCode(65 + index)}
                  </span>

                  <span class="option-text">
                    ${option}
                  </span>

                  <span class="option-check">
                    ✓
                  </span>
                </button>
              `,
            )
            .join("")}

        </div>

      </section>
    `;

    /* Restore previously selected answer */

    if (answers[currentQuestion] !== null) {
      const selectedOption = Array.from(
        quizContainer.querySelectorAll(".quiz-option"),
      ).find((option) => option.dataset.option === answers[currentQuestion]);

      if (selectedOption) {
        selectedOption.classList.add("selected");
      }
    }

    /* Option handlers */

    const options = quizContainer.querySelectorAll(".quiz-option");

    options.forEach((option) => {
      option.addEventListener("click", function () {
        if (submitted) {
          return;
        }

        options.forEach((opt) => {
          opt.classList.remove("selected");
        });

        this.classList.add("selected");

        answers[currentQuestion] = this.dataset.option;
      });
    });
  }

  /* =========================================================
     Previous
     ========================================================= */

  prevBtn.addEventListener("click", function () {
    if (currentQuestion > 0) {
      currentQuestion--;
      loadQuestion();
    }
  });

  /* =========================================================
     Next
     ========================================================= */

  nextBtn.addEventListener("click", function () {
    if (currentQuestion < questions.length - 1) {
      currentQuestion++;
      loadQuestion();
    }
  });

  /* =========================================================
     Submit
     ========================================================= */

  submitBtn.addEventListener("click", function () {
    const unanswered = answers.filter((answer) => answer === null).length;

    if (unanswered > 0) {
      const shouldSubmit = confirm(
        `You have ${unanswered} unanswered question(s). Do you want to submit anyway?`,
      );

      if (!shouldSubmit) {
        return;
      }
    }

    submitted = true;

    let correctCount = 0;

    questions.forEach((question, index) => {
      if (answers[index] === question.correct_answer) {
        correctCount++;
      }
    });

    const score = Math.round((correctCount / questions.length) * 100);

    showResults(correctCount, questions.length, score);

    /* Save score */

    fetch("/submit_quiz", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        answers: answers,
        questions: questions,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data.success) {
          console.error("Failed to save quiz scores:", data.error);
        }
      })
      .catch((error) => {
        console.error("Error saving quiz scores:", error);
      });
  });

  /* =========================================================
     Results
     ========================================================= */

  function showResults(correct, total, percentage) {
    const resultsContent = document.getElementById("resultsContent");

    let grade;
    let message;

    if (percentage >= 90) {
      grade = "A";
      message = "Excellent work! You have mastered this topic.";
    } else if (percentage >= 80) {
      grade = "B";
      message = "Great job! You have a good understanding of this topic.";
    } else if (percentage >= 70) {
      grade = "C";
      message =
        "Good effort! Review the material to improve your understanding.";
    } else if (percentage >= 60) {
      grade = "D";
      message = "Keep studying! You need more practice with this topic.";
    } else {
      grade = "F";
      message = "Don't give up! Review the lesson and try again.";
    }

    resultsContent.innerHTML = `
      <div class="score-display">

        <div class="score-number">
          ${percentage}%
        </div>

        <div class="score-grade">
          Grade ${grade}
        </div>

        <p>
          ${correct}
          out of
          ${total}
          questions correct
        </p>

      </div>

      <div class="results-message">
        ${message}
      </div>

      <div class="results-stats">

        <div class="result-stat">

          <span class="result-stat-number correct">
            ${correct}
          </span>

          <span>
            Correct
          </span>

        </div>

        <div class="result-stat">

          <span class="result-stat-number incorrect">
            ${total - correct}
          </span>

          <span>
            Incorrect
          </span>

        </div>

      </div>
    `;

    if (resultsModal) {
      resultsModal.show();
    }
  }

  /* =========================================================
     Attribute Helper
     ========================================================= */

  function escapeAttribute(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /* =========================================================
     Initialize
     ========================================================= */

  loadQuestion();
});
ffff;
