/**
 * Help modal functionality for ClueChain game
 * Displays game rules in a modal dialog
 */

// Game rules content parsed from Markdown
const gameRules = {
  title: "Quick Rules for First-Time Players",
  rules: [
    {
      number: 1,
      title: "Pick your starting letters",
      description: "Choose 1 vowel and 2 consonants at the start. These letters are revealed wherever they appear in the hidden words."
    },
    {
      number: 2,
      title: "Start guessing words",
      description: "There are 10 hidden words in the paragraph. You can guess them in any order."
    },
    {
      number: 3,
      title: "Clues unlock progressively",
      description: "Each hidden word has multiple clue tiers — harder clues come first. After every guess (right or wrong), more clues and word endings are revealed."
    },
    {
      number: 4,
      title: "Scoring depends on clue tier",
      description: "Solving a word with a harder clue earns more points (links). If you view easier clues before solving, your points for that word are reduced."
    },
    {
      number: 5,
      title: "Letter Marketplace",
      description: "Spend links to reveal a letter across all hidden words. The marketplace shows how many unrevealed instances of each letter remain."
    },
    {
      number: 6,
      title: "🗝️ Golden Key — one use per game",
      description: "If any word clues are still hidden, the Golden Key reveals the next one for free. Once all clues are visible, it instead upgrades one word to a harder clue tier — with no score penalty."
    },
    {
      number: 7,
      title: "🪙 Golden Coin — one use per game",
      description: "Reveals all instances of a rare letter (appearing 2 or fewer times) across all hidden words, for free."
    },
    {
      number: 8,
      title: "Goal",
      description: "Find all 10 words and maximize your total score. Games where you used a golden item are marked as assisted."
    }
  ]
};

/**
 * Creates and shows the help modal
 */
export function showHelpModal() {
  // Create modal container if it doesn't exist
  let modalContainer = document.getElementById("help-modal-container");
  
  if (!modalContainer) {
    modalContainer = document.createElement("div");
    modalContainer.id = "help-modal-container";
    modalContainer.className = "modal-container";
    document.body.appendChild(modalContainer);
  }
  
  // Set modal content
  modalContainer.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h2>${gameRules.title}</h2>
        <button class="close-button">&times;</button>
      </div>
      <div class="modal-body">
        <ul class="rules-list">
          ${gameRules.rules.map(rule => `
            <li class="rule-item">
              <div class="rule-number">${rule.number}</div>
              <div class="rule-text">
                <h3>${rule.title}</h3>
                <p>${rule.description}</p>
              </div>
            </li>
          `).join('')}
        </ul>
      </div>
    </div>
  `;
  
  // Show the modal
  modalContainer.classList.add("show");
  
  // Add event listener to close button
  const closeButton = modalContainer.querySelector(".close-button");
  if (closeButton) {
    closeButton.addEventListener("click", hideHelpModal);
  }
  
  // Close modal when clicking outside the content
  modalContainer.addEventListener("click", (event) => {
    if (event.target === modalContainer) {
      hideHelpModal();
    }
  });
  
  // Close modal with Escape key
  document.addEventListener("keydown", handleEscapeKey);
}

/**
 * Hides the help modal
 */
export function hideHelpModal() {
  const modalContainer = document.getElementById("help-modal-container");
  if (modalContainer) {
    modalContainer.classList.remove("show");
    // Remove event listener when modal is closed
    document.removeEventListener("keydown", handleEscapeKey);
  }
}

/**
 * Handles Escape key press to close the modal
 * @param {KeyboardEvent} event - The keyboard event
 */
function handleEscapeKey(event) {
  if (event.key === "Escape") {
    hideHelpModal();
  }
}

/**
 * Sets up the help button click handler
 */
export function setupHelpButton() {
  const helpButton = document.getElementById("help-button");
  if (helpButton) {
    helpButton.addEventListener("click", showHelpModal);
  }
}