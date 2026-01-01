/**
 * FormAI Browser Debloat Script
 *
 * Removes CSS styling and hides popups for faster form detection.
 * Used by MCP Form Agent via --init-script flag.
 */

(function () {
  "use strict";

  // Remove all stylesheets
  function removeStyles() {
    // Disable and remove link stylesheets
    document
      .querySelectorAll('link[rel="stylesheet"]')
      .forEach(function (el) {
        el.disabled = true;
        el.remove();
      });

    // Remove inline style tags
    document.querySelectorAll("style").forEach(function (el) {
      el.remove();
    });

    // Clear body inline styles
    if (document.body) {
      document.body.style.cssText = "";
    }
  }

  // Hide fixed/sticky elements (popups, headers, footers)
  function hidePopups() {
    var selectors = [
      '[style*="position: fixed"]',
      '[style*="position:fixed"]',
      '[style*="position: sticky"]',
      '[style*="position:sticky"]',
      '[class*="popup"]',
      '[class*="modal"]',
      '[class*="overlay"]',
      '[class*="cookie"]',
      '[class*="consent"]',
      '[class*="banner"]',
      '[class*="newsletter"]',
      '[class*="subscribe"]',
      '[id*="popup"]',
      '[id*="modal"]',
      '[id*="cookie"]',
      '[id*="consent"]',
      '[id*="newsletter"]',
      '[role="dialog"]',
      '[aria-modal="true"]',
    ];

    selectors.forEach(function (selector) {
      try {
        document.querySelectorAll(selector).forEach(function (el) {
          // Don't hide if it contains form elements
          if (
            !el.querySelector(
              'input, select, textarea, button[type="submit"]'
            )
          ) {
            el.style.display = "none";
            el.style.visibility = "hidden";
            el.style.opacity = "0";
            el.style.pointerEvents = "none";
          }
        });
      } catch (e) {
        // Ignore selector errors
      }
    });
  }

  // Block tracking scripts
  function blockTrackers() {
    var blockedDomains = [
      "google-analytics.com",
      "googletagmanager.com",
      "facebook.net",
      "onetrust.com",
      "cookiebot.com",
      "hotjar.com",
      "segment.io",
      "intercom.io",
      "drift.com",
      "zendesk.com",
    ];

    // Override script createElement to block tracking scripts
    var originalCreateElement = document.createElement.bind(document);
    document.createElement = function (tagName) {
      var element = originalCreateElement(tagName);

      if (tagName.toLowerCase() === "script") {
        var originalSetAttribute = element.setAttribute.bind(element);
        element.setAttribute = function (name, value) {
          if (name === "src") {
            for (var i = 0; i < blockedDomains.length; i++) {
              if (value.indexOf(blockedDomains[i]) !== -1) {
                console.log("[FormAI] Blocked script:", value);
                return;
              }
            }
          }
          return originalSetAttribute(name, value);
        };
      }

      return element;
    };
  }

  // Run immediately if DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      removeStyles();
      hidePopups();
    });
  } else {
    removeStyles();
    hidePopups();
  }

  // Run after full page load
  window.addEventListener("load", function () {
    removeStyles();
    hidePopups();
  });

  // Watch for dynamic content
  var observer = new MutationObserver(function (mutations) {
    // Only process if new nodes added
    var hasNewNodes = mutations.some(function (m) {
      return m.addedNodes.length > 0;
    });

    if (hasNewNodes) {
      // Debounce to avoid excessive processing
      clearTimeout(window._debloatTimeout);
      window._debloatTimeout = setTimeout(function () {
        removeStyles();
        hidePopups();
      }, 100);
    }
  });

  // Start observing when body is available
  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });
    });
  }

  // Block trackers
  blockTrackers();

  console.log("[FormAI] Browser debloating active");
})();
