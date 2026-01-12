const API_BASE = "";

let currentPage = 0;
const limit = 5;

/* ===============================
   Утилиты
================================ */
function showStatus(el, msg, type = "success") {
    el.textContent = msg;
    el.className = `status ${type}`;
}

/* ===============================
   Добавление молекулы
================================ */
document.getElementById("add-molecule-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("mol-id").value;
    const smiles = document.getElementById("mol-smiles").value;
    const statusEl = document.getElementById("add-status");

    try {
        const res = await fetch(`${API_BASE}/molecules`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, smiles })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        showStatus(statusEl, "Молекула добавлена");
        loadMolecules();
    } catch (err) {
        showStatus(statusEl, err.message, "error");
    }
});

/* ===============================
   Загрузка списка молекул
================================ */
async function loadMolecules() {
    const list = document.getElementById("molecules-list");
    const pageInfo = document.getElementById("page-info");

    list.innerHTML = "Загрузка...";

    const skip = currentPage * limit;
    const res = await fetch(`/molecules?skip=${skip}&limit=${limit}`);
    const data = await res.json();

    list.innerHTML = "";
    data.molecules.forEach(m => {
        const div = document.createElement("div");
        div.textContent = `${m.id} | ${m.smiles}`;
        list.appendChild(div);
    });

    pageInfo.textContent = `Страница ${currentPage + 1}`;
}

document.getElementById("prev-page").onclick = () => {
    if (currentPage > 0) {
        currentPage--;
        loadMolecules();
    }
};

document.getElementById("next-page").onclick = () => {
    currentPage++;
    loadMolecules();
};

/* ===============================
   Субструктурный поиск (async)
================================ */
document.getElementById("search-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const substructure = document.getElementById("substructure").value;
    const statusEl = document.getElementById("search-status");
    const resultsEl = document.getElementById("search-results");

    resultsEl.innerHTML = "";

    try {
        const res = await fetch("/async/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ substructure })
        });

        const data = await res.json();
        showStatus(statusEl, "Задача запущена");

        pollTaskStatus(data.task_id);
    } catch (err) {
        showStatus(statusEl, err.message, "error");
    }
});

/* ===============================
   Polling Celery статуса
================================ */
async function pollTaskStatus(taskId) {
    const statusEl = document.getElementById("search-status");
    const resultsEl = document.getElementById("search-results");

    const interval = setInterval(async () => {
        const res = await fetch(`/tasks/status/${taskId}`);
        const data = await res.json();

        statusEl.textContent = `Статус: ${data.status}`;

        if (data.progress !== undefined) {
            statusEl.textContent += ` (${data.progress}%)`;
        }

        if (data.status === "SUCCESS") {
            clearInterval(interval);
            showStatus(statusEl, "Поиск завершён");

            data.result?.molecules?.forEach(m => {
                const div = document.createElement("div");
                div.textContent = `${m.id} | ${m.smiles}`;
                resultsEl.appendChild(div);
            });
        }

        if (data.status === "FAILURE") {
            clearInterval(interval);
            showStatus(statusEl, data.error, "error");
        }
    }, 1000);
}

/* INIT */
loadMolecules();
