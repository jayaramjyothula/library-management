/**
 * app.js - Frontend Logic for Modern Library Management System
 * Unified shared interface (zero-login) with real-time REST API integration.
 */

(function () {
  "use strict";

  // Application State
  const state = {
    stats: {},
    books: [],
    categories: [],
    students: [],
    activeLoans: [],
    overdueLoans: [],
    allLoans: [],
    activity: [],
    filters: {
      search: "",
      category: "All",
      availability: "all", // 'all' | 'available' | 'borrowed'
    },
  };

  // Helper: DOM Selector
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => document.querySelectorAll(selector);

  // ---------------------------------------------------------------------------
  // Toast Notifications
  // ---------------------------------------------------------------------------
  function showToast(message, type = "success") {
    const container = $("#toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${type === "success" ? "✓" : "⚠"}</span>
      <span class="toast-msg">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(24px)";
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ---------------------------------------------------------------------------
  // API Fetch Helpers
  // ---------------------------------------------------------------------------
  async function apiGet(endpoint) {
    try {
      const res = await fetch(endpoint);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "API request failed");
      }
      return await res.json();
    } catch (e) {
      console.error(`Error in GET ${endpoint}:`, e);
      throw e;
    }
  }

  async function apiSend(endpoint, method, data) {
    try {
      const res = await fetch(endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: data ? JSON.stringify(data) : undefined,
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(json.detail || "Request failed");
      }
      return json;
    } catch (e) {
      console.error(`Error in ${method} ${endpoint}:`, e);
      throw e;
    }
  }

  // ---------------------------------------------------------------------------
  // Data Loading & Rendering
  // ---------------------------------------------------------------------------

  async function loadAllData() {
    await Promise.all([
      loadStats(),
      loadCategories(),
      loadBooks(),
      loadStudents(),
      loadLoans(),
      loadActivity(),
    ]);
  }

  async function loadStats() {
    try {
      const stats = await apiGet("/api/stats");
      state.stats = stats;
      $("#kpiTotalBooks").textContent = stats.total_books ?? 0;
      $("#kpiTotalCopies").textContent = `${stats.total_copies ?? 0} total physical copies`;
      $("#kpiAvailableCopies").textContent = stats.available_copies ?? 0;
      
      const availRate = stats.total_copies > 0
        ? Math.round((stats.available_copies / stats.total_copies) * 100)
        : 0;
      $("#kpiAvailabilityRate").textContent = `${availRate}% copies ready to issue`;

      $("#kpiActiveLoans").textContent = stats.borrowed_copies ?? 0;
      $("#kpiActiveStudents").textContent = `Across ${stats.total_students ?? 0} students`;

      $("#kpiOverdueLoans").textContent = stats.overdue_loans ?? 0;
      if (stats.overdue_loans > 0) {
        $("#kpiOverdueAlert").textContent = "Action required: overdue books";
        $("#kpiOverdueAlert").className = "metric-sub badge-overdue-alert";
      } else {
        $("#kpiOverdueAlert").textContent = "All loans in good standing";
        $("#kpiOverdueAlert").className = "metric-sub";
      }
    } catch (e) {
      console.error("Failed to load stats:", e);
    }
  }

  async function loadCategories() {
    try {
      const cats = await apiGet("/api/categories");
      state.categories = cats;

      // Populate Select Dropdown
      const select = $("#categoryFilter");
      select.innerHTML = '<option value="All">All Categories</option>';
      cats.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        select.appendChild(opt);
      });

      // Populate Pills
      const pillsBox = $("#categoryPillsContainer");
      pillsBox.innerHTML = `
        <button type="button" class="cat-pill active" data-category="All">All Categories</button>
      `;
      cats.forEach((c) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "cat-pill";
        btn.dataset.category = c;
        btn.textContent = c;
        pillsBox.appendChild(btn);
      });
    } catch (e) {
      console.error("Failed to load categories:", e);
    }
  }

  async function loadBooks() {
    try {
      const books = await apiGet("/api/books");
      state.books = books;
      renderBooks();
      updateIssueBookSelect();
    } catch (e) {
      console.error("Failed to load books:", e);
      $("#booksGrid").innerHTML = `
        <div class="empty-state">
          <h3>Failed to load catalogue</h3>
          <p>${escapeHtml(e.message)}</p>
          <button type="button" class="btn btn-secondary btn-sm" onclick="location.reload()">Retry</button>
        </div>
      `;
    }
  }

  function renderBooks() {
    const grid = $("#booksGrid");
    const emptyState = $("#booksEmptyState");
    const { search, category, availability } = state.filters;

    const filtered = state.books.filter((b) => {
      // Search filter
      if (search) {
        const q = search.toLowerCase();
        const matchTitle = b.title.toLowerCase().includes(q);
        const matchAuthor = b.author.toLowerCase().includes(q);
        const matchIsbn = b.isbn ? b.isbn.toLowerCase().includes(q) : false;
        const matchCat = b.category ? b.category.toLowerCase().includes(q) : false;
        if (!matchTitle && !matchAuthor && !matchIsbn && !matchCat) return false;
      }
      // Category filter
      if (category && category !== "All") {
        if (b.category !== category) return false;
      }
      // Availability filter
      if (availability === "available" && b.available_copies <= 0) return false;
      if (availability === "borrowed" && b.available_copies === b.total_copies) return false;

      return true;
    });

    if (filtered.length === 0) {
      grid.innerHTML = "";
      emptyState.classList.remove("hidden");
      return;
    }

    emptyState.classList.add("hidden");

    grid.innerHTML = filtered
      .map((b) => {
        const inStock = b.available_copies > 0;
        const percent = b.total_copies > 0
          ? Math.round((b.available_copies / b.total_copies) * 100)
          : 0;

        return `
          <div class="book-card" data-book-id="${b.id}">
            <div class="book-cover-banner">
              <span class="book-cat-badge">${escapeHtml(b.category)}</span>
              <span class="book-stock-pill ${inStock ? "stock-in" : "stock-out"}">
                ${inStock ? `${b.available_copies} In Stock` : "Checked Out"}
              </span>
            </div>
            
            <div class="book-card-body">
              <h3 class="book-title" title="${escapeHtml(b.title)}">${escapeHtml(b.title)}</h3>
              <p class="book-author">by ${escapeHtml(b.author)}</p>
              
              <div class="book-meta-row">
                <span class="book-isbn-tag">${b.isbn ? `ISBN: ${escapeHtml(b.isbn)}` : "No ISBN"}</span>
              </div>

              <div class="copies-status">
                <div class="copies-text-row">
                  <span>Available: ${b.available_copies} / ${b.total_copies}</span>
                  <span>${percent}%</span>
                </div>
                <div class="progress-track">
                  <div class="progress-fill ${b.available_copies === 0 ? "empty" : ""}" style="width: ${percent}%;"></div>
                </div>
              </div>

              <div class="book-card-actions">
                <button type="button" class="btn btn-primary btn-sm glow-hover btn-card-issue" 
                  data-book-id="${b.id}" ${inStock ? "" : "disabled title='No copies available'"}>
                  Issue
                </button>
                <button type="button" class="btn btn-secondary btn-sm btn-card-edit" data-book-id="${b.id}">
                  Edit
                </button>
                <button type="button" class="btn btn-secondary btn-sm btn-card-delete" data-book-id="${b.id}" title="Delete book">
                  ✕
                </button>
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  async function loadStudents() {
    try {
      const students = await apiGet("/api/students");
      state.students = students;
      renderStudents();
      updateIssueStudentSelect();
    } catch (e) {
      console.error("Failed to load students:", e);
    }
  }

  function renderStudents() {
    const grid = $("#studentsGrid");
    const badge = $("#studentCountBadge");
    const q = ($("#studentsSearchInput")?.value || "").toLowerCase().trim();

    const filtered = state.students.filter((s) => {
      if (!q) return true;
      return (
        s.name.toLowerCase().includes(q) ||
        s.student_id.toLowerCase().includes(q) ||
        s.email.toLowerCase().includes(q)
      );
    });

    badge.textContent = `${filtered.length} registered students`;

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <h3>No students found</h3>
          <p>No student records matched "${escapeHtml(q)}".</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = filtered
      .map((s) => {
        const initials = s.name
          .split(" ")
          .map((n) => n[0])
          .slice(0, 2)
          .join("")
          .toUpperCase();

        return `
          <div class="student-card glow-card">
            <div class="student-header">
              <div class="student-avatar">${initials}</div>
              <div>
                <h4 class="student-name">${escapeHtml(s.name)}</h4>
                <span class="student-code-badge">${escapeHtml(s.student_id)}</span>
              </div>
            </div>
            
            <p class="student-email">${escapeHtml(s.email)}</p>

            <div class="student-loans-count">
              <span>Active Loans</span>
              <span class="status-badge ${s.active_loans_count > 0 ? "status-issued" : ""}">
                ${s.active_loans_count || 0} books
              </span>
            </div>

            <button type="button" class="btn btn-secondary btn-sm btn-student-history" data-student-id="${s.id}" data-student-name="${escapeHtml(s.name)}">
              Borrowing History
            </button>
          </div>
        `;
      })
      .join("");
  }

  async function loadLoans() {
    try {
      const [active, overdue, all] = await Promise.all([
        apiGet("/api/loans/active"),
        apiGet("/api/loans/overdue"),
        apiGet("/api/loans"),
      ]);
      state.activeLoans = active;
      state.overdueLoans = overdue;
      state.allLoans = all;

      $("#activeLoansCountBadge").textContent = active.length;
      $("#overdueCountBadge").textContent = overdue.length;

      renderActiveLoans();
      renderOverdueLoans();
      renderAllLoans();
    } catch (e) {
      console.error("Failed to load loans:", e);
    }
  }

  function renderActiveLoans() {
    const tbody = $("#activeLoansTableBody");
    const q = ($("#activeLoansSearch")?.value || "").toLowerCase().trim();

    const filtered = state.activeLoans.filter((l) => {
      if (!q) return true;
      return (
        l.book_title.toLowerCase().includes(q) ||
        l.student_name.toLowerCase().includes(q) ||
        l.student_code.toLowerCase().includes(q)
      );
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center" style="padding: 40px; color: var(--text-muted); text-align: center;">
            No active loans found. All borrowed books have been returned.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filtered
      .map((l) => {
        const isOverdue = l.is_overdue;
        return `
          <tr>
            <td>
              <strong>${escapeHtml(l.book_title)}</strong>
              <div style="font-size: 0.8rem; color: var(--text-muted);">by ${escapeHtml(l.book_author || "")}</div>
            </td>
            <td>
              <div>${escapeHtml(l.student_name)}</div>
              <span class="student-code-badge">${escapeHtml(l.student_code)}</span>
            </td>
            <td>${l.issue_date}</td>
            <td>
              <strong>${l.due_date}</strong>
            </td>
            <td>
              ${
                isOverdue
                  ? `<span class="status-badge status-overdue">⚠ Overdue (${l.days_overdue}d)</span>`
                  : `<span class="status-badge status-issued">Active</span>`
              }
            </td>
            <td class="text-right">
              <button type="button" class="btn btn-secondary btn-sm glow-hover btn-return-loan" 
                data-loan-id="${l.id}" data-book-title="${escapeHtml(l.book_title)}" data-student-name="${escapeHtml(l.student_name)}">
                Return Book
              </button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function renderOverdueLoans() {
    const tbody = $("#overdueLoansTableBody");
    const loans = state.overdueLoans;

    if (loans.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="padding: 40px; color: var(--text-muted); text-align: center;">
            ✓ Great news! Zero overdue loans currently on record.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = loans
      .map((l) => {
        return `
          <tr>
            <td>
              <strong>${escapeHtml(l.book_title)}</strong>
              <div style="font-size: 0.8rem; color: var(--text-muted);">by ${escapeHtml(l.book_author || "")}</div>
            </td>
            <td>
              <div>${escapeHtml(l.student_name)}</div>
              <span class="student-code-badge">${escapeHtml(l.student_code)}</span>
            </td>
            <td>${l.issue_date}</td>
            <td><strong>${l.due_date}</strong></td>
            <td>
              <span class="status-badge status-overdue">${l.days_overdue} days overdue</span>
            </td>
            <td class="text-right">
              <button type="button" class="btn btn-danger btn-sm glow-hover btn-return-loan" 
                data-loan-id="${l.id}" data-book-title="${escapeHtml(l.book_title)}" data-student-name="${escapeHtml(l.student_name)}">
                Return Book
              </button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function renderAllLoans() {
    const tbody = $("#allLoansTableBody");
    const q = ($("#historyLoansSearch")?.value || "").toLowerCase().trim();
    const statusFilter = $("#historyStatusFilter")?.value || "All";

    const filtered = state.allLoans.filter((l) => {
      if (statusFilter !== "All" && l.status !== statusFilter) return false;
      if (q) {
        const matchTitle = l.book_title.toLowerCase().includes(q);
        const matchStudent = l.student_name.toLowerCase().includes(q);
        const matchCode = l.student_code.toLowerCase().includes(q);
        if (!matchTitle && !matchStudent && !matchCode) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="padding: 30px; text-align: center; color: var(--text-muted);">
            No records matched your query.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filtered
      .map((l) => {
        let badgeClass = "status-issued";
        if (l.status === "RETURNED") badgeClass = "status-returned";
        else if (l.is_overdue) badgeClass = "status-overdue";

        return `
          <tr>
            <td><strong>${escapeHtml(l.book_title)}</strong></td>
            <td>${escapeHtml(l.student_name)} (${escapeHtml(l.student_code)})</td>
            <td>${l.issue_date || "-"}</td>
            <td>${l.due_date || "-"}</td>
            <td>${l.return_date || "-"}</td>
            <td>
              <span class="status-badge ${badgeClass}">${l.status}</span>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  async function loadActivity() {
    try {
      const activity = await apiGet("/api/activity");
      state.activity = activity;
      const container = $("#activityTimeline");

      if (!activity || activity.length === 0) {
        container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">No recent transactions.</div>`;
        return;
      }

      container.innerHTML = activity
        .map((a) => {
          const isRet = a.status === "RETURNED";
          return `
            <div class="activity-item">
              <span class="activity-dot ${isRet ? "dot-returned" : ""}"></span>
              <div class="activity-content">
                <span class="activity-text">
                  <strong>${escapeHtml(a.student_name)}</strong> 
                  ${isRet ? "returned" : "borrowed"} 
                  <em>'${escapeHtml(a.book_title)}'</em>
                </span>
                <span class="activity-time">${a.created_at || a.issue_date} • Status: ${a.status}</span>
              </div>
            </div>
          `;
        })
        .join("");
    } catch (e) {
      console.error("Failed to load activity:", e);
    }
  }

  function updateIssueStudentSelect() {
    const select = $("#issueStudentSelect");
    if (!select) return;
    select.innerHTML = '<option value="">-- Choose Student --</option>';
    state.students.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `${s.name} (${s.student_id}) - ${s.email}`;
      select.appendChild(opt);
    });
  }

  function updateIssueBookSelect(preselectedBookId = null) {
    const select = $("#issueBookSelect");
    if (!select) return;
    select.innerHTML = '<option value="">-- Choose Book --</option>';
    
    const availableBooks = state.books.filter((b) => b.available_copies > 0);
    availableBooks.forEach((b) => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = `${b.title} (${b.available_copies} copies available)`;
      if (preselectedBookId && b.id === preselectedBookId) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    const hint = $("#issueBookAvailabilityHint");
    if (availableBooks.length === 0) {
      hint.textContent = "No books currently have available copies in stock.";
      hint.style.color = "var(--rose-600)";
    } else {
      hint.textContent = `${availableBooks.length} titles currently in stock ready to borrow.`;
      hint.style.color = "var(--text-muted)";
    }
  }

  // ---------------------------------------------------------------------------
  // Modal Handlers
  // ---------------------------------------------------------------------------
  function openModal(id) {
    const el = $(`#${id}`);
    if (el) el.classList.remove("hidden");
  }

  function closeModal(id) {
    const el = $(`#${id}`);
    if (el) el.classList.add("hidden");
  }

  // ---------------------------------------------------------------------------
  function setupEventListeners() {
    // 1. Navigation Menu Links, Mobile Toggle, and Sticky Header Scroll Spy
    const siteHeader = $(".site-header");
    const sections = Array.from($$("main section[id]"));
    const navLinks = Array.from($$(".nav-link"));

    let isClickScrolling = false;
    let clickScrollTimer = null;

    navLinks.forEach((link) => {
      link.addEventListener("click", () => {
        isClickScrolling = true;
        clearTimeout(clickScrollTimer);
        navLinks.forEach((l) => l.classList.remove("active"));
        link.classList.add("active");
        $("#navMenu")?.classList.remove("mobile-open");
        clickScrollTimer = setTimeout(() => {
          isClickScrolling = false;
        }, 800);
      });
    });

    function handleScroll() {
      const scrollPos = window.scrollY || window.pageYOffset || document.documentElement.scrollTop;

      // Header elevation shadow on scroll
      if (siteHeader) {
        if (scrollPos > 12) {
          siteHeader.classList.add("scrolled");
        } else {
          siteHeader.classList.remove("scrolled");
        }
      }

      // Dynamic nav pill update during mouse wheel scroll
      if (!isClickScrolling && sections.length > 0) {
        const viewportMarker = scrollPos + 120;
        let activeSectionId = "hero";

        for (const section of sections) {
          const top = section.offsetTop;
          const height = section.offsetHeight;
          if (viewportMarker >= top && viewportMarker < top + height) {
            activeSectionId = section.getAttribute("id");
            break;
          }
        }

        navLinks.forEach((link) => {
          const href = link.getAttribute("href")?.replace("#", "");
          if (href === activeSectionId) {
            link.classList.add("active");
          } else {
            link.classList.remove("active");
          }
        });
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    $("#mobileMenuBtn")?.addEventListener("click", () => {
      $("#navMenu")?.classList.toggle("mobile-open");
    });

    // 2. Hero Search Bar
    function triggerHeroSearch() {
      const val = $("#heroSearchInput").value.trim();
      state.filters.search = val;
      $("#catalogueSearchInput").value = val;
      renderBooks();

      const catSection = $("#catalogue");
      if (catSection) {
        catSection.scrollIntoView({ behavior: "smooth" });
      }
    }

    $("#heroSearchBtn")?.addEventListener("click", triggerHeroSearch);
    $("#heroSearchInput")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") triggerHeroSearch();
    });

    // 3. Quick Action Buttons in Hero & Navbar
    $("#qaBrowse")?.addEventListener("click", () => {
      $("#catalogue").scrollIntoView({ behavior: "smooth" });
    });

    $("#qaAddBook")?.addEventListener("click", () => openModal("modalAddBook"));
    $("#btnAddBook")?.addEventListener("click", () => openModal("modalAddBook"));
    $("#btnCatalogueAdd")?.addEventListener("click", () => openModal("modalAddBook"));

    $("#qaIssueBook")?.addEventListener("click", () => {
      switchCirculationTab("issueForm");
      $("#circulation").scrollIntoView({ behavior: "smooth" });
    });

    $("#btnQuickIssue")?.addEventListener("click", () => {
      switchCirculationTab("issueForm");
      $("#circulation").scrollIntoView({ behavior: "smooth" });
    });

    $("#btnIssueBookTab")?.addEventListener("click", () => {
      switchCirculationTab("issueForm");
    });

    $("#qaReturnBook")?.addEventListener("click", () => {
      switchCirculationTab("activeLoans");
      $("#circulation").scrollIntoView({ behavior: "smooth" });
    });

    // 4. Catalogue Filters
    $("#catalogueSearchInput")?.addEventListener("input", (e) => {
      state.filters.search = e.target.value.trim();
      renderBooks();
    });

    $("#clearCatalogueSearch")?.addEventListener("click", () => {
      $("#catalogueSearchInput").value = "";
      state.filters.search = "";
      renderBooks();
    });

    $("#categoryFilter")?.addEventListener("change", (e) => {
      state.filters.category = e.target.value;
      $$(".cat-pill").forEach((p) => {
        p.classList.toggle("active", p.dataset.category === e.target.value);
      });
      renderBooks();
    });

    document.addEventListener("click", (e) => {
      const pill = e.target.closest(".cat-pill");
      if (pill) {
        const cat = pill.dataset.category;
        state.filters.category = cat;
        $("#categoryFilter").value = cat;
        $$(".cat-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        renderBooks();
      }
    });

    $$(".avail-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".avail-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.filters.availability = btn.dataset.avail;
        renderBooks();
      });
    });

    $("#btnResetFilters")?.addEventListener("click", () => {
      state.filters.search = "";
      state.filters.category = "All";
      state.filters.availability = "all";
      $("#catalogueSearchInput").value = "";
      $("#categoryFilter").value = "All";
      $$(".cat-pill").forEach((p) => p.classList.toggle("active", p.dataset.category === "All"));
      $$(".avail-btn").forEach((b) => b.classList.toggle("active", b.dataset.avail === "all"));
      renderBooks();
    });

    // 5. Book Card Actions (Issue, Edit, Delete via Event Delegation)
    $("#booksGrid")?.addEventListener("click", async (e) => {
      // Issue Button
      const issueBtn = e.target.closest(".btn-card-issue");
      if (issueBtn && !issueBtn.disabled) {
        const bookId = parseInt(issueBtn.dataset.bookId, 10);
        updateIssueBookSelect(bookId);
        switchCirculationTab("issueForm");
        $("#circulation").scrollIntoView({ behavior: "smooth" });
        return;
      }

      // Edit Button
      const editBtn = e.target.closest(".btn-card-edit");
      if (editBtn) {
        const bookId = parseInt(editBtn.dataset.bookId, 10);
        const book = state.books.find((b) => b.id === bookId);
        if (book) {
          $("#editBookId").value = book.id;
          $("#editBookTitle").value = book.title;
          $("#editBookAuthor").value = book.author;
          $("#editBookCategory").value = book.category;
          $("#editBookCopies").value = book.total_copies;
          $("#editBookISBN").value = book.isbn || "";
          
          const borrowed = book.total_copies - book.available_copies;
          $("#editCopiesHint").textContent = borrowed > 0
            ? `Note: ${borrowed} copy(ies) are currently loaned out. Total copies cannot be reduced below ${borrowed}.`
            : "";
          openModal("modalEditBook");
        }
        return;
      }

      // Delete Button
      const delBtn = e.target.closest(".btn-card-delete");
      if (delBtn) {
        const bookId = parseInt(delBtn.dataset.bookId, 10);
        const book = state.books.find((b) => b.id === bookId);
        if (!book) return;

        if (book.available_copies < book.total_copies) {
          showToast(`Cannot delete '${book.title}': active loans exist for this book.`, "error");
          return;
        }

        if (confirm(`Are you sure you want to delete '${book.title}'? This action cannot be undone.`)) {
          try {
            const res = await apiSend(`/api/books/${bookId}`, "DELETE");
            showToast(res.message || "Book deleted successfully!");
            await Promise.all([loadBooks(), loadStats()]);
          } catch (err) {
            showToast(err.message || "Failed to delete book", "error");
          }
        }
      }
    });

    // 6. Circulation Tabs Switching
    $$(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        switchCirculationTab(btn.dataset.tab);
      });
    });

    function switchCirculationTab(tabName) {
      $$(".tab-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.tab === tabName);
      });

      const tabMap = {
        activeLoans: "tabActiveLoans",
        overdueLoans: "tabOverdueLoans",
        issueForm: "tabIssueForm",
        loanHistory: "tabLoanHistory",
      };

      $$(".tab-panel").forEach((p) => p.classList.add("hidden"));
      const targetPanel = $(`#${tabMap[tabName]}`);
      if (targetPanel) targetPanel.classList.remove("hidden");
    }

    $("#activeLoansSearch")?.addEventListener("input", renderActiveLoans);
    $("#btnRefreshLoans")?.addEventListener("click", async () => {
      await loadLoans();
      showToast("Circulation records refreshed.");
    });
    $("#historyLoansSearch")?.addEventListener("input", renderAllLoans);
    $("#historyStatusFilter")?.addEventListener("change", renderAllLoans);

    // 7. Return Book Action (from tables)
    document.addEventListener("click", (e) => {
      const retBtn = e.target.closest(".btn-return-loan");
      if (retBtn) {
        const loanId = retBtn.dataset.loanId;
        const bookTitle = retBtn.dataset.bookTitle;
        const studentName = retBtn.dataset.studentName;

        $("#returnLoanId").value = loanId;
        $("#returnBookDetailsText").innerHTML = `
          Returning <strong>'${escapeHtml(bookTitle)}'</strong> borrowed by <strong>${escapeHtml(studentName)}</strong>.
        `;
        $("#returnDateInput").value = new Date().toISOString().slice(0, 10);
        openModal("modalReturnBook");
      }
    });

    // 8. Duration Presets in Issue Form
    $$(".preset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".preset-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const days = parseInt(btn.dataset.days, 10);
        const issueDateVal = $("#issueDateInput").value || new Date().toISOString().slice(0, 10);
        const d = new Date(issueDateVal);
        d.setDate(d.getDate() + days);
        $("#dueDateInput").value = d.toISOString().slice(0, 10);
      });
    });

    // Initialize Default Dates in Issue Form
    const todayStr = new Date().toISOString().slice(0, 10);
    const in14Days = new Date();
    in14Days.setDate(in14Days.getDate() + 14);
    if ($("#issueDateInput")) $("#issueDateInput").value = todayStr;
    if ($("#dueDateInput")) $("#dueDateInput").value = in14Days.toISOString().slice(0, 10);

    // 9. Form Submissions
    // Add Book Form
    $("#formAddBook")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = $("#addBookTitle").value.trim();
      const author = $("#addBookAuthor").value.trim();
      const category = $("#addBookCategory").value.trim();
      const total_copies = parseInt($("#addBookCopies").value, 10);
      const isbn = $("#addBookISBN").value.trim() || null;

      try {
        const res = await apiSend("/api/books", "POST", {
          title,
          author,
          category,
          total_copies,
          isbn,
        });
        showToast(res.message || "Book added successfully!");
        closeModal("modalAddBook");
        e.target.reset();
        await Promise.all([loadBooks(), loadCategories(), loadStats()]);
      } catch (err) {
        showToast(err.message || "Failed to add book", "error");
      }
    });

    // Edit Book Form
    $("#formEditBook")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const bookId = parseInt($("#editBookId").value, 10);
      const title = $("#editBookTitle").value.trim();
      const author = $("#editBookAuthor").value.trim();
      const category = $("#editBookCategory").value.trim();
      const total_copies = parseInt($("#editBookCopies").value, 10);
      const isbn = $("#editBookISBN").value.trim() || null;

      try {
        const res = await apiSend(`/api/books/${bookId}`, "PUT", {
          title,
          author,
          category,
          total_copies,
          isbn,
        });
        showToast(res.message || "Book updated successfully!");
        closeModal("modalEditBook");
        await Promise.all([loadBooks(), loadCategories(), loadStats()]);
      } catch (err) {
        showToast(err.message || "Failed to update book", "error");
      }
    });

    // Issue Book Form
    $("#issueBookForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const studentId = parseInt($("#issueStudentSelect").value, 10);
      const bookId = parseInt($("#issueBookSelect").value, 10);
      const issueDate = $("#issueDateInput").value;
      const dueDate = $("#dueDateInput").value;

      if (!studentId || !bookId) {
        showToast("Please choose both a student and an available book.", "error");
        return;
      }

      try {
        const res = await apiSend("/api/loans/issue", "POST", {
          student_id: studentId,
          book_id: bookId,
          issue_date: issueDate,
          due_date: dueDate,
        });
        showToast(res.message || "Book issued successfully!");
        await Promise.all([loadBooks(), loadLoans(), loadStats(), loadActivity(), loadStudents()]);
        switchCirculationTab("activeLoans");
      } catch (err) {
        showToast(err.message || "Failed to issue book", "error");
      }
    });

    // Return Book Form
    $("#formReturnBook")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const loanId = parseInt($("#returnLoanId").value, 10);
      const returnDate = $("#returnDateInput").value;

      try {
        const res = await apiSend("/api/loans/return", "POST", {
          loan_id: loanId,
          return_date: returnDate,
        });
        showToast(res.message || "Book returned successfully!");
        closeModal("modalReturnBook");
        await Promise.all([loadBooks(), loadLoans(), loadStats(), loadActivity(), loadStudents()]);
      } catch (err) {
        showToast(err.message || "Failed to process return", "error");
      }
    });

    // Register Student Modal & Form
    $("#btnAddStudent")?.addEventListener("click", () => openModal("modalAddStudent"));
    $("#linkQuickStudent")?.addEventListener("click", (e) => {
      e.preventDefault();
      openModal("modalAddStudent");
    });

    $("#formAddStudent")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const student_id = $("#studentIdInput").value.trim();
      const name = $("#studentNameInput").value.trim();
      const email = $("#studentEmailInput").value.trim();

      try {
        const res = await apiSend("/api/students", "POST", {
          student_id,
          name,
          email,
        });
        showToast(res.message || "Student registered successfully!");
        closeModal("modalAddStudent");
        e.target.reset();
        await loadStudents();
      } catch (err) {
        showToast(err.message || "Failed to register student", "error");
      }
    });

    // Student Search & History
    $("#studentsSearchInput")?.addEventListener("input", renderStudents);
    $("#clearStudentSearch")?.addEventListener("click", () => {
      $("#studentsSearchInput").value = "";
      renderStudents();
    });

    document.addEventListener("click", async (e) => {
      const histBtn = e.target.closest(".btn-student-history");
      if (histBtn) {
        const studentId = histBtn.dataset.studentId;
        const studentName = histBtn.dataset.studentName;
        $("#historyModalTitle").textContent = `${studentName}'s Borrowing History`;
        $("#historyModalSubtitle").textContent = `Full audit trail for student record ID #${studentId}`;

        try {
          const history = await apiGet(`/api/students/${studentId}/history`);
          const tbody = $("#studentHistoryTableBody");
          if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 24px; color: var(--text-muted);">No borrowing records on file for this student.</td></tr>`;
          } else {
            tbody.innerHTML = history
              .map((h) => `
                <tr>
                  <td><strong>${escapeHtml(h.book_title)}</strong></td>
                  <td>${h.issue_date || "-"}</td>
                  <td>${h.due_date || "-"}</td>
                  <td>${h.return_date || "-"}</td>
                  <td>
                    <span class="status-badge ${h.status === "RETURNED" ? "status-returned" : "status-issued"}">
                      ${h.status}
                    </span>
                  </td>
                </tr>
              `)
              .join("");
          }
          openModal("modalStudentHistory");
        } catch (err) {
          showToast("Failed to load student history: " + err.message, "error");
        }
      }
    });

    // Modal Close Buttons & Backdrop Clicks
    $$("[data-close]").forEach((btn) => {
      btn.addEventListener("click", () => {
        closeModal(btn.dataset.close);
      });
    });

    $$(".modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) {
          backdrop.classList.add("hidden");
        }
      });
    });

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        $$(".modal-backdrop").forEach((m) => m.classList.add("hidden"));
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Application Entry Point
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    setupEventListeners();
    await loadAllData();
  });
})();
