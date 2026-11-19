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

  function setUp(figure, reduced) {
    var img = figure.querySelector("img");
    var columns = whole(figure, "columns");
    var rows = whole(figure, "rows");
    var rate = whole(figure, "interval");
    var first = figure.getAttribute("data-start") === "first";
    var wholeSource = figure.getAttribute("data-whole-src");
    var cells = columns * rows;
    // The two pictures a figure can show, each a sheet with its own cell size and gap.
    var views = {
      near: {
        image: img,
        gap: whole(figure, "gap"),
        width: whole(figure, "tile-width"),
        height: whole(figure, "tile-height"),
      },
    };
    if (wholeSource !== null) {
      views.far = {
        image: null,
        gap: whole(figure, "whole-gap"),
        width: whole(figure, "whole-tile-width"),
        height: whole(figure, "whole-tile-height"),
      };
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
    var cell = 0;
    var timer = null;
    var moving = false;

    function draw() {
      var sx = (cell % columns) * (view.width + view.gap);
      var sy = Math.floor(cell / columns) * (view.height + view.gap);
      if (canvas.width !== view.width || canvas.height !== view.height) {
        canvas.width = view.width;
        canvas.height = view.height;
      }
      context.clearRect(0, 0, view.width, view.height);
      context.drawImage(view.image, sx, sy, view.width, view.height, 0, 0, view.width, view.height);
    }

    function controls(on) {
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
        cell = (cell + 1) % cells;
        draw();
      }, rate);
    }

    function pause() {
      stop();
      draw();
      show(false);
    }

    buttons.play.addEventListener("click", play);
    buttons.pause.addEventListener("click", pause);
    buttons.step.addEventListener("click", function () {
      stop();
      cell = (cell + 1) % cells;
      draw();
      show(false);
    });

    // Swap to the other picture of the figure, at the same cell and, once it is loaded, in the same state.
    function swap(next) {
      var keep = moving;
      stop();
      if (next.image === null) {
        var loaded = new Image();
        next.image = loaded;
        loaded.addEventListener("load", function () {
          view = next;
          resume(keep);
        });
        loaded.setAttribute("src", wholeSource);
        return;
      }
      view = next;
      resume(keep);
    }

    function resume(keep) {
      if (keep) {
        play();
      } else {
        pause();
      }
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
      if (first || reduced) {
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
  document.querySelectorAll("figure.photo[data-columns]").forEach(function (figure) {
    setUp(figure, reduced);
  });
  openAddress();
  addEventListener("hashchange", openAddress);
})();
