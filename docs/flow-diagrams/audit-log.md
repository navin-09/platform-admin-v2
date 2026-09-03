# Audit Logging — Architecture & Flow

How every consequential action in Platform Admin becomes durable, tamper-evident
audit evidence. Grounded in the current implementation; every box names the real
module. View on GitHub (or any Mermaid renderer) for the diagrams to draw.

## The four guarantees

| Guarantee | Mechanism |
| --- | --- |
| Complete — every consequential action is recorded | one `AuditEvent` shape, 1 call per action |
| Attributed — actor always known | identity lives in the request context, never in call sites |
| Durable — evidence survives crashes | Pending Audit Intent written in the request transaction scope, forged asynchronously |
| Tamper-evident — edits/deletes/reorders are detectable | SHA-256 hash chain over `seq`-ordered entries |

---

## 1. Component map

```mermaid
flowchart TB
    subgraph Request["HTTP request scope"]
        MW["RequestContextMiddleware<br/>app/middleware/request_context.py<br/>sets: url · ip · user-agent · request-id"]
        AUTH["get_current_admin<br/>app/api/deps.py<br/>sets: actor (authenticated)"]
        CLAIM["claimed_actor()<br/>app/core/audit_context.py<br/>sets: claimed actor (pre-auth)"]
        CTX[("Request context<br/>ContextVars<br/>app/core/audit_context.py")]
        HANDLER["API handler / service<br/>builds AuditEvent<br/>record(event) · record_failure(event, exc)"]
    end

    subgraph Intake["Durable intake"]
        REDACT["redact()<br/>app/utils/redact.py"]
        SVC["audit_service.record<br/>app/services/audit_service.py"]
        REPO["audit_repository<br/>app/repositories/audit_repository.py"]
        INTENT[("audit_intents<br/>(outbox, pending)")]
    end

    subgraph Forge["Background forge (lifespan task, 1s poll)"]
        FWD["_audit_forwarder<br/>app/main.py"]
        PROMOTE["promote_audit_intents<br/>advisory lock → hash-chain → insert + delete in ONE tx"]
    end

    subgraph Evidence["Immutable evidence"]
        LOGS[("audit_logs<br/>seq · prev_hash · entry_hash<br/>app/models/audit_log.py")]
        VERIFY["verify_audit_chain.py<br/>app/database/scripts/"]
    end

    READ["GET /audit-logs<br/>AuditLogFilter DTO → audit_log_filters() → SQL"]
    EXPORT["Export engine<br/>stored filter JSON → same AuditLogFilter mapping"]

    MW --> CTX
    AUTH --> CTX
    CLAIM --> CTX
    CTX --> HANDLER
    HANDLER --> SVC
    SVC --> REDACT
    SVC --> REPO
    REPO --> INTENT
    INTENT --> PROMOTE
    FWD --> PROMOTE
    PROMOTE --> LOGS
    LOGS --> VERIFY
    LOGS --> READ
    LOGS --> EXPORT
```

**One source of truth per concern**

| Concern | Lives in | Set by |
| --- | --- | --- |
| What happened (action, resource, payload, reason) | the `AuditEvent` | each call site |
| Who did it (actor, actor_type) | request context | `get_current_admin` · `claimed_actor` · `system_actor` |
| Where from (url, ip, ua, request-id) | request context | `RequestContextMiddleware`, once |

---

## 2. Write flow — authenticated action (happy path)

Example: an admin creates a user.

```mermaid
sequenceDiagram
    autonumber
    participant R as request
    participant MW as RequestContextMiddleware
    participant A as get_current_admin
    participant H as handler / user_service
    participant S as audit_service.record
    participant I as audit_intents (outbox)

    R->>MW: POST /users
    MW->>MW: set url, ip, user-agent, request-id
    R->>A: bearer token
    A->>A: set actor = admin.email
    A->>H: admin resolved
    H->>H: create user (own transaction)
    H->>S: record(AuditEvent(action=USER_CREATE, ...))
    S->>S: read actor + request facts from context
    S->>S: redact(details / payload / response)
    S->>I: INSERT intent (committed — durable)
    Note over I: crash here = intent already safe
    H-->>R: 201 Created
```

The intent insert is best-effort: if the database rejects it, the action still
succeeds and the failure is logged — evidence quality is degraded, never faked.

## 3. Pre-auth flow — login / OTP / password reset

Nobody is authenticated yet, so the endpoint **claims** an identity: the email
from the submitted credentials. A failed login by an attacker records the
attacker's email — that is the evidence.

```mermaid
sequenceDiagram
    autonumber
    participant C as client
    participant L as POST /auth/login
    participant S as audit_service
    participant I as audit_intents

    C->>L: credentials (maybe wrong password)
    L->>L: claimed_actor(credentials.email) — context now holds the claim
    L->>L: auth_service.login() raises AccountLockedError
    L->>S: record_failure(event, exc)
    S->>S: merges error_code into details
    S->>I: intent committed (actor = claimed email)
    L-->>C: 423 locked
    Note over I: both failure AND success paths inside the<br/>claimed_actor block inherit the identity
```

`POST /auth/refresh` is the one flow with no claimable identity (the body is
just a token) — its entries honestly record `actor = NULL`.

## 4. The forge — outbox promotion loop

A lifespan task polls every second. Promotion is atomic: **insert entries +
delete intents in one transaction**, so a crash retries the batch and can never
duplicate or lose evidence.

```mermaid
sequenceDiagram
    autonumber
    participant F as _audit_forwarder (app/main.py)
    participant P as promote_audit_intents
    participant I as audit_intents
    participant L as audit_logs

    loop every 1s until shutdown
        F->>P: promote_intents()
        P->>I: SELECT oldest batch (200)
        alt outbox empty
            P-->>F: 0
        else batch found
            P->>P: pg advisory lock (serializes chain writers)
            P->>P: per entry: seq = MAX(seq)+1, prev_hash = tip, entry_hash = SHA-256
            P->>L: INSERT chained entries
            P->>I: DELETE promoted intents (same tx)
            P-->>F: count
        end
    end
```

Evidence timestamps never move: the entry's `created_at` is the action time
copied from the intent, not the promotion time.

## 5. The hash chain — tamper evidence

Each entry seals its own fields *and* its position, linking to the previous
entry's seal.

```mermaid
flowchart LR
    E1["seq=1<br/>prev=NULL<br/>hash=H1"] --> E2["seq=2<br/>prev=H1<br/>hash=H2"] --> E3["seq=3<br/>prev=H2<br/>hash=H3"] --> E4["seq=4<br/>prev=H3<br/>hash=H4"]
```

```
entry_hash = SHA-256( prev_hash | canonical_json(seq, actor, action, ..., created_at) )
```

`verify_audit_chain.py` walks entries in `seq` order and recomputes every hash.
Exit code 1 + a `TAMPER:` line on the first break.

| Attack | Detection |
| --- | --- |
| Edit a field in any row | its `entry_hash` no longer matches |
| Delete a middle row | next row's `prev_hash` doesn't link |
| Reorder rows | `seq` inside the hash no longer matches position |
| Fabricate a new row | must also forge every later hash — verifier still catches it because `seq` order and links break |

Not claimed: a DB superuser rewriting the *entire* chain consistently. Detecting
that needs an off-site seal (e.g. exporting the latest `entry_hash` somewhere
external) — the natural job for a future second adapter on this same seam.

## 6. Read & export paths

```mermaid
flowchart TB
    Q["GET /audit-logs<br/>page, limit, actor, action, resource_type,<br/>actor_type, from_date, to_date"]
    F["AuditLogFilter (resolved: None = no filter)"]
    M["audit_log_filters()<br/>the ONE filter → WHERE mapping"]
    SQL["SELECT ... WHERE ... ORDER BY created_at DESC"]
    E["stored export filter JSON<br/>(ALL sentinels)"]
    RES["AuditLogFilter"]

    Q --> F
    E --> RES
    F --> M
    RES --> M
    M --> SQL
```

Adding a filter = one DTO field + one condition in `audit_log_filters()` + one
`Query()` param. No other layer learns about it.

## 7. Failure modes — what evidence survives

| Crash / failure point | Result |
| --- | --- |
| Business change committed, process dies before `record()` | sub-millisecond window; action un-audited (the strict intent-*before*-change pattern for governed modules closes this) |
| `record()` fails (DB blip) | logged, action succeeds — best-effort by design |
| Intent committed, forwarder down | intent waits in the outbox; promoted when the app restarts |
| Forwarder crashes mid-batch | transaction rolls back; retried next pass — no duplicates, no loss |
| DB edited directly | `verify_audit_chain.py` flags it |

## 8. Cheat sheet — where to change what

| Task | Touch |
| --- | --- |
| Audit a new action | add `AuditAction` + `AuditResourceType` enum values (app/models/enums.py), call `record(AuditEvent(...))` after the change |
| Add a sensitive key to mask | `_SENSITIVE_KEYS` in app/utils/redact.py |
| Add a list filter | `AuditLogFilter` (app/schemas/audit.py) + `audit_log_filters()` (audit_repository) + the `Query()` param |
| Check evidence integrity | `uv run python app/database/scripts/verify_audit_chain.py` |
| Add a governed module needing intent-*before*-change | claim the intent before the write, close it with the outcome — same outbox, same forge |
