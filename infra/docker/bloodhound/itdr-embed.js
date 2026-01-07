(function () {
  const MENU_ITEMS = [
    { id: "itdr_identity_graph", label: "Identity Graph (BloodHound)", url: "/embed/bloodhound" },
    { id: "itdr_identity_governance", label: "Identity Governance (midPoint)", url: "/embed/midpoint" },
  ];

  function findSidebar() {
    // Heuristic: TheHive layout usually includes a <nav> for the left panel.
    // We avoid relying on brittle class names.
    const navs = Array.from(document.querySelectorAll("nav"));
    if (!navs.length) return null;

    // Prefer a nav that contains at least a few links (typical sidebar).
    navs.sort((a, b) => b.querySelectorAll("a").length - a.querySelectorAll("a").length);
    const candidate = navs[0];
    return candidate.querySelectorAll("a").length >= 3 ? candidate : null;
  }

  function getInsertionList(sidebar) {
    // Find a list container to append into.
    return (
      sidebar.querySelector("ul") ||
      sidebar.querySelector("div") ||
      sidebar
    );
  }

  function ensureEmbedContainer() {
    let container = document.getElementById("_itdr_embed_container");
    if (container) return container;

    container = document.createElement("div");
    container.id = "_itdr_embed_container";
    container.style.position = "fixed";
    container.style.display = "none";
    container.style.zIndex = "999";

    const iframe = document.createElement("iframe");
    iframe.id = "_itdr_embed_iframe";
    iframe.style.width = "100%";
    iframe.style.height = "100%";
    iframe.style.border = "0";
    iframe.referrerPolicy = "no-referrer";

    container.appendChild(iframe);
    document.body.appendChild(container);

    function layout() {
      const sidebar = findSidebar();
      const header = document.querySelector("header") || document.querySelector(".navbar") || null;

      let top = 0;
      let left = 0;

      if (header) {
        const r = header.getBoundingClientRect();
        if (r && r.bottom > 0) top = Math.round(r.bottom);
      }
      if (sidebar) {
        const r = sidebar.getBoundingClientRect();
        if (r && r.right > 0) left = Math.round(r.right);
      }

      container.style.top = top + "px";
      container.style.left = left + "px";
      container.style.right = "0";
      container.style.bottom = "0";
    }

    window.addEventListener("resize", layout);
    setInterval(layout, 2000);
    layout();

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        container.style.display = "none";
      }
    });

    return container;
  }

  function openEmbed(url) {
    const container = ensureEmbedContainer();
    const iframe = document.getElementById("_itdr_embed_iframe");
    if (!iframe) return;

    // Toggle if clicking same tool again.
    if (container.style.display !== "none" && iframe.getAttribute("src") === url) {
      container.style.display = "none";
      return;
    }

    iframe.setAttribute("src", url);
    container.style.display = "block";
  }

  function addMenuItem(sidebar, item) {
    if (document.getElementById(item.id)) return;

    const insertion = getInsertionList(sidebar);
    const existingLink = sidebar.querySelector("a");

    let link;
    if (existingLink) {
      link = existingLink.cloneNode(true);
      link.removeAttribute("target");
      link.setAttribute("href", "#");
      link.textContent = item.label;
    } else {
      link = document.createElement("a");
      link.setAttribute("href", "#");
      link.textContent = item.label;
    }

    link.id = item.id;
    link.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openEmbed(item.url);
    });

    const li = document.createElement("li");
    li.appendChild(link);

    // If the sidebar uses <ul>, append <li>; otherwise append the link directly.
    if (insertion.tagName && insertion.tagName.toLowerCase() === "ul") {
      insertion.appendChild(li);
    } else {
      insertion.appendChild(link);
    }
  }

  function bootstrap() {
    const sidebar = findSidebar();
    if (!sidebar) return false;

    for (const item of MENU_ITEMS) addMenuItem(sidebar, item);
    return true;
  }

  // Poll until TheHive UI renders the sidebar.
  const start = Date.now();
  const timer = setInterval(() => {
    if (bootstrap()) {
      clearInterval(timer);
      return;
    }

    if (Date.now() - start > 60000) {
      clearInterval(timer);
    }
  }, 500);
})();
