# 📚 Library Management System

A high-performance, modern, and aesthetically refined **Library Management System** with a unified shared interface (zero-login) designed for college project demonstrations. Featuring an editorial design inspired by **Swiggy, Google Gemini, and modern SaaS products**, vibrant electric cyan/blue hover glow effects, atomic SQLite transactions, dynamic real-time analytics, and instant issue/return workflows.

---

## 🌟 Key Highlights & Design System

### 1. 🚀 Unified Entry Point (Zero Login Screens)
- **Direct Access**: No admin/student login screens, credentials prompts, or role selection barriers. Anyone visiting the website enters the full library workspace immediately.
- **Single Cohesive Interface**: Seamlessly merges catalog exploration, circulation desk operations, student directory tracking, and system activity logs into one shared workspace.

### 2. 🎨 Modern SaaS & Editorial Aesthetic
- **Inspiration**: Visual elegance and simplicity drawn from Swiggy, Google Gemini, and modern SaaS products.
- **Color Palette**:
  - **Surfaces**: Crisp warm white (`#f8fafc`, `#ffffff`) and soft neutral card surfaces.
  - **Primary**: Rich midnight navy (`#0b132b`, `#0f172a`).
  - **Accents**: Premium electric cyan and blue (`#0284c7`, `#0ea5e9`, `#38bdf8`) with smooth glowing ambient backdrops.
  - **Typography**: Modern Google Fonts (**Plus Jakarta Sans** for headings, **Inter** for body text and data tables).
- **Interactive Hover Glow Effects**:
  - Buttons smoothly elevate (`translateY(-2px)`) with glowing cyan aura (`box-shadow: 0 0 22px rgba(14, 165, 233, 0.42)`).
  - Search inputs and form fields feature polished focus rings with glowing edges.
  - Book and metric cards elevate (`translateY(-4px)`) with subtle cyan border illumination.
  - Butter-smooth `200ms` cubic-bezier transitions with full `prefers-reduced-motion` accessibility support.

### 3. 📖 Full-Featured Library Management
- **Hero Section**: Prominent live search bar with instant autocomplete and quick action buttons (*Browse Books*, *Add Book*, *Issue Book*, *Return Book*).
- **Real-Time KPI Cards**: Total Books, Available Copies, Active Loans, and Overdue Loans dynamically computed directly from SQLite.
- **Book Catalogue**:
  - Responsive book cards with subject category badges, stock pills, and copy progress bars.
  - Real-time search, category filters, and availability toggles (*All*, *In Stock*, *Checked Out*).
  - Add, edit, and safe delete operations (deletion blocked while active loans exist).
  - **Optional ISBN**: Full support for books with or without an ISBN; duplicate enforcement applies only when an ISBN is provided.
- **Circulation Desk**:
  - Instant Issue Book workflow with student selector, book availability validation, and customizable loan duration presets (+7, +14, +28 days).
  - Active Loans table with borrower details, issue dates, due dates, and highlighted overdue warnings with day counters.
  - 1-click Return Book action with date recording and automatic copy restoration.
- **Student Directory**:
  - Searchable directory showing student roll numbers, emails, and active loan counts.
  - Direct student registration form.
  - Interactive "Borrowing History" audit modal showing full borrowing timelines.
- **Activity & Reports**:
  - Live timeline of recent borrow and return transactions.
  - 1-click CSV export of the complete circulation audit trail.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend & REST API** | Python 3.10+, FastAPI, Uvicorn |
| **Database Layer** | SQLite3 (WAL mode, Foreign Keys ON, Atomic ACID Transactions) |
| **Modern Frontend** | HTML5, CSS3 (Custom Design System & Glowing Shaders), Vanilla ES6+ JavaScript |
| **Alternative Frontend** | Streamlit (Unified Zero-Login interface supported via `streamlit run app.py`) |
| **Data & Testing** | Pandas, Requests, Unittest |

---

## 📂 Project Structure

```text
LIBRARY MANAGEMENT/
│
├── server.py               # FastAPI REST API & static web server (Serves port 8501)
├── app.py                  # Dual-mode launcher (runs FastAPI web app or Streamlit)
├── database.py             # SQLite database layer, migrations, and atomic transactions
├── library.db              # Persistent SQLite database file
├── requirements.txt        # Project dependencies (fastapi, uvicorn, requests, streamlit, pandas)
├── README.md               # Comprehensive project documentation
├── test_web_api.py         # End-to-end integration tests for REST API & web workflows
├── test_app.py             # Streamlit AppTest integration tests for zero-login interface
├── test_database.py        # Database constraint & transaction unit tests
├── test_live_features.py   # Step-by-step verification of all 7 core college requirements
├── verify_project.py       # Isolated database verification across 8 lifecycle stages
│
└── static/                 # Modern Frontend Web Assets
    ├── index.html          # High-fidelity single-page web interface (Hero, Grid, Modals)
    ├── styles.css          # Design system, Google fonts, cyan hover glow, responsive layouts
    └── app.js              # Vanilla JS frontend state, live search, modals, and toasts
```

---

## 🚀 Quickstart: How to Run the Website

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Launch the Application
Run either of the following commands from the project directory:

**Primary (Modern Web Website — Recommended):**
```bash
python app.py
```
*(or `python server.py`)*

**Alternative (Streamlit Zero-Login Interface):**
```bash
streamlit run app.py
```

### Step 3: Open in Browser
Open your web browser and navigate to:
👉 **`http://localhost:8501`**

---

## 🧪 Automated Test Verification

All automated test suites can be executed directly from terminal:

```bash
# 1. Test REST API, book lifecycle, and CSV export
python test_web_api.py

# 2. Test Streamlit zero-login interface & metrics
python test_app.py

# 3. Test core SQLite constraints and transactions
python -m unittest test_database.py

# 4. Test live 7 core college features against SQLite
python test_live_features.py

# 5. Full end-to-end verification across 8 lifecycle stages
python verify_project.py
```

---

## ☁️ Free Cloud Hosting Guide: Streamlit Community Cloud

Follow these beginner-friendly steps to host this application online for free:

### 1. Which Files to Upload to GitHub
Upload all project files to a new GitHub repository:
- `app.py` (Main application entry point)
- `database.py` (SQLite database engine and queries)
- `requirements.txt` (Dependencies list)
- `README.md` (Project documentation)
- `server.py` & `static/` folder (Modern web UI files)
- `library.db` (Optional: upload to preserve your exact current local records; if omitted, the app automatically initializes and seeds sample catalog books upon cloud startup!)

*(Do NOT upload: `venv/`, `__pycache__/`, `.env`)*

### 2. Push Project to GitHub

#### Option A: Using Git CLI in Terminal
```bash
git init
git add .
git commit -m "Initial commit of Library Management System"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/library-management.git
git push -u origin main
```

#### Option B: Using GitHub Web UI (Zero CLI)
1. Go to [github.com/new](https://github.com/new) and create a new **Public** repository named `library-management`.
2. Click **"uploading an existing file"**.
3. Drag and drop all project files into the browser and click **Commit changes**.

### 3. Deploy on Streamlit Community Cloud (100% Free)
1. Visit **[share.streamlit.io](https://share.streamlit.io)** and sign in with your GitHub account.
2. Click the **"New app"** button.
3. Fill in the deployment form:
   - **Repository**: Select your `library-management` repository.
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL** (Optional): Choose a custom subdomain (e.g. `yourname-library.streamlit.app`).
4. Click **"Deploy!"**.
5. Within 1-2 minutes, your Library Management System will be live with a shareable public URL!

### 4. How SQLite Works on Streamlit Cloud
- **Initial Startup**: The application runs in an isolated container. On first boot, `database.py` automatically initializes tables and pre-seeds sample books, students, and loans.
- **Active Sessions**: All book additions, edits, loans, and returns work dynamically and persist in `library.db` during user interactions.
- **Container Lifecycle**: Streamlit Cloud containers are ephemeral (rebooted upon idle sleep or new code commits). If the container reboots, it restores from the latest GitHub repository state. For college project submissions and evaluator grading, this ensures a clean, reliable, working state every time the evaluator opens the link.

