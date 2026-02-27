var skip = 0;
var limit = 2;
var total = 0;

function setStatus(id, text, isError) {
  var statusDiv = document.getElementById(id);

  if (statusDiv !== null) {
    statusDiv.textContent = text;

    if (isError === true) {
      statusDiv.style.color = "red";
    } else {
      statusDiv.style.color = "green";
    }
  }
}

function addNewMolecule(name, smiles) {
  fetch("/molecules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: name, smiles: smiles })
  })
    .then(res => {
      if (!res.ok) {
        return res.json().then(err => { throw new Error(err.detail || "Ошибка добавления"); });
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
    .catch(err => setStatus("status-add", "Ошибка: " + err.message, true));
}

function addMolecule() {
  const name = document.getElementById("mol-name").value.trim();
  const smiles = document.getElementById("mol-smiles").value.trim();

  if (!name || !smiles) {
    setStatus("status-add", "Введите название и SMILES", true);
    return;
  }

  fetch(`/molecules/by-smiles/${encodeURIComponent(smiles)}`)
    .then(res => {
      if (res.status === 404) {
        return addNewMolecule(name, smiles);
      } else if (res.ok) {
        setStatus("status-add", "Молекула уже есть в базе данных", true);
      } else {
        setStatus("status-add", "Ошибка при проверке молекулы", true);
      }
    });
}

function renderTable(molecules) {
  var tbody = document.querySelector("#molecules-table tbody");
  tbody.innerHTML = "";

  window.RDKitAsyncInit.then(function(RDKit) {
    molecules.forEach(function(m, index) {
      var row = document.createElement("tr");
      var viewerId = "viewer-" + index;

      row.innerHTML =
      "<td>" + m.id + "</td>" +
      "<td>" + m.smiles + "</td>" +
      "<td><div id='" + viewerId + "' class='mol-viewer'></div></td>";


      tbody.appendChild(row);

      try {
        const molObject = RDKit.get_mol(m.smiles);
        if (!molObject) throw new Error("Невалидный SMILES");

        const svg = molObject.get_svg();
        document.getElementById(viewerId).innerHTML = svg;

        molObject.delete();
      } catch (e) {
        console.error("Ошибка SMILES:", m.smiles, e);
        document.getElementById(viewerId).textContent = "Ошибка SMILES";
      }
    });
  }).catch(err => {
    console.error("Не удалось загрузить RDKit:", err);
  });
}


function loadMolecules() {
  fetch("/molecules?skip=" + skip + "&limit=" + limit)
    .then(response => response.json())
    .then(data => {
      total = data.total;
      renderTable(data.molecules);
      renderPagination(data.molecules.length);
    })
    .catch(() => console.error("Ошибка загрузки списка"));
}

function renderPagination(countOnPage) {
  var info = document.getElementById("page-info");
  var prevBtn = document.getElementById("prev");
  var nextBtn = document.getElementById("next");

  if (total === 0) {
    info.textContent = "Нет данных";
    if (prevBtn) prevBtn.disabled = true;
    if (nextBtn) nextBtn.disabled = true;
    return;
  }

  var start = skip + 1;
  var end = Math.min(skip + countOnPage, total);
  info.textContent = "Показано " + start + "–" + end + " из " + total;

  if (prevBtn) prevBtn.disabled = (skip === 0);
  if (nextBtn) nextBtn.disabled = (skip + limit >= total);
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

function search() {
  var query = document.getElementById("search-query").value;
  var results = document.getElementById("search-results");
  if (!results) return;

  results.innerHTML = "";
  if (query === "") {
    setStatus("status-search", "Введите SMILES для поиска", true);
    return;
  }

  fetch("/molecules/by-smiles/" + encodeURIComponent(query))
    .then(response => {
      if (!response.ok) throw new Error("not found");
      return response.json();
    })
    .then(data => {
      var li = document.createElement("li");
      li.textContent = "Молекула: " + data.id;
      results.appendChild(li);
      setStatus("status-search", "Молекула найдена");
      document.getElementById("search-query").value = "";
    })
    .catch(() => setStatus("status-search", "Молекула не найдена", true));
    document.getElementById("search-query").value = "";
}

function deleteMoleculeByInput() {
  var value = document.getElementById("delete-input").value.trim();
  if (value === "") {
    setStatus("status-delete", "Введите название или SMILES", true);
    return;
  }


  fetch("/molecules/by-smiles/" + encodeURIComponent(value))
    .then(response => response.ok ? response.json() : { id: value })
    .then(data => {
      var moleculeId = data.id;
      setStatus("status-delete", "Удаляю молекулу " + moleculeId + "...");
      return fetch("/molecules/" + encodeURIComponent(moleculeId), { method: "DELETE" });
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => { throw new Error(err.detail || "Ошибка удаления"); });
      }
      return response.json();
    })
    .then(() => {
      setStatus("status-delete", "Молекула успешно удалена");
      document.getElementById("delete-input").value = "";
      skip = 0;
      loadMolecules();
    })
    .catch(err => setStatus("status-delete", "Ошибка: " + err.message, true));
}

loadMolecules();
