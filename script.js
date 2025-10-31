document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed");
    
    const conversationDisplay = document.getElementById('conversationDisplay');
    const queryInput = document.getElementById('queryInput');
    const submitQuery = document.getElementById('submitQuery');
    const clearConversation = document.getElementById('clearConversation');

    // Email control elements
    const emailDateInput = document.getElementById('emailDate');
    const fetchEmailsButton = document.getElementById('fetchEmails');
    const emailCount = document.getElementById('emailCount');
    const emailList = document.getElementById('emailList');

    console.log("submitQuery:", submitQuery);
    console.log("clearConversation:", clearConversation);
    console.log("queryInput:", queryInput);

    // Configure the marked library for converting markdown in the botresponse.
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        langPrefix: 'language-',
    });

    let eventSource;
    let currentEmailBody = "";  // Store the current email body for LLM context
    let fetchedEmails = [];  // Store all fetched emails
    let activeEmailIndex = -1;  // Currently active email index

    function initUI() {
        console.log("Initializing Prompt Playground");

        // Load conversation history
        loadConversationHistory();

        // Show content
        setTimeout(() => {
            document.querySelector('.container').classList.add('loaded');
        }, 100);
    }



    function handleQuerySubmit() {
        if (!queryInput) {
            console.error("Query input element not found");
            return;
        }
        const query = queryInput.value.trim();
        if (query) {
            addMessageToConversation('User', query);
            queryInput.value = '';

            if (eventSource) {
                eventSource.close();
            }

            // Build the full query with email context if available
            let fullQuery = query;
            if (activeEmailIndex >= 0 && currentEmailBody) {
                const email = fetchedEmails[activeEmailIndex];
                // Email is loaded, prepend full context including body
                const emailContext = `[EMAIL CONTEXT]
From: ${email.sender}
Subject: ${email.subject}
Date: ${email.date}

Body:
${currentEmailBody}

[USER QUESTION]
`;
                fullQuery = emailContext + query;
                console.log('Injecting email context with body into query');
            }

            eventSource = new EventSource('/api/chat?message=' + encodeURIComponent(fullQuery));

            let botMessage = document.createElement('div');
            botMessage.className = 'message bot-message';
            conversationDisplay.appendChild(botMessage);

            let accumulatedMarkdown = '';
            
            eventSource.onmessage = function(event) {
                console.log("Received data:", event.data);
                if (event.data === "DONE") {
                    eventSource.close();
                    console.log("Final markdown:", accumulatedMarkdown);
                    
                    // Render the complete markdown when all chunks are received
                    const finalMarkdown = accumulatedMarkdown.replace(/\\n/g, '\n');
                    botMessage.innerHTML = DOMPurify.sanitize(marked.parse(finalMarkdown));
                } else {
                    // Accumulate response data
                    let chunk = event.data.replace(/\\n/g, '\n');
                    accumulatedMarkdown += chunk;
            
                    // Render markdown only if a certain threshold is reached
                    if (accumulatedMarkdown.length > 100 || chunk.includes('\n\n')) {
                        let renderedNewContent = DOMPurify.sanitize(marked.parse(accumulatedMarkdown));
                        botMessage.innerHTML = renderedNewContent;
                    } else {
                        // If not rendering yet, provide a placeholder to indicate typing
                        if (!botMessage.innerHTML.includes('Bot is typing...')) {
                            botMessage.innerHTML = 'Bot is typing...';
                        }
                    }
                }
            
                // Scroll to the bottom
                conversationDisplay.scrollTop = conversationDisplay.scrollHeight;
            };
            
            
            eventSource.onerror = function(error) {
                console.error('EventSource failed:', error);
                eventSource.close();
            };
        }
    }
    
    function addMessageToConversation(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender.toLowerCase()}-message`;
        if (sender === 'User') {
            messageElement.textContent = `${sender}: ${message}`;
        } else {
            messageElement.innerHTML = `${sender}: ${DOMPurify.sanitize(marked.parse(message))}`;
        }
        conversationDisplay.appendChild(messageElement);
        conversationDisplay.scrollTop = conversationDisplay.scrollHeight;
    }

    function loadConversationHistory() {
        fetch('/api/get_conversation_history')
            .then(response => response.json())
            .then(data => {
                conversationDisplay.innerHTML = ''; // Clear existing conversation
                data.history.forEach(message => {
                    const messageElement = document.createElement('div');
                    messageElement.className = `message ${message.type}-message`;
                    if (message.type == 'human') {
                        messageElement.textContent = `User: ${message.content}`;
                    } else {
                        messageElement.innerHTML = `Bot: ${DOMPurify.sanitize(marked.parse(message.content))}`;
                    }
                    conversationDisplay.appendChild(messageElement);
                });
                conversationDisplay.scrollTop = conversationDisplay.scrollHeight;
            })
            .catch(error => console.error('Error loading conversation history:', error));
    }

    function handleClearConversation() {
        fetch('/api/clear')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear the conversation display
                    conversationDisplay.innerHTML = '';

                    // Close the EventSource if it exists
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }

                    console.log("Conversation cleared");
                } else {
                    console.error("Failed to clear conversation");
                }
            })
            .catch(error => console.error('Error:', error));
    }

    // Email handling functions
    function handleFetchEmails() {
        const dateValue = emailDateInput.value || getTodayDate();
        console.log('Fetching emails for date:', dateValue);

        // Clear current list
        emailList.innerHTML = '<div style="padding: 10px; text-align: center; color: #999;">Loading...</div>';
        emailCount.textContent = '';

        fetch('/api/fetch_emails?date=' + encodeURIComponent(dateValue))
            .then(response => response.json())
            .then(data => {
                console.log('Fetch emails response:', data);
                if (data.success) {
                    if (data.count > 0) {
                        emailCount.textContent = `${data.count} email${data.count > 1 ? 's' : ''}`;

                        // Backend returns all emails sorted by date (newest first)
                        fetchAllEmailMetadata(data.emails);
                    } else {
                        emailCount.textContent = data.message;
                        emailList.innerHTML = '<div style="padding: 10px; text-align: center; color: #999;">No emails found</div>';
                    }
                } else {
                    alert('Error fetching emails: ' + data.error);
                    emailList.innerHTML = '';
                }
            })
            .catch(error => {
                console.error('Error fetching emails:', error);
                alert('Failed to fetch emails. See console for details.');
                emailList.innerHTML = '';
            });
    }

    function fetchAllEmailMetadata(emailsData) {
        // Backend returns all emails already sorted by date (newest first)
        fetchedEmails = emailsData;
        emailList.innerHTML = '';

        // Add all emails to the list
        emailsData.forEach((email, index) => {
            addEmailToList(email, index);
        });

        // Select first email (newest)
        if (emailsData.length > 0) {
            selectEmail(0);
        }
    }

    function addEmailToList(email, index) {
        const emailItem = document.createElement('div');
        emailItem.className = 'email-item';
        emailItem.dataset.index = index;

        const sender = document.createElement('div');
        sender.className = 'email-item-sender';
        sender.textContent = email.sender || 'Unknown Sender';

        const subject = document.createElement('div');
        subject.className = 'email-item-subject';
        subject.textContent = email.subject || '(No Subject)';

        const date = document.createElement('div');
        date.className = 'email-item-date';
        date.textContent = email.date || '';

        emailItem.appendChild(sender);
        emailItem.appendChild(subject);
        emailItem.appendChild(date);

        emailItem.addEventListener('click', () => selectEmail(index));

        emailList.appendChild(emailItem);
    }

    function selectEmail(index) {
        // Remove active class from all items
        document.querySelectorAll('.email-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to selected item
        const selectedItem = emailList.querySelector(`[data-index="${index}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }

        // Store active index
        activeEmailIndex = index;

        // Fetch body from backend (with lazy loading)
        const email = fetchedEmails[index];
        if (email) {
            if (email.body) {
                // Body already loaded
                currentEmailBody = email.body;
                console.log('Email body already loaded');
            } else {
                // Fetch body from backend
                console.log('Fetching email body for index', index);
                fetch('/api/select_email?index=' + index)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.email) {
                            currentEmailBody = data.email.body;
                            // Cache it in our local array
                            fetchedEmails[index].body = data.email.body;
                            console.log('Email body loaded');
                        } else {
                            console.error('Failed to fetch email body:', data.error);
                            currentEmailBody = "";
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching email body:', error);
                        currentEmailBody = "";
                    });
            }
        }
    }

    function getTodayDate() {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function initEmailControls() {
        // Set default date to today
        if (emailDateInput) {
            emailDateInput.value = getTodayDate();
        }
    }

    // Event listeners
    if (submitQuery) submitQuery.addEventListener('click', handleQuerySubmit);
    if (clearConversation) clearConversation.addEventListener('click', handleClearConversation);
    if (queryInput) {
        queryInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleQuerySubmit();
            }
        });
    }

    // Email event listeners
    if (fetchEmailsButton) fetchEmailsButton.addEventListener('click', handleFetchEmails);

    // Initialize the UI when the page loads
    initUI();
    initEmailControls();
});