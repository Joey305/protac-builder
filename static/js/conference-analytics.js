(() => {
  const page = "/barcelona-2026";
  const key = "protac_conference_session";
  let sessionId = sessionStorage.getItem(key);
  if (!sessionId) { sessionId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`; sessionStorage.setItem(key, sessionId); }
  const query = new URLSearchParams(location.search);
  const attribution = Object.fromEntries(["utm_source","utm_medium","utm_campaign","utm_content"].map(k => [k, query.get(k) || sessionStorage.getItem(`protac_${k}`) || ""]));
  Object.entries(attribution).forEach(([k,v]) => { if (query.get(k)) sessionStorage.setItem(`protac_${k}`, v); });
  const device = innerWidth < 768 ? "mobile" : innerWidth < 1024 ? "tablet" : "desktop";
  const browser = /Firefox/i.test(navigator.userAgent) ? "Firefox" : /Edg/i.test(navigator.userAgent) ? "Edge" : /Chrome/i.test(navigator.userAgent) ? "Chrome" : /Safari/i.test(navigator.userAgent) ? "Safari" : "other";
  const send = (event_type, extra = {}) => {
    const body = JSON.stringify({event_type, session_id: sessionId, page, device_category: device, browser_family: browser, screen_category: innerWidth < 768 ? "small" : innerWidth < 1200 ? "medium" : "large", referrer: document.referrer ? new URL(document.referrer).origin : "", ...attribution, ...extra});
    try { if (navigator.sendBeacon) navigator.sendBeacon("/api/analytics/event", new Blob([body], {type:"application/json"})); else fetch("/api/analytics/event", {method:"POST", headers:{"Content-Type":"application/json"}, body, keepalive:true}).catch(()=>{}); } catch (_) {}
  };
  send("conference_page_view");
  document.querySelectorAll("[data-analytics-tool]").forEach(a => a.addEventListener("click", () => send("ecosystem_tool_click", {tool_name:a.dataset.analyticsTool, ecosystem_stage:a.dataset.analyticsStage, destination:a.href})));
  document.querySelectorAll("[data-resource-type]").forEach(a => a.addEventListener("click", () => send("poster_resource_click", {resource_type:a.dataset.resourceType, destination:a.href})));
  document.querySelectorAll("[data-analytics-cta]").forEach(a => a.addEventListener("click", () => send("ecosystem_cta_click", {destination:a.href, resource_type:a.dataset.analyticsCta})));
})();
