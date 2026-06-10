# AutoCareer Technology Stack

This document explains the technology choices for AutoCareer and the rationale behind each decision.

## Table of Contents

1. [Frontend Technologies](#frontend-technologies)
2. [Backend Technologies](#backend-technologies)
3. [AI & Machine Learning](#ai--machine-learning)
4. [Scraping & Automation](#scraping--automation)
5. [Database Technologies](#database-technologies)
6. [PDF Generation](#pdf-generation)
7. [DevOps & Infrastructure](#devops--infrastructure)

---

## Frontend Technologies

### Next.js 14 (App Router)

**What It Is**: React framework with server-side rendering, file-based routing, and server components.

**Why Chosen**:

1. **App Router Architecture**: Next.js 14's App Router provides:
   - File-based routing (`app/dashboard/page.tsx` → `/dashboard`)
   - Server components by default (reduced JavaScript bundle size)
   - Built-in API routes (not used in this project, but available for future)
   - Streaming SSR for faster initial page loads

2. **Developer Experience**: 
   - Zero-config setup with sensible defaults
   - Fast Refresh for instant feedback during development
   - TypeScript support out of the box
   - Automatic code splitting per route

3. **Performance Optimizations**:
   - Image optimization with `next/image`
   - Automatic static optimization for pages without server data
   - Prefetching of linked pages on hover
   - Edge runtime support for global deployment (future-proofing)

4. **SEO & Accessibility**:
   - Server-side rendering enables proper meta tags
   - Built-in `<head>` management
   - Accessibility warnings during development

**Alternatives Considered**:
- **Create React App**: Deprecated, no longer maintained
- **Vite + React Router**: More manual configuration required
- **Remix**: Similar to Next.js App Router, but smaller ecosystem

**Trade-offs**:
- **Learning Curve**: App Router is new (2023), different from Pages Router
- **Bundle Size**: Next.js framework adds ~80KB gzipped
- **Overkill for Simple Apps**: For AutoCareer's dashboard-focused UI, a SPA might suffice, but Next.js provides room to grow (e.g., public job board, marketing pages)

---

### React 19

**What It Is**: JavaScript library for building user interfaces with component-based architecture.

**Why Chosen**:

1. **Industry Standard**: 
   - Largest ecosystem of components and libraries
   - Extensive documentation and community support
   - Well-understood patterns (hooks, context, effects)

2. **Hooks Simplicity**: 
   - `useState` for local state (job lists, form inputs)
   - `useEffect` for polling and side effects
   - No need for complex state management (Redux) given app size

3. **Component Reusability**:
   - Button, Card, Badge components used across all pages
   - shadcn/ui provides pre-built React components
   - Easy to share logic via custom hooks

4. **React 19 Features** (Future):
   - Server Actions for form submissions
   - Suspense for async components
   - Use hook for async state management

**Alternatives Considered**:
- **Vue 3**: Easier learning curve, but smaller ecosystem
- **Svelte**: Smaller bundle, but less mature tooling
- **Angular**: Full framework, overkill for this use case

**Trade-offs**:
- **Boilerplate**: More verbose than Vue/Svelte (JSX, explicit state)
- **Re-renders**: Requires careful `useEffect` dependencies to avoid loops
- **No Built-in State Management**: Need external library for complex state (though AutoCareer doesn't require it)

---

### TypeScript

**What It Is**: Superset of JavaScript with static type checking.

**Why Chosen**:

1. **Type Safety for API Calls**:
   ```typescript
   // Compile-time error if API response shape changes
   interface Job {
     id: number;
     title: string;
     score?: number;  // Optional field
   }
   
   const jobs: Job[] = await getJobs();
   // TypeScript prevents accessing jobs[0].nonexistent_field
   ```

2. **Better IDE Support**:
   - Autocomplete for API client functions
   - Jump to definition for component props
   - Inline documentation via JSDoc comments
   - Refactoring tools (rename symbol across files)

3. **Fewer Runtime Errors**:
   - Catches null/undefined access before deployment
   - Prevents passing wrong prop types to components
   - Enforces consistent data structures

4. **Self-Documenting Code**:
   ```typescript
   function applyToJob(jobId: number, resume: File): Promise<ApplicationStatus>
   // Clear contract: takes number + File, returns Promise<ApplicationStatus>
   ```

**Alternatives Considered**:
- **JavaScript (plain)**: Faster to write, but error-prone in larger codebases
- **Flow**: Facebook's type checker, less popular than TypeScript
- **JSDoc comments**: Lightweight type hints, but not enforced

**Trade-offs**:
- **Build Step Required**: Need to compile TypeScript → JavaScript
- **Learning Curve**: Generic types, advanced patterns can be complex
- **Type Definitions**: Some libraries lack good types (need `@types/` packages)

---

### Tailwind CSS

**What It Is**: Utility-first CSS framework with predefined classes.

**Why Chosen**:

1. **Utility-First Approach**:
   ```jsx
   // No separate CSS file needed
   <button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
     Apply
   </button>
   ```
   - Rapid prototyping (no naming classes)
   - Consistent spacing scale (`p-4` = 1rem padding)
   - Built-in responsive design (`md:flex lg:grid`)

2. **Small Bundle Size**:
   - PurgeCSS removes unused classes (production bundle ~10KB)
   - Only ships CSS for classes actually used in code
   - Compare to Bootstrap (~50KB) or Material-UI (~100KB)

3. **Design System Enforced**:
   - Predefined color palette (can't use arbitrary `#AF3B2C`)
   - Spacing scale ensures visual consistency
   - Typography scale for font sizes

4. **Dark Mode Support**:
   ```jsx
   <div className="bg-white dark:bg-gray-800">
     Content adapts to system theme
   </div>
   ```

**Alternatives Considered**:
- **Bootstrap**: Component library, harder to customize
- **CSS Modules**: More verbose, need separate files
- **Styled Components**: CSS-in-JS, runtime cost

**Trade-offs**:
- **HTML Verbosity**: Long `className` strings can be hard to read
- **Learning Curve**: Need to memorize utility class names
- **Non-Semantic HTML**: `<div className="flex items-center">` doesn't describe content

---

### shadcn/ui

**What It Is**: Collection of accessible, customizable React components built on Radix UI.

**Why Chosen**:

1. **Copy-Paste Components** (Not a Library):
   - Components copied into `components/ui/` directory
   - Full control over code (can modify any component)
   - No dependency on external package updates
   - Tree-shakable (only import what you use)

2. **Accessibility Built-In**:
   - Uses Radix UI primitives (ARIA roles, keyboard navigation)
   - Example: `<Button>` has proper focus states, disabled handling
   - `<Dropdown>` supports keyboard arrow navigation

3. **Tailwind Integration**:
   - Components styled with Tailwind classes
   - Easy to customize via `className` prop
   - Consistent with rest of application

4. **Common Patterns Solved**:
   - Badge component for status tags (green/yellow/red)
   - Card for job listings
   - Table for dashboard grid
   - Input/Label for forms

**Alternatives Considered**:
- **Material-UI**: Heavy bundle size (~300KB), opinionated design
- **Chakra UI**: Good accessibility, but more dependencies
- **Headless UI**: Similar to Radix, but shadcn provides pre-styled components

**Trade-offs**:
- **Manual Updates**: Need to manually update components (no `npm update`)
- **Initial Setup**: Requires copying files during setup
- **Less Comprehensive**: Fewer components than Material-UI

---

## Backend Technologies

### Python 3.11

**What It Is**: High-level programming language with strong ecosystem for AI/ML and web.

**Why Chosen**:

1. **AI Library Ecosystem**:
   - `claude-agent-sdk` (official Claude Agent SDK; default engine) — and the Google Generative AI SDK retained as a fallback
   - Pydantic for data validation (target models for the SDK's structured output)
   - LangChain for AI agent patterns (future potential)

2. **Web Framework Compatibility**:
   - FastAPI requires Python 3.7+
   - Python 3.11 is 10-60% faster than 3.10 (PEP 659 optimizations)
   - Async/await support mature in 3.11

3. **Type Hints and Validation**:
   ```python
   def score_job(job_title: str, resume_text: str) -> int:
       # Type hints enable FastAPI auto-validation
       return ai_score(job_title, resume_text)
   ```

4. **Development Velocity**:
   - Concise syntax (no boilerplate)
   - Rich standard library (subprocess for LaTeX, json, datetime)
   - REPL for rapid testing

**Alternatives Considered**:
- **Node.js**: Better for isomorphic apps (share code with frontend), but weaker AI ecosystem
- **Go**: Faster performance, but immature AI libraries
- **Rust**: Maximum performance, but steep learning curve, overkill for I/O-bound tasks

**Trade-offs**:
- **Performance**: Slower than compiled languages (mitigated by async I/O, parallel processing)
- **Packaging**: Dependency management (pip, virtualenv) less robust than npm
- **Type Safety**: Optional type hints, not enforced at runtime (Pydantic helps)

---

### FastAPI

**What It Is**: Modern Python web framework with automatic API documentation and async support.

**Why Chosen**:

1. **Automatic OpenAPI Documentation**:
   - Visit `/docs` for interactive Swagger UI
   - Automatically generated from route signatures:
     ```python
     @app.post("/apply")
     def apply(request: ApplyRequest) -> ApplyResponse:
         # FastAPI auto-generates docs from types
     ```
   - No need to manually write API specs

2. **Async/Await for Performance**:
   - Handle multiple requests concurrently without threads
   - Perfect for I/O-bound tasks (database queries, HTTP requests to scraper)
   - Example:
     ```python
     @app.get("/suggestions")
     async def get_suggestions():
         # Can handle 1000s of requests/sec with single process
         jobs = await db.query(...)
         return jobs
     ```

3. **Pydantic Validation**:
   - Request/response bodies validated automatically:
     ```python
     class ApplyRequest(BaseModel):
         url: str  # FastAPI returns 400 if not a string
         job_id: Optional[int] = None
     ```
   - Type errors caught before handler code runs

4. **Dependency Injection**:
   - Database sessions managed via DI:
     ```python
     @app.get("/jobs/{id}")
     def get_job(id: int, session: Session = Depends(get_session)):
         # Session auto-injected, auto-closed
     ```

**Alternatives Considered**:
- **Flask**: Simpler, but no async support, manual validation
- **Django**: Full-stack framework, overkill for API-only service
- **Express (Node.js)**: Good async, but Python ecosystem preferred for AI

**Trade-offs**:
- **Newer Framework**: Less mature than Flask/Django (2018 release)
- **Magic via Decorators**: Dependency injection can be hard to debug
- **Less Comprehensive**: No built-in ORM (separate SQLModel), admin panel

---

### SQLModel

**What It Is**: Library combining SQLAlchemy (ORM) and Pydantic (validation).

**Why Chosen**:

1. **Single Model Definition**:
   ```python
   class Job(SQLModel, table=True):
       id: Optional[int] = Field(default=None, primary_key=True)
       url: str = Field(unique=True)
       score: Optional[int] = None
   
   # Same model works for:
   # - Database ORM (SQLAlchemy)
   # - API validation (Pydantic)
   # - JSON serialization (FastAPI)
   ```

2. **Type Safety**:
   - Database schema matches Python types
   - FastAPI validates against same models
   - Prevents type mismatches (e.g., string where int expected)

3. **SQLAlchemy Power**:
   - Mature query builder:
     ```python
     jobs = session.exec(
         select(Job)
         .where(Job.status == "suggested")
         .order_by(Job.score.desc())
     ).all()
     ```
   - Relationships, joins, migrations all supported

4. **FastAPI Integration**:
   - Return SQLModel instances from routes → auto-serialized to JSON
   - No manual `.to_dict()` conversions

**Alternatives Considered**:
- **Raw SQLAlchemy**: More boilerplate (separate Pydantic models)
- **Django ORM**: Coupled to Django framework
- **Tortoise ORM**: Native async, but less mature

**Trade-offs**:
- **Newer Library**: SQLModel created in 2021, smaller community
- **Less Flexibility**: Shared models mean database and API schemas must match
- **Migration Complexity**: Alembic migrations can be tricky with SQLModel

---

### Alembic

**What It Is**: Database migration tool for SQLAlchemy.

**Why Chosen**:

1. **Version Control for Schema**:
   - Each migration is a Python script in `migrations/versions/`
   - Upgrades/downgrades tracked:
     ```bash
     alembic upgrade head      # Apply all migrations
     alembic downgrade -1      # Rollback one migration
     ```

2. **Automatic Migration Generation**:
   ```bash
   alembic revision --autogenerate -m "Add job_sources table"
   # Detects model changes, generates migration script
   ```

3. **Team Collaboration**:
   - Developers apply same migrations to local databases
   - Prevents "it works on my machine" schema mismatches

4. **Production Safety**:
   - Incremental schema changes (no DROP DATABASE)
   - Migrations run on container startup (see `entrypoint.sh`)

**Alternatives Considered**:
- **Raw SQL scripts**: Manual, error-prone, no version tracking
- **Django migrations**: Tied to Django ORM
- **Flyway**: Java-based, more complex setup

**Trade-offs**:
- **Manual Review Required**: Auto-generated migrations can be wrong (need to verify)
- **Downgrade Complexity**: Writing reverse migrations is tedious
- **SQLite Limitations**: Some operations (e.g., DROP COLUMN) require table recreation

---

## AI & Machine Learning

### Claude (via the Claude Agent SDK)

**What It Is**: Anthropic's Claude family of large language models, accessed through the `claude-agent-sdk` Python package. The default engine, selectable via `LLM_PROVIDER` (`claude` default, `gemini` legacy fallback). Model chosen via `CLAUDE_MODEL` (default `sonnet`; also `haiku`/`opus`/full model ids).

**Why Chosen**:

1. **No Per-Token Cost**:
   - Authenticated by a Claude Pro/Max **subscription** via `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`)
   - Inference draws from the subscription — no pay-per-token API billing
   - **Never set `ANTHROPIC_API_KEY`**: it shadows the OAuth token and switches to pay-per-token billing; the `claude_auth_configured` startup check fails fast if it is present

2. **Structured JSON Output** (Killer Feature):
   ```python
   # Define expected output schema (core/models.py)
   class JobListing(BaseModel):
       title: str
       company: str
       url: str

   # The SDK's output_format JSON schema produces structured_output,
   # which is validated into the Pydantic model.
   result_message = await query_with_schema(prompt, schema=JobListing)
   listing = JobListing.model_validate(result_message.structured_output)
   ```
   - No prompt engineering to coax valid JSON
   - SDK enforces the schema; Pydantic validates structure on the way in
   - Works the same across the provider abstraction

3. **Provider Abstraction Kept**:
   - The active code is `core/llm_providers.py`: the `LLMProvider` ABC plus `ClaudeAgentProvider` (default), `GeminiProvider` (fallback), and `StubProvider` (tests), wired up by `create_default_provider()`
   - Agents (`core/agents.py`) depend only on the `LLMProvider` interface, so swapping engines is configuration, not code surgery
   - Gemini stays a documented fallback: set `LLM_PROVIDER=gemini` (needs `GOOGLE_API_KEY`)

**Alternatives Considered**:
- **Google Gemini** (now the fallback): direct HTTP API with native JSON mode; retained behind the abstraction
- **OpenAI GPT-4**: Strong reasoning, but pay-per-token and would need its own provider implementation
- **Open-Source LLMs (LLaMA, Mistral)**: Self-hosted, but require GPU, generally worse quality

**Trade-offs**:
- **Subprocess Latency**: The SDK shells out to the local `claude` CLI subprocess (Node + `@anthropic-ai/claude-code`, installed in the tailor Docker image), so each call is ~3–13s — slower than the old direct Gemini HTTP path. This is a real architectural trade-off, accepted for subscription billing and structured-output reliability.
- **Runtime Dependency**: Requires the `claude` CLI (Node) present in the container alongside Python.
- **Non-Deterministic**: Same prompt can yield different results (need quality checks).

---

### Pydantic

**What It Is**: Data validation library using Python type hints.

**Why Chosen for AI**:

1. **Schema Enforcement**:
   ```python
   class JobRequirements(BaseModel):
       requirements: List[str]
       min_experience_years: int
       education: Optional[str]
   
   # The Claude Agent SDK returns structured_output, Pydantic validates
   result = JobRequirements.model_validate(result_message.structured_output)
   # Raises ValidationError if schema doesn't match
   ```

2. **Default Values**:
   ```python
   class JobScore(BaseModel):
       score: int  # Required field
       reasoning: str = "No reasoning provided"  # Default
   
   # AI can omit reasoning, Pydantic fills default
   ```

3. **Type Coercion**:
   ```python
   class Job(BaseModel):
       score: int
   
   # AI returns "87" (string) → Pydantic converts to 87 (int)
   # AI returns 87.5 (float) → Pydantic rounds to 88 (int)
   ```

4. **Error Messages**:
   ```python
   # If AI returns invalid data:
   # ValidationError: 1 validation error
   #   score
   #     value is not a valid integer (type=type_error.integer)
   ```

**Value for AutoCareer**:
- **Prevents Silent Failures**: Invalid AI output caught immediately
- **Type Safety**: Database models are also Pydantic models (via SQLModel)
- **Documentation**: Model schemas auto-document API responses

---

## Scraping & Automation

### Playwright

**What It Is**: Browser automation library supporting Chrome, Firefox, Safari.

**Why Chosen**:

1. **JavaScript Rendering**:
   - Many job sites load content via React/Vue (client-side rendering)
   - Playwright waits for JavaScript to execute before returning HTML
   - Example: LinkedIn jobs load via AJAX after initial page render

2. **Headless Mode**:
   - Runs Chrome without GUI (fast, low memory)
   - Perfect for Docker containers (no display needed)
   - Can switch to headful mode for debugging (screenshot on error)

3. **Wait Strategies**:
   ```python
   page.goto(url)
   page.wait_for_selector(".job-listing")  # Wait for content
   html = page.content()
   ```
   - Auto-waits for network idle, DOM ready
   - Configurable timeouts (default: 30s)

4. **Modern API**:
   - Async/await support (works with FastAPI)
   - Built-in browser context isolation (parallel scraping)
   - Auto-retries on network errors

**Alternatives Considered**:
- **Selenium**: Older, slower, more flaky
- **Puppeteer**: Chrome-only (Playwright supports Firefox/Safari)
- **Requests + BeautifulSoup**: Can't handle JavaScript-rendered pages

**Trade-offs**:
- **Heavy Dependency**: Requires downloading Chromium (~300MB)
- **Resource Intensive**: Each browser instance uses ~100MB RAM
- **Anti-Bot Detection**: Some sites block headless browsers (need user-agent spoofing)

---

### BeautifulSoup

**What It Is**: HTML parsing library for extracting data from markup.

**Why Chosen**:

1. **Lenient Parsing**:
   - Handles malformed HTML gracefully
   - Many job sites have invalid markup (unclosed tags, etc.)
   - BeautifulSoup auto-corrects syntax errors

2. **Simple API**:
   ```python
   soup = BeautifulSoup(html, "html.parser")
   job_cards = soup.find_all("div", class_="job-card")
   titles = [card.find("h2").text for card in job_cards]
   ```

3. **CSS Selectors**:
   ```python
   soup.select(".job-listing > .title")  # Same syntax as browser DevTools
   ```

4. **Lightweight**:
   - No browser needed (just parses HTML string)
   - Fast for static content

**Why Not Used for Full Pipeline?**
- BeautifulSoup alone can't handle JavaScript-rendered content
- AutoCareer uses **Playwright (fetch HTML) → BeautifulSoup (parse)** combo

**Alternatives Considered**:
- **lxml**: Faster, but stricter parsing (fails on invalid HTML)
- **Regular Expressions**: Too brittle for HTML
- **AI Parsing Only**: Expensive to send full HTML to the LLM for every job

---

## Database Technologies

### PostgreSQL 15

**What It Is**: Open-source relational database with ACID guarantees.

**Why Chosen**:

1. **Production-Grade Reliability**:
   - ACID transactions (no data corruption on crashes)
   - Write-ahead logging (WAL) for durability
   - Point-in-time recovery (PITR) from backups

2. **Advanced Features**:
   - **JSON/JSONB columns**: Store `jobs.requirements` as structured data
     ```sql
     SELECT * FROM jobs WHERE requirements @> '["Python"]';
     -- Query inside JSON array
     ```
   - **Full-text search**: Future feature (search job descriptions)
   - **Foreign keys**: Enforce `jobs.source_id` → `job_sources.id` relationship

3. **Performance at Scale**:
   - Indexes on `url` (unique) and `status` (filtering)
   - Query planner optimizes complex joins
   - Connection pooling via SQLAlchemy

4. **Community & Extensions**:
   - pg_trgm for fuzzy text search
   - pgvector for AI embedding search (future: semantic job search)

**Alternatives Considered**:
- **MySQL**: Less feature-rich (no JSONB, weaker full-text search)
- **SQLite**: Great for development, but no concurrent writes (problem for multi-user)
- **MongoDB**: NoSQL overkill, loses relational benefits

**Trade-offs**:
- **Operational Complexity**: Requires separate container, backups, monitoring
- **Memory Usage**: ~50MB RAM minimum (vs SQLite's ~5MB)
- **Overkill for Single User**: AutoCareer is self-hosted (1 user), but PostgreSQL enables future multi-user

---

### SQLite

**What It Is**: Embedded relational database (single file, no server).

**Why Chosen for Hybrid Mode**:

1. **Portability**:
   - Database is a single file (`autocareer.db`)
   - Easy to backup (copy file)
   - Can move between machines (attach to email, Dropbox)

2. **Zero Configuration**:
   - No daemon to run (embeds in Python process)
   - No ports to expose
   - No user/password management

3. **Development Velocity**:
   - Test migrations locally without Docker
   - Faster iteration (no container rebuild)

4. **Hybrid Mode Strategy**:
   - **Development**: SQLite for speed
   - **Production**: PostgreSQL for reliability
   - **Sync Script**: `migrate_postgres_to_sqlite.py` for backups

**Limitations** (Why Not Primary DB):
- **Concurrent Writes**: Only one writer at a time (fine for single-user)
- **No Network Access**: Can't query from remote machine
- **Limited Data Types**: No native JSON querying (stored as TEXT)

**Hybrid Mode Configuration**:
```env
DATABASE_BACKEND=hybrid
DB_SYNC_ENABLED=true
SYNC_ON_BOOT=true   # Copy PostgreSQL → SQLite on startup
```

---

## PDF Generation

### TeX Live + pdflatex

**What It Is**: Comprehensive LaTeX distribution with pdflatex compiler.

**Why Chosen**:

1. **Professional Typography**:
   - LaTeX produces publication-quality PDFs
   - Automatic hyphenation, kerning, ligatures
   - Consistent spacing and alignment
   - Superior to Word/Google Docs for technical resumes

2. **Programmability**:
   - The resume layout is a Jinja2 LaTeX template (`data/resume_template.tex.j2`)
   - Content lives as structured JSON (`data/master_resume.json`); `core/resume_renderer.py` renders it deterministically:
     ```python
     content = load_master_resume_content("./data/master_resume.json")  # → ResumeContent
     latex = render_resume(content)  # Jinja2 + LaTeX escaping, always compilable
     ```
   - The AI agent never writes LaTeX — it produces validated `ResumeContent` (structured output)

3. **Version Control**:
   - `.tex` files are plain text (Git-friendly)
   - Diffs show actual content changes
   - Compare to `.docx` (binary blob, hard to diff)

4. **Consistency Across Jobs**:
   - Same template = identical formatting for all resumes
   - Font sizes, margins, spacing stay consistent
   - Recruiter can't tell which resume is "original"

**Challenges**:

1. **Large Installation**:
   - TeX Live full distribution: ~6GB
   - TeX Live basic: ~200MB (used in Docker)
   - Requires separate container layer

2. **Compilation Errors**:
   - LaTeX syntax errors stop compilation
   - Mitigated by design: the template is fixed and every interpolated value is escaped (`| tex` filter), so the LLM cannot produce invalid LaTeX — a pdflatex failure points at a template bug, not model output

3. **Learning Curve**:
   - Users maintain their master resume as structured JSON (`master_resume.json`), no LaTeX knowledge needed for content
   - Layout changes require editing the Jinja2 LaTeX template
   - Not WYSIWYG (need to compile to see output)

**Alternatives Considered**:
- **HTML → PDF (wkhtmltopdf)**: Easier, but lower quality typography
- **Markdown → PDF (Pandoc)**: Limited styling control
- **Python libraries (ReportLab)**: Programmatic, but verbose

**Why LaTeX Wins**:
- **Quality**: Recruiters prefer LaTeX-typeset resumes (clean, professional)
- **AI Integration**: structured `ResumeContent` from the LLM maps 1:1 onto the template — no fragile format conversion
- **Future-Proof**: LaTeX hasn't changed in decades (stability)

---

## DevOps & Infrastructure

### Docker Compose

**What It Is**: Tool for defining multi-container applications via YAML config.

**Why Chosen**:

1. **Service Orchestration**:
   ```yaml
   services:
     frontend:
       build: ./frontend
       ports: ["3000:3000"]
     tailor:
       build: ./backend/services/resume-tailor
       depends_on: [postgres]
     postgres:
       image: postgres:15
   ```
   - Single command: `docker-compose up` starts all services
   - Automatic network creation (services can talk via hostnames)

2. **Environment Parity**:
   - Development = Production environment (same containers)
   - No "works on my machine" issues
   - Dependencies (TeX Live, Playwright) installed once in Dockerfile

3. **Isolation**:
   - Each service in separate container
   - Scraper crash doesn't affect main API
   - Can restart individual services: `docker-compose restart tailor`

4. **Volume Mounts**:
   - Development: Mount source code (hot reload)
   - Production: Persist database, PDFs, logs

**Alternatives Considered**:
- **Kubernetes**: Overkill for single-machine deployment
- **Systemd services**: Manual setup, no cross-platform
- **Bare metal**: Dependency conflicts (Python versions, TeX Live)

**Trade-offs**:
- **Resource Usage**: 4 containers use more RAM than monolith (~500MB total)
- **Startup Time**: Docker build can take 5-10 minutes first time
- **Complexity**: Need to understand Docker concepts (images, volumes, networks)

---

### GitHub Actions (Future)

**What It Would Enable**:

1. **CI/CD Pipeline**:
   - Run tests on every commit
   - Build Docker images automatically
   - Deploy to production on merge to `main`

2. **Automated Migrations**:
   - Test Alembic migrations in PR preview environment
   - Prevent breaking schema changes

3. **Release Automation**:
   - Tag releases, generate changelogs
   - Build multi-platform Docker images (ARM64 for Raspberry Pi)

**Not Implemented Yet**:
- AutoCareer is self-hosted (users run locally)
- No shared infrastructure to deploy to
- Future SaaS version would use GitHub Actions

---

## Technology Decision Matrix

| Requirement | Technology Chosen | Key Reason |
|-------------|-------------------|------------|
| **Frontend Framework** | Next.js 14 | File-based routing, SSR, React ecosystem |
| **UI Components** | shadcn/ui | Copy-paste, accessible, Tailwind-integrated |
| **Styling** | Tailwind CSS | Utility-first, small bundle, design system |
| **Type Safety** | TypeScript | IDE support, fewer runtime errors |
| **Backend Language** | Python 3.11 | AI ecosystem, FastAPI compatibility |
| **Web Framework** | FastAPI | Async I/O, auto-docs, Pydantic validation |
| **ORM** | SQLModel | Single model definition, type safety |
| **Migrations** | Alembic | Version control, autogenerate, team collab |
| **Primary Database** | PostgreSQL 15 | JSONB, production reliability, advanced features |
| **Portable Database** | SQLite | Single file, zero config, easy backups |
| **AI Model** | Claude (Claude Agent SDK) | Subscription billing (no per-token cost), structured output, provider abstraction with Gemini fallback |
| **Validation** | Pydantic | Schema enforcement, type coercion, error messages |
| **Scraping** | Playwright | JavaScript rendering, headless, modern API |
| **HTML Parsing** | BeautifulSoup | Lenient parsing, simple API, lightweight |
| **PDF Generation** | TeX Live (pdflatex) | Professional typography, programmable, version control |
| **Orchestration** | Docker Compose | Multi-service, environment parity, isolation |

---

## Dependency Licenses

All technologies used in AutoCareer are open-source or have permissive licenses:

| Technology | License | Commercial Use |
|------------|---------|----------------|
| Next.js | MIT | ✅ Yes |
| React | MIT | ✅ Yes |
| TypeScript | Apache 2.0 | ✅ Yes |
| Tailwind CSS | MIT | ✅ Yes |
| Python | PSF License | ✅ Yes |
| FastAPI | MIT | ✅ Yes |
| SQLModel | MIT | ✅ Yes |
| PostgreSQL | PostgreSQL License | ✅ Yes |
| SQLite | Public Domain | ✅ Yes |
| Playwright | Apache 2.0 | ✅ Yes |
| TeX Live | LPPL (LaTeX), GPL (Binaries) | ✅ Yes (with attribution) |

**Claude (Claude Agent SDK)**:
- Not open-source (proprietary service); `claude-agent-sdk` is the client package
- Default engine, authenticated by a Claude Pro/Max subscription (`CLAUDE_CODE_OAUTH_TOKEN`) — inference uses the subscription, no per-token cost
- **Google Gemini API** remains the documented fallback (`LLM_PROVIDER=gemini`, `GOOGLE_API_KEY`): proprietary API, billed per token when used

---

## Performance Benchmarks

### Frontend Bundle Size

- **JavaScript**: ~250KB gzipped
  - Next.js framework: ~80KB
  - React runtime: ~40KB
  - shadcn/ui components: ~30KB
  - Application code: ~50KB
  - Tailwind CSS: ~10KB

- **First Load Time**: ~1.2s on 4G connection
- **Largest Contentful Paint (LCP)**: <2.5s (Good)

### Backend Response Times

| Endpoint | Avg Response Time | Bottleneck |
|----------|-------------------|------------|
| `GET /jobs` | 50ms | Database query |
| `GET /suggestions` | 100ms | Database join + sorting |
| `POST /sources` | 30ms | Database insert |
| `POST /apply` | 200ms (initial), 20s (background) | AI + LaTeX |
| `POST /suggestions/refresh` | 300ms (initial), 25s (background) | Parallel AI calls |

### Database Performance

- **Jobs table**: ~10K rows → 5ms for filtered query
- **Index usage**: `url` (UNIQUE), `status` (B-tree)
- **Connection pool**: 5 connections (SQLAlchemy default)

### AI Latency

Per-call latency runs ~3–13s on Claude, since each call spawns the `claude` CLI subprocess (slower than the old direct Gemini HTTP path):

- **JobDiscoveryAgent**: 3-5s per source (HTML parsing)
- **JobScoringAgent**: 2-3s per job (parallel, 10 jobs = 3s total)
- **JobParsingAgent**: 4-6s per job (detailed extraction)
- **ResumeTailorAgent**: 8-12s per job (longest response)

### Scraping Performance

- **Playwright startup**: 2s (Chrome launch, cached after first request)
- **Page load**: 1-5s depending on site
- **HTML fetch**: 0.5-2s (network latency)

---

## Future Technology Considerations

### Potential Upgrades

1. **AI Provider Abstraction** (foundation now in place):
   - The `LLMProvider` ABC in `core/llm_providers.py` already unifies engines — Claude (default) and Gemini (fallback) ship today
   - Adding OpenAI or local LLMs is implementing the interface
   - Fallback to an alternate provider if the primary fails

2. **Caching Layer** (Redis):
   - Cache scraped HTML for 1 hour (avoid re-scraping)
   - Cache AI scores for duplicate jobs
   - Session management for multi-user

3. **Job Queue** (Celery + RabbitMQ):
   - Replace background tasks with distributed queue
   - Scale workers horizontally
   - Persist tasks across restarts

4. **Vector Database** (Pinecone, Weaviate):
   - Store job embeddings for semantic search
   - Find similar jobs to those user applied to
   - Recommend jobs based on past applications

5. **Monitoring** (Prometheus + Grafana):
   - Track API response times
   - Alert on AI failures
   - Dashboard for job discovery metrics

6. **Frontend Framework Migration**:
   - Keep Next.js, but adopt:
   - Server Actions for form submissions
   - React Server Components for data fetching
   - Streaming UI for real-time scan progress

---

## Conclusion

AutoCareer's technology stack balances:
- **Developer Velocity**: FastAPI, Next.js, Tailwind enable rapid iteration
- **Type Safety**: TypeScript + Pydantic + SQLModel catch errors early
- **AI Integration**: Claude's structured output (via the Claude Agent SDK) + Pydantic = reliable automation
- **Quality**: LaTeX produces professional PDFs recruiters respect
- **Reliability**: PostgreSQL + Docker ensure production-grade stability

Each technology choice optimizes for AutoCareer's core goal: **automate job applications without sacrificing quality**.
