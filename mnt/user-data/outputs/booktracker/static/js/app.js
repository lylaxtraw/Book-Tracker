/* ============================================================================
   Book Tracker — front end

   No framework, no build step. Open the folder in VS Code, run uvicorn, edit,
   refresh. Everything below is organised top to bottom: helpers, API, state,
   then one section per screen.
   ========================================================================== */

(() => {
"use strict";

const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const RAINBOW = ["#E5484D", "#F2801F", "#FFC65C", "#3DBE7C",
                 "#4A8FE7", "#6C7BE8", "#A472F0"];

/* ------------------------------------------------------------------ helpers */

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(child));
  }
  return node;
}

let toastTimer;
function toast(message, bad = false) {
  const box = $("#toast");
  box.textContent = message;
  box.classList.toggle("bad", bad);
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.hidden = true; }, 2800);
}

const debounce = (fn, ms = 260) => {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
};

const today = () => new Date().toISOString().slice(0, 10);

/* ---------------------------------------------------------------------- api */

async function api(path, { method = "GET", body, raw } = {}) {
  const options = { method, headers: {} };
  if (body !== undefined && !raw) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  } else if (raw) {
    options.body = raw;
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("No connection. Check your network and try again.");
  }

  if (response.status === 401) { showLock(); throw new Error("Session expired"); }
  if (response.status === 204) return null;

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Something went wrong. Try again.");
  }
  return payload;
}

/* -------------------------------------------------------------------- state */

const state = {
  books: [],
  categories: [],
  tagsById: new Map(),
  filterTagIds: new Set(),
  filterText: "",
  sort: "added",
  view: "library",
  readerName: "you",
};

function indexTags() {
  state.tagsById.clear();
  for (const category of state.categories) {
    for (const tag of category.tags) {
      state.tagsById.set(tag.id, { ...tag, categoryName: category.name });
    }
  }
}

/** The colour on a book's spine: its tag from the first exclusive group. */
function spineColor(book) {
  for (const category of state.categories) {
    if (!category.exclusive) continue;
    const hit = book.tags.find(t => t.category_id === category.id);
    if (hit) return hit.color;
  }
  return book.tags[0]?.color || "#2C2542";
}

/* ------------------------------------------------------------------- router */

function goto(view) {
  state.view = view;
  $$(".view").forEach(v => { v.hidden = v.id !== `view-${view}`; });
  $$(".tab").forEach(t => t.classList.toggle("is-on", t.dataset.goto === view));
  window.scrollTo(0, 0);
  if (view === "stats") renderStats();
  if (view === "tags") renderTagManager();
}

/* ========================================================================= */
/*  LIBRARY                                                                  */
/* ========================================================================= */

async function loadLibrary() {
  const params = new URLSearchParams({ sort: state.sort });
  if (state.filterText) params.set("q", state.filterText);
  for (const id of state.filterTagIds) params.append("tag", id);
  params.set("match", "all");

  state.books = await api(`/api/books?${params}`);
  renderShelf();
}

function renderShelf() {
  const shelf = $("#shelf");
  shelf.textContent = "";

  const nothingYet = state.books.length === 0
    && !state.filterText && state.filterTagIds.size === 0;
  $("#library-empty").hidden = !nothingYet;

  if (state.books.length === 0 && !nothingYet) {
    shelf.append(el("p", { className: "muted", style: "grid-column:1/-1" },
      "No books match that. Try clearing a filter."));
    return;
  }

  for (const book of state.books) {
    const cover = el("div", { className: "book-cover" });
    cover.style.setProperty("--spine", spineColor(book));

    if (book.cover_url) {
      const img = el("img", { src: book.cover_url, alt: "", loading: "lazy" });
      img.onerror = () => {
        img.replaceWith(el("div", { className: "fallback" }, book.title));
      };
      cover.append(img);
    } else {
      cover.append(el("div", { className: "fallback" }, book.title));
    }

    if (book.progress_percent > 0 && book.progress_percent < 100) {
      const bar = el("div", { className: "book-progress" });
      bar.append(el("span", { style: `width:${book.progress_percent}%` }));
      cover.append(bar);
    }

    const card = el("button", { className: "book", type: "button" },
      cover,
      el("p", { className: "book-title" }, book.title),
      el("p", { className: "book-author" }, book.author || "Unknown author"));

    card.addEventListener("click", () => openSheet(book.id));
    shelf.append(card);
  }
}

function renderFilterBar() {
  const bar = $("#filter-tags");
  bar.textContent = "";

  for (const tag of state.tagsById.values()) {
    const pill = el("button", { className: "pill", type: "button" }, tag.name);
    pill.style.setProperty("--dot", tag.color);
    pill.classList.toggle("is-on", state.filterTagIds.has(tag.id));
    pill.addEventListener("click", () => {
      state.filterTagIds.has(tag.id)
        ? state.filterTagIds.delete(tag.id)
        : state.filterTagIds.add(tag.id);
      renderFilterBar();
      loadLibrary().catch(e => toast(e.message, true));
    });
    bar.append(pill);
  }
}

/* ========================================================================= */
/*  ADD — catalogue search and manual entry                                  */
/* ========================================================================= */

function advancedFields() {
  return {
    title:     $("#adv-title").value.trim(),
    author:    $("#adv-author").value.trim(),
    isbn:      $("#adv-isbn").value.trim(),
    subject:   $("#adv-subject").value.trim(),
    publisher: $("#adv-publisher").value.trim(),
    year:      $("#adv-year").value.trim(),
  };
}

async function runSearch() {
  const params = new URLSearchParams();
  const plain = $("#search-q").value.trim();
  const advancedOpen = !$("#advanced").hidden;

  if (advancedOpen) {
    for (const [key, value] of Object.entries(advancedFields())) {
      if (value) params.set(key, value);
    }
  }
  if (plain && !params.toString()) params.set("q", plain);

  if (!params.toString()) {
    toast("Type something to search for", true);
    return;
  }

  const results = $("#results");
  results.textContent = "";
  results.append(el("p", { className: "muted" }, "Looking…"));

  try {
    const hits = await api(`/api/search?${params}`);
    renderResults(hits);
  } catch (error) {
    results.textContent = "";
    results.append(el("p", { className: "field-error" }, error.message));
  }
}

function renderResults(hits) {
  const results = $("#results");
  results.textContent = "";

  if (hits.length === 0) {
    results.append(
      el("p", { className: "muted" },
        "Nothing came back. Try fewer words, or add it by hand."));
    return;
  }

  hits.forEach((hit, index) => {
    const thumb = hit.cover_url
      ? el("img", { src: hit.cover_url, alt: "", loading: "lazy" })
      : el("div", { className: "thumb-blank" });

    const meta = [hit.author, hit.year, hit.publisher].filter(Boolean).join(" · ");

    const body = el("div", {},
      el("h3", {}, hit.title),
      el("p", { className: "meta" }, meta || "No details listed"));

    // Only flag the leader, and only when it's actually a strong match.
    if (index === 0 && hit.confidence >= 55) {
      const strong = hit.confidence >= 80;
      body.append(el("span", { className: `match ${strong ? "close" : ""}` },
        strong ? "Closest match" : "Best guess"));
    }

    const row = el("button", { className: "result", type: "button" }, thumb, body);
    row.addEventListener("click", () => openEditor(hitToDraft(hit)));
    results.append(row);
  });

  results.append(el("button", { className: "linkish", type: "button",
    onclick: () => openEditor(blankDraft()) }, "None of these — add it by hand"));
}

const hitToDraft = hit => ({
  title: hit.title, author: hit.author || "", isbn: hit.isbn || "",
  publisher: hit.publisher || "", year: hit.year || "", pages: hit.pages || "",
  cover_url: hit.cover_url || "", openlibrary_key: hit.openlibrary_key || "",
  rating: null, notes: "", progress_pages: 0,
  started_on: "", finished_on: "", tag_ids: [], id: null,
});

const blankDraft = () => ({
  title: "", author: "", isbn: "", publisher: "", year: "", pages: "",
  cover_url: "", openlibrary_key: "", rating: null, notes: "",
  progress_pages: 0, started_on: "", finished_on: "", tag_ids: [], id: null,
});

/* ========================================================================= */
/*  SHEET — view / edit one book                                             */
/* ========================================================================= */

function closeSheet() { $("#sheet").hidden = true; }

async function openSheet(bookId) {
  const book = await api(`/api/books/${bookId}`);
  openEditor({ ...book, tag_ids: book.tags.map(t => t.id) });
}

function openEditor(draft) {
  const body = $("#sheet-body");
  body.textContent = "";
  const isNew = draft.id == null;
  const chosen = new Set(draft.tag_ids);

  /* header ---------------------------------------------------------------- */
  const thumb = draft.cover_url
    ? el("img", { src: draft.cover_url, alt: "" })
    : el("div", { className: "thumb-blank" });

  body.append(el("div", { className: "sheet-hero" }, thumb,
    el("div", {},
      el("h2", {}, draft.title || "New book"),
      el("p", { className: "muted" },
        [draft.author, draft.year].filter(Boolean).join(" · ") || "Fill in the details below"))));

  /* stars ----------------------------------------------------------------- */
  let rating = draft.rating || 0;
  const stars = el("div", { className: "stars" });
  const paintStars = () => $$("button", stars)
    .forEach((s, i) => s.classList.toggle("lit", i < rating));

  for (let i = 1; i <= 5; i++) {
    const star = el("button", { type: "button", textContent: "★",
      title: `${i} star${i > 1 ? "s" : ""}` });
    star.addEventListener("click", () => {
      rating = (rating === i) ? 0 : i;   // tapping the same star clears it
      paintStars();
    });
    stars.append(star);
  }
  paintStars();
  body.append(el("label", {}, "How was it?"), stars);

  /* tags ------------------------------------------------------------------ */
  for (const category of state.categories) {
    if (category.tags.length === 0) continue;
    const bar = el("div", { className: "tagbar" });

    for (const tag of category.tags) {
      const pill = el("button", { className: "pill", type: "button" }, tag.name);
      pill.style.setProperty("--dot", tag.color);
      pill.classList.toggle("is-on", chosen.has(tag.id));
      pill.addEventListener("click", () => {
        if (chosen.has(tag.id)) {
          chosen.delete(tag.id);
        } else {
          if (category.exclusive) {
            category.tags.forEach(t => chosen.delete(t.id));
          }
          chosen.add(tag.id);
        }
        $$(".pill", bar).forEach((p, i) =>
          p.classList.toggle("is-on", chosen.has(category.tags[i].id)));
      });
      bar.append(pill);
    }

    body.append(
      el("label", {}, category.name + (category.exclusive ? " — pick one" : "")),
      bar);
  }

  /* progress -------------------------------------------------------------- */
  const pagesField = el("input", { type: "number", inputMode: "numeric",
    value: draft.pages ?? "", min: "0" });
  const progressField = el("input", { type: "number", inputMode: "numeric",
    value: draft.progress_pages ?? 0, min: "0" });
  const track = el("div", { className: "progress-track" });
  const trackFill = el("span", {});
  track.append(trackFill);

  const paintTrack = () => {
    const total = Number(pagesField.value) || 0;
    const done = Number(progressField.value) || 0;
    trackFill.style.width =
      total > 0 ? `${Math.min(100, Math.round(done / total * 100))}%` : "0%";
  };
  pagesField.addEventListener("input", paintTrack);
  progressField.addEventListener("input", paintTrack);
  paintTrack();

  const progressRow = el("div", { className: "progress-row" },
    el("label", { style: "flex:1;margin:0" }, "On page", progressField),
    el("label", { style: "flex:1;margin:0" }, "of", pagesField));
  body.append(el("label", {}, "Progress"), progressRow, track);

  /* dates, notes, details -------------------------------------------------- */
  const startedField  = el("input", { type: "date", value: draft.started_on || "" });
  const finishedField = el("input", { type: "date", value: draft.finished_on || "" });
  body.append(el("div", { className: "grid-2", style: "margin-top:18px" },
    el("label", {}, "Started", startedField),
    el("label", {}, "Finished", finishedField)));

  const notesField = el("textarea", { value: draft.notes || "",
    placeholder: "What stayed with you?" });
  body.append(el("label", {}, "Notes", notesField));

  const titleField     = el("input", { type: "text", value: draft.title || "" });
  const authorField    = el("input", { type: "text", value: draft.author || "" });
  const isbnField      = el("input", { type: "text", value: draft.isbn || "" });
  const publisherField = el("input", { type: "text", value: draft.publisher || "" });
  const yearField      = el("input", { type: "number", inputMode: "numeric",
                                       value: draft.year ?? "" });
  const coverField     = el("input", { type: "text", value: draft.cover_url || "",
                                       placeholder: "https://…" });

  const details = el("div", {},
    el("label", {}, "Title", titleField),
    el("label", {}, "Author", authorField),
    el("div", { className: "grid-2" },
      el("label", {}, "ISBN", isbnField),
      el("label", {}, "Published", yearField)),
    el("label", {}, "Publisher", publisherField),
    el("label", {}, "Cover image URL", coverField));
  details.hidden = !isNew;

  const detailsToggle = el("button", { className: "linkish", type: "button" },
    isNew ? "Hide book details" : "Edit book details");
  detailsToggle.addEventListener("click", () => {
    details.hidden = !details.hidden;
    detailsToggle.textContent = details.hidden ? "Edit book details" : "Hide book details";
  });
  body.append(detailsToggle, details);

  /* save / delete ---------------------------------------------------------- */
  const collect = () => ({
    title: titleField.value.trim(),
    author: authorField.value.trim() || null,
    isbn: isbnField.value.trim() || null,
    publisher: publisherField.value.trim() || null,
    year: yearField.value ? Number(yearField.value) : null,
    pages: pagesField.value ? Number(pagesField.value) : null,
    cover_url: coverField.value.trim() || null,
    openlibrary_key: draft.openlibrary_key || null,
    rating: rating || null,
    notes: notesField.value.trim() || null,
    progress_pages: Number(progressField.value) || 0,
    started_on: startedField.value || null,
    finished_on: finishedField.value || null,
    tag_ids: [...chosen],
  });

  const save = el("button", { className: "btn-primary", type: "button" },
    isNew ? "Add to library" : "Save changes");

  save.addEventListener("click", async () => {
    const payload = collect();
    if (!payload.title) { toast("A title is the one thing it needs", true); return; }

    save.disabled = true;
    try {
      if (isNew) {
        await api("/api/books", { method: "POST", body: payload });
        toast("Added to your library");
        $("#results").textContent = "";
        $("#search-q").value = "";
      } else {
        delete payload.openlibrary_key;
        await api(`/api/books/${draft.id}`, { method: "PATCH", body: payload });
        toast("Saved");
      }
      closeSheet();
      await loadLibrary();
      goto("library");
    } catch (error) {
      toast(error.message, true);
    } finally {
      save.disabled = false;
    }
  });
  body.append(save);

  if (!isNew) {
    const remove = el("button", { className: "linkish danger", type: "button" },
      "Remove from library");
    remove.addEventListener("click", async () => {
      if (!confirm(`Remove “${draft.title}” from the library?`)) return;
      await api(`/api/books/${draft.id}`, { method: "DELETE" });
      toast("Removed");
      closeSheet();
      loadLibrary();
    });
    body.append(remove);
  }

  $("#sheet").hidden = false;
  $(".sheet-panel").scrollTop = 0;
}

/* ========================================================================= */
/*  STATS                                                                    */
/* ========================================================================= */

function goalRing(done, target) {
  const RADIUS = 34;
  const circumference = 2 * Math.PI * RADIUS;
  const ratio = target > 0 ? Math.min(1, done / target) : 0;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 80 80");
  svg.setAttribute("width", "80");
  svg.setAttribute("height", "80");

  const ring = (cls, offset) => {
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("cx", "40"); c.setAttribute("cy", "40");
    c.setAttribute("r", String(RADIUS));
    c.setAttribute("fill", "none");
    c.setAttribute("stroke-width", "7");
    c.setAttribute("transform", "rotate(-90 40 40)");
    c.setAttribute("class", cls);
    if (offset != null) {
      c.setAttribute("stroke-dasharray", String(circumference));
      c.setAttribute("stroke-dashoffset", String(offset));
    }
    return c;
  };

  svg.append(ring("track"), ring("fill", circumference * (1 - ratio)));
  return svg;
}

async function renderStats() {
  const body = $("#stats-body");
  body.textContent = "";
  const stats = await api("/api/stats");
  const year = new Date().getFullYear();

  const cards = el("div", { className: "stat-grid" },
    el("div", { className: "stat" },
      el("b", {}, String(stats.total_books)), el("span", {}, "books on the shelf")),
    el("div", { className: "stat" },
      el("b", {}, String(stats.finished_books)), el("span", {}, "finished, all time")),
    el("div", { className: "stat" },
      el("b", {}, stats.pages_read.toLocaleString()), el("span", {}, "pages read")),
    el("div", { className: "stat" },
      el("b", {}, stats.average_rating ? stats.average_rating.toFixed(1) : "—"),
      el("span", {}, "average rating")));
  body.append(cards);

  /* goal ------------------------------------------------------------------ */
  const target = stats.goal?.target_books ?? 0;
  const done = stats.goal_completed;
  const goalInput = el("input", { type: "number", inputMode: "numeric",
    min: "0", value: target || "", placeholder: "How many?",
    style: "max-width:120px" });

  goalInput.addEventListener("change", async () => {
    await api("/api/goals", { method: "PUT",
      body: { year, target_books: Number(goalInput.value) || 0 } });
    toast("Goal set");
    renderStats();
  });

  const goalText = target > 0
    ? (done >= target
        ? `${done} of ${target}. Goal met.`
        : `${done} of ${target}. ${target - done} to go.`)
    : "No goal set for this year yet.";

  body.append(el("div", { className: "block" },
    el("h2", {}, `${year} reading goal`),
    el("div", { className: "goal-ring" },
      goalRing(done, target),
      el("div", {},
        el("p", { className: "muted", style: "margin-bottom:8px" }, goalText),
        goalInput))));

  /* by year --------------------------------------------------------------- */
  if (stats.per_year.length) {
    const peak = Math.max(...stats.per_year.map(y => y.books));
    const bars = el("div", { className: "bars" });
    for (const row of stats.per_year) {
      const bar = el("div", { className: "bar" });
      bar.append(el("span", { style: `width:${Math.round(row.books / peak * 100)}%` }));
      bars.append(el("div", { className: "bar-row" },
        el("span", {}, String(row.year)), bar,
        el("span", { className: "count" }, String(row.books))));
    }
    body.append(el("div", { className: "block" },
      el("h2", {}, "Books finished each year"), bars));
  }

  /* by tag ---------------------------------------------------------------- */
  const used = stats.per_tag.filter(row => row.books > 0);
  if (used.length) {
    const pills = el("div", { className: "tagbar", style: "flex-wrap:wrap" });
    for (const row of used) {
      const pill = el("button", { className: "pill static", type: "button" },
        `${row.tag.name} · ${row.books}`);
      pill.style.setProperty("--dot", row.tag.color);
      pills.append(pill);
    }
    body.append(el("div", { className: "block" },
      el("h2", {}, "How the shelf breaks down"), pills));
  }

  if (stats.reading_now > 0) {
    body.append(el("p", { className: "muted", style: "margin-top:20px" },
      `Reading ${stats.reading_now} book${stats.reading_now > 1 ? "s" : ""} right now.`));
  }
}

/* ========================================================================= */
/*  TAG MANAGER                                                              */
/* ========================================================================= */

async function loadTags() {
  state.categories = await api("/api/categories");
  indexTags();
  renderFilterBar();
}

function renderTagManager() {
  const body = $("#tags-body");
  body.textContent = "";

  for (const category of state.categories) {
    const block = el("div", { className: "cat" });

    block.append(el("div", { className: "cat-head" },
      el("h2", {}, category.name),
      el("span", { className: "muted" },
        category.exclusive ? "one at a time" : "stack freely")));

    for (const tag of category.tags) {
      const swatch = el("input", { type: "color", value: tag.color });
      const name = el("input", { type: "text", value: tag.name });
      const remove = el("button", { className: "x", type: "button",
        title: "Delete tag" }, "✕");

      const patch = debounce(async (payload) => {
        try {
          await api(`/api/tags/${tag.id}`, { method: "PATCH", body: payload });
          await loadTags();
          await loadLibrary();
        } catch (error) { toast(error.message, true); }
      }, 400);

      swatch.addEventListener("input", () => patch({ color: swatch.value }));
      name.addEventListener("input", () => {
        if (name.value.trim()) patch({ name: name.value.trim() });
      });

      remove.addEventListener("click", async () => {
        const count = state.books.filter(b =>
          b.tags.some(t => t.id === tag.id)).length;
        const warning = count
          ? `“${tag.name}” is on ${count} book${count > 1 ? "s" : ""}. Delete it anyway?`
          : `Delete “${tag.name}”?`;
        if (!confirm(warning)) return;
        await api(`/api/tags/${tag.id}`, { method: "DELETE" });
        state.filterTagIds.delete(tag.id);
        await loadTags();
        await loadLibrary();
        renderTagManager();
      });

      block.append(el("div", { className: "tag-row" }, swatch, name, remove));
    }

    /* add a tag to this group -------------------------------------------- */
    let pickedColor = RAINBOW[6];
    const swatches = el("div", { className: "swatches" });
    RAINBOW.forEach((hex, i) => {
      const dot = el("button", { type: "button", title: hex });
      dot.style.background = hex;
      dot.classList.toggle("is-on", i === 6);
      dot.addEventListener("click", () => {
        pickedColor = hex;
        $$("button", swatches).forEach(b => b.classList.remove("is-on"));
        dot.classList.add("is-on");
      });
      swatches.append(dot);
    });

    const nameField = el("input", { type: "text",
      placeholder: `New tag in ${category.name}` });
    const add = el("button", { className: "btn-quiet", type: "button" }, "Add tag");

    add.addEventListener("click", async () => {
      const value = nameField.value.trim();
      if (!value) { toast("Give the tag a name", true); return; }
      try {
        await api("/api/tags", { method: "POST", body: {
          name: value, color: pickedColor, category_id: category.id,
          position: category.tags.length } });
        nameField.value = "";
        await loadTags();
        renderTagManager();
        toast("Tag added");
      } catch (error) { toast(error.message, true); }
    });

    block.append(nameField, swatches, add);
    body.append(block);
  }
}

/* ========================================================================= */
/*  AUTH + BOOT                                                              */
/* ========================================================================= */

function showLock() {
  $("#lock").hidden = false;
  $("#app").hidden = true;
}

async function enterApp() {
  $("#lock").hidden = true;
  $("#app").hidden = false;
  await loadTags();
  await loadLibrary();
  $("#library-heading").textContent = `${state.readerName}’s library`;
}

async function signIn() {
  const error = $("#lock-error");
  error.hidden = true;
  try {
    await api("/api/auth/login", { method: "POST",
      body: { password: $("#lock-password").value } });
    $("#lock-password").value = "";
    await enterApp();
  } catch (e) {
    error.textContent = e.message;
    error.hidden = false;
  }
}

function wireEvents() {
  $$("[data-goto]").forEach(node =>
    node.addEventListener("click", () => goto(node.dataset.goto)));

  $$("[data-close-sheet]").forEach(node =>
    node.addEventListener("click", closeSheet));

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && !$("#sheet").hidden) closeSheet();
  });

  $("#lock-submit").addEventListener("click", signIn);
  $("#lock-password").addEventListener("keydown", e => {
    if (e.key === "Enter") signIn();
  });

  $("#filter-text").addEventListener("input", debounce(e => {
    state.filterText = e.target.value.trim();
    loadLibrary().catch(err => toast(err.message, true));
  }));

  $("#sort-select").addEventListener("change", e => {
    state.sort = e.target.value;
    loadLibrary().catch(err => toast(err.message, true));
  });

  $("#toggle-advanced").addEventListener("click", () => {
    const panel = $("#advanced");
    panel.hidden = !panel.hidden;
    $("#toggle-advanced").setAttribute("aria-expanded", String(!panel.hidden));
    $("#toggle-advanced").textContent =
      panel.hidden ? "Advanced search" : "Hide advanced search";
  });

  $("#search-run").addEventListener("click", runSearch);
  $("#search-q").addEventListener("keydown", e => {
    if (e.key === "Enter") runSearch();
  });
  $("#manual-open").addEventListener("click", () => openEditor(blankDraft()));

  $("#new-category-save").addEventListener("click", async () => {
    const name = $("#new-category-name").value.trim();
    if (!name) { toast("Give the group a name", true); return; }
    try {
      await api("/api/categories", { method: "POST", body: {
        name, exclusive: $("#new-category-exclusive").checked,
        position: state.categories.length } });
      $("#new-category-name").value = "";
      $("#new-category-exclusive").checked = false;
      await loadTags();
      renderTagManager();
      toast("Group added");
    } catch (error) { toast(error.message, true); }
  });

  $("#import-file").addEventListener("change", async e => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api("/api/import.csv", { method: "POST", raw: form });
      toast(`Added ${result.added}, skipped ${result.skipped}`);
      await loadTags();
      await loadLibrary();
    } catch (error) {
      toast(error.message, true);
    } finally {
      e.target.value = "";
    }
  });

  $("#sign-out").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    showLock();
  });
}

async function boot() {
  wireEvents();

  const session = await api("/api/auth/session");
  state.readerName = session.reader_name;
  $("#splash-studio").textContent = session.studio_name;
  $("#splash-dedication").textContent = session.dedication;

  if (session.signed_in) {
    await enterApp();
  } else {
    showLock();
  }

  // The splash animation is 3.4s; let it finish, then take it out of the tree.
  setTimeout(() => $("#splash")?.remove(), 3600);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

boot().catch(error => {
  $("#splash")?.remove();
  showLock();
  console.error(error);
});

})();
