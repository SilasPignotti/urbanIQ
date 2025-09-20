# Frontend Implementation Guide

This document defines the frontend implementation strategy for urbanIQ Berlin using HTMX and Tailwind CSS.

## Technology Stack

**Core Technologies**:

- **HTMX**: Reactive frontend interactions without complex JavaScript
- **Jinja2**: Server-side template rendering
- **Tailwind CSS**: Utility-first CSS framework
- **FastAPI Templates**: Integrated template serving

**Design Philosophy**:

- Minimal JavaScript footprint
- Server-driven UI updates
- Progressive enhancement
- Mobile-responsive design

## Template Structure

### Base Template (base.html)

```html
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{% block title %}Geodaten-Assistent Berlin{% endblock %}</title>

    <!-- HTMX Core -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    {% block head %}{% endblock %}
  </head>
  <body class="bg-gray-50 min-h-screen">
    <div class="max-w-4xl mx-auto p-6">{% block content %}{% endblock %}</div>

    {% block scripts %}{% endblock %}
  </body>
</html>
```

### Main Interface (index.html)

**Layout Components**:

- Header with system title and description
- Chat input form with HTMX integration
- Loading indicator with animation
- Results container for dynamic updates
- Progress tracking UI

**HTMX Integration**:

```html
<form
  hx-post="/api/chat/message"
  hx-target="#chat-result"
  hx-indicator="#loading"
  class="mb-6"
>
  <div class="flex gap-4">
    <input
      type="text"
      name="text"
      placeholder="z.B.: Pankow Grunddaten für Mobilitätsanalyse"
      class="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
      required
    />
    <button
      type="submit"
      class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
    >
      Abfragen
    </button>
  </div>
</form>
```

## Interactive Features

### Job Status Polling

**JavaScript Implementation**:

```javascript
// HTMX event listener for job creation
document.body.addEventListener("htmx:afterRequest", function (evt) {
  if (
    evt.detail.successful &&
    evt.detail.xhr.responseURL.includes("/chat/message")
  ) {
    const response = JSON.parse(evt.detail.xhr.response);
    if (response.job_id) {
      pollJobStatus(response.job_id);
    }
  }
});

// Polling function with automatic cleanup
function pollJobStatus(jobId) {
  const pollInterval = setInterval(async () => {
    const response = await fetch(`/api/jobs/status/${jobId}`);
    const job = await response.json();

    updateProgressUI(job);

    if (job.status === "completed" || job.status === "failed") {
      clearInterval(pollInterval);
    }
  }, 2000); // 2-second polling interval
}
```

### Dynamic UI Updates

**Progress Indicators**:

```html
<!-- Processing State -->
<div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
  <div class="flex items-center gap-2 mb-2">
    <div
      class="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"
    ></div>
    <span class="text-blue-800">Verarbeitung läuft... ${job.progress}%</span>
  </div>
  <div class="w-full bg-blue-200 rounded-full h-2">
    <div
      class="bg-blue-600 h-2 rounded-full transition-all"
      style="width: ${job.progress}%"
    ></div>
  </div>
</div>

<!-- Completed State -->
<div class="bg-green-50 border border-green-200 rounded-lg p-4">
  <h3 class="font-semibold text-green-800">Geodatenpaket erstellt!</h3>
  <a
    href="${job.download_url}"
    class="inline-block mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
  >
    Herunterladen
  </a>
</div>

<!-- Error State -->
<div class="bg-red-50 border border-red-200 rounded-lg p-4">
  <h3 class="font-semibold text-red-800">Fehler bei der Verarbeitung</h3>
  <p class="text-red-600">${job.error}</p>
</div>
```

## Styling Guidelines

### Tailwind CSS Configuration

**Color Palette**:

- Primary: Blue (blue-600, blue-700)
- Success: Green (green-600, green-700)
- Warning: Yellow (yellow-600, yellow-700)
- Error: Red (red-600, red-700)
- Neutral: Gray (gray-50, gray-100, gray-600, gray-900)

**Component Classes**:

```css
/* Form Elements */
.input-field {
  @apply px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500;
}

.btn-primary {
  @apply px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700;
}

/* Status Cards */
.status-card {
  @apply border rounded-lg p-4;
}

.status-processing {
  @apply bg-blue-50 border-blue-200;
}

.status-success {
  @apply bg-green-50 border-green-200;
}

.status-error {
  @apply bg-red-50 border-red-200;
}
```

### Responsive Design

**Breakpoints**:

- Mobile: Default (< 640px)
- Tablet: sm (≥ 640px)
- Desktop: lg (≥ 1024px)

**Layout Adaptations**:

```html
<!-- Mobile-first responsive form -->
<div class="flex flex-col sm:flex-row gap-4">
  <input class="flex-1" type="text" />
  <button class="w-full sm:w-auto">Abfragen</button>
</div>

<!-- Responsive grid for status cards -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
  <!-- Status cards -->
</div>
```

## Performance Optimization

### Loading States

**HTMX Indicators**:

```html
<div id="loading" class="htmx-indicator">
  <div class="flex items-center gap-2 text-blue-600">
    <div
      class="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"
    ></div>
    <span>Geodaten werden verarbeitet...</span>
  </div>
</div>
```

### Error Handling

**Network Error Recovery**:

```javascript
// HTMX error handling
document.body.addEventListener("htmx:responseError", function (evt) {
  const errorDiv = document.getElementById("chat-result");
  errorDiv.innerHTML = `
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
            <h3 class="font-semibold text-red-800">Verbindungsfehler</h3>
            <p class="text-red-600">Bitte versuchen Sie es erneut.</p>
        </div>
    `;
});
```

## Accessibility

**WCAG 2.1 AA Compliance**:

- Semantic HTML structure
- Keyboard navigation support
- Screen reader compatibility
- High contrast color ratios
- Focus indicators
- ARIA labels where appropriate

**Implementation**:

```html
<form role="search" aria-label="Geodaten-Anfrage">
  <input
    type="text"
    aria-label="Geodaten-Anfrage eingeben"
    aria-describedby="search-help"
  />
  <button type="submit" aria-label="Anfrage absenden">Abfragen</button>
</form>
```

## Static Assets

**Directory Structure**:

```
app/frontend/static/
├── css/
│   └── custom.css        # Additional custom styles
├── js/
│   └── htmx-extensions.js # HTMX customizations
└── images/
    └── favicon.ico       # Site favicon
```

**Asset Serving**: FastAPI StaticFiles middleware for efficient static file serving
