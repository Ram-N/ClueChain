/**
 * @fileoverview Game initialization and event handling module for ParaSight.
 * Manages game lifecycle, data loading, and event coordination.
 * @module game-controller
 */

import {
  checkGuess,
  getCurrentParagraph,
  getCurrentWords,
  getCurrentScore,
  getMaxScore,
  getChosenVowel,
  setCurrentParagraph,
  setCurrentWords,
  setGameParameters,
  setAllParagraphs,
  setSuffixConfig,
  isInitPhase,
  isSelectionComplete,
  revealSelectedLetters,
  revealNextSuffix,
  initializeSuffixes,
  resetGameState,
  showInitialCluesAfterSelection,
} from "./game-state.js?v=1.1";

import {
  renderParagraph,
  renderClues,
  updateScore,
  showGameOver,
  resetUI,
  setupMarketplace,
  updateLetterCounts,
  showToast,
  animateClueForWord,
  updateInputState,
  addNotification,
  clearNotifications,
  showInitialMessage,
  addCorrectGuessNotification,
  addIncorrectGuessNotification
} from "./ui-manager.js?v=1.1";

import {
  highlightCorrectWord,
  createSparklesAroundElement
} from "./animations.js";

/**
 * Sets up the game UI and initializes event handlers
 * @private
 */
function setupGame() {
  resetUI();
  renderParagraph("");
  renderClues();
  setupGuessInput();
}

/**
 * Sets up the word guessing form and its event handlers
 * @private
 */
function setupGuessing() {
  console.log("Setting up guessing form...");
  const form = document.getElementById("guess-form");
  const input = document.getElementById("guess-input");

  if (!form || !input) {
    console.error("Could not find form or input elements:", { form, input });
    return;
  }

  form.addEventListener("submit", handleGuess);
}

/**
 * Handles player's word guess submissions
 * @param {Event} e - The submit event object
 * @private
 */
function handleGuess(e) {
  e.preventDefault();
  const input = document.getElementById("guess-input");
  if (!input || !(input instanceof HTMLInputElement)) return;

  const guess = input.value.trim();
  if (!guess) return;

  console.log("Submitted guess:", guess);
  const result = checkGuess(guess);

  if (result.success) {
    input.classList.add("correct");
    setTimeout(() => input.classList.remove("correct"), 1000);

    // Reveal next suffix after correct guess
    const suffixRevealed = revealNextSuffix();
    if (suffixRevealed) {
      console.log("Revealed new suffix after correct guess");
    }

    renderParagraph(getChosenVowel());
    
    // Add visual celebration to the found word
    const word = getCurrentWords().find(w => w.word.toLowerCase() === guess.toLowerCase());
    setTimeout(() => {
      // Find all instances of the newly found word in the paragraph
      if (word) {
        // Find all found word spans
        const foundElements = document.querySelectorAll('span.found');
        let foundCount = 0;
        
        foundElements.forEach(element => {
          // Check if this element contains our word
          if (element.textContent.trim().toLowerCase() === word.word.toLowerCase()) {
            // Apply animation and sparkles to this element
            highlightCorrectWord(element);
            foundCount++;
          }
        });
        
        // If we didn't find any elements, try once more with a broader approach
        if (foundCount === 0) {
          console.log("Using broader search for word:", word.word);
          document.querySelectorAll('[data-masked="true"]').forEach(element => {
            if (element.textContent.includes(word.word)) {
              highlightCorrectWord(element);
            }
          });
        }
      }
    }, 200); // Slight delay to ensure DOM has updated
    
    renderClues();
    updateScore();
    updateLetterCounts();
    
    // Add notification for correct guess
    addCorrectGuessNotification(guess, result.pointsEarned);
    
    // Show additional context about point reduction if applicable
    if (word) {
      const lowestClueIndexSeen = word.lowestClueIndexSeen || 0;
      const originalPoints = word.clues && word.clues[0] ? word.clues[0].points : 0;
      
      if (lowestClueIndexSeen > 0 && originalPoints > result.pointsEarned) {
        showToast(`Points reduced from ${originalPoints} because you viewed easier clues`, "info");
      }
      
      // Animate the clue tumbling down
      animateClueForWord(word.word);
    }

    if (result.gameComplete) {
      console.log("Game complete detected! Triggering end game.");

      // Record game completion for streak tracking (only for authenticated users)
      if (window.streakTracker && window.authManager && window.authManager.isAuthenticated()) {
        const words = getCurrentWords();
        const paragraph = getCurrentParagraph();
        const mmdd = paragraph ? paragraph.date : null;
        const fullDate = mmdd ? `${new Date().getFullYear()}-${mmdd}` : null;
        window.streakTracker.recordGameCompletion({
          gameDate: fullDate,
          score: getCurrentScore(),
          maxPossibleScore: getMaxScore(),
          wordsFound: words.filter(w => w.found || w.revealed).length,
          totalWords: words.length,
        }).catch(err => console.warn("Failed to record game completion:", err));
      }

      showGameOver();
    }
  } else {
    input.classList.add("wrong");
    setTimeout(() => input.classList.remove("wrong"), 1000);
    
    // Add notification for incorrect guess
    addIncorrectGuessNotification(guess);
    
    // Reveal next suffix after wrong guess too
    const suffixRevealed = revealNextSuffix();
    if (suffixRevealed) {
      console.log("Revealed new suffix after wrong guess");
    }
    
    renderParagraph(getChosenVowel()); // Also re-render paragraph to show newly revealed suffix
    renderClues();
    updateScore();
  }

  input.value = "";
  input.focus();
}

/**
 * Sets up the guess input field and submit button
 */
function setupGuessInput() {
  const input = document.getElementById("guess-input");
  const submitButton = document.getElementById("submit-guess");

  if (!input || !submitButton) return;

  const handleGuess = () => {
    if (!(input instanceof HTMLInputElement)) return;

    const guess = input.value.trim();
    if (!guess) return;

    const result = checkGuess(guess);
    if (result.success) {
      // Add success visual feedback to input
      input.classList.add("correct");
      setTimeout(() => input.classList.remove("correct"), 1000);
      
      // Reveal next suffix after correct guess
      const suffixRevealed = revealNextSuffix();
      if (suffixRevealed) {
        console.log("Revealed new suffix after correct guess");
      }
      
      // Render updated paragraph
      renderParagraph(getChosenVowel());
      
      // Add visual celebration to the found word
      const word = getCurrentWords().find(w => w.word.toLowerCase() === guess.toLowerCase());
      setTimeout(() => {
        // Find all instances of the newly found word in the paragraph
        if (word) {
          // Find all found word spans
          const foundElements = document.querySelectorAll('span.found');
          let foundCount = 0;
          
          foundElements.forEach(element => {
            // Check if this element contains our word
            if (element.textContent.trim().toLowerCase() === word.word.toLowerCase()) {
              // Apply animation and sparkles to this element
              highlightCorrectWord(element);
              foundCount++;
            }
          });
          
          // If we didn't find any elements, try once more with a broader approach
          if (foundCount === 0) {
            console.log("Using broader search for word:", word.word);
            document.querySelectorAll('[data-masked="true"]').forEach(element => {
              if (element.textContent.includes(word.word)) {
                highlightCorrectWord(element);
              }
            });
          }
        }
      }, 200); // Slight delay to ensure DOM has updated
      
      renderClues();
      updateScore();
      updateLetterCounts();
      
      // Add notification for correct guess
      addCorrectGuessNotification(guess, result.pointsEarned);
      
      // Show additional toast with context about point reduction if applicable
      const lowestClueIndexSeen = word ? word.lowestClueIndexSeen : 0;
      const originalPoints = word && word.clues && word.clues[0] ? word.clues[0].points : 0;
      
      if (lowestClueIndexSeen > 0 && originalPoints > result.pointsEarned) {
        showToast(`Points reduced from ${originalPoints} because you viewed easier clues`, "info");
      }
      
      // Animate the clue tumbling down
      if (word) {
        animateClueForWord(word.word);
      }

      if (result.gameComplete) {
        // Record game completion for streak tracking (only for authenticated users)
        if (window.streakTracker && window.authManager && window.authManager.isAuthenticated()) {
          const words = getCurrentWords();
          const paragraph = getCurrentParagraph();
          const mmdd = paragraph ? paragraph.date : null;
          const fullDate = mmdd ? `${new Date().getFullYear()}-${mmdd}` : null;
          window.streakTracker.recordGameCompletion({
            gameDate: fullDate,
            score: getCurrentScore(),
            maxPossibleScore: getMaxScore(),
            wordsFound: words.filter(w => w.found || w.revealed).length,
            totalWords: words.length,
          }).catch(err => console.warn("Failed to record game completion:", err));
        }

        showGameOver();
      }
    } else {
      input.classList.add("wrong");
      setTimeout(() => input.classList.remove("wrong"), 1000);
      
      // Add notification for incorrect guess
      addIncorrectGuessNotification(guess);
      
      // Reveal next suffix after wrong guess too
      const suffixRevealed = revealNextSuffix();
      if (suffixRevealed) {
        console.log("Revealed new suffix after wrong guess");
      }
      
      // Even for wrong guesses, we need to re-render clues to show newly revealed ones
      renderParagraph(getChosenVowel()); // Also re-render paragraph to show newly revealed suffix
      renderClues();
      updateScore();
    }

    input.value = "";
    input.focus();
  };

  submitButton.addEventListener("click", handleGuess);
  input.addEventListener("keyup", (event) => {
    if (event.key === "Enter") {
      handleGuess();
    }
  });
}

/**
 * Renders the current game state
 */
function renderGameState() {
  renderParagraph(""); // Start with no vowels revealed
  renderClues();
  updateScore(); // This now also updates chain links
}

/**
 * Initializes the game and sets up event listeners
 * Entry point for the game
 */
export async function initializeGame() {
  console.log("Window loaded, initializing game...");
  
  // Reset both UI elements and game state for a completely fresh start
  resetGameState(); // Reset the game state first
  resetUI(); // Then reset the UI

  try {
    // Load game parameters
    const params = await fetch("./game_parameters.json").then((r) => r.json());

    // Load suffix configuration
    const suffixConfig = await fetch("./assets/config/suffix_config.json")
      .then(response => response.json())
      .catch(error => {
        console.error("Error loading suffix configuration:", error);
        return { suffixes: [] };
      });
    
    console.log("Loaded suffix configuration:", suffixConfig);

    // Load all JSON files from assets/data directory
    const dataFiles = await fetch("./assets/data/index.json")
      .then(response => {
        if (response.ok) {
          // If index.json exists, use it to get the list of files
          return response.json();
        } else {
          // Otherwise, we'll rely on our glob detection at build time
          console.error("Error: index.json not found in assets/data directory");
          // Return an empty array, as the data structure has changed
          return { files: [] };
        }
      })
      .then(data => data.files || []);

    // Fetch all data files in parallel
    const paragraphsData = await Promise.all(
      dataFiles.map(file => 
        fetch(file)
          .then(response => {
            if (!response.ok) {
              throw new Error(`HTTP error ${response.status} while loading ${file}`);
            }
            return response.json();
          })
          .catch(error => {
            console.error(`Error loading ${file}:`, error);
            // Log more details about the file to help with debugging
            console.warn(`Failed to load data file: ${file}. Please check that the file exists and is valid JSON.`);
            return null;
          })
      )
    );

    // Filter out any failed loads and combine all paragraphs
    const allParagraphs = paragraphsData
      .filter(data => data !== null)
      .map(data => ({
        id: data.id,
        date: data.date,
        title: data.title,
        text: data.text,
        hiddenWords: data.hiddenWords
      }));

    // Check if we have valid game data
    if (!allParagraphs || !Array.isArray(allParagraphs) || allParagraphs.length === 0) {
      throw new Error("No valid paragraph data found in data files");
    }

    console.log(`Loaded ${allParagraphs.length} paragraphs from data files`);
    
    // Log loaded paragraphs for debugging
    allParagraphs.forEach(paragraph => {
      console.log(`Loaded paragraph: ID=${paragraph.id}, Date=${paragraph.date}, Title=${paragraph.title?.substring(0, 30)}...`);
    });

    // Initialize game state
    setGameParameters(params);
    setAllParagraphs(allParagraphs);
    setSuffixConfig(suffixConfig);

    // Get the current date from the date element
    const dateElement = document.getElementById("current-date");
    const currentDateStr = dateElement ? dateElement.textContent : null;
    let selectedParagraph = null;

    if (currentDateStr) {
      try {
        // Parse the displayed date string to a Date object
        const currentDate = new Date(currentDateStr);

        // Format date as MM-DD (year-agnostic)
        const month = String(currentDate.getMonth() + 1).padStart(2, '0');
        const day = String(currentDate.getDate()).padStart(2, '0');
        const formattedDate = `${month}-${day}`;

        console.log(`Looking for paragraph with date: ${formattedDate}`);

        // Find paragraph matching MM-DD format
        selectedParagraph = allParagraphs.find(paragraph => {
          if (!paragraph || !paragraph.date) return false;
          return paragraph.date === formattedDate;
        });

        if (selectedParagraph) {
          console.log(`Found matching paragraph for date: ${formattedDate}`);
        } else {
          console.log(`No paragraph found for date: ${formattedDate}`);
        }
      } catch (error) {
        console.error("Error parsing date:", error);
      }
    }
    
    // If no paragraph found for the current date, handle appropriately
    if (!selectedParagraph) {
      // Display a message that no puzzle is available for this date
      const container = document.getElementById("paragraph-container");
      const dateElement = document.getElementById("current-date");
      const displayDate = dateElement ? dateElement.textContent : "this date";
      
      if (container) {
        container.innerHTML = `
          <div class="no-puzzle-message">
            <h3>No puzzle available for ${displayDate}</h3>
            <p>Use the arrow buttons to navigate to a date with a puzzle.</p>
          </div>
        `;
      }
      
      // Clear other game elements
      const cluesContainer = document.getElementById("clues-container");
      if (cluesContainer) {
        cluesContainer.innerHTML = "";
      }
      
      const scoreValue = document.getElementById("score-value");
      const maxScoreValue = document.getElementById("max-score-value");
      if (scoreValue) scoreValue.textContent = "0";
      if (maxScoreValue) maxScoreValue.textContent = "0";
      
      return; // Exit early, don't try to initialize a game
    }
    if (!selectedParagraph || !Array.isArray(selectedParagraph.hiddenWords)) {
      throw new Error("Invalid paragraph data structure");
    } // Initialize game state in the correct order
    // Filter and process hidden words to ensure they exist in the paragraph
    const initialWords = selectedParagraph.hiddenWords
      .filter(
        /** @param {import('./game-state.js').GameWord} word */ (word) => {
          // Test if word appears in the text (case-insensitive)
          const wordRegex = new RegExp(`\\b${word.word}\\b`, "gi");
          const exists = wordRegex.test(selectedParagraph.text);
          if (!exists) {
            console.warn(
              `Warning: Hidden word "${word.word}" not found in paragraph ${selectedParagraph.id}. Ignoring this word.`
            );
          }
          return exists;
        }
      )
      .map(
        /** @param {import('./game-state.js').GameWord} word */ (word) => {
          // Find all positions of the word in the paragraph text
          const positions = [];
          const wordRegex = new RegExp(`\\b${word.word}\\b`, "gi");
          let match;
          while ((match = wordRegex.exec(selectedParagraph.text)) !== null) {
            positions.push({
              start: match.index,
              end: match.index + match[0].length, // Use actual match length in case of different casing
            });
          }

          return {
            ...word,
            found: false,
            positions: positions,
          };
        }
      );
    console.log("Initialized words with positions:", initialWords);
    setCurrentWords(initialWords);
    setCurrentParagraph(selectedParagraph);
    updateScore(); // Ensure score is displayed after initialization        // Set up event listeners
    setupGuessInput();
    
    // Setup marketplace (re-adding event listeners since we cloned tiles in resetUI)
    setupMarketplace();

    // Force a delay to ensure all setup is complete
    setTimeout(() => {
      // If we're in init phase, show different UI state
      if (isInitPhase() && !isSelectionComplete()) {
        // Show initial clues first, then render
        showInitialCluesAfterSelection();
        // Only render the paragraph with masked words without revealing any letters
        renderParagraph("");
        renderClues();
        updateScore();
        // Show letter tiles without counts
        updateLetterCounts(false);
        // Disable input and submit button during selection phase
        updateInputState();
        // Show initial notification prompting letter selection
        showInitialMessage();
      } else {
        // Normal game initialization (after selection or on reload)
        // Make sure we have initial clues if selection is already complete
        if (isSelectionComplete()) {
          showInitialCluesAfterSelection();
        }
        renderGameState();
        updateLetterCounts(true); // Update initial letter counts
        // Make sure input is enabled
        updateInputState();
      }

      // Show one-time banner prompting sign-in for streak tracking (only for guest users)
      if (window.authManager && !window.authManager.isAuthenticated() && !localStorage.getItem('auth-banner-dismissed')) {
        setTimeout(() => {
          showToast('🔥 Sign in to track your streak!', 'info');
          localStorage.setItem('auth-banner-dismissed', 'true');
        }, 2000);
      }
    }, 0);
  } catch (error) {
    console.error("Failed to initialize game:", error);
    const container = document.getElementById("paragraph-container");
    if (container) {
      container.innerHTML = "Error loading game data. Please refresh the page.";
    }
  }
}
