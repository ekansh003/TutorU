document.addEventListener("DOMContentLoaded", function () {
  const formManager = new FormSubmissionManager();

  window.formManager = formManager;

  initializeCourseIdeas();
  initializeErrorFocus();
});

/* =========================================================
   Form Submission Manager
   ========================================================= */

class FormSubmissionManager {
  constructor() {
    this.isSubmitting = false;
    this.forms = new Map();

    this.init();
  }

  init() {
    this.initializeFormStates();
    this.registerEventListeners();
  }

  /* =======================================================
     Form Initialization
     ======================================================= */

  initializeFormStates() {
    const courseNameForm = document
      .querySelector('form input[name="action"][value="generate_chapters"]')
      ?.closest("form");

    if (courseNameForm) {
      this.initializeCourseNameForm(courseNameForm);
    }

    const chapterForm = document
      .querySelector('form input[name="action"][value="create_course"]')
      ?.closest("form");

    if (chapterForm) {
      this.initializeChapterSelectionForm(chapterForm);
    }
  }

  initializeCourseNameForm(form) {
    const input = form.querySelector("#course_name");
    const submitButton = form.querySelector('button[type="submit"]');

    if (input) {
      input.focus();

      input.addEventListener("input", () => {
        this.validateCourseNameForm(form);
      });

      input.addEventListener("blur", () => {
        this.validateCourseNameForm(form);
      });
    }

    this.forms.set("course_name", {
      form,
      submitButton,
      courseNameInput: input,
      isValid: false,
      validationErrors: [],
    });

    this.validateCourseNameForm(form);
  }

  initializeChapterSelectionForm(form) {
    const checkboxes = form.querySelectorAll('input[name="selected_chapters"]');

    const submitButton = form.querySelector("#createCourseBtn");

    const selectAllButton = document.getElementById("selectAll");

    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        this.updateChapterSelectionState(form);
      });
    });

    if (selectAllButton) {
      selectAllButton.addEventListener("click", () => {
        this.toggleSelectAll(form);
      });
    }

    this.forms.set("chapter_selection", {
      form,
      submitButton,
      checkboxes,
      selectAllBtn: selectAllButton,
      isValid: false,
      validationErrors: [],
    });

    this.updateChapterSelectionState(form);
  }

  /* =======================================================
     Validation
     ======================================================= */

  validateCourseNameForm(form) {
    const input = form.querySelector("#course_name");
    const formState = this.forms.get("course_name");

    if (!input || !formState) {
      return false;
    }

    const courseName = input.value.trim();
    const errors = [];

    input.classList.remove("is-invalid", "is-valid");

    this.clearValidationMessage(input);

    if (!courseName) {
      errors.push("Course name is required");

      input.classList.add("is-invalid");

      this.showValidationMessage(input, "Please enter a course name");
    } else if (courseName.length < 3) {
      errors.push("Course name must be at least 3 characters long");

      input.classList.add("is-invalid");

      this.showValidationMessage(
        input,
        "Course name must be at least 3 characters long",
      );
    } else if (courseName.length > 200) {
      errors.push("Course name must be less than 200 characters");

      input.classList.add("is-invalid");

      this.showValidationMessage(
        input,
        "Course name must be less than 200 characters",
      );
    } else {
      input.classList.add("is-valid");
    }

    formState.isValid = errors.length === 0;
    formState.validationErrors = errors;

    return formState.isValid;
  }

  /* =======================================================
     Chapter Selection
     ======================================================= */

  updateChapterSelectionState(form) {
    const formState = this.forms.get("chapter_selection");

    if (!formState) {
      return;
    }

    const checkedCount = form.querySelectorAll(
      'input[name="selected_chapters"]:checked',
    ).length;

    const totalCount = form.querySelectorAll(
      'input[name="selected_chapters"]',
    ).length;

    formState.isValid = checkedCount > 0;

    formState.submitButton.disabled = !formState.isValid;

    const selectedCount = document.getElementById("selectedCount");

    if (selectedCount) {
      selectedCount.textContent = `${checkedCount} selected`;
    }

    if (checkedCount === 0) {
      formState.submitButton.innerHTML = "Select chapters to continue";
    } else {
      formState.submitButton.innerHTML = `Create course (${checkedCount}) <span>→</span>`;
    }

    if (formState.selectAllBtn) {
      const allChecked = checkedCount === totalCount && totalCount > 0;

      formState.selectAllBtn.textContent = allChecked
        ? "Deselect all"
        : "Select all";
    }
  }

  toggleSelectAll(form) {
    const checkboxes = form.querySelectorAll('input[name="selected_chapters"]');

    const allChecked =
      checkboxes.length > 0 &&
      Array.from(checkboxes).every((checkbox) => checkbox.checked);

    checkboxes.forEach((checkbox) => {
      checkbox.checked = !allChecked;
    });

    this.updateChapterSelectionState(form);
  }

  /* =======================================================
     Form Submission
     ======================================================= */

  handleFormSubmission(event) {
    const form = event.target;

    const actionInput = form.querySelector('input[name="action"]');

    if (!actionInput) {
      return;
    }

    if (this.isSubmitting) {
      event.preventDefault();
      return;
    }

    const action = actionInput.value;

    if (action === "generate_chapters") {
      const formState = this.forms.get("course_name");

      const isValid = this.validateCourseNameForm(form);

      if (!formState || !isValid) {
        event.preventDefault();

        const input = form.querySelector("#course_name");

        if (input) {
          input.focus();
        }

        return;
      }
    }

    if (action === "create_course") {
      const formState = this.forms.get("chapter_selection");

      if (!formState || !formState.isValid) {
        event.preventDefault();
        return;
      }
    }

    this.setLoadingState(form, true);
  }

  /* =======================================================
     Loading State
     ======================================================= */

  setLoadingState(form, isLoading) {
    this.isSubmitting = isLoading;

    const submitButton = form.querySelector('button[type="submit"]');

    if (!submitButton) {
      return;
    }

    if (isLoading) {
      submitButton.disabled = true;

      submitButton.dataset.originalText = submitButton.innerHTML;

      const actionInput = form.querySelector('input[name="action"]');

      const action = actionInput?.value || "";

      let message = "Processing...";

      if (action === "generate_chapters") {
        message = "Generating chapters...";
      } else if (action === "create_course") {
        message = "Creating course...";
      }

      submitButton.innerHTML = `
        <span class="button-spinner"></span>
        ${message}
      `;

      return;
    }

    submitButton.disabled = false;

    if (submitButton.dataset.originalText) {
      submitButton.innerHTML = submitButton.dataset.originalText;

      delete submitButton.dataset.originalText;
    }
  }

  /* =======================================================
     Validation Messages
     ======================================================= */

  showValidationMessage(input, message) {
    this.clearValidationMessage(input);

    const feedback = document.createElement("div");

    feedback.className = "course-validation";

    feedback.textContent = message;

    feedback.dataset.validationMessage = "true";

    input.parentNode.appendChild(feedback);
  }

  clearValidationMessage(input) {
    const existing = input.parentNode.querySelector(
      '[data-validation-message="true"]',
    );

    if (existing) {
      existing.remove();
    }
  }

  /* =======================================================
     Events
     ======================================================= */

  registerEventListeners() {
    document.addEventListener("submit", (event) => {
      this.handleFormSubmission(event);
    });
  }
}

/* =========================================================
   Course Ideas
   ========================================================= */

function initializeCourseIdeas() {
  const courseNameInput = document.getElementById("course_name");

  if (!courseNameInput) {
    return;
  }

  document.querySelectorAll(".idea-item").forEach((idea) => {
    idea.addEventListener("click", function () {
      courseNameInput.value = this.dataset.course || "";

      courseNameInput.focus();

      courseNameInput.dispatchEvent(
        new Event("input", {
          bubbles: true,
        }),
      );
    });
  });
}

/* =========================================================
   Focus Input After Error
   ========================================================= */

function initializeErrorFocus() {
  const courseNameInput = document.getElementById("course_name");

  const errorAlert = document.querySelector(".alert-error");

  if (courseNameInput && errorAlert) {
    courseNameInput.focus();
    courseNameInput.select();
  }
}

/* =========================================================
   Restore Loading State
   ========================================================= */

function resetLoadingStates() {
  if (!window.formManager) {
    return;
  }

  document.querySelectorAll("form").forEach((form) => {
    window.formManager.setLoadingState(form, false);
  });
}

window.addEventListener("beforeunload", resetLoadingStates);

window.addEventListener("pageshow", function (event) {
  if (event.persisted) {
    resetLoadingStates();
  }
});

window.addEventListener("error", resetLoadingStates);
