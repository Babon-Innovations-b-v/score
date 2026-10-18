// The Library grid's choice: ticking pictures shows a bar to lock or withdraw them together.
const picked = document.getElementById("lib-pick");
if (picked) {
  const bar = picked.querySelector(".lib-bar");
  const boxes = () => [...document.querySelectorAll('input[name="address"][form="lib-pick"]')];
  const show = () => {
    const chosen = boxes().filter((box) => box.checked);
    bar.hidden = chosen.length === 0;
    bar.querySelector("[data-picked]").textContent = String(chosen.length);
    bar.querySelector('[value="lock"]').disabled = !chosen.every((box) => box.dataset.state === "draft");
    bar.querySelector('[value="withdraw"]').disabled = !chosen.every((box) => box.dataset.state === "locked");
    for (const box of boxes()) box.closest(".tile").classList.toggle("chosen", box.checked);
  };
  document.addEventListener("change", (event) => { if (event.target.matches('input[name="address"]')) show(); });
  bar.querySelector("[data-unpick]").addEventListener("click", () => { for (const box of boxes()) box.checked = false; show(); });
  show();
}
