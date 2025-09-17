/**
 * HTMX Extensions for urbanIQ Berlin Geodata Assistant
 *
 * Provides job status polling, error handling, and UI enhancements
 * for the chat interface and download management.
 */

// Global polling state management
let activePollingJobs = new Map();

/**
 * Initialize HTMX event listeners and enhancements
 */
document.addEventListener('DOMContentLoaded', function() {
  setupHTMXEventListeners();
  setupGlobalErrorHandling();
});

/**
 * Setup HTMX event listeners for job processing workflow
 */
function setupHTMXEventListeners() {
  // Handle successful chat message submission
  document.body.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.successful && evt.detail.xhr.responseURL.includes('/api/chat/message')) {
      try {
        const response = JSON.parse(evt.detail.xhr.response);
        if (response.job_id) {
          console.log('Job created:', response.job_id);
          startJobPolling(response.job_id);
        }
      } catch (error) {
        console.error('Error parsing chat response:', error);
        showErrorMessage('Antwort konnte nicht verarbeitet werden. Bitte versuchen Sie es erneut.');
      }
    }
  });

  // Handle HTMX request errors
  document.body.addEventListener('htmx:responseError', function(evt) {
    console.error('HTMX request error:', evt.detail);

    const errorDiv = document.getElementById('chat-result');
    if (errorDiv) {
      let errorMessage = 'Verbindungsfehler aufgetreten.';

      // Customize error message based on status code
      if (evt.detail.xhr.status === 400) {
        errorMessage = 'Ungültige Anfrage. Bitte überprüfen Sie Ihre Eingabe.';
      } else if (evt.detail.xhr.status === 429) {
        errorMessage = 'Zu viele Anfragen. Bitte warten Sie einen Moment.';
      } else if (evt.detail.xhr.status >= 500) {
        errorMessage = 'Serverfehler. Bitte versuchen Sie es später erneut.';
      }

      errorDiv.innerHTML = createErrorHTML(errorMessage, 'NETWORK_ERROR');
    }
  });

  // Handle HTMX timeout
  document.body.addEventListener('htmx:timeout', function(evt) {
    console.error('HTMX request timeout:', evt.detail);

    const errorDiv = document.getElementById('chat-result');
    if (errorDiv) {
      errorDiv.innerHTML = createErrorHTML(
        'Zeitüberschreitung bei der Anfrage. Bitte versuchen Sie es erneut.',
        'TIMEOUT_ERROR'
      );
    }
  });
}

/**
 * Start polling for job status updates
 * @param {string} jobId - The job ID to poll
 */
function startJobPolling(jobId) {
  // Stop any existing polling for this job
  stopJobPolling(jobId);

  console.log('Starting job polling for:', jobId);

  // Show initial processing state
  showJobProcessingState(jobId, {
    status: 'processing',
    progress: 0,
    message: 'Geodaten-Verarbeitung gestartet...'
  });

  // Start polling with 2-second intervals
  const pollInterval = setInterval(async () => {
    try {
      await pollJobStatus(jobId);
    } catch (error) {
      console.error('Polling error for job', jobId, ':', error);
      clearInterval(pollInterval);
      activePollingJobs.delete(jobId);

      showErrorMessage(
        'Fehler beim Abrufen des Verarbeitungsstatus. Die Verarbeitung läuft möglicherweise weiter.',
        'POLLING_ERROR'
      );
    }
  }, 2000);

  // Store polling information
  activePollingJobs.set(jobId, {
    interval: pollInterval,
    startTime: Date.now(),
    attempts: 0
  });

  // Safety timeout after 10 minutes
  setTimeout(() => {
    if (activePollingJobs.has(jobId)) {
      console.log('Polling timeout for job:', jobId);
      stopJobPolling(jobId);
      showErrorMessage(
        'Zeitüberschreitung bei der Verarbeitung. Bitte erstellen Sie eine neue Anfrage.',
        'POLLING_TIMEOUT'
      );
    }
  }, 600000); // 10 minutes
}

/**
 * Poll job status from the API
 * @param {string} jobId - The job ID to poll
 */
async function pollJobStatus(jobId) {
  const pollingInfo = activePollingJobs.get(jobId);
  if (!pollingInfo) return;

  pollingInfo.attempts++;

  const response = await fetch(`/api/jobs/status/${jobId}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Cache-Control': 'no-cache'
    }
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Job nicht gefunden');
    } else if (response.status >= 500) {
      throw new Error('Server-Fehler beim Statusabruf');
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  const jobStatus = await response.json();
  console.log('Job status update:', jobStatus);

  updateJobStatusUI(jobId, jobStatus);

  // Stop polling if job is completed or failed
  if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
    stopJobPolling(jobId);
  }
}

/**
 * Stop polling for a specific job
 * @param {string} jobId - The job ID to stop polling
 */
function stopJobPolling(jobId) {
  const pollingInfo = activePollingJobs.get(jobId);
  if (pollingInfo) {
    clearInterval(pollingInfo.interval);
    activePollingJobs.delete(jobId);
    console.log('Stopped polling for job:', jobId);
  }
}

/**
 * Update the UI with job status information
 * @param {string} jobId - The job ID
 * @param {Object} jobStatus - The job status response
 */
function updateJobStatusUI(jobId, jobStatus) {
  const resultDiv = document.getElementById('chat-result');
  if (!resultDiv) return;

  if (jobStatus.status === 'processing') {
    showJobProcessingState(jobId, jobStatus);
  } else if (jobStatus.status === 'completed') {
    showJobCompletedState(jobId, jobStatus);
  } else if (jobStatus.status === 'failed') {
    showJobFailedState(jobId, jobStatus);
  }
}

/**
 * Show job processing state in the UI
 * @param {string} jobId - The job ID
 * @param {Object} jobStatus - The job status
 */
function showJobProcessingState(jobId, jobStatus) {
  const progress = jobStatus.progress || 0;
  const bezirk = jobStatus.bezirk || 'Unbekannt';
  const datasets = jobStatus.datasets || [];

  let statusMessage = getProgressMessage(progress);

  const html = `
    <div class="status-card status-processing" role="status" aria-live="polite">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <div class="animate-spin h-6 w-6 border-2 border-urban-blue-600 border-t-transparent rounded-full"></div>
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="text-lg font-semibold text-urban-blue-800 mb-2">
            Geodaten werden verarbeitet
          </h3>

          <div class="space-y-3">
            <div class="flex items-center justify-between text-sm">
              <span class="text-urban-blue-700 font-medium">${statusMessage}</span>
              <span class="text-urban-blue-600 font-mono">${progress}%</span>
            </div>

            <div class="w-full bg-urban-blue-200 rounded-full h-3">
              <div
                class="bg-urban-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
                style="width: ${progress}%"
                role="progressbar"
                aria-valuenow="${progress}"
                aria-valuemin="0"
                aria-valuemax="100"
                aria-label="Verarbeitungsfortschritt"
              ></div>
            </div>

            ${bezirk !== 'Unbekannt' ? `
              <div class="text-sm text-gray-600">
                <span class="font-medium">Bezirk:</span> ${bezirk}
              </div>
            ` : ''}

            ${datasets.length > 0 ? `
              <div class="text-sm text-gray-600">
                <span class="font-medium">Datensätze:</span> ${datasets.join(', ')}
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('chat-result').innerHTML = html;
}

/**
 * Show job completed state in the UI
 * @param {string} jobId - The job ID
 * @param {Object} jobStatus - The job status
 */
function showJobCompletedState(jobId, jobStatus) {
  const bezirk = jobStatus.bezirk || 'Unbekannt';
  const datasets = jobStatus.datasets || [];
  const downloadUrl = jobStatus.download_url;

  const html = `
    <div class="status-card status-success" role="alert" aria-live="assertive">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <svg class="h-6 w-6 text-urban-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="text-lg font-semibold text-urban-green-800 mb-2">
            Geodatenpaket erfolgreich erstellt!
          </h3>

          <div class="space-y-4">
            <div class="text-sm text-gray-600 space-y-1">
              <div><span class="font-medium">Bezirk:</span> ${bezirk}</div>
              ${datasets.length > 0 ? `<div><span class="font-medium">Datensätze:</span> ${datasets.join(', ')}</div>` : ''}
              <div><span class="font-medium">Abgeschlossen:</span> ${formatTimestamp(jobStatus.completed_at)}</div>
            </div>

            ${downloadUrl ? `
              <div class="flex flex-col sm:flex-row gap-3">
                <a
                  href="${downloadUrl}"
                  class="btn-primary inline-flex items-center justify-center space-x-2"
                  download
                  aria-describedby="download-help"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-4-4m4 4l4-4m5-5v8a2 2 0 01-2 2H5a2 2 0 01-2-2v-8a2 2 0 012-2h8l4 4z"></path>
                  </svg>
                  <span>ZIP-Paket herunterladen</span>
                </a>

                <button
                  onclick="createNewRequest()"
                  class="btn-secondary inline-flex items-center justify-center space-x-2"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                  </svg>
                  <span>Neue Anfrage</span>
                </button>
              </div>

              <p id="download-help" class="text-xs text-gray-500">
                Das ZIP-Paket enthält harmonisierte Geodaten in GeoJSON und Shapefile Formaten,
                sowie eine umfassende Metadaten-Dokumentation.
              </p>
            ` : `
              <div class="text-sm text-urban-red-600">
                Download-Link nicht verfügbar. Bitte kontaktieren Sie den Support.
              </div>
            `}
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('chat-result').innerHTML = html;
}

/**
 * Show job failed state in the UI
 * @param {string} jobId - The job ID
 * @param {Object} jobStatus - The job status
 */
function showJobFailedState(jobId, jobStatus) {
  const errorMessage = jobStatus.error_message || 'Unbekannter Fehler bei der Verarbeitung';

  const html = `
    <div class="status-card status-error" role="alert" aria-live="assertive">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <svg class="h-6 w-6 text-urban-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="text-lg font-semibold text-urban-red-800 mb-2">
            Fehler bei der Verarbeitung
          </h3>

          <div class="space-y-4">
            <p class="text-sm text-urban-red-700">
              ${errorMessage}
            </p>

            <div class="flex flex-col sm:flex-row gap-3">
              <button
                onclick="createNewRequest()"
                class="btn-primary inline-flex items-center justify-center space-x-2"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
                <span>Erneut versuchen</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('chat-result').innerHTML = html;
}

/**
 * Get progress message based on completion percentage
 * @param {number} progress - Progress percentage (0-100)
 * @returns {string} Localized progress message
 */
function getProgressMessage(progress) {
  if (progress < 15) return 'Anfrage wird analysiert...';
  if (progress < 25) return 'NLP-Verarbeitung abgeschlossen...';
  if (progress < 40) return 'Geodaten werden abgerufen...';
  if (progress < 55) return 'Datenquellen werden abgefragt...';
  if (progress < 70) return 'Geodaten werden harmonisiert...';
  if (progress < 85) return 'Metadaten werden generiert...';
  if (progress < 100) return 'ZIP-Paket wird erstellt...';
  return 'Verarbeitung abgeschlossen';
}

/**
 * Format timestamp for display
 * @param {string} timestamp - ISO timestamp string
 * @returns {string} Formatted timestamp
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return 'Unbekannt';

  try {
    const date = new Date(timestamp);
    return date.toLocaleString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    return 'Ungültiges Datum';
  }
}

/**
 * Show a general error message
 * @param {string} message - Error message to display
 * @param {string} errorCode - Error code for debugging
 */
function showErrorMessage(message, errorCode = 'GENERAL_ERROR') {
  const resultDiv = document.getElementById('chat-result');
  if (resultDiv) {
    resultDiv.innerHTML = createErrorHTML(message, errorCode);
  }
}

/**
 * Create error HTML
 * @param {string} message - Error message
 * @param {string} errorCode - Error code
 * @returns {string} HTML string
 */
function createErrorHTML(message, errorCode) {
  return `
    <div class="status-card status-error" role="alert" aria-live="assertive">
      <div class="flex items-start space-x-3">
        <div class="flex-shrink-0">
          <svg class="h-6 w-6 text-urban-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="text-lg font-semibold text-urban-red-800 mb-2">
            Fehler aufgetreten
          </h3>
          <p class="text-sm text-urban-red-700 mb-4">
            ${message}
          </p>
          <button
            onclick="createNewRequest()"
            class="btn-primary inline-flex items-center space-x-2"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            <span>Erneut versuchen</span>
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Create a new request by clearing the results and focusing the form
 */
function createNewRequest() {
  // Clear results
  const resultDiv = document.getElementById('chat-result');
  if (resultDiv) {
    resultDiv.innerHTML = '';
  }

  // Focus the textarea
  const textarea = document.getElementById('geodata-request');
  if (textarea) {
    textarea.focus();
    textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

/**
 * Setup global error handling
 */
function setupGlobalErrorHandling() {
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    // Don't prevent default to allow logging
  });

  // Handle uncaught errors
  window.addEventListener('error', function(event) {
    console.error('Uncaught error:', event.error);
    // Don't prevent default to allow logging
  });
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
  // Stop all active polling
  activePollingJobs.forEach((pollingInfo, jobId) => {
    clearInterval(pollingInfo.interval);
  });
  activePollingJobs.clear();
});