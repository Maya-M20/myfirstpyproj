/* =========================================================
   CONFIG
========================================================= */

const API_BASE = ""; // nginx проксирует API в /


let currentPage = 0;
const limit = 5;


/* =========================================================
   HELPERS
========================================================= */

function showStatus(el, message, type = "success") {
    el.textContent = message;
    el.className = `status ${type}`;
}

function clearElement(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
}


/* =========================================================
   ADD MOLECULE
========================================================= */

document
    .getElementById("add-molecule-form")
    .addEventListener("submit", async (e) => {
        e.preventDefault();

        const id = document.getElementById("mol-id").value.trim();
        const smiles = document.getElementById("mol-smiles").value.trim();
        const statusEl = document.getElementById("add-status");

        if (!id || !smiles) {
            showStatus(statusEl, "Заполните все поля", "error");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/molecules`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id, smiles }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Ошибка добавления");
            }

            showStatus(statusEl, "Молекула успешно добавлена");
            document.getElementById("add-molecule-form").reset();
            loadMolecules();

        } catch (err) {
            showStatus(statusEl, err.message, "error");
        }
    });


/* =========================================================
   LOAD MOLECULES (PAGINATION)
========================================================= */

async function loadMolecules() {
    const listEl = document.getElementById("molecules-list");
    const pageInfo = document.getElementById("page-info");

    listEl.textContent = "Загрузка...";

    try {
        const skip = currentPage * limit;
        const res = await fetch(
            `${API_BASE}/molecules?skip=${skip}&limit=${limit}`
        );

        const data = await res.json();

        clearElement(listEl);

        if (!data.molecules || data.molecules.length === 0) {
            listEl.textContent = "Нет молекул";
            return;
        }

        data.molecules.forEach((m) => {
            const div = document.createElement("div");
            div.className = "molecule-item";
            div.textContent = `${m.id} | ${m.smiles}`;
            listEl.appendChild(div);
        });

        pageInfo.textContent = `Страница ${currentPage + 1}`;

    } catch (err) {
        listEl.textContent = "Ошибка загрузки списка";
    }
}

document.getElementById("prev-page").addEventListener("click", () => {
    if (currentPage > 0) {
        currentPage--;
        loadMolecules();
    }
});

document.getElementById("next-page").addEventListener("click", () => {
    currentPage++;
    loadMolecules();
});


/* =========================================================
   ASYNC SUBSTRUCTURE SEARCH (CELERY)
========================================================= */

document
    .getElementById("search-form")
    .addEventListener("submit", async (e) => {
        e.preventDefault();

        const input = document.getElementById("search-input");
        const statusEl = document.getElementById("search-status");
        const resultsList = document.getElementById("results-list");

        const substructure = input.value.trim();
        clearElement(resultsList);

        if (!substructure) {
            showStatus(statusEl, "Введите SMILES", "error");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/async/search`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    substructure,
                }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Ошибка запуска задачи");
            }

            showStatus(statusEl, "Задача запущена");
            pollTaskStatus(data.task_id);

        } catch (err) {
            showStatus(statusEl, err.message, "error");
        }
    });


/* =========================================================
   CELERY TASK POLLING
========================================================= */

function pollTaskStatus(taskId) {
    const statusEl = document.getElementById("search-status");
    const resultsList = document.getElementById("results-list");

    const intervalId = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/tasks/status/${taskId}`);
            const data = await res.json();

            let text = `Статус: ${data.status}`;

            if (data.progress !== undefined) {
                text += ` (${data.progress}%)`;
            }

            statusEl.textContent = text;

            if (data.status === "SUCCESS") {
                clearInterval(intervalId);
                showStatus(statusEl, "Поиск завершён");

                if (!data.molecules || data.molecules.length === 0) {
                    const li = document.createElement("li");
                    li.textContent = "Ничего не найдено";
                    resultsList.appendChild(li);
                    return;
                }

                data.molecules.forEach((m) => {
                    const li = document.createElement("li");
                    li.textContent = `${m.id} | ${m.smiles}`;
                    resultsList.appendChild(li);
                });
            }

            if (data.status === "FAILURE") {
                clearInterval(intervalId);
                showStatus(
                    statusEl,
                    data.error || "Ошибка выполнения задачи",
                    "error"
                );
            }

        } catch (err) {
            clearInterval(intervalId);
            showStatus(statusEl, "Ошибка соединения", "error");
        }
    }, 1000);
}


/* =========================================================
   INIT
========================================================= */

loadMolecules();
