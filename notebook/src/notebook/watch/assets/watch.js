/* The refresh of the watch (lab-notebook design, Component 13 and N36). Only the watch serves this script;
   the build never links it.
   Every 1000 ms it reads /version. When the version number changes it fetches the page at the current
   address, keeps the scroll position and the open state of every <details> that has an id, replaces the
   content of main with the content of the fetched page, puts the scroll position and the open states
   back, and sends the event notebook:refresh on the document. notebook.js listens for that event and sets
   up the moving pictures again on the new content.
   When /version carries a stop text, the text is shown with textContent in #watch-stop and the page keeps
   the last content that passed. A request that fails is shown there too, and is not tried another way.
   Every request goes to the same origin, by a relative address. */
(function () {
  "use strict";
  var INTERVAL = 1000;
  var known = null;
  var busy = false;
  function banner() {
    var found = document.getElementById("watch-stop");
    if (found !== null) {
      return found;
    }
    found = document.createElement("p");
    found.id = "watch-stop";
    found.className = "sticky sticky-stamp";
    found.setAttribute("role", "status");
    found.hidden = true;
    var main = document.querySelector("main");
    main.parentNode.insertBefore(found, main);
    return found;
  }
  function say(text) {
    var note = banner();
    if (text === null) {
      note.textContent = "";
      note.hidden = true;
    } else {
      note.textContent = text;
      note.hidden = false;
    }
  }
  function get(address) {
    return fetch(address, { cache: "no-store" }).then(function (reply) {
      if (!reply.ok) {
        throw new Error("the watch answered " + reply.status + " for " + address);
      }
      return reply;
    });
  }
  function opened() {
    var states = {};
    document.querySelectorAll("details[id]").forEach(function (note) {
      states[note.id] = note.open;
    });
    return states;
  }
  function replaceMain(text) {
    var fetched = new DOMParser().parseFromString(text, "text/html").querySelector("main");
    if (fetched === null) {
      throw new Error("the page the watch sent has no main element");
    }
    var main = document.querySelector("main");
    var content = [];
    fetched.childNodes.forEach(function (node) {
      content.push(document.importNode(node, true));
    });
    main.replaceChildren.apply(main, content);
  }
  function refresh() {
    var left = scrollY;
    var states = opened();
    return get(location.pathname)
      .then(function (reply) {
        return reply.text();
      })
      .then(function (text) {
        replaceMain(text);
        document.querySelectorAll("details[id]").forEach(function (note) {
          if (Object.prototype.hasOwnProperty.call(states, note.id)) {
            note.open = states[note.id];
          }
        });
        scrollTo(0, left);
        document.dispatchEvent(new CustomEvent("notebook:refresh"));
      });
  }
  function poll() {
    if (busy) {
      return;
    }
    busy = true;
    get("/version")
      .then(function (reply) {
        return reply.json();
      })
      .then(function (state) {
        say(state.stop);
        if (state.version === known) {
          return null;
        }
        return refresh().then(function () {
          known = state.version;
        });
      })
      .catch(function (problem) {
        say(String(problem.message));
        throw problem;
      })
      .finally(function () {
        busy = false;
      });
  }
  setInterval(poll, INTERVAL);
  poll();
})();
