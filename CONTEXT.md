# Platform Admin

The secure, controlled portal for administering reference and operational data consumed by the Kyber AI LOS Platform. Every business-changing action is validated, reasoned, versioned and auditable; control comes from live validation and immutable evidence, never from maker-checker.

## Language

**Audit Event**:
One consequential action claimed for recording — the action, the resource type and id it touched, and optional payload, response, and reason. Becomes an Audit Entry when persisted.
_Avoid_: audit record, log line

**Audit Entry**:
A persisted, immutable Audit Event — the administrative or security evidence the BRD promises.
_Avoid_: audit log row

**Actor**:
The authenticated identity behind an action: an admin's login email or a system identity.
_Avoid_: user, account (when you mean the recorded identity)

**Claimed actor**:
An unauthenticated identity asserted by submitted credentials (e.g. the email on a failed login attempt). Recorded as security evidence before any authentication exists.
_Avoid_: unauthenticated user

**Governed action**:
A business-changing action the BRD requires to carry a mandatory change reason and external references. Current-phase modules are administrative; governed modules (Price, ED, Negative Area) arrive later.
_Avoid_: controlled action
