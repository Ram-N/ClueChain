/**
 * @fileoverview Core game state management module for ParaSight.
 * Manages the game's state using a centralized object with getters and setters.
 * This module is the daily-mode adapter: it creates a ClueChainEngine instance
 * and delegates scoring/guess/reveal logic to it, while retaining ownership of
 * the daily-specific state (masking, suffix reveals, marketplace sets, etc.).
 * @module game-state
 */

import { ClueChainEngine } from './engine/cluechain-engine.js';

console.log("🔄 Game State loaded - Version 1.2 (engine-backed)");

/** @type {ClueChainEngine|null} Shared engine instance for the current puzzle */
let _engine = null;

/**
 * Returns the active ClueChainEngine instance (created by setCurrentWords).
 * Exposed for debugging only — callers should use the exported functions.
 * @returns {ClueChainEngine|null}
 */
export function getEngine() {
  return _engine;
}

/**
 * @typedef {Object} GameWord
 * @property {string} word - The actual word
 * @property {string} clue - Primary clue for the word
 * @property {string} [clue2] - Secondary clue for the word
 * @property {number} points - Points awarded for finding the word
 * @property {boolean} found - Whether the word has been found
 * @property {boolean} revealed - Whether the word was revealed by the player
 * @property {Array<{start: number, end: number}>} positions - Word positions in text
 * @property {number} visibleClues - Number of clues currently visible for the word
 */

/**
 * @typedef {Object} GameParagraph
 * @property {number} id - Unique identifier
 * @property {string} text - The paragraph text
 * @property {Array<GameWord>} hiddenWords - Words to find in the paragraph
 * @property {string} [title] - Optional title for the paragraph
 */

/**
 * @typedef {Object} MarketplaceVowelConfig
 * @property {number} cost - Cost to purchase a vowel
 */

/**
 * @typedef {Object} MarketplaceConsonantConfig
 * @property {number} cost - Cost to reveal a consonant
 */

/**
 * @typedef {Object} MarketplaceConfig
 * @property {MarketplaceVowelConfig} vowel - Vowel purchase configuration
 * @property {MarketplaceConsonantConfig} consonant - Consonant reveal configuration
 */

/**
 * @typedef {Object} GamePenalties
 * @property {number} wrongGuess - Points deducted for wrong guesses
 */

/**
 * @typedef {Object} GameParameters
 * @property {GamePenalties} penalties - Game penalties configuration
 * @property {MarketplaceConfig} marketplace - Marketplace configuration
 * @property {Object} styles - UI styling configuration
 */

/**
 * @typedef {Object} GameResult
 * @property {boolean} success - Whether the guess was correct
 * @property {boolean} gameComplete - Whether all words have been found
 * @property {number} pointsEarned - Points earned for the guess
 */

/**
 * @typedef {Object} GameState
 * @property {{
 *   paragraph: GameParagraph | null,
 *   chosenVowel: string,
 *   words: GameWord[],
 *   score: number,
 *   maxScore: number
 * }} current
 * @property {{
 *   parameters: GameParameters | null,
 *   paragraphs: GameParagraph[] | null
 * }} config
 */

// Interface definitions moved to JSDoc types above

/** @type {Record<string, number>} */
export const letterCounts = {}; // Tracks count of each letter remaining in hidden words

/**
 * Resets the game state to its initial values
 * This function should be called when changing paragraphs or starting a new game
 */
export function resetGameState() {
  // Reset the engine
  _engine = null;

  // Reset the current game state
  gameState.current.paragraph = null;
  gameState.current.chosenVowel = "";
  gameState.current.words = [];
  gameState.current.score = 100; // Start with 100 links
  gameState.current.maxScore = 0;
  gameState.current.clueAttempts = 0;
  gameState.current.shownWordIndices = [];
  gameState.current.initPhase = true;
  gameState.current.selectedVowel = "";
  gameState.current.selectedConsonants = [];
  gameState.current.wordsWithRevealedSuffixes = [];
  gameState.current.goldenKeyUsed = false;
  gameState.current.goldenCoinUsed = false;
  gameState.current.assistedPlay = false;

  // Reset marketplace state
  marketState.vowels.clear();
  marketState.consonants.clear();
  marketState.hints = 0;
  marketState.selectionComplete = false;
  
  // Reset letter counts
  Object.keys(letterCounts).forEach(key => delete letterCounts[key]);
  
  console.log("Game state completely reset");
}

/** @type {GameState} */
export const gameState = {
  current: {
    paragraph: null, // Currently displayed paragraph
    chosenVowel: "", // Vowel selected by player for revelation
    words: [], // Array of word objects with found status
    score: 0, // Player's current score
    maxScore: 0, // Maximum achievable score for current paragraph
    clueAttempts: 0, // Number of answer attempts made
    initialCluesShown: 3, // Number of clues to show initially
    shownWordIndices: [], // Indices of words with visible clues
    revealPenalty: 15, // Default penalty for revealing a word
    initPhase: true, // Whether the game is in the initial letter selection phase
    selectedVowel: "", // The vowel selected during initialization
    selectedConsonants: [], // The consonants selected during initialization
    wordsWithRevealedSuffixes: [], // Array of word indices that have their suffixes revealed
    initialSuffixesShown: 1, // Number of words to show suffixes for initially (changed from 3 to 1)
    goldenKeyUsed: false, // Whether the golden key has been used this game
    goldenCoinUsed: false, // Whether the golden coin has been used this game
    assistedPlay: false, // Whether either golden item was used this game
  },
  config: {
    parameters: null, // Game rules like penalties
    paragraphs: null, // All available game content
    suffixes: null, // Suffix configuration for progressive reveal
    availableDates: [], // File path array from index.json (for calendar use)
  },
};

// Marketplace state
export const marketState = {
  /** @type {Set<string>} */
  vowels: new Set(), // Set of purchased vowels
  /** @type {Set<string>} */
  consonants: new Set(), // Set of purchased consonants
  /** @type {number} */
  hints: 0, // Number of hints purchased
  /** @type {boolean} */
  selectionComplete: false, // Whether the initial letter selection is complete
};

/** @type {{[key: string]: number}} */
export const letterState = {
  counts: {}, // Tracks count of each letter remaining in hidden words
};

// Getters
/**
 * Gets the current active paragraph
 * @returns {GameParagraph|null} The current paragraph object or null if not set
 */
export function getCurrentParagraph() {
  return gameState.current.paragraph;
}

/**
 * Gets the suffix configuration
 * @returns {Object|null} The suffix configuration or null if not loaded
 */
export function getSuffixConfig() {
  return gameState.config.suffixes;
}

/**
 * Gets the indices of words that have their suffixes revealed
 * @returns {Array<number>} Array of word indices
 */
export function getWordsWithRevealedSuffixes() {
  return gameState.current.wordsWithRevealedSuffixes || [];
}

/**
 * Gets the suffix for a specific word from the suffix configuration
 * @param {string} word - The word to check
 * @returns {Object|null} The matching suffix object or null if no match
 */
export function getWordSuffix(word) {
  if (!word || typeof word !== 'string') return null;
  
  const lowerWord = word.toLowerCase();
  const suffixConfig = getSuffixConfig();
  
  if (!suffixConfig || !suffixConfig.suffixes || !Array.isArray(suffixConfig.suffixes)) {
    console.warn("No valid suffix configuration found");
    return null;
  }
  
  // Debug log all available suffixes
  console.log(`Checking word "${word}" against suffixes:`, 
    suffixConfig.suffixes.map(s => s.ending).join(', '));
  
  // Check each suffix in the configuration
  for (const suffix of suffixConfig.suffixes) {
    if (lowerWord.endsWith(suffix.ending)) {
      console.log(`Found matching suffix "${suffix.ending}" for word "${word}"`);
      return suffix;
    }
  }
  
  console.log(`No matching suffix found for word "${word}"`);
  return null;
}

/**
 * Gets the number of initially shown suffixes
 * @returns {number} Number of initial suffixes
 */
export function getInitialSuffixesShown() {
  return gameState.current.initialSuffixesShown;
}

/**
 * Gets the game parameters including penalties and rules
 * @returns {GameParameters|null} Game parameters object or null if not loaded
 */
export function getGameParameters() {
  return gameState.config.parameters;
}

/**
 * Gets all available paragraphs for the game
 * @returns {Array<GameParagraph>|null} Array of paragraph objects or null if not loaded
 */
export function getAllParagraphs() {
  return gameState.config.paragraphs;
}

/**
 * Gets the currently chosen vowel by the player
 * @returns {string} The selected vowel
 */
export function getChosenVowel() {
  return gameState.current.chosenVowel;
}

/**
 * Gets whether the game is in the initial letter selection phase
 * @returns {boolean} True if in initialization phase, false otherwise
 */
export function isInitPhase() {
  return gameState.current.initPhase;
}

/**
 * Gets the selected vowel during initialization
 * @returns {string} The selected vowel
 */
export function getSelectedVowel() {
  return gameState.current.selectedVowel;
}

/**
 * Gets the selected consonants during initialization
 * @returns {string[]} The selected consonants
 */
export function getSelectedConsonants() {
  return gameState.current.selectedConsonants;
}

/**
 * Gets whether the initial letter selection is complete
 * @returns {boolean} True if selection is complete, false otherwise
 */
export function isSelectionComplete() {
  return marketState.selectionComplete;
}

/**
 * Gets the list of words for the current paragraph
 * @returns {Array<GameWord>} Array of word objects with their current state
 */
export function getCurrentWords() {
  return gameState.current.words || [];
}

/**
 * Gets the number of attempts made so far
 * @returns {number} The number of attempts
 */
export function getClueAttempts() {
  return gameState.current.clueAttempts;
}

/**
 * Gets the number of initial clues shown
 * @returns {number} Number of initial clues
 */
export function getInitialCluesShown() {
  return gameState.current.initialCluesShown;
}

/**
 * Gets the indices of words with visible clues
 * @returns {number[]} Array of word indices
 */
export function getShownWordIndices() {
  return gameState.current.shownWordIndices;
}

/**
 * Gets the current score of the player
 * @returns {number} The current score
 */
export function getCurrentScore() {
  // Ensure score is always a valid number
  if (isNaN(gameState.current.score)) {
    console.error("Score is NaN, resetting to 100");
    gameState.current.score = 100;
  }
  return gameState.current.score;
}

/**
 * Gets the maximum score possible in the current game session
 * @returns {number} The maximum score
 */
export function getMaxScore() {
  return gameState.current.maxScore;
}

// Setters
/**
 * Sets the current active paragraph
 * @param {GameParagraph} paragraph - The paragraph object to set as current
 */
export function setCurrentParagraph(paragraph) {
  gameState.current.paragraph = paragraph;
}

/**
 * Sets the game parameters including rules and penalties
 * @param {GameParameters} params - The parameters object to configure the game
 */
export function setGameParameters(params) {
  gameState.config.parameters = params;
}

/**
 * Sets all available paragraphs for the game
 * @param {Array<GameParagraph>} paragraphs - Array of paragraph objects to be set
 */
export function setAllParagraphs(paragraphs) {
  gameState.config.paragraphs = paragraphs;
}

/**
 * Sets the suffix configuration for the game
 * @param {Object} suffixConfig - The suffix configuration object
 */
export function setSuffixConfig(suffixConfig) {
  gameState.config.suffixes = suffixConfig;
}

/**
 * Gets the list of available puzzle file paths (from index.json)
 * @returns {string[]} Array of file paths
 */
export function getAvailableDates() {
  return gameState.config.availableDates;
}

/**
 * Sets the list of available puzzle file paths (from index.json)
 * @param {string[]} files - Array of file paths
 */
export function setAvailableDates(files) {
  gameState.config.availableDates = files;
}

/**
 * Sets the chosen vowel for the current game session
 * @param {string} vowel - The vowel to be set as chosen
 */
export function setVowel(vowel) {
  gameState.current.chosenVowel = vowel;
}

/**
 * Sets the selected vowel during initialization
 * @param {string} vowel - The vowel to be set as selected
 */
export function setSelectedVowel(vowel) {
  if (gameState.current.initPhase) {
    gameState.current.selectedVowel = vowel.toLowerCase();
    return true;
  }
  return false;
}

/**
 * Clears all selected consonants (used by the Reset button during init phase)
 */
export function clearSelectedConsonants() {
  if (gameState.current.initPhase) {
    gameState.current.selectedConsonants = [];
  }
}

/**
 * Adds a selected consonant during initialization
 * @param {string} consonant - The consonant to be added
 * @returns {boolean} Whether the consonant was added successfully
 */
export function addSelectedConsonant(consonant) {
  if (gameState.current.initPhase && gameState.current.selectedConsonants.length < 2) {
    gameState.current.selectedConsonants.push(consonant.toLowerCase());
    return true;
  }
  return false;
}

/**
 * Completes the initial letter selection phase
 * @returns {boolean} Whether the transition was successful
 */
export function completeLetterSelection() {
  if (gameState.current.initPhase && 
      gameState.current.selectedVowel && 
      gameState.current.selectedConsonants.length === 2) {
    gameState.current.initPhase = false;
    marketState.selectionComplete = true;
    
    // Add selected letters to purchased sets
    marketState.vowels.add(gameState.current.selectedVowel);
    gameState.current.selectedConsonants.forEach(consonant => {
      marketState.consonants.add(consonant);
    });
    
    // Set the chosen vowel
    gameState.current.chosenVowel = gameState.current.selectedVowel;
    
    // Initialize the suffix reveal system first (before counting letters)
    initializeSuffixes();
    
    // Now initialize letter counts with suffixes already revealed
    initializeLetterCounts();
    
    return true;
  }
  return false;
}

// Note: updateLetterCountsAfterSelection() function removed as it's now handled
// by initializeLetterCounts() which is called after suffix initialization

/**
 * Sets the list of words for the current paragraph
 * @param {Array<GameWord>} words - Array of word objects to be set
 */
export function setCurrentWords(words) {
  // Initialize each word with visibleClues = 0 and revealed = false
  gameState.current.words = words.map(word => ({
    ...word,
    visibleClues: 0,
    revealed: false,
    activeClueIndex: 0, // Default to the hardest clue (index 0)
    lowestClueIndexSeen: 0 // Track the easiest clue seen (0=hard, 1=medium, 2=easy)
  }));

  // Create engine instance now that we have both words and parameters
  _engine = new ClueChainEngine(
    { hiddenWords: gameState.current.words },
    { mode: 'daily', params: gameState.config.parameters }
  );
  _engine.init();
  
  // Get indices of unfound words
  const unfoundIndices = words.map((_, index) => index);
  
  // Randomly select initialCluesShown indices for initial display
  const initialCount = Math.min(gameState.current.initialCluesShown, unfoundIndices.length);
  gameState.current.shownWordIndices = [];
  
  // Shuffle the unfound indices to pick random words
  for (let i = unfoundIndices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [unfoundIndices[i], unfoundIndices[j]] = [unfoundIndices[j], unfoundIndices[i]];
  }
  
  // Set the initial visible clues
  for (let i = 0; i < initialCount; i++) {
    const wordIndex = unfoundIndices[i];
    gameState.current.shownWordIndices.push(wordIndex);
  }
  
  // Calculate starting score so that perfect play always yields exactly 100
  let totalWordPoints = 0;
  words.forEach(word => {
    if (word.clues && Array.isArray(word.clues) && word.clues.length > 0) {
      totalWordPoints += word.clues[0].points || 0;
    } else if (word.points) {
      totalWordPoints += word.points;
    }
  });
  gameState.current.maxScore = 100;

  gameState.current.score = Math.max(0, 100 - totalWordPoints); // Start in deficit; earn up to 100
  gameState.current.clueAttempts = 0; // Reset attempt counter
  // Note: initializeLetterCounts() will be called later after suffix initialization
}

/**
 * Sets the current score of the player
 * @param {number} score - The score value to be set
 */
export function setScore(score) {
  // Ensure we're setting a valid number
  if (isNaN(score)) {
    console.error("Attempted to set score to NaN, using 100 instead");
    gameState.current.score = 100;
  } else {
    gameState.current.score = score;
  }
}

/**
 * Sets the maximum score for the current game session
 * @param {number} score - The maximum score value to be set
 */
export function setMaxScore(score) {
  gameState.current.maxScore = score;
}

// Game logic functions
/**
 * Masks a word by replacing non-vowel characters with dashes
 * @param {string} word - The word to mask
 * @param {string} vowel - The vowel to reveal in the word
 * @returns {string} The masked word with only the specified vowel visible
 */
export function maskWord(word, vowel) {
  return word.replace(/[^\W_]/gi, (char) => {
    if (char.toLowerCase() === vowel) return char;
    return "-";
  });
}

/**
 * Finds all positions of a word in a text
 * @param {string} text - The text to search in
 * @param {string} word - The word to find
 * @returns {Array<{start: number, end: number}>} Array of position objects
 */
export function findWordPositions(text, word) {
  const positions = [];
  const regex = new RegExp(`\\b${word}\\b`, "gi");
  let match;
  while ((match = regex.exec(text)) !== null) {
    positions.push({
      start: match.index,
      end: match.index + word.length,
    });
  }
  return positions;
}

/**
 * Checks if all words have been found
 * @returns {boolean} True if game is complete, false otherwise
 */
export function isGameComplete() {
  const complete = gameState.current.words.every((word) => word.found);
  console.log("Game completion check:", {
    complete,
    totalWords: gameState.current.words.length,
    foundWords: gameState.current.words.filter((w) => w.found).length,
    wordStatuses: gameState.current.words.map((w) => ({
      word: w.word,
      found: w.found,
    })),
  });
  return complete;
}

/**
 * Processes a player's guess
 * @param {string} guess - The player's guess
 * @returns {{success: boolean, wordObj?: Object}} Result object with success status and found word
 */
export function processGuess(guess) {
  // Convert guess to lowercase for case-insensitive matching
  const wordObj = gameState.current.words.find(
    (w) => w.word.toLowerCase() === guess.toLowerCase() && !w.found
  );

  if (wordObj) {
    // Mark word as found and award points
    wordObj.found = true;
    gameState.current.score += wordObj.points;
    updateLetterCounts(wordObj.word);
    return { success: true, wordObj };
  } else {
    // Apply penalty for wrong guess, but don't go below zero
    const params = getGameParameters();
    if (params?.penalties?.wrongGuess) {
      gameState.current.score = Math.max(
        0,
        gameState.current.score - params.penalties.wrongGuess
      );
    }
    return { success: false };
  }
}

/**
 * Attempts to purchase a vowel from the marketplace.
 * Delegates cost calculation to the engine; keeps marketplace set and letter counts local.
 * @param {string} vowel - The vowel to purchase
 * @returns {{success: boolean, cost: number, newScore: number}} Result of the purchase attempt
 */
export function purchaseVowel(vowel) {
  const params = gameState.config.parameters;
  if (!params)
    return { success: false, cost: 0, newScore: gameState.current.score };

  if (marketState.vowels.has(vowel))
    return { success: false, cost: 0, newScore: gameState.current.score };

  const instances = letterCounts[vowel.toLowerCase()] || 0;
  const costPerInstance = params.marketplace.vowel.costPerInstance ?? 2;
  const cost = instances * costPerInstance;

  if (cost === 0)
    return { success: false, cost: 0, newScore: gameState.current.score };

  if (gameState.current.score >= cost) {
    gameState.current.score -= cost;
    // Sync engine score
    if (_engine) _engine._score = gameState.current.score;
    marketState.vowels.add(vowel);
    clearLetterCount(vowel.toLowerCase());
    return { success: true, cost, newScore: gameState.current.score };
  }
  return { success: false, cost, newScore: gameState.current.score };
}

/**
 * Attempts to purchase a consonant hint from the marketplace.
 * Delegates cost calculation to the engine; keeps marketplace set and letter counts local.
 * @param {string} consonant - The consonant to purchase
 * @returns {{success: boolean, cost: number, newScore: number, consonant?: string}} Result
 */
export function purchaseConsonant(consonant) {
  const params = gameState.config.parameters;
  if (!params)
    return { success: false, cost: 0, newScore: gameState.current.score };

  const isConsonant = "bcdfghjklmnpqrstvwxyz".includes(consonant.toLowerCase());
  if (!isConsonant || marketState.consonants.has(consonant.toLowerCase())) {
    return { success: false, cost: 0, newScore: gameState.current.score };
  }

  const instances = letterCounts[consonant.toLowerCase()] || 0;
  const costPerInstance = params.marketplace.consonant.costPerInstance ?? 3;
  const cost = instances * costPerInstance;

  if (cost === 0)
    return { success: false, cost: 0, newScore: gameState.current.score };

  if (gameState.current.score >= cost) {
    gameState.current.score -= cost;
    // Sync engine score
    if (_engine) _engine._score = gameState.current.score;
    marketState.consonants.add(consonant.toLowerCase());
    clearLetterCount(consonant.toLowerCase());
    return {
      success: true,
      cost,
      newScore: gameState.current.score,
      consonant: consonant.toLowerCase(),
    };
  }
  return { success: false, cost, newScore: gameState.current.score };
}

/**
 * Finds the most common consonant in the hidden words that hasn't been revealed
 * @private
 * @returns {string|null} The best consonant to reveal or null if none found
 */
function findBestConsonant() {
  const words = getCurrentWords()
    .filter((w) => !w.found)
    .map((w) => w.word.toLowerCase());

  if (words.length === 0) return null;

  /** @type {{[key: string]: number}} */
  const consonantCount = {};
  const consonants = "bcdfghjklmnpqrstvwxyz".split("");

  words.forEach((word) => {
    word.split("").forEach((char) => {
      if (consonants.includes(char) && !marketState.consonants.has(char)) {
        consonantCount[char] = (consonantCount[char] || 0) + 1;
      }
    });
  });

  const sorted = Object.entries(consonantCount).sort(([, a], [, b]) => b - a);
  return sorted.length > 0 ? sorted[0][0] : null;
}

/**
 * Checks if a guess matches any hidden word.
 * Delegates scoring and completion logic to the engine; keeps local state in sync.
 * @param {string} guess - The player's guess
 * @returns {GameResult} The result of the guess
 */
export function checkGuess(guess) {
  const normalizedGuess = guess.toLowerCase().trim();
  const wordObj = getCurrentWords().find(
    (w) => w.word.toLowerCase() === normalizedGuess && !w.found
  );

  // Increment attempt counter for progressive clue revealing
  gameState.current.clueAttempts++;

  // After each attempt, reveal one more clue if there are any unfound words
  const unfoundIndices = getCurrentWords()
    .map((word, index) => word.found ? -1 : index)
    .filter(index => index !== -1 && !gameState.current.shownWordIndices.includes(index));

  if (unfoundIndices.length > 0) {
    const randomIndex = Math.floor(Math.random() * unfoundIndices.length);
    const wordIndexToReveal = unfoundIndices[randomIndex];
    if (wordIndexToReveal !== undefined && !gameState.current.shownWordIndices.includes(wordIndexToReveal)) {
      gameState.current.shownWordIndices.push(wordIndexToReveal);
    }
  }

  // Delegate to engine for scoring/completion
  if (_engine) {
    if (wordObj) {
      // Correct guess — calculate points locally (engine doesn't know lowestClueIndexSeen)
      wordObj.found = true;
      const lowestClueIndexSeen = wordObj.lowestClueIndexSeen || 0;
      const pointsEarned = wordObj.clues && wordObj.clues[lowestClueIndexSeen]
        ? (wordObj.clues[lowestClueIndexSeen].points || 0)
        : (wordObj.points || 0);
      gameState.current.score += pointsEarned;
      // Sync engine score so it stays coherent
      _engine._score = gameState.current.score;
      // Mark the corresponding engine item solved
      const engineItem = _engine._items.find(it => it.word.toLowerCase() === normalizedGuess && !it.solved);
      if (engineItem) engineItem.solved = true;
      _engine._completed = _engine._items.every(it => it.solved || it.revealed);

      updateLetterCounts(wordObj.word);
      const allFound = getCurrentWords().every((w) => w.found || w.revealed);
      return { success: true, gameComplete: allFound, pointsEarned };
    }

    // Wrong guess — apply penalty through engine
    const penalty = getGameParameters()?.penalties?.wrongGuess ?? 5;
    gameState.current.score = Math.max(0, gameState.current.score - penalty);
    _engine._score = gameState.current.score;
    return { success: false, gameComplete: false, pointsEarned: 0 };
  }

  // Fallback (no engine yet — should not happen in normal flow)
  if (wordObj) {
    wordObj.found = true;
    const lowestClueIndexSeen = wordObj.lowestClueIndexSeen || 0;
    let pointsEarned;
    if (wordObj.clues && Array.isArray(wordObj.clues) && wordObj.clues[lowestClueIndexSeen]) {
      pointsEarned = wordObj.clues[lowestClueIndexSeen].points || 0;
    } else {
      pointsEarned = wordObj.points || 0;
    }
    gameState.current.score += pointsEarned;
    updateLetterCounts(wordObj.word);
    const allFound = getCurrentWords().every((w) => w.found || w.revealed);
    return { success: true, gameComplete: allFound, pointsEarned };
  }
  const params = getGameParameters();
  if (params?.penalties?.wrongGuess) {
    gameState.current.score = Math.max(0, gameState.current.score - params.penalties.wrongGuess);
  }
  return { success: false, gameComplete: false, pointsEarned: 0 };
}

/**
 * Masks a word, optionally revealing a vowel, purchased letters, and suffix endings
 * @param {string} word - The word to mask
 * @param {string} [vowel=''] - The vowel to reveal
 * @param {number} [wordIndex=-1] - The index of the word in the game state
 * @returns {string} The masked word
 */
export function maskWordWithPurchases(word, vowel = "", wordIndex = -1) {
  // Check if we're in the initial phase with selection complete
  const inInitPhase = isInitPhase() && !marketState.selectionComplete;
  
  // If in normal phase or selection is complete, use standard masking
  if (!inInitPhase) {
    // First check if this word has a revealed suffix
    let hasSuffix = false;
    let suffixStart = word.length;
    
    if (wordIndex >= 0) {
      const revealedSuffixes = getWordsWithRevealedSuffixes();
      hasSuffix = revealedSuffixes.includes(wordIndex);
      
      if (hasSuffix) {
        const suffix = getWordSuffix(word);
        if (suffix && suffix.ending) {
          suffixStart = word.length - suffix.ending.length;
          console.log(`Word "${word}" has revealed suffix "${suffix.ending}" starting at index ${suffixStart}`);
        } else {
          console.warn(`Word "${word}" should have a suffix but none was found`);
          hasSuffix = false;
        }
      }
    }
    
    // Debug log for test environment
    if (wordIndex >= 0) {
      console.log(`Masking word "${word}" with wordIndex=${wordIndex}, hasSuffix=${hasSuffix}, suffixStart=${suffixStart}`);
    }
    
    return word
      .split("")
      .map((char, index) => {
        const lowerChar = char.toLowerCase();
        
        // Show the specified vowel if it matches
        if (vowel && lowerChar === vowel.toLowerCase()) {
          return char;
        }
        
        // Show purchased consonants
        if (marketState.consonants.has(lowerChar)) {
          return char;
        }
        
        // Show purchased vowels
        if (marketState.vowels.has(lowerChar)) {
          return char;
        }
        
        // Show suffix letters if this character is part of a revealed suffix
        if (hasSuffix && index >= suffixStart) {
          console.log(`Revealing suffix character '${char}' at position ${index} in word "${word}"`);
          return char;
        }
        
        // Mask everything else
        return "_";
      })
      .join("");
  } else {
    // In initial phase - mask everything
    return word
      .split("")
      .map(() => "_")
      .join("");
  }
}

/**
 * Shows initial clues after letter selection is complete
 * @returns {void}
 */
export function showInitialCluesAfterSelection() {
  const words = getCurrentWords();
  if (!words || words.length === 0) return;
  
  // Get indices of unfound words
  const unfoundIndices = words
    .map((word, index) => (!word.found && !word.revealed) ? index : -1)
    .filter(index => index !== -1);
  
  // Randomly select initialCluesShown indices for initial display
  const initialCount = Math.min(gameState.current.initialCluesShown, unfoundIndices.length);
  gameState.current.shownWordIndices = [];
  
  // Shuffle the unfound indices to pick random words
  for (let i = unfoundIndices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [unfoundIndices[i], unfoundIndices[j]] = [unfoundIndices[j], unfoundIndices[i]];
  }
  
  // Set the initial visible clues
  for (let i = 0; i < initialCount; i++) {
    const wordIndex = unfoundIndices[i];
    gameState.current.shownWordIndices.push(wordIndex);
  }
  
  console.log(`Showing initial clues for words: ${gameState.current.shownWordIndices.map(i => words[i]?.word).join(', ')}`);
}

/**
 * Reveals selected letters in hidden words after initial selection
 * @returns {void}
 */
export function revealSelectedLetters() {
  if (!marketState.selectionComplete) return;
  
  // Get the selected letters
  const vowel = gameState.current.selectedVowel;
  const consonants = gameState.current.selectedConsonants;
  
  // No need to modify the masking algorithm as maskWordWithPurchases
  // already handles revealing the selected letters based on market state
  // The selected letters were added to marketState.vowels and marketState.consonants
  // in completeLetterSelection()
}

/**
 * Initializes letter counts for all hidden words
 * @private
 */
function initializeLetterCounts() {
  // Reset the counts
  Object.keys(letterCounts).forEach((key) => delete letterCounts[key]);

  // Count letters in all hidden words
  const words = getCurrentWords();
  
  // Get the list of words with revealed suffixes
  const wordsWithRevealedSuffixes = getWordsWithRevealedSuffixes();
  
  // Get the selected letters (initial selection)
  const selectedVowel = getSelectedVowel();
  const selectedConsonants = getSelectedConsonants();
  const alreadyRevealedLetters = new Set([selectedVowel, ...selectedConsonants]);
  
  // Also consider purchased letters
  marketState.vowels.forEach(vowel => alreadyRevealedLetters.add(vowel));
  marketState.consonants.forEach(consonant => alreadyRevealedLetters.add(consonant));
  
  // Process each word that isn't found yet
  words.forEach((word, wordIndex) => {
    if (!word.found) {
      // Check if this word has a revealed suffix
      const hasSuffix = wordsWithRevealedSuffixes.includes(wordIndex);
      let suffixStart = word.word.length;
      
      // If this word has a revealed suffix, get its starting position
      if (hasSuffix) {
        const suffix = getWordSuffix(word.word);
        if (suffix && suffix.ending) {
          suffixStart = word.word.length - suffix.ending.length;
        }
      }
      
      // Count each letter, excluding revealed suffixes and already revealed letters
      word.word
        .toLowerCase()
        .split("")
        .forEach((char, charIndex) => {
          // Skip if this char is part of a revealed suffix
          if (hasSuffix && charIndex >= suffixStart) {
            return;
          }
          
          // Skip if this char is already revealed through selection or purchase
          if (alreadyRevealedLetters.has(char)) {
            return;
          }
          
          // Otherwise, count this letter
          letterCounts[char] = (letterCounts[char] || 0) + 1;
        });
    }
  });
  
  console.log("Initialized letter counts (after suffix reveals):", letterCounts);
  console.log("Words with revealed suffixes:", wordsWithRevealedSuffixes.map(idx => 
    words[idx] ? `${words[idx].word} (index ${idx})` : `invalid index ${idx}`
  ));
}

/**
 * Updates letter counts when a word is found
 * @private
 * @param {string} word - The word that was found
 */
function updateLetterCounts(word) {
  // Find the word index to check for revealed suffixes
  const words = getCurrentWords();
  const wordIndex = words.findIndex(w => w.word.toLowerCase() === word.toLowerCase());
  
  if (wordIndex === -1) {
    console.error(`Could not find word "${word}" in current words list`);
    return;
  }
  
  // Count occurrences of each letter in this word
  const wordLetterCounts = {};
  
  // Get the selected letters (initial selection and purchased)
  const alreadyRevealedLetters = new Set();
  marketState.vowels.forEach(vowel => alreadyRevealedLetters.add(vowel));
  marketState.consonants.forEach(consonant => alreadyRevealedLetters.add(consonant));
  
  // Check if this word has a revealed suffix
  const wordsWithRevealedSuffixes = getWordsWithRevealedSuffixes();
  const hasSuffix = wordsWithRevealedSuffixes.includes(wordIndex);
  let suffixStart = word.length;
  
  // If this word has a revealed suffix, get its starting position
  if (hasSuffix) {
    const suffix = getWordSuffix(word);
    if (suffix && suffix.ending) {
      suffixStart = word.length - suffix.ending.length;
      console.log(`Word "${word}" has revealed suffix "${suffix.ending}" starting at index ${suffixStart}`);
    }
  }
  
  // Count each letter in the word, excluding already revealed letters AND suffix letters
  word.toLowerCase().split("").forEach((char, charIndex) => {
    // Skip if this char is part of a revealed suffix (matches initializeLetterCounts logic)
    if (hasSuffix && charIndex >= suffixStart) {
      console.log(`Skipping suffix character '${char}' at position ${charIndex} in word "${word}"`);
      return;
    }
    
    // Skip if this char is already revealed through selection or purchase
    if (alreadyRevealedLetters.has(char)) {
      return;
    }
    
    wordLetterCounts[char] = (wordLetterCounts[char] || 0) + 1;
  });
  
  // Update the global counts
  Object.entries(wordLetterCounts).forEach(([char, count]) => {
    if (letterCounts[char]) {
      letterCounts[char] = Math.max(0, letterCounts[char] - count);
      if (letterCounts[char] === 0) {
        delete letterCounts[char];
      }
    }
  });
  
  console.log(`Updated letter counts after finding word "${word}" (suffix excluded: ${hasSuffix}):`, letterCounts);
}

/**
 * Updates letter counts when a letter is purchased/revealed
 * @private
 * @param {string} letter - The letter that was purchased
 */
function clearLetterCount(letter) {
  // Always convert to lowercase for consistency
  const lowerLetter = letter.toLowerCase();
  
  // Remove this letter from the counts entirely
  if (lowerLetter in letterCounts) {
    delete letterCounts[lowerLetter];
    console.log(`Cleared letter count for '${lowerLetter}' after purchase`);
  }
}

/**
 * Returns current count of remaining letters in hidden words
 * @returns {Record<string, number>} Object with letter counts
 */
export function getLetterCounts() {
  return { ...letterCounts };
}

/**
 * Reveals a word to the player with a score penalty.
 * Delegates scoring/completion to the engine; keeps local state in sync.
 * @param {number} wordIndex - The index of the word to reveal
 * @returns {{success: boolean, pointsDeducted: number, gameComplete: boolean}} Result
 */
export function revealWord(wordIndex) {
  const word = gameState.current.words[wordIndex];

  if (!word || word.found || word.revealed) {
    return { success: false, pointsDeducted: 0, gameComplete: false };
  }

  if (_engine) {
    // Calculate penalty locally (source of truth)
    const params = gameState.config.parameters;
    const penalty = params?.marketplace?.wordReveal?.cost ?? 8;
    const pointsToDeduct = Math.min(gameState.current.score, penalty);
    gameState.current.score -= pointsToDeduct;
    word.revealed = true;
    // Sync engine item and score
    if (_engine._items[wordIndex]) _engine._items[wordIndex].revealed = true;
    _engine._score = gameState.current.score;
    _engine._completed = _engine._items.every(it => it.solved || it.revealed);
    updateLetterCounts(word.word);

    if (!gameState.current.shownWordIndices.includes(wordIndex)) {
      gameState.current.shownWordIndices.push(wordIndex);
    }

    const unstartedIndices = getCurrentWords()
      .map((w, i) => (w.found || w.revealed ? -1 : i))
      .filter(i => i !== -1 && !gameState.current.shownWordIndices.includes(i));
    if (unstartedIndices.length > 0) {
      const pick = unstartedIndices[Math.floor(Math.random() * unstartedIndices.length)];
      gameState.current.shownWordIndices.push(pick);
    }

    const gameComplete = getCurrentWords().every((w) => w.found || w.revealed);
    return { success: true, pointsDeducted: pointsToDeduct, gameComplete };
  }

  // Fallback (no engine)
  const params = gameState.config.parameters;
  const penalty = params?.marketplace?.wordReveal?.cost ?? 8;
  const pointsToDeduct = Math.min(gameState.current.score, penalty);
  gameState.current.score -= pointsToDeduct;
  word.revealed = true;
  updateLetterCounts(word.word);
  if (!gameState.current.shownWordIndices.includes(wordIndex)) {
    gameState.current.shownWordIndices.push(wordIndex);
  }
  const unstartedIndices = getCurrentWords()
    .map((w, i) => (w.found || w.revealed ? -1 : i))
    .filter(i => i !== -1 && !gameState.current.shownWordIndices.includes(i));
  if (unstartedIndices.length > 0) {
    const pick = unstartedIndices[Math.floor(Math.random() * unstartedIndices.length)];
    gameState.current.shownWordIndices.push(pick);
  }
  const gameComplete = getCurrentWords().every((w) => w.found || w.revealed);
  return { success: true, pointsDeducted: pointsToDeduct, gameComplete };
}

/**
 * Updates the active clue index for a word
 * @param {number} wordIndex - The index of the word in the game state
 * @param {number} clueIndex - The index of the clue to set as active
 * @returns {boolean} Whether the update was successful
 */
export function updateActiveClueIndex(wordIndex, clueIndex) {
  if (wordIndex < 0 || wordIndex >= gameState.current.words.length) {
    console.error(`Invalid word index: ${wordIndex}`);
    return false;
  }
  
  const word = gameState.current.words[wordIndex];
  if (word.found || word.revealed) {
    return false; // Can't change clue for found or revealed words
  }
  
  // Ensure clue index is valid (word has clues array)
  if (!word.clues || !Array.isArray(word.clues) || clueIndex >= word.clues.length) {
    console.error(`Invalid clue index: ${clueIndex} for word at index ${wordIndex}`);
    return false;
  }
  
  // Update the active clue index
  word.activeClueIndex = clueIndex;
  
  // Update the lowest clue index seen (higher index = easier clue)
  // Skip penalty if this word was upgraded by the golden key
  if (clueIndex > word.lowestClueIndexSeen && !word.goldenKeyProtected) {
    word.lowestClueIndexSeen = clueIndex;
    console.log(`Updated lowest clue index seen for word "${word.word}" to ${clueIndex}`);
  }
  
  console.log(`Updated active clue index for word "${word.word}" to ${clueIndex}`);
  return true;
}

/**
 * Gets the active clue index for a word
 * @param {number} wordIndex - The index of the word in the game state
 * @returns {number} The active clue index (0, 1, or 2)
 */
export function getActiveClueIndex(wordIndex) {
  if (wordIndex < 0 || wordIndex >= gameState.current.words.length) {
    console.error(`Invalid word index: ${wordIndex}`);
    return 0;
  }
  
  return gameState.current.words[wordIndex].activeClueIndex || 0;
}

/**
 * Gets the lowest (easiest) clue index seen for a word
 * @param {number} wordIndex - The index of the word in the game state
 * @returns {number} The lowest clue index seen (0, 1, or 2)
 */
export function getLowestClueIndexSeen(wordIndex) {
  if (wordIndex < 0 || wordIndex >= gameState.current.words.length) {
    console.error(`Invalid word index: ${wordIndex}`);
    return 0;
  }
  
  return gameState.current.words[wordIndex].lowestClueIndexSeen || 0;
}

/**
 * Checks if a word ends with any of the revealed suffixes
 * @param {string} word - The word to check
 * @returns {Object|null} The matching suffix object or null if no match
 */
export function getMatchingSuffix(word) {
  if (!word || typeof word !== 'string') return null;
  
  const lowerWord = word.toLowerCase();
  const revealedSuffixes = getRevealedSuffixes();
  
  for (const suffix of revealedSuffixes) {
    if (lowerWord.endsWith(suffix.ending)) {
      return suffix;
    }
  }
  
  return null;
}

/**
 * Checks if a character at a specific position in a word is part of a revealed suffix
 * @param {string} word - The word to check
 * @param {number} charIndex - The character index to check
 * @param {number} wordIndex - The index of the word in the game state
 * @returns {boolean} True if the character is part of a revealed suffix
 */
export function isPartOfRevealedSuffix(word, charIndex, wordIndex) {
  if (!word || typeof word !== 'string') return false;
  
  // Check if this word's index is in the revealed list
  const revealedWordIndices = getWordsWithRevealedSuffixes();
  if (!revealedWordIndices.includes(wordIndex)) {
    return false;
  }
  
  // Get the suffix for this word
  const suffix = getWordSuffix(word);
  if (!suffix || !suffix.ending) {
    // This shouldn't happen for words in the revealed list
    console.debug(`No valid suffix found for word "${word}" at index ${wordIndex}`);
    return false;
  }
  
  // Calculate the start position of the suffix more accurately
  // Make sure we're using the actual word characters
  const suffixStart = word.length - suffix.ending.length;
  
  // Check if this character is in the suffix portion
  const isPartOfSuffix = charIndex >= suffixStart;
  
  if (isPartOfSuffix) {
    console.debug(`Revealing suffix char at index ${charIndex} in word "${word}" with suffix "${suffix.ending}"`);
  }
  
  return isPartOfSuffix;
}

/**
 * Initializes the suffix reveal system, revealing the suffixes for the initial set of words
 */
export function initializeSuffixes() {
  // Reset any previously revealed word suffixes
  gameState.current.wordsWithRevealedSuffixes = [];
  
  const suffixConfig = getSuffixConfig();
  if (!suffixConfig || !suffixConfig.suffixes || !Array.isArray(suffixConfig.suffixes)) {
    console.warn("No valid suffix configuration found");
    return;
  }
  
  console.log("Initializing suffixes with config:", suffixConfig);
  
  // Find all words that have suffixes defined in the config
  const words = getCurrentWords();
  const wordsWithSuffixes = words
    .map((word, index) => {
      const suffix = getWordSuffix(word.word);
      return { 
        word, 
        index, 
        suffix: suffix ? suffix.ending : null 
      };
    })
    .filter(item => item.suffix !== null && !item.word.found);
  
  console.log("Words with suffixes:", wordsWithSuffixes.map(item => 
    `${item.word.word} (${item.suffix})`
  ));
  
  if (wordsWithSuffixes.length === 0) {
    console.warn("No words with suffixes found");
    return;
  }
  
  // Shuffle the words to randomly select which ones to reveal
  const shuffledWords = [...wordsWithSuffixes];
  for (let i = shuffledWords.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffledWords[i], shuffledWords[j]] = [shuffledWords[j], shuffledWords[i]];
  }
  
  // Choose first N words (or fewer if not enough available)
  const initialCount = Math.min(gameState.current.initialSuffixesShown, shuffledWords.length);
  
  // Add the word indices to the revealed list
  const revealedWordIndices = [];
  for (let i = 0; i < initialCount; i++) {
    const wordIndex = shuffledWords[i].index;
    revealedWordIndices.push(wordIndex);
    gameState.current.wordsWithRevealedSuffixes.push(wordIndex);
    
    // Note: Letter counts will be initialized after this function completes
    // No need to update them here during initial setup
  }
  
  console.log(`Revealed suffixes for ${revealedWordIndices.length} initial words:`, 
    revealedWordIndices.map(idx => {
      const word = words[idx].word;
      const suffix = getWordSuffix(word);
      return `${word} (${suffix ? suffix.ending : 'unknown'})`;
    }));
}

/**
 * Reveals the suffix for the next word after a guess
 * @returns {boolean} True if a new word suffix was revealed, false otherwise
 */
export function revealNextSuffix() {
  // Find all words that have suffixes defined in the config
  const words = getCurrentWords();
  const alreadyRevealedIndices = getWordsWithRevealedSuffixes();
  
  // Get words with suffixes that haven't been revealed yet and aren't found
  const revealableWords = words
    .map((word, index) => ({ word, index }))
    .filter(item => {
      // Skip if this word's suffix is already revealed or the word is found
      if (alreadyRevealedIndices.includes(item.index) || item.word.found) {
        return false;
      }
      
      // Check if the word has a valid suffix
      return getWordSuffix(item.word.word) !== null;
    });
  
  // If we have no more words to reveal, return false
  if (revealableWords.length === 0) {
    console.log("No more word suffixes to reveal");
    return false;
  }
  
  // Randomly select one word to reveal its suffix
  const randomIndex = Math.floor(Math.random() * revealableWords.length);
  const selectedWord = revealableWords[randomIndex];
  
  // Add the word index to the revealed list
  gameState.current.wordsWithRevealedSuffixes.push(selectedWord.index);
  
  // Update letter counts for this word's suffix
  updateLetterCountsForWordSuffix(selectedWord.index);
  
  // Get the suffix for logging
  const suffix = getWordSuffix(selectedWord.word.word);
  
  console.log(`Revealed suffix for word "${selectedWord.word.word}" (${suffix ? suffix.ending : 'unknown'})`);
  return true;
}

/**
 * Updates letter counts for a word's revealed suffix
 * @param {number} wordIndex - The index of the word with revealed suffix
 */
function updateLetterCountsForWordSuffix(wordIndex) {
  const words = getCurrentWords();
  
  // Make sure the word index is valid
  if (wordIndex < 0 || wordIndex >= words.length) {
    console.error(`Invalid word index: ${wordIndex}`);
    return;
  }
  
  const word = words[wordIndex];
  
  // Skip if the word is already found
  if (word.found) return;
  
  // Get the suffix for this word
  const suffix = getWordSuffix(word.word);
  if (!suffix || !suffix.ending) return;
  
  // Count occurrences of each letter in the suffix for this specific word
  const suffixLetterCounts = {};
  const wordSuffixStart = word.word.length - suffix.ending.length;
  const wordSuffix = word.word.substring(wordSuffixStart);
  
  // Count each letter in the suffix
  wordSuffix.split("").forEach(letter => {
    const lowerLetter = letter.toLowerCase();
    suffixLetterCounts[lowerLetter] = (suffixLetterCounts[lowerLetter] || 0) + 1;
  });
  
  // Now decrement the global letter counts based on actual counts from this suffix
  Object.entries(suffixLetterCounts).forEach(([letter, count]) => {
    if (letterCounts[letter]) {
      letterCounts[letter] = Math.max(0, letterCounts[letter] - count);
      if (letterCounts[letter] === 0) {
        delete letterCounts[letter];
      }
    }
  });
  
  console.log(`Updated letter counts for word "${word.word}" with suffix "${suffix.ending}"`);
}

// ─── Golden Key & Golden Coin ────────────────────────────────────────────────

/**
 * Returns "reveal" if there are any word indices not yet in shownWordIndices,
 * or "upgrade" if all clues are already visible.
 * @returns {"reveal"|"upgrade"}
 */
export function getGoldenKeyMode() {
  const allIndices = gameState.current.words.map((_, i) => i).filter(i => {
    const w = gameState.current.words[i];
    return !w.found && !w.revealed;
  });
  const shown = gameState.current.shownWordIndices;
  const hasHidden = allIndices.some(i => !shown.includes(i));
  return hasHidden ? "reveal" : "upgrade";
}

/**
 * Uses the golden key: reveals next hidden clue OR upgrades one clue tier.
 * No lowestClueIndexSeen penalty on upgrade.
 * @param {number} [wordIndex] - Required only for "upgrade" mode (player-chosen word)
 * @returns {{success: boolean, mode?: "reveal"|"upgrade", wordIndex?: number}}
 */
export function useGoldenKey(wordIndex) {
  if (gameState.current.goldenKeyUsed) return { success: false };

  const mode = getGoldenKeyMode();

  if (mode === "reveal") {
    // Find lowest unfound word index not yet shown
    const unfoundIndices = gameState.current.words
      .map((w, i) => (!w.found && !w.revealed ? i : -1))
      .filter(i => i !== -1 && !gameState.current.shownWordIndices.includes(i));
    if (unfoundIndices.length === 0) return { success: false };
    const nextIndex = unfoundIndices[0];
    gameState.current.shownWordIndices.push(nextIndex);
    gameState.current.goldenKeyUsed = true;
    gameState.current.assistedPlay = true;
    return { success: true, mode: "reveal", wordIndex: nextIndex };
  }

  // Upgrade mode — wordIndex is required
  if (wordIndex === undefined || wordIndex === null) return { success: false };
  const word = gameState.current.words[wordIndex];
  if (!word || word.found || word.revealed) return { success: false };
  if (!word.clues || !Array.isArray(word.clues)) return { success: false };
  const nextClueIndex = (word.activeClueIndex || 0) + 1;
  if (nextClueIndex >= word.clues.length) return { success: false }; // Already at easiest tier

  // Upgrade the clue index WITHOUT touching lowestClueIndexSeen (no penalty)
  word.activeClueIndex = nextClueIndex;
  word.goldenKeyProtected = true; // Prevent lowestClueIndexSeen from updating after GK upgrade
  gameState.current.goldenKeyUsed = true;
  gameState.current.assistedPlay = true;
  return { success: true, mode: "upgrade", wordIndex };
}

/**
 * Returns an array of letters eligible for the golden coin reveal.
 * A letter is eligible if its count in letterCounts is <= maxFrequency and not yet purchased.
 * @returns {Array<{letter: string, count: number}>}
 */
export function getEligibleCoinLetters() {
  const params = gameState.config.parameters;
  const maxFreq = params?.golden?.coin?.maxFrequency ?? 2;
  return Object.entries(letterCounts)
    .filter(([letter, count]) =>
      count > 0 &&
      count <= maxFreq &&
      !marketState.vowels.has(letter) &&
      !marketState.consonants.has(letter)
    )
    .map(([letter, count]) => ({ letter, count }));
}

/**
 * Uses the golden coin: reveals all instances of a rare letter for a flat cost.
 * @param {string} letter - The letter to reveal
 * @returns {{success: boolean, letter?: string, cost?: number}}
 */
export function useGoldenCoin(letter) {
  if (gameState.current.goldenCoinUsed) return { success: false };

  const params = gameState.config.parameters;
  const maxFreq = params?.golden?.coin?.maxFrequency ?? 2;
  const cost = params?.golden?.coin?.cost ?? 3;

  const lowerLetter = letter.toLowerCase();
  const count = letterCounts[lowerLetter] || 0;
  if (count === 0 || count > maxFreq) return { success: false };

  // Deduct cost, floor at 0
  gameState.current.score = Math.max(0, gameState.current.score - cost);
  if (_engine) _engine._score = gameState.current.score;

  // Reveal the letter in the marketplace (same as purchaseVowel/purchaseConsonant)
  const isVowel = "aeiou".includes(lowerLetter);
  if (isVowel) {
    marketState.vowels.add(lowerLetter);
  } else {
    marketState.consonants.add(lowerLetter);
  }
  clearLetterCount(lowerLetter);

  gameState.current.goldenCoinUsed = true;
  gameState.current.assistedPlay = true;
  return { success: true, letter: lowerLetter, cost };
}
