"""Ambient audit-actor and request-metadata context (ContextVars)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass

from app.models.enums import ActorType


@dataclass(frozen=True)
class AuditActor:
    """The actor (snapshot string + type) behind an action."""

    actor: str
    actor_type: str


current_actor: ContextVar[AuditActor | None] = ContextVar("audit_actor", default=None)


def set_current_actor(actor: str, actor_type: str) -> Token[AuditActor | None]:
    return current_actor.set(AuditActor(actor=actor, actor_type=actor_type))


def reset_current_actor(token: Token[AuditActor | None]) -> None:
    current_actor.reset(token)


def get_current_actor() -> AuditActor | None:
    return current_actor.get()


@dataclass(frozen=True)
class RequestMetadata:
    """The HTTP facts (URL path, client IP, user-agent, request id) behind an action."""

    url: str | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None


request_metadata_var: ContextVar[RequestMetadata | None] = ContextVar(
    "request_metadata", default=None
)


def set_request_metadata(
    url: str | None,
    ip_address: str | None,
    user_agent: str | None,
    request_id: str | None,
) -> Token[RequestMetadata | None]:
    return request_metadata_var.set(
        RequestMetadata(
            url=url,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
    )


def reset_request_metadata(token: Token[RequestMetadata | None]) -> None:
    request_metadata_var.reset(token)


def get_request_metadata() -> RequestMetadata | None:
    return request_metadata_var.get()


@asynccontextmanager
async def system_actor(name: str) -> AsyncIterator[None]:
    """Run a block with the actor set to an automation identity (non-HTTP entry points)."""
    token = set_current_actor(name, ActorType.SYSTEM.value)
    try:
        yield
    finally:
        reset_current_actor(token)
