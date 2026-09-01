"""Seed the students master-data example (idempotent)."""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.database.database import async_session_factory
from app.models.address import Address
from app.models.country import Country
from app.models.course import Course
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.program import Program
from app.models.student import Student
from app.models.teacher import Teacher

COUNTRIES = [("India", "IN"), ("United States", "US"), ("United Kingdom", "GB")]

ADDRESSES = [
    ("12 MG Road", "Chennai", "Tamil Nadu", "600001", "IN"),
    ("500 Main St", "Boston", "MA", "02108", "US"),
    ("9 Baker Street", "London", "England", "NW1 6XE", "GB"),
    ("45 Nehru Nagar", "Bengaluru", "Karnataka", "560001", "IN"),
    ("221 Elm St", "Austin", "TX", "73301", "US"),
]

DEPARTMENTS = [
    ("Computer Science", "Turing Hall"),
    ("Mathematics", "Euler Hall"),
    ("Physics", "Newton Hall"),
]

TEACHERS = [
    ("Dr. Sarah Chen", "Rm 204", "Computer Science"),
    ("Dr. James Patel", "Rm 118", "Mathematics"),
    ("Dr. Maria Gomez", "Rm 310", "Physics"),
]

PROGRAMS = [
    ("Software Engineering", "B.Sc.", "Computer Science"),
    ("Applied Mathematics", "B.Sc.", "Mathematics"),
    ("Quantum Physics", "M.Sc.", "Physics"),
]

COURSES = [
    ("Data Structures", 4, "Computer Science"),
    ("Linear Algebra", 3, "Mathematics"),
    ("Quantum Mechanics I", 4, "Physics"),
    ("Database Systems", 3, "Computer Science"),
    ("Calculus II", 4, "Mathematics"),
]

# (first, last, email, enrollment_date, gpa, address_index, department, teacher, program)
STUDENTS = [
    (
        "Aditi",
        "Rao",
        "aditi.rao@example.edu",
        date(2022, 8, 15),
        Decimal("3.85"),
        0,
        "Computer Science",
        "Dr. Sarah Chen",
        "Software Engineering",
    ),
    (
        "Marcus",
        "Lee",
        "marcus.lee@example.edu",
        date(2022, 8, 20),
        Decimal("3.42"),
        1,
        "Mathematics",
        "Dr. James Patel",
        "Applied Mathematics",
    ),
    (
        "Fatima",
        "Noor",
        "fatima.noor@example.edu",
        date(2022, 8, 15),
        Decimal("3.91"),
        2,
        "Physics",
        "Dr. Maria Gomez",
        "Quantum Physics",
    ),
    (
        "Diego",
        "Alvarez",
        "diego.alvarez@example.edu",
        date(2024, 8, 18),
        Decimal("3.10"),
        3,
        "Computer Science",
        "Dr. James Patel",
        "Software Engineering",
    ),
    (
        "Wei",
        "Zhang",
        "wei.zhang@example.edu",
        date(2024, 1, 10),
        Decimal("3.67"),
        4,
        "Mathematics",
        "Dr. Sarah Chen",
        "Applied Mathematics",
    ),
]

MENTORS = [
    ("diego.alvarez@example.edu", "aditi.rao@example.edu"),
    ("wei.zhang@example.edu", "marcus.lee@example.edu"),
]

ENROLLMENTS = [
    ("aditi.rao@example.edu", "Data Structures", "Fall 2024", "A"),
    ("aditi.rao@example.edu", "Database Systems", "Fall 2024", "A-"),
    ("marcus.lee@example.edu", "Linear Algebra", "Fall 2024", "B+"),
    ("fatima.noor@example.edu", "Quantum Mechanics I", "Fall 2024", "A"),
    ("diego.alvarez@example.edu", "Data Structures", "Fall 2024", "B"),
    ("diego.alvarez@example.edu", "Database Systems", "Fall 2024", "B+"),
    ("wei.zhang@example.edu", "Calculus II", "Fall 2024", "A-"),
    ("wei.zhang@example.edu", "Linear Algebra", "Spring 2024", "A"),
]


async def _country(db: AsyncSession, name: str, code: str) -> Country:
    row = (
        await db.execute(select(Country).where(col(Country.country_code) == code))
    ).scalar_one_or_none()
    if row is None:
        row = Country(country_name=name, country_code=code)
        db.add(row)
        await db.flush()
    return row


async def _department(db: AsyncSession, name: str, building: str | None) -> Department:
    row = (
        await db.execute(select(Department).where(col(Department.department_name) == name))
    ).scalar_one_or_none()
    if row is None:
        row = Department(department_name=name, building=building)
        db.add(row)
        await db.flush()
    return row


async def _teacher(db: AsyncSession, name: str, room: str | None, dept: Department) -> Teacher:
    row = (
        await db.execute(select(Teacher).where(col(Teacher.teacher_name) == name))
    ).scalar_one_or_none()
    if row is None:
        row = Teacher(teacher_name=name, office_room=room, department_id=dept.id)
        db.add(row)
        await db.flush()
    return row


async def _program(db: AsyncSession, name: str, degree: str | None, dept: Department) -> Program:
    row = (
        await db.execute(select(Program).where(col(Program.program_name) == name))
    ).scalar_one_or_none()
    if row is None:
        row = Program(program_name=name, degree_type=degree, department_id=dept.id)
        db.add(row)
        await db.flush()
    return row


async def _course(db: AsyncSession, name: str, credits: int, dept: Department) -> Course:
    row = (
        await db.execute(select(Course).where(col(Course.course_name) == name))
    ).scalar_one_or_none()
    if row is None:
        row = Course(course_name=name, credits=credits, department_id=dept.id)
        db.add(row)
        await db.flush()
    return row


async def _address(
    db: AsyncSession,
    street: str,
    city: str,
    state: str | None,
    postal: str | None,
    country: Country,
) -> Address:
    row = (
        await db.execute(
            select(Address).where(col(Address.street_address) == street, col(Address.city) == city)
        )
    ).scalar_one_or_none()
    if row is None:
        row = Address(
            street_address=street,
            city=city,
            state_province=state,
            postal_code=postal,
            country_id=country.id,
        )
        db.add(row)
        await db.flush()
    return row


async def _student(
    db: AsyncSession,
    *,
    first: str,
    last: str,
    email: str,
    enrolled: date,
    gpa: Decimal | None,
    address: Address,
    dept: Department,
    teacher: Teacher,
    program: Program,
) -> Student:
    row = (
        await db.execute(select(Student).where(col(Student.email) == email))
    ).scalar_one_or_none()
    if row is None:
        row = Student(
            first_name=first,
            last_name=last,
            email=email,
            enrollment_date=enrolled,
            gpa=gpa,
            address_id=address.id,
            department_id=dept.id,
            teacher_id=teacher.id,
            program_id=program.id,
        )
        db.add(row)
        await db.flush()
    return row


async def _enrollment(
    db: AsyncSession, student: Student, course: Course, semester: str, grade: str | None
) -> None:
    existing = (
        await db.execute(
            select(Enrollment).where(
                col(Enrollment.student_id) == student.id,
                col(Enrollment.course_id) == course.id,
                col(Enrollment.semester) == semester,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            Enrollment(student_id=student.id, course_id=course.id, semester=semester, grade=grade)
        )


async def seed() -> None:
    """Seed the students schema; every row is created only if absent."""
    async with async_session_factory() as db:
        countries = {code: await _country(db, name, code) for name, code in COUNTRIES}
        addresses = [
            await _address(db, s, c, st, p, countries[cc]) for s, c, st, p, cc in ADDRESSES
        ]
        departments = {name: await _department(db, name, b) for name, b in DEPARTMENTS}
        teachers = {
            name: await _teacher(db, name, room, departments[dept]) for name, room, dept in TEACHERS
        }
        programs = {
            name: await _program(db, name, degree, departments[dept])
            for name, degree, dept in PROGRAMS
        }
        courses = {
            name: await _course(db, name, credits, departments[dept])
            for name, credits, dept in COURSES
        }

        students: dict[str, Student] = {}
        for first, last, email, enrolled, gpa, addr_idx, dept, teacher, program in STUDENTS:
            students[email] = await _student(
                db,
                first=first,
                last=last,
                email=email,
                enrolled=enrolled,
                gpa=gpa,
                address=addresses[addr_idx],
                dept=departments[dept],
                teacher=teachers[teacher],
                program=programs[program],
            )

        for student_email, mentor_email in MENTORS:
            students[student_email].mentor_id = students[mentor_email].id

        for email, course, semester, grade in ENROLLMENTS:
            await _enrollment(db, students[email], courses[course], semester, grade)

        await db.commit()
    print("Students master-data seed is ready.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
