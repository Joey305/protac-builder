(function () {
  const state = {
    timer: null,
    mode: "overlay",
    target: null,
    root: null,
    messages: [],
    index: 0,
  };

  function normalizeMessages(messages) {
    return (messages || []).map((message) => {
      if (typeof message === "string") return { html: message };
      return message;
    });
  }

  function getOverlayElements() {
    return {
      shell: document.getElementById("async-loading"),
      title: document.getElementById("async-loading-title"),
      message: document.getElementById("async-loading-message"),
      subtle: document.getElementById("async-loading-subtle"),
    };
  }

  function resolveInlineElements(target) {
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) return null;

    const root = el.matches("[data-loader-root]") ? el : el.querySelector("[data-loader-root]") || el;
    return {
      shell: root,
      title: root.querySelector("[data-loader-title]"),
      message: root.querySelector("[data-loader-message]"),
      subtle: root.querySelector("[data-loader-subtle]"),
    };
  }

  function renderMessage(target, html) {
    if (!target) return;
    if (window.jQuery) {
      window.jQuery(target).fadeOut(150, function updateMessage() {
        window.jQuery(this).html(html).fadeIn(150);
      });
      return;
    }
    target.innerHTML = html;
  }

  function rotate(renderMessage) {
    clearInterval(state.timer);
    if (state.messages.length < 2) return;
    state.timer = setInterval(() => {
      state.index = (state.index + 1) % state.messages.length;
      renderMessage(state.messages[state.index].html || "");
    }, 4500);
  }

  function renderInline(target, options) {
    const elements = resolveInlineElements(target);
    if (!elements) return;

    if (elements.title) elements.title.textContent = options.title || "Working…";
    if (elements.subtle) elements.subtle.textContent = options.subtle || "This may take a moment.";
    if (elements.message) elements.message.innerHTML = state.messages[0]?.html || "";
    elements.shell.classList.remove("d-none");

    rotate((html) => renderMessage(elements.message, html));

    state.target = typeof target === "string" ? document.querySelector(target) : target;
    state.root = elements.shell;
  }

  function renderOverlay(options) {
    const { shell, title, message, subtle } = getOverlayElements();
    if (!shell || !title || !message || !subtle) return;
    title.textContent = options.title;
    message.innerHTML = state.messages[0]?.html || "";
    subtle.textContent = options.subtle || "";
    shell.classList.remove("d-none");
    rotate((html) => {
      message.innerHTML = html;
    });
  }

  window.ProtacLoader = {
    show(options = {}) {
      state.messages = normalizeMessages(options.messages || ["Working…"]);
      state.index = 0;
      state.mode = options.mode || "overlay";
      state.target = null;
      state.root = null;

      if (state.mode === "inline" && options.target) {
        renderInline(options.target, options);
        return;
      }

      renderOverlay({
        title: options.title || "Working…",
        subtle: options.subtle || "This may take a moment.",
      });
    },

    hide(target) {
      clearInterval(state.timer);
      state.timer = null;

      if (target) {
        const el = typeof target === "string" ? document.querySelector(target) : target;
        if (el) {
          const root = el.matches?.("[data-loader-root]") ? el : el.querySelector?.("[data-loader-root]");
          if (root) {
            root.classList.add("d-none");
            const message = root.querySelector("[data-loader-message]");
            if (message) message.innerHTML = "";
          } else {
            el.innerHTML = "";
          }
        }
      }

      if (state.target) {
        if (state.root) {
          state.root.classList.add("d-none");
        } else {
          state.target.innerHTML = "";
        }
        state.target = null;
        state.root = null;
      }

      const { shell, message } = getOverlayElements();
      if (shell) shell.classList.add("d-none");
      if (message) message.innerHTML = "";
    },
  };

  window.startAsyncLoader = function startAsyncLoader(options = {}) {
    window.ProtacLoader.show({
      mode: "overlay",
      title: options.title || "Working…",
      messages: options.messages || ["Working…"],
      subtle: options.subtle || "This may take a moment.",
    });
  };

  window.stopAsyncLoader = function stopAsyncLoader() {
    window.ProtacLoader.hide();
  };
})();
