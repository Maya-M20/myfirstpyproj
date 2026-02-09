var skip = 0;
var limit = 5;
var total = 0;

/* ---------- УНИВЕРСАЛЬНЫЙ СТАТУС ---------- */
function setStatus(id, text, isError) {
  var statusDiv = document.getElementById(id);
  statusDiv.textContent = text;
  statusDiv.style.color = isError ? "red" : "green";
}

/* ---------- ДОБАВЛЕНИЕ МОЛЕКУЛЫ ---------- */

function addMolecule() {
  const name = document.getElementById("mol-name").value.trim();
  const smiles = document.getElementById("mol-smiles").value.trim();

  if (!name || !smiles) {
    setStatus("status-add", "Введите название и SMILES", true);
    return;
  }

  setStatus("status-add", "Проверяю, есть ли такая молекула...");

  fetch(`/molecules/by-smiles/${encodeURIComponent(smiles)}`)
    .then(res => {
      if (res.status === 404) {
        return addNewMolecule(name, smiles);
      } else if (res.ok) {
        throw new Error("exists");
      } else {
        throw new Error("check error");
      }
    })
    .catch(err => {
      if (err.message === "exists") {
        setStatus("status-add", "Молекула уже есть в базе данных", true);
      } else {
        setStatus("status-add", "Ошибка при проверке молекулы", true);
      }
    });
}

function addNewMolecule(name, smiles) {
  setStatus("status-add", "Добавляю молекулу...");

  fetch("/molecules", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      id: name,
      smiles: smiles
    })
  })
    .then(res => {
      if (!res.ok) {
        return res.json().then(err => {
          throw new Error(err.detail || "Ошибка добавления");
        });
      }
      return res.json();
    })
    .then(() => {
      setStatus("status-add", "Молекула успешно добавлена");

      document.getElementById("mol-name").value = "";
      document.getElementById("mol-smiles").value = "";

      skip = 0;
      loadMolecules();
    })
    .catch(err => {
      setStatus("status-add", "Ошибка: " + err.message, true);
    });
}

/* ---------- ЗАГРУЗКА СПИСКА ---------- */

function loadMolecules() {
  fetch("/molecules?skip=" + skip + "&limit=" + limit)
    .then(response => response.json())
    .then(data => {
      total = data.total;
      renderTable(data.molecules);
      renderPagination(data.molecules.length);
    })
    .catch(() => {
      console.error("Ошибка загрузки списка");
    });
}

function renderTable(molecules) {
  var tbody = document.querySelector("#molecules-table tbody");
  tbody.innerHTML = "";

  if (!molecules || molecules.length === 0) {
    var row = document.createElement("tr");
    row.innerHTML = "<td colspan='2'>Молекул нет</td>";
    tbody.appendChild(row);
    return;
  }

  molecules.forEach(function(m) {
    var row = document.createElement("tr");
    row.innerHTML =
      "<td>" + m.id + "</td>" +
      "<td>" + m.smiles + "</td>";
    tbody.appendChild(row);
  });
}

/* ---------- ПАГИНАЦИЯ ---------- */

function renderPagination(countOnPage) {
  var info = document.getElementById("page-info");
  var prevBtn = document.getElementById("prev");
  var nextBtn = document.getElementById("next");

  if (total === 0) {
    info.textContent = "Нет данных";
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    return;
  }

  var start = skip + 1;
  var end = Math.min(skip + countOnPage, total);

  info.textContent = "Показано " + start + "–" + end + " из " + total;

  prevBtn.disabled = (skip === 0);
  nextBtn.disabled = (skip + limit >= total);
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

/* ---------- ПОИСК ---------- */

function search() {
  var query = document.getElementById("search-query").value;
  var results = document.getElementById("search-results");

  results.innerHTML = "";

  if (query === "") {
    setStatus("status-search", "Введите SMILES для поиска", true);
    return;
  }

  setStatus("status-search", "Ищу молекулу...");

  fetch("/molecules/by-smiles/" + encodeURIComponent(query))
    .then(response => {
      if (!response.ok) {
        throw new Error("not found");
      }
      return response.json();
    })
    .then(data => {
      var li = document.createElement("li");
      li.textContent = "ID: " + data.id + " | SMILES: " + data.smiles;
      results.appendChild(li);

      setStatus("status-search", "Молекула найдена");
    })
    .catch(() => {
      setStatus("status-search", "Молекула не найдена", true);
    });
}

/* ---------- УДАЛЕНИЕ ---------- */

function deleteMoleculeByInput() {
  var value = document.getElementById("delete-input").value.trim();

  if (value === "") {
    setStatus("status-delete", "Введите название или SMILES", true);
    return;
  }

  setStatus("status-delete", "Ищу молекулу для удаления...");

  fetch("/molecules/by-smiles/" + encodeURIComponent(value))
    .then(response => {
      if (response.ok) {
        return response.json();
      }
      return { id: value };
    })
    .then(data => {
      var moleculeId = data.id;

      setStatus("status-delete", "Удаляю молекулу " + moleculeId + "...");

      return fetch("/molecules/" + encodeURIComponent(moleculeId), {
        method: "DELETE"
      });
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => {
          throw new Error(err.detail || "Ошибка удаления");
        });
      }
      return response.json();
    })
    .then(() => {
      setStatus("status-delete", "Молекула успешно удалена");
      document.getElementById("delete-input").value = "";

      skip = 0;
      loadMolecules();
    })
    .catch(err => {
      setStatus("status-delete", "Ошибка: " + err.message, true);
    });
}

/* ---------- ЗАПУСК ---------- */

loadMolecules();
