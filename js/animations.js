/**
 * @fileoverview Animation effects for the ClueChain game.
 * Provides visual feedback for game events like correct guesses and game completion.
 * @module animations
 */

/**
 * Creates a firework animation at a random position on the screen
 * @param {number} [count=1] - Number of fireworks to create
 */
export function createFirework(count = 1) {
  const container = document.getElementById('celebration-container');
  if (!container) return;

  for (let i = 0; i < count; i++) {
    // Random position within the viewport
    const x = Math.random() * window.innerWidth;
    const y = Math.random() * (window.innerHeight * 0.7); // Keep in top 70% of screen
    
    // Random color
    const hue = Math.floor(Math.random() * 360);
    const firework = document.createElement('div');
    firework.className = 'firework';
    firework.style.left = `${x}px`;
    firework.style.top = `${y}px`;
    firework.style.backgroundColor = `hsl(${hue}, 100%, 50%)`;
    
    container.appendChild(firework);
    
    // Remove after animation completes
    setTimeout(() => {
      firework.remove();
    }, 1500);
  }
}

/**
 * Creates confetti animation
 * @param {number} [count=30] - Number of confetti pieces
 */
export function createConfetti(count = 30) {
  const container = document.getElementById('celebration-container');
  if (!container) return;

  const colors = ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', 
                 '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4CAF50', 
                 '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722'];
  
  for (let i = 0; i < count; i++) {
    const confetti = document.createElement('div');
    confetti.className = 'confetti';
    
    // Random position, size, color, and delay
    const x = Math.random() * window.innerWidth;
    const size = Math.random() * 10 + 5;
    const colorIndex = Math.floor(Math.random() * colors.length);
    const delay = Math.random() * 3;
    
    confetti.style.left = `${x}px`;
    confetti.style.width = `${size}px`;
    confetti.style.height = `${size}px`;
    confetti.style.backgroundColor = colors[colorIndex];
    confetti.style.animationDelay = `${delay}s`;
    
    // Random shape (square, rectangle, or circle)
    const shape = Math.floor(Math.random() * 3);
    if (shape === 0) {
      confetti.style.borderRadius = '50%';
    } else if (shape === 1) {
      confetti.style.borderRadius = '0';
    } else {
      confetti.style.borderRadius = '4px';
      confetti.style.height = `${size * 1.5}px`;
    }
    
    container.appendChild(confetti);
    
    // Remove after animation completes
    setTimeout(() => {
      confetti.remove();
    }, 4000 + delay * 1000);
  }
}

/**
 * Displays a mild celebration for game completion when the last word was revealed (given up)
 */
export function celebrateRevealGameOver() {
  // Single small burst + a handful of confetti
  createFirework(1);
  createConfetti(20);
}

/**
 * Displays a big celebration animation for game completion
 */
export function celebrateGameOver() {
  // Initial burst of fireworks
  for (let i = 0; i < 10; i++) {
    setTimeout(() => {
      createFirework(2);
    }, i * 300);
  }
  
  // Add confetti
  createConfetti(100);
  
  // Periodic fireworks
  let count = 0;
  const interval = setInterval(() => {
    createFirework(1);
    count++;
    
    if (count > 15) {
      clearInterval(interval);
    }
  }, 1000);
}

/**
 * Creates sparkle effects around an element
 * @param {HTMLElement} element - The element to add sparkles around
 * @param {number} [count=10] - Number of sparkles
 */
export function createSparklesAroundElement(element, count = 10) {
  if (!element) return;
  
  const rect = element.getBoundingClientRect();
  const container = document.getElementById('celebration-container');
  if (!container) return;
  
  for (let i = 0; i < count; i++) {
    const sparkle = document.createElement('div');
    sparkle.className = 'sparkle';
    
    // Random position around the element
    const offsetX = (Math.random() - 0.5) * 2 * (rect.width + 20);
    const offsetY = (Math.random() - 0.5) * 2 * (rect.height + 20);
    
    const x = rect.left + rect.width / 2 + offsetX;
    const y = rect.top + rect.height / 2 + offsetY;
    
    // Random color (gold, yellow, white)
    const colors = ['#FFD700', '#FFEB3B', '#FFC107', '#FFFFFF'];
    const colorIndex = Math.floor(Math.random() * colors.length);
    
    sparkle.style.left = `${x}px`;
    sparkle.style.top = `${y}px`;
    sparkle.style.backgroundColor = colors[colorIndex];
    
    container.appendChild(sparkle);
    
    // Remove after animation completes
    setTimeout(() => {
      sparkle.remove();
    }, 1000);
  }
}

/**
 * Highlights a correct word with animation and sparkles
 * @param {HTMLElement} wordElement - The word element to highlight
 */
export function highlightCorrectWord(wordElement) {
  if (!wordElement) return;
  
  // Add pulse animation class
  wordElement.classList.add('word-correct-animation');
  
  // Create sparkles around the word
  createSparklesAroundElement(wordElement, 15);
  
  // Remove animation class after it completes
  setTimeout(() => {
    wordElement.classList.remove('word-correct-animation');
  }, 1000);
}