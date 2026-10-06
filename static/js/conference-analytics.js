(() => {
  const page = "/barcelona-2026";
  const key = "protac_conference_session";
  let sessionId = sessionStorage.getItem(key);
  if (!sessionId) { sessionId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`; sessionStorage.setItem(key, sessionId); }
  const query = new URLSearchParams(location.search);
  const defaultCampaign = window.posterAnalyticsCampaign || "ecosystem_poster";
  const referrerHost = (() => { try { return document.referrer ? new URL(document.referrer).hostname : ""; } catch (_) { return ""; } })();
  const attribution = {
    utm_source: query.get("utm_source") || sessionStorage.getItem("protac_utm_source") || referrerHost || "direct",
    utm_medium: query.get("utm_medium") || sessionStorage.getItem("protac_utm_medium") || (referrerHost ? "referral" : "direct"),
    utm_campaign: query.get("utm_campaign") || sessionStorage.getItem("protac_utm_campaign") || defaultCampaign,
    utm_content: query.get("utm_content") || sessionStorage.getItem("protac_utm_content") || "",
  };
  Object.entries(attribution).forEach(([k,v]) => { if (query.get(k)) sessionStorage.setItem(`protac_${k}`, v); });
  const device = innerWidth < 768 ? "mobile" : innerWidth < 1024 ? "tablet" : "desktop";
  const browser = /Firefox/i.test(navigator.userAgent) ? "Firefox" : /Edg/i.test(navigator.userAgent) ? "Edge" : /Chrome/i.test(navigator.userAgent) ? "Chrome" : /Safari/i.test(navigator.userAgent) ? "Safari" : "other";
  const send = (event_type, extra = {}) => {
    const body = JSON.stringify({event_type, session_id: sessionId, page, device_category: device, browser_family: browser, screen_category: innerWidth < 768 ? "small" : innerWidth < 1200 ? "medium" : "large", referrer: document.referrer ? new URL(document.referrer).origin : "", ...attribution, ...extra});
    try { if (navigator.sendBeacon) navigator.sendBeacon("/api/analytics/event", new Blob([body], {type:"application/json"})); else fetch("/api/analytics/event", {method:"POST", headers:{"Content-Type":"application/json"}, body, keepalive:true}).catch(()=>{}); } catch (_) {}
  };
  send("conference_page_view");
  const toolsSection = document.getElementById("tools");
  if (toolsSection && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => { if (entries.some(entry => entry.isIntersecting)) { send("poster_tools_viewed"); observer.disconnect(); } }, {threshold: 0.35});
    observer.observe(toolsSection);
  }
  document.querySelectorAll("[data-analytics-tool]").forEach(a => {
    // Every handoff carries a stable origin, campaign, and destination label.
    // Destination analytics can therefore report arrivals from this poster.
    try {
      const destination = new URL(a.href, location.origin);
      destination.searchParams.set("utm_source", "protac_poster");
      destination.searchParams.set("utm_medium", "ecosystem_referral");
      destination.searchParams.set("utm_campaign", attribution.utm_campaign);
      destination.searchParams.set("utm_content", a.dataset.analyticsToolKey || "tool");
      a.href = destination.toString();
    } catch (_) {}
    a.addEventListener("click", () => send("ecosystem_tool_click", {tool_name:a.dataset.analyticsTool, ecosystem_stage:a.dataset.analyticsStage, destination:a.href}));
  });
  document.querySelectorAll("[data-resource-type]").forEach(a => a.addEventListener("click", () => send("poster_resource_click", {resource_type:a.dataset.resourceType, destination:a.href})));
  document.querySelectorAll("[data-analytics-cta]").forEach(a => a.addEventListener("click", () => send("ecosystem_cta_click", {destination:a.href, resource_type:a.dataset.analyticsCta})));
})();
