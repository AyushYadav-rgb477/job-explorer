// CV upload + rendering of match results on the home page.
(function () {
  const form = document.getElementById("match-form");
  const input = document.getElementById("cv-input");
  const dropzone = document.getElementById("dropzone");
  const title = document.getElementById("drop-title");
  const button = document.getElementById("match-btn");
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  const lakh = (n) => "₹" + (n / 100000).toFixed(2).replace(/\.?0+$/, "") + " L";

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function chips(list, cls) {
    const wrap = el("div", "chips");
    list.forEach((s) => wrap.appendChild(el("span", "chip " + (cls || ""), s)));
    return wrap;
  }

  input.addEventListener("change", () => {
    title.textContent = input.files[0] ? input.files[0].name : "Choose a CV or drop it here";
  });
  ["dragenter", "dragover"].forEach((e) =>
    dropzone.addEventListener(e, (ev) => { ev.preventDefault(); dropzone.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((e) =>
    dropzone.addEventListener(e, () => dropzone.classList.remove("drag")));
  dropzone.addEventListener("drop", (ev) => {
    ev.preventDefault();
    if (ev.dataTransfer.files.length) {
      input.files = ev.dataTransfer.files;
      input.dispatchEvent(new Event("change"));
    }
  });

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!input.files[0]) return;
    button.disabled = true;
    button.textContent = "Matching…";
    status.className = "status";
    status.textContent = "Reading your CV and ranking jobs…";
    results.hidden = true;

    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "X-CSRF-Token": csrf },
        body: new FormData(form),
      });
      const data = await res.json().catch(() => ({ error: "Unexpected server response." }));
      if (!res.ok) throw new Error(data.error || "Something went wrong.");
      render(data);
      status.textContent = data.matches.length
        ? (data.saved ? "Done — results saved to your History." : "Done.")
        : "";
    } catch (err) {
      status.className = "status error";
      status.textContent = err.message;
    } finally {
      button.disabled = false;
      button.textContent = "Find matching jobs";
    }
  });

  function render(data) {
    const skillBox = document.getElementById("cv-skills");
    skillBox.replaceChildren();
    if (data.cv_skills.length) {
      skillBox.appendChild(chips(data.cv_skills, "chip-good"));
    } else {
      skillBox.appendChild(el("p", "muted", "We couldn't spot any skills from our job listings in your CV."));
    }

    const list = document.getElementById("matches");
    list.replaceChildren();
    if (!data.matches.length) {
      list.appendChild(el("p", "muted", "No matching jobs found. Try a CV with more skills listed."));
    }
    data.matches.forEach((job) => {
      const card = el("article", "card match");
      const head = el("div", "match-head");
      const info = el("div");
      info.appendChild(el("h3", "", job.title));
      const meta = [job.company, job.cities.slice(0, 3).join(", ") + (job.cities.length > 3 ? " +" + (job.cities.length - 3) : "")];
      if (job.is_hybrid) meta.push("Hybrid");
      if (job.salary_min) meta.push(lakh(job.salary_min) + (job.salary_max !== job.salary_min ? " – " + lakh(job.salary_max) : ""));
      info.appendChild(el("p", "muted", meta.filter(Boolean).join(" · ")));
      head.appendChild(info);
      const score = el("div", "score", job.score + "%");
      score.style.setProperty("--pct", Math.min(job.score, 100));
      head.appendChild(score);
      card.appendChild(head);

      if (job.matched_skills.length) {
        card.appendChild(el("p", "label", "You have"));
        card.appendChild(chips(job.matched_skills, "chip-good"));
      }
      if (job.missing_skills.length) {
        card.appendChild(el("p", "label", "Skills to learn"));
        card.appendChild(chips(job.missing_skills, "chip-gap"));
      }
      const link = el("a", "btn btn-ghost btn-small", "View on Internshala ↗");
      link.href = job.url;
      link.target = "_blank";
      link.rel = "noopener";
      card.appendChild(link);
      list.appendChild(card);
    });
    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }
})();
