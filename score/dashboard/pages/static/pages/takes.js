// A sound's takes side by side (pages/library_item.html): each take's waveform drawn from its decoded samples, a
// click or its button plays it from the start or stops it, one take at a time; the played share is drawn over it.
(function () {
  const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const listen = new AudioContext();
  const playing = { source: null, take: null, began: 0 };

  function draw(take, played) {
    const canvas = take.canvas, paint = canvas.getContext("2d"), { width, height } = canvas;
    paint.clearRect(0, 0, width, height);
    if (!take.peaks) return;
    take.peaks.forEach(([low, high], column) => {
      paint.fillStyle = column / width < played ? token("--color-accent") : token("--color-text-faint");
      paint.fillRect(column, (1 - high) * height / 2, 1, Math.max(1, (high - low) * height / 2));
    });
  }

  // Each pixel column's lowest and highest sample.
  function peaks(samples, columns) {
    const per = Math.max(1, Math.floor(samples.length / columns));
    return Array.from({ length: columns }, (_, column) => {
      let low = 0, high = 0;
      for (let index = column * per; index < Math.min((column + 1) * per, samples.length); index++) {
        low = Math.min(low, samples[index]);
        high = Math.max(high, samples[index]);
      }
      return [low, high];
    });
  }

  function stop() {
    if (!playing.source) return;
    playing.source.onended = null;
    playing.source.stop();
    const take = playing.take;
    Object.assign(playing, { source: null, take: null });
    take.button.innerHTML = "&#9654;";
    draw(take, 0);
  }

  function play(take) {
    const again = playing.take === take;
    stop();
    if (again || !take.buffer) return;
    listen.resume();
    const source = listen.createBufferSource();
    source.buffer = take.buffer;
    source.connect(listen.destination);
    source.onended = stop;
    source.start();
    Object.assign(playing, { source, take, began: listen.currentTime });
    take.button.innerHTML = "&#9632;";
    const step = () => {
      if (playing.take !== take) return;
      draw(take, (listen.currentTime - playing.began) / take.buffer.duration);
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  async function open(canvas) {
    const take = { canvas, button: canvas.closest(".take").querySelector("[data-play]"), buffer: null, peaks: null };
    canvas.width = canvas.clientWidth * Math.min(window.devicePixelRatio, 2);
    canvas.addEventListener("click", () => play(take));
    take.button.addEventListener("click", () => play(take));
    try {
      const answer = await fetch(canvas.dataset.wave, { credentials: "same-origin" });
      if (!answer.ok) throw new Error(`${canvas.dataset.wave}: ${answer.status}`);
      take.buffer = await listen.decodeAudioData(await answer.arrayBuffer());
      take.peaks = peaks(take.buffer.getChannelData(0), canvas.width);
      draw(take, 0);
    } catch (error) {
      canvas.closest(".take").classList.add("failed");
      console.error(error);
    }
  }

  document.querySelectorAll("canvas[data-wave]").forEach(open);
})();
