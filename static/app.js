function navLink(label, href) {
  const a = document.createElement("a");
  a.href = href;
  a.textContent = label;
  if (window.location.pathname === href) {
    a.style.background = "rgba(96,165,250,.14)";
    a.style.borderColor = "rgba(96,165,250,.35)";
    a.style.borderStyle = "solid";
    a.style.borderWidth = "1px";
  }
  return a;
}

export function mountNavbar() {
  const nav = document.createElement("div");
  nav.className = "app-nav";
  const left = document.createElement("div");
  left.className = "brand";
  left.innerHTML = `<span class="logo"></span><span>Health Intelligence</span>`;

  const right = document.createElement("div");
  right.className = "links";
  right.appendChild(navLink("Home", "/"));
  right.appendChild(navLink("Live Pose", "/live-pose"));
  right.appendChild(navLink("Nutrition", "/nutrition-planner"));
  right.appendChild(navLink("Daily Progress", "/daily-progress"));
  right.appendChild(navLink("Cook", "/cook-assistant"));
  right.appendChild(navLink("Yoga", "/yoga-mode"));

  nav.appendChild(left);
  nav.appendChild(right);

  document.body.prepend(nav);
}

export function scoreToChip(score) {
  const s = Number(score);
  if (!Number.isFinite(s)) return { cls: "", label: "—" };
  if (s >= 85) return { cls: "good", label: "Correct" };
  if (s >= 70) return { cls: "warn", label: "Almost" };
  return { cls: "bad", label: "Incorrect" };
}

export function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

