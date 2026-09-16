/* =========================================================================
   CherryStraw Bookmark -- front end

   No build step and no framework, on purpose: the whole thing is three static
   files FastAPI serves directly, which is what keeps hosting free and makes
   the service worker trivial.
   ========================================================================= */

/* ---------------------------------------------------------------- helpers */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/** Escape anything that came from the network before it touches innerHTML. */
const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, options = {}) {
  // Only JSON string bodies get the header. FormData must set its own
  // multipart boundary, which it cannot do if we override Content-Type.
  const isJson = typeof options.body === "string";
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(isJson ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    showLogin();
    throw new ApiError("Please sign in again.", 401);
  }

  if (!response.ok) {
    let detail = `Something went wrong (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail[0]?.msg ?? detail;
    } catch { /* keep the generic message */ }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

function toast(message, kind = "") {
  const node = document.createElement("div");
  node.className = `toast ${kind === "error" ? "toast--error" : ""}`;
  node.textContent = message;
  $("#toastRoot").append(node);
  setTimeout(() => {
    node.style.transition = "opacity 300ms";
    node.style.opacity = "0";
    setTimeout(() => node.remove(), 320);
  }, 2600);
}

const stars = (rating) => {
  if (!rating) return `<span class="stars stars--empty">Not rated</span>`;
  const full = Math.floor(rating);
  const half = rating % 1 >= 0.5;
  return `<span class="stars">${"\u2605".repeat(full)}${half ? "\u00BD" : ""}</span>`;
};

/* ------------------------------------------------------------------ state */

const state = {
  view: "library",
  books: [],
  total: 0,
  categories: [],
  tags: [],
  branding: { brand: "CherryStraw", dedication: "", title: "Bookmark" },
  prefs: {},
  filters: { q: "", tagIds: [], sort: "recent", view: "grid" },
};

const tagById = (id) => state.tags.find((t) => t.id === id);

/* ------------------------------------------------------------ transition */

function showTransition() {
  const transition = $("#transition");
  transition.hidden = false;

  return new Promise((resolve) => {
    // Wait for the beautiful shark animation + text to stay visible for 5 seconds,
    // then fade out and resolve
    setTimeout(() => {
      transition.classList.add("is-leaving");
      setTimeout(() => { transition.hidden = true; resolve(); }, 500);
    }, 5500);
  });
}

/* ------------------------------------------------------------------- auth */

function showLogin() {
  $("#app").hidden = true;
  $("#login").hidden = false;
  $("#transition").hidden = true;
}

async function attemptLogin() {
  const username = $("#loginUser").value.trim();
  const password = $("#loginPass").value;
  const error = $("#loginError");
  error.hidden = true;

  if (!username || !password) {
    error.textContent = "Both fields, please.";
    error.hidden = false;
    return;
  }

  try {
    await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    $("#loginPass").value = "";
    $("#login").hidden = true;
    // Show the shark transition animation before loading the app
    await showTransition();
    await boot();
  } catch (err) {
    error.textContent = err.message;
    error.hidden = false;
  }
}

/* ------------------------------------------------------------------ views */

const TITLES = {
  library: "Library", add: "Add a book", tags: "Tags",
  stats: "Reading", settings: "Settings",
};

function switchView(name) {
  state.view = name;
  $$(".view").forEach((v) => { v.hidden = v.id !== `view-${name}`; });
  $$(".tab").forEach((t) => t.classList.toggle("is-on", t.dataset.view === name));
  $("#viewTitle").textContent = TITLES[name] ?? name;
  window.scrollTo({ top: 0 });

  if (name === "library") loadBooks();
  if (name === "tags") renderTags();
  if (name === "stats") loadStats();
}

/* --------------------------------------------------------------- library */

function bookCard(book) {
  const cover = book.cover_url
    ? `<img class="book__cover" src="${esc(book.cover_url)}" alt="" loading="lazy">`
    : `<div class="book__cover"></div>`;

  const tags = book.tags
    .map((t) => `<span class="book__tag" style="color:${esc(t.color)};
       background:color-mix(in srgb, ${esc(t.color)} 17%, transparent)">
       ${esc(t.name)}</span>`)
    .join("");

  const showProgress = book.progress_percent > 0 && book.progress_percent < 100;

  return `
    <article class="book" data-id="${book.id}">
      ${cover}
      <div class="book__body">
        <h3 class="book__title">${esc(book.title)}</h3>
        <p class="book__author">${esc(book.authors || "Unknown author")}</p>
        ${stars(book.rating)}
        ${showProgress ? `<div class="progress"><div class="progress__fill"
            style="width:${book.progress_percent}%"></div></div>` : ""}
        <div class="book__tags">${tags}</div>
      </div>
    </article>`;
}

const EMPTY_WAVE = `<svg class="empty__wave" viewBox="0 0 100 34" aria-hidden="true">
  <path d="M2 12c8-9 16-9 24 0s16 9 24 0 16-9 24 0 16 9 24 0"/>
  <path d="M2 26c8-8 16-8 24 0s16 8 24 0 16-8 24 0 16 8 24 0" opacity=".45"/>
</svg>`;

async function loadBooks() {
  const params = new URLSearchParams();
  if (state.filters.q) params.set("q", state.filters.q);
  params.set("sort", state.filters.sort);
  params.set("limit", "200");
  state.filters.tagIds.forEach((id) => params.append("tag_ids", id));

  try {
    const page = await api(`/api/books?${params}`);
    state.books = page.items;
    state.total = page.total;
  } catch (err) {
    if (err.status !== 401) toast(err.message, "error");
    return;
  }

  const container = $("#libBooks");
  container.className = `books books--${state.filters.view}`;
  $("#libCount").textContent = state.total
    ? `${state.total} book${state.total === 1 ? "" : "s"}`
    : "";

  if (!state.books.length) {
    const filtering = state.filters.q || state.filters.tagIds.length;
    container.className = "books";
    container.innerHTML = `<div class="empty">${EMPTY_WAVE}
      <h3>${filtering ? "Nothing matches that" : "Nothing on the shelves yet"}</h3>
      <p>${filtering
        ? "Try loosening the filters."
        : "Head to Add and search for the first one."}</p></div>`;
    return;
  }

  container.innerHTML = state.books.map(bookCard).join("");
  $$(".book", container).forEach((node) =>
    node.addEventListener("click", () => openBook(Number(node.dataset.id)))
  );
}

function renderFilters() {
  const chips = state.categories
    .map((cat) => {
      if (!cat.tags.length) return "";
      const inner = cat.tags
        .map((t) => {
          const on = state.filters.tagIds.includes(t.id);
          return `<button class="chip ${on ? "is-on" : ""}" data-tag="${t.id}"
                    style="--chip:${esc(t.color)}">
                    <span class="chip__dot"></span>${esc(t.name)}
                    <span class="chip__count">${t.book_count}</span></button>`;
        })
        .join("");
      return `<div style="margin-bottom:9px">
          <div class="muted" style="margin-bottom:5px;font-size:.72rem;
               text-transform:uppercase;letter-spacing:.07em">${esc(cat.name)}</div>
          <div class="row row--tight">${inner}</div></div>`;
    })
    .join("");

  const box = $("#libFilters");
  box.innerHTML = chips;
  $$("[data-tag]", box).forEach((node) =>
    node.addEventListener("click", () => {
      const id = Number(node.dataset.tag);
      const at = state.filters.tagIds.indexOf(id);
      if (at === -1) state.filters.tagIds.push(id);
      else state.filters.tagIds.splice(at, 1);
      renderFilters();
      loadBooks();
    })
  );
}

/* ----------------------------------------------------------------- modals */

function closeModal() {
  $("#modalRoot").innerHTML = "";
  document.body.style.overflow = "";
}

function openModal(html) {
  document.body.style.overflow = "hidden";
  $("#modalRoot").innerHTML = `
    <div class="modal" id="modalBackdrop">
      <div class="modal__panel" role="dialog" aria-modal="true">
        <div class="modal__grab"></div>
        ${html}
      </div>
    </div>`;
  $("#modalBackdrop").addEventListener("click", (event) => {
    if (event.target.id === "modalBackdrop") closeModal();
  });
  return $("#modalRoot .modal__panel");
}

/** The tag picker used by both the book editor and the add flow. */
function tagPickerHtml(selectedIds) {
  return state.categories
    .map((cat) => {
      if (!cat.tags.length) return "";
      const chips = cat.tags
        .map((t) => {
          const on = selectedIds.includes(t.id);
          return `<button type="button" class="chip ${on ? "is-on" : ""}"
                    data-pick="${t.id}" data-cat="${cat.id}"
                    data-exclusive="${cat.exclusive}"
                    style="--chip:${esc(t.color)}">
                    <span class="chip__dot"></span>${esc(t.name)}</button>`;
        })
        .join("");
      return `<div style="margin-bottom:11px">
        <div class="muted" style="font-size:.72rem;text-transform:uppercase;
             letter-spacing:.07em;margin-bottom:5px">${esc(cat.name)}${
               cat.exclusive ? " &middot; one only" : ""}</div>
        <div class="row row--tight">${chips}</div></div>`;
    })
    .join("");
}

/** Wire a tag picker so exclusive categories behave like radio buttons. */
function bindTagPicker(root) {
  $$("[data-pick]", root).forEach((node) =>
    node.addEventListener("click", () => {
      const exclusive = node.dataset.exclusive === "true";
      if (exclusive && !node.classList.contains("is-on")) {
        $$(`[data-cat="${node.dataset.cat}"]`, root).forEach((sib) =>
          sib.classList.remove("is-on")
        );
      }
      node.classList.toggle("is-on");
    })
  );
}

const pickedTagIds = (root) =>
  $$("[data-pick].is-on", root).map((n) => Number(n.dataset.pick));

/* ------------------------------------------------------------- book modal */

async function openBook(id) {
  let book;
  try {
    book = await api(`/api/books/${id}`);
  } catch (err) {
    return toast(err.message, "error");
  }

  const selected = book.tags.map((t) => t.id);
  const panel = openModal(`
    <div class="row" style="align-items:flex-start;margin-bottom:16px">
      ${book.cover_url
        ? `<img class="book__cover" style="width:84px" src="${esc(book.cover_url)}" alt="">`
        : `<div class="book__cover" style="width:84px"></div>`}
      <div class="grow">
        <h2 style="font-family:var(--font-display);margin:0 0 3px;font-size:1.25rem">
          ${esc(book.title)}</h2>
        <p class="muted" style="margin:0">${esc(book.authors || "Unknown author")}</p>
        <p class="muted" style="margin:6px 0 0;font-size:.78rem">
          ${[book.published_year, book.publisher, book.page_count && `${book.page_count} pp.`]
            .filter(Boolean).map(esc).join(" &middot; ")}</p>
      </div>
    </div>

    <label class="field"><span>Rating</span>
      <select id="bkRating">
        <option value="">Not rated</option>
        ${[5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5].map((v) =>
          `<option value="${v}" ${book.rating === v ? "selected" : ""}>
             ${"\u2605".repeat(Math.floor(v))}${v % 1 ? "\u00BD" : ""} &nbsp;${v}</option>`
        ).join("")}
      </select>
    </label>

    <div class="grid-2">
      <label class="field"><span>Page reached</span>
        <input type="number" id="bkPage" min="0" inputmode="numeric"
               value="${book.current_page || 0}"></label>
      <label class="field"><span>Total pages</span>
        <input type="number" id="bkPages" min="0" inputmode="numeric"
               value="${book.page_count ?? ""}"></label>
      <label class="field"><span>Started</span>
        <input type="date" id="bkStarted" value="${book.date_started ?? ""}"></label>
      <label class="field"><span>Finished</span>
        <input type="date" id="bkFinished" value="${book.date_finished ?? ""}"></label>
    </div>

    <label class="field"><span>Notes</span>
      <textarea id="bkNotes" placeholder="What stayed with you?">${esc(book.notes ?? "")}</textarea>
    </label>

    <div class="field"><span>Tags</span>${tagPickerHtml(selected)}</div>

    <div class="row" style="margin-top:8px">
      <button class="btn btn--primary grow" id="bkSave">Save</button>
      <button class="btn btn--ghost" id="bkCancel">Close</button>
    </div>
    <button class="btn btn--danger btn--block" id="bkDelete"
            style="margin-top:10px">Remove from library</button>
  `);

  bindTagPicker(panel);
  $("#bkCancel").addEventListener("click", closeModal);

  $("#bkSave").addEventListener("click", async () => {
    const ratingRaw = $("#bkRating").value;
    const pagesRaw = $("#bkPages").value;
    const payload = {
      rating: ratingRaw === "" ? null : Number(ratingRaw),
      current_page: Number($("#bkPage").value || 0),
      page_count: pagesRaw === "" ? null : Number(pagesRaw),
      date_started: $("#bkStarted").value || null,
      date_finished: $("#bkFinished").value || null,
      notes: $("#bkNotes").value.trim() || null,
      tag_ids: pickedTagIds(panel),
    };
    try {
      await api(`/api/books/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      closeModal();
      toast("Saved.");
      await refreshTags();
      await loadBooks();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#bkDelete").addEventListener("click", async () => {
    if (!confirm(`Remove "${book.title}" from your library?`)) return;
    try {
      await api(`/api/books/${id}`, { method: "DELETE" });
      closeModal();
      toast("Removed.");
      await refreshTags();
      await loadBooks();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

/* --------------------------------------------------------------- add flow */

function candidateCard(candidate, index, isBest) {
  const confidence = Math.round(candidate.match_score * 100);
  return `
    <article class="candidate ${isBest ? "candidate--best" : ""}">
      ${candidate.cover_url
        ? `<img class="book__cover" src="${esc(candidate.cover_url)}" alt="" loading="lazy">`
        : `<div class="book__cover"></div>`}
      <div class="book__body">
        ${isBest ? `<div class="candidate__score">Closest match &middot; ${confidence}% sure</div>` : ""}
        <h3 class="book__title">${esc(candidate.title)}</h3>
        <p class="book__author">${esc(candidate.authors || "Unknown author")}</p>
        <p class="muted" style="font-size:.76rem;margin:0 0 9px">
          ${[candidate.published_year, candidate.publisher,
             candidate.page_count && `${candidate.page_count} pp.`]
            .filter(Boolean).map(esc).join(" &middot; ")}</p>
        <button class="btn btn--sm btn--primary" data-confirm="${index}">
          ${isBest ? "Yes, that's the one" : "Add this one"}</button>
      </div>
    </article>`;
}

let lastCandidates = [];

function renderResults(results) {
  const box = $("#addResults");
  lastCandidates = results.candidates;

  if (!results.candidates.length) {
    box.innerHTML = `<div class="empty">${EMPTY_WAVE}
      <h3>No luck</h3><p>${esc(results.message || "Try different words.")}</p>
      <button class="btn" id="fallbackManual" style="margin-top:14px">
        Add it by hand instead</button></div>`;
    $("#fallbackManual")?.addEventListener("click", () => openManualForm());
    return;
  }

  const note = results.message
    ? `<p class="muted" style="margin:0 0 12px">${esc(results.message)}</p>`
    : "";

  box.innerHTML = `
    ${note}
    <p class="muted" style="margin:0 0 12px">
      ${results.total_found.toLocaleString()} found. Showing the closest
      ${results.candidates.length}.</p>
    ${results.candidates.map((c, i) => candidateCard(c, i, i === 0)).join("")}
    <button class="btn btn--block" id="fallbackManual" style="margin-top:6px">
      None of these &mdash; add by hand</button>`;

  $$("[data-confirm]", box).forEach((node) =>
    node.addEventListener("click", () =>
      confirmCandidate(lastCandidates[Number(node.dataset.confirm)])
    )
  );
  $("#fallbackManual").addEventListener("click", () => openManualForm());
}

/** Last step before a search hit becomes a book: pick its shelves. */
function confirmCandidate(candidate) {
  const wishlist = state.tags.find((t) => t.role === "wishlist");
  const panel = openModal(`
    <h2 style="font-family:var(--font-display);margin:0 0 4px;font-size:1.2rem">
      ${esc(candidate.title)}</h2>
    <p class="muted" style="margin:0 0 18px">${esc(candidate.authors || "Unknown author")}</p>
    <div class="field"><span>Put it on</span>
      ${tagPickerHtml(wishlist ? [wishlist.id] : [])}</div>
    <div class="row">
      <button class="btn btn--primary grow" id="cfSave">Add to library</button>
      <button class="btn btn--ghost" id="cfCancel">Cancel</button>
    </div>`);

  bindTagPicker(panel);
  $("#cfCancel").addEventListener("click", closeModal);

  $("#cfSave").addEventListener("click", async () => {
    const params = new URLSearchParams();
    pickedTagIds(panel).forEach((id) => params.append("tag_ids", id));
    try {
      await api(`/api/search/confirm?${params}`, {
        method: "POST",
        body: JSON.stringify(candidate),
      });
      closeModal();
      toast(`"${candidate.title}" is on the shelf.`);
      await refreshTags();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

function openManualForm() {
  const panel = openModal(`
    <h2 style="font-family:var(--font-display);margin:0 0 14px;font-size:1.2rem">
      Add by hand</h2>
    <label class="field"><span>Title *</span><input type="text" id="mnTitle"></label>
    <label class="field"><span>Author</span><input type="text" id="mnAuthors"></label>
    <div class="grid-2">
      <label class="field"><span>Year</span><input type="number" id="mnYear" inputmode="numeric"></label>
      <label class="field"><span>Pages</span><input type="number" id="mnPages" inputmode="numeric"></label>
      <label class="field"><span>Publisher</span><input type="text" id="mnPublisher"></label>
      <label class="field"><span>Series</span><input type="text" id="mnSeries"></label>
    </div>
    <label class="field"><span>Cover image URL</span><input type="url" id="mnCover"></label>
    <div class="field"><span>Tags</span>${tagPickerHtml([])}</div>
    <div class="row">
      <button class="btn btn--primary grow" id="mnSave">Add to library</button>
      <button class="btn btn--ghost" id="mnCancel">Cancel</button>
    </div>`);

  bindTagPicker(panel);
  $("#mnCancel").addEventListener("click", closeModal);

  $("#mnSave").addEventListener("click", async () => {
    const title = $("#mnTitle").value.trim();
    if (!title) return toast("A title, at least.", "error");
    const payload = {
      title,
      authors: $("#mnAuthors").value.trim() || null,
      published_year: Number($("#mnYear").value) || null,
      page_count: Number($("#mnPages").value) || null,
      publisher: $("#mnPublisher").value.trim() || null,
      series: $("#mnSeries").value.trim() || null,
      cover_url: $("#mnCover").value.trim() || null,
      source: "manual",
      tag_ids: pickedTagIds(panel),
    };
    try {
      await api("/api/books", { method: "POST", body: JSON.stringify(payload) });
      closeModal();
      toast(`"${title}" is on the shelf.`);
      await refreshTags();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

async function runQuickSearch() {
  const q = $("#addQuery").value.trim();
  if (!q) return toast("Type something first.", "error");
  $("#addResults").innerHTML = `<p class="muted"><span class="spinner"></span>
    Looking through Open Library...</p>`;
  try {
    renderResults(await api(`/api/search/quick?q=${encodeURIComponent(q)}`));
  } catch (err) {
    toast(err.message, "error");
    $("#addResults").innerHTML = "";
  }
}

async function runAdvancedSearch() {
  const body = {
    title: $("#advTitle").value.trim() || null,
    author: $("#advAuthor").value.trim() || null,
    subject: $("#advSubject").value.trim() || null,
    publisher: $("#advPublisher").value.trim() || null,
    isbn: $("#advIsbn").value.trim() || null,
    language: $("#advLanguage").value || null,
    year_from: Number($("#advYearFrom").value) || null,
    year_to: Number($("#advYearTo").value) || null,
    limit: 20,
  };
  $("#addResults").innerHTML = `<p class="muted"><span class="spinner"></span>
    Searching...</p>`;
  try {
    renderResults(await api("/api/search/advanced", {
      method: "POST", body: JSON.stringify(body),
    }));
  } catch (err) {
    toast(err.message, "error");
    $("#addResults").innerHTML = "";
  }
}

/* ------------------------------------------------------------------- tags */

function renderTags() {
  $("#tagList").innerHTML = state.categories
    .map((cat) => `
      <section class="category">
        <div class="category__head">
          <h3 class="category__name">${esc(cat.name)}</h3>
          ${cat.exclusive ? `<span class="category__badge">one only</span>` : ""}
          <span class="grow"></span>
          <button class="btn btn--sm btn--ghost" data-editcat="${cat.id}">Edit</button>
        </div>
        ${cat.description ? `<p class="category__desc">${esc(cat.description)}</p>` : ""}
        <div class="category__tags">
          ${cat.tags.map((t) => `
            <button class="chip" data-edittag="${t.id}" style="--chip:${esc(t.color)}">
              <span class="chip__dot"></span>${esc(t.name)}
              <span class="chip__count">${t.book_count}</span></button>`).join("")
            || `<span class="muted">No tags here yet.</span>`}
        </div>
      </section>`)
    .join("");

  $$("[data-edittag]").forEach((n) =>
    n.addEventListener("click", () => editTag(tagById(Number(n.dataset.edittag))))
  );
  $$("[data-editcat]").forEach((n) =>
    n.addEventListener("click", () =>
      editCategory(state.categories.find((c) => c.id === Number(n.dataset.editcat)))
    )
  );
}

const RAINBOW = ["#ff5c6b", "#ff9f45", "#ffd93d", "#5cd68a",
                 "#4ea8ff", "#7b7bff", "#b96bff"];

function editTag(tag) {
  const isNew = !tag;
  const current = tag ?? { name: "", color: RAINBOW[6], category_id: state.categories[0]?.id };

  const panel = openModal(`
    <h2 style="font-family:var(--font-display);margin:0 0 14px;font-size:1.2rem">
      ${isNew ? "New tag" : "Edit tag"}</h2>
    <label class="field"><span>Name</span>
      <input type="text" id="tgName" value="${esc(current.name)}"></label>
    <label class="field"><span>Category</span>
      <select id="tgCat">${state.categories.map((c) =>
        `<option value="${c.id}" ${c.id === current.category_id ? "selected" : ""}>
           ${esc(c.name)}</option>`).join("")}</select></label>
    <div class="field"><span>Colour</span>
      <div class="row row--tight">
        <input type="color" id="tgColor" value="${esc(current.color)}">
        ${RAINBOW.map((c) => `<button type="button" class="chip" data-swatch="${c}"
            style="--chip:${c};width:30px;padding:5px 0;justify-content:center">
            <span class="chip__dot"></span></button>`).join("")}
      </div>
    </div>
    ${!isNew && tag.is_preset
      ? `<p class="muted">This is one of the seven presets. Renaming and
         recolouring it is fine &mdash; deleting it removes that tag from every
         book that carries it.</p>` : ""}
    <div class="row" style="margin-top:12px">
      <button class="btn btn--primary grow" id="tgSave">Save</button>
      <button class="btn btn--ghost" id="tgCancel">Cancel</button>
    </div>
    ${isNew ? "" : `<button class="btn btn--danger btn--block" id="tgDelete"
        style="margin-top:10px">Delete tag</button>`}`);

  $$("[data-swatch]", panel).forEach((n) =>
    n.addEventListener("click", () => { $("#tgColor").value = n.dataset.swatch; })
  );
  $("#tgCancel").addEventListener("click", closeModal);

  $("#tgSave").addEventListener("click", async () => {
    const payload = {
      name: $("#tgName").value.trim(),
      color: $("#tgColor").value,
      category_id: Number($("#tgCat").value),
    };
    if (!payload.name) return toast("Give it a name.", "error");
    try {
      if (isNew) await api("/api/tags", { method: "POST", body: JSON.stringify(payload) });
      else await api(`/api/tags/${tag.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      closeModal();
      await refreshTags();
      renderTags();
      toast("Saved.");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#tgDelete")?.addEventListener("click", async () => {
    if (!confirm(`Delete "${tag.name}"? It comes off every book that has it.`)) return;
    try {
      await api(`/api/tags/${tag.id}`, { method: "DELETE" });
      closeModal();
      await refreshTags();
      renderTags();
      toast("Deleted.");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

function editCategory(cat) {
  const isNew = !cat;
  const current = cat ?? { name: "", description: "", exclusive: false };

  openModal(`
    <h2 style="font-family:var(--font-display);margin:0 0 14px;font-size:1.2rem">
      ${isNew ? "New category" : "Edit category"}</h2>
    <label class="field"><span>Name</span>
      <input type="text" id="ctName" value="${esc(current.name)}"></label>
    <label class="field"><span>Description</span>
      <input type="text" id="ctDesc" value="${esc(current.description ?? "")}"></label>
    <label class="row" style="gap:9px;margin-bottom:6px">
      <input type="checkbox" id="ctExcl" style="width:auto" ${current.exclusive ? "checked" : ""}>
      <span>One tag per book from this group</span>
    </label>
    <p class="muted">Turn this on for things a book can only be one of at a
      time, like a reading status. Leave it off for genres and moods.</p>
    <div class="row" style="margin-top:12px">
      <button class="btn btn--primary grow" id="ctSave">Save</button>
      <button class="btn btn--ghost" id="ctCancel">Cancel</button>
    </div>
    ${isNew ? "" : `<button class="btn btn--danger btn--block" id="ctDelete"
        style="margin-top:10px">Delete category and its tags</button>`}`);

  $("#ctCancel").addEventListener("click", closeModal);

  $("#ctSave").addEventListener("click", async () => {
    const payload = {
      name: $("#ctName").value.trim(),
      description: $("#ctDesc").value.trim() || null,
      exclusive: $("#ctExcl").checked,
    };
    if (!payload.name) return toast("Give it a name.", "error");
    try {
      if (isNew) await api("/api/categories", { method: "POST", body: JSON.stringify(payload) });
      else await api(`/api/categories/${cat.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      closeModal();
      await refreshTags();
      renderTags();
      toast("Saved.");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#ctDelete")?.addEventListener("click", async () => {
    if (!confirm(`Delete "${cat.name}" and all ${cat.tags.length} tags inside it?`)) return;
    try {
      await api(`/api/categories/${cat.id}`, { method: "DELETE" });
      closeModal();
      await refreshTags();
      renderTags();
      toast("Deleted.");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

/* ------------------------------------------------------------------ stats */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

async function loadStats() {
  let s;
  try {
    s = await api("/api/stats");
  } catch (err) {
    return toast(err.message, "error");
  }

  const peak = Math.max(1, ...s.monthly.map((m) => m.count));
  const goalPct = s.goal ? Math.min(s.goal.books_percent, 100) : 0;

  const goalBlock = s.goal
    ? `<div class="goal-ring">
         <div style="position:relative;width:78px;height:78px;flex:none">
           <svg viewBox="0 0 80 80" style="transform:rotate(-90deg)">
             <circle cx="40" cy="40" r="34" fill="none" stroke="var(--deep)" stroke-width="8"/>
             <circle cx="40" cy="40" r="34" fill="none" stroke="var(--ember)"
                     stroke-width="8" stroke-linecap="round"
                     stroke-dasharray="${(goalPct / 100) * 213.6} 213.6"/>
           </svg>
           <div style="position:absolute;inset:0;display:grid;place-items:center;
                font-variant-numeric:tabular-nums;font-weight:650">
             ${Math.round(goalPct)}%</div>
         </div>
         <div>
           <div style="font-family:var(--font-display);font-size:1.15rem">
             ${s.goal.books_finished} of ${s.goal.target_books} in ${s.year}</div>
           <p class="muted" style="margin:3px 0 9px">
             ${s.goal.pages_read.toLocaleString()} pages so far.</p>
           <button class="btn btn--sm" id="editGoal">Change goal</button>
         </div>
       </div>`
    : `<div class="goal-ring">
         <div class="grow">
           <div style="font-family:var(--font-display);font-size:1.1rem">
             No goal set for ${s.year}</div>
           <p class="muted" style="margin:3px 0 9px">
             A number to aim at, if you like having one.</p>
           <button class="btn btn--sm btn--primary" id="editGoal">Set a goal</button>
         </div>
       </div>`;

  $("#statsBody").innerHTML = `
    ${goalBlock}
    <div class="stat-grid">
      <div class="stat"><div class="stat__value">${s.total_books}</div>
        <div class="stat__label">On the shelves</div></div>
      <div class="stat"><div class="stat__value">${s.finished_all_time}</div>
        <div class="stat__label">Finished, ever</div></div>
      <div class="stat"><div class="stat__value">${s.currently_reading}</div>
        <div class="stat__label">Reading now</div></div>
      <div class="stat"><div class="stat__value">${s.pages_all_time.toLocaleString()}</div>
        <div class="stat__label">Pages read</div></div>
      <div class="stat"><div class="stat__value" style="color:var(--ember)">
        ${s.average_rating ?? "\u2014"}</div>
        <div class="stat__label">Average rating</div></div>
      <div class="stat"><div class="stat__value">${s.finished_this_year}</div>
        <div class="stat__label">Finished in ${s.year}</div></div>
    </div>

    <h3 class="section-title">${s.year} by month</h3>
    <div class="bars">
      ${s.monthly.map((m) => `
        <div class="bar">
          <span class="muted">${MONTHS[m.month - 1]}</span>
          <div class="bar__track"><div class="bar__fill"
               style="width:${(m.count / peak) * 100}%"></div></div>
          <span class="bar__n">${m.count || ""}</span>
        </div>`).join("")}
    </div>

    <h3 class="section-title">Most used tags</h3>
    <div class="bars">
      ${s.by_tag.filter((t) => t.count > 0).slice(0, 10).map((t) => {
        const top = Math.max(1, s.by_tag[0]?.count ?? 1);
        return `<div class="bar">
          <span class="muted" style="white-space:nowrap;overflow:hidden;
                text-overflow:ellipsis">${esc(t.name)}</span>
          <div class="bar__track"><div class="bar__fill"
               style="width:${(t.count / top) * 100}%;background:${esc(t.color)}"></div></div>
          <span class="bar__n">${t.count}</span></div>`;
      }).join("") || `<p class="muted">Tag a few books and this fills in.</p>`}
    </div>

    ${s.longest_book ? `<p class="muted" style="margin-top:22px">
      Longest on the shelves: <strong>${esc(s.longest_book)}</strong>.</p>` : ""}`;

  $("#editGoal").addEventListener("click", () => editGoal(s.year, s.goal));
}

function editGoal(year, goal) {
  openModal(`
    <h2 style="font-family:var(--font-display);margin:0 0 14px;font-size:1.2rem">
      Goal for ${year}</h2>
    <div class="grid-2">
      <label class="field"><span>Books</span>
        <input type="number" id="glBooks" min="0" inputmode="numeric"
               value="${goal?.target_books ?? 12}"></label>
      <label class="field"><span>Pages (optional)</span>
        <input type="number" id="glPages" min="0" inputmode="numeric"
               value="${goal?.target_pages ?? 0}"></label>
    </div>
    <div class="row">
      <button class="btn btn--primary grow" id="glSave">Save</button>
      <button class="btn btn--ghost" id="glCancel">Cancel</button>
    </div>`);

  $("#glCancel").addEventListener("click", closeModal);
  $("#glSave").addEventListener("click", async () => {
    try {
      await api("/api/goals", {
        method: "PUT",
        body: JSON.stringify({
          year,
          target_books: Number($("#glBooks").value || 0),
          target_pages: Number($("#glPages").value || 0),
        }),
      });
      closeModal();
      await loadStats();
      toast("Goal set.");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

/* --------------------------------------------------------------- settings */

function applyAccent(hex) {
  document.documentElement.style.setProperty("--flame", hex);
  document.documentElement.style.setProperty("--flame-glow", `${hex}66`);
  $("#accentPicker").value = hex;
}

async function savePref(key, value) {
  state.prefs[key] = value;
  try {
    await api(`/api/preferences/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify({ value: String(value) }),
    });
  } catch { /* a preference failing to save is not worth interrupting anyone */ }
}

function download(path) {
  // A plain navigation so the browser handles Content-Disposition itself.
  window.location.href = path;
}

/* ------------------------------------------------------------------- boot */

async function refreshTags() {
  try {
    state.categories = await api("/api/tags");
  } catch (err) {
    // If /api/tags fails, create a default structure
    state.categories = [
      {
        id: 1,
        name: "Status",
        exclusive: true,
        tags: []
      },
      {
        id: 2,
        name: "Shelf",
        exclusive: false,
        tags: []
      }
    ];
  }
  state.tags = state.categories.flatMap((c) => c.tags);
  if (state.view === "library") renderFilters();
}

async function boot() {
  const session = await api("/api/auth/session");
  if (!session.authenticated) return showLogin();

  $("#app").hidden = false;
  
  // Use defaults for branding
  state.branding = { brand: "Boocker", dedication: "", title: "Boocker" };
  state.prefs = {};

  $("#transitionBrand").textContent = state.branding.brand;
  $("#transitionDedication").textContent = state.branding.dedication;
  $("#settingsBrand").textContent =
    `${state.branding.brand}${state.branding.dedication ? ` \u00B7 ${state.branding.dedication}` : ""}`;

  // Set default preferences
  state.filters.view = "grid";
  state.filters.sort = "recent";
  $("#libSort").value = state.filters.sort;
  $("#libViewToggle").textContent = "Grid";

  await refreshTags();
  await loadBooks();
}

/* -------------------------------------------------------------- listeners */

function wire() {
  $$(".tab").forEach((tab) =>
    tab.addEventListener("click", () => switchView(tab.dataset.view))
  );

  $("#loginBtn").addEventListener("click", attemptLogin);
  $("#loginPass").addEventListener("keydown", (e) => {
    if (e.key === "Enter") attemptLogin();
  });
  let searchTimer;
  $("#libSearch").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.filters.q = e.target.value.trim();
      loadBooks();
    }, 280);
  });

  $("#libSort").addEventListener("change", (e) => {
    state.filters.sort = e.target.value;
    savePref("library.default_sort", e.target.value);
    loadBooks();
  });

  $("#libViewToggle").addEventListener("click", () => {
    state.filters.view = state.filters.view === "grid" ? "list" : "grid";
    $("#libViewToggle").textContent = state.filters.view === "grid" ? "Grid" : "List";
    savePref("library.default_view", state.filters.view);
    loadBooks();
  });

  $("#addSearchBtn").addEventListener("click", runQuickSearch);
  $("#advSearchBtn").addEventListener("click", runAdvancedSearch);
  $("#addManualBtn").addEventListener("click", () => openManualForm());
  $("#addQuery").addEventListener("keydown", (e) => {
    if (e.key === "Enter") runQuickSearch();
  });

  $("#newTagBtn").addEventListener("click", () => editTag(null));
  $("#newCategoryBtn").addEventListener("click", () => editCategory(null));

  $("#accentPicker").addEventListener("input", (e) => {
    applyAccent(e.target.value);
    savePref("theme.accent", e.target.value);
  });
  $$("[data-accent]").forEach((btn) =>
    btn.addEventListener("click", () => {
      applyAccent(btn.dataset.accent);
      savePref("theme.accent", btn.dataset.accent);
    })
  );

  $("#exportCsvBtn").addEventListener("click", () => download("/api/export/csv"));
  $("#exportJsonBtn").addEventListener("click", () => download("/api/export/json"));

  $("#importFile").addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const report = await api("/api/import/csv", { method: "POST", body: form });
      toast(`Added ${report.created}, skipped ${report.skipped}.`);
      if (report.errors.length) console.warn("Import notes:", report.errors);
      await refreshTags();
      await loadBooks();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      e.target.value = "";
    }
  });

  $("#changeUsernameBtn").addEventListener("click", async () => {
    const new_username = $("#pwUsername").value.trim();
    const current_password = $("#pwCurrentForUsername").value;
    if (!new_username) return toast("Enter a new username.", "error");
    if (new_username.length < 2) return toast("Username must be at least 2 characters.", "error");
    try {
      await api("/api/auth/username", {
        method: "POST",
        body: JSON.stringify({ current_password, new_username }),
      });
      $("#pwUsername").value = $("#pwCurrentForUsername").value = "";
      toast("Username changed.");
      // Optionally reload to update the session
      setTimeout(() => location.reload(), 500);
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#changePwBtn").addEventListener("click", async () => {
    const current_password = $("#pwCurrent").value;
    const new_password = $("#pwNew").value;
    if (new_password.length < 8) return toast("Eight characters or more.", "error");
    try {
      await api("/api/auth/password", {
        method: "POST",
        body: JSON.stringify({ current_password, new_password }),
      });
      $("#pwCurrent").value = $("#pwNew").value = "";
      toast("Password changed.");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  $("#logoutBtn").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    location.reload();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
}

wire();
boot().catch(() => showLogin());

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () =>
    navigator.serviceWorker.register("/sw.js").catch(() => {})
  );
}
