/* The notebook's one script (lab-notebook design 10 and 9). It makes no request and loads no other code.

   Moving pictures: every figure.photo with layout data gets a canvas that shows one cell of the picture sheet
   at a time, in reading order (left to right, then top to bottom), one cell per --cell-interval, looping.
   The sheet is never re-encoded: each cell is drawn from the loaded image with a source rectangle that
   skips the gap between cells. Controls: play, pause, step one cell, whole sheet. When the browser asks for
   reduced motion, a picture starts paused on its first cell.

   Addresses: the <details> named by the address, and every <details> around it, are opened.

   Without this script the page shows every whole sheet and every text; nothing needs it to be read. */
(function () {
  "use strict";

  function interval() {
    var value = getComputedStyle(document.documentElement).getPropertyValue("--cell-interval").trim();
    var match = /^([0-9]+)ms$/.exec(value);
    if (match === null) {
      throw new Error("notebook.css must set --cell-interval in ms, got '" + value + "'");
    }
    return Number(match[1]);
  }

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
    element.hidden = !on;
    element.style.display = on ? "" : "none";
  }

  function setUp(figure, rate, reduced) {
    var img = figure.querySelector("img");
    var columns = whole(figure, "columns");
    var rows = whole(figure, "rows");
    var gap = whole(figure, "gap");
    var tileWidth = whole(figure, "tile-width");
    var tileHeight = whole(figure, "tile-height");
    var cells = columns * rows;
    var canvas = document.createElement("canvas");
    canvas.width = tileWidth;
    canvas.height = tileHeight;
    shown(canvas, false);
    img.parentNode.insertBefore(canvas, img);
    var context = canvas.getContext("2d");
    var buttons = {};
    figure.querySelectorAll("button[data-action]").forEach(function (button) {
      buttons[button.getAttribute("data-action")] = button;
    });
    var cell = 0;
    var timer = null;

    function draw() {
      var sx = (cell % columns) * (tileWidth + gap);
      var sy = Math.floor(cell / columns) * (tileHeight + gap);
      context.clearRect(0, 0, tileWidth, tileHeight);
      context.drawImage(img, sx, sy, tileWidth, tileHeight, 0, 0, tileWidth, tileHeight);
    }

    function show(moving) {
      shown(canvas, true);
      shown(img, false);
      shown(buttons.play, !moving);
      shown(buttons.pause, moving);
      shown(buttons.step, true);
      shown(buttons.sheet, true);
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
    buttons.sheet.addEventListener("click", function () {
      stop();
      shown(canvas, false);
      shown(img, true);
      shown(buttons.play, true);
      shown(buttons.pause, false);
      shown(buttons.step, true);
      shown(buttons.sheet, false);
    });

    function start() {
      if (reduced) {
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
  var rate = interval();
  document.querySelectorAll("figure.photo[data-columns]").forEach(function (figure) {
    setUp(figure, rate, reduced);
  });
  openAddress();
  addEventListener("hashchange", openAddress);
})();
