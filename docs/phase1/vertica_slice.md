Phase 1
✅ - DONE  |  ⁉️- PENDING
✅Phase 1.0) Purpose (Phase 1 “vertical slice”)
Executive Summary
Phase 1 фиксирует минимальный вертикальный срез данных: из факта выполненного pickup в Odoo18 (SoR dispatch) получить в ITAD Core (SoR compliance) неизменяемые комплаенс-артефакты (pickup_manifest → BOL(PICKUP) → Receiving Weight Record v3) и доказать это UI-сценарием + идемпотентностью.
Data Architecture View
Цепочка данных (Data Lineage) (Phase 1):
Odoo18: Work Order/Stop Completed + POD evidence (attachments)
 ↓ (submit event via outbox, contract)


ITAD Core:
pickup_manifest (compliance envelope + external refs + snapshot + evidence refs)


bol with source_type=PICKUP (1:1)


receiving_weight_record_v3 (receiving anchor tied to BOL)
Ключевой принцип SSOT/SoR:
Operational truth (route/stop execution state) — только Odoo.


Compliance truth (manifest/BOL/receiving states, immutability, attempt logs) — только ITAD Core.
Risk & Compliance Check
Риск “dual truth”: если routing/dispatch state попадёт в ITAD Core как редактируемая сущность — SoR breach.


NIST 800-88 / R2v3 / GDPR: уже на Phase 1 требуется минимальная трассируемость (кто/когда/что отправил), неизменяемость ключевых записей и доказуемые ссылки на evidence (hash+ref).
Implementation Steps
Зафиксировать “Minimum Working Flow” как контрольный тест (UI + API).


Определить canonical identifiers и правила snapshot’ов, чтобы Phase 1 не сломался при rebuild DB.


Встроить идемпотентность + outbox как обязательный контур доставки событий.



 Phase 1.1) Locked Governance (NON-NEGOTIABLE)
Executive Summary
Governance закрепляет архитектуру владения данными: Odoo18 = SoR dispatch, ITAD Core = SoR compliance, Routific = optimizer-only, Odoo19 архивирован, single-writer везде.
Data Architecture View
Границы доменов (Domain Boundaries / Ownership):
Odoo18 domain objects (авторитетные): route/day plan, stops, completion state, technician assignment, dispatch timestamps, proposal acceptance.


ITAD Core domain objects (авторитетные): pickup_manifest, bol, receiving, custody events, evidence registry (hash+refs), retention flags, immutability/void-reissue.


Routific: вход/выход (proposal) хранятся в Odoo; в ITAD Core — только routific_job_id, input_hash как non-authoritative.
Single-writer enforcement (архитектурно):
Контрактные события только из Odoo → ITAD Core.


Обратный канал: ITAD Core → Odoo только read-only references/status, без “команд” менять compliance-истину.
Risk & Compliance Check
Auditability / defensibility: без single-writer любая проверка цепочки custody станет спорной (“кто последний изменил?”).


Change control: любые “скрытые” правки в compliance-объектах нарушат принципы R2 и NIST (traceability, tamper-evidence).
Implementation Steps
В документах и коде ввести SoR Guard: статические проверки формулировок и запретные слова/пути.


В ITAD Core добавить server-side валидации, которые отклоняют поля routing/dispatch truth (если кто-то попытается их прислать/обновить).


Явно пометить Odoo19 как non-authoritative во всех доках/README.



Phase 1.2) Phase 1 Scope
Executive Summary
Scope Phase 1 — минимально нужные compliance-объекты + интеграционный контур: manifest bridge, BOL binding (1:1), evidence policy (hash+ref), receiving v3, observability/audit.
Data Architecture View
A) Pickup Manifest Bridge (ITAD Core)
Сущность pickup_manifest (core attributes, Phase 1):
Identity / keys


pickup_manifest_id (UUID internal)


manifest_no (human-readable, immutable once issued)


idempotency_key (stored)


manifest_fingerprint (stored; dedupe defense-in-depth)


External refs (immutable)


odoo_db / odoo_instance_id (required)


odoo_work_order_id / odoo_fsm_order_id (required)


optional: odoo_day_route_id, odoo_stop_id


odoo_customer_id, odoo_service_location_id


Snapshot payloads (JSON, immutable snapshot)


route/stop context snapshot (sequence, technician, planned window, completion timestamps)


location snapshot (address, geo snapshot, confidence)


POD metadata refs (see evidence)


Lifecycle/state


DRAFT | SUBMITTED | BOUND_TO_BOL | (RECEIVED optional) | VOIDED


Audit


created_at, created_by_system, source_system


correlation fields: x_request_id, x_correlation_id


B) BOL binding for PICKUP (ITAD Core)
Сущность bol (Phase 1 minimum):
bol_id, bol_no


source_type = PICKUP (enum)


pickup_manifest_id (required for PICKUP)


status state machine (минимум: OPEN → CLOSED позже; Phase 1 — достаточно CREATED/BOUND)


immutability: изменения через события/void-reissue по правилам ITAD Core


Binding rule (LOCKED): 1 pickup_manifest → 1 BOL
C) Evidence (POD) policy
Evidence registry (ITAD Core, Phase 1) — только refs + hashes:
artifact_id


artifact_type (photo/signature/notes)


source_system = ODOO18


odoo_attachment_id / attachment_url (immutable reference)


content_hash (sha256)


metadata (timestamp, author/technician id, file name, mime)


retention/visibility flags: retention_class, is_sensitive, access_scope (минимум заглушки)


D) Receiving Anchor v3
receiving_weight_record_v3:
receiving_id


bol_id (required)


facility_id


weights/measures + units (lbs locked, если Phase 0 так решила)


immutability: void/reissue, no edits


E) Observability + audit
Attempt log (ITAD Core):
attempt_id, timestamps


source_system, odoo_db


x_request_id, x_correlation_id, idempotency_key


outcome (SUCCESS / DUPLICATE_RETURNED / VALIDATION_ERROR / SERVER_ERROR)


error summary (JSON-safe)


Outbox (Odoo18):
event_id (UUID)


state (PENDING/SENT/FAILED)


payload hash, last_error, retry_count, next_retry_at


Risk & Compliance Check
Data collision risk без odoo_db: одинаковые numeric IDs после rebuild разрушат lineage.


Evidence integrity: отсутствие hash/ref делает POD недоказуемым.


Receiving immutability: если “править вес” редактированием — audit failure (R2/NIST defensibility).


Implementation Steps
Утвердить минимальные схемы (pickup_manifest, bol, artifact_ref, attempt_log, receiving_v3).


Реализовать “submit pipeline” так, чтобы binding происходил автоматически (Phase 1) и был идемпотентным.


Включить обязательные корреляционные заголовки и хранение их в обеих системах.



Phase 1.3) Phase 1 Deliverables (Definition of “Done”)
Executive Summary
“Done” = зафиксированные документы/контракты + реализованные модели/endpoint’ы + Odoo outbox+UI + проверяемый smoke сценарий на чистой среде.
Data Architecture View
Deliverables формируют контур управляемости данных:
Контракт определяет shape данных, идемпотентность, ошибки/ретраи, мэппинг Odoo моделей.


Тесты закрепляют инварианты: no duplicates, 1:1 binding, immutability, traceability.


Risk & Compliance Check
Без data_mapping_odoo18.md команда начнёт “угадывать” модели OCA FS — это почти гарантированная причина нестыковок и “скрытых” dual-writes.


Без verification log сложно доказать, что Phase 1 действительно закрывает вертикальный срез (а не “частично работает”).


Implementation Steps
Создать папку docs/phase1/ и минимально заполнить:


PHASE_1.md


INTEGRATION_CONTRACT_ODoo18_ITADCore.md


state_machines.md


idempotency_logic.md


data_mapping_odoo18.md


PHASE_1_VERIFICATION_LOG.md


В ITAD Core: миграции + endpoint submit + binding + attempt logs + тесты.


В Odoo: outbox + кнопка submit + cron retry + read-only поля.



Phase 1.4) Canonical Data Flow (Phase 1)
Executive Summary
Flow должен быть UI-driven и воспроизводим: Odoo создаёт событие → outbox → ITAD submit → manifest+bol → (optional receiving) → read-only feedback в Odoo.
Data Architecture View
Событийная модель (Event-driven integration):
Business action: “Submit Pickup Manifest”


Technical event: outbox row with stable event_id + stable idempotency_key


ITAD Core: command endpoint submit (idempotent) → internal transitions


Read model в Odoo:
Odoo хранит только: manifest_id, manifest_no, manifest_status, bol_id, receiving_id?, last_submit_at, last_error


Никаких “редактируемых compliance полей” в Odoo.


Risk & Compliance Check
Риск “UI says done but compliance missing”: обязательно выводить статус отправки/ошибок в Odoo (visibility).


Риск “split brain”: если Odoo начнёт локально трактовать compliance state — конфликт SoR.


Implementation Steps
В Odoo UI: отдельная секция “Compliance (ITAD Core)” только read-only.


В ITAD Core: статусная модель manifest и возвращаемый payload должен быть стабильным.


Верификационный сценарий закрепить как “Demo Scenario” с командами и ожидаемыми результатами.



Phase 1.5) Integration Rules (Phase 1 MUST LOCK)
Executive Summary
Правила интеграции — это ваши “законы физики”: идемпотентность, fingerprint, external ID policy, networking, geocode policy, no ghost mounts.
Data Architecture View
Idempotency-Key vs Fingerprint
Idempotency-Key: контрактный ключ запроса (primary dedupe)


manifest_fingerprint: вторичная защита (defense-in-depth), хранится и используется при спорных кейсах


External ID policy
odoo_db/instance — обязательный namespace


immutable external refs в ITAD Core


Geocode policy
gates и “routing hygiene” остаются в Odoo


ITAD Core хранит geo snapshot только для аудита


No ghost mounts
избегаем “невидимых” путей addons, которые приводят к non-reproducible builds


Risk & Compliance Check
Без строгой идемпотентности получите “двойные манифесты” → неразрешимые reconciliation кейсы и audit findings.


Ghost mounts = риск поставки непроверенного кода/аддонов (управляемость среды, риск безопасности).


Implementation Steps
Зафиксировать формулу fingerprint (и хранить completion_timestamp/driver/vehicle стабильно).


Реализовать в ITAD Core хранилище idempotency requests/responses (JSON-safe).


В dev: стандартный адрес host.docker.internal + документированный порт/токен.


Добавить guard/checklist на mounts/addons_path.



Phase 1.6) State Machines (Phase 1)
Executive Summary
State machines — это контракт комплаенса: manifest lifecycle и BOL binding должны быть детерминированными, append-only и идемпотентными.
Data Architecture View
pickup_manifest lifecycle (minimum)
DRAFT → SUBMITTED → BOUND_TO_BOL → (RECEIVED optional) → (CLOSED later)


VOIDED (terminal, requires reason)


Event sourcing light (минимум)
Не обязательно полноценное event sourcing в Phase 1, но:


transitions должны логироваться (who/when/why)


изменение “по-тихому” запрещено


BOL binding
1:1


BOL.source_type=PICKUP requires pickup_manifest_id


повторные bind/submit → возвращают существующее


Risk & Compliance Check
Без явных причин VOID/REISSUE будут “дырки” в Chain of Custody (особенно под R2/NIST аудит).


Непрозрачные переходы = невозможность forensic объяснения.


Implementation Steps
Описать transitions в state_machines.md.


В ITAD Core: enforce через сервисный слой (не в контроллере) и тестами.


В ответе submit возвращать: manifest_status, bol_status (минимум), timestamps.



Phase 1.7) Sprint Plan (small, reviewable)
Executive Summary
План спринтов держит систему “reviewable”: сначала Odoo outbox/UX, затем ITAD submit+binding, затем receiving+verification.
Data Architecture View
Sprint 1 (foundation) = “delivery pipeline” (outbox) + headers + payload builder
 Sprint 2 (compliance) = submit endpoint + idempotency store + 1:1 BOL bind
 Sprint 3 (chain proof) = receiving v3 + end-to-end verification artifacts
Risk & Compliance Check
Перепрыгивание через Sprint 1 почти всегда даёт “ручные отправки без outbox” → потеря retry/auditability.


Receiving без immutability правил → ломает compliance foundation.


Implementation Steps
Sprint 1: UI + outbox + retry + видимость ошибок.


Sprint 2: submit contract + tests + attempt logs.


Sprint 3: receiving flow + verification log.



Phase 1.8) Acceptance Criteria (Phase 1 Exit Gate)
Executive Summary
Exit gate — это Pass/Fail критерии защиты SoR, идемпотентности, трассируемости и работоспособной цепочки manifest→BOL→receiving.
Data Architecture View
Метрики “готовности” (minimum)
0 duplicates на повторных submit


100% manifest имеет odoo_db + ключевые external refs


attempt logs присутствуют для каждого submit


Odoo UI показывает текущий compliance status


Risk & Compliance Check
Главный риск — “вроде работает”, но нет доказательной базы (verification log, attempt logs, immutability tests).


Implementation Steps
Автоматизировать smoke run (скрипт/README).


Ввести обязательный PR-чеклист: SoR guard, no ghost mounts, contract tests.



Phase 1.9) Top Risks (Phase 1)
Executive Summary
Риски Phase 1 типовые для ITAD интеграций: неверный trigger, дубликаты, мэппинг OCA FS, evidence gaps, SoR breach, external ID collisions.
Data Architecture View
Risk-to-control mapping (быстро)
Wrong trigger → manual button + explicit user action + outbox event_id


Duplicates → Idempotency-Key store + fingerprint + tests


Model mapping ambiguity → data_mapping_odoo18.md verified from UI/ORM


Evidence gaps → hash+ref registry + append-only artifacts


SoR breach → guardrails + server-side validation


ID collisions → odoo_db namespace


Risk & Compliance Check
Evidence integrity и immutability — “аудиторские” риски №1.


SoR breach — архитектурный риск №1 (дорогой откат).


Implementation Steps
Зафиксировать “controls” рядом с каждым риском в Phase 1 docs.


Добавить негативные тесты (попытка изменить compliance truth из Odoo должна быть невозможна/непредусмотрена контрактом).



Phase 1.10) Immediate Next Actions (do this before coding)
Executive Summary
Перед кодом нужно “закрыть неопределённость”: создать doc set, верифицировать реальные модели Odoo, закрепить dev networking и секреты.
Data Architecture View
Data mapping как фундамент
OCA FS модель Work Order, Location, Technician, Attachments, (Route/Stop если есть)


Поля completion timestamp, technician assignment, sequence, attachments storage


Это определяет payload builder и fingerprint формулу


Secret/config management
ITAD Core base URL, token — через system parameters (Odoo) + env/secret store (ITAD Core)


Risk & Compliance Check
“Guessing fields” в Odoo = гарантированная расходимость данных и ломка интеграции.


Token handling без дисциплины = security risk (минимум: не хранить токены в коде/репо).


Implementation Steps
Создать и заполнить docs/phase1/* (минимальная версия, но с locked decisions).


В Odoo: через UI/ORM (Developer mode) задокументировать модели/поля и записать в data_mapping_odoo18.md.


Зафиксировать dev URL: host.docker.internal:<itad_port> + где хранится token + как ротируется.


Определить минимальные seed’ы/демо: customer, service location, work order, attachment evidence.



Phase 1.11 Дополнительные подглавы (добавлены для ITAD best practice)
A) Canonical Entity Catalog (Phase 1)
Odoo18 (Operational): fsm_order, res_partner (customer), fsm_location (service location), ir.attachment (POD), (route/stop модели по факту мэппинга)


ITAD Core (Compliance): pickup_manifest, bol, receiving_weight_record_v3, artifact_ref, integration_attempt_log, idempotency_record


B) Chain of Custody (минимум для Phase 1)
Даже если детальная custody-цепочка будет в Phase 2+, Phase 1 обязан:
фиксировать кто/когда инициировал submit (operator/technician context)


фиксировать неизменяемые ссылки на POD (hash+ref)


фиксировать binding manifest→BOL как “точку передачи в compliance”


C) Compliance Baseline Checklist (Phase 1)
Append-only evidence registry (hash/ref)


Idempotency store + replay-safe responses


Void/reissue mechanics (receiving минимум)


Trace headers persisted (request/correlation ids)


Retention flags (минимум поля, политика позже)





## Deliverables (What "Done" Means)

The following items represent the tangible outputs required for Phase 1 completion, ensuring the "Minimum Working Flow" objective is met and the "Success Criteria" are passed.
Documentation & Contracts
Deliverable
Description
Location
Status
Phase 1 Spec
Finalized scope, objective, and locked decisions.
docs/phase1/PHASE_1.md
-
Integration Contract
API payload schemas, error codes, retry policy, and idempotency key generation logic.
docs/phase1/INTEGRATION_CONTRACT_ODoo_ITADCore.md
-
State Machine Definitions
Formal definition of pickup_manifest lifecycle states and BOL binding rules (1:1).
docs/phase1/state_machines.md
-
Idempotency Fingerprint Logic
Documented, deterministic logic for creating the Idempotency-Key hash in Odoo.
docs/phase1/idempotency_logic.md
-

ITAD Core (FastAPI)
Deliverable
Description
Status
Data Model & Migrations
pickup_manifest data model with external refs and state fields.
-
Manifest Submission Endpoint
POST /api/v1/pickup-manifests (Single, idempotent endpoint).
-
BOL Binding Logic
Internal service to bind a newly created manifest to a BOL with source_type=PICKUP (1:1 rule).
-
Evidence Reference Storage
Logic to store immutable hash and reference to Odoo POD attachments on the manifest record.
-
Observability
Correlation ID (X-Request-Id) logging/passthrough and integration attempt audit log.
-
Unit & Integration Tests
Proving idempotency, 1:1 binding, immutability, and correlation ID passthrough.
-

Odoo 18 Module (itad_core_bridge)
Deliverable
Description
Status
Manifest Generation Logic
Python method to construct the manifest payload, including external IDs, snapshot, and POD metadata/hashes.
-
Idempotency Key Generator
Deterministic function to generate the Idempotency-Key header.
-
API Client
Simple service to call the ITAD Core manifest endpoint.
-
UI Integration
Read-only fields on the FSM Work Order/Stop to display returned manifest_id, bol_id, and status.
-
Trigger Mechanism
Implementation of the locked decision (manual button or auto-submit on completion).
-

Verification
Deliverable
Description
Status
Smoke Run Script
End-to-end script that executes the "Demo Scenario" on a clean environment.
-
Verification Log
Recorded output proving the chain: Odoo event → manifest created → bound to BOL(PICKUP).
-
SoR Guard Pass
Confirmation that Phase 0 SoR guard tests pass against the new Phase 1 code.
-


