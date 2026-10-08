/* Privacy-safe Builder milestones. Never send chemistry, atom IDs, or form data. */
(function () {
  const allowed = {
    component_saved: new Set(["warhead", "linker", "recruiter"]),
    attachment_prepared: new Set(["warhead", "linker", "recruiter"]),
    linker_selected: new Set(["curated", "custom"]),
  };

  window.trackProductAnalyticsEvent = function (eventType, feature) {
    if (!allowed[eventType] || !allowed[eventType].has(feature)) return;
    const body = JSON.stringify({event_type: eventType, feature});
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon("/api/product-analytics/event", new Blob([body], {type: "application/json"}));
      } else {
        fetch("/api/product-analytics/event", {method: "POST", headers: {"Content-Type": "application/json"}, body, keepalive: true}).catch(() => {});
      }
    } catch (_) {}
  };
}());
