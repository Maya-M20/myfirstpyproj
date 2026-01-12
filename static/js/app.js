let skip = 0;
const limit = 5;
let total = 0;

/* ---------------- STATUS ---------------- */

function setStatus(msg, isError = false) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.style.color = isError ? "red" : "green";
}

/* ---------------- ADD MOLECULE ---------------- */

async function addMolecule() {
  const id = document.getElementById("mol-id").value.trim();
  const smiles = document.getElementById("mol-smiles").value.trim();

  if (!id || !smiles) {
    setStatus("ID и SMILES обязательны", true);
    return;
  }

  try {
    setStatus("Добавление молекулы...");
    const res = await fetch("/molecules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, smiles })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Ошибка добавления");

    setStatus("Молекула добавлена ✅");
    skip = 0;
    loadMolecules();
  } catch (e) {
    setStatus(e.message, true);
  }
}

/* ---------------- LIST + PAGINATION ---------------- */

async function loadMolecules() {
  try {
    const res = await fetch(`/molecules?skip=${skip}&limit=${limit}`);
    const data = await res.json();

    total = data.total;

    renderTable(data.molecules);
    renderPagination(data.molecules.length);
  } catch (e) {
    setStatus("Ошибка загрузки списка", true);
  }
}

function renderTable(molecules) {
  const tbody = document.querySelector("#molecules-table tbody");
  tbody.innerHTML = "";

  if (!molecules || molecules.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="2">Молекулы не найдены</td>
      </tr>
    `;
    return;
  }

  molecules.forEach(m => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>
        <div><strong>ID:</strong> ${m.id}</div>
        <div style="font-size: 0.9em; color: #555;">
          название: ${m.id}
        </div>
      </td>
      <td>
        <div><strong>SMILES</strong></div>
        <code>${m.smiles}</code>
      </td>
    `;

    tbody.appendChild(row);
  });
}

function renderPagination(countOnPage) {
  const info = document.getElementById("page-info");
  const prevBtn = document.getElementById("prev");
  const nextBtn = document.getElementById("next");

  if (total === 0) {
    info.textContent = "Нет данных";
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    return;
  }

  const start = skip + 1;
  const end = Math.min(skip + countOnPage, total);

  info.textContent = `Показано ${start}–${end} из ${total}`;

  prevBtn.disabled = skip === 0;
  nextBtn.disabled = skip + limit >= total;
}

function nextPage() {
  if (skip + limit < total) {
    skip += limit;
    loadMolecules();
  }
}

function prevPage() {
  if (skip > 0) {
    skip -= limit;
    loadMolecules();
  }
}

/* ---------------- SEARCH ---------------- */

async function search() {
  const query = document.getElementById("search-query").value.trim();
  const list = document.getElementById("search-results");
  list.innerHTML = "";

  if (!query) {
    setStatus("Введите SMILES для поиска", true);
    return;
  }

  try {
    setStatus("Поиск молекулы...");
    const res = await fetch(
      `/molecules/by-smiles/${encodeURIComponent(query)}`
    );

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Молекула не найдена");

    list.innerHTML = `
      <li>
        <strong>ID:</strong> ${data.id}<br>
        <strong>SMILES:</strong> ${data.smiles}
      </li>
    `;

    setStatus("Молекула найдена ✅");
  } catch (e) {
    setStatus(e.message, true);
  }
}

/* ---------------- INIT ---------------- */

loadMolecules();
