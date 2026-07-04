/* ============================================================
   QuizMaster — prywatna aplikacja do fiszek (alternatywa Quizleta)
   Czysty JS, bez zależności. Dane w localStorage.
   ============================================================ */

(() => {
  "use strict";

  const LS_SETS = "quizmaster.sets.v1";
  const LS_BEST = "quizmaster.matchBest.v1";

  const $app = document.getElementById("app");

  // ---------- Stan ----------

  const state = {
    sets: loadSets(),
    search: "",
    // aktywna sesja nauki (fiszki / ucz się / pisanie / test / dopasowanie)
    session: null,
  };

  // ---------- Narzędzia ----------

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function esc(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function normalize(s) {
    return String(s ?? "").trim().toLowerCase().replace(/\s+/g, " ");
  }

  function plural(n, one, few, many) {
    if (n === 1) return one;
    const mod10 = n % 10, mod100 = n % 100;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
    return many;
  }

  function toast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 2600);
  }

  // ---------- Trwałość danych ----------

  function loadSets() {
    try {
      const raw = localStorage.getItem(LS_SETS);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (e) { /* uszkodzone dane — zaczynamy od zera */ }
    return [makeSampleSet()];
  }

  function saveSets() {
    localStorage.setItem(LS_SETS, JSON.stringify(state.sets));
  }

  function loadBestTimes() {
    try {
      return JSON.parse(localStorage.getItem(LS_BEST)) || {};
    } catch (e) { return {}; }
  }

  function saveBestTime(setId, seconds) {
    const best = loadBestTimes();
    if (best[setId] == null || seconds < best[setId]) {
      best[setId] = seconds;
      localStorage.setItem(LS_BEST, JSON.stringify(best));
      return true;
    }
    return false;
  }

  function makeSampleSet() {
    const cards = [
      ["hello", "cześć"],
      ["thank you", "dziękuję"],
      ["dog", "pies"],
      ["cat", "kot"],
      ["book", "książka"],
      ["water", "woda"],
      ["house", "dom"],
      ["friend", "przyjaciel"],
      ["to learn", "uczyć się"],
      ["memory", "pamięć"],
    ].map(([term, def]) => ({ id: uid(), term, def, level: 0 }));

    return {
      id: uid(),
      title: "Przykład: angielski — podstawy",
      description: "Przykładowy zestaw startowy. Możesz go edytować albo usunąć i stworzyć własne zestawy.",
      cards,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
  }

  function getSet(id) {
    return state.sets.find((s) => s.id === id);
  }

  // ---------- Router (prosty, na hash) ----------

  function go(route) {
    location.hash = route;
  }

  function render() {
    const hash = location.hash.replace(/^#\/?/, "");
    const [view, id, extra] = hash.split("/");
    stopMatchTimer();

    if (view === "set" && getSet(id)) return renderSetView(getSet(id));
    if (view === "edit" && (id === "new" || getSet(id))) return renderEditor(id === "new" ? null : getSet(id));
    if (view === "study" && getSet(id)) return renderStudy(getSet(id), extra);
    return renderHome();
  }

  window.addEventListener("hashchange", render);

  // ============================================================
  //  STRONA GŁÓWNA
  // ============================================================

  function renderHome() {
    state.session = null;
    const q = normalize(state.search);
    const sets = state.sets
      .filter((s) => !q || normalize(s.title).includes(q) || normalize(s.description).includes(q))
      .sort((a, b) => b.updatedAt - a.updatedAt);

    $app.innerHTML = `
      <div class="page-head">
        <div>
          <h1>Twoje zestawy</h1>
          <div class="subtitle">${state.sets.length} ${plural(state.sets.length, "zestaw", "zestawy", "zestawów")} · wszystko zapisane lokalnie w Twojej przeglądarce</div>
        </div>
      </div>
      <div class="search-row">
        <input class="search-input" id="searchInput" type="search" placeholder="Szukaj zestawu…" value="${esc(state.search)}">
      </div>
      ${sets.length === 0 ? `
        <div class="empty-state">
          <div class="big">📚</div>
          <h2>${state.sets.length === 0 ? "Nie masz jeszcze żadnych zestawów" : "Brak wyników wyszukiwania"}</h2>
          <p>${state.sets.length === 0 ? "Stwórz pierwszy zestaw fiszek i zacznij naukę." : "Spróbuj innej frazy."}</p>
          ${state.sets.length === 0 ? `<button class="btn btn-primary btn-lg" data-action="new-set">+ Stwórz zestaw</button>` : ""}
        </div>
      ` : `
        <div class="sets-grid">
          ${sets.map((s) => {
            const mastered = s.cards.filter((c) => c.level >= 2).length;
            return `
              <button class="set-card" data-open="${s.id}">
                <h3>${esc(s.title)}</h3>
                ${s.description ? `<div class="set-desc">${esc(s.description)}</div>` : ""}
                <div class="set-meta">
                  <span class="pill">${s.cards.length} ${plural(s.cards.length, "pojęcie", "pojęcia", "pojęć")}</span>
                  ${mastered > 0 ? `<span class="pill pill-green">${mastered} opanowane</span>` : ""}
                </div>
              </button>`;
          }).join("")}
        </div>
      `}
    `;

    const search = document.getElementById("searchInput");
    search.addEventListener("input", () => {
      state.search = search.value;
      // przerysuj tylko siatkę — najprościej: pełny rerender z zachowaniem fokusa
      const pos = search.selectionStart;
      renderHome();
      const s2 = document.getElementById("searchInput");
      s2.focus();
      s2.setSelectionRange(pos, pos);
    });

    $app.querySelectorAll("[data-open]").forEach((el) =>
      el.addEventListener("click", () => go(`/set/${el.dataset.open}`))
    );
    $app.querySelector("[data-action='new-set']")?.addEventListener("click", () => go("/edit/new"));
  }

  // ============================================================
  //  WIDOK ZESTAWU
  // ============================================================

  function renderSetView(set) {
    state.session = null;
    const total = set.cards.length;
    const mastered = set.cards.filter((c) => c.level >= 2).length;
    const learning = set.cards.filter((c) => c.level === 1).length;
    const best = loadBestTimes()[set.id];

    $app.innerHTML = `
      <button class="back-link" data-action="back">← Wszystkie zestawy</button>
      <div class="page-head">
        <div>
          <h1>${esc(set.title)}</h1>
          ${set.description ? `<div class="subtitle">${esc(set.description)}</div>` : ""}
        </div>
        <div class="head-actions">
          <button class="btn btn-ghost" data-action="edit">✎ Edytuj</button>
          <button class="btn btn-ghost" data-action="export">⬇ Eksport</button>
          <button class="btn btn-danger" data-action="delete">Usuń</button>
        </div>
      </div>

      <div class="progress-summary">
        <span>Pojęcia: <b>${total}</b></span>
        <span>Opanowane: <b>${mastered}</b></span>
        <span>W trakcie nauki: <b>${learning}</b></span>
        ${best != null ? `<span>Rekord dopasowania: <b>${best.toFixed(1)}s</b></span>` : ""}
      </div>

      <div class="mode-grid">
        <button class="mode-btn" data-mode="flashcards">
          <span class="mode-icon">🃏</span> Fiszki
          <span class="mode-hint">przeglądaj i odwracaj</span>
        </button>
        <button class="mode-btn" data-mode="learn">
          <span class="mode-icon">🎓</span> Ucz się
          <span class="mode-hint">tryb adaptacyjny</span>
        </button>
        <button class="mode-btn" data-mode="write">
          <span class="mode-icon">✍️</span> Pisanie
          <span class="mode-hint">wpisuj odpowiedzi</span>
        </button>
        <button class="mode-btn" data-mode="test">
          <span class="mode-icon">📝</span> Test
          <span class="mode-hint">sprawdzian z oceną</span>
        </button>
        <button class="mode-btn" data-mode="match">
          <span class="mode-icon">⚡</span> Dopasowanie
          <span class="mode-hint">gra na czas</span>
        </button>
      </div>

      <div class="section-label">Pojęcia w zestawie (${total})</div>
      <div class="card-list">
        ${set.cards.map((c) => `
          <div class="card-row">
            <div class="term">${esc(c.term)}</div>
            <div class="def">${esc(c.def)}</div>
            <span class="mastery-dot m${c.level >= 2 ? 2 : c.level}" title="${c.level >= 2 ? "opanowane" : c.level === 1 ? "w trakcie nauki" : "nowe"}"></span>
          </div>
        `).join("")}
      </div>
    `;

    $app.querySelector("[data-action='back']").addEventListener("click", () => go("/"));
    $app.querySelector("[data-action='edit']").addEventListener("click", () => go(`/edit/${set.id}`));
    $app.querySelector("[data-action='export']").addEventListener("click", () => exportJson([set], `${set.title}.json`));
    $app.querySelector("[data-action='delete']").addEventListener("click", () => {
      if (confirm(`Usunąć zestaw „${set.title}"? Tej operacji nie można cofnąć.`)) {
        state.sets = state.sets.filter((s) => s.id !== set.id);
        saveSets();
        toast("Zestaw usunięty");
        go("/");
      }
    });
    $app.querySelectorAll("[data-mode]").forEach((el) =>
      el.addEventListener("click", () => {
        if (el.dataset.mode !== "flashcards" && set.cards.length < 2) {
          toast("Ten tryb wymaga co najmniej 2 pojęć w zestawie");
          return;
        }
        if (set.cards.length === 0) {
          toast("Dodaj najpierw pojęcia do zestawu");
          return;
        }
        go(`/study/${set.id}/${el.dataset.mode}`);
      })
    );
  }

  // ============================================================
  //  EDYTOR ZESTAWU
  // ============================================================

  function renderEditor(set) {
    state.session = null;
    const isNew = !set;
    const draft = {
      title: set?.title ?? "",
      description: set?.description ?? "",
      cards: set ? set.cards.map((c) => ({ ...c })) : [blankCard(), blankCard(), blankCard()],
    };

    function blankCard() {
      return { id: uid(), term: "", def: "", level: 0 };
    }

    function rowsHtml() {
      return draft.cards.map((c, i) => `
        <div class="editor-row" data-idx="${i}">
          <div class="row-num">${i + 1}</div>
          <input type="text" data-field="term" placeholder="pojęcie" value="${esc(c.term)}">
          <input type="text" data-field="def" placeholder="definicja" value="${esc(c.def)}">
          <button class="row-del" title="Usuń wiersz">✕</button>
        </div>
      `).join("");
    }

    $app.innerHTML = `
      <button class="back-link" data-action="back">← Wróć</button>
      <div class="page-head">
        <h1>${isNew ? "Nowy zestaw" : "Edytuj zestaw"}</h1>
      </div>

      <div class="editor-field">
        <label for="setTitle">Tytuł</label>
        <input class="text-input" id="setTitle" type="text" placeholder="np. Hiszpański — czasowniki" value="${esc(draft.title)}">
      </div>
      <div class="editor-field">
        <label for="setDesc">Opis (opcjonalnie)</label>
        <input class="text-input" id="setDesc" type="text" placeholder="Krótki opis zestawu" value="${esc(draft.description)}">
      </div>

      <details class="import-box">
        <summary>📋 Szybki import z tekstu</summary>
        <div class="hint">
          Wklej listę pojęć — każde pojęcie w nowej linii, pojęcie i definicję oddziel tabulatorem,
          średnikiem albo znakiem „ - " (myślnik ze spacjami). Przykład:<br>
          <code>dog - pies</code><br><code>cat - kot</code>
        </div>
        <textarea class="textarea" id="importText" rows="6" placeholder="dog - pies&#10;cat - kot"></textarea>
        <div style="margin-top:10px">
          <button class="btn btn-ghost btn-sm" id="importTextBtn">Dodaj z tekstu</button>
        </div>
      </details>

      <div class="section-label">Pojęcia</div>
      <div class="editor-rows" id="editorRows">${rowsHtml()}</div>
      <button class="btn btn-ghost" id="addRowBtn">+ Dodaj pojęcie</button>

      <div class="editor-actions">
        <button class="btn btn-primary btn-lg" id="saveBtn">${isNew ? "Utwórz zestaw" : "Zapisz zmiany"}</button>
        <button class="btn btn-ghost btn-lg" data-action="back2">Anuluj</button>
      </div>
    `;

    const $rows = document.getElementById("editorRows");

    function syncDraftFromDom() {
      $rows.querySelectorAll(".editor-row").forEach((row) => {
        const i = Number(row.dataset.idx);
        draft.cards[i].term = row.querySelector("[data-field='term']").value;
        draft.cards[i].def = row.querySelector("[data-field='def']").value;
      });
    }

    function repaintRows() {
      $rows.innerHTML = rowsHtml();
    }

    $rows.addEventListener("input", (e) => {
      const row = e.target.closest(".editor-row");
      if (!row) return;
      const i = Number(row.dataset.idx);
      const field = e.target.dataset.field;
      if (field) draft.cards[i][field] = e.target.value;
    });

    $rows.addEventListener("click", (e) => {
      const del = e.target.closest(".row-del");
      if (!del) return;
      syncDraftFromDom();
      const i = Number(del.closest(".editor-row").dataset.idx);
      draft.cards.splice(i, 1);
      if (draft.cards.length === 0) draft.cards.push(blankCard());
      repaintRows();
    });

    document.getElementById("addRowBtn").addEventListener("click", () => {
      syncDraftFromDom();
      draft.cards.push(blankCard());
      repaintRows();
      const inputs = $rows.querySelectorAll(".editor-row:last-child input");
      inputs[0]?.focus();
    });

    document.getElementById("importTextBtn").addEventListener("click", () => {
      const text = document.getElementById("importText").value;
      const parsed = parsePastedCards(text);
      if (parsed.length === 0) {
        toast("Nie udało się rozpoznać żadnych pojęć");
        return;
      }
      syncDraftFromDom();
      // usuń puste wiersze przed dołączeniem importu
      draft.cards = draft.cards.filter((c) => c.term.trim() || c.def.trim());
      parsed.forEach(([term, def]) => draft.cards.push({ id: uid(), term, def, level: 0 }));
      repaintRows();
      document.getElementById("importText").value = "";
      toast(`Dodano ${parsed.length} ${plural(parsed.length, "pojęcie", "pojęcia", "pojęć")}`);
    });

    document.getElementById("saveBtn").addEventListener("click", () => {
      syncDraftFromDom();
      const title = document.getElementById("setTitle").value.trim();
      const description = document.getElementById("setDesc").value.trim();
      const cards = draft.cards
        .map((c) => ({ ...c, term: c.term.trim(), def: c.def.trim() }))
        .filter((c) => c.term && c.def);

      if (!title) { toast("Podaj tytuł zestawu"); return; }
      if (cards.length === 0) { toast("Dodaj co najmniej jedno pojęcie z definicją"); return; }

      if (isNew) {
        const newSet = { id: uid(), title, description, cards, createdAt: Date.now(), updatedAt: Date.now() };
        state.sets.push(newSet);
        saveSets();
        toast("Zestaw utworzony 🎉");
        go(`/set/${newSet.id}`);
      } else {
        set.title = title;
        set.description = description;
        set.cards = cards;
        set.updatedAt = Date.now();
        saveSets();
        toast("Zapisano zmiany");
        go(`/set/${set.id}`);
      }
    });

    const goBack = () => (isNew ? go("/") : go(`/set/${set.id}`));
    $app.querySelector("[data-action='back']").addEventListener("click", goBack);
    $app.querySelector("[data-action='back2']").addEventListener("click", goBack);
  }

  function parsePastedCards(text) {
    const out = [];
    for (const rawLine of String(text).split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line) continue;
      let term, def;
      if (line.includes("\t")) {
        [term, ...def] = line.split("\t");
        def = def.join(" ");
      } else if (line.includes(";")) {
        [term, ...def] = line.split(";");
        def = def.join(";");
      } else if (line.includes(" - ")) {
        [term, ...def] = line.split(" - ");
        def = def.join(" - ");
      } else {
        continue;
      }
      term = String(term).trim();
      def = String(def).trim();
      if (term && def) out.push([term, def]);
    }
    return out;
  }

  // ============================================================
  //  TRYBY NAUKI
  // ============================================================

  function renderStudy(set, mode) {
    switch (mode) {
      case "flashcards": return renderFlashcards(set);
      case "learn": return renderLearn(set);
      case "write": return renderWrite(set);
      case "test": return renderTestConfig(set);
      case "match": return renderMatch(set);
      default: return go(`/set/${set.id}`);
    }
  }

  function studyHeader(set, modeName, progressText) {
    return `
      <button class="back-link" data-action="back">← ${esc(set.title)}</button>
      <div class="study-head">
        <h2>${modeName}</h2>
        <div class="study-progress-text">${progressText}</div>
      </div>
    `;
  }

  function bindBack(set) {
    $app.querySelector("[data-action='back']").addEventListener("click", () => go(`/set/${set.id}`));
  }

  // ---------- FISZKI ----------

  function renderFlashcards(set) {
    if (!state.session || state.session.kind !== "flashcards" || state.session.setId !== set.id) {
      state.session = {
        kind: "flashcards",
        setId: set.id,
        order: set.cards.map((c) => c.id),
        idx: 0,
        flipped: false,
      };
    }
    const ses = state.session;
    const card = set.cards.find((c) => c.id === ses.order[ses.idx]) || set.cards[0];

    $app.innerHTML = `
      ${studyHeader(set, "🃏 Fiszki", `${ses.idx + 1} / ${ses.order.length}`)}
      <div class="progress-bar"><div class="fill" style="width:${((ses.idx + 1) / ses.order.length) * 100}%"></div></div>

      <div class="flashcard-stage">
        <button class="flashcard ${ses.flipped ? "flipped" : ""}" id="flashcard" aria-label="Odwróć fiszkę">
          <span class="face front"><span class="face-label">Pojęcie</span>${esc(card.term)}</span>
          <span class="face back"><span class="face-label">Definicja</span>${esc(card.def)}</span>
        </button>
      </div>

      <div class="flash-controls">
        <button class="nav-btn" id="prevBtn" title="Poprzednia" ${ses.idx === 0 ? "disabled" : ""}>←</button>
        <button class="btn btn-ghost" id="shuffleBtn">🔀 Tasuj</button>
        <button class="btn btn-ghost" id="speakBtn">🔊 Czytaj</button>
        <button class="nav-btn" id="nextBtn" title="Następna" ${ses.idx === ses.order.length - 1 ? "disabled" : ""}>→</button>
      </div>
      <div class="kbd-hint"><kbd>Spacja</kbd> odwróć · <kbd>←</kbd>/<kbd>→</kbd> nawigacja</div>
    `;

    bindBack(set);

    const flip = () => {
      ses.flipped = !ses.flipped;
      document.getElementById("flashcard").classList.toggle("flipped", ses.flipped);
    };
    const goIdx = (i) => {
      if (i < 0 || i >= ses.order.length) return;
      ses.idx = i;
      ses.flipped = false;
      renderFlashcards(set);
    };

    document.getElementById("flashcard").addEventListener("click", flip);
    document.getElementById("prevBtn").addEventListener("click", () => goIdx(ses.idx - 1));
    document.getElementById("nextBtn").addEventListener("click", () => goIdx(ses.idx + 1));
    document.getElementById("shuffleBtn").addEventListener("click", () => {
      ses.order = shuffle(ses.order);
      ses.idx = 0;
      ses.flipped = false;
      renderFlashcards(set);
      toast("Przetasowano fiszki");
    });
    document.getElementById("speakBtn").addEventListener("click", () => {
      const text = ses.flipped ? card.def : card.term;
      try {
        speechSynthesis.cancel();
        speechSynthesis.speak(new SpeechSynthesisUtterance(text));
      } catch (e) { toast("Synteza mowy niedostępna w tej przeglądarce"); }
    });

    document.onkeydown = (e) => {
      if (!location.hash.includes("/flashcards")) { document.onkeydown = null; return; }
      if (e.target.matches("input, textarea")) return;
      if (e.code === "Space") { e.preventDefault(); flip(); }
      if (e.key === "ArrowLeft") goIdx(ses.idx - 1);
      if (e.key === "ArrowRight") goIdx(ses.idx + 1);
    };
  }

  // ---------- UCZ SIĘ (adaptacyjny) ----------
  // Poziomy opanowania: 0 = nowe (pytanie wyboru), 1 = w trakcie (pisanie), 2 = opanowane.

  function renderLearn(set) {
    if (!state.session || state.session.kind !== "learn" || state.session.setId !== set.id) {
      state.session = { kind: "learn", setId: set.id, roundSize: 7, answered: 0, correct: 0 };
    }
    nextLearnQuestion(set);
  }

  function nextLearnQuestion(set) {
    const ses = state.session;
    const remaining = set.cards.filter((c) => (c.level ?? 0) < 2);

    if (remaining.length === 0) {
      return renderResults(set, {
        title: "🎓 Wszystko opanowane!",
        scoreText: "100%",
        scoreClass: "good",
        detail: `Opanowano wszystkie ${set.cards.length} ${plural(set.cards.length, "pojęcie", "pojęcia", "pojęć")} w tym zestawie.`,
        actions: [
          { label: "Zresetuj postępy i ucz się od nowa", handler: () => { resetProgress(set); renderLearn(set); } },
          { label: "Wróć do zestawu", handler: () => go(`/set/${set.id}`) },
        ],
      });
    }

    // preferuj karty o niższym poziomie, wybieraj losowo
    const pool = shuffle(remaining).sort((a, b) => (a.level ?? 0) - (b.level ?? 0));
    const card = pool[0];
    const type = (card.level ?? 0) === 0 && set.cards.length >= 4 ? "choice" : "write";

    const mastered = set.cards.filter((c) => c.level >= 2).length;
    const progressPct = (mastered / set.cards.length) * 100;

    let bodyHtml;
    if (type === "choice") {
      const distractors = shuffle(set.cards.filter((c) => c.id !== card.id)).slice(0, 3);
      const choices = shuffle([card, ...distractors]);
      bodyHtml = `
        <div class="question-type-tag">Wybierz definicję</div>
        <div class="question-prompt">${esc(card.term)}</div>
        <div class="choices">
          ${choices.map((c) => `<button class="choice-btn" data-id="${c.id}">${esc(c.def)}</button>`).join("")}
        </div>
        <div id="feedbackZone"></div>
      `;
    } else {
      bodyHtml = `
        <div class="question-type-tag">Wpisz pojęcie</div>
        <div class="question-prompt">${esc(card.def)}</div>
        <div class="write-row">
          <input class="text-input" id="writeInput" type="text" placeholder="Wpisz odpowiedź…" autocomplete="off">
          <button class="btn btn-primary" id="checkBtn">Sprawdź</button>
          <button class="btn btn-ghost" id="dontKnowBtn">Nie wiem</button>
        </div>
        <div id="feedbackZone"></div>
      `;
    }

    $app.innerHTML = `
      ${studyHeader(set, "🎓 Ucz się", `opanowane: ${mastered} / ${set.cards.length}`)}
      <div class="progress-bar"><div class="fill" style="width:${progressPct}%"></div></div>
      <div class="question-card">${bodyHtml}</div>
    `;

    bindBack(set);

    const finishQuestion = (ok, answerShownAlready) => {
      ses.answered++;
      if (ok) {
        ses.correct++;
        card.level = Math.min(2, (card.level ?? 0) + 1);
      } else {
        card.level = 0;
      }
      set.updatedAt = Date.now();
      saveSets();

      const zone = document.getElementById("feedbackZone");
      if (!answerShownAlready) {
        zone.innerHTML = ok
          ? `<div class="feedback good"><b>Dobrze! 🎉</b></div>`
          : `<div class="feedback bad"><b>Niestety nie.</b> Poprawna odpowiedź: ${esc(card.term)} — ${esc(card.def)}</div>`;
      }
      setTimeout(() => {
        if (state.session === ses && location.hash.includes("/learn")) nextLearnQuestion(set);
      }, ok ? 750 : 2100);
    };

    if (type === "choice") {
      $app.querySelectorAll(".choice-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const ok = btn.dataset.id === card.id;
          $app.querySelectorAll(".choice-btn").forEach((b) => {
            b.disabled = true;
            if (b.dataset.id === card.id) b.classList.add("correct");
          });
          if (!ok) btn.classList.add("wrong");
          finishQuestion(ok, true);
        });
      });
    } else {
      const input = document.getElementById("writeInput");
      input.focus();
      const submit = () => {
        const ok = normalize(input.value) === normalize(card.term);
        input.disabled = true;
        document.getElementById("checkBtn").disabled = true;
        document.getElementById("dontKnowBtn").disabled = true;
        finishQuestion(ok, false);
      };
      document.getElementById("checkBtn").addEventListener("click", submit);
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
      document.getElementById("dontKnowBtn").addEventListener("click", () => {
        input.disabled = true;
        document.getElementById("checkBtn").disabled = true;
        document.getElementById("dontKnowBtn").disabled = true;
        finishQuestion(false, false);
      });
    }
  }

  function resetProgress(set) {
    set.cards.forEach((c) => { c.level = 0; });
    set.updatedAt = Date.now();
    saveSets();
    toast("Postępy zresetowane");
  }

  // ---------- PISANIE ----------

  function renderWrite(set) {
    if (!state.session || state.session.kind !== "write" || state.session.setId !== set.id) {
      state.session = {
        kind: "write",
        setId: set.id,
        queue: shuffle(set.cards.map((c) => c.id)),
        total: set.cards.length,
        firstTryCorrect: 0,
        seen: new Set(),
      };
    }
    nextWriteQuestion(set);
  }

  function nextWriteQuestion(set) {
    const ses = state.session;

    if (ses.queue.length === 0) {
      const pct = Math.round((ses.firstTryCorrect / ses.total) * 100);
      return renderResults(set, {
        title: "✍️ Runda pisania ukończona",
        scoreText: `${pct}%`,
        scoreClass: pct >= 80 ? "good" : pct >= 50 ? "mid" : "bad",
        detail: `Za pierwszym podejściem: ${ses.firstTryCorrect} / ${ses.total}.`,
        actions: [
          { label: "Jeszcze raz", handler: () => { state.session = null; renderWrite(set); } },
          { label: "Wróć do zestawu", handler: () => go(`/set/${set.id}`) },
        ],
      });
    }

    const cardId = ses.queue[0];
    const card = set.cards.find((c) => c.id === cardId);
    const done = ses.total - new Set(ses.queue).size;

    $app.innerHTML = `
      ${studyHeader(set, "✍️ Pisanie", `pozostało: ${new Set(ses.queue).size} / ${ses.total}`)}
      <div class="progress-bar"><div class="fill" style="width:${(done / ses.total) * 100}%"></div></div>
      <div class="question-card">
        <div class="question-type-tag">Wpisz pojęcie</div>
        <div class="question-prompt">${esc(card.def)}</div>
        <div class="write-row">
          <input class="text-input" id="writeInput" type="text" placeholder="Wpisz odpowiedź…" autocomplete="off">
          <button class="btn btn-primary" id="checkBtn">Sprawdź</button>
          <button class="btn btn-ghost" id="dontKnowBtn">Nie wiem</button>
        </div>
        <div id="feedbackZone"></div>
      </div>
    `;

    bindBack(set);

    const input = document.getElementById("writeInput");
    input.focus();

    const answer = (ok) => {
      input.disabled = true;
      document.getElementById("checkBtn").disabled = true;
      document.getElementById("dontKnowBtn").disabled = true;

      ses.queue.shift();
      if (ok) {
        if (!ses.seen.has(card.id)) ses.firstTryCorrect++;
      } else {
        ses.queue.push(card.id); // wraca na koniec kolejki
      }
      ses.seen.add(card.id);

      const zone = document.getElementById("feedbackZone");
      zone.innerHTML = ok
        ? `<div class="feedback good"><b>Dobrze! 🎉</b></div>`
        : `<div class="feedback bad"><b>Poprawna odpowiedź:</b> ${esc(card.term)}<br><span class="muted">To pytanie wróci na koniec rundy.</span></div>`;

      setTimeout(() => {
        if (state.session === ses && location.hash.includes("/write")) nextWriteQuestion(set);
      }, ok ? 700 : 2200);
    };

    const submit = () => answer(normalize(input.value) === normalize(card.term));
    document.getElementById("checkBtn").addEventListener("click", submit);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    document.getElementById("dontKnowBtn").addEventListener("click", () => answer(false));
  }

  // ---------- TEST ----------

  function renderTestConfig(set) {
    state.session = null;
    const maxQ = set.cards.length;

    $app.innerHTML = `
      ${studyHeader(set, "📝 Test", "")}
      <div class="test-config">
        <div class="config-row">
          <label for="qCount">Liczba pytań</label>
          <input type="number" id="qCount" min="1" max="${maxQ}" value="${Math.min(10, maxQ)}">
          <span class="muted">(maks. ${maxQ})</span>
        </div>
        <div class="config-row">
          <label>Rodzaje pytań</label>
          <label class="checkbox-label"><input type="checkbox" id="typeChoice" checked ${set.cards.length < 4 ? "disabled" : ""}> Wybór</label>
          <label class="checkbox-label"><input type="checkbox" id="typeWrite" checked> Pisanie</label>
          <label class="checkbox-label"><input type="checkbox" id="typeTf" checked> Prawda/Fałsz</label>
        </div>
        <div class="config-row">
          <label for="answerWith">Odpowiadaj</label>
          <select id="answerWith">
            <option value="def">definicją (pytanie: pojęcie)</option>
            <option value="term">pojęciem (pytanie: definicja)</option>
          </select>
        </div>
        <div>
          <button class="btn btn-primary btn-lg" id="startTestBtn">Rozpocznij test</button>
        </div>
      </div>
    `;

    bindBack(set);

    document.getElementById("startTestBtn").addEventListener("click", () => {
      const count = Math.max(1, Math.min(maxQ, Number(document.getElementById("qCount").value) || 1));
      const types = [];
      if (document.getElementById("typeChoice").checked && set.cards.length >= 4) types.push("choice");
      if (document.getElementById("typeWrite").checked) types.push("write");
      if (document.getElementById("typeTf").checked) types.push("tf");
      if (types.length === 0) { toast("Wybierz co najmniej jeden rodzaj pytań"); return; }
      const answerWith = document.getElementById("answerWith").value;
      startTest(set, count, types, answerWith);
    });
  }

  function startTest(set, count, types, answerWith) {
    const picked = shuffle(set.cards).slice(0, count);
    const questions = picked.map((card, i) => {
      const type = types[i % types.length];
      const prompt = answerWith === "def" ? card.term : card.def;
      const answer = answerWith === "def" ? card.def : card.term;
      const q = { card, type, prompt, answer };

      if (type === "choice") {
        const others = shuffle(set.cards.filter((c) => c.id !== card.id)).slice(0, 3);
        q.choices = shuffle([answer, ...others.map((c) => (answerWith === "def" ? c.def : c.term))]);
      } else if (type === "tf") {
        // 50% szans na fałszywe dopasowanie
        if (Math.random() < 0.5 || set.cards.length < 2) {
          q.shown = answer;
          q.isTrue = true;
        } else {
          const other = shuffle(set.cards.filter((c) => c.id !== card.id))[0];
          q.shown = answerWith === "def" ? other.def : other.term;
          q.isTrue = false;
        }
      }
      return q;
    });

    state.session = { kind: "test", setId: set.id, questions: shuffle(questions), answerWith };
    renderTestForm(set);
  }

  function renderTestForm(set) {
    const ses = state.session;

    $app.innerHTML = `
      ${studyHeader(set, "📝 Test", `${ses.questions.length} ${plural(ses.questions.length, "pytanie", "pytania", "pytań")}`)}
      <form id="testForm">
        ${ses.questions.map((q, i) => `
          <div class="question-card test-question">
            <div class="q-index">Pytanie ${i + 1} z ${ses.questions.length}</div>
            ${q.type === "choice" ? `
              <div class="question-type-tag">Wybierz poprawną odpowiedź</div>
              <div class="question-prompt">${esc(q.prompt)}</div>
              <div class="choices">
                ${q.choices.map((c, ci) => `
                  <label class="choice-btn checkbox-label" style="display:flex">
                    <input type="radio" name="q${i}" value="${ci}"> <span>${esc(c)}</span>
                  </label>
                `).join("")}
              </div>
            ` : q.type === "write" ? `
              <div class="question-type-tag">Wpisz odpowiedź</div>
              <div class="question-prompt">${esc(q.prompt)}</div>
              <input class="text-input" type="text" name="q${i}" placeholder="Twoja odpowiedź…" autocomplete="off">
            ` : `
              <div class="question-type-tag">Prawda czy fałsz?</div>
              <div class="question-prompt">${esc(q.prompt)}</div>
              <div class="tf-answer">→ ${esc(q.shown)}</div>
              <div class="choices">
                <label class="choice-btn checkbox-label" style="display:flex"><input type="radio" name="q${i}" value="true"> <span>Prawda</span></label>
                <label class="choice-btn checkbox-label" style="display:flex"><input type="radio" name="q${i}" value="false"> <span>Fałsz</span></label>
              </div>
            `}
          </div>
        `).join("")}
        <button class="btn btn-primary btn-lg" type="submit">Zakończ i oceń test</button>
      </form>
    `;

    bindBack(set);

    document.getElementById("testForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const form = e.target;
      const results = ses.questions.map((q, i) => {
        const field = form.elements[`q${i}`];
        let userAnswer, ok;
        if (q.type === "choice") {
          const v = field.value !== "" ? Number(field.value) : -1;
          userAnswer = v >= 0 ? q.choices[v] : "(brak odpowiedzi)";
          ok = v >= 0 && q.choices[v] === q.answer;
        } else if (q.type === "write") {
          userAnswer = field.value.trim() || "(brak odpowiedzi)";
          ok = normalize(field.value) === normalize(q.answer);
        } else {
          const v = field.value;
          userAnswer = v === "true" ? "Prawda" : v === "false" ? "Fałsz" : "(brak odpowiedzi)";
          ok = v !== "" && (v === "true") === q.isTrue;
        }
        return { q, userAnswer, ok };
      });

      const correct = results.filter((r) => r.ok).length;
      const pct = Math.round((correct / results.length) * 100);

      renderResults(set, {
        title: "📝 Wynik testu",
        scoreText: `${pct}%`,
        scoreClass: pct >= 80 ? "good" : pct >= 50 ? "mid" : "bad",
        detail: `Poprawne odpowiedzi: ${correct} / ${results.length}.`,
        actions: [
          { label: "Nowy test", handler: () => renderTestConfig(set) },
          { label: "Wróć do zestawu", handler: () => go(`/set/${set.id}`) },
        ],
        reviewHtml: `
          <div class="review-list">
            ${results.map((r, i) => `
              <div class="review-item ${r.ok ? "ok" : "bad"}">
                <div class="q">${i + 1}. ${esc(r.q.prompt)}${r.q.type === "tf" ? ` → ${esc(r.q.shown)}` : ""}</div>
                <div class="a">Twoja odpowiedź: <b>${esc(r.userAnswer)}</b>${r.ok ? " ✓" : ` ✗ · poprawna: <b>${esc(r.q.type === "tf" ? (r.q.isTrue ? "Prawda" : "Fałsz") : r.q.answer)}</b>`}</div>
              </div>
            `).join("")}
          </div>
        `,
      });
    });
  }

  // ---------- DOPASOWANIE ----------

  let matchTimerId = null;

  function stopMatchTimer() {
    if (matchTimerId) { clearInterval(matchTimerId); matchTimerId = null; }
  }

  function renderMatch(set) {
    stopMatchTimer();
    const pairCount = Math.min(6, set.cards.length);
    const chosen = shuffle(set.cards).slice(0, pairCount);
    const tiles = shuffle(
      chosen.flatMap((c) => [
        { pairId: c.id, text: c.term, side: "term" },
        { pairId: c.id, text: c.def, side: "def" },
      ])
    );

    state.session = {
      kind: "match",
      setId: set.id,
      matchedCount: 0,
      pairCount,
      selected: null,
      penalty: 0,
      startedAt: null,
    };
    const ses = state.session;
    const best = loadBestTimes()[set.id];

    $app.innerHTML = `
      ${studyHeader(set, "⚡ Dopasowanie", "")}
      <div class="match-head">
        <div class="match-timer" id="matchTimer">0.0s</div>
        <div class="match-best">${best != null ? `Twój rekord: ${best.toFixed(1)}s` : "Zagraj, aby ustawić rekord!"} · błąd = +1s kary</div>
      </div>
      <div class="match-grid" id="matchGrid">
        ${tiles.map((t, i) => `<button class="match-tile" data-i="${i}" data-pair="${t.pairId}" data-side="${t.side}">${esc(t.text)}</button>`).join("")}
      </div>
    `;

    bindBack(set);

    const $timer = document.getElementById("matchTimer");
    const elapsed = () => (Date.now() - ses.startedAt) / 1000 + ses.penalty;

    function startTimer() {
      ses.startedAt = Date.now();
      matchTimerId = setInterval(() => {
        $timer.textContent = `${elapsed().toFixed(1)}s`;
      }, 100);
    }

    document.getElementById("matchGrid").addEventListener("click", (e) => {
      const tile = e.target.closest(".match-tile");
      if (!tile || tile.classList.contains("matched")) return;
      if (!ses.startedAt) startTimer();

      if (!ses.selected) {
        ses.selected = tile;
        tile.classList.add("selected");
        return;
      }
      if (ses.selected === tile) {
        tile.classList.remove("selected");
        ses.selected = null;
        return;
      }

      const a = ses.selected;
      ses.selected = null;
      a.classList.remove("selected");

      const isMatch = a.dataset.pair === tile.dataset.pair && a.dataset.side !== tile.dataset.side;
      if (isMatch) {
        a.classList.add("matched");
        tile.classList.add("matched");
        ses.matchedCount++;
        if (ses.matchedCount === ses.pairCount) {
          const finalTime = elapsed();
          stopMatchTimer();
          $timer.textContent = `${finalTime.toFixed(1)}s`;
          const isRecord = saveBestTime(set.id, Math.round(finalTime * 10) / 10);
          setTimeout(() => {
            renderResults(set, {
              title: "⚡ Dopasowanie ukończone!",
              scoreText: `${finalTime.toFixed(1)}s`,
              scoreClass: "good",
              detail: isRecord ? "🏆 Nowy rekord!" : `Twój rekord: ${loadBestTimes()[set.id].toFixed(1)}s`,
              actions: [
                { label: "Zagraj jeszcze raz", handler: () => renderMatch(set) },
                { label: "Wróć do zestawu", handler: () => go(`/set/${set.id}`) },
              ],
            });
          }, 450);
        }
      } else {
        ses.penalty += 1;
        [a, tile].forEach((el) => {
          el.classList.add("error");
          setTimeout(() => el.classList.remove("error"), 380);
        });
      }
    });
  }

  // ---------- EKRAN WYNIKÓW ----------

  function renderResults(set, { title, scoreText, scoreClass, detail, actions, reviewHtml = "" }) {
    state.session = null;
    stopMatchTimer();

    $app.innerHTML = `
      <button class="back-link" data-action="back">← ${esc(set.title)}</button>
      <div class="results-card">
        <h2>${title}</h2>
        <div class="score-big ${scoreClass}">${esc(scoreText)}</div>
        <p>${detail}</p>
        <div class="results-actions">
          ${actions.map((a, i) => `<button class="btn ${i === 0 ? "btn-primary" : "btn-ghost"} btn-lg" data-result-action="${i}">${esc(a.label)}</button>`).join("")}
        </div>
        ${reviewHtml}
      </div>
    `;

    bindBack(set);
    actions.forEach((a, i) => {
      $app.querySelector(`[data-result-action='${i}']`).addEventListener("click", a.handler);
    });
  }

  // ============================================================
  //  IMPORT / EKSPORT JSON
  // ============================================================

  function exportJson(sets, filename) {
    const payload = {
      app: "quizmaster",
      version: 1,
      exportedAt: new Date().toISOString(),
      sets,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename.replace(/[^\p{L}\p{N} ._-]/gu, "_");
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Wyeksportowano do pliku JSON");
  }

  function importJsonFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        const incoming = Array.isArray(data) ? data : data.sets;
        if (!Array.isArray(incoming)) throw new Error("bad format");

        let added = 0;
        for (const s of incoming) {
          if (!s || typeof s.title !== "string" || !Array.isArray(s.cards)) continue;
          const cards = s.cards
            .filter((c) => c && typeof c.term === "string" && typeof c.def === "string")
            .map((c) => ({ id: uid(), term: c.term, def: c.def, level: Number(c.level) || 0 }));
          if (cards.length === 0) continue;
          state.sets.push({
            id: uid(),
            title: s.title,
            description: typeof s.description === "string" ? s.description : "",
            cards,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          });
          added++;
        }
        if (added === 0) throw new Error("no sets");
        saveSets();
        toast(`Zaimportowano ${added} ${plural(added, "zestaw", "zestawy", "zestawów")}`);
        go("/");
        render();
      } catch (e) {
        toast("Nie udało się zaimportować pliku — nieprawidłowy format");
      }
    };
    reader.readAsText(file);
  }

  // ============================================================
  //  ZDARZENIA GLOBALNE
  // ============================================================

  document.getElementById("brandBtn").addEventListener("click", () => { go("/"); render(); });
  document.getElementById("newSetBtn").addEventListener("click", () => go("/edit/new"));
  document.getElementById("exportJsonBtn").addEventListener("click", () => {
    if (state.sets.length === 0) { toast("Brak zestawów do eksportu"); return; }
    exportJson(state.sets, "quizmaster-zestawy.json");
  });

  const fileInput = document.getElementById("importFileInput");
  document.getElementById("importJsonBtn").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) importJsonFile(fileInput.files[0]);
    fileInput.value = "";
  });

  // start
  saveSets(); // utrwal przykładowy zestaw przy pierwszym uruchomieniu
  render();
})();
