// Draws the Insights dashboard from /api/insights.
(async function () {
  const css = getComputedStyle(document.documentElement);
  const color = (name) => css.getPropertyValue(name).trim();
  const lakh = (n) => "₹" + (n / 100000).toFixed(1).replace(/\.0$/, "") + " L";

  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = color("--muted");
  Chart.defaults.borderColor = color("--border");

  let data;
  try {
    const res = await fetch("/api/insights");
    if (!res.ok) throw new Error();
    data = await res.json();
  } catch {
    const box = document.getElementById("insights-error");
    box.textContent = "Couldn't load the charts. Please refresh the page.";
    box.hidden = false;
    return;
  }

  function bar(id, series, { horizontal = false, money = false, accent = "--accent" } = {}) {
    new Chart(document.getElementById(id), {
      type: "bar",
      data: {
        labels: series.labels,
        datasets: [{ data: series.values, backgroundColor: color(accent), borderRadius: 4, maxBarThickness: 28 }],
      },
      options: {
        indexAxis: horizontal ? "y" : "x",
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => (money ? lakh(c.raw) : c.raw.toLocaleString("en-IN") + " listings") } },
        },
        scales: {
          [horizontal ? "x" : "y"]: {
            beginAtZero: true,
            grid: { color: color("--grid") },
            ticks: { callback: (v) => (money ? lakh(v) : v.toLocaleString("en-IN")) },
          },
          [horizontal ? "y" : "x"]: {
            grid: { display: false },
            ticks: { autoSkip: false, callback: function (v) {
              const label = this.getLabelForValue(v);
              return label.length > 28 ? label.slice(0, 27) + "…" : label;
            } },
          },
        },
      },
    });
  }

  bar("top_skills", data.top_skills, { horizontal: true });
  bar("top_cities", data.top_cities, { horizontal: true });
  bar("top_companies", data.top_companies, { horizontal: true });
  bar("top_titles", data.top_titles, { horizontal: true });
  bar("salary_bands", data.salary_bands, { accent: "--accent-2" });
  bar("salary_by_experience", data.salary_by_experience, { money: true, accent: "--accent-2" });
  bar("top_paying_titles", data.top_paying_titles, { horizontal: true, money: true, accent: "--accent-2" });

  const pairs = document.getElementById("skill_pairs");
  const max = Math.max(...data.skill_pairs.map((p) => p.count), 1);
  data.skill_pairs.forEach((p) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = `${p.a} + ${p.b}`;
    const meter = document.createElement("span");
    meter.className = "meter";
    meter.style.setProperty("--w", (100 * p.count) / max + "%");
    const n = document.createElement("span");
    n.className = "muted small";
    n.textContent = p.count.toLocaleString("en-IN");
    li.append(name, meter, n);
    pairs.appendChild(li);
  });
})();
