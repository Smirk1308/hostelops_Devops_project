/**
 * triage.js — auto-suggest category and priority from complaint description.
 *
 * Debounces the description input, calls POST /api/triage/suggest, and
 * fills #category and #priority selects only if the user has not changed
 * them manually.
 */
(function () {
  'use strict';

  var descEl = document.getElementById('description');
  if (!descEl) return; // Not on a complaint form; do nothing.

  var categoryEl = document.getElementById('category');
  var priorityEl = document.getElementById('priority');
  var hintEl = document.getElementById('triage-hint');

  // Track whether the user has manually changed each select
  var manualCategory = false;
  var manualPriority = false;

  if (categoryEl) {
    categoryEl.addEventListener('change', function () {
      manualCategory = true;
    });
  }
  if (priorityEl) {
    priorityEl.addEventListener('change', function () {
      manualPriority = true;
    });
  }

  /** Read CSRF token from meta tag or hidden input, whichever is present. */
  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    var input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;
    return '';
  }

  /** Set a select value from code (does NOT count as a manual change). */
  function setSelectValue(el, value) {
    if (!el) return false;
    for (var i = 0; i < el.options.length; i++) {
      if (el.options[i].value === value) {
        el.value = value;
        return true;
      }
    }
    return false;
  }

  /** Clear the hint text. */
  function clearHint() {
    if (hintEl) hintEl.textContent = '';
  }

  /** Debounce timer handle and request cancellation tracking. */
  var debounceTimer = null;
  var currentAbortController = null;
  var latestRequestId = 0;

  descEl.addEventListener('input', function () {
    clearTimeout(debounceTimer);

    // Cancel any in-flight request when input changes
    if (currentAbortController) {
      currentAbortController.abort();
      currentAbortController = null;
    }
    latestRequestId++;
    var thisRequestId = latestRequestId;

    var text = descEl.value.trim();

    if (text.length < 5) {
      clearHint();
      return;
    }

    debounceTimer = setTimeout(function () {
      if (typeof window.AbortController !== 'undefined') {
        currentAbortController = new AbortController();
      }
      var signal = currentAbortController ? currentAbortController.signal : null;

      fetch('/api/triage/suggest', {
        method: 'POST',
        credentials: 'same-origin',
        signal: signal,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ text: text }),
      })
        .then(function (resp) {
          if (!resp.ok) {
            clearHint();
            return null;
          }
          return resp.json();
        })
        .then(function (data) {
          // Discard stale responses if input changed or a newer request was dispatched
          if (thisRequestId !== latestRequestId) {
            return;
          }
          if (!data) return;

          var category = data.category;
          var priority = data.priority;
          var confidence = data.confidence;

          if (!category && !priority) {
            clearHint();
            return;
          }

          if (category && !manualCategory) {
            setSelectValue(categoryEl, category);
          }
          if (priority && !manualPriority) {
            setSelectValue(priorityEl, priority);
          }

          if (hintEl && (category || priority)) {
            var pct = Math.round((confidence || 0) * 100);
            var label = 'Suggested: ' + (category || '?') + ' / ' + (priority || '?');
            if (category && typeof confidence === 'number') {
              hintEl.textContent = label + ' · Category confidence: ' + pct + '%';
            } else {
              hintEl.textContent = label;
            }
          }
        })
        .catch(function (err) {
          if (err && err.name === 'AbortError') {
            return; // Normal cancellation of superseded request
          }
          clearHint();
        });
    }, 600);
  });
}());
