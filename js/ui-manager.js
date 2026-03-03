/**
 * @fileoverview UI rendering and DOM manipulation module for ParaSight.
 * Handles all user interface updates and DOM interactions.
 * @module ui-manager
 */

console.log("🔄 UI Manager loaded - Version 1.1 with fixes for vowel selection and correct guess notifications");

/**
 * @typedef {import('./game-state.js').GameWord} GameWord
 * @typedef {import('./game-state.js').GameParagraph} GameParagraph
 */

import {
  getCurrentParagraph,
  getCurrentWords,
  getCurrentScore,
  getMaxScore,
  maskWord,
  maskWordWithPurchases,
  getChosenVowel,
  purchaseVowel,
  purchaseConsonant,
  getLetterCounts,
  getGameParameters,
  marketState,
  getInitialCluesShown,
  getClueAttempts,
  getShownWordIndices,
  revealWord,
  isInitPhase,
  isSelectionComplete,
  getSelectedVowel,
  getSelectedConsonants,
  setSelectedVowel,
  addSelectedConsonant,
  clearSelectedConsonants,
  completeLetterSelection,
  updateActiveClueIndex,
  getActiveClueIndex,
  getLowestClueIndexSeen,
  gameState,
  revealSelectedLetters,
  showInitialCluesAfterSelection,
  getGoldenKeyMode,
  useGoldenKey,
  useGoldenCoin,
  getEligibleCoinLetters,
} from "./game-state.js?v=1.1";

import {
  celebrateGameOver,
  celebrateRevealGameOver,
  highlightCorrectWord,
  createSparklesAroundElement,
} from "./animations.js";

/**
 * A map to store currently animated clues to prevent duplicate animations
 * @type {Map<string, boolean>}
 */
const animatingClues = new Map();

/**
 * A map to track chain links that have been animated
 * @type {Map<number, boolean>}
 */
const animatedChainLinks = new Map();

/**
 * Counter for notification IDs
 * @type {number}
 */
let notificationIdCounter = 0;

/**
 * Maximum number of notifications to keep in the panel
 * @type {number}
 */
const MAX_NOTIFICATIONS = 10;

/**
 * Track whether initial message has been shown
 * @type {boolean}
 */
let initialMessageShown = false;

/**
 * Updates the DOM element if it exists
 * @param {string} id - Element ID
 * @param {(element: HTMLElement) => void} updater - Function to update the element
 */
function updateElement(id, updater) {
  const element = document.getElementById(id);
  if (element) updater(element);
}

/**
 * Adds a notification to the notification panel
 * @param {string} message - The notification message
 * @param {string} type - The notification type (info, success, error, warning)
 * @param {boolean} persistent - Whether the notification should persist
 * @returns {string} The notification ID
 */
export function addNotification(message, type = "info", persistent = true) {
  const notificationContent = document.querySelector(".notification-content");
  if (!notificationContent) return "";

  // Check for duplicate messages to prevent showing the same message multiple times
  // Skip duplicate check for guess notifications to allow multiple correct/wrong guesses
  if (!type.includes("success") && !type.includes("error")) {
    const existingNotifications = notificationContent.querySelectorAll(".notification-text");
    for (const existingNotification of existingNotifications) {
      if (existingNotification.textContent === message) {
        console.log(`Duplicate notification prevented: "${message}"`);
        return ""; // Don't add duplicate
      }
    }
  }

  const notificationId = `notification-${++notificationIdCounter}`;
  
  // Create notification card
  const card = document.createElement("div");
  card.className = `notification-card notification-${type}`;
  card.id = notificationId;
  
  // Add timestamp for newer notifications
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  
  card.innerHTML = `
    <span class="notification-text">${message}</span>
    <span class="notification-time" style="font-size: 0.7em; color: #888; float: right;">${timeStr}</span>
  `;
  
  // Add click handler to dismiss notification if not persistent
  if (!persistent) {
    card.style.cursor = "pointer";
    card.addEventListener("click", () => removeNotification(notificationId));
  }
  
  // Add to top of notifications
  notificationContent.insertBefore(card, notificationContent.firstChild);
  
  // Limit number of notifications
  const notifications = notificationContent.querySelectorAll(".notification-card");
  if (notifications.length > MAX_NOTIFICATIONS) {
    // Remove oldest notifications
    for (let i = MAX_NOTIFICATIONS; i < notifications.length; i++) {
      notifications[i].remove();
    }
  }
  
  // Scroll to top to show new notification
  notificationContent.scrollTop = 0;
  
  return notificationId;
}

/**
 * Removes a specific notification by ID
 * @param {string} notificationId - The ID of the notification to remove
 */
export function removeNotification(notificationId) {
  const notification = document.getElementById(notificationId);
  if (notification) {
    notification.style.transition = "all 0.3s ease";
    notification.style.opacity = "0";
    notification.style.transform = "translateX(-20px)";
    setTimeout(() => {
      if (notification.parentNode) {
        notification.remove();
      }
    }, 300);
  }
}

/**
 * Clears all notifications from the panel
 */
export function clearNotifications() {
  const notificationContent = document.querySelector(".notification-content");
  if (notificationContent) {
    notificationContent.innerHTML = "";
  }
}

/**
 * Shows the initial game message only once
 */
export function showInitialMessage() {
  if (!initialMessageShown) {
    addNotification("Please select 1 vowel and 2 consonants to begin", "info", true);
    initialMessageShown = true;
  }
}

/**
 * Adds a notification for a correct guess
 * @param {string} word - The correctly guessed word
 * @param {number} points - Points earned for the guess
 */
export function addCorrectGuessNotification(word, points) {
  console.log(`Adding correct guess notification: word="${word}", points=${points}`);
  const message = `${word.toUpperCase()} Correct! You earned ${points} links!`;
  console.log(`Notification message: "${message}"`);
  const notificationId = addNotification(message, "success", true);
  const notification = document.getElementById(notificationId);
  if (notification) {
    notification.classList.add("notification-correct-guess");
    console.log(`Successfully added correct guess notification with ID: ${notificationId}`);
  } else {
    console.log(`Failed to find notification element with ID: ${notificationId}`);
  }
}

/**
 * Adds a notification for an incorrect guess
 * @param {string} word - The incorrectly guessed word
 */
export function addIncorrectGuessNotification(word) {
  const message = `${word.toUpperCase()} - Wrong guess`;
  const notificationId = addNotification(message, "error", true);
  const notification = document.getElementById(notificationId);
  if (notification) {
    notification.classList.add("notification-wrong-guess");
  }
}

/**
 * Updates the selection status in notifications with contextual messages
 * @param {string} vowel - Selected vowel
 * @param {string[]} consonants - Selected consonants
 */
export function updateSelectionStatus(vowel = "", consonants = []) {
  // Don't show status message if initial message hasn't been shown yet or no selections made
  if (!vowel && consonants.length === 0 && !initialMessageShown) {
    return; // Let showInitialMessage handle the first message
  }
  
  // Generate contextual message based on current selection state
  let statusMessage = "";
  
  if (!vowel && consonants.length === 0) {
    // Don't add another initial message if we already have one
    return;
  } else if (vowel && consonants.length === 0) {
    statusMessage = `Vowel selected: ${vowel.toUpperCase()}. Select 2 consonants to continue`;
  } else if (vowel && consonants.length === 1) {
    statusMessage = `Selected: ${vowel.toUpperCase()}, ${consonants[0].toUpperCase()}. Select 1 more consonant to continue`;
  } else if (vowel && consonants.length === 2) {
    statusMessage = `Selection complete: ${vowel.toUpperCase()}, ${consonants.join(', ').toUpperCase()}`;
  }
  
  // Find existing status notification and update it, or create new one
  const existingStatus = document.querySelector('[data-notification-type="selection-status"]');
  if (existingStatus) {
    const textSpan = existingStatus.querySelector('.notification-text');
    if (textSpan) {
      textSpan.textContent = statusMessage;
    }
  } else if (statusMessage) {
    const notificationId = addNotification(statusMessage, "info", true);
    const notification = document.getElementById(notificationId);
    if (notification) {
      notification.setAttribute('data-notification-type', 'selection-status');
    }
  }
}

/**
 * Animates the tumble down effect for a clue when its word is found
 * @param {string} word - The word that was found
 * @returns {boolean} Whether the animation was successfully started
 */
export function animateClueForWord(word) {
  if (!word) return false;

  // Normalize the word to lowercase for comparison
  const normalizedWord = word.toLowerCase();

  // If this word is already being animated, skip
  if (animatingClues.has(normalizedWord)) return false;

  // Find the clue element for this word
  const clueElements = document.querySelectorAll(
    "#clues-list .active-clues-container li"
  );
  let targetClue = null;

  // First try matching by data-word attribute
  clueElements.forEach((clue) => {
    const clueWord = clue.getAttribute("data-word")?.toLowerCase();
    if (clueWord === normalizedWord) {
      targetClue = clue;
    }
  });

  // If we didn't find it that way, try looking at the clue text content
  if (!targetClue) {
    clueElements.forEach((clue) => {
      const clueText = clue.textContent.toLowerCase();
      if (clueText.includes(`(${word.length})`)) {
        // This clue is for a word of the same length
        targetClue = clue;
      }
    });
  }

  if (!targetClue) {
    console.log(`ℹ️ Clue for "${word}" wasn't visible yet, skipping animation. It will appear in the solved section.`);
    // Even without animation, make sure clues are re-rendered to show in solved section
    setTimeout(() => renderClues(), 100);

    // Update chain links even if clue animation fails
    updateChainLinks();
    return false;
  }

  // Mark this clue as currently animating
  animatingClues.set(normalizedWord, true);

  // Add the tumble-down class to trigger animation
  targetClue.classList.add("tumble-down");

  // Update chain links immediately to show progress
  updateChainLinks();

  // When animation completes, re-render clues to move this item to the solved section
  setTimeout(() => {
    renderClues();
    // Remove from animating map
    animatingClues.delete(normalizedWord);
  }, 2500); // Match animation duration (2.5s)

  return true;
}

/**
 * Updates the input field and submit button state based on game phase
 */
export function updateInputState() {
  const input = document.getElementById("guess-input");
  const submitButton = document.getElementById("submit-guess");

  if (!input || !submitButton) return;

  // Check if we're in initialization phase and selection is not complete
  const inSelectionPhase = isInitPhase() && !isSelectionComplete();

  // Disable/enable based on game phase
  input.disabled = inSelectionPhase;
  submitButton.disabled = inSelectionPhase;

  if (inSelectionPhase) {
    input.placeholder = "Please select 1 vowel and 2 consonants first...";
    input.classList.add("disabled");
    submitButton.classList.add("disabled");
  } else {
    input.placeholder = "Enter your guess...";
    input.classList.remove("disabled");
    submitButton.classList.remove("disabled");
  }
}

/**
 * Renders the paragraph with masked words
 * @param {string} vowel - The vowel to reveal in masked words
 */
export function renderParagraph(vowel) {
  /** @type {GameParagraph|null} */
  const currentParagraph = getCurrentParagraph();
  if (!currentParagraph) return;

  // Create a list of all word positions that need to be replaced
  // Sort from end to start to avoid index shifting during replacement
  const allReplacements = getCurrentWords()
    .flatMap((word, wordIdx) =>
      word.positions.map((pos) => ({
        ...pos,
        word: word.word,
        found: word.found,
        revealed: word.revealed,
        wordIndex: wordIdx,
      }))
    )
    .sort((a, b) => b.start - a.start);

  let maskedParagraph = currentParagraph.text; // Create word to index mapping first
  const wordToIndexMap = new Map();
  getCurrentWords().forEach((gameWord, idx) => {
    wordToIndexMap.set(gameWord.word.toLowerCase(), idx);
  });

  // Replace words one by one, starting from the end
  allReplacements.forEach(
    ({ start, end, word, found, revealed, wordIndex }) => {
      const wordToReplace = maskedParagraph.substring(start, end);
      // Use different styling for found vs masked vs revealed words
      let maskedWord;

      if (found) {
        // Word found by player
        maskedWord = `<span data-masked="true" data-clue-index="${wordIndex}" class="found">${wordToReplace}</span>`;
      } else if (revealed) {
        // Word revealed by player
        maskedWord = `<span data-masked="true" data-clue-index="${wordIndex}" class="revealed">${wordToReplace}</span>`;
      } else {
        // Word still hidden
        maskedWord = `<span data-masked="true" data-clue-index="${wordIndex}">${maskWordWithPurchases(
          wordToReplace,
          vowel,
          wordIndex
        )}</span>`;
      }

      maskedParagraph =
        maskedParagraph.substring(0, start) +
        maskedWord +
        maskedParagraph.substring(end);
    }
  );

  // Add title if it exists
  let html = "";
  if (currentParagraph.title) {
    if (currentParagraph.title.length > 40) {
      html += `<div class=\"paragraph-title-small\">${currentParagraph.title}</div>`;
    } else {
      html += `<h2 class=\"paragraph-title\">${currentParagraph.title}</h2>`;
    }
  }
  html += maskedParagraph;

  updateElement("paragraph-container", (el) => {
    el.innerHTML = html;
  });

  // Set up interactions between clues and masked words
  setupClueInteractions();
}

/**
 * Sets up hover interactions between clues and masked words
 */
function setupClueInteractions() {
  const cluesList = document.getElementById("clues-list");
  if (!cluesList) return;

  // Check if we're in the initialization phase - if so, disable all interactions
  const inInitPhase = isInitPhase() && !isSelectionComplete();

  // Add a class to the clues container if in init phase
  const cluesContainer = document.getElementById("clues-container");
  if (cluesContainer) {
    cluesContainer.classList.toggle("disabled-clues", inInitPhase);
  }

  // Get all visible clues
  const visibleClues = Array.from(cluesList.getElementsByTagName("li"));

  // Add click handlers for all clue icons
  visibleClues.forEach((clue) => {
    const wordIndex = clue.getAttribute("data-word-index");
    const clueText = clue.querySelector(".clue-text");

    // Add click handlers for each difficulty icon
    const clueIcons = clue.querySelectorAll(".clue-icon");
    clueIcons.forEach((icon) => {
      icon.addEventListener("click", (event) => {
        // Stop propagation to prevent triggering the clue highlight
        event.stopPropagation();

        // Make sure letter selection is complete
        if (isInitPhase() || !isSelectionComplete()) {
          showToast("Please select 1 vowel and 2 consonants first", "error");
          return;
        }

        // Get the clue index (difficulty level)
        const clueIndex = parseInt(icon.getAttribute("data-clue-index"), 10);

        // Update active state of icons
        clueIcons.forEach((i) => i.classList.remove("active"));
        icon.classList.add("active");

        // Get the clues data from the parent li element
        try {
          const cluesData = JSON.parse(clue.getAttribute("data-clues") || "[]");
          const selectedClue = cluesData[clueIndex];

          if (selectedClue && clueText) {
            const word = getCurrentWords()[parseInt(wordIndex, 10)];
            const wordLen = word?.word?.length || 0;

            // Show all revealed clues up to and including the selected one
            if (clueIndex === 0) {
              clueText.textContent = `${selectedClue.clue} (${wordLen})`;
            } else {
              clueText.innerHTML = "";
              for (let ci = 0; ci <= clueIndex; ci++) {
                const clueEntry = document.createElement("span");
                clueEntry.className = `clue-line clue-line-${ci}${ci === clueIndex ? " clue-line-current" : ""}`;
                clueEntry.textContent = ci === clueIndex
                  ? `${cluesData[ci]?.clue || ""} (${wordLen})`
                  : cluesData[ci]?.clue || "";
                clueText.appendChild(clueEntry);
              }
            }

            // Update the active clue index in the UI
            clue.setAttribute("data-active-clue", clueIndex.toString());

            // Update the active clue index in the game state
            updateActiveClueIndex(parseInt(wordIndex, 10), clueIndex);
          }
        } catch (e) {
          console.error("Error parsing clues data:", e);
        }
      });
    });

    // Add click handler for the eye icon (reveal word)
    const eyeIcon = clue.querySelector(".clue-eye");
    if (eyeIcon) {
      eyeIcon.addEventListener("click", (event) => {
        // Stop propagation to prevent triggering the clue highlight
        event.stopPropagation();

        // Make sure letter selection is complete
        if (isInitPhase() || !isSelectionComplete()) {
          showToast("Please select 1 vowel and 2 consonants first", "error");
          return;
        }

        // Get the word before we reveal it
        const wordObj = getCurrentWords()[parseInt(wordIndex, 10)];

        // Reveal the word using our game state function
        const result = revealWord(parseInt(wordIndex, 10));

        if (result.success) {
          // Animate the clue tumbling down
          if (wordObj && wordObj.word) {
            animateClueForWord(wordObj.word);
          }

          // Update the UI to reflect the revealed word
          renderParagraph(getChosenVowel());
          renderClues();
          updateScore(); // This now also updates chain links
          updateLetterCounts();

          if (result.gameComplete) {
            showGameOver(true);
          } else {
            // Show toast notification only when game isn't over
            showToast(
              `Word revealed for ${result.pointsDeducted} link penalty`,
              "info"
            );
          }
        }
      });
    }
  });

  /**
   * Helper function to highlight corresponding elements
   * @param {string} clueIndex - The index of the clue/word pair to highlight
   * @param {boolean} highlight - Whether to add or remove highlight
   */
  const highlightPair = (clueIndex, highlight) => {
    // Make sure letter selection is complete
    if (isInitPhase() || !isSelectionComplete()) {
      return;
    }

    // Find the clue and all instances of its word
    const clue = document.querySelector(
      `#clues-list li[data-clue-index="${clueIndex}"]`
    );
    // Get the word index from the clue
    const wordIndex = clue ? clue.getAttribute("data-word-index") : null;

    // Find all instances of the word using the word index instead of clue index
    const wordInstances = wordIndex
      ? document.querySelectorAll(
          `[data-masked="true"][data-clue-index="${wordIndex}"]`
        )
      : [];

    if (clue && wordInstances.length > 0) {
      // Remove any existing highlights
      if (highlight) {
        document
          .querySelectorAll(".highlight")
          .forEach((el) => el.classList.remove("highlight"));
      }

      // Add highlight to both the clue and all word instances
      requestAnimationFrame(() => {
        clue.classList.toggle("highlight", highlight);
        wordInstances.forEach((word) =>
          word.classList.toggle("highlight", highlight)
        );
      });
    }
  };

  // Set up hover effects on clues
  visibleClues.forEach((clue) => {
    const clueIndex = clue.getAttribute("data-clue-index");
    const wordIndex = clue.getAttribute("data-word-index");

    if (clueIndex && wordIndex) {
      clue.addEventListener("mouseenter", () => highlightPair(clueIndex, true));
      clue.addEventListener("mouseleave", () =>
        highlightPair(clueIndex, false)
      );

      clue.addEventListener("click", () => {
        // Make sure letter selection is complete
        if (isInitPhase() || !isSelectionComplete()) {
          showToast("Please select 1 vowel and 2 consonants first", "error");
          return;
        }

        const firstWord = document.querySelector(
          `[data-masked="true"][data-clue-index="${wordIndex}"]`
        );
        if (firstWord) {
          firstWord.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      });
    }
  });

  // Set up hover effects on words
  const maskedWords = document.querySelectorAll('[data-masked="true"]');
  maskedWords.forEach((word) => {
    const wordIndex = word.getAttribute("data-clue-index");

    if (wordIndex) {
      // Find the corresponding clue (if it's visible)
      const clue = document.querySelector(
        `#clues-list li[data-word-index="${wordIndex}"]`
      );

      if (clue) {
        const clueIndex = clue.getAttribute("data-clue-index");

        word.addEventListener("mouseenter", () =>
          highlightPair(clueIndex, true)
        );
        word.addEventListener("mouseleave", () =>
          highlightPair(clueIndex, false)
        );

        word.addEventListener("click", () => {
          // Make sure letter selection is complete
          if (isInitPhase() || !isSelectionComplete()) {
            showToast("Please select 1 vowel and 2 consonants first", "error");
            return;
          }

          if (clue) {
            clue.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        });
      }
    }
  });
}

/**
 * Renders the clues list for hidden words with progressive revealing
 * Separates active and solved clues with a tumble-down animation
 */
export function renderClues() {
  // First check if the parent container exists
  const cluesContainer = document.getElementById("clues-container");
  if (!cluesContainer) {
    console.error("clues-container element not found");
    return;
  }

  let cluesList = document.getElementById("clues-list");
  if (!cluesList) {
    // Create the clues-list if it doesn't exist
    cluesList = document.createElement("ul");
    cluesList.id = "clues-list";
    cluesContainer.appendChild(cluesList);
  }

  cluesList.innerHTML = "";

  // Create containers for active and solved clues
  const activeCluesContainer = document.createElement("div");
  activeCluesContainer.className = "active-clues-container";

  const solvedCluesContainer = document.createElement("div");
  solvedCluesContainer.className = "solved-clues-container";

  // Add a heading for the solved clues section
  const solvedHeading = document.createElement("div");
  solvedHeading.className = "solved-clues-heading";
  solvedHeading.textContent = "Solved Clues";
  solvedCluesContainer.appendChild(solvedHeading);

  // Get visible clues based on attempts made
  const words = getCurrentWords();
  let clueIndex = 0;

  // Get indices of words whose clues should be shown
  const shownWordIndices = getShownWordIndices();

  // Counters for active and solved clues
  let activeClueCount = 0;
  let solvedClueCount = 0;

  // Display clues for each word
  words.forEach((gameWord, wordIndex) => {
    const { word, found, revealed, clues } = gameWord;

    // Show clue if the word is found OR revealed OR if it's in the list of shown word indices
    const shouldShowClue =
      found || revealed || shownWordIndices.includes(wordIndex);

    if (shouldShowClue && Array.isArray(clues) && clues.length > 0) {
      const li = document.createElement("li");
      let statusMark = "";

      if (found) {
        statusMark = "✓"; // Checkmark for found words
      } else if (revealed) {
        statusMark = "⚠️"; // Warning symbol for revealed words
      }

      // Get the active clue index from the game state
      const activeClueIndex = getActiveClueIndex(wordIndex);
      const activeClue = clues[activeClueIndex]?.clue || clues[0]?.clue || "";
      const cluePoints =
        clues[activeClueIndex]?.points || clues[0]?.points || 0;

      // Create a container for clue text and icons
      // Show all revealed clues (from index 0 up to activeClueIndex), not just the current one
      const clueTextSpan = document.createElement("span");
      clueTextSpan.className = "clue-text";
      if (activeClueIndex === 0) {
        clueTextSpan.textContent = `${activeClue} (${word.length})`;
      } else {
        // Build stacked display: each revealed clue on its own line
        clueTextSpan.innerHTML = "";
        for (let ci = 0; ci <= activeClueIndex; ci++) {
          const clueEntry = document.createElement("span");
          clueEntry.className = `clue-line clue-line-${ci}${ci === activeClueIndex ? " clue-line-current" : ""}`;
          clueEntry.textContent = ci === activeClueIndex
            ? `${clues[ci]?.clue || ""} (${word.length})`
            : clues[ci]?.clue || "";
          clueTextSpan.appendChild(clueEntry);
        }
      }

      // Create a container for all icons
      const iconsContainer = document.createElement("span");
      iconsContainer.className = "clue-icons";

      // Only show icons if word is not found and not revealed
      if (!found && !revealed) {
        // Create icons for each clue type (difficulty level)
        // Get the lowest clue index seen to determine which clues are available at full points
        const lowestClueIndexSeen = getLowestClueIndexSeen(wordIndex);

        // Icon 1: Hard/Indirect clue
        const indirectIcon = document.createElement("span");
        indirectIcon.className = `clue-icon clue-icon-hard ${
          activeClueIndex === 0 ? "active" : ""
        }`;
        // Add a class if this clue is no longer available at full points
        if (lowestClueIndexSeen > 0) {
          indirectIcon.classList.add("reduced-points");
        }
        indirectIcon.innerHTML = '<i class="fa fa-lock"></i>';

        // Update title to show if points are reduced
        const cluePoints = clues[0]?.points || 0;
        const actualPoints =
          lowestClueIndexSeen > 0
            ? clues[lowestClueIndexSeen]?.points || 0
            : cluePoints;
        indirectIcon.title =
          lowestClueIndexSeen > 0
            ? `Indirect Clue. Worth: ${actualPoints} links (reduced from ${cluePoints})`
            : `Indirect Clue. Worth: ${cluePoints} links`;
        indirectIcon.setAttribute("data-clue-index", "0");
        iconsContainer.appendChild(indirectIcon);

        // Only show medium and easy clues if there are more than 1 clue
        if (clues.length > 1) {
          // Icon 2: Medium/Suggestive clue
          const suggestiveIcon = document.createElement("span");
          suggestiveIcon.className = `clue-icon clue-icon-medium ${
            activeClueIndex === 1 ? "active" : ""
          }`;
          suggestiveIcon.innerHTML = '<i class="fa fa-unlock-alt"></i>';
          suggestiveIcon.title = `Suggestive Clue. Worth: ${clues[1]?.points || 0} links`;
          suggestiveIcon.setAttribute("data-clue-index", "1");
          iconsContainer.appendChild(suggestiveIcon);
        }

        // Only show easy clue if there are at least 3 clues
        if (clues.length > 2) {
          // Icon 3: Easy/Straight clue
          const straightIcon = document.createElement("span");
          straightIcon.className = `clue-icon clue-icon-easy ${
            activeClueIndex === 2 ? "active" : ""
          }`;
          straightIcon.innerHTML = '<i class="fa fa-unlock"></i>';
          straightIcon.title = `Straight Clue. Worth: ${clues[2]?.points || 0} links`;
          straightIcon.setAttribute("data-clue-index", "2");
          iconsContainer.appendChild(straightIcon);
        }

        // Add eye icon for revealing the word
        const eyeIcon = document.createElement("span");
        eyeIcon.className = "clue-eye";
        eyeIcon.innerHTML = '<i class="fa fa-eye"></i>';
        eyeIcon.title = `Reveal Word. Costs: ${getGameParameters()?.marketplace?.wordReveal?.cost ?? 8} links`;
        iconsContainer.appendChild(eyeIcon);
      } else if (statusMark) {
        // If the word is found or revealed, append the status mark to the clue text
        clueTextSpan.textContent = `${activeClue} (${word.length}) ${statusMark}`;
      }

      li.appendChild(clueTextSpan);
      li.appendChild(iconsContainer);

      // Add class if the word is found
      if (found) {
        li.classList.add("found");
      } else if (revealed) {
        li.classList.add("revealed");
      }

      // Set data attributes to track word and clue
      li.setAttribute("data-word", word);
      li.setAttribute("data-word-index", wordIndex.toString());
      li.setAttribute("data-clue-index", wordIndex.toString());
      li.setAttribute("data-active-clue", activeClueIndex.toString());
      li.setAttribute("data-visible", "true");

      // Store clue data as JSON in a data attribute for reference
      li.setAttribute("data-clues", JSON.stringify(clues));

      // Add to appropriate container
      if (found || revealed) {
        solvedCluesContainer.appendChild(li);
        solvedClueCount++;
      } else {
        activeCluesContainer.appendChild(li);
        activeClueCount++;
      }

      clueIndex++;
    }
  });

  // Add the containers to the main clues list
  cluesList.appendChild(activeCluesContainer);

  // Only add solved container if there are solved clues
  if (solvedClueCount > 0) {
    cluesList.appendChild(solvedCluesContainer);
  }

  // Always scroll to the top to show active clues first
  const cluesSection = document.getElementById("clues-section");
  if (cluesSection) {
    cluesSection.scrollTop = 0;
  }

  // Also scroll the clues container itself if it has its own scroll
  if (cluesContainer) {
    cluesContainer.scrollTop = 0;
  }

  // Set up hover interactions
  setupClueInteractions();
}

/**
 * Creates and updates the chain links progress indicator
 */
export function updateChainLinks() {
  const chainLinksContainer = document.getElementById("chain-links");
  if (!chainLinksContainer) return;

  // Get the current words and calculate progress
  const words = getCurrentWords();
  const totalWords = words.length;

  // If no words or container not ready, exit
  if (totalWords === 0) return;

  // Count found and revealed words
  const foundWords = words.filter((word) => word.found).length;
  const revealedWords = words.filter(
    (word) => !word.found && word.revealed
  ).length;

  // Clear existing content if number of links doesn't match
  if (chainLinksContainer.children.length !== totalWords) {
    chainLinksContainer.innerHTML = "";

    // Create all chain links (active and inactive)
    for (let i = 0; i < totalWords; i++) {
      const chainLink = document.createElement("div");
      chainLink.className = "chain-link inactive";

      // Chain links will be displayed in a simple straight line
      chainLink.textContent = "🔗";

      chainLink.innerHTML = '<i class="fas fa-link"></i>';
      chainLink.setAttribute("data-index", i.toString());
      chainLink.setAttribute("title", `Word ${i + 1} of ${totalWords}`);
      chainLinksContainer.appendChild(chainLink);
    }
  }

  // Now update the status of each link
  const chainLinks = chainLinksContainer.querySelectorAll(".chain-link");

  // Update each link based on the corresponding word's status
  words.forEach((word, index) => {
    const chainLink = chainLinks[index];
    if (!chainLink) return;

    // Set appropriate class based on word status
    if (word.found) {
      // Word was found by player
      if (!chainLink.classList.contains("active")) {
        chainLink.classList.remove("inactive", "revealed");
        chainLink.classList.add("active");

        // Apply scaling for active links
        chainLink.style.transform = `scale(1.2)`;

        // Add animation class if this is a newly found word
        if (!animatedChainLinks.has(index)) {
          chainLink.classList.add("chain-link-new");
          animatedChainLinks.set(index, true);

          // Remove animation class after animation completes
          setTimeout(() => {
            chainLink.classList.remove("chain-link-new");
          }, 800);
        }
      }
      chainLink.setAttribute("title", `Word ${index + 1} found!`);
    } else if (word.revealed) {
      // Word was revealed by player
      if (!chainLink.classList.contains("revealed")) {
        chainLink.classList.remove("inactive", "active");
        chainLink.classList.add("revealed");

        // Apply scaling for revealed links
        chainLink.style.transform = `scale(1.1)`;

        // Add animation class if this is a newly revealed word
        if (!animatedChainLinks.has(index)) {
          chainLink.classList.add("chain-link-new");
          animatedChainLinks.set(index, true);

          // Remove animation class after animation completes
          setTimeout(() => {
            chainLink.classList.remove("chain-link-new");
          }, 800);
        }
      }
      chainLink.setAttribute("title", `Word ${index + 1} revealed`);
    } else {
      // Word is still hidden
      chainLink.classList.remove("active", "revealed");
      chainLink.classList.add("inactive");

      // Reset transform for inactive links
      chainLink.style.transform = ``;

      chainLink.setAttribute("title", `Word ${index + 1} of ${totalWords}`);
    }
  });
}

/**
 * Updates the score display with current and max scores
 */
export function updateScore() {
  // Update current score
  updateElement(
    "score-value",
    (el) => (el.textContent = getCurrentScore().toString())
  );

  // Update max score
  updateElement(
    "max-score-value",
    (el) => (el.textContent = getMaxScore().toString())
  );

  // Also update chain links whenever score is updated
  updateChainLinks();
  // Keep golden buttons in sync with game state
  renderGoldenActions();
}

/**
 * Displays the game over message with final score and celebration animations
 */
export async function showGameOver(lastWordRevealed = false) {
  const score = getCurrentScore();
  const maxScore = getMaxScore();
  const scorePercentage = Math.round((score / maxScore) * 100);

  const input = document.getElementById("guess-input");
  if (input && input instanceof HTMLInputElement) {
    input.disabled = true;
    input.placeholder = "Game Complete!";
  }

  // Record game completion for authenticated users
  if (window.authManager && window.authManager.isAuthenticated() && window.streakTracker) {
    try {
      const currentParagraph = getCurrentParagraph();
      const currentWords = getCurrentWords();
      
      const gameData = {
        score: score,
        maxPossibleScore: maxScore,
        wordsFound: currentWords.filter(w => w.found).length,
        totalWords: currentWords.length,
        gameDate: currentParagraph ? `${new Date().getFullYear()}-${currentParagraph.date}` : new Date().toISOString().split('T')[0],
        completionTime: null, // Could be tracked if needed
        metadata: {
          percentage: scorePercentage,
          paragraphId: currentParagraph ? currentParagraph.id : null,
          paragraphTitle: currentParagraph ? currentParagraph.title : null
        }
      };

      const result = await window.streakTracker.recordGameCompletion(gameData);

      if (result.success) {
        console.log('✅ Game completion recorded successfully');

        // Update streak display in UI
        const streakResult = await window.streakTracker.getCurrentStreak();
        if (streakResult.success && window.authUI) {
          window.authUI.updateStreakDisplay(streakResult.streak.current_streak || 0);
        }

        // Refresh the calendar play history to show the updated dot
        if (window.loadPlayHistory) {
          await window.loadPlayHistory();
          console.log('✅ Calendar play history refreshed');
        }
      } else {
        console.warn('⚠️ Failed to record game completion:', result.error);
      }
    } catch (error) {
      console.error('❌ Error recording game completion:', error);
    }
  }

  const assistedPlay = gameState.current.assistedPlay;
  const assistedBadge = assistedPlay
    ? `<div><span class="assisted-badge">&#x1F5DD;&#xFE0F; Assisted play</span></div>`
    : "";

  const endGameMessage = document.createElement("div");
  endGameMessage.className = "game-over-message";
  endGameMessage.innerHTML = lastWordRevealed
    ? `
        <h2>Chain Complete 🔓</h2>
        <p>Final Score: <span class="final-score">${score}</span> <span class="max-score">(Max Possible: ${maxScore})</span> - ${scorePercentage}%</p>
        ${assistedBadge}
    `
    : `
        <h2>Chain Complete! 🎉</h2>
        <p>You've linked every word in the paragraph!</p>
        <p>Final Score: <span class="final-score">${score}</span> <span class="max-score">(Max Possible: ${maxScore})</span> - ${scorePercentage}%</p>
        ${assistedBadge}
    `;

  updateElement("paragraph-container", (el) =>
    el.insertAdjacentElement("afterend", endGameMessage)
  );

  // Start the celebration animations
  setTimeout(() => {
    if (lastWordRevealed) {
      celebrateRevealGameOver();
    } else {
      celebrateGameOver();
    }
  }, 300);
}

/**
 * Shows a notification message (replaces old toast system)
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, info, warning)
 * @param {number} duration - Duration in milliseconds (unused for persistent notifications)
 */
export function showToast(message, type = "info", duration = 3000) {
  // Use the new notification system instead of toasts
  addNotification(message, type, true);
}

/**
 * Updates the letter tile counts in the marketplace
 * @param {boolean} showCounts - Whether to show counts or hide them
 */
export function updateLetterCounts(showCounts = true) {
  // Update the letters display with remaining counts
  const letterTiles = document.querySelectorAll(".letter-tile");
  const letterCounts = getLetterCounts();

  // Get selected letters to ensure they stay blue even when count is zero
  const selectedVowel = getSelectedVowel();
  const selectedConsonants = getSelectedConsonants();
  const selectedLetters = new Set(
    [selectedVowel, ...selectedConsonants].filter(Boolean)
  );

  // Get per-instance rates from parameters for tooltips
  const params = getGameParameters();
  const vowelRate = params?.marketplace?.vowel?.costPerInstance ?? 2;
  const consonantRate = params?.marketplace?.consonant?.costPerInstance ?? 3;

  letterTiles.forEach((tile) => {
    const letter = tile.getAttribute("data-letter");
    if (!letter) return;

    // Find the count span
    const countSpan = tile.querySelector(".count");
    if (!countSpan) return;

    // Get the count for this letter
    const count = letterCounts[letter] || 0;

    // Update the count display based on showCounts parameter
    if (showCounts) {
      // Only show non-zero counts
      countSpan.textContent = count > 0 ? count.toString() : "";

      // Style the tile based on count and selection status
      if (
        count === 0 &&
        !selectedLetters.has(letter) &&
        !tile.classList.contains("purchased")
      ) {
        // Gray out tiles with zero count (unless they're selected initial letters)
        tile.classList.add("empty");
        tile.removeAttribute("title");
      } else {
        tile.classList.remove("empty");
        // Set tooltip for in-play letters
        if (!tile.classList.contains("purchased")) {
          const isVowel = VOWELS.includes(letter.toLowerCase());
          const rate = isVowel ? vowelRate : consonantRate;
          const totalCost = count * rate;
          tile.title = `Reveal cost: ${totalCost} links (${count}×${rate})`;
        }
      }
    } else {
      // Hide all counts in initial selection phase
      countSpan.textContent = "";
      // Don't apply empty styling during initial phase
      tile.classList.remove("empty");
      tile.removeAttribute("title");
    }
  });
}

/**
 * Sets up the marketplace interactions including letter selection
 */
const VOWELS = ["a", "e", "i", "o", "u"];

/**
 * Applies visual highlighting to letter tiles based on current selection phase.
 * Step 1 (no vowel yet): vowels highlighted, consonants dimmed.
 * Step 2 (vowel chosen, need consonants): consonants highlighted, vowels dimmed.
 * Step 3 (complete): all phase classes removed.
 */
function applySelectionPhaseStyles() {
  if (!isInitPhase() || isSelectionComplete()) {
    // Remove all phase classes once selection is done
    document.querySelectorAll(".letter-tile").forEach((t) => {
      t.classList.remove("vowel-enabled", "consonant-enabled", "phase-disabled");
    });
    const resetBtn = document.getElementById("reset-selection");
    if (resetBtn) resetBtn.style.display = "none";
    return;
  }

  const vowelChosen = !!getSelectedVowel();
  const resetBtn = document.getElementById("reset-selection");

  document.querySelectorAll(".letter-tile").forEach((t) => {
    const letter = t.getAttribute("data-letter");
    if (!letter) return;
    const isVowel = VOWELS.includes(letter.toLowerCase());

    t.classList.remove("vowel-enabled", "consonant-enabled", "phase-disabled");

    if (!vowelChosen) {
      // Step 1: highlight vowels, dim consonants
      if (isVowel) {
        t.classList.add("vowel-enabled");
      } else {
        t.classList.add("phase-disabled");
      }
    } else {
      // Step 2: highlight consonants, dim vowels (unless already selected)
      if (!isVowel && !t.classList.contains("selected")) {
        t.classList.add("consonant-enabled");
      } else if (isVowel && !t.classList.contains("selected")) {
        t.classList.add("phase-disabled");
      }
    }
  });

  if (resetBtn) resetBtn.style.display = vowelChosen ? "block" : "none";
}

export function setupMarketplace() {
  // Set up letter selection in the marketplace
  const letterTiles = document.querySelectorAll(".letter-tile");

  letterTiles.forEach((tile) => {
    const letter = tile.getAttribute("data-letter");
    if (!letter) return;

    const isVowel = VOWELS.includes(letter.toLowerCase());

    // Clear any existing event listeners by cloning and replacing
    const newTile = tile.cloneNode(true);
    tile.parentNode.replaceChild(newTile, tile);

    // Add click event to the new tile
    newTile.addEventListener("click", () => {
      // Check if we're in the initialization phase
      if (isInitPhase()) {
        // In initialization phase, handle letter selection
        handleLetterSelection(newTile, isVowel);
      } else {
        // In regular gameplay, handle letter purchases
        handleLetterPurchase(newTile, isVowel);
      }
    });
  });

  // Apply initial phase styles
  applySelectionPhaseStyles();

  // Wire up reset button (clone to clear old listeners)
  const resetBtn = document.getElementById("reset-selection");
  if (resetBtn) {
    const newBtn = resetBtn.cloneNode(true);
    resetBtn.parentNode.replaceChild(newBtn, resetBtn);
    newBtn.addEventListener("click", () => {
      if (!isInitPhase() || isSelectionComplete()) return;

      // Deselect vowel
      const currentVowel = getSelectedVowel();
      if (currentVowel) {
        const vowelTile = document.querySelector(`.letter-tile[data-letter="${currentVowel}"]`);
        if (vowelTile) vowelTile.classList.remove("selected");
        setSelectedVowel("");
      }

      // Deselect consonants
      getSelectedConsonants().forEach((c) => {
        const cTile = document.querySelector(`.letter-tile[data-letter="${c}"]`);
        if (cTile) cTile.classList.remove("selected");
      });
      clearSelectedConsonants();

      updateSelectionStatus("", []);
      applySelectionPhaseStyles();
    });
  }
}

/**
 * Handles letter selection during the initial phase
 * @param {HTMLElement} tile - The letter tile element
 * @param {boolean} isVowel - Whether the letter is a vowel
 */
function handleLetterSelection(tile, isVowel) {
  const letter = tile.getAttribute("data-letter");
  if (!letter) return;

  // If selection is already complete, ignore clicks
  if (isSelectionComplete()) {
    showToast("Letter selection is already complete", "info");
    return;
  }

  if (isVowel) {
    // Handle vowel selection
    const currentVowel = getSelectedVowel();

    // If a vowel is already selected, deselect it first
    if (currentVowel) {
      // Find and deselect the current vowel tile
      const currentVowelTile = document.querySelector(
        `.letter-tile[data-letter="${currentVowel}"]`
      );
      if (currentVowelTile) {
        currentVowelTile.classList.remove("selected");
      }
    }

    // Select this vowel
    setSelectedVowel(letter);
    tile.classList.add("selected");

    // Update the vowel display
    updateSelectedVowelDisplay(letter);

    // Advance to consonant-selection phase
    applySelectionPhaseStyles();
  } else {
    // Handle consonant selection
    const currentConsonants = getSelectedConsonants();

    // Check if this consonant is already selected
    if (currentConsonants.includes(letter)) {
      // Already selected, ignore
      return;
    }

    // Check if we already have 2 consonants selected
    if (currentConsonants.length >= 2) {
      showToast("You can only select 2 consonants", "error");
      return;
    }

    // Add this consonant to selection
    addSelectedConsonant(letter);
    tile.classList.add("selected");

    // Update the consonants display
    updateSelectedConsonantsDisplay();
  }

  // Check if selection is now complete
  checkSelectionComplete();
}

/**
 * Updates the display of the selected vowel
 * @param {string} vowel - The selected vowel
 */
function updateSelectedVowelDisplay(vowel) {
  // Update legacy display for backward compatibility
  const vowelDisplay = document.getElementById("selected-vowel");
  if (vowelDisplay) {
    vowelDisplay.textContent = vowel.toUpperCase();
  }
  
  // Update notification system
  updateSelectionStatus(vowel, getSelectedConsonants());
}

/**
 * Updates the display of selected consonants
 */
function updateSelectedConsonantsDisplay() {
  // Update legacy display for backward compatibility
  const consonantsDisplay = document.getElementById("selected-consonants");
  if (consonantsDisplay) {
    const selectedConsonants = getSelectedConsonants();

    // Create display text with placeholders for unselected consonants
    let displayText = "";
    for (let i = 0; i < 2; i++) {
      if (i > 0) displayText += " ";
      displayText +=
        i < selectedConsonants.length ? selectedConsonants[i].toUpperCase() : "-";
    }

    consonantsDisplay.textContent = displayText;
  }
  
  // Update notification system
  updateSelectionStatus(getSelectedVowel(), getSelectedConsonants());
}

/**
 * Checks if letter selection is complete and finalizes if it is
 */
function checkSelectionComplete() {
  const vowel = getSelectedVowel();
  const consonants = getSelectedConsonants();

  if (vowel && consonants.length === 2) {
    // Selection is complete, finalize
    completeLetterSelection();
    applySelectionPhaseStyles(); // Removes all phase highlight classes

    // Show notification
    addNotification(
      `Selection complete: ${vowel.toUpperCase()}, ${consonants[0].toUpperCase()}, ${consonants[1].toUpperCase()}`,
      "success"
    );

    // Enable the clues container
    const cluesContainer = document.getElementById("clues-container");
    if (cluesContainer) {
      cluesContainer.classList.remove("disabled-clues");
    }

    // Initialize the game with the selected letters
    revealSelectedLetters();

    // Show initial clues now that selection is complete
    showInitialCluesAfterSelection();

    // Update the UI to reflect the revealed letters
    renderParagraph(getChosenVowel());
    renderClues();
    updateLetterCounts(true);
    updateScore();

    // Enable the input field and submit button
    updateInputState();
  }
}

/**
 * Shows a confirmation modal before a letter purchase.
 * Calls onConfirm() if the player proceeds.
 */
function showPurchaseConfirmModal(letter, count, cost, onConfirm) {
  let modal = document.getElementById("purchase-confirm-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "purchase-confirm-modal";
    modal.className = "modal-container";
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-content" style="max-width:340px;text-align:center;">
      <div class="modal-header">
        <h2>Reveal Letter?</h2>
        <button class="close-button" id="purchase-modal-close">&times;</button>
      </div>
      <div class="modal-body">
        <p style="font-size:2rem;font-weight:bold;margin:0.25rem 0;">
          ${letter.toUpperCase()}
        </p>
        <p style="margin:0.5rem 0 1rem;">
          Revealing <strong>${count}</strong> instance${count !== 1 ? "s" : ""}
          will cost <strong>${cost} link${cost !== 1 ? "s" : ""}</strong>
        </p>
        <div style="display:flex;gap:0.75rem;justify-content:center;">
          <button id="purchase-cancel-btn"
            style="padding:0.5rem 1.25rem;border-radius:6px;border:2px solid #4a90e2;
                   background:#fff;color:#4a90e2;cursor:pointer;font-size:0.95rem;font-weight:bold;">
            Cancel
          </button>
          <button id="purchase-confirm-btn"
            style="padding:0.5rem 1.25rem;border-radius:6px;border:none;
                   background:#4a90e2;color:#fff;cursor:pointer;font-size:0.95rem;font-weight:bold;">
            Buy
          </button>
        </div>
      </div>
    </div>
  `;

  modal.classList.add("show");

  const close = () => {
    modal.classList.remove("show");
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };

  modal.querySelector("#purchase-modal-close").addEventListener("click", close);
  modal.querySelector("#purchase-cancel-btn").addEventListener("click", close);
  modal.querySelector("#purchase-confirm-btn").addEventListener("click", () => {
    close();
    onConfirm();
  });
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  document.addEventListener("keydown", onKey);
}

/**
 * Handles letter purchase during regular gameplay
 * @param {HTMLElement} tile - The letter tile element
 * @param {boolean} isVowel - Whether the letter is a vowel
 */
function handleLetterPurchase(tile, isVowel) {
  // Ignore if initialization phase is not complete
  if (!isSelectionComplete()) {
    showToast("Please complete letter selection first", "error");
    return;
  }

  const letter = tile.getAttribute("data-letter");
  if (!letter) return;

  // Check if the tile is already purchased/disabled
  if (
    tile.classList.contains("purchased") ||
    tile.classList.contains("disabled")
  ) {
    return;
  }

  // Get the count for this letter
  const countSpan = tile.querySelector(".count");
  const count = countSpan ? parseInt(countSpan.textContent || "0", 10) : 0;

  // Only allow purchase if there are occurrences to reveal
  if (count <= 0) {
    showToast("No more instances of this letter to reveal", "info");
    return;
  }

  // Calculate cost to show in confirmation
  const params = getGameParameters();
  const ratePerInstance = isVowel
    ? (params?.marketplace?.vowel?.costPerInstance ?? 2)
    : (params?.marketplace?.consonant?.costPerInstance ?? 3);
  const totalCost = count * ratePerInstance;

  // Show confirmation modal before committing the purchase
  showPurchaseConfirmModal(letter, count, totalCost, () => {
    let result;
    if (isVowel) {
      result = purchaseVowel(letter);
    } else {
      result = purchaseConsonant(letter);
    }

    if (result.success) {
      tile.classList.add("purchased");
      renderParagraph(getChosenVowel());
      updateLetterCounts();
      updateScore();
      showToast(
        `Revealed ${count} instance${
          count !== 1 ? "s" : ""
        } of "${letter.toUpperCase()}" for ${result.cost} links`,
        "success"
      );
    } else {
      showToast(
        result.message || "Not enough links to purchase this letter",
        "error"
      );
    }
  });
}

/**
 * Resets the UI to its initial state
 */
export function resetUI() {
  // Force complete cleanup of all UI state
  console.log("Performing complete UI reset");

  // Reset vowel tiles
  document
    .querySelectorAll(".vowel-tile")
    .forEach((btn) => btn.classList.remove("disabled"));

  // Reset letter tiles in keyboard/marketplace
  document.querySelectorAll(".letter-tile").forEach((tile) => {
    // Remove all possible state classes
    tile.classList.remove("disabled");
    tile.classList.remove("purchased");
    tile.classList.remove("selected");

    // Clear any counts
    const countSpan = tile.querySelector(".count");
    if (countSpan) {
      countSpan.textContent = "";
    }
  });

  // Reset notification panel
  clearNotifications();
  
  // Reset initial message flag and show initial message
  initialMessageShown = false;
  showInitialMessage();

  // Reset selected letter displays (for backward compatibility)
  const vowelDisplay = document.getElementById("selected-vowel");
  if (vowelDisplay) {
    vowelDisplay.textContent = "-";
  }

  const consonantsDisplay = document.getElementById("selected-consonants");
  if (consonantsDisplay) {
    consonantsDisplay.textContent = "- -";
  }

  // Clear clues list
  const cluesList = document.getElementById("clues-list");
  if (cluesList) {
    cluesList.innerHTML = "";
  }

  // Reset paragraph container
  const paragraphContainer = document.getElementById("paragraph-container");
  if (paragraphContainer) {
    paragraphContainer.innerHTML = "";
  }

  // Enable the input field and reset its state
  const input = document.getElementById("guess-input");
  if (input && input instanceof HTMLInputElement) {
    input.disabled = false;
    input.value = "";
    input.placeholder = "Enter your guess...";
    input.classList.remove("correct", "wrong");
  }

  // Remove any game over message
  const gameOverMessage = document.querySelector(".game-over-message");
  if (gameOverMessage) {
    gameOverMessage.remove();
  }

  // Remove any toast messages
  const toast = document.querySelector(".toast");
  if (toast) {
    toast.remove();
  }

  // Reset chain links
  const chainLinksContainer = document.getElementById("chain-links");
  if (chainLinksContainer) {
    chainLinksContainer.innerHTML = "";
  }

  // Clear animation tracking maps
  animatingClues.clear();
  animatedChainLinks.clear();
}

// ─── Golden Key & Golden Coin UI ─────────────────────────────────────────────

/**
 * Updates the golden action buttons to reflect used/available state.
 * Called automatically from updateScore().
 */
export function renderGoldenActions() {
  const keyBtn = document.getElementById("golden-key-btn");
  const coinBtn = document.getElementById("golden-coin-btn");
  if (!keyBtn || !coinBtn) return;

  const keyUsed = gameState.current.goldenKeyUsed;
  const coinUsed = gameState.current.goldenCoinUsed;

  if (keyUsed) {
    keyBtn.disabled = true;
    keyBtn.classList.add("used");
  } else {
    keyBtn.disabled = false;
    keyBtn.classList.remove("used");
  }

  if (coinUsed) {
    coinBtn.disabled = true;
    coinBtn.classList.add("used");
  } else {
    coinBtn.disabled = false;
    coinBtn.classList.remove("used");
  }
}

/**
 * Handles the Golden Key button click.
 * If there are hidden clues, reveals the next one.
 * If all clues are visible, shows a word picker to upgrade one clue tier.
 */
export function handleGoldenKey() {
  if (gameState.current.goldenKeyUsed) return;

  const mode = getGoldenKeyMode();

  if (mode === "reveal") {
    const result = useGoldenKey();
    if (result.success) {
      renderClues();
      renderGoldenActions();
      addNotification("Golden Key used: a new clue has been revealed!", "success");
    }
    return;
  }

  // Upgrade mode: show word picker
  const words = gameState.current.words;
  const eligibleWords = words
    .map((w, i) => ({ w, i }))
    .filter(({ w }) => {
      if (w.found || w.revealed) return false;
      if (!w.clues || !Array.isArray(w.clues)) return false;
      return (w.activeClueIndex || 0) + 1 < w.clues.length;
    });

  if (eligibleWords.length === 0) {
    addNotification("No clues can be upgraded further.", "info");
    return;
  }

  showGoldenKeyPicker(eligibleWords);
}

/**
 * Shows an inline picker to let the player choose which word's clue to upgrade.
 * @param {Array<{w: Object, i: number}>} eligibleWords
 */
function showGoldenKeyPicker(eligibleWords) {
  let modal = document.getElementById("golden-key-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "golden-key-modal";
    modal.className = "modal-container";
    document.body.appendChild(modal);
  }

  const tierNames = ["indirect", "suggestive", "straight"];

  const optionsHTML = eligibleWords.map(({ w, i }) => {
    const currentTier = w.activeClueIndex || 0;
    const nextTier = currentTier + 1;
    const fromLabel = tierNames[currentTier] || `tier ${currentTier}`;
    const toLabel = tierNames[nextTier] || `tier ${nextTier}`;
    const clueText = w.clues[currentTier]?.clue || "";
    return `<button class="golden-key-option" data-word-index="${i}"
      style="display:block;width:100%;margin:0.4rem 0;padding:0.5rem 0.75rem;
             border-radius:6px;border:2px solid #b8860b;background:#fffbe6;
             color:#333;cursor:pointer;font-size:0.95rem;text-align:left;">
      "${clueText}"
      <span style="font-size:0.8rem;color:#888;display:block;">${fromLabel} → ${toLabel}</span>
    </button>`;
  }).join("");

  modal.innerHTML = `
    <div class="modal-content" style="max-width:360px;">
      <div class="modal-header">
        <h2>&#x1F5DD;&#xFE0F; Upgrade a Clue</h2>
        <button class="close-button" id="golden-key-modal-close">&times;</button>
      </div>
      <div class="modal-body">
        <p style="margin:0 0 0.75rem;">Choose a word to upgrade its clue to the next tier (no score penalty):</p>
        ${optionsHTML}
      </div>
    </div>
  `;

  modal.classList.add("show");

  const close = () => {
    modal.classList.remove("show");
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  modal.querySelector("#golden-key-modal-close").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  document.addEventListener("keydown", onKey);

  modal.querySelectorAll(".golden-key-option").forEach(btn => {
    btn.addEventListener("click", () => {
      const wordIndex = parseInt(btn.getAttribute("data-word-index"), 10);
      close();
      const result = useGoldenKey(wordIndex);
      if (result.success) {
        renderClues();
        renderGoldenActions();
        addNotification("Golden Key used: a clue has been upgraded!", "success");
      }
    });
  });
}

/**
 * Handles the Golden Coin button click.
 * Shows eligible rare letters and lets the player pick one to reveal for 3 links.
 */
export function handleGoldenCoin() {
  if (gameState.current.goldenCoinUsed) return;

  const eligible = getEligibleCoinLetters();
  if (eligible.length === 0) {
    addNotification("No rare letters left to reveal.", "info");
    return;
  }

  const params = gameState.current; // just for cost
  const cost = (gameState.config?.parameters?.golden?.coin?.cost) ?? 3;

  let modal = document.getElementById("golden-coin-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "golden-coin-modal";
    modal.className = "modal-container";
    document.body.appendChild(modal);
  }

  const optionsHTML = eligible.map(({ letter, count }) =>
    `<button class="golden-coin-option" data-letter="${letter}"
      style="display:inline-block;margin:0.3rem;padding:0.5rem 0.9rem;
             border-radius:6px;border:2px solid #b8860b;background:#fffbe6;
             color:#333;cursor:pointer;font-size:1.1rem;font-weight:bold;">
      ${letter.toUpperCase()} <span style="font-size:0.75rem;font-weight:normal;color:#666;">(×${count})</span>
    </button>`
  ).join("");

  modal.innerHTML = `
    <div class="modal-content" style="max-width:360px;text-align:center;">
      <div class="modal-header">
        <h2>&#x1FA99; Reveal a Rare Letter</h2>
        <button class="close-button" id="golden-coin-modal-close">&times;</button>
      </div>
      <div class="modal-body">
        <p style="margin:0 0 0.75rem;">Costs <strong>${cost} links</strong>. Choose a letter to reveal all its instances:</p>
        <div>${optionsHTML}</div>
      </div>
    </div>
  `;

  modal.classList.add("show");

  const close = () => {
    modal.classList.remove("show");
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  modal.querySelector("#golden-coin-modal-close").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  document.addEventListener("keydown", onKey);

  modal.querySelectorAll(".golden-coin-option").forEach(btn => {
    btn.addEventListener("click", () => {
      const letter = btn.getAttribute("data-letter");
      close();
      const result = useGoldenCoin(letter);
      if (result.success) {
        renderParagraph(getChosenVowel());
        updateLetterCounts();
        updateScore(); // also calls renderGoldenActions
        // Gild the tile for the revealed letter
        const tile = document.querySelector(`.letter-tile[data-letter="${result.letter}"]`);
        if (tile) {
          tile.classList.remove("empty");
          tile.classList.add("purchased", "purchased-golden");
        }
        addNotification(
          `Golden Coin used: all instances of "${letter.toUpperCase()}" revealed (−${result.cost} links)`,
          "success"
        );
      }
    });
  });
}
