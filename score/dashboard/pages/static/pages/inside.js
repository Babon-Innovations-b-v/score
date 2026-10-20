// The concept page's inside places (pages/plans.py plan_named): the names he types, comma between, posted for the
// place; its draws hold them and its plan lays each out.
(() => {
  const input = document.getElementById("concept-inside");
  const button = document.getElementById("concept-name");
  if (!input || !button) return;
  const said = document.getElementById("concept-said");
  const cookie = (name) => (document.cookie.split("; ").find((part) => part.startsWith(name + "=")) || "").split("=")[1];
  button.addEventListener("click", async () => {
    button.disabled = true;
    const names = input.value.split(",").map((name) => name.trim()).filter(Boolean);
    const answer = await fetch(`/plan/${input.dataset.place}/named/`, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
      body: JSON.stringify({ names }),
    });
    const found = await answer.json().catch(() => ({}));
    said.className = `dot tone-${answer.ok ? "done" : "bad"}`;
    said.title = answer.ok ? found.said : String(found.detail || answer.status);
    said.hidden = false;
    button.disabled = false;
  });
})();
