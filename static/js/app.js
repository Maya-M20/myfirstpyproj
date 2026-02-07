function setStatus(text) {
  var statusDiv = document.getElementById("status");
  statusDiv.textContent = text;
}

function search() {
  var query = document.getElementById("search-query").value;
  var results = document.getElementById("search-results");

  results.innerHTML = "";

  if (query === "") {
    setStatus("Введите SMILES для поиска");
    return;
  }

  setStatus("Ищу молекулу...");

  fetch("/molecules/by-smiles/" + query)
    .then(function(response) {
      return response.json();
    })
    .then(function(data) {
      var li = document.createElement("li");
      li.textContent = "ID: " + data.id + " | SMILES: " + data.smiles;
      results.appendChild(li);

      setStatus("Молекула найдена");
    })
    .catch(function() {
      setStatus("Молекула не найдена");
    });
}
