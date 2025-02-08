// Constants and Config
const CONFIG = {
  API_BASE:
    window.location.hostname === "localhost"
      ? "http://localhost:8000"
      : window.location.origin,
  REFRESH_INTERVAL: 30000,
  ALERT_TIMEOUT: 5000,
};

// State
const state = {
  authToken: localStorage.getItem("authToken"),
  popularityRefreshInterval: null,
};

// UI Components
class UIComponent {
  static createAlert(message, type) {
    const alertDiv = document.createElement("div");
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
            ${typeof message === "object" ? JSON.stringify(message, null, 2) : message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
    document.querySelector("#alerts").appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), CONFIG.ALERT_TIMEOUT);
  }

  static showError(message) {
    this.createAlert(message, "danger");
  }

  static showSuccess(message) {
    this.createAlert(message, "success");
  }
}

// API Service
class APIService {
  static async fetchWithAuth(endpoint, options = {}) {
    const response = await fetch(`${CONFIG.API_BASE}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${state.authToken}`,
      },
    });
    const data = await response.json();
    if (!response.ok) throw data;
    return data;
  }

  static async getActiveGames() {
    return this.fetchWithAuth("/games/");
  }

  static async submitScore(scoreData) {
    return this.fetchWithAuth("/scores/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scoreData),
    });
  }

  static async getLeaderboard() {
    return this.fetchWithAuth("/leaderboard/");
  }

  static async getGamePopularity() {
    return this.fetchWithAuth("/games/popularity/");
  }

  static async deleteGame(gameId) {
    return this.fetchWithAuth(`/games/${gameId}`, {
      method: "DELETE",
    });
  }

  static async toggleGameStatus(gameId, active) {
    return this.fetchWithAuth(`/games/${gameId}/${active ? "start" : "end"}`, {
      method: "PUT",
    });
  }

  static async getContestants() {
    return this.fetchWithAuth("/contestants/");
  }

  static async createContestant(contestantData) {
    return this.fetchWithAuth("/contestants/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(contestantData),
    });
  }

  static async deleteContestant(contestantId) {
    return this.fetchWithAuth(`/contestants/${contestantId}`, {
      method: "DELETE",
    });
  }
}

// Game Manager
class GameManager {
  static async loadActiveGames() {
    try {
      const games = await APIService.getActiveGames();
      this.updateActiveGamesUI(games);
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to load active games");
    }
  }

  static updateActiveGamesUI(games) {
    const container = document.querySelector("#activeGames");
    container.innerHTML = games
      .map(
        (game) => `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span>${game.name}</span>
                <div>
                    <button class="btn btn-sm ${game.is_active ? "btn-success" : "btn-secondary"}"
                            onclick="GameManager.toggleGameStatus(${game.id}, ${!game.is_active})">
                        ${game.is_active ? "Active" : "Inactive"}
                    </button>
                    <button class="btn btn-sm btn-primary"
                            onclick="GameManager.selectGame(${game.id}, '${game.name}')">
                        Select
                    </button>
                    <button class="btn btn-sm btn-danger"
                            onclick="GameManager.deleteGame(${game.id})">
                        Delete
                    </button>
                </div>
            </div>
        `,
      )
      .join("");

    // Update game select dropdown
    const gameSelect = document.querySelector('select[name="game_id"]');
    gameSelect.innerHTML = `
            <option value="">Select Game</option>
            ${games
              .filter((game) => game.is_active)
              .map(
                (game) => `
                <option value="${game.id}">${game.name}</option>
            `,
              )
              .join("")}
        `;
  }

  static selectGame(gameId) {
    document.querySelector('select[name="game_id"]').value = gameId;
    document.querySelector('input[name="score"]').focus();
  }

  static async deleteGame(gameId) {
    if (!confirm("Are you sure you want to delete this game?")) return;
    try {
      await APIService.deleteGame(gameId);
      UIComponent.showSuccess("Game deleted successfully");
      this.loadActiveGames();
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to delete game");
    }
  }

  static async toggleGameStatus(gameId, active) {
    try {
      await APIService.toggleGameStatus(gameId, active);
      UIComponent.showSuccess(
        `Game ${active ? "activated" : "deactivated"} successfully`,
      );
      this.loadActiveGames();
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to update game status");
    }
  }

  static async submitGameScore(event) {
    event.preventDefault();
    const formData = new FormData(event.target);

    try {
      await APIService.submitScore({
        contestant_id: parseInt(formData.get("contestant_id")),
        game_id: parseInt(formData.get("game_id")),
        score: parseFloat(formData.get("score")),
      });

      UIComponent.showSuccess("Score submitted successfully!");
      event.target.reset();
      this.loadRecentScores();
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to submit score");
    }
  }

  static async loadRecentScores() {
    try {
      const data = await APIService.getLeaderboard();
      const tbody = document.querySelector("#recentScores");
      tbody.innerHTML = data
        .slice(0, 10)
        .map(
          (entry) => `
                <tr>
                    <td>${entry.game_name}</td>
                    <td>${entry.score}</td>
                    <td>${new Date(entry.timestamp).toLocaleString()}</td>
                </tr>
            `,
        )
        .join("");
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to load recent scores");
    }
  }
}

// Popularity Dashboard
class PopularityDashboard {
  static async loadGamePopularity() {
    try {
      const data = await APIService.getGamePopularity();
      this.updatePopularityUI(data);
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to load game popularity");
    }
  }

  static updatePopularityUI(data) {
    const container = document.querySelector("#popularityContent");
    container.innerHTML = `
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Game</th>
                            <th>Popularity Score</th>
                            <th>Total Scores</th>
                            <th>Unique Players</th>
                            <th>Recent Activity</th>
                            <th>Trend</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data
                          .map(
                            (game) => `
                            <tr>
                                <td>${game.name}</td>
                                <td>${game.popularity_score.toFixed(2)}</td>
                                <td>${game.total_scores}</td>
                                <td>${game.unique_players}</td>
                                <td>${game.recent_scores}</td>
                                <td>
                                    <i class="bi bi-arrow-${game.score_trend > 0 ? "up" : "down"}-circle${
                                      game.score_trend === 0 ? "-fill" : ""
                                    } text-${game.score_trend > 0 ? "success" : "danger"}"></i>
                                    ${Math.abs(game.score_trend * 100).toFixed(1)}%
                                </td>
                            </tr>
                        `,
                          )
                          .join("")}
                    </tbody>
                </table>
            </div>
        `;
  }

  static startPopularityRefresh() {
    this.loadGamePopularity();
    if (state.popularityRefreshInterval) {
      clearInterval(state.popularityRefreshInterval);
    }
    state.popularityRefreshInterval = setInterval(
      () => this.loadGamePopularity(),
      CONFIG.REFRESH_INTERVAL,
    );
  }
}

// Contest Manager
class ContestManager {
  static async loadContestants() {
    try {
      const contestants = await APIService.getContestants();
      this.updateContestantsUI(contestants);
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to load contestants");
    }
  }

  static updateContestantsUI(contestants) {
    const container = document.querySelector("#contestantsList");
    if (container) {
      container.innerHTML = contestants
        .map(
          (contestant) => `
              <tr>
                  <td>${contestant.name}</td>
                  <td>${contestant.email}</td>
                  <td>${new Date(contestant.created_at).toLocaleString()}</td>
                  <td>
                      <button class="btn btn-sm btn-danger"
                              onclick="ContestManager.deleteContestant(${contestant.id})">
                          Delete
                      </button>
                  </td>
              </tr>
          `,
        )
        .join("");
    }

    // Update contestant select dropdowns
    const selects = document.querySelectorAll('select[name="contestant_id"]');
    const options = contestants
      .map(
        (contestant) => `
          <option value="${contestant.id}">${contestant.name}</option>
      `,
      )
      .join("");

    selects.forEach((select) => {
      select.innerHTML = `
          <option value="">Select Contestant</option>
          ${options}
      `;
    });
  }

  static async createContestant(event) {
    event.preventDefault();
    const formData = new FormData(event.target);

    try {
      await APIService.createContestant({
        name: formData.get("name"),
        email: formData.get("email"),
      });

      UIComponent.showSuccess("Contestant created successfully!");
      event.target.reset();
      this.loadContestants();
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to create contestant");
    }
  }

  static async deleteContestant(contestantId) {
    if (!confirm("Are you sure you want to delete this contestant?")) return;
    try {
      await APIService.deleteContestant(contestantId);
      UIComponent.showSuccess("Contestant deleted successfully");
      this.loadContestants();
    } catch (error) {
      UIComponent.showError(error.detail || "Failed to delete contestant");
    }
  }
}

// Logout function
function logout() {
  localStorage.removeItem("authToken");
  window.location.href = "/";
}

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
  if (!state.authToken) {
    window.location.href = "/";
    return;
  }

  GameManager.loadActiveGames();
  GameManager.loadRecentScores();
  ContestManager.loadContestants();
  setInterval(() => GameManager.loadRecentScores(), CONFIG.REFRESH_INTERVAL);

  // Initialize popularity tab
  const popularityTab = document.querySelector('a[href="#popularity"]');
  if (popularityTab) {
    popularityTab.addEventListener("click", () => {
      PopularityDashboard.loadGamePopularity();
      PopularityDashboard.startPopularityRefresh();
    });
  }

  // Handle tab switching
  document.querySelectorAll(".nav-link").forEach((tab) => {
    tab.addEventListener("click", (e) => {
      if (
        e.target.getAttribute("href") !== "#popularity" &&
        state.popularityRefreshInterval
      ) {
        clearInterval(state.popularityRefreshInterval);
      }
    });
  });

  // Load popularity data if popularity tab is active
  const activeTab = document.querySelector(".nav-link.active");
  if (activeTab?.getAttribute("href") === "#popularity") {
    PopularityDashboard.loadGamePopularity();
    PopularityDashboard.startPopularityRefresh();
  }

  // Set up form submission
  document
    .querySelector("#scoreForm")
    .addEventListener("submit", (e) => GameManager.submitGameScore(e));
});

function updateGamePopularity() {
  const refreshBadge = document.querySelector(".refresh-badge");
  refreshBadge.classList.add("refreshing");

  fetch("/games/popularity")
    .then((response) => response.json())
    .then((data) => {
      displayPopularityData(data);
      setTimeout(() => refreshBadge.classList.remove("refreshing"), 500);
    });
}

// Set 5-minute refresh
setInterval(updateGamePopularity, 300000);
