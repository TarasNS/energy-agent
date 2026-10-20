/* Energy 4.0 Harness portal — small enhancements. Every page is readable without this script. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  // Markdown links: set this if the portal is published on GitHub Pages (owner: Dev 3),
  // not needed: every document is built as a page in docs/reference/
  var REPO_BLOB_BASE = "";
  if (REPO_BLOB_BASE && location.protocol !== "file:") {
    document.querySelectorAll('a[href^="../"]').forEach(function (a) {
      var href = a.getAttribute("href");
      if (/\.html(#|$)/.test(href)) return;
      a.setAttribute("href", REPO_BLOB_BASE + href.replace(/^\.\.\//, ""));
    });
  }

  // Copy buttons
  document.querySelectorAll("pre[data-copy]").forEach(function (pre) {
    var btn = document.createElement("button");
    btn.type = "button"; btn.className = "copy"; btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var text = pre.querySelector("code").innerText;
      var done = function () { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy"; }, 1500); };
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, function () { legacy(text); done(); });
      else { legacy(text); done(); }
    });
    pre.appendChild(btn);
  });
  function legacy(text) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "absolute"; ta.style.left = "-9999px";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
  }

  // Diagram legend: show which parts each developer covers
  document.querySelectorAll("[data-legend]").forEach(function (list) {
    var arch = document.getElementById(list.getAttribute("data-legend"));
    if (!arch) return;
    var pinned = null;
    var set = function (d) { if (d) arch.setAttribute("data-focus", d); else arch.removeAttribute("data-focus"); };
    list.querySelectorAll("button[data-d]").forEach(function (b) {
      b.addEventListener("mouseenter", function () { if (!pinned) set(b.dataset.d); });
      b.addEventListener("mouseleave", function () { if (!pinned) set(null); });
      b.addEventListener("focus", function () { if (!pinned) set(b.dataset.d); });
      b.addEventListener("blur", function () { if (!pinned) set(null); });
      b.addEventListener("click", function () {
        pinned = pinned === b.dataset.d ? null : b.dataset.d;
        list.querySelectorAll("button[data-d]").forEach(function (x) { x.setAttribute("aria-pressed", String(x.dataset.d === pinned)); });
        set(pinned);
      });
    });
  });

  // Fade-up on scroll
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("visible"); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("visible"); });
  }
})();

/* Build flow (index.html#combine): point at or tap a task to light up what it waits for and what waits for it. */
(function () {
  "use strict";
  var svg = document.getElementById("flow");
  if (!svg) return;
  var edges = [].slice.call(svg.querySelectorAll(".fe"));
  var nodes = [].slice.call(svg.querySelectorAll(".fn"));
  function walk(id, from, to, seen) {
    edges.forEach(function (ed) {
      if (ed.getAttribute(from) !== id) return;
      ed.classList.add("hot");
      var next = ed.getAttribute(to);
      if (!seen[next]) { seen[next] = 1; walk(next, from, to, seen); }
    });
  }
  function clear() {
    svg.classList.remove("focus");
    edges.concat(nodes).forEach(function (x) { x.classList.remove("hot"); });
  }
  function show(id) {
    clear();
    svg.classList.add("focus");
    var seen = {}; seen[id] = 1;
    walk(id, "data-from", "data-to", seen);
    walk(id, "data-to", "data-from", seen);
    nodes.forEach(function (n) { if (seen[n.getAttribute("data-id")]) n.classList.add("hot"); });
  }
  nodes.forEach(function (n) {
    var id = n.getAttribute("data-id");
    n.addEventListener("mouseenter", function () { show(id); });
    n.addEventListener("mouseleave", clear);
    n.addEventListener("focus", function () { show(id); });
    n.addEventListener("blur", clear);
    n.addEventListener("click", function (ev) { ev.stopPropagation(); show(id); });
  });
  document.addEventListener("click", clear);
})();
