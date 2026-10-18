// The pages' live parts: a fold that refreshes itself from the server every few seconds (data-refresh="URL").
for (const element of document.querySelectorAll("[data-refresh]")) {
  const every = Number(element.dataset.every || 10) * 1000;
  setInterval(async () => {
    try {
      const answer = await fetch(element.dataset.refresh, { credentials: "same-origin" });
      if (answer.ok) element.innerHTML = await answer.text();
    } catch (error) {
      element.dataset.failed = String(error);
    }
  }, every);
}
