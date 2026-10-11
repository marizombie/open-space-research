"use strict";

(() => {
  const datasets = JSON.parse(document.getElementById("datasets").textContent);
  const byId = new Map(datasets.map(dataset => [dataset.id, dataset]));
  const element = id => document.getElementById(id);
  const controls = ["dataset", "search", "filter-field", "filter-value", "page-size", "all-columns"];
  const preferred = {
    failures: ["date", "name", "org_country", "root_cause_category", "did_fix_hold"],
    organizations: ["organization", "country_bloc", "flagship_vehicle", "orbital_launches_2025", "orbital_launches_2026_ytd"],
    spaceflight_milestones: ["num", "date", "milestone", "actor", "category"],
    tech_gaps: ["capability", "current_trl", "readiness_label", "evidence_2026"],
    funding: ["entity", "entity_type", "annual_budget_or_revenue_busd", "budget_year", "funding_source"],
    launch_costs: ["vehicle", "year", "leo_kg", "cost_per_kg_usd", "reuse"],
    cost_model: ["vehicle", "contract_type", "destination_orbit", "effective_usd_per_kg", "price_basis"]
  };
  // Readable column names come from build_site.py; the CSV column name is the fallback.
  const label = field => (current && current.labels && current.labels[field]) || field.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
  const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" });
  let current;
  let page = 0;
  let sortField = "";
  let descending = false;
  let filtered = [];

  function node(tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  }

  function option(value, text) {
    const result = node("option", text);
    result.value = value;
    return result;
  }

  function selectDataset() {
    current = byId.get(element("dataset").value);
    sortField = "";
    descending = false;
    page = 0;
    element("search").value = "";
    element("filter-field").replaceChildren(option("", "All fields"), ...current.columns.map(field => option(field, label(field))));
    element("dataset-description").textContent = current.description;
    if (element("dataset-page")) {
      element("dataset-page").href = current.url;
      element("dataset-page").setAttribute("aria-label", `Open ${current.label} dataset page`);
    }
    selectFilter();
  }

  function selectFilter() {
    const field = element("filter-field").value;
    const values = field ? [...new Set(current.rows.map(row => row[field]))].sort(collator.compare) : [];
    element("filter-value").replaceChildren(option("", "All values"), ...values.map(value => option(value || "__blank__", value || "(blank)")));
    element("filter-value").disabled = !field;
    page = 0;
    render();
  }

  function showRecord(row) {
    element("record-title").textContent = row.name || row.event_name || row.milestone || row.organization || row.vehicle || row.capability || row.record_id || current.label;
    const fields = element("record-fields");
    fields.replaceChildren();
    for (const field of current.columns) {
      fields.append(node("dt", label(field)), node("dd", row[field] || "—"));
    }
    element("record-dialog").showModal();
  }

  function render() {
    const query = element("search").value.trim().toLocaleLowerCase();
    const field = element("filter-field").value;
    const value = element("filter-value").value;
    filtered = current.rows.filter(row => (!query || current.columns.some(column => row[column].toLocaleLowerCase().includes(query))) && (!field || !value || row[field] === (value === "__blank__" ? "" : value)));
    if (sortField) {
      const numeric = filtered.some(row => row[sortField] !== "") && filtered.every(row => row[sortField] === "" || Number.isFinite(Number(row[sortField])));
      filtered.sort((a, b) => {
        const left = a[sortField], right = b[sortField];
        const compared = numeric && left !== "" && right !== "" ? Number(left) - Number(right) : collator.compare(left, right);
        return descending ? -compared : compared;
      });
    }
    const pageSize = element("page-size").value === "all" ? Math.max(1, filtered.length) : Number(element("page-size").value);
    const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
    page = Math.max(0, Math.min(page, pages - 1));
    const start = page * pageSize;
    const visible = filtered.slice(start, start + pageSize);
    const columns = element("all-columns").checked ? current.columns : preferred[current.id] || current.columns.slice(0, 6);
    const header = node("tr");
    for (const column of columns) {
      const th = node("th");
      th.scope = "col";
      if (sortField === column) th.setAttribute("aria-sort", descending ? "descending" : "ascending");
      const button = node("button", `${label(column)}${sortField === column ? (descending ? " ↓" : " ↑") : " ↕"}`, "sort-button");
      button.type = "button";
      button.addEventListener("click", () => {
        descending = sortField === column ? !descending : false;
        sortField = column;
        page = 0;
        render();
      });
      th.append(button);
      header.append(th);
    }
    const detailsHeader = node("th", "Details");
    detailsHeader.scope = "col";
    header.prepend(detailsHeader);
    element("data-table").querySelector("thead").replaceChildren(header);
    const rows = visible.map(row => {
      const tr = node("tr");
      for (const column of columns) tr.append(node("td", row[column] || "—"));
      const td = node("td");
      const button = node("button", "View record", "record-button");
      button.type = "button";
      button.addEventListener("click", () => showRecord(row));
      td.append(button);
      tr.prepend(td);
      return tr;
    });
    element("data-table").querySelector("tbody").replaceChildren(...rows);
    element("results-status").textContent = filtered.length ? `${start + 1}–${start + visible.length} of ${filtered.length} records · ${current.rows.length} total` : `0 matching records · ${current.rows.length} total`;
    element("empty-state").hidden = filtered.length > 0;
    element("page-status").textContent = `Page ${page + 1} of ${pages}`;
    element("previous-page").disabled = page === 0;
    element("next-page").disabled = page >= pages - 1;
    element("reset-sorting").disabled = !sortField;
  }

  element("dataset").addEventListener("change", selectDataset);
  element("filter-field").addEventListener("change", selectFilter);
  for (const id of controls.filter(id => !["dataset", "filter-field"].includes(id))) {
    element(id).addEventListener(id === "search" ? "input" : "change", () => { page = 0; render(); });
  }
  element("reset").addEventListener("click", () => {
    element("page-size").value = "25";
    element("all-columns").checked = datasets.length === 1;
    selectDataset();
  });
  element("reset-sorting").addEventListener("click", () => {
    sortField = "";
    descending = false;
    page = 0;
    render();
  });
  element("previous-page").addEventListener("click", () => { page--; render(); });
  element("next-page").addEventListener("click", () => { page++; render(); });
  element("close-record").addEventListener("click", () => element("record-dialog").close());
  element("record-dialog").addEventListener("click", event => {
    if (event.target === element("record-dialog")) {
      const bounds = event.target.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) event.target.close();
    }
  });
  selectDataset();
  element("explorer-controls").hidden = false;
})();
