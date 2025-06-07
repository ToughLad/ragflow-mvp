// Global state
let authState = {
  inboxes: [],
  authenticatedInboxes: new Set(),
  overallStatus: 'checking'
};

let emailState = {
  currentPage: 0,
  pageSize: 50,
  totalEmails: 0,
  filters: {}
};

let chatState = {
  messages: [],
  ragMode: false
};

// API helper functions
async function fetchJSON(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    const data = await res.json();
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// Tab management
const tabs = document.querySelectorAll('nav button');
const sections = document.querySelectorAll('.tab');

tabs.forEach(btn => {
  btn.addEventListener('click', () => {
    tabs.forEach(tab => tab.classList.remove('active'));
    sections.forEach(sec => sec.classList.remove('active'));
    
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
    
    // Load data when switching to certain tabs
    if (btn.dataset.tab === 'emails') {
      loadEmailDatabase();
    } else if (btn.dataset.tab === 'chat') {
      checkLLMStatus();
    } else if (btn.dataset.tab === 'search') {
      loadSearchInfo();
    } else if (btn.dataset.tab === 'admin') {
      loadSystemStatus();
    }
  });
});

// ==================== AUTHENTICATION FUNCTIONS ====================

async function loadInboxConfiguration() {
  try {
    const response = await fetchJSON('/api/inbox/list');
    authState.inboxes = response.inboxes || [];
    renderInboxList();
    populateEmailInboxSelect();
  } catch (error) {
    console.error('Failed to load inbox configuration:', error);
    showError('Failed to load inbox configuration');
  }
}

async function addNewInbox() {
  const email = document.getElementById('newInboxEmail').value.trim();
  const description = document.getElementById('newInboxDescription').value.trim();
  
  if (!email) {
    showError('Please enter a valid email address');
    return;
  }
  
  try {
    const response = await fetchJSON('/api/emails/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `email_address=${encodeURIComponent(email)}&description=${encodeURIComponent(description)}`
    });
    
    showSuccess(`Added inbox: ${email}`);
    document.getElementById('newInboxEmail').value = '';
    document.getElementById('newInboxDescription').value = '';
    
    // Refresh inbox list
    await loadInboxConfiguration();
  } catch (error) {
    showError(`Failed to add inbox: ${error.message}`);
  }
}

async function checkAuthStatus(email = null) {
  try {
    const url = email ? `/api/auth/status?email=${encodeURIComponent(email)}` : '/api/auth/status';
    const response = await fetchJSON(url);
    return response;
  } catch (error) {
    console.error('Auth status check failed:', error);
    return { authenticated: false, error: error.message };
  }
}

async function checkAllAuthStatus() {
  if (authState.inboxes.length === 0) {
    updateAuthStatusBar();
    return;
  }
  
  const statusPromises = authState.inboxes.map(async (inbox) => {
    const status = await checkAuthStatus(inbox);
    return { inbox, ...status };
  });
  
  const results = await Promise.all(statusPromises);
  
  authState.authenticatedInboxes.clear();
  results.forEach(result => {
    if (result.authenticated) {
      authState.authenticatedInboxes.add(result.inbox);
    }
  });
  
  const totalAuthenticated = authState.authenticatedInboxes.size;
  const totalInboxes = authState.inboxes.length;
  
  if (totalAuthenticated === 0) {
    authState.overallStatus = 'none';
  } else if (totalAuthenticated === totalInboxes) {
    authState.overallStatus = 'complete';
  } else {
    authState.overallStatus = 'partial';
  }
  
  updateAuthStatusBar();
  renderInboxList();
  updateAuthStatusDetails(results);
  
  return results;
}

async function autoAuthenticateAll() {
  showInfo('Starting auto-authentication for all inboxes...');
  
  for (const inbox of authState.inboxes) {
    if (!authState.authenticatedInboxes.has(inbox)) {
      await authenticateInbox(inbox);
      // Add small delay between authentications
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  showSuccess('Auto-authentication completed!');
}

function renderInboxList() {
  const container = document.getElementById('inboxAuthList');
  container.innerHTML = '';
  
  if (authState.inboxes.length === 0) {
    container.innerHTML = '<p class="text-muted">No inboxes configured. Add an inbox above to get started.</p>';
    return;
  }
  
  authState.inboxes.forEach(inbox => {
    const isAuthenticated = authState.authenticatedInboxes.has(inbox);
    
    const inboxDiv = document.createElement('div');
    inboxDiv.className = `inbox-item ${isAuthenticated ? 'authenticated' : ''}`;
    
    inboxDiv.innerHTML = `
      <div class="inbox-email">${inbox}</div>
      <div class="inbox-status">
        <span class="status-badge ${isAuthenticated ? 'authenticated' : 'pending'}">
          ${isAuthenticated ? 'Authenticated' : 'Pending'}
        </span>
        <button class="btn-auth ${isAuthenticated ? 'authenticated' : ''}" 
                onclick="authenticateInbox('${inbox}')"
                ${isAuthenticated ? 'title="Re-authenticate"' : 'title="Authenticate"'}>
          ${isAuthenticated ? 'Re-auth' : 'Authenticate'}
        </button>
        <button class="btn-small btn-danger" onclick="removeInbox('${inbox}')" title="Remove inbox">
          🗑️
        </button>
      </div>
    `;
    
    container.appendChild(inboxDiv);
  });
}

function updateAuthStatusBar() {
  const statusBar = document.getElementById('authStatus');
  const message = document.getElementById('authMessage');
  
  statusBar.className = 'auth-status';
  
  switch (authState.overallStatus) {
    case 'checking':
      message.textContent = 'Checking authentication status...';
      break;
    case 'none':
      statusBar.classList.add('error');
      message.textContent = 'No Gmail inboxes authenticated. Please authenticate at least one inbox.';
      break;
    case 'partial':
      message.textContent = `${authState.authenticatedInboxes.size}/${authState.inboxes.length} inboxes authenticated. Some inboxes need authentication.`;
      break;
    case 'complete':
      statusBar.classList.add('authenticated');
      message.textContent = `All ${authState.inboxes.length} Gmail inboxes are authenticated. System ready!`;
      break;
  }
  
  const startBtn = document.getElementById('startProcessingBtn');
  startBtn.disabled = authState.authenticatedInboxes.size === 0;
}

function updateAuthStatusDetails(results) {
  const container = document.getElementById('authStatusDetails');
  
  if (!results || results.length === 0) {
    container.innerHTML = '<p>No authentication status available.</p>';
    return;
  }
  
  let html = '<div class="status-grid">';
  results.forEach(result => {
    html += `
      <div class="status-item ${result.authenticated ? 'success' : 'error'}">
        <strong>${result.inbox}</strong>: 
        ${result.authenticated ? '✅ Authenticated' : '❌ Not authenticated'}
        ${result.error ? `<br><small>Error: ${result.error}</small>` : ''}
      </div>
    `;
  });
  html += '</div>';
  
  container.innerHTML = html;
}

async function authenticateInbox(email) {
  try {
    const authUrl = `/auth/google?email=${encodeURIComponent(email)}`;
    const authWindow = window.open(authUrl, 'auth', 'width=600,height=700,scrollbars=yes,resizable=yes');
    
    const pollTimer = setInterval(() => {
      try {
        if (authWindow.closed) {
          clearInterval(pollTimer);
          setTimeout(() => {
            checkAuthStatus(email).then(status => {
              if (status.authenticated) {
                authState.authenticatedInboxes.add(email);
                showSuccess(`Successfully authenticated ${email}`);
              } else {
                showError(`Authentication failed for ${email}`);
              }
              checkAllAuthStatus();
            });
          }, 1000);
        }
      } catch (e) {
        // Cross-origin errors are expected
      }
    }, 1000);
    
    setTimeout(() => {
      clearInterval(pollTimer);
      if (!authWindow.closed) {
        authWindow.close();
        showError('Authentication timed out. Please try again.');
      }
    }, 300000);
    
  } catch (error) {
    console.error('Authentication error:', error);
    showError(`Failed to start authentication for ${email}`);
  }
}

async function removeInbox(email) {
  if (!confirm(`Are you sure you want to remove ${email} from the system?`)) {
    return;
  }
  
  try {
    // Remove from local state
    authState.inboxes = authState.inboxes.filter(inbox => inbox !== email);
    authState.authenticatedInboxes.delete(email);
    
    showSuccess(`Removed inbox: ${email}`);
    renderInboxList();
    updateAuthStatusBar();
  } catch (error) {
    showError(`Failed to remove inbox: ${error.message}`);
  }
}

async function startEmailProcessing() {
  try {
    showInfo('Starting email processing...');
    const response = await fetchJSON('/ingest/emails', { method: 'POST' });
    showSuccess('Email processing started successfully!');
  } catch (error) {
    console.error('Failed to start email processing:', error);
    showError('Failed to start email processing');
  }
}

// ==================== LLM CHAT FUNCTIONS ====================

async function checkLLMStatus() {
  try {
    const response = await fetchJSON('/api/scheduler/status');
    const statusElement = document.getElementById('modelStatus');
    statusElement.textContent = 'Online';
    statusElement.className = 'status-badge authenticated';
  } catch (error) {
    const statusElement = document.getElementById('modelStatus');
    statusElement.textContent = 'Offline';
    statusElement.className = 'status-badge error';
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  
  if (!message) return;
  
  // Add user message to chat
  addChatMessage('user', message);
  input.value = '';
  
  try {
    const ragMode = document.getElementById('ragModeToggle').checked;
    
    let response;
    if (ragMode) {
      // Use RAG search for contextual responses
      response = await fetchJSON('/api/search', {
        method: 'POST',
        body: JSON.stringify({ q: message }),
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.answer) {
        addChatMessage('assistant', response.answer);
      } else {
        addChatMessage('assistant', 'I couldn\'t find relevant information in the indexed content.');
      }
    } else {
      // Direct LLM chat
      const llamaResponse = await fetch('http://localhost:11434/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'mistral:7b-instruct-v0.3',
          prompt: message,
          stream: false
        })
      });
      
      const llamaData = await llamaResponse.json();
      addChatMessage('assistant', llamaData.response);
    }
  } catch (error) {
    console.error('Chat error:', error);
    addChatMessage('system', 'Error: Unable to process your message. Please try again.');
  }
}

function addChatMessage(sender, content) {
  const messagesContainer = document.getElementById('chatMessages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `chat-message ${sender}`;
  
  const timestamp = new Date().toLocaleTimeString();
  messageDiv.innerHTML = `
    <strong>${sender === 'user' ? 'You' : sender === 'assistant' ? 'Assistant' : 'System'}:</strong>
    ${content}
    <div style="font-size: 11px; opacity: 0.7; margin-top: 5px;">${timestamp}</div>
  `;
  
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  chatState.messages.push({ sender, content, timestamp });
}

function clearChat() {
  document.getElementById('chatMessages').innerHTML = `
    <div class="chat-message system">
      <strong>System:</strong> LLM chat ready! Ask me anything about your emails, documents, or general questions.
    </div>
  `;
  chatState.messages = [];
}

// ==================== SEARCH FUNCTIONS ====================

async function loadSearchInfo() {
  try {
    // Load knowledge base info
    const kbResponse = await fetchJSON('/api/ragflow/status');
    document.getElementById('kbCount').textContent = kbResponse.count || 'Unknown';
    document.getElementById('lastIndexed').textContent = kbResponse.lastUpdated || 'Unknown';
  } catch (error) {
    document.getElementById('kbCount').textContent = 'Error';
    document.getElementById('lastIndexed').textContent = 'Error';
  }
}

async function performSearch() {
  const query = document.getElementById('query').value.trim();
  if (!query) {
    showError('Please enter a search query');
    return;
  }
  
  const scope = document.getElementById('searchScope').value;
  const advanced = document.getElementById('advancedSearchOptions').style.display !== 'none';
  
  let searchData = { q: query };
  
  if (advanced) {
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    const priority = document.getElementById('priorityFilter').value;
    const category = document.getElementById('categoryFilter').value;
    
    if (dateFrom) searchData.date_from = dateFrom;
    if (dateTo) searchData.date_to = dateTo;
    if (priority) searchData.priority = priority;
    if (category) searchData.category = category;
  }
  
  try {
    showInfo('Searching...');
    const response = await fetchJSON('/api/search', {
      method: 'POST',
      body: JSON.stringify(searchData),
      headers: { 'Content-Type': 'application/json' }
    });
    
    displaySearchResults(response, query);
  } catch (error) {
    console.error('Search failed:', error);
    showError('Search failed: ' + error.message);
  }
}

function displaySearchResults(response, query) {
  const summary = document.getElementById('searchResultsSummary');
  const results = document.getElementById('searchResults');
  
  if (response.error) {
    summary.innerHTML = `<strong>Search Error:</strong> ${response.error}`;
    results.innerHTML = '';
    return;
  }
  
  // Display summary
  const resultCount = response.references ? response.references.length : 0;
  summary.innerHTML = `
    <strong>Search Results for:</strong> "${query}"<br>
    <strong>Found:</strong> ${resultCount} relevant items
    ${response.answer ? `<br><strong>AI Summary:</strong> ${response.answer}` : ''}
  `;
  
  // Display results
  if (response.references && response.references.length > 0) {
    let html = '';
    response.references.forEach((ref, index) => {
      html += `
        <div class="search-result-item" style="padding: 15px; border-bottom: 1px solid #eee;">
          <h4 style="margin: 0 0 5px 0; color: #007bff;">Result ${index + 1}</h4>
          <p><strong>Type:</strong> ${ref.doc_name || ref.type || 'Document'}</p>
          <p><strong>Content:</strong> ${ref.content_ltks || ref.text || 'No content available'}</p>
          ${ref.similarity ? `<p><strong>Relevance:</strong> ${(ref.similarity * 100).toFixed(1)}%</p>` : ''}
        </div>
      `;
    });
    results.innerHTML = html;
  } else {
    results.innerHTML = '<p style="padding: 20px; text-align: center; color: #6c757d;">No results found.</p>';
  }
}

function toggleAdvancedSearch() {
  const advanced = document.getElementById('advancedSearchOptions');
  const button = document.getElementById('advancedSearchBtn');
  
  if (advanced.style.display === 'none') {
    advanced.style.display = 'block';
    button.textContent = '⚙️ Hide Advanced';
  } else {
    advanced.style.display = 'none';
    button.textContent = '⚙️ Advanced';
  }
}

// ==================== EMAIL DATABASE FUNCTIONS ====================

async function loadEmailDatabase() {
  await loadEmailStats();
  await loadEmailCategories();
  await populateEmailInboxSelect();
}

async function loadEmailStats() {
  try {
    const today = new Date().toISOString().split('T')[0];
    
    // Get total email count
    const totalResponse = await fetchJSON('/api/emails?limit=1');
    // Note: This is a simplified approach. In a real system, you'd have a dedicated stats endpoint
    
    document.getElementById('totalEmailCount').textContent = 'Loading...';
    document.getElementById('todayEmailCount').textContent = 'Loading...';
    document.getElementById('urgentEmailCount').textContent = 'Loading...';
    document.getElementById('categoryCount').textContent = 'Loading...';
  } catch (error) {
    console.error('Failed to load email stats:', error);
  }
}

async function loadEmailCategories() {
  // This would ideally come from an API endpoint that returns unique categories
  const categories = [
    'Purchase Order', 'Invoice', 'Quality Assurance', 'Customer Sales Inquiry',
    'Maintenance/Repair', 'Drawing/GAD', 'Inspection/TPI', 'Documentation/Compliance',
    'Financial Compliance', 'Operations/Logistics', 'HR/Recruitment'
  ];
  
  const select = document.getElementById('emailCategory');
  categories.forEach(category => {
    const option = document.createElement('option');
    option.value = category;
    option.textContent = category;
    select.appendChild(option);
  });
}

async function populateEmailInboxSelect() {
  try {
    const data = await fetchJSON('/api/inbox/list');
    const select = document.getElementById('emailInbox');
    select.innerHTML = '';
    
    data.inboxes.forEach(addr => {
      const opt = document.createElement('option');
      opt.value = addr;
      opt.textContent = addr;
      select.appendChild(opt);
    });
  } catch (error) {
    console.error('Failed to load inboxes:', error);
  }
}

async function searchEmails() {
  const filters = {
    inboxes: [...document.getElementById('emailInbox').selectedOptions].map(o => o.value).join(','),
    category: document.getElementById('emailCategory').value,
    priority: document.getElementById('emailPriority').value,
    sender: document.getElementById('emailSenderFilter').value,
    date_from: document.getElementById('emailDateFrom').value,
    date_to: document.getElementById('emailDateTo').value,
    offset: emailState.currentPage * emailState.pageSize,
    limit: emailState.pageSize
  };
  
  // Remove empty filters
  Object.keys(filters).forEach(key => {
    if (!filters[key]) delete filters[key];
  });
  
  try {
    const params = new URLSearchParams(filters);
    const response = await fetchJSON(`/api/emails?${params}`);
    
    displayEmailResults(response);
    updateEmailPagination(response);
  } catch (error) {
    console.error('Failed to search emails:', error);
    showError('Failed to search emails');
  }
}

function displayEmailResults(response) {
  const container = document.getElementById('emailList');
  const countElement = document.getElementById('emailResultsCount');
  
  if (!response.emails || response.emails.length === 0) {
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">No emails found.</div>';
    countElement.textContent = 'No emails found';
    return;
  }
  
  countElement.textContent = `Found ${response.emails.length} emails`;
  
  let html = '';
  response.emails.forEach(email => {
    const date = email.date ? new Date(email.date).toLocaleDateString() : 'Unknown';
    const priority = email.priority || 'Normal';
    
    html += `
      <div class="email-item ${priority.toLowerCase()}" onclick="viewEmailDetails('${email.email_id}')">
        <div style="display: flex; justify-content: space-between; align-items: start;">
          <div style="flex: 1;">
            <div style="font-weight: bold; margin-bottom: 5px;">${email.subject || 'No Subject'}</div>
            <div style="font-size: 14px; color: #6c757d;">
              <span>From: ${email.sender || 'Unknown'}</span> |
              <span>Date: ${date}</span> |
              <span>Priority: ${priority}</span>
              ${email.category ? ` | Category: ${email.category}` : ''}
            </div>
            ${email.summary ? `<div style="margin-top: 8px; font-size: 13px; color: #495057;">${email.summary}</div>` : ''}
          </div>
          <div style="margin-left: 15px;">
            <span class="status-badge ${priority.toLowerCase()}">${priority}</span>
          </div>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
}

function updateEmailPagination(response) {
  const pageInfo = document.getElementById('emailPageInfo');
  const totalPages = Math.ceil((response.total || response.emails.length) / emailState.pageSize);
  const currentPage = emailState.currentPage + 1;
  
  pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  
  document.getElementById('prevEmailPage').disabled = emailState.currentPage === 0;
  document.getElementById('nextEmailPage').disabled = emailState.currentPage >= totalPages - 1;
}

function resetEmailFilters() {
  document.getElementById('emailInbox').selectedIndex = -1;
  document.getElementById('emailCategory').value = '';
  document.getElementById('emailPriority').value = '';
  document.getElementById('emailSenderFilter').value = '';
  document.getElementById('emailDateFrom').value = '';
  document.getElementById('emailDateTo').value = '';
  emailState.currentPage = 0;
  searchEmails();
}

async function viewEmailDetails(emailId) {
  // This would open a modal or navigate to a detailed view
  showInfo(`Viewing details for email: ${emailId}`);
  // Implementation would depend on your needs
}

// ==================== SYSTEM ADMIN FUNCTIONS ====================

async function loadSystemStatus() {
  try {
    // Load various system statuses
    const [queueStatus, schedulerStatus, authStatus] = await Promise.all([
      fetchJSON('/api/queue/status'),
      fetchJSON('/api/scheduler/status'),
      fetchJSON('/api/auth/status')
    ]);
    
    displaySystemStatus({ queueStatus, schedulerStatus, authStatus });
    loadQueue();
    loadSchedulerInfo(schedulerStatus);
  } catch (error) {
    console.error('Failed to load system status:', error);
  }
}

function displaySystemStatus(status) {
  const container = document.getElementById('systemStatus');
  
  let html = `
    <div class="status-item ${status.authStatus.authenticated ? 'success' : 'error'}">
      <strong>Authentication:</strong> ${status.authStatus.authenticated ? 'Active' : 'Issues Detected'}
    </div>
    <div class="status-item success">
      <strong>Queue Status:</strong> Active
    </div>
    <div class="status-item ${status.schedulerStatus.status === 'running' ? 'success' : 'error'}">
      <strong>Scheduler:</strong> ${status.schedulerStatus.status || 'Unknown'}
    </div>
  `;
  
  container.innerHTML = html;
}

function loadSchedulerInfo(schedulerStatus) {
  const container = document.getElementById('schedulerStatus');
  
  if (schedulerStatus.jobs && schedulerStatus.jobs.length > 0) {
    let html = '<div class="status-grid">';
    schedulerStatus.jobs.forEach(job => {
      html += `
        <div class="status-item success">
          <strong>${job.name}</strong><br>
          <small>Next run: ${job.next_run ? new Date(job.next_run).toLocaleString() : 'Not scheduled'}</small>
        </div>
      `;
    });
    html += '</div>';
    container.innerHTML = html;
  } else {
    container.innerHTML = '<p>No scheduled jobs found.</p>';
  }
}

// ==================== NOTIFICATION FUNCTIONS ====================

function showSuccess(message) {
  showNotification(message, 'success');
}

function showError(message) {
  showNotification(message, 'error');
}

function showInfo(message) {
  showNotification(message, 'info');
}

function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.innerHTML = `
    <span>${message}</span>
    <button onclick="this.parentElement.remove()">×</button>
  `;
  
  if (!document.querySelector('#notification-styles')) {
    const styles = document.createElement('style');
    styles.id = 'notification-styles';
    styles.textContent = `
      .notification {
        position: fixed;
        top: 70px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease;
      }
      .notification.success { background: #28a745; }
      .notification.error { background: #dc3545; }
      .notification.info { background: #17a2b8; }
      .notification button {
        background: none;
        border: none;
        color: white;
        float: right;
        cursor: pointer;
        font-size: 18px;
        font-weight: bold;
        margin-left: 10px;
        padding: 0;
      }
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
    `;
    document.head.appendChild(styles);
  }
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    if (notification.parentElement) {
      notification.remove();
    }
  }, 5000);
}

// ==================== EVENT LISTENERS ====================

// Authentication events
document.getElementById('refreshAuthBtn').addEventListener('click', checkAllAuthStatus);
document.getElementById('addInboxBtn').addEventListener('click', addNewInbox);
document.getElementById('autoAuthAllBtn').addEventListener('click', autoAuthenticateAll);
document.getElementById('checkAllAuthBtn').addEventListener('click', checkAllAuthStatus);
document.getElementById('startProcessingBtn').addEventListener('click', startEmailProcessing);

// Chat events
document.getElementById('sendChatBtn').addEventListener('click', sendChatMessage);
document.getElementById('clearChatBtn').addEventListener('click', clearChat);
document.getElementById('chatInput').addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'Enter') {
    sendChatMessage();
  }
});

// Search events
document.getElementById('searchBtn').addEventListener('click', performSearch);
document.getElementById('advancedSearchBtn').addEventListener('click', toggleAdvancedSearch);
document.getElementById('query').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    performSearch();
  }
});

// Email database events
document.getElementById('loadEmails').addEventListener('click', searchEmails);
document.getElementById('resetEmailFilters').addEventListener('click', resetEmailFilters);
document.getElementById('refreshAllInboxes').addEventListener('click', () => {
  fetchJSON('/api/inbox/refreshAll', { method: 'POST' });
  showSuccess('All inboxes queued for refresh');
});
document.getElementById('generateDigest').addEventListener('click', () => {
  fetchJSON('/api/digest/daily', { method: 'POST' });
  showSuccess('Daily digest generation started');
});

// Email pagination
document.getElementById('prevEmailPage').addEventListener('click', () => {
  if (emailState.currentPage > 0) {
    emailState.currentPage--;
    searchEmails();
  }
});
document.getElementById('nextEmailPage').addEventListener('click', () => {
  emailState.currentPage++;
  searchEmails();
});

// Document events
document.getElementById('loadDocs').addEventListener('click', async () => {
  const type = document.getElementById('docType').value;
  const cat = document.getElementById('docCategory').value;
  
  try {
    const data = await fetchJSON(`/api/documents?source_type=${encodeURIComponent(type)}&category=${encodeURIComponent(cat)}`);
    const ul = document.getElementById('docList');
    ul.innerHTML = '';
    data.documents.forEach(d => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div style="font-weight: bold;">${d.doc_metadata.filename || 'Unknown Document'}</div>
        <div style="font-size: 14px; color: #6c757d;">
          Category: ${d.category || 'Uncategorized'} | Type: ${d.source_type || 'Unknown'}
        </div>
      `;
      ul.appendChild(li);
    });
  } catch (error) {
    showError('Failed to load documents');
  }
});

document.getElementById('processNewDocs').addEventListener('click', () => {
  fetchJSON('/api/documents/upload', { method: 'POST' });
  showSuccess('Document processing started');
});

// Queue management
let queueOffset = 0;
async function loadQueue() {
  try {
    const data = await fetchJSON(`/api/processing_queue/list?offset=${queueOffset}&limit=10`);
    const ul = document.getElementById('queueList');
    ul.innerHTML = '';
    data.items.forEach(item => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div style="display: flex; justify-content: space-between;">
          <span>${item.created_at} - ${item.item_type}</span>
          <span class="status-badge ${item.status}">${item.status}</span>
        </div>
      `;
      ul.appendChild(li);
    });
  } catch (error) {
    console.error('Failed to load queue:', error);
  }
}

document.getElementById('nextPage').addEventListener('click', () => {
  queueOffset += 10;
  loadQueue();
});

document.getElementById('prevPage').addEventListener('click', () => {
  queueOffset = Math.max(0, queueOffset - 10);
  loadQueue();
});

// Initialize the application
async function initializeApp() {
  try {
    authState.overallStatus = 'checking';
    updateAuthStatusBar();
    
    await loadInboxConfiguration();
    await checkAllAuthStatus();
    
    // Initialize default tab
    document.querySelector('[data-tab="auth"]').classList.add('active');
    document.getElementById('auth').classList.add('active');
    
    showSuccess('RAGFlow MVP Dashboard initialized successfully!');
  } catch (error) {
    console.error('Initialization error:', error);
    showError('Failed to initialize application');
  }
}

// Start the app when page loads
document.addEventListener('DOMContentLoaded', initializeApp);
