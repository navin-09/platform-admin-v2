"""Router factory that generates typed CRUD routes for a master-data TableSpec."""

import uuid

from fastapi import APIRouter, Query

from app.core.constants import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
)
from app.core.master_data import TableSpec
from app.models.enums import Status, StatusFilter, resolve_filter
from app.schemas.common import ApiResponse, ListData, build_list_data
from app.schemas.master_data import (
    CODE_CREATED,
    CODE_DELETED,
    CODE_FETCHED,
    CODE_LISTED,
    CODE_UPDATED,
    MSG_CREATED,
    MSG_DELETED,
    MSG_FETCHED,
    MSG_LISTED,
    MSG_UPDATED,
)
from app.services import master_data_service
from app.utils.limits import SEARCH_MAX_LENGTH


def build_router(spec: TableSpec) -> APIRouter:
    """Build a router exposing typed CRUD for ``spec``'s table.

    FastAPI requires the *runtime* concrete classes (``spec.create_model`` etc.) in the
    handler signatures, so those dynamic type annotations carry ``type: ignore`` — the DTO
    classes themselves remain fully typed and drive validation + OpenAPI.
    """
    router = APIRouter(tags=[spec.table.title()])

    if spec.create_model is not None:

        @router.post(
            "",
            response_model=ApiResponse[spec.read_model],  # type: ignore[name-defined]
            status_code=201,
            name=f"{spec.table}_create",
        )
        async def create(data: spec.create_model) -> ApiResponse[spec.read_model]:  # type: ignore[name-defined]
            """Create a record; FK ids are validated before insert."""
            result = await master_data_service.create_row(spec, data)
            return ApiResponse(code=CODE_CREATED, message=MSG_CREATED, data=result)

    @router.get(
        "",
        response_model=ApiResponse[ListData[spec.read_model]],  # type: ignore[name-defined]
        name=f"{spec.table}_list",
    )
    async def list_rows(
        page: int = Query(DEFAULT_PAGE, ge=MIN_PAGE),
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
        search: str | None = Query(None, max_length=SEARCH_MAX_LENGTH),
        status: StatusFilter = Query(StatusFilter.ALL),
    ) -> ApiResponse[ListData[spec.read_model]]:  # type: ignore[name-defined]
        """List a page of records, fully nested and paginated."""
        items, total = await master_data_service.list_rows(
            spec,
            page=page,
            limit=limit,
            search=search,
            status=resolve_filter(status, Status),
        )
        return ApiResponse(
            code=CODE_LISTED,
            message=MSG_LISTED,
            data=build_list_data(spec.read_model, items, page=page, limit=limit, total=total),
        )

    @router.get(
        "/{record_id}",
        response_model=ApiResponse[spec.read_model],  # type: ignore[name-defined]
        name=f"{spec.table}_get",
    )
    async def get_row(record_id: uuid.UUID) -> ApiResponse[spec.read_model]:  # type: ignore[name-defined]
        """Fetch one record, fully nested."""
        result = await master_data_service.get_row(spec, record_id)
        return ApiResponse(code=CODE_FETCHED, message=MSG_FETCHED, data=result)

    if spec.update_model is not None:

        @router.patch(
            "/{record_id}",
            response_model=ApiResponse[spec.read_model],  # type: ignore[name-defined]
            name=f"{spec.table}_update",
        )
        async def update_row(
            record_id: uuid.UUID,
            data: spec.update_model,  # type: ignore[name-defined]
        ) -> ApiResponse[spec.read_model]:  # type: ignore[name-defined]
            """Partially update a record; changed FK ids are validated."""
            result = await master_data_service.update_row(spec, record_id, data)
            return ApiResponse(code=CODE_UPDATED, message=MSG_UPDATED, data=result)

    @router.delete(
        "/{record_id}",
        response_model=ApiResponse[None],
        name=f"{spec.table}_delete",
    )
    async def delete_row(record_id: uuid.UUID) -> ApiResponse[None]:
        """Soft-delete a record."""
        await master_data_service.delete_row(spec, record_id)
        return ApiResponse(code=CODE_DELETED, message=MSG_DELETED, data=None)

    return router
