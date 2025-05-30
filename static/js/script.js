document.addEventListener("DOMContentLoaded", function () {
  console.log("Survey page loaded.");

  const conversationContainer = document.getElementById(
    "conversation-container"
  );
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");
  const nextButton = document.getElementById("next-button");
  const backButton = document.getElementById("back-button"); // Get the back button
  const completeBatchButton = document.getElementById("complete-batch-button"); // Get the complete batch button

  let conversations = []; // Array to hold all conversations for the batch
  let currentConversationIndex = 0;
  let totalConversationsInBatch = 0;
  let currentBatch = 0;
  let username = "";

  let assignedBatches = []; // Array to hold assigned batches
  let completedBatches = []; // Array to hold completed batches

  // Function to display the batch status
  function displayBatchStatus(assigned, completed, current) {
    const batchStatusDiv = document.getElementById("batch-status");
    if (!batchStatusDiv) return;

    batchStatusDiv.innerHTML = "<h2>Batch Status</h2>"; // Clear and add title

    const totalAssigned = assigned.length;
    const totalCompleted = completed.length;
    const totalRemaining = totalAssigned - totalCompleted;

    let statusText = `Done ${totalCompleted} out of ${totalAssigned} batches.`;

    if (current !== null && totalCompleted < totalAssigned) {
      statusText += ` Currently on batch ${current}.`;
      if (totalRemaining > 1) {
        statusText += ` Still ${totalRemaining} batches to go.`;
      } else if (totalRemaining === 1) {
        statusText += ` Still ${totalRemaining} batch to go.`;
      }
    } else if (totalCompleted === totalAssigned && totalAssigned > 0) {
      statusText = `All ${totalAssigned} batches completed. Thank you!`;
    } else if (totalAssigned === 0) {
      statusText = "No batches assigned.";
    }

    const statusParagraph = document.createElement("p");
    statusParagraph.textContent = statusText;
    batchStatusDiv.appendChild(statusParagraph);
  }

  // Function to display the total number of completed responses
  function displayTotalCompletedResponses(totalCompleted) {
    const totalCompletedElement = document.getElementById(
      "total-completed-responses"
    );
    if (totalCompletedElement) {
      totalCompletedElement.textContent = `Total Completed Responses: ${totalCompleted}`;
    }
  }

  // Function to update the progress bar
  function updateProgressBar() {
    const progress = (currentConversationIndex + 1) / totalConversationsInBatch;
    progressBar.style.width = `${progress * 100}%`;
    progressText.textContent = `Conversation ${
      currentConversationIndex + 1
    } of ${totalConversationsInBatch} (Batch ${currentBatch})`;
  }

  // Function to display a conversation with formatted turns
  function displayConversation(conversation) {
    conversationContainer.innerHTML = ""; // Clear previous conversation

    // Add context before the conversation
    const contextElement = document.createElement("div");
    contextElement.classList.add("context-container"); // Add a class for styling
    contextElement.innerHTML = `<h3>Context:</h3><p>${conversation.context}</p>`;
    conversationContainer.appendChild(contextElement);

    const conversationElement = document.createElement("div");
    conversationElement.classList.add("conversation"); // Add a class for styling

    const titleElement = document.createElement("h3");
    // Use conversation.uuid and conversation.title
    titleElement.textContent = `Conversation ID: ${conversation.uuid} - ${conversation.title}`;
    conversationElement.appendChild(titleElement);

    // Check if cleaned_conversation exists and is an array
    if (
      conversation.cleaned_conversation &&
      Array.isArray(conversation.cleaned_conversation)
    ) {
      conversation.cleaned_conversation.forEach((turn) => {
        const turnElement = document.createElement("div");
        turnElement.classList.add("turn"); // General class for a turn

        // Add speaker-specific class based on 'role'
        if (turn.role) {
          turnElement.classList.add(
            `${turn.role.toLowerCase().replace(" ", "-")}-turn`
          );
        }

        const speakerElement = document.createElement("strong");
        // Use turn.role for speaker
        speakerElement.textContent = `${turn.role || "Unknown"}: `; // Handle potential missing role

        const textContent = turn.content || ""; // Handle potential missing content
        // Split text into sentences (basic split by ., !, ?)
        const sentences = textContent.match(/[^.!?]+[.!?]+/g) || [textContent];

        turnElement.appendChild(speakerElement); // Add speaker before sentences

        sentences.forEach((sentenceText) => {
          const sentenceElement = document.createElement("span");
          sentenceElement.textContent = sentenceText.trim();
          sentenceElement.classList.add("sentence"); // Add a class to identify sentences
          turnElement.appendChild(sentenceElement);
        });

        conversationElement.appendChild(turnElement);
      });

      // Add click event listener to the conversation container
      conversationElement.addEventListener("click", function (event) {
        const target = event.target;
        // Check if the clicked element is a sentence span
        if (target.classList.contains("sentence")) {
          target.classList.toggle("highlighted-sentence");
        }
      });
    } else {
      // Fallback if cleaned_conversation is not in the expected format
      const errorElement = document.createElement("p");
      errorElement.textContent =
        "Conversation data is not in the expected format.";
      errorElement.style.color = "red";
      conversationElement.appendChild(errorElement);
      console.error("Invalid conversation data:", conversation);
    }

    conversationContainer.appendChild(conversationElement);

    // Update button visibility
    backButton.style.display =
      currentConversationIndex > 0 ? "inline-block" : "none";
    nextButton.style.display =
      currentConversationIndex < totalConversationsInBatch - 1
        ? "inline-block"
        : "none";

    // Handle case where it's the last conversation
    if (currentConversationIndex >= totalConversationsInBatch - 1) {
      nextButton.style.display = "none"; // Hide next button explicitly
      completeBatchButton.style.display = "inline-block"; // Show the complete batch button
    } else {
      completeBatchButton.style.display = "none"; // Hide complete batch button
    }
  }

  // Function to submit survey data for the current conversation
  async function submitSurveyData() {
    const currentConversation = conversations[currentConversationIndex];
    const surveyQuestionsDiv = document.getElementById("survey-questions");
    const surveyResponses = {
      username: username,
      conversation_uuid: currentConversation.uuid,
    };

    if (surveyQuestionsDiv) {
      const questionDivs = surveyQuestionsDiv.querySelectorAll(".question");
      questionDivs.forEach((questionDiv) => {
        const radioButtons = questionDiv.querySelectorAll(
          'input[type="radio"]'
        );
        radioButtons.forEach((radio) => {
          if (radio.checked) {
            surveyResponses[radio.name] = parseInt(radio.value);
          }
        });
      });
    }

    // Collect highlighted text data
    const highlightedSentences = conversationContainer.querySelectorAll(
      ".highlighted-sentence"
    );
    const highlightedText = Array.from(highlightedSentences)
      .map((sentence) => sentence.textContent)
      .join(" <<>> ");
    surveyResponses["highlighted_text"] = highlightedText;

    try {
      const response = await fetch("/submit_survey", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(surveyResponses),
      });

      const result = await response.json();
      console.log("Survey submission result:", result);

      if (result.status !== "success") {
        console.error("Failed to submit survey data:", result.message);
        // Optionally display an error message to the user
      }
    } catch (error) {
      console.error("Error submitting survey data:", error);
      // Optionally display an error message to the user
    }
  }

  // Function to display the next conversation
  async function displayNextConversation() {
    // Submit survey data for the current conversation before moving to the next
    await submitSurveyData();

    currentConversationIndex++;

    // Reset survey selections and set default to "Strongly Disagree"
    const surveyQuestionsDiv = document.getElementById("survey-questions");
    if (surveyQuestionsDiv) {
      const questionDivs = surveyQuestionsDiv.querySelectorAll(".question");
      questionDivs.forEach((questionDiv) => {
        const radioButtons = questionDiv.querySelectorAll(
          'input[type="radio"]'
        );
        radioButtons.forEach((radio) => {
          radio.checked = false; // Uncheck all first
        });
        // Check the "Strongly Disagree" option (value="1")
        const stronglyDisagreeRadio = questionDiv.querySelector(
          'input[type="radio"][value="1"]'
        );
        if (stronglyDisagreeRadio) {
          stronglyDisagreeRadio.checked = true;
        }
      });
    }

    // Scroll to the top of the page
    window.scrollTo(0, 0);

    if (currentConversationIndex < totalConversationsInBatch) {
      displayConversation(conversations[currentConversationIndex]);
      updateProgressBar();
      // Show back button if not the first conversation
      backButton.style.display = "inline-block";
    } else {
      // End of survey - adjust index back if over limit
      currentConversationIndex = totalConversationsInBatch - 1;
      conversationContainer.innerHTML =
        "<p>You have completed this batch of the survey. Thank you!</p>";
      nextButton.style.display = "none"; // Hide the next button
      completeBatchButton.style.display = "inline-block"; // Show the complete batch button
      backButton.style.display =
        totalConversationsInBatch > 1 ? "inline-block" : "none"; // Show back if there was more than one convo
      progressText.textContent = `Batch ${currentBatch} Completed!`;
      progressBar.style.width = "100%";
      // Optionally redirect the user or show a final message
    }
  }

  // Function to display the previous conversation
  function displayPreviousConversation() {
    if (currentConversationIndex > 0) {
      currentConversationIndex--;
      displayConversation(conversations[currentConversationIndex]);
      updateProgressBar();
      // Hide back button if now on the first conversation
      backButton.style.display =
        currentConversationIndex === 0 ? "none" : "inline-block";
      // Ensure next button is visible if not on the last conversation
      nextButton.style.display = "inline-block";
    }
  }

  // Initialize the survey
  function initializeSurvey() {
    const initialDataElement = document.getElementById("initial-survey-data");
    if (initialDataElement) {
      const initialData = JSON.parse(initialDataElement.textContent);
      username = initialData.username;
      let allConversations = initialData.conversations; // Get all conversations for the batch
      currentBatch = initialData.current_batch;
      currentConversationIndex = 0; // Start with the first conversation

      // Get assigned and completed batches from initial data
      assignedBatches = initialData.assigned_batches || [];
      completedBatches = initialData.completed_batches || [];

      // Fetch completed surveys for the user
      fetch(`/completed_surveys/${username}`)
        .then((response) => response.json())
        .then((completedSurveysResult) => {
          if (completedSurveysResult.status === "success") {
            const completedConversationUuids = completedSurveysResult.data.map(
              (response) => response.conversation_uuid
            );

            // Filter out conversations that have already been completed by the user
            conversations = allConversations.filter(
              (conversation) =>
                !completedConversationUuids.includes(conversation.uuid)
            );

            totalConversationsInBatch = conversations.length;

            // Display batch status (can be updated later to include total completed responses)
            displayBatchStatus(assignedBatches, completedBatches, currentBatch);

            // Display total completed responses
            displayTotalCompletedResponses(completedSurveysResult.data.length);

            if (totalConversationsInBatch > 0) {
              displayConversation(conversations[currentConversationIndex]);
              updateProgressBar();

              // Add event listeners
              nextButton.addEventListener("click", displayNextConversation);
              backButton.addEventListener("click", displayPreviousConversation); // Add listener for back button
              completeBatchButton.addEventListener("click", completeBatch); // Add listener for complete batch button

              // Initially hide back button and disable next button
              backButton.style.display = "none";
              nextButton.disabled = true;

              // Add event listeners to survey radio buttons
              const surveyQuestionsDiv =
                document.getElementById("survey-questions");
              if (surveyQuestionsDiv) {
                surveyQuestionsDiv.addEventListener(
                  "change",
                  checkSurveyCompletion
                );
              }

              // Initial check for survey completion
              checkSurveyCompletion();
            } else {
              conversationContainer.innerHTML =
                "<p>You have completed all conversations in this batch.</p>";
              nextButton.style.display = "none";
              backButton.style.display = "none"; // Also hide back button if no conversations
              progressText.textContent = `Batch ${currentBatch}`;
              progressBar.style.width = "100%"; // Indicate batch is fully processed
              completeBatchButton.style.display = "inline-block"; // Show complete batch button if all are done
            }
          } else {
            console.error(
              "Failed to fetch completed surveys:",
              completedSurveysResult.message
            );
            // Proceed with all conversations if fetching completed surveys fails
            conversations = allConversations;
            totalConversationsInBatch = conversations.length;
            // Display batch status (can be updated later to include total completed responses)
            displayBatchStatus(assignedBatches, completedBatches, currentBatch);
            // Display total completed responses (0 if fetch failed)
            displayTotalCompletedResponses(0);

            if (totalConversationsInBatch > 0) {
              displayConversation(conversations[currentConversationIndex]);
              updateProgressBar();

              // Add event listeners
              nextButton.addEventListener("click", displayNextConversation);
              backButton.addEventListener("click", displayPreviousConversation); // Add listener for back button
              completeBatchButton.addEventListener("click", completeBatch); // Add listener for complete batch button

              // Initially hide back button and disable next button
              backButton.style.display = "none";
              nextButton.disabled = true;

              // Add event listeners to survey radio buttons
              const surveyQuestionsDiv =
                document.getElementById("survey-questions");
              if (surveyQuestionsDiv) {
                surveyQuestionsDiv.addEventListener(
                  "change",
                  checkSurveyCompletion
                );
              }

              // Initial check for survey completion
              checkSurveyCompletion();
            } else {
              conversationContainer.innerHTML =
                "<p>No conversations found for this batch.</p>";
              nextButton.style.display = "none";
              backButton.style.display = "none"; // Also hide back button if no conversations
              progressText.textContent = `Batch ${currentBatch}`;
              progressBar.style.width = "0%";
            }
          }
        })
        .catch((error) => {
          console.error("Error fetching completed surveys:", error);
          // Proceed with all conversations if fetching completed surveys fails
          conversations = allConversations;
          totalConversationsInBatch = conversations.length;
          // Display batch status (can be updated later to include total completed responses)
          displayBatchStatus(assignedBatches, completedBatches, currentBatch);
          // Display total completed responses (0 if fetch failed)
          displayTotalCompletedResponses(0);

          if (totalConversationsInBatch > 0) {
            displayConversation(conversations[currentConversationIndex]);
            updateProgressBar();

            // Add event listeners
            nextButton.addEventListener("click", displayNextConversation);
            backButton.addEventListener("click", displayPreviousConversation); // Add listener for back button
            completeBatchButton.addEventListener("click", completeBatch); // Add listener for complete batch button

            // Initially hide back button and disable next button
            backButton.style.display = "none";
            nextButton.disabled = true;

            // Add event listeners to survey radio buttons
            const surveyQuestionsDiv =
              document.getElementById("survey-questions");
            if (surveyQuestionsDiv) {
              surveyQuestionsDiv.addEventListener(
                "change",
                checkSurveyCompletion
              );
            }

            // Initial check for survey completion
            checkSurveyCompletion();
          } else {
            conversationContainer.innerHTML =
              "<p>No conversations found for this batch.</p>";
            nextButton.style.display = "none";
            backButton.style.display = "none"; // Also hide back button if no conversations
            progressText.textContent = `Batch ${currentBatch}`;
            progressBar.style.width = "0%";
          }
        });
    } else {
      console.error("Initial survey data not found in the HTML.");
      conversationContainer.innerHTML =
        "<p>Error initializing survey data.</p>";
      nextButton.style.display = "none";
    }
  }

  // Function to check if all survey questions are answered
  function checkSurveyCompletion() {
    const surveyQuestionsDiv = document.getElementById("survey-questions");
    if (!surveyQuestionsDiv) return;

    const questionDivs = surveyQuestionsDiv.querySelectorAll(".question");
    let allAnswered = true;

    questionDivs.forEach((questionDiv) => {
      const radioButtons = questionDiv.querySelectorAll('input[type="radio"]');
      let questionAnswered = false;
      radioButtons.forEach((radio) => {
        if (radio.checked) {
          questionAnswered = true;
        }
      });
      if (!questionAnswered) {
        allAnswered = false;
      }
    });

    nextButton.disabled = !allAnswered;
  }

  // Function to call the /complete_batch endpoint
  async function completeBatch() {
    try {
      const response = await fetch("/complete_batch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username,
          batch: currentBatch,
        }),
      });

      const result = await response.json();
      console.log("Complete batch result:", result);

      if (result.status === "success") {
        alert("Batch completed successfully!"); // Simple success feedback
        // Optionally redirect the user or update the UI further
      } else {
        alert("Failed to complete batch: " + result.message); // Simple error feedback
      }
    } catch (error) {
      console.error("Error completing batch:", error);
      alert("An error occurred while trying to complete the batch."); // Simple error feedback
    }
  }

  // Call initializeSurvey when the DOM is ready
  initializeSurvey();
});
