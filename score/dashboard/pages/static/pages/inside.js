// The design page's rooms inside this scene (pages/plans.py plan_named): each name a chip with its x, one more added
// on Enter or Add; every change posts the whole list for the place, whose draws hold them and whose plan lays each
// out, each its own scene with its own card. A note typed there by mistake (owner, 2026-10-21: "you need to be able
// to walk past" became a room) is refused: a name is a few words, a note goes in the note box.
(() => {
  const input = document.getElementById("concept-inside");
  const button = document.getElementById("concept-name");
  const chips = document.getElementById("concept-inside-names");
  if (!input || !button || !chips) return;
  const said = document.getElementById("inside-said");
  const LONGEST = 4;  // words: a room's name, not a sentence
  const cookie = (name) => (document.cookie.split("; ").find((part) => part.startsWith(name + "=")) || "").split("=")[1];
  const tell = (tone, words) => {
    said.className = `dot tone-${tone}`;
    said.title = words;
    said.hidden = false;
  };
  const names = () => [...chips.children].map((chip) => chip.dataset.name);
  const chip = (name) => {
    const item = document.createElement("li");
    item.dataset.name = name;
    item.innerHTML = '<span data-v></span><button type="button" class="chip-drop" aria-label="remove">&times;</button>';
    item.querySelector("span").textContent = name;
    item.querySelector("button").title = `remove ${name}: no scene of its own`;
    return item;
  };
  const sent = async (wanted) => {
    const answer = await fetch(`/plan/${input.dataset.place}/named/`, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
      body: JSON.stringify({ names: wanted }),
    });
    const found = await answer.json().catch(() => ({}));
    if (!answer.ok) throw new Error(String(found.detail || answer.status));
    chips.replaceChildren(...wanted.map(chip));
    tell("done", found.said);
  };
  const added = async () => {
    const name = input.value.trim();
    if (!name) return;
    if (name.split(/\s+/).length > LONGEST) { tell("bad", "a room's name, a few words: a note goes in the note box"); return; }
    if (names().includes(name)) { input.value = ""; return; }
    button.disabled = true;
    try {
      await sent([...names(), name]);
      input.value = "";
    } catch (error) {
      tell("bad", error.message);
      console.error("room name refused", error);
    }
    button.disabled = false;
  };
  button.addEventListener("click", added);
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); added(); } });
  chips.addEventListener("click", async (event) => {
    const drop = event.target.closest(".chip-drop");
    if (!drop) return;
    drop.disabled = true;
    const gone = drop.closest("li").dataset.name;
    try {
      await sent(names().filter((name) => name !== gone));
    } catch (error) {
      tell("bad", error.message);
      console.error("room removal refused", error);
      drop.disabled = false;
    }
  });
})();
