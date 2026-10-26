document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const messageDiv = document.getElementById("message");
  const loginToggle = document.getElementById("login-toggle");
  const logoutButton = document.getElementById("logout-button");
  const userInfo = document.getElementById("user-info");
  const signupPrompt = document.getElementById("signup-prompt");
  const targetEmailGroup = document.getElementById("target-email-group");

  let signedInUser = null;
  let csrfToken = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function updateAuthControls() {
    const isManager =
      signedInUser?.role === "organizer" || signedInUser?.role === "admin";
    loginToggle.classList.toggle("hidden", Boolean(signedInUser));
    userInfo.classList.toggle("hidden", !signedInUser);
    loginForm.classList.add("hidden");
    signupPrompt.classList.toggle("hidden", Boolean(signedInUser));
    signupForm.classList.toggle("hidden", !signedInUser);
    targetEmailGroup.classList.toggle("hidden", !isManager);
    document.getElementById("target-email").required = Boolean(isManager);
    document.getElementById("registered-user-label").textContent = signedInUser
      ? `Signed in as ${signedInUser.email}`
      : "";
    document.getElementById("current-user").textContent = signedInUser
      ? `${signedInUser.email} (${signedInUser.role})`
      : "";
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error(`Activity request failed with status ${response.status}`);
      }
      const activities = await response.json();
      activitiesList.innerHTML = "";
      activitySelect.length = 1;

      Object.entries(activities).forEach(([name, details]) => {
        const spotsLeft =
          details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
                <h5>Participants:</h5>
                <ul class="participants-list">
                  ${details.participants
                    .map((email) => {
                      const canUnregister =
                        signedInUser &&
                        (signedInUser.role === "admin" ||
                          signedInUser.role === "organizer" ||
                          (signedInUser.role === "student" &&
                            signedInUser.email === email));
                      const removeButton = canUnregister
                        ? `<button class="delete-btn" data-activity="${escapeHtml(name)}" data-email="${escapeHtml(email)}" aria-label="Unregister ${escapeHtml(email)}">Unregister</button>`
                        : "";
                      return `<li><span class="participant-email">${escapeHtml(email)}</span>${removeButton}</li>`;
                    })
                    .join("")}
                </ul>
              </div>`
            : "<p><em>No participants yet</em></p>";

        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">${participantsHTML}</div>
        `;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;
    const targetQuery =
      signedInUser.role === "student"
        ? ""
        : `?email=${encodeURIComponent(email)}`;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister${targetQuery}`,
        {
          method: "DELETE",
          headers: { "X-CSRF-Token": csrfToken },
        }
      );
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to unregister");
      }
      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  loginToggle.addEventListener("click", () => {
    loginForm.classList.toggle("hidden");
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("login-email").value,
          password: document.getElementById("login-password").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign in");
      }
      signedInUser = { email: result.email, role: result.role };
      csrfToken = result.csrf_token;
      loginForm.reset();
      updateAuthControls();
      showMessage(`Signed in as ${result.email}`, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to sign in. Please try again.", "error");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken },
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign out");
      }
      signedInUser = null;
      csrfToken = null;
      updateAuthControls();
      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const activity = activitySelect.value;
    const targetEmail = document.getElementById("target-email").value.trim();
    const emailQuery =
      signedInUser.role === "student"
        ? ""
        : `?email=${encodeURIComponent(targetEmail)}`;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup${emailQuery}`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": csrfToken },
        }
      );
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign up");
      }
      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  async function initialize() {
    updateAuthControls();
    try {
      const response = await fetch("/auth/me");
      if (!response.ok) {
        throw new Error(`Authentication request failed with status ${response.status}`);
      }
      const result = await response.json();
      signedInUser = result.user;
      csrfToken = result.csrf_token;
    } catch (error) {
      console.error("Error checking authentication:", error);
    }
    updateAuthControls();
    await fetchActivities();
  }

  initialize();
});
