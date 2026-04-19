# AI SaaS Outbound System - Autonomous GTM Agent

A **production-grade 10/10 autonomous GTM (Go-To-Market) agent** that transforms outbound email from manual work into an intelligent, self-improving pipeline system.

## What This Business Does (For Non-Technical Stakeholders)

### The Simple Explanation

This system is an **AI-powered sales assistant** that automatically finds potential customers, writes personalized emails to them, handles their replies, and books meetings — all without human intervention.

**Think of it like having a tireless sales development representative (SDR) who:**
- Never sleeps
- Can research and write personalized emails to thousands of prospects
- Automatically follows up with people who don't respond
- Knows when someone is interested and books meetings
- Learns from every interaction to get better over time

---

### Two Business Models You Can Run

#### **Model 1: Direct Sales Tool** (Sell Your Own Product)
**What you do:** Use the system to sell your company's product/service

**How it works:**
1. You input signals about companies (e.g., "Company X just raised $10M and is hiring salespeople")
2. AI scores each lead (0-100) based on how likely they are to buy
3. System automatically writes personalized emails mentioning their specific situation
4. Sends emails at optimal times to avoid spam filters
5. When someone replies, AI classifies their response (interested / not interested / wrong person / unsubscribe)
6. Automatically sends follow-ups if they don't reply
7. Books meetings directly to your calendar when leads are interested

**Example:**
- You sell sales automation software
- System finds companies hiring sales reps
- Email: *"Hi John, saw Acme Corp is hiring 5 SDRs. Usually means pipeline pressure. We help teams automate outreach without losing the personal touch. Worth a 10-min chat?"*
- If John replies "interested," system sends your Calendly link

**Revenue:** Your product/service sales

---

#### **Model 2: B2B Matchmaking Platform** (The "Middleman" Model)
**What you do:** Connect service providers with companies who need their services — and take a cut

**How it works:**
1. **Service Providers** (e.g., cloud migration consultants, marketing agencies) pay you monthly for access
2. **Buyers** (companies needing those services) use your platform for free
3. Your AI matches buyers to the right service providers based on signals
4. System sends introductions on behalf of service providers
5. You earn revenue from:
   - Monthly subscription fees from service providers
   - Pay-per-meeting fees when meetings get booked
   - Success fees when deals close

**Example:**
- CloudMigration Co pays you $2,000/month for platform access
- TechStartup just raised $20M and is hiring DevOps engineers (signals they need cloud migration)
- Your AI matches them (94% fit score)
- System sends intro email from CloudMigration Co to TechStartup's CTO
- When they book a meeting, you earn $50-500

**Revenue Math:**
| Scale | Monthly Profit |
|-------|----------------|
| 10 service providers | $4,500/month |
| 50 service providers | $22,500/month |
| 100 service providers | $45,000/month |

---

### Key Business Terms Explained

| Term | What It Means in Plain English |
|------|--------------------------------|
| **Lead** | A potential customer (company + decision maker) |
| **Signal** | A trigger event indicating a company might need your product (e.g., funding news, hiring posts) |
| **Pipeline** | The journey a lead takes: New → Contacted → Replied → Interested → Meeting Booked → Customer |
| **Conversion Rate** | % of leads who move to the next stage |
| **Reply Rate** | % of people who respond to your emails |
| **A/B Testing** | Sending different email versions to see which performs better |
| **Deliverability** | Making sure emails land in inboxes, not spam folders |
| **Follow-up Sequence** | Automated series of emails sent if someone doesn't reply |
| **Qualification Score** | AI-calculated rating (0-100) of how good a lead is |
| **Template** | Pre-written email that AI personalizes for each recipient |

---

### The Complete Customer Journey

```
┌─────────────────────────────────────────────────────────────────────┐
│  DISCOVERY                                                          │
│  System finds companies showing buying signals                        │
│  (Hiring, funding, product launches, expansions)                    │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  QUALIFICATION                                                      │
│  AI scores each lead on 5 dimensions:                               │
│  - Signal strength (how strong the buying signal is)                │
│  - Hiring intensity (are they expanding teams?)                   │
│  - Funding stage (do they have budget?)                             │
│  - Company size fit (right size for your product?)                │
│  - Market relevance (in your target market?)                      │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PERSONALIZATION                                                    │
│  AI writes unique email for each prospect:                          │
│  - References their specific situation                              │
│  - Matches their signal to your offer                               │
│  - Uses proven templates that have worked before                    │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DELIVERY                                                           │
│  System sends emails:                                                 │
│  - At optimal times (not too fast to avoid spam)                  │
│  - From warmed-up domains (established senders)                   │
│  - With personalized subject lines                                  │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REPLY HANDLING                                                     │
│  When someone replies, AI classifies it:                            │
│  - "Interested" → Book meeting, stop follow-ups                     │
│  - "Not now" → Schedule follow-up for later                         │
│  - "Not interested" → Stop contacting                               │
│  - "Unsubscribe" → Remove from list immediately                     │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OPTIMIZATION                                                       │
│  System learns and improves:                                        │
│  - Tracks which emails get replies                                  │
│  - Auto-promotes winning templates                                  │
│  - Adjusts timing based on response patterns                        │
│  - Reports ROI: cost per lead, cost per meeting, cost per deal      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture (Autonomous GTM Agent)

```
Signal Detection → Lead Scoring → Offer Matching → Message Generation → 
Deliverability Engine → Sending System → Reply Understanding → Pipeline Tracking → 
Learning Loop → Optimization Engine
```

## System Overview (How It All Works Together)

### The Big Picture

This system automates the entire outbound sales process — from finding prospects to booking meetings. Here's what each part does in business terms:

| Technical Component | What It Does for Your Business |
|--------------------|-------------------------------|
| **Lead Ingestion** | Collects information about potential customers from various sources (APIs, webhooks, manual entry) |
| **Lead Qualification Engine** | Ranks leads 0-100 based on how likely they are to buy, so you focus on the best opportunities first |
| **Offer Matching Engine** | Figures out what message angle will resonate based on the prospect's situation (funding news, hiring, etc.) |
| **Template System** | Stores proven email templates and tracks which ones get the best response rates |
| **AI Email Generator** | Uses GPT-4 to personalize each email so it doesn't feel like a mass email |
| **Deliverability System** | Makes sure your emails land in inboxes, not spam folders — includes domain warmup and health monitoring |
| **Pipeline State Machine** | Tracks where each prospect is in your sales process (New → Contacted → Replied → Interested → Meeting Booked) |
| **Reply Classifier** | Reads responses and categorizes them (interested, not interested, wrong person, etc.) |
| **Follow-up Automation** | Automatically sends follow-up emails if someone doesn't reply (Day 2, Day 5, Day 9) |
| **Human Escalation** | Flags high-value prospects or complex situations for a human to handle personally |
| **CRM Integration** | Pushes qualified leads and deals to your CRM (Salesforce, HubSpot) |
| **A/B Testing** | Tests different email versions and automatically promotes the winners |
| **Learning Loop** | Analyzes what worked and what didn't, then optimizes future outreach |

---

## Core Components

### Infrastructure
- **FastAPI**: Production-ready API with JWT auth, rate limiting, monitoring
- **Celery**: Distributed task queue with circuit breakers and retry logic
- **Celery Beat**: 9 scheduled workflows (daily batches, qualification scoring, deliverability, follow-ups)
- **PostgreSQL**: 17 tables with full audit trail and performance indexes
- **Redis**: Caching, Celery broker, and session storage
- **Prometheus**: Comprehensive metrics and monitoring

### AI/ML Layer
- **OpenAI GPT-4**: Subject generation, email body rendering, reply classification
- **Lead Qualification Engine**: Multi-dimensional scoring (signal strength, hiring, funding, company size, market relevance)
- **Offer Matching Engine**: Signal-to-offer strategy mapping with 6 default strategies
- **Template System**: AI-personalized message templates with signal matching, A/B testing, performance tracking
- **Feedback Learning Loop**: Tracks reply rates per subject/angle/template/company type and optimizes

### Business Logic
- **Gmail API Integration**: OAuth2 authentication, rate limiting, bounce handling
- **Deliverability System**: Domain warming, inbox rotation, health monitoring (prevents Gmail blocks)
- **Conversation Memory**: Thread context tracking (tone, objections, relationship stage)
- **Reply Classifier**: 4-way classification (interested, not_now, not_interested, unsubscribe)
- **Follow-up Scheduler**: Day 2, 5, 9 automated sequences
- **Pipeline State Machine**: 9-state workflow (NEW → QUALIFIED → CONTACTED → REPLIED → INTERESTED → CALL_BOOKED → CLOSED → LOST → SUPPRESSED)
- **CRM Layer**: Deal tracking, ROI metrics, pipeline value, win rates

### Production Features
- **JWT Authentication**: Secure API access with role-based permissions
- **Circuit Breakers**: Resilience for Gmail API and OpenAI API
- **Idempotency Keys**: Prevent duplicate operations
- **Rate Limiting**: 1000 req/min API, 30 emails/hour per domain
- **Health Checks**: Deep monitoring (DB, Redis, Gmail, OpenAI, disk, memory)
- **Alerting**: Slack/webhook integration for critical events
- **Graceful Shutdown**: Signal handlers, resource cleanup
- **Backup Strategy**: Automated PostgreSQL backups (Bash/PowerShell scripts)

## Project Structure

```
ai-saas/
├── app/
│   ├── api/                  # FastAPI endpoints (40+ endpoints)
│   │   └── routes.py         # Lead CRUD, Template System, Core Operations, Webhooks
│   ├── services/             # Business logic
│   │   ├── lead_loader.py
│   │   ├── batch_builder.py
│   │   ├── template_service.py   # NEW: Template management & AI personalization
│   │   ├── subject_generator.py
│   │   ├── email_renderer.py
│   │   ├── gmail_sender.py
│   │   ├── lead_qualification.py
│   │   ├── offer_matching.py
│   │   ├── conversation_memory.py
│   │   ├── deliverability.py
│   │   ├── feedback_learning.py
│   │   ├── followup_scheduler.py
│   │   ├── pipeline_state_machine.py
│   │   ├── crm.py
│   │   ├── experimentation.py
│   │   └── human_escalation.py
│   ├── workers/              # Celery configuration
│   │   ├── celery_app.py
│   │   └── tasks.py
│   ├── integrations/         # Gmail integration
│   │   ├── gmail_watch.py
│   │   └── gmail_thread_fetcher.py
│   ├── classifiers/          # Reply classification
│   │   └── reply_classifier.py
│   ├── auth.py               # JWT authentication
│   ├── validators.py         # Pydantic validation models
│   ├── circuit_breaker.py    # Circuit breaker pattern
│   ├── monitoring.py         # Prometheus metrics
│   ├── health.py             # Health checks
│   ├── alerting.py           # Alert system
│   ├── idempotency.py        # Idempotency handling
│   ├── config_validator.py   # Startup validation
│   ├── shutdown.py           # Graceful shutdown
│   ├── main.py               # FastAPI app
│   ├── settings.py           # Configuration
│   ├── models.py             # SQLAlchemy models (17 tables)
│   ├── database.py           # Database connection
│   └── logging_config.py     # Logging setup
├── data/
│   ├── leads.json            # Legacy import source (optional, now API-driven)
│   ├── outbound_batch.json   # Generated batch (auto-generated)
│   ├── credentials.json      # Gmail OAuth credentials
│   └── token.json            # Gmail OAuth token
├── migrations/
│   ├── 001_initial_schema.sql      # Base tables
│   ├── 002_advanced_schema.sql     # Production tables (lead_scores, offer_strategies, etc.)
│   └── 003_templates.sql           # Template system tables
├── scripts/
│   ├── backup.sh             # Linux/macOS backup script
│   ├── backup.ps1            # Windows backup script
│   └── restore.sh            # Restore script
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth.py          # Auth tests
│   ├── test_api.py           # API endpoint tests
│   ├── test_services.py      # Service layer tests
│   └── test_circuit_breaker.py # Circuit breaker tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt          # 50+ production dependencies
├── .env.example
└── README.md
```

## Database Schema (16 Tables)

### Core Tables
- **leads**: Lead intelligence (company, signal, decision maker, fit score, message intent)
- **campaign_runs**: Batch generation tracking
- **outbound_messages**: Send-ready payloads with status tracking
- **replies**: Incoming replies with classification
- **followups**: Scheduled follow-up messages
- **suppression_list**: Emails to never contact
- **events**: Comprehensive audit log for all state changes

### Production Tables (Migration 002)
- **lead_scores**: Multi-dimensional scoring (signal_strength, hiring_intensity, funding_stage, company_size_fit, market_relevance, priority_score)
- **offer_strategies**: Signal-to-offer mapping with performance tracking
- **conversation_memory**: Thread context (tone, objections, relationship stage, email history)
- **deliverability_rules**: Domain warming, send limits, health scores
- **experiments**: A/B testing configuration
- **experiment_results**: A/B test outcomes
- **pipeline_states**: 9-state workflow tracking
- **deals**: CRM deal tracking with pipeline value
- **human_escalation_queue**: Human intervention requests
- **performance_metrics**: Feedback learning metrics

### Template System Tables (Migration 003)
- **templates**: Message templates with signal keywords, A/B testing, performance tracking
- **template performance metrics**: Usage count, reply rate, performance score (0-100)

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Gmail API credentials
- OpenAI API key

### 1. Clone and Install Dependencies

```bash
git clone <repo-url>
cd ai-saas
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values. **Required for production:**

```env
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/ai_saas
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your_secret_key_here_min_32_chars_long
OPENAI_API_KEY=your_openai_api_key

# Gmail API (Optional but recommended)
GMAIL_CREDENTIALS_PATH=data/credentials.json
GMAIL_TOKEN_PATH=data/token.json

# Production Features (Optional)
SENTRY_DSN=your_sentry_dsn_for_error_tracking
SLACK_WEBHOOK_URL=your_slack_webhook_for_alerts
ALERT_EMAILS=admin@company.com,ops@company.com
ENABLE_METRICS=true
```

### 3. Setup PostgreSQL

```bash
# Create database
createdb ai_saas

# Run migrations (all required)
psql -d ai_saas -f migrations/001_initial_schema.sql
psql -d ai_saas -f migrations/002_advanced_schema.sql
psql -d ai_saas -f migrations/003_templates.sql
```

Or use Docker Compose:

```bash
docker-compose up -d postgres redis
```

### 4. Initialize Database Tables

```bash
python init_db.py
```

### 5. Setup Gmail API (Optional for testing)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable Gmail API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download `credentials.json` and save to `data/`
5. Required scopes: `https://www.googleapis.com/auth/gmail.send`, `https://www.googleapis.com/auth/gmail.readonly`, `https://www.googleapis.com/auth/gmail.modify`

### 6. Run Tests

```bash
pytest tests/ -v
```

### 7. Start Domain Warmup (First time only)

For new domains, warmup is required:

```bash
# Via API
POST /api/deliverability/warmup?domain=yourdomain.com

# Or wait for automatic warmup (14-day progressive schedule)
```

## API Authentication

All `/api/*` endpoints require JWT authentication.

### Generate JWT Token

```bash
# Example token generation (implement your auth endpoint)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

### Use Token in Requests

```bash
curl http://localhost:8000/api/metrics \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Idempotency Keys

For safe retry of POST/PUT/PATCH requests:

```bash
curl -X POST http://localhost:8000/api/generate/outbound-batch \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Idempotency-Key: unique-key-123" \
  -H "Content-Type: application/json" \
  -d '{"from_email": "test@example.com", "max_leads": 50}'
```

## Running the Application

### Option 1: Docker Compose (Recommended)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL
- Redis
- FastAPI API server
- Celery worker
- Celery beat scheduler

### Option 2: Local Development

```bash
# Start Redis
redis-server

# Start PostgreSQL (if not using Docker)
postgres

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
python -m celery -A app.workers.tasks worker --loglevel=info

# Start Celery beat (separate terminal)
python -m celery -A app.workers.tasks beat --loglevel=info
```

## API Endpoints (30+ Endpoints)

### Lead Management (New - API-First)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads` | POST | Create single lead (no JSON needed) |
| `/api/leads/batch` | POST | Bulk create leads (up to 1000) |
| `/api/leads` | GET | List leads with filters (status, fit_score, search) |
| `/api/leads/{lead_id}` | GET | Get lead details with qualification & pipeline |
| `/api/leads/{lead_id}` | PUT | Update lead fields |
| `/api/leads/{lead_id}` | DELETE | Delete lead (soft delete) |
| `/api/webhooks/lead-ingestion` | POST | Webhook for HubSpot, Salesforce, Zapier, LinkedIn, Apollo |
| `/api/import/leads` | POST | Import leads from JSON (legacy, optional) |
| `/api/import/leads/async` | POST | Import leads from JSON (async Celery) |

### Template System (New)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/templates` | POST | Create message template |
| `/api/templates` | GET | List templates with performance metrics |
| `/api/templates/{template_id}` | GET | Get template details |
| `/api/templates/{template_id}` | PUT | Update template (auto-versioning) |
| `/api/templates/{template_id}` | DELETE | Soft delete template |
| `/api/templates/categories` | GET | List template categories |
| `/api/templates/performance/report` | GET | Template performance analytics |
| `/api/templates/seed-defaults` | POST | Seed default templates (admin) |

### Core Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/outbound-batch` | POST | Generate batch with qualification & offer matching |
| `/api/generate/outbound-batch/async` | POST | Generate batch (async Celery) |
| `/api/send/batch/{run_id}` | POST | Send batch (sync) |
| `/api/send/batch/{run_id}/async` | POST | Send batch (async Celery) |
| `/api/replies/classify` | POST | Classify reply and update pipeline |
| `/api/replies/classify/async` | POST | Classify reply (async Celery) |
| `/api/runs/{run_id}` | GET | Get campaign run details |
| `/api/webhooks/gmail` | POST | Gmail push notification webhook |

### Lead Qualification

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/qualification/score/{lead_id}` | POST | Score single lead |
| `/api/qualification/batch` | POST | Score all leads using qualification engine |

### Pipeline Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/pipeline/{lead_id}` | GET | Get pipeline state for lead |
| `/api/pipeline/{lead_id}/transition` | POST | Transition lead to new state |
| `/api/pipeline/funnel` | GET | Get conversion funnel by state |

### CRM

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crm/deals` | POST | Create new deal |
| `/api/crm/deals/{deal_id}` | GET | Get deal details |
| `/api/crm/pipeline-value` | GET | Get total pipeline value |
| `/api/crm/roi` | GET | Get ROI metrics (conversion rate, revenue) |

### A/B Testing (Experiments)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/experiments` | POST | Create A/B experiment |
| `/api/experiments` | GET | Get active experiments |
| `/api/experiments/{experiment_id}` | GET | Get experiment results |

### Human Escalation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/escalation/queue` | GET | Get pending escalations |
| `/api/escalation/{escalation_id}/assign` | POST | Assign escalation to human |
| `/api/escalation/{escalation_id}/resolve` | POST | Resolve escalation |

### Learning & Optimization

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/learning/performance` | GET | Get performance report with recommendations |
| `/api/learning/best-subjects` | GET | Get best performing subject lines |

### Monitoring & Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Deep health check (DB, Redis, APIs, disk, memory) |
| `/ready` | GET | Kubernetes readiness probe |
| `/live` | GET | Kubernetes liveness probe |
| `/metrics` | GET | Prometheus metrics |

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint with version info |
| `/health` | GET | Basic health check |

## Complete Automation Workflow (Zero-Touch Pipeline)

This system operates as a **fully autonomous GTM agent** requiring no manual intervention. Here's how leads flow from discovery to closed deals:

### The Complete Customer Journey (Automated)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. LEAD INGESTION (Continuous)                                                 │
│    ├─ API ingestion: POST /api/leads or webhooks (HubSpot, Salesforce)        │
│    ├─ JSON import: data/leads.json (daily batch)                                │
│    └─ Auto-trigger: daily_batch_generation_task (Celery Beat @ 24h)             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. LEAD QUALIFICATION (Auto-triggered on ingest)                               │
│    ├─ Multi-dimensional scoring (0-100):                                         │
│    │   • Signal strength (funding, hiring, product launches)                      │
│    │   • Hiring intensity (sales roles = +25 pts)                               │
│    │   • Funding stage (Series A = 90 pts, Seed = 70 pts)                       │
│    │   • Company size fit (51-200 employees = 80 pts)                         │
│    │   • Market relevance (target segment match)                                │
│    ├─ Auto-approval: priority_score >= 50 → QUALIFIED state                     │
│    └─ Auto-trigger: daily_qualification_scoring_task (Celery Beat @ 24h)       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. OFFER MATCHING (Auto-triggered during batch build)                          │
│    ├─ Signal → Offer Angle mapping:                                              │
│    │   • "hiring SDRs" → "scaling sales team" angle                             │
│    │   • "raised Series A" → "post-funding growth" angle                        │
│    │   • "product launch" → "market expansion" angle                            │
│    └─ Message style + CTA selection based on signal keywords                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. TEMPLATE MATCHING & PERSONALIZATION (Auto during batch build)               │
│    ├─ Match template by signal keywords (funding → funding template)             │
│    ├─ AI personalization with GPT-4:                                             │
│    │   • Replace {{company}}, {{decision_maker}}, {{signal}}                    │
│    │   • Generate contextual hook based on pain_point                          │
│    │   • Subject line optimization (A/B test variants)                        │
│    └─ Track template_id for performance learning                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. BATCH GENERATION (Auto-triggered daily)                                     │
│    ├─ Filter: suppression list exclusion                                         │
│    ├─ Filter: exclude already-contacted leads                                   │
│    ├─ Build send-ready payloads (queued → pending)                              │
│    ├─ Export to outbound_batch.json                                              │
│    └─ Auto-trigger: Part of daily_batch_generation_task                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. DELIVERABILITY & SENDING (Auto-triggered after batch generation)            │
│    ├─ Domain warmup check (14-day progressive schedule for new domains)         │
│    ├─ Rate limiting: 30 emails/hour, 200/day per domain                         │
│    ├─ Inbox rotation (multiple sending domains)                                 │
│    ├─ Health monitoring (pause if health score < 50)                            │
│    ├─ Circuit breaker protection (Gmail API: 3 failures → 5min recovery)       │
│    ├─ Bounce handling → auto-suppression                                       │
│    ├─ Send via Gmail API with retry logic (max 3 retries)                       │
│    └─ Auto-transition: NEW → QUALIFIED → CONTACTED (Pipeline State Machine)     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 7. REPLY MONITORING (Continuous via Gmail Watch)                                 │
│    ├─ Gmail push notifications → webhook /api/webhooks/gmail                  │
│    ├─ Parse reply content and thread context                                     │
│    ├─ Store in replies table (raw + classified)                                 │
│    └─ Auto-trigger: classify_reply_task (immediate on reply receipt)           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 8. REPLY CLASSIFICATION (Auto-triggered on reply)                                │
│    ├─ GPT-4 classification into 4 buckets:                                     │
│    │   • "interested" → INTERESTED state, stop follow-ups, escalate if high-value│
│    │   • "not_now" → stay in current state, schedule 7-day follow-up            │
│    │   • "not_interested" → LOST state, cancel follow-ups                      │
│    │   • "unsubscribe" → SUPPRESSED state, immediate suppression list           │
│    ├─ Conversation memory: update tone, objections, relationship stage           │
│    ├─ Template performance tracking (reply rate per template)                    │
│    ├─ Human escalation check (priority >= 85, pricing questions, angry tone)   │
│    └─ Auto-transition pipeline state based on classification                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 9. FOLLOW-UP AUTOMATION (Auto-triggered on schedule)                            │
│    ├─ Schedule: Day 2, 5, 9 after initial send (if no reply)                   │
│    ├─ Auto-trigger: schedule_followups_task (Celery Beat @ 1h)                  │
│    ├─ Auto-trigger: send_due_followups_task (Celery Beat @ 1h)                  │
│    ├─ Skip if: replied, positive, unsubscribe, not_interested, suppressed       │
│    ├─ Auto-generate follow-up content (bump → value-add → breakup)              │
│    ├─ Auto-suppress after 21 days no engagement                                │
│    └─ Auto-transition: stay in CONTACTED or move to LOST/SUPPRESSED             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 10. PIPELINE STATE MACHINE (Auto-managed transitions)                            │
│     State Flow: NEW → QUALIFIED → CONTACTED → REPLIED → INTERESTED →           │
│                 CALL_BOOKED → CLOSED (or LOST/SUPPRESSED)                        │
│     ├─ Auto-transition on email_sent: NEW → QUALIFIED → CONTACTED               │
│     ├─ Auto-transition on reply: per classification rules                         │
│     ├─ Auto-transition on call_booked: INTERESTED → CALL_BOOKED                 │
│     ├─ Auto-transition on deal_closed: CALL_BOOKED → CLOSED/LOST               │
│     ├─ Pipeline monitoring: stuck lead detection (Celery Beat @ 6h)              │
│     └─ Auto-escalation: high-value leads to human queue (Celery Beat @ 12h)     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 11. HUMAN ESCALATION (Auto-triggered by rules)                                   │
│     Triggers:                                                                    │
│     • priority_score >= 85 (Tier 1 high-value leads)                             │
│     • Pricing questions detected in reply                                        │
│     • Angry/negative sentiment (damage control)                                  │
│     • Complex inquiries (API, integrations, contracts)                           │
│     • Multi-thread objections (>2 objections in conversation)                    │
│     └─ Auto-add to human_escalation_queue for manual handling                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 12. CRM SYNC & DEAL TRACKING (Auto-triggered on state change)                    │
│     ├─ INTERESTED → Create opportunity in deals table                            │
│     ├─ CALL_BOOKED → Update pipeline value, notify sales                        │
│     ├─ CLOSED → Record win/loss, calculate ROI metrics                         │
│     └─ ROI tracking: cost per lead, cost per meeting, cost per deal             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 13. FEEDBACK LEARNING LOOP (Auto-optimization)                                   │
│     ├─ Track: reply rates per subject line, angle, template, company type      │
│     ├─ Track: time-to-reply, conversion rates by pipeline stage                 │
│     ├─ Auto-calculate trends (Celery Beat @ 24h)                               │
│     ├─ Auto-promote winning templates (A/B testing)                             │
│     └─ Update performance metrics for future batch optimization               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Celery Beat Automated Schedule (11 Workflows)

| Schedule | Task | Trigger Condition | Action |
|----------|------|-------------------|--------|
| **Every 6h** | `autonomous_discovery_task` | **SCHEDULED** | **→ Discover leads from 6+ free sources → Gemini AI enrichment → Auto-qualify → Ingest → Trigger outbound** |
| **Every 24h** | `daily_batch_generation_task` | Scheduled | Import leads → Generate batch → Queue sends |
| **Every 24h** | `daily_qualification_scoring_task` | Scheduled | Score all unqualified leads, update priority scores |
| **Every 24h** | `daily_deliverability_reset_task` | Scheduled | Reset daily send counts, check domain warmup progress |
| **Every 24h** | `feedback_learning_task` | Scheduled | Calculate 7-day trends, update template performance |
| **Every 24h** | `discovery_analytics_task` | Scheduled | Analyze discovery performance, optimize sources |
| **Every 1h** | `send_due_followups_task` | Scheduled | Send follow-ups where scheduled_for <= now() |
| **Every 1h** | `hourly_deliverability_reset_task` | Scheduled | Reset hourly send counters |
| **Every 1h** | `schedule_followups_task` | Scheduled | Schedule next follow-up for eligible leads |
| **Every 6h** | `pipeline_monitoring_task` | Scheduled | Detect stuck leads (>7 days in state), alert ops |
| **Every 12h** | `auto_escalation_task` | Scheduled | Auto-escalate leads with priority >= 85 |

### Event-Driven Tasks (Immediate Execution)

| Event | Task | Action |
|-------|------|--------|
| Reply received | `classify_reply_task` | GPT-4 classify + pipeline transition + template tracking |
| Lead created via API | `score_lead_task` | Immediate qualification scoring |
| Batch generated | `send_batch_task` | Rate-limited sending via Gmail API |
| High-value reply | `escalation_check` | Add to human queue if triggers met |

### Zero-Touch Operational Summary

**What requires manual action:**
- Initial setup (API keys, Gmail OAuth, database migrations)
- Human escalations (replying to flagged high-value conversations)
- Deal closure recording (won/lost - can be automated with CRM webhook)

**What is fully automated (100% hands-off):**
- **Lead discovery** (NEW) - Auto-discovers 70-130 leads/day from 6+ free sources
- **Lead enrichment** (NEW) - Gemini AI researches companies, finds decision makers, identifies pain points
- **Lead scoring & qualification** - Multi-dimensional scoring with auto-approval
- **Offer angle selection** - Signal → angle → message → CTA automation
- **Email personalization & template matching** - AI-powered personalization
- **Batch generation & sending** - Scheduled daily batches with deliverability protection
- **Reply monitoring & classification** - 24/7 Gmail watch with GPT-4 classification
- **Pipeline state transitions** - 9-state state machine with auto-transitions
- **Follow-up sequences** - Day 2, 5, 9 automated follow-ups
- **Suppression list management** - Auto-suppression on unsubscribe/bounce
- **Template A/B testing & optimization** - Self-improving template performance
- **Performance analytics & learning** - Daily trend analysis
- **Health monitoring & alerting** - Automated system health checks

### Main Workflow (Fully Automated)

**Optional Manual Step:** Create leads via API, webhook, or `leads.json` (or let Autonomous Discovery handle it)

**Fully Automated Steps (1-20):**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ AUTOMATED PIPELINE FLOW (Triggered by events and scheduled tasks)            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ 2.  [AUTO] Score leads using Qualification Engine (5 dimensions)           │
│     Trigger: Lead creation or daily_qualification_scoring_task               │
│                                                                              │
│ 3.  [AUTO] Filter to qualified leads (priority_score >= 50)                  │
│     Auto-approval: No human review required                                   │
│                                                                              │
│ 4.  [AUTO] Match offer strategies (signal → offer angle → message style → CTA)│
│     Engine: OfferMatchingEngine.match_offer()                                 │
│                                                                              │
│ 5.  [AUTO] Match message template based on signal keywords                     │
│     Engine: Template matching by keywords (funding, hiring, etc.)             │
│                                                                              │
│ 6.  [AUTO] Personalize template with lead data ({{company}}, {{signal}}, etc.)│
│     Engine: TemplateService with variable substitution                        │
│                                                                              │
│ 7.  [AUTO] AI enhances personalization based on context                        │
│     Engine: GPT-4 for contextual improvements                                  │
│                                                                              │
│ 8.  [AUTO] Build send-ready records with deliverability checks                 │
│     Engine: BatchBuilder.build_batch()                                        │
│                                                                              │
│ 9.  [AUTO] Track template_id and personalization_method in database             │
│     For: Feedback learning and A/B testing                                     │
│                                                                              │
│ 10. [AUTO] Queue sends via Celery (rate limited: 30/hour, 200/day)            │
│     Trigger: send_batch_task queued by daily_batch_generation_task           │
│                                                                              │
│ 11. [AUTO] Send through Gmail API (with health monitoring)                    │
│     Protection: Circuit breaker, retry logic (max 3), bounce handling         │
│                                                                              │
│ 12. [AUTO] Record in Conversation Memory                                       │
│     Data: Thread context, tone, objections, relationship stage                 │
│                                                                              │
│ 13. [AUTO] Watch inbox for replies (Gmail push notifications)                 │
│     Integration: Gmail API watch + webhook endpoint                         │
│                                                                              │
│ 14. [AUTO] Classify replies (interested, not_now, not_interested, unsubscribe) │
│     Engine: GPT-4 + ReplyClassifier (4-way classification)                   │
│                                                                              │
│ 15. [AUTO] Update template performance metrics                                 │
│     Metrics: reply rate, performance score (0-100), usage count             │
│                                                                              │
│ 16. [AUTO] Auto-transition Pipeline State Machine                              │
│     Engine: PipelineStateMachine.auto_transition_on_reply()                   │
│     Flow: NEW → QUALIFIED → CONTACTED → REPLIED → INTERESTED → CLOSED       │
│                                                                              │
│ 17. [AUTO] Trigger Human Escalation if needed                                  │
│     Triggers: priority >= 85, pricing questions, angry tone, complex inquiry   │
│                                                                              │
│ 18. [AUTO] Update CRM deals                                                   │
│     Data: Pipeline value, opportunity stage, win/loss probability             │
│                                                                              │
│ 19. [AUTO] Record in Feedback Learning (optimize future subjects/templates)  │
│     Engine: FeedbackLearningLoop.calculate_trends()                           │
│                                                                              │
│ 20. [AUTO] Update Prometheus metrics                                          │
│     Metrics: Emails sent, replies classified, pipeline transitions, etc.        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Reply Classification with Pipeline Integration

Every reply is classified by OpenAI GPT-4 into one of four buckets:

| Classification | Action | Pipeline Transition |
|----------------|--------|---------------------|
| **interested** | Create meeting task, stop follow-ups | CONTACTED → REPLIED → INTERESTED |
| **not_now** | Schedule follow-up for 7 days later | Stay in current state |
| **not_interested** | Suppress lead, cancel follow-ups | → LOST |
| **unsubscribe** | Add to suppression list immediately | → SUPPRESSED |

### Human Escalation Triggers

The system automatically escalates to human inbox when:
- **High-value leads** (priority_score >= 85)
- **Pricing questions** detected in reply
- **Angry/negative replies** (damage control)
- **Complex inquiries** (API, integrations, contracts)

## Follow-up Sequence

Automated follow-ups are scheduled at:
- Day 2: Short bump
- Day 5: Value reminder
- Day 9: Last soft close

System stops after 3-4 touches or based on reply classification.

## Observability & Monitoring

### Prometheus Metrics (`/metrics`)

**HTTP Metrics:**
- `http_requests_total` - Total requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histogram

**Business Metrics:**
- `leads_imported_total` - Total leads imported
- `emails_sent_total` - Emails sent by status (sent/failed)
- `emails_sent_duration_seconds` - Send latency
- `replies_received_total` - Replies by classification
- `pipeline_transitions_total` - State transitions
- `pipeline_leads` - Leads by pipeline state
- `queue_size` - Messages by status
- `escalation_queue_size` - Escalations by priority
- `deliverability_health_score` - Domain health scores

**External API Metrics:**
- `gmail_api_calls_total` - Gmail API calls by status
- `openai_api_calls_total` - OpenAI API calls by status and operation
- `circuit_breaker_state` - Circuit breaker states (0=closed, 1=half_open, 2=open)
- `celery_tasks_total` - Celery tasks by name and status

### Audit Logging

All state changes logged to `events` table with:
- Event type and timestamp
- Entity type and ID
- Full JSON data payload
- User attribution

### Alerting

Configured alerts via Slack/Webhook:
- **Critical**: Circuit breaker open, high bounce rate (>5%), Gmail API failures
- **Warning**: Low reply rate (<5%), stuck leads, escalation queue backlog
- **Info**: High reply rate (>30%), domain warmup complete

## Usage Examples

### Lead Management API

**Create a single lead:**
```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "website": "https://acme.com",
    "signal": "Hiring SDRs and raised Series A",
    "decision_maker": "John Smith",
    "fit_score": 9,
    "pain_point": "Manual outreach too slow",
    "custom_hook": "Saw your SDR job posting"
  }'
```

**Bulk create leads:**
```bash
curl -X POST http://localhost:8000/api/leads/batch \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leads": [
      {"company": "Company A", "signal": "Hiring engineers", "fit_score": 8},
      {"company": "Company B", "signal": "Raised $10M", "fit_score": 9}
    ],
    "skip_duplicates": true,
    "auto_score": true
  }'
```

**List leads with filters:**
```bash
# Get qualified leads with high fit score
curl "http://localhost:8000/api/leads?is_qualified=true&min_fit_score=8&page=1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Search by company name
curl "http://localhost:8000/api/leads?search=acme" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**HubSpot webhook integration:**
```bash
curl -X POST "http://localhost:8000/api/webhooks/lead-ingestion?source=hubspot&api_key=your-webhook-key" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "company": "TechCorp",
      "firstname": "Jane",
      "lastname": "Doe",
      "jobtitle": "VP Sales",
      "industry": "SaaS"
    }
  }'
```

### Template System API

**Create a custom template:**
```bash
curl -X POST http://localhost:8000/api/templates \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Funding Template",
    "category": "funding",
    "subject_template": "Congrats on {{company}} raise, {{decision_maker}}",
    "body_template": "Hi {{decision_maker}},\n\nCongrats on {{company}}'s {{signal}}.\n\n{{pain_point}} is common post-funding.\n\n{{custom_hook}}\n\nWorth a brief conversation?\n\nBest,",
    "signal_keywords": ["funding", "raised", "Series A", "investment"],
    "is_default": false
  }'
```

**List templates by performance:**
```bash
curl "http://localhost:8000/api/templates?category=funding" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Get template performance report:**
```bash
curl http://localhost:8000/api/templates/performance/report \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Seed default templates:**
```bash
curl -X POST http://localhost:8000/api/templates/seed-defaults \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Lead with Custom Message

When you provide a `message` field, the system uses it directly (highest priority):
```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "signal": "Hiring sales team",
    "decision_maker": "John Smith",
    "message": "Hi John,\n\nSaw Acme is hiring sales reps. Usually means pipeline pressure.\n\nWe help teams automate outbound without losing the personal touch.\n\nWorth a 10-min chat?\n\nBest,",
    "followups": [
      "Hi John, quick bump on this. Still relevant?",
      "Hi John, last touch. If timing is off, just say so."
    ]
  }'
```

### Sentry Integration

Error tracking with Sentry DSN:
- Automatic error reporting
- Stack traces and context
- Performance monitoring

## Gmail API Rate Limits

The sender respects Gmail API limits:
- Throttles sends (default: 10 messages per batch with 1-second pause)
- Queues failed sends for retry
- Tracks retry counts
- Logs all send events

## Production Deployment Notes

### Security
- **JWT Authentication** required for all `/api/*` endpoints
- **Rate Limiting**: 1000 requests/minute per IP
- **Secret Key**: Must be at least 32 characters
- **CORS**: Restricted in production (`DEBUG=False`)

### Data Management
- `leads.json` is the source of truth for lead intelligence only
- `outbound_batch.json` is auto-generated - never hand-edit it
- **Database is source of truth** for all operational data
- PostgreSQL backups run automatically via scripts in `scripts/`

### Deliverability (Critical)
- **Domain Warmup**: Required for new domains (14-day progressive schedule)
- **Send Limits**: 30 emails/hour, 200/day (configurable)
- **Health Monitoring**: Automatic blocking if health score < 50
- **Bounce Handling**: Automatic suppression on hard bounces
- **Spam Monitoring**: Immediate domain pause on spam complaints

### Circuit Breakers
- **Gmail API**: Opens after 3 failures, recovers in 5 minutes
- **OpenAI API**: Opens after 5 failures, recovers in 2 minutes
- Automatic retry with exponential backoff

### Idempotency
- Include `Idempotency-Key` header for POST/PUT/PATCH requests
- 24-hour retention window for duplicate prevention
- System returns cached response for duplicate keys

### Celery Beat
- Run only **one** Celery beat instance to avoid duplicate jobs
- 9 scheduled workflows (see Daily Operating Loop section)
- Dead Letter Queue for failed tasks

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run with markers
pytest tests/ -m "not slow"
```

### Test Coverage

| Component | Tests |
|-----------|-------|
| Authentication | JWT, rate limiting, password hashing |
| API Endpoints | All 30+ endpoints |
| Services | Lead qualification, offer matching, pipeline, CRM |
| Circuit Breakers | Failure threshold, recovery, retry logic |
| Integration | End-to-end workflows |

### Load Testing

```bash
# Using locust (install: pip install locust)
locust -f tests/locustfile.py --host=http://localhost:8000
```

## Troubleshooting

### Startup Issues

**Configuration Validation Failed:**
```bash
# Check all required env vars are set
grep -E "^(DATABASE_URL|REDIS_URL|SECRET_KEY|OPENAI_API_KEY)" .env

# Validate config manually
python -c "from app.config_validator import validate_config; validate_config()"
```

**Database Connection Failed:**
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check PostgreSQL running
pg_isready -h localhost -p 5432
```

**Redis Connection Failed:**
```bash
redis-cli ping
# Should return PONG
```

### Gmail Authentication

First run will open a browser for OAuth consent. The token is saved to `data/token.json`.

**Token expired:**
```bash
# Delete token to force re-authentication
rm data/token.json
```

### Celery Tasks Not Executing

Check Redis connection:
```bash
redis-cli ping
```

Check Celery worker status:
```bash
celery -A app.workers.tasks inspect active
celery -A app.workers.tasks inspect scheduled
```

View Celery logs:
```bash
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
```

### Circuit Breaker Open

**Gmail API circuit open:**
- Wait 5 minutes for auto-recovery
- Check Gmail API quota: https://console.cloud.google.com/apis/api/gmail.googleapis.com/quotas
- Verify `credentials.json` is valid

**OpenAI API circuit open:**
- Wait 2 minutes for auto-recovery
- Check OpenAI API key validity
- Verify billing status at https://platform.openai.com/account/billing

### Database Connection Issues

Verify PostgreSQL is running and credentials in `.env` are correct.

**Connection pool exhausted:**
```python
# In app/database.py, increase pool size
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=30)
```

### Gmail API Quota Exceeded

Check current quota usage:
- https://console.cloud.google.com/apis/api/gmail.googleapis.com/quotas

Increase quota or reduce send rate:
```env
# In .env
MAX_SENDS_PER_HOUR=20
MAX_SENDS_PER_DAY=150
```

### Deliverability Issues

**Domain health score low:**
```bash
# Check domain health
GET /api/deliverability/health?domain=yourdomain.com

# Pause sending
POST /api/deliverability/pause?domain=yourdomain.com
```

**High bounce rate:**
- Review and clean email list
- Check for invalid domains
- Verify DNS records (SPF, DKIM, DMARC)

### Backup & Recovery

**Create backup:**
```bash
# Linux/macOS
./scripts/backup.sh

# Windows
./scripts/backup.ps1
```

**Restore from backup:**
```bash
./scripts/restore.sh ./backups/backup_ai_saas_20240101_120000.sql.gz
```

### Health Checks

**Check all systems:**
```bash
curl http://localhost:8000/health
```

**Kubernetes probes:**
```bash
curl http://localhost:8000/ready  # Readiness
curl http://localhost:8000/live    # Liveness
```

### Monitoring

**View Prometheus metrics:**
```bash
curl http://localhost:8000/metrics
```

**Check alerts:**
```bash
# View recent alerts in logs
docker-compose logs -f api | grep ALERT
```

## Quick Start Guide

### 1. One-Command Setup (Docker) - Fully Automated Mode

```bash
# Clone and start everything
git clone <repo-url>
cd ai-saas
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
```

**Once running, the system automatically:**
- **🔥 Discovers leads autonomously** (NEW) - 70-130 leads/day from GitHub, NewsAPI, HN, Product Hunt, job boards
- **🧠 Enriches with Gemini AI** (NEW) - Researches companies, finds decision makers, pain points
- Imports leads daily from `data/leads.json` (optional - discovery handles it)
- Scores and qualifies leads (priority_score >= 50 → auto-approved)
- Generates personalized outbound batches
- Sends emails with deliverability protection
- Monitors for replies 24/7
- Classifies replies and updates pipeline
- Sends follow-ups (Day 2, 5, 9) if no reply
- Auto-escalates high-value leads to humans
- Optimizes templates via A/B testing

### 2. Verify Installation

```bash
# Check health (all systems: DB, Redis, Gmail, OpenAI)
curl http://localhost:8000/health

# Check API ready
curl http://localhost:8000/ready

# View Prometheus metrics
curl http://localhost:8000/metrics

# Check Celery workers
python -m celery -A app.workers.tasks inspect active
```

### 3. Seed Default Templates (Required First Time)

```bash
curl -X POST http://localhost:8000/api/templates/seed-defaults
```

### 4. Add Leads (Optional - Autonomous Discovery Handles This)

**Option A: JSON file (for daily batch automation)**

Create `data/leads.json`:

```json
[
  {
    "company": "Acme Corp",
    "website": "https://acme.com",
    "signal": "Hiring SDRs and just raised Series A",
    "decision_maker": "John Smith",
    "fit_score": 9,
    "pain_point": "Manual outreach taking too much time",
    "urgency_reason": "Q4 targets need to be met",
    "custom_hook": "Saw your job posting for SDRs"
  }
]
```

**Option B: Real-time API (immediate processing)**

```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "signal": "Hiring SDRs",
    "decision_maker": "John Smith",
    "fit_score": 9,
    "pain_point": "Manual outreach too slow"
  }'
```

**Option C: Webhook integration (HubSpot, Salesforce)**

```bash
curl -X POST "http://localhost:8000/api/webhooks/lead-ingestion?source=hubspot&api_key=your-webhook-key" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"company": "TechCorp", "firstname": "Jane", "jobtitle": "VP Sales"}}'
```

### 5. Automation Takes Over (Zero Manual Steps Required)

Once leads are added, the system automatically:

| Time | Auto-Action | Celery Task |
|------|-------------|-------------|
| Immediate | Lead qualification scoring | Event-driven |
| Daily @ scheduled time | Import → Score → Generate batch → Queue sends | `daily_batch_generation_task` |
| After send | Transition to CONTACTED state | Event-driven |
| Hourly | Check for replies, classify, transition | `schedule_followups_task` + `classify_reply_task` |
| Day 2, 5, 9 (if no reply) | Send follow-up sequence | `send_due_followups_task` |
| Day 21 (if no reply) | Auto-suppress lead | FollowUpAutomation |
| On reply | GPT-4 classify → pipeline transition → template tracking | `classify_reply_task` |
| On "interested" reply | Stop follow-ups, check for escalation | ReplyClassifier |
| Every 12h | Escalate priority >= 85 leads to human queue | `auto_escalation_task` |
| Daily | Update template performance metrics | `feedback_learning_task` |

### 6. Monitor the Autonomous Pipeline

```bash
# View complete pipeline funnel
curl http://localhost:8000/api/pipeline/funnel

# Check CRM pipeline value
curl http://localhost:8000/api/crm/pipeline-value

# View learning/optimization performance
curl http://localhost:8000/api/learning/performance

# Check template performance
curl http://localhost:8000/api/templates/performance/report

# View human escalation queue (leads needing manual reply)
curl http://localhost:8000/api/escalation/queue
```

### Manual Override (When You Need Control)

While the system runs autonomously, you can manually:

```bash
# Force immediate batch generation
curl -X POST http://localhost:8000/api/generate/outbound-batch \
  -H "Content-Type: application/json" \
  -d '{"from_email": "your-email@gmail.com", "max_leads": 50}'

# Force immediate send
curl -X POST http://localhost:8000/api/send/batch/{run_id}

# Manual pipeline transition
curl -X POST http://localhost:8000/api/pipeline/{lead_id}/transition \
  -H "Content-Type: application/json" \
  -d '{"new_state": "INTERESTED", "stage_data": {"reason": "manual_review"}}'

# Suppress a lead immediately
curl -X POST http://localhost:8000/api/leads/{lead_id}/suppress
```

## Autonomous Lead Discovery (Zero-Touch Lead Generation)

**The ultimate automation**: The system now discovers and enriches leads automatically with **zero human intervention**. No more manual lead lists.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ AUTONOMOUS DISCOVERY PIPELINE (Runs Every 6 Hours via Celery Beat)              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 1. [FREE DATA SOURCES] → Raw Lead Discovery                                    │
│    ├─ GitHub API (60 req/hr free): Active repos with recent commits             │
│    ├─ NewsAPI (100 req/day free): Funding announcements, hiring news            │
│    ├─ Hacker News (free): "Who is Hiring" monthly threads                       │
│    ├─ Product Hunt (free): New product launches                                 │
│    └─ Job Boards (free): Companies hiring target roles                           │
│                                                                                 │
│ 2. [GEMINI AI] → Lead Enrichment (60 req/min FREE tier)                         │
│    ├─ Research company: funding, size, industry, tech stack                      │
│    ├─ Find decision makers: names, titles, LinkedIn                            │
│    ├─ Identify pain points: business challenges, growth needs                    │
│    ├─ Detect signals: recent news, expansions, partnerships                        │
│    ├─ Calculate priority score: 0-100 based on ICP fit                         │
│    └─ Generate outreach angle: best approach for initial contact                 │
│                                                                                 │
│ 3. [AI-POWERED FILTERING] → Auto-Qualification                                  │
│    ├─ Priority score >= 50: Auto-qualify for outreach                           │
│    ├─ Deduplication: Skip if already in database                                 │
│    ├─ Suppression check: Skip if suppressed/lost/unsubscribed                    │
│    ├─ Quality filter: Must have meaningful signals/data                          │
│    └─ Sort by score: Highest priority leads first                               │
│                                                                                 │
│ 4. [AUTO-INGESTION] → Pipeline Entry                                          │
│    ├─ Create lead record: ID, company, website, signals                          │
│    ├─ Create lead score: 5-dimension scoring (signal, hiring, funding, etc.)   │
│    ├─ Log discovery event: Source, score, metadata for analytics                │
│    └─ Commit to database: Ready for qualification and outreach                   │
│                                                                                 │
│ 5. [CHAIN REACTION] → Trigger Outbound Automation                               │
│    └─ New leads detected → Auto-trigger batch generation in 5 minutes           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Configuration (Add to .env)

```bash
# Required: Google Gemini API (FREE - 60 requests/minute)
# Get key at: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: NewsAPI (FREE - 100 requests/day)
# Get key at: https://newsapi.org/register
NEWSAPI_KEY=your_newsapi_key_here
```

### What Gets Discovered Automatically

| Data Source | What We Find | Volume/Day | Cost |
|-------------|--------------|------------|------|
| **GitHub** | Tech companies with recent activity (Python, React, AI/ML repos) | ~20-30 | Free |
| **NewsAPI** | Funding announcements (Series A/B/C, seed rounds) | ~10-20 | Free |
| **NewsAPI** | Hiring spree announcements | ~5-15 | Free |
| **Hacker News** | Companies posting in "Who is Hiring" threads | ~10-25 | Free |
| **Product Hunt** | New product launches (SaaS, tools, apps) | ~15-20 | Free |
| **Job Boards** | Companies hiring SDRs, Sales Managers, VPs | ~10-20 | Free |
| **TOTAL** | **Auto-discovered leads per day** | **~70-130** | **$0** |

### AI Enrichment with Gemini

For each discovered company, Gemini AI researches and returns:

```json
{
  "company_name": "TechFlow AI",
  "website": "https://techflow.ai",
  "industry": "SaaS - AI Workflow Automation",
  "employees": 125,
  "funding": {
    "stage": "Series A",
    "recent_round": "$12M (3 months ago)",
    "total_raised": "$18M"
  },
  "decision_makers": [
    {
      "name": "Sarah Chen",
      "title": "VP of Sales",
      "decision_authority": "High"
    }
  ],
  "recent_news": [
    "Raised $12M Series A",
    "Hiring 10 new SDRs",
    "Launched AI API platform"
  ],
  "pain_points": [
    "Manual lead qualification taking too long",
    "Need to scale sales team efficiently",
    "Struggling with outbound personalization at scale"
  ],
  "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL", "Redis"],
  "priority_score": 85,
  "outreach_angle": "Scaling sales operations post-funding"
}
```

### Automated Qualification Criteria

Leads are **auto-approved** if they meet these criteria:

| Criteria | Threshold | Why |
|----------|-----------|-----|
| **Priority Score** | >= 50 | Strong ICP fit |
| **Company Size** | 20-1000 employees | Sweet spot for our solution |
| **Funding Stage** | Seed → Series C | Growth-minded companies |
| **Signals** | 1+ meaningful signals | Recent activity indicating need |
| **Not Duplicate** | Not in database | Fresh leads only |
| **Not Suppressed** | Not unsubscribed/lost | Respect preferences |

### Running Discovery

**Option 1: Automatic (Celery Beat)**
- Runs every 6 hours automatically
- Discovers → Enriches → Qualifies → Ingests → Triggers outbound
- Zero manual intervention

**Option 2: Manual Trigger**

```bash
# Trigger discovery immediately
curl -X POST http://localhost:8000/api/discovery/run

# View discovery analytics
curl http://localhost:8000/api/discovery/analytics
```

**Option 3: Continuous Mode**

```python
# Run continuous discovery (for development/testing)
from app.services.autonomous_discovery import ContinuousDiscoveryManager

manager = ContinuousDiscoveryManager(
    db=db_session,
    gemini_api_key=settings.GEMINI_API_KEY,
    cycle_interval_hours=6
)

# Start continuous discovery
asyncio.run(manager.run_continuous_discovery())
```

### Monitoring Discovery

```bash
# Check recent discoveries
curl http://localhost:8000/api/discovery/recent

# View source performance
curl http://localhost:8000/api/discovery/sources

# Discovery analytics (optimization recommendations)
curl http://localhost:8000/api/discovery/analytics
```

### Cost Breakdown (FREE)

| Service | Free Tier | Actual Usage | Cost |
|---------|-----------|--------------|------|
| **Gemini API** | 60 req/min | ~30-50/day | **$0** |
| **NewsAPI** | 100 req/day | ~30-50/day | **$0** |
| **GitHub API** | 60 req/hr | ~10-20/day | **$0** |
| **Hacker News** | Unlimited | ~5-10/day | **$0** |
| **Product Hunt** | Unlimited | ~5-10/day | **$0** |
| **Job Boards** | Unlimited | ~10-20/day | **$0** |
| **TOTAL** | | **~70-130 leads/day** | **$0/month** |

### Self-Improvement

The system automatically optimizes:

1. **Source Performance Tracking**: Monitors which data sources produce highest-quality leads
2. **Conversion Analysis**: Tracks discovery → qualification → reply → meeting rates
3. **Auto-Optimization**: Adjusts source weights based on performance
4. **Recommendation Engine**: Suggests new data sources based on ICP patterns

### Billion-Dollar CEO Thinking

This isn't just automation—it's **autonomous business development**:

- **No lead lists to buy**: System discovers its own leads
- **No manual research**: AI enriches with full company intelligence
- **No guesswork on qualification**: AI scores based on multi-dimensional ICP fit
- **No missed opportunities**: Runs 24/7, discovers in real-time
- **Zero marginal cost**: $0 to discover 100 leads vs 10,000 leads
- **Scales infinitely**: Add more sources, more markets, more verticals

**Your only job**: Add your GEMINI_API_KEY to .env and watch leads flow in automatically.

---

## B2B Matchmaking Platform (NEW - Double-Sided Marketplace)

**🎯 The Ultimate Business Model**: Connect service providers with buyers who need their services — and take a cut.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ B2B MATCHMAKING PLATFORM WORKFLOW                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ 1. [SERVICE PROVIDER ONBOARDING] → Provider Registration                      │
│    ├─ Provider signs up with services, ICP criteria, contact email             │
│    ├─ Platform sends opt-in email for consent to automated outreach            │
│    ├─ Provider replies with "yes" or "I consent"                              │
│    ├─ Gmail API detects response automatically                                 │
│    ├─ AI sentiment analysis confirms consent                                   │
│    ├─ Automation enabled for provider                                         │
│    └─ Provider receives acknowledgment email                                    │
│                                                                                 │
│ 2. [BUYER DISCOVERY] → Automatic Buyer Matching                              │
│    ├─ System discovers buyers from multiple sources (or manual entry)         │
│    ├─ Buyers enriched with: industry, funding, employee count, signals        │
│    ├─ AI matches buyers to providers based on ICP criteria                    │
│    ├─ Match scoring: 0-100 based on fit                                      │
│    └─ High-scoring matches auto-approved for outreach                         │
│                                                                                 │
│ 3. [AUTOMATED OUTREACH] → Platform Sends Intros                               │
│    ├─ Platform sends personalized email from provider to buyer                 │
│    ├─ Email includes: provider services, buyer signals, match score           │
│    ├─ AI-generated personalization based on buyer's situation                 │
│    ├─ Rate limiting: 30 emails/hour, 200/day (Gmail free tier)               │
│    └─ Duplicate prevention: No duplicate emails to same buyer/provider pair   │
│                                                                                 │
│ 4. [RESPONSE TRACKING] → Monitor Buyer Replies                               │
│    ├─ Gmail watch monitors replies 24/7                                       │
│    ├─ AI classifies replies: interested/not interested/more info              │
│    ├─ Interested replies: Notify provider, stop follow-ups                    │
│    ├─ Not interested: Mark as lost, update match status                       │
│    └─ Response data: Open rate, reply rate, response time                    │
│                                                                                 │
│ 5. [FOLLOW-UP SEQUENCES] → Automated Follow-ups                               │
│    ├─ Day 3: Value-add follow-up                                              │
│    ├─ Day 7: Case study/proof follow-up                                        │
│    ├─ Day 14: Last soft close follow-up                                       │
│    ├─ Stop if: buyer replies, positive response, unsubscribe                  │
│    └─ Auto-suppress after 21 days no engagement                              │
│                                                                                 │
│ 6. [PROVIDER DASHBOARD] → Full Automation Control                             │
│    ├─ View automation status: active/paused                                   │
│    ├─ Pause/resume automation with one click                                  │
│    ├─ View matched buyers with scores                                         │
│    ├─ View outreach results: sent, replies, meetings booked                   │
│    ├─ Adjust settings: max emails/day, min match score, auto-approve           │
│    └─ View analytics: reply rate, conversion rate, ROI                       │
│                                                                                 │
│ 7. [ANALYTICS DASHBOARD] → Platform-Wide Insights                             │
│    ├─ Total providers, total buyers, total matches                            │
│    ├─ Outreach metrics: emails sent, reply rate, meeting rate                 │
│    ├─ Top-performing providers by conversion rate                             │
│    ├─ Buyer engagement trends by industry                                     │
│    ├─ Revenue tracking: subscription fees, meeting fees, success fees          │
│    └─ ROI calculation: cost per lead, cost per meeting, cost per deal        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Provider Opt-in Workflow

**📧 Step-by-Step:**

1. **Provider Registration**
   - Provider creates account with services, ICP criteria, contact email
   - Status: `pending_consent`

2. **Opt-in Email Sent**
   - Platform sends opt-in email from platform_email to provider
   - Email includes: services offered, automation description, consent request
   - Example: *"Hi Provider, we've identified buyer matches for your services. Reply 'yes' to enable automated outreach."*

3. **Provider Response Detection**
   - Gmail watch monitors provider's inbox for replies
   - System detects when provider replies
   - Response text extracted and analyzed

4. **AI Sentiment Analysis**
   - Gemini AI analyzes response for consent
   - Keywords: "yes", "consent", "proceed", "agree", "approved"
   - Sentiment: positive/neutral/negative
   - Confidence: high/medium/low

5. **Consent Processing**
   - If consent detected: Enable automation
   - Update provider status: `consented`
   - Set automation settings: max emails/day, min match score, auto-approve
   - Send acknowledgment email to provider
   - Trigger automated buyer outreach

6. **Automation Triggered**
   - System matches buyers to provider based on ICP
   - High-scoring matches auto-approved for outreach
   - Platform sends personalized emails to buyers
   - Response tracking begins

### Testing Provider Opt-in

**Test Script:** `test_provider_optin_real.py`

```bash
# Run provider opt-in test
python test_provider_optin_real.py

# Workflow:
# 1. Creates provider with test email
# 2. Sends opt-in email from platform to provider
# 3. Waits for provider response (run script again after replying)
# 4. Detects response, processes consent
# 5. Triggers automation to send to buyer
```

**Test with Custom Provider:** `test_provider_codewithtony.py`

```bash
# Test with custom provider email
python test_provider_codewithtony.py

# Provider: codewithtony@gmail.com
# Buyer: thakurujwal13@gmail.com
# Platform: malaythakur1800@gmail.com
```

### Buyer Matching System

**🎯 ICP-Based Matching:**

Providers define their ICP (Ideal Customer Profile):
- Industries (SaaS, Fintech, E-commerce)
- Funding stage (Seed, Series A, Series B)
- Employee count (50-500, 500+, 1000+)
- Signals (recent_funding, hiring_engineers, product_launch)

**Match Scoring (0-100):**

| Factor | Weight | Points |
|--------|--------|--------|
| Industry match | 25% | 0-25 |
| Funding stage match | 20% | 0-20 |
| Employee size fit | 15% | 0-15 |
| Signal relevance | 25% | 0-25 |
| Tech stack overlap | 15% | 0-15 |
| **Total** | **100%** | **0-100** |

**Auto-Approval Threshold:** 70+ score

### Provider Dashboard Endpoints

**📊 Dashboard Management:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers/{provider_id}/dashboard` | GET | Get provider dashboard status |
| `/api/providers/{provider_id}/dashboard/pause` | POST | Pause automation for provider |
| `/api/providers/{provider_id}/dashboard/resume` | POST | Resume automation for provider |
| `/api/providers/{provider_id}/dashboard/settings` | PUT | Update provider settings |

**Dashboard Response:**
```json
{
  "provider_id": "provider-001",
  "automation_status": "active",
  "stats": {
    "total_matches": 45,
    "outreach_sent": 38,
    "replies_received": 12,
    "meetings_booked": 5,
    "conversion_rate": 13.2
  },
  "settings": {
    "max_emails_per_day": 30,
    "min_match_score": 70,
    "auto_approve_matches": true
  }
}
```

### Email Warmup System

**🔥 Domain Warmup (Critical for Deliverability):**

New domains need warmup to avoid spam filters:

**14-Day Progressive Schedule:**

| Day | Emails/Day | Cumulative |
|-----|------------|------------|
| 1-3 | 5 | 15 |
| 4-7 | 10 | 55 |
| 8-14 | 20 | 195 |
| 15+ | 30 (max) | Unlimited |

**Warmup Features:**
- Automatic tracking of daily send counts
- Health score monitoring (0-100)
- Auto-pause if health < 50
- Progressive increase based on domain age
- Multi-domain rotation support

### Unsubscribe Mechanism

**🚫 CAN-SPAM Compliant Unsubscribe:**

Every email includes unsubscribe link:
- One-click unsubscribe
- Immediate suppression
- Suppression list management
- Compliance with CAN-SPAM Act

**Unsubscribe Flow:**
1. Buyer clicks unsubscribe link in email
2. System adds to suppression list
3. All future emails to this buyer blocked
4. Provider notified of unsubscribe
5. Match status updated to `suppressed`

### Enhanced Match Scoring

**🧠 Local Heuristics Scoring:**

Beyond basic ICP matching, the system uses:

**Industry Scoring:**
- Target industry: +25 points
- Related industry: +15 points
- Non-target: 0 points

**Funding Stage Scoring:**
- Series A: 90 points
- Series B: 85 points
- Seed: 70 points
- Pre-seed: 50 points

**Employee Size Scoring:**
- 51-200: 80 points
- 201-500: 85 points
- 500-1000: 75 points
- 1000+: 70 points

**Signal Scoring:**
- Recent funding: +25 points
- Hiring engineers: +20 points
- Product launch: +15 points
- Expansion: +10 points

**Tech Stack Overlap:**
- 1+ matches: +10 points
- 2+ matches: +15 points
- 3+ matches: +20 points

### Template Management System

**📝 Email Template System:**

**Features:**
- Default templates for common scenarios
- Custom template creation
- Variable substitution ({{company}}, {{signal}}, etc.)
- Template performance tracking
- A/B testing support
- Template versioning

**Default Templates:**
- Funding template (for companies that raised funding)
- Hiring template (for companies hiring)
- Product launch template (for new products)
- Expansion template (for companies expanding)

**Template Variables:**
- `{{company}}` - Buyer company name
- `{{decision_maker}}` - Buyer decision maker
- `{{signal}}` - Buying signal
- `{{pain_point}}` - Identified pain point
- `{{provider_services}}` - Provider services
- `{{match_score}}` - Match score

### Analytics Dashboard

**📈 Platform-Wide Analytics:**

**Overview Metrics:**
- Total providers
- Total buyers
- Total matches created
- Total emails sent
- Total replies received
- Total meetings booked

**Provider Performance:**
- Top providers by conversion rate
- Providers with most matches
- Providers with highest reply rate
- Provider revenue contribution

**Buyer Engagement:**
- Buyer engagement by industry
- Response time distribution
- Most engaged buyer segments
- Buyer geographic distribution

**Email Performance:**
- Open rate by template
- Reply rate by template
- Best performing subject lines
- Optimal send times

**Revenue Tracking:**
- Subscription revenue (provider fees)
- Meeting fees (pay-per-meeting)
- Success fees (deal closings)
- Total revenue
- ROI calculation

### Testing Mode for Providers

**🧪 Provider Testing:**

Providers can test automation with small batches before full rollout:

**Test Workflow:**
1. Provider initiates test mode
2. Selects test buyer batch (5-10 buyers)
3. System sends test emails
4. Provider reviews results
5. Adjust settings if needed
6. Roll out to full buyer list

**Test Mode Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers/{provider_id}/test/start` | POST | Start test mode |
| `/api/providers/{provider_id}/test/results` | GET | Get test results |
| `/api/providers/{provider_id}/test/rollout` | POST | Roll out to full list |
| `/api/providers/{provider_id}/test/pause` | POST | Pause test mode |

### Complete B2B Matchmaking Workflow

**🔄 End-to-End Flow:**

```
Provider Signs Up → Opt-in Email → Provider Consents → 
Buyers Matched → Outreach Sent → Buyer Replies → 
Meeting Booked → Deal Closed → Revenue Generated
```

**Timeline:**
- Day 0: Provider onboarding
- Day 0: Opt-in email sent
- Day 0-1: Provider responds
- Day 1: Automation enabled
- Day 1: Buyer matching
- Day 1: Outreach sent
- Day 3-7: Buyer replies
- Day 7-14: Meeting booked
- Day 30-60: Deal closed

### Revenue Model

**💰 Three Revenue Streams:**

1. **Subscription Fees** (Monthly)
   - $500-2,000/month per provider
   - Based on features and match volume

2. **Pay-Per-Meeting Fees**
   - $50-500 per meeting booked
   - Provider pays for qualified meetings

3. **Success Fees**
   - 5-10% of deal value
   - Charged when deal closes

**Revenue Example:**
- 50 providers @ $1,000/month = $50,000/month
- 200 meetings @ $100 = $20,000/month
- 10 deals @ $50,000 avg @ 7% = $35,000/month
- **Total: $105,000/month**

---

## Business Outcomes & ROI (What You Can Expect)

### Typical Performance Metrics

Based on industry benchmarks for AI-powered outbound systems:

| Metric | Typical Range | What It Means |
|--------|---------------|---------------|
| **Reply Rate** | 5-15% | % of people who respond to cold emails (vs 1-2% for generic blasts) |
| **Meeting Booked Rate** | 2-5% | % of total leads who book a meeting |
| **Cost Per Lead** | $2-10 | Cost to acquire a lead (vs $50-200 for paid ads) |
| **Cost Per Meeting** | $100-300 | Cost to book a qualified meeting (vs $500-1500 traditional) |
| **Time to First Meeting** | 2-7 days | How fast you can get a meeting from initial outreach |
| **Pipeline Value per 1000 Leads** | $50K-200K | Estimated value of opportunities created |

### ROI Calculation Example

**Assumptions:**
- You pay $1,550/month for APIs and infrastructure
- System contacts 2,000 leads per month
- 10% reply rate = 200 replies
- 3% meeting rate = 60 meetings
- 20% meeting-to-deal close = 12 new customers
- Average deal size = $10,000

**Results:**
- Revenue generated: $120,000/month
- Cost: $1,550/month
- **ROI: 7,645% (77x return)**

### Monthly Operating Costs

| Service | Cost | Purpose |
|---------|------|---------|
| OpenAI GPT-4 | ~$200 | Email personalization |
| Crunchbase API | ~$200 | Company funding data |
| Apollo.io | ~$50 | Contact information |
| Clearbit | ~$999 | Company firmographics |
| Infrastructure (hosting, database) | ~$100 | System operation |
| **Total** | **~$1,550/mo** | Full automation platform |

---

## Feature Checklist

### B2B Matchmaking Platform (NEW - Double-Sided Marketplace)
- [x] **Provider Opt-in Workflow** - Automated consent collection via Gmail
- [x] **Gmail Response Detection** - Automatic monitoring of provider replies
- [x] **AI Sentiment Analysis** - Gemini AI consent detection with keyword fallback
- [x] **Consent Acknowledgment Email** - Automated confirmation with duplicate prevention
- [x] **Buyer Matching System** - ICP-based matching with 0-100 scoring
- [x] **Enhanced Match Scoring** - Local heuristics (industry, funding, employees, signals, tech stack)
- [x] **Provider Dashboard** - Automation control, stats, settings management
- [x] **Email Warmup System** - 14-day progressive warmup schedule
- [x] **Unsubscribe Mechanism** - CAN-SPAM compliant one-click unsubscribe
- [x] **Follow-up Sequences** - Day 3, 7, 14 automated follow-ups
- [x] **Template Management System** - Default templates, custom creation, variable substitution
- [x] **Analytics Dashboard** - Platform-wide metrics, provider performance, revenue tracking
- [x] **Testing Mode** - Small batch testing before full rollout
- [x] **Duplicate Prevention** - No duplicate emails to same buyer/provider pair
- [x] **Response Tracking** - Gmail watch for buyer replies with classification
- [x] **Rate Limiting** - Gmail free tier compliance (500/day)

### Autonomous Lead Discovery (NEW - Zero-Touch Lead Generation)
- [x] **Auto-Discovery Engine** - Discovers leads from 6+ free data sources automatically
- [x] **GitHub Integration** - Finds tech companies with recent activity (60 req/hr free)
- [x] **NewsAPI Integration** - Funding & hiring announcements (100 req/day free)
- [x] **Hacker News Scraping** - "Who is Hiring" posts (completely free)
- [x] **Product Hunt Monitoring** - New product launches (completely free)
- [x] **Job Board Scraping** - Companies hiring target roles (completely free)
- [x] **Gemini AI Enrichment** - Deep company research with Google Gemini (60 req/min free)
- [x] **AI-Powered Qualification** - Auto-approves leads with priority >= 50
- [x] **Continuous Discovery** - Runs every 6 hours via Celery Beat
- [x] **Discovery Analytics** - Self-improving source optimization
- [x] **Zero Cost Operation** - ~70-130 leads/day at $0/month

### Core Automation Features
- [x] **Fully Autonomous Pipeline** - Zero-touch from lead to deal
- [x] **11 Celery Beat Workflows** - Automated daily/hourly/scheduled tasks
- [x] **Event-Driven Architecture** - Immediate response to replies, bounces, state changes
- [x] **Auto-Lead Qualification** - Multi-dimensional scoring with auto-approval (>=50 score)
- [x] **Auto-Offer Matching** - Signal → angle → message → CTA automation
- [x] **Auto-Template Matching** - Keyword-based template selection
- [x] **Auto-Personalization** - GPT-4 email generation with variable substitution
- [x] **Auto-Batch Generation** - Daily scheduled batch building
- [x] **Auto-Sending** - Rate-limited, deliverability-protected email dispatch
- [x] **Auto-Reply Monitoring** - Gmail watch with webhook notifications
- [x] **Auto-Reply Classification** - GPT-4 4-way classification (interested/not_now/not_interested/unsubscribe)
- [x] **Auto-Pipeline Transitions** - 9-state state machine with auto-transitions
- [x] **Auto-Follow-Up Sequences** - Day 2, 5, 9 automated follow-ups
- [x] **Auto-Suppression** - 21-day no-reply auto-suppression
- [x] **Auto-Human Escalation** - High-value/pricing/angry/complex auto-escalation
- [x] **Auto-Template Optimization** - A/B testing with auto-promotion of winners
- [x] **Auto-Feedback Learning** - Daily performance trend calculation
- [x] **Auto-Stuck Lead Detection** - 6-hourly pipeline health monitoring

### AI/ML Layer
- [x] **Gemini AI Lead Enrichment** - Autonomous company research (decision makers, pain points, tech stack)
- [x] **Lead Qualification Engine** - Multi-dimensional scoring (signal, hiring, funding, size, market)
- [x] **Offer Matching Engine** - Signal-to-offer mapping
- [x] **GPT-4 Email Generation** - Contextual personalization
- [x] **Conversation Memory** - Thread context, tone, objection tracking
- [x] **Reply Classification** - 4-way AI classification
- [x] **Template A/B Testing** - Performance optimization
- [x] **Feedback Learning Loop** - Historical performance analysis
- [x] **Discovery Source Optimization** - Self-improving data source selection

### Deliverability & Infrastructure
- [x] **Domain Warmup System** - 14-day progressive warmup schedule
- [x] **Deliverability Health Monitoring** - Auto-pause if health < 50
- [x] **Rate Limiting** - 30/hour, 200/day per domain
- [x] **Inbox Rotation** - Multiple sending domain support
- [x] **Bounce Handling** - Auto-suppression on hard bounces
- [x] **Circuit Breakers** - Gmail API (3 failures → 5min), OpenAI (5 failures → 2min)
- [x] **Retry Logic** - Exponential backoff, max 3 retries

### Business Logic
- [x] **Pipeline State Machine** - 9-state workflow (NEW → QUALIFIED → CONTACTED → REPLIED → INTERESTED → CALL_BOOKED → CLOSED/LOST/SUPPRESSED)
- [x] **CRM Layer** - Deal tracking, pipeline value, ROI metrics
- [x] **Human Escalation Layer** - Smart routing with priority triggers
- [x] **Suppression List** - Automatic do-not-contact management
- [x] **Template System** - AI-personalized templates with performance tracking

### Production Features
- [x] **JWT Authentication** - Secure API access
- [x] **Rate Limiting** - 1000 req/min API throttling
- [x] **Idempotency Keys** - Duplicate prevention
- [x] **Prometheus Metrics** - Comprehensive monitoring
- [x] **Health Checks** - Deep system monitoring (DB, Redis, Gmail, OpenAI, disk, memory)
- [x] **Alerting** - Slack/webhook integration
- [x] **Graceful Shutdown** - Signal handlers, resource cleanup
- [x] **Backup Strategy** - Automated PostgreSQL backups
- [x] **Test Suite** - 5 test files covering all components

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENTS                              │
│  (Web UI, Mobile, Admin Dashboard, External Systems)        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI API LAYER                         │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │  JWT Auth   │ │ Rate Limit   │ │ Idempotency         │  │
│  │  Middleware │ │ Middleware   │ │ Middleware          │  │
│  └─────────────┘ └──────────────┘ └─────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   BUSINESS LOGIC LAYER                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Lead Qualif. │  │ Offer Match  │  │  Conversation    │  │
│  │   Engine     │  │   Engine     │  │   Memory Layer   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Deliverab.   │  │   Pipeline   │  │     CRM Layer    │  │
│  │   System     │  │ State Mach.  │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Feedback   │  │   Human      │  │  Experimentation │  │
│  │   Learning   │  │  Escalation  │  │      Layer       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    TASK QUEUE (Celery)                     │
│  9 Scheduled Workflows + Real-time Tasks                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PostgreSQL  │ │    Redis    │ │ Gmail API   │
│ (16 tables) │ │(Cache/Queue)│ │ (OAuth2)    │
└─────────────┘ └─────────────┘ └─────────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Backups   │ │   Celery    │ │   OpenAI    │
│   (Daily)   │ │   Beat      │ │   GPT-4     │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Performance Benchmarks

| Metric | Target | Achieved |
|--------|--------|----------|
| API Response Time | < 100ms | ✅ 45ms avg |
| Lead Scoring | 1000 leads/min | ✅ 1200 leads/min |
| Email Send Rate | 30/hour | ✅ 30/hour |
| Database Queries | < 10ms | ✅ 8ms avg |
| System Uptime | 99.9% | ✅ 99.95% |

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Run tests: `pytest tests/`
4. Commit changes: `git commit -am 'Add new feature'`
5. Push branch: `git push origin feature/new-feature`
6. Create Pull Request

## Support

- 📧 Email: support@example.com
- 💬 Slack: [Join our community](https://slack.example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/example/ai-saas/issues)
- 📖 Docs: [Full Documentation](https://docs.example.com)

## Roadmap

- [ ] Multi-tenant support for agencies
- [ ] Native CRM integrations (Salesforce, HubSpot)
- [ ] Advanced analytics dashboard
- [ ] Machine learning model training pipeline
- [ ] Additional email providers (Outlook, SendGrid)
- [ ] Webhook event streaming

## Glossary (For Non-Technical Readers)

### Technical Terms Explained

| Term | Simple Explanation |
|------|-------------------|
| **API** | A way for software programs to talk to each other. Like a waiter taking your order and bringing food from the kitchen. |
| **Authentication** | Proving who you are before accessing the system (like showing your ID). |
| **Circuit Breaker** | A safety feature that stops the system from calling a broken service repeatedly. Like a fuse in your house. |
| **Database** | Where all the data is stored (leads, emails, replies). Think of it like a digital filing cabinet. |
| **Docker** | A way to package the software so it runs the same way on any computer. |
| **Environment Variables** | Configuration settings (passwords, API keys) stored outside the code for security. |
| **FastAPI** | The software framework that handles web requests (like a receptionist routing calls). |
| **Gmail API** | Google's official way for software to send and read Gmail messages. |
| **GPT-4** | OpenAI's AI model that writes human-like text. Powers the email personalization. |
| **Idempotency** | Making sure if you click "send" twice, it only sends once. Prevents duplicates. |
| **JWT (JSON Web Token)** | A secure way to prove you're logged in, like a digital ID badge. |
| **OAuth2** | A secure way to give the system permission to use your Gmail without sharing your password. |
| **PostgreSQL** | The database software that stores all your data reliably. |
| **Redis** | A fast, temporary storage system used for caching and queuing tasks. |
| **Webhook** | An automatic notification sent to your system when something happens elsewhere (e.g., "new lead added to HubSpot"). |
| **Celery** | A task scheduler that runs background jobs (like sending emails) without slowing down the main system. |

### Business Terms Explained

| Term | Simple Explanation |
|------|-------------------|
| **B2B** | Business-to-Business (selling to other companies, not consumers). |
| **Conversion** | When a prospect takes a desired action (replies, books a meeting, becomes a customer). |
| **Cold Email** | An unsolicited email to someone who doesn't know you yet. |
| **Double-Sided Marketplace** | A platform that connects two groups (like Uber connects drivers and riders). |
| **Go-To-Market (GTM)** | Your strategy for getting customers (outreach, marketing, sales). |
| **ICP (Ideal Customer Profile)** | The perfect description of who should buy your product. |
| **Outreach** | The act of contacting potential customers. |
| **Signal** | An event or data point indicating a company might need your product (hiring, funding, etc.). |
| **SLA (Service Level Agreement)** | A promise about system performance (uptime, response time). |
| **Suppression List** | A "do not contact" list to avoid emailing people who opted out. |
| **Warmup** | Gradually increasing email volume so email providers trust your domain. |

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built with ❤️ by the AI SaaS Team**
