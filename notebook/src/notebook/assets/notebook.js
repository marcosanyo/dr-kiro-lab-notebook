/* The notebook's one script (lab-notebook design 10 and 9). It makes no request and loads no other code
   except the pictures the page names.

   Moving pictures: every figure.photo with layout data gets a canvas that shows one cell of the picture sheet
   at a time, in reading order (left to right, then top to bottom), one cell per data-interval ms (set per lab
   in layouts.toml), looping. Only the cells of the sheet are shown: nothing between two cells is made.
   The sheet is never re-encoded: each cell is drawn from the loaded image with a source rectangle that
   skips the gap between cells. Controls: play, pause, step one cell, whole picture.
   The magnified picture of a body-lab trial moves on its own. Its whole picture is not on the page: the
   "whole picture" control swaps it in at the same place and cell, loading the sheet named by data-whole-src,
   and it moves the same way; a second control swaps the magnified picture back. A body-lab picture without a
   magnified one (a lab card, data-start "first") waits on its first cell until play is pressed.
   When the browser asks for reduced motion, a moving picture starts paused on its first cell.

   The night lab and the day lab: a button switches `data-mode` on the root element.
   Addresses: the <details> named by the address, and every <details> around it, are opened.

   Without this script a body-lab picture shows its first cell and a wind-tunnel picture its whole sheet;
   nothing needs it to be read. */
(function () {
  "use strict";

  function whole(figure, name) {
    var value = figure.getAttribute("data-" + name);
    if (value === null || !/^[0-9]+$/.test(value)) {
      throw new Error("a moving picture has no whole-number data-" + name);
    }
    return Number(value);
  }
  // The stylesheet gives `.photo img` and `.photo canvas` a display value, which would win over the hidden
  // attribute alone, so the inline style is set too.
  function shown(element, on) {
    if (element === undefined) {
      return;
    }
    element.hidden = !on;
    element.style.display = on ? "" : "none";
  }
  // One moving picture. It returns the little interface the group controls use: `seek(fraction)` shows the
  // cell at that fraction of the way through (0 to 1), `play` and `pause` start and stop it, `position`
  // says the fraction it is at.
  function setUp(figure, reduced, grouped) {
    var img = figure.querySelector("img");
    var first = figure.getAttribute("data-start") === "first";
    var wholeSource = figure.getAttribute("data-whole-src");
    // The two pictures a figure can show, each a sheet with its own cells, gap and rate.
    var views = {
      near: {
        image: img,
        gap: whole(figure, "gap"),
        width: whole(figure, "tile-width"),
        height: whole(figure, "tile-height"),
        columns: whole(figure, "columns"),
        rows: whole(figure, "rows"),
        rate: whole(figure, "interval"),
      },
    };
    views.near.cells = views.near.columns * views.near.rows;
    if (wholeSource !== null) {
      views.far = {
        image: null,
        gap: whole(figure, "whole-gap"),
        width: whole(figure, "whole-tile-width"),
        height: whole(figure, "whole-tile-height"),
        columns: whole(figure, "whole-columns"),
        rows: whole(figure, "whole-rows"),
        rate: whole(figure, "whole-interval"),
      };
      views.far.cells = views.far.columns * views.far.rows;
    }
    var view = views.near;
    var canvas = document.createElement("canvas");
    shown(canvas, false);
    img.parentNode.insertBefore(canvas, img);
    var context = canvas.getContext("2d");
    var buttons = {};
    figure.querySelectorAll("button[data-action]").forEach(function (button) {
      buttons[button.getAttribute("data-action")] = button;
    });
    var captions = {};
    figure.querySelectorAll("[data-caption]").forEach(function (span) {
      captions[span.getAttribute("data-caption")] = span;
    });
    var clock = figure.querySelectorAll("[data-frame]");
    var cell = 0;
    var timer = null;
    var moving = false;
    function draw() {
      var sx = (cell % view.columns) * (view.width + view.gap);
      var sy = Math.floor(cell / view.columns) * (view.height + view.gap);
      if (canvas.width !== view.width || canvas.height !== view.height) {
        canvas.width = view.width;
        canvas.height = view.height;
      }
      context.clearRect(0, 0, view.width, view.height);
      context.drawImage(view.image, sx, sy, view.width, view.height, 0, 0, view.width, view.height);
      // The words under the picture belong to the frame of the retaken picture only.
      clock.forEach(function (span) {
        shown(span, view === views.near && Number(span.getAttribute("data-frame")) === cell);
      });
    }
    function controls(on) {
      shown(captions.near, views.far === undefined || view === views.near);
      shown(captions.far, views.far !== undefined && view === views.far);
      moving = on;
      shown(buttons.play, !on);
      shown(buttons.pause, on);
      shown(buttons.step, true);
      shown(buttons.sheet, views.far === undefined || view === views.near);
      shown(buttons.back, views.far !== undefined && view === views.far);
    }
    function show(on) {
      shown(canvas, true);
      shown(img, false);
      controls(on);
    }
    function stop() {
      if (timer !== null) {
        clearInterval(timer);
        timer = null;
      }
    }
    function play() {
      stop();
      draw();
      show(true);
      timer = setInterval(function () {
        cell = (cell + 1) % view.cells;
        draw();
      }, view.rate);
    }
    function pause() {
      stop();
      draw();
      show(false);
    }
    function seek(fraction) {
      stop();
      cell = Math.min(view.cells - 1, Math.round(fraction * (view.cells - 1)));
      pause();
    }
    if (buttons.play !== undefined) {
      buttons.play.addEventListener("click", play);
      buttons.pause.addEventListener("click", pause);
      buttons.step.addEventListener("click", function () {
        stop();
        cell = (cell + 1) % view.cells;
        draw();
        show(false);
      });
    }
    // Swap to the other picture of the figure, at the same place in the motion and, once it is loaded, in
    // the same state.
    function swap(next) {
      var keep = moving;
      var fraction = view.cells > 1 ? cell / (view.cells - 1) : 0;
      stop();
      var go = function () {
        view = next;
        cell = Math.round(fraction * (view.cells - 1));
        if (keep) {
          play();
        } else {
          pause();
        }
      };
      if (next.image === null) {
        var loaded = new Image();
        next.image = loaded;
        loaded.addEventListener("load", go);
        loaded.setAttribute("src", wholeSource);
        return;
      }
      go();
    }
    // A wind-tunnel picture only: the sheet itself, every cell side by side.
    function sheet() {
      stop();
      shown(canvas, false);
      shown(img, true);
      shown(buttons.play, true);
      shown(buttons.pause, false);
      shown(buttons.step, true);
      shown(buttons.sheet, false);
    }
    if (buttons.sheet !== undefined) {
      buttons.sheet.addEventListener("click", views.far !== undefined ? function () { swap(views.far); } : sheet);
    }
    if (buttons.back !== undefined) {
      buttons.back.addEventListener("click", function () { swap(views.near); });
    }
    function start() {
      if (grouped || first || reduced) {
        pause();
      } else {
        play();
      }
    }
    if (img.complete && img.naturalWidth > 0) {
      start();
    } else {
      img.addEventListener("load", start);
    }
    return {
      seek: seek,
      play: function () {
        if (moving) {
          return;
        }
        play();
      },
      pause: pause,
      cells: function () {
        return views.near.cells;
      },
      position: function () {
        return view.cells > 1 ? cell / (view.cells - 1) : 0;
      },
    };
  }
  // The photos of one `section[data-sync]` play together, with one set of controls under them: a play and
  // a pause button and a slider that moves them all through the same moment.
  function setUpGroup(group, reduced) {
    var parts = [];
    group.querySelectorAll("figure.photo[data-columns]").forEach(function (figure) {
      parts.push(setUp(figure, reduced, true));
    });
    if (parts.length === 0) {
      return;
    }
    var steps = parts[0].cells();
    var position = 0;
    var timer = null;
    var bar = document.createElement("p");
    bar.className = "sync-bar";
    var button = document.createElement("button");
    button.type = "button";
    button.className = "sync-play";
    var slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = String(steps - 1);
    slider.value = "0";
    slider.setAttribute("aria-label", group.getAttribute("data-label") || "time");
    bar.appendChild(button);
    bar.appendChild(slider);
    group.appendChild(bar);
    var labels = [group.getAttribute("data-play"), group.getAttribute("data-pause")];
    function go(index) {
      position = index;
      slider.value = String(index);
      parts.forEach(function (part) {
        part.seek(steps > 1 ? index / (steps - 1) : 0);
      });
    }
    function stop() {
      if (timer !== null) {
        clearInterval(timer);
        timer = null;
      }
      button.textContent = labels[0];
    }
    function play() {
      stop();
      button.textContent = labels[1];
      var rate = Number(group.getAttribute("data-interval"));
      timer = setInterval(function () {
        go((position + 1) % steps);
      }, rate);
    }
    button.addEventListener("click", function () {
      if (timer === null) {
        play();
      } else {
        stop();
      }
    });
    slider.addEventListener("input", function () {
      stop();
      go(Number(slider.value));
    });
    stop();
    go(0);
    if (!reduced) {
      play();
    }
  }
  function openAddress() {
    var name = decodeURIComponent(location.hash.slice(1));
    if (name === "") {
      return;
    }
    var target = document.getElementById(name);
    if (target === null) {
      return;
    }
    for (var node = target; node !== null; node = node.parentElement) {
      if (node.nodeName === "DETAILS") {
        node.open = true;
      }
    }
    target.scrollIntoView();
  }

  var reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // A figure inside a closed <details> is set up when the note is first opened, so a page with many trials
  // moves only the pictures that are in view.
  document.querySelectorAll("section[data-sync]").forEach(function (group) {
    setUpGroup(group, reduced);
  });
  document.querySelectorAll("figure.photo[data-columns]").forEach(function (figure) {
    if (figure.closest("section[data-sync]") !== null) {
      return;
    }
    var note = figure.closest("details");
    if (note === null || note.open) {
      setUp(figure, reduced, false);
      return;
    }
    note.addEventListener(
      "toggle",
      function () {
        if (figure.getAttribute("data-ready") === null) {
          figure.setAttribute("data-ready", "yes");
          setUp(figure, reduced, false);
        }
      },
      { once: true }
    );
  });
  // The night lab and the day lab. The page opens in the night lab; the button switches it and the choice is
  // kept for the other pages when the browser allows it (it is the only thing the script stores).
  var KEY = "notebook-mode";
  var root = document.documentElement;
  var toggle = document.querySelector("button.mode-toggle");
  function applyMode(mode) {
    if (mode === "day") {
      root.setAttribute("data-mode", "day");
    } else {
      root.removeAttribute("data-mode");
    }
    if (toggle !== null) {
      var label = toggle.querySelector("span") || toggle;
      label.textContent = toggle.getAttribute(mode === "day" ? "data-to-night" : "data-to-day");
    }
  }
  if (toggle !== null) {
    var saved = null;
    try {
      saved = localStorage.getItem(KEY);
    } catch (error) {
      saved = null; // storage is blocked: the page simply opens in the night lab
    }
    applyMode(saved === "day" ? "day" : "night");
    toggle.hidden = false;
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-mode") === "day" ? "night" : "day";
      applyMode(next);
      try {
        localStorage.setItem(KEY, next);
      } catch (error) {
        return; // storage is blocked: the choice lasts for this page only
      }
    });
  }
  openAddress();
  addEventListener("hashchange", openAddress);
})();
