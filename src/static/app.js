document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const accountButton = document.getElementById("account-button");
  const accountMenu = document.getElementById("account-menu");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const accountStatus = document.getElementById("account-status");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  let isTeacher = false;

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(activitySelect.options[0]);

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        const title = document.createElement("h4");
        title.textContent = name;
        const description = document.createElement("p");
        description.textContent = details.description;
        const schedule = document.createElement("p");
        schedule.innerHTML = "<strong>Schedule:</strong> ";
        schedule.append(document.createTextNode(details.schedule));
        const availability = document.createElement("p");
        availability.innerHTML = "<strong>Availability:</strong> ";
        availability.append(document.createTextNode(`${spotsLeft} spots left`));
        const participantsContainer = document.createElement("div");
        participantsContainer.className = "participants-container";
        const participantsHeading = document.createElement("h5");
        participantsHeading.textContent = "Participants:";
        participantsContainer.appendChild(participantsHeading);

        if (details.participants.length > 0) {
          const participantsList = document.createElement("ul");
          participantsList.className = "participants-list";
          details.participants.forEach((email) => {
            const participantItem = document.createElement("li");
            const participantEmail = document.createElement("span");
            participantEmail.className = "participant-email";
            participantEmail.textContent = email;
            participantItem.appendChild(participantEmail);

            if (isTeacher) {
              const removeButton = document.createElement("button");
              removeButton.className = "delete-btn";
              removeButton.type = "button";
              removeButton.textContent = "Remove";
              removeButton.setAttribute("aria-label", `Unregister ${email}`);
              removeButton.dataset.activity = name;
              removeButton.dataset.email = email;
              removeButton.addEventListener("click", handleUnregister);
              participantItem.appendChild(removeButton);
            }
            participantsList.appendChild(participantItem);
          });
          participantsContainer.appendChild(participantsList);
        } else {
          const noParticipants = document.createElement("p");
          noParticipants.innerHTML = "<em>No participants yet</em>";
          participantsContainer.appendChild(noParticipants);
        }

        activityCard.append(
          title,
          description,
          schedule,
          availability,
          participantsContainer
        );

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  accountButton.addEventListener("click", () => {
    const isExpanded = accountButton.getAttribute("aria-expanded") === "true";
    accountButton.setAttribute("aria-expanded", String(!isExpanded));
    accountMenu.classList.toggle("hidden", isExpanded);
  });

  loginButton.addEventListener("click", () => {
    accountMenu.classList.add("hidden");
    accountButton.setAttribute("aria-expanded", "false");
    loginMessage.className = "hidden";
    loginMessage.textContent = "";
    loginDialog.showModal();
  });

  document.getElementById("cancel-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        loginMessage.textContent = result.detail || "Unable to log in";
        loginMessage.className = "error";
        return;
      }

      loginDialog.close();
      loginForm.reset();
      await refreshAuthState();
      await fetchActivities();
    } catch (error) {
      loginMessage.textContent = "Failed to log in. Please try again.";
      loginMessage.className = "error";
      console.error("Error logging in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to log out");
      }
      await refreshAuthState();
      await fetchActivities();
    } catch (error) {
      accountStatus.textContent = "Unable to log out. Please try again.";
      accountStatus.classList.remove("hidden");
      console.error("Error logging out:", error);
    }
  });

  async function refreshAuthState() {
    try {
      const response = await fetch("/auth/me");
      if (!response.ok) {
        throw new Error("Unable to read login status");
      }
      const result = await response.json();
      isTeacher = result.authenticated;
      signupContainer.classList.toggle("hidden", !isTeacher);
      loginButton.classList.toggle("hidden", isTeacher);
      logoutButton.classList.toggle("hidden", !isTeacher);
      accountStatus.textContent = isTeacher ? `Signed in as ${result.username}` : "";
      accountStatus.classList.toggle("hidden", !isTeacher);
    } catch (error) {
      isTeacher = false;
      signupContainer.classList.add("hidden");
      loginButton.classList.remove("hidden");
      logoutButton.classList.add("hidden");
      accountStatus.classList.add("hidden");
      console.error("Error reading login status:", error);
    }
  }

  // Initialize app
  refreshAuthState().then(fetchActivities);
});
