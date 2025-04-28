document.addEventListener("DOMContentLoaded", function () {
  console.log("Survey page loaded.");

  const conversationContainer = document.getElementById(
    "conversation-container"
  );
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");
  const nextButton = document.getElementById("next-button");

  let conversations = []; // Array to hold all conversations for the batch
  let currentConversationIndex = 0;
  let totalConversationsInBatch = 0;
  let currentBatch = 0;
  let username = "";

  // Function to update the progress bar
  function updateProgressBar() {
    const progress = (currentConversationIndex + 1) / totalConversationsInBatch;
    progressBar.style.width = `${progress * 100}%`;
    progressText.textContent = `Conversation ${
      currentConversationIndex + 1
    } of ${totalConversationsInBatch} (Batch ${currentBatch})`;
  }

  // Function to display a conversation
  function displayConversation(conversation) {
    conversationContainer.innerHTML = ""; // Clear previous conversation

    const conversationElement = document.createElement("div");
    conversationElement.classList.add("conversation"); // Add a class for styling

    const titleElement = document.createElement("h3");
    titleElement.textContent = conversation.title;

    const contentElement = document.createElement("div"); // Use a div for potentially complex content
    // Displaying cleaned_conversation as an example, format as needed
    contentElement.innerHTML =
      "<pre>" +
      JSON.stringify(conversation.cleaned_conversation, null, 2) +
      "</pre>";

    conversationElement.appendChild(titleElement);
    conversationElement.appendChild(contentElement);
    conversationContainer.appendChild(conversationElement);
  }

  // Function to display the next conversation
  function displayNextConversation() {
    currentConversationIndex++;

    if (currentConversationIndex < totalConversationsInBatch) {
      displayConversation(conversations[currentConversationIndex]);
      updateProgressBar();
    } else {
      // End of survey
      conversationContainer.innerHTML =
        "<p>You have completed this batch of the survey. Thank you!</p>";
      nextButton.style.display = "none"; // Hide the next button
      progressText.textContent = `Batch ${currentBatch} Completed!`;
      progressBar.style.width = "100%";
    }
  }

  // Initialize the survey
  function initializeSurvey() {
    const initialDataElement = document.getElementById("initial-survey-data");
    if (initialDataElement) {
      const initialData = JSON.parse(initialDataElement.textContent);
      username = initialData.username;
      conversations = initialData.conversations; // Get all conversations
      totalConversationsInBatch = initialData.total_in_batch;
      currentBatch = initialData.current_batch;
      currentConversationIndex = 0; // Start with the first conversation

      if (totalConversationsInBatch > 0) {
        displayConversation(conversations[currentConversationIndex]);
        updateProgressBar();

        // Add event listener to the next button
        nextButton.addEventListener("click", displayNextConversation);
      } else {
        conversationContainer.innerHTML =
          "<p>No conversations found for this batch.</p>";
        nextButton.style.display = "none";
        progressText.textContent = `Batch ${currentBatch}`;
        progressBar.style.width = "0%";
      }
    } else {
      console.error("Initial survey data not found in the HTML.");
      conversationContainer.innerHTML =
        "<p>Error initializing survey data.</p>";
      nextButton.style.display = "none";
    }
  }

  // Call initializeSurvey when the DOM is ready
  initializeSurvey();
});
