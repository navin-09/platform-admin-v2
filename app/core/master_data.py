"""Master-data engine declarations: table specs, FK introspection, and the registry."""

import uuid
from dataclasses import dataclass
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy import Table
from sqlmodel import SQLModel

from app.models.address import Address
from app.models.country import Country
from app.models.course import Course
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.program import Program
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.address import AddressRead
from app.schemas.country import CountryRead
from app.schemas.course import CourseRead
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.enrollment import EnrollmentRead
from app.schemas.program import ProgramRead
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate
from app.schemas.teacher import TeacherCreate, TeacherRead, TeacherUpdate


@dataclass(frozen=True)
class Collection:
    """A reverse (one-to-many / many-to-many) child edge, capped per parent."""

    via_table: str
    via_fk: str
    cap: int = 20


@dataclass(frozen=True)
class TableSpec:
    """Everything the engine needs to serve typed CRUD for one master-data table."""

    table: str
    model: type[SQLModel]
    read_model: type[BaseModel]
    create_model: type[BaseModel] | None = None
    update_model: type[BaseModel] | None = None
    search_field: str | None = None
    collections: tuple[Collection, ...] = ()
    max_depth: int = 6


COUNTRY_SPEC = TableSpec(
    table="countries", model=Country, read_model=CountryRead, search_field="country_name"
)
ADDRESS_SPEC = TableSpec(table="addresses", model=Address, read_model=AddressRead)
DEPARTMENT_SPEC = TableSpec(
    table="departments",
    model=Department,
    read_model=DepartmentRead,
    create_model=DepartmentCreate,
    update_model=DepartmentUpdate,
    search_field="department_name",
)
TEACHER_SPEC = TableSpec(
    table="teachers",
    model=Teacher,
    read_model=TeacherRead,
    create_model=TeacherCreate,
    update_model=TeacherUpdate,
    search_field="teacher_name",
)
PROGRAM_SPEC = TableSpec(
    table="programs", model=Program, read_model=ProgramRead, search_field="program_name"
)
COURSE_SPEC = TableSpec(
    table="courses", model=Course, read_model=CourseRead, search_field="course_name"
)
ENROLLMENT_SPEC = TableSpec(table="enrollments", model=Enrollment, read_model=EnrollmentRead)
STUDENT_SPEC = TableSpec(
    table="students",
    model=Student,
    read_model=StudentRead,
    create_model=StudentCreate,
    update_model=StudentUpdate,
    search_field="email",
    collections=(Collection(via_table="enrollments", via_fk="student_id", cap=20),),
)

REGISTRY: dict[str, TableSpec] = {
    COUNTRY_SPEC.table: COUNTRY_SPEC,
    ADDRESS_SPEC.table: ADDRESS_SPEC,
    DEPARTMENT_SPEC.table: DEPARTMENT_SPEC,
    TEACHER_SPEC.table: TEACHER_SPEC,
    PROGRAM_SPEC.table: PROGRAM_SPEC,
    COURSE_SPEC.table: COURSE_SPEC,
    ENROLLMENT_SPEC.table: ENROLLMENT_SPEC,
    STUDENT_SPEC.table: STUDENT_SPEC,
}


def table_of(model: type[SQLModel]) -> Table:
    """Return the SQLAlchemy Table for a SQLModel table class (not typed on the base)."""
    return cast(Table, cast(Any, model).__table__)


def fk_edges(model: type[SQLModel]) -> list[tuple[str, str]]:
    """Return ``(local_column, target_table)`` pairs from the model's FK metadata."""
    return [(fk.parent.name, fk.column.table.name) for fk in table_of(model).foreign_keys]


def nested_name(fk_column: str) -> str:
    """Map an FK column to its nested field name (``department_id`` -> ``department``)."""
    return fk_column[:-3] if fk_column.endswith("_id") else fk_column


def record_id(row: Any) -> uuid.UUID:
    """Return a row's UUID primary key (every master-data table uses ``id``)."""
    return cast(uuid.UUID, row.id)
