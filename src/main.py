import asyncio
import json
import math
import os
import pathlib
import re
import shutil
import time

import flet as ft
import pymupdf
import sympy
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel, Field as PydanticField
from sqlalchemy.exc import IntegrityError
from sqlmodel import (
    JSON,
    Column,
    Field,
    Session,
    SQLModel,
    create_engine,
    select,
)
from zxcvbn import zxcvbn


password_hasher = PasswordHasher()


class Name(BaseModel):
    first_name: str
    last_name: str


class User(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    user_name: Name = Field(sa_column=Column(JSON))
    user_id: int = Field(ge=1000, le=99999, unique=True)
    user_pass: str = Field(nullable=False)

    @classmethod
    def create_user(
        cls,
        engine,
        user_name_ent,
        user_id_ent,
        user_pass_ent,
    ):
        with Session(engine) as session:
            new_user = cls(
                user_name=user_name_ent.model_dump(),
                user_id=user_id_ent,
                user_pass=password_hasher.hash(
                    user_pass_ent
                ),
            )

            try:
                session.add(new_user)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    @classmethod
    def update_user_info(
        cls,
        engine,
        user_id,
        value_to_change,
        new_value=None,
    ):
        with Session(engine) as session:
            statement = select(cls).where(
                cls.user_id == user_id
            )

            user = session.exec(
                statement
            ).first()

            if user is None:
                return False

            if (
                value_to_change == "Password"
                and isinstance(new_value, str)
            ):
                user.user_pass = (
                    password_hasher.hash(
                        new_value
                    )
                )

            elif (
                value_to_change == "ID"
                and isinstance(new_value, int)
            ):
                user.user_id = new_value

            else:
                return False

            session.commit()

            return True

    @classmethod
    def remove_user(
        cls,
        engine,
        user_id_ent,
        user_pass_ent,
    ):
        with Session(engine) as session:
            statement = select(cls).where(
                cls.user_id == user_id_ent
            )

            user = session.exec(
                statement
            ).first()

            if user is None:
                return False

            try:
                password_hasher.verify(
                    user.user_pass,
                    user_pass_ent,
                )
            except (
                InvalidHashError,
                VerificationError,
            ):
                return False

            session.delete(user)
            session.commit()

            return True

    @classmethod
    def login(
        cls,
        engine,
        user_id_ent,
        user_pass_ent,
    ):
        with Session(engine) as session:
            statement = select(cls).where(
                cls.user_id == user_id_ent
            )

            user = session.exec(
                statement
            ).first()

            if user is None:
                return False

            try:
                password_hasher.verify(
                    user.user_pass,
                    user_pass_ent,
                )

                if password_hasher.check_needs_rehash(
                    user.user_pass
                ):
                    user.user_pass = (
                        password_hasher.hash(
                            user_pass_ent
                        )
                    )

                    session.commit()

                return True

            except (
                InvalidHashError,
                VerificationError,
            ):
                return False

    @staticmethod
    def db_config():
        db_path = (
            pathlib.Path(__file__).parent
            / "users.db"
        )

        engine = create_engine(
            f"sqlite:///{db_path}"
        )

        SQLModel.metadata.create_all(
            engine
        )

        return engine


class Question(BaseModel):
    question_no: int
    question_sub_let: str = ""
    question_text: str
    question_formula: str | None = None
    question_images: list[str] = PydanticField(
        default_factory=list
    )
    correct_answer: str = ""
    acceptable_answers: list[str] = PydanticField(
        default_factory=list
    )
    answer_working: str = ""


class QuestionSet(BaseModel):
    question_set_name: str
    question_year: str | None = None
    question_list: list[Question] = PydanticField(
        default_factory=list
    )

    def save_to_json(self):
        directory = (
            pathlib.Path(__file__).parent
            / "question_sets"
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (
            directory
            / f"{self.question_set_name}.json"
        )

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.model_dump(),
                file,
                indent=4,
                ensure_ascii=False,
            )

        return file_path

    @classmethod
    def load_from_json(
        cls,
        file_path,
    ):
        try:
            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            return cls.model_validate(data)

        except (
            FileNotFoundError,
            json.JSONDecodeError,
            ValueError,
        ):
            return None


def get_question_sets_directory():
    directory = (
        pathlib.Path(__file__).parent
        / "question_sets"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def get_question_assets_directory():
    directory = (
        pathlib.Path(__file__).parent
        / "question_assets"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def question_set_files():
    directory = (
        get_question_sets_directory()
    )

    return sorted(
        [
            file
            for file in directory.glob("*.json")
            if file.name
            != "question_set_schema.json"
        ]
    )


def password_strength(password):
    if not password:
        return 0, "Enter a password."

    result = zxcvbn(password)

    score = result["score"]

    if score == 0:
        message = "Very weak"
    elif score == 1:
        message = "Weak"
    elif score == 2:
        message = "Moderate"
    elif score == 3:
        message = "Strong"
    else:
        message = "Very strong"

    return score, message


def clean_pdf_text(text):
    text = text.replace(
        "\u00a0",
        " ",
    )

    text = text.replace(
        "\u200b",
        "",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def extract_standard_number(text):
    patterns = [
        r"Achievement Standard\s+(\d{5})",
        r"Achievement Standard.*?(\d{5})",
        r"\b(91\d{3})\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return ""


def extract_year(text):
    years = re.findall(
        r"\b(20\d{2})\b",
        text,
    )

    if not years:
        return ""

    return max(
        set(years),
        key=years.count,
    )


def determine_ncea_level(
    standard_number,
    text,
):
    match = re.search(
        r"NCEA\s+Level\s+([123])",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(
            match.group(1)
        )

    if standard_number.startswith("91"):
        return 3

    return 3


def extract_subject(text):
    if "Calculus" in text:
        return "Calculus"

    if "Physics" in text:
        return "Physics"

    if "Mathematics" in text:
        return "Mathematics"

    return "Unknown"


def extract_pdf_text(pdf_path):
    document = pymupdf.open(
        str(pdf_path)
    )

    text = "\n".join(
        page.get_text()
        for page in document
    )

    document.close()

    return clean_pdf_text(text)


def get_pdf_lines(pdf_path):
    document = pymupdf.open(
        str(pdf_path)
    )

    pages = []

    for page in document:
        blocks = page.get_text(
            "blocks"
        )

        lines = []

        for block in blocks:
            if len(block) < 5:
                continue

            x0, y0, x1, y1, text = (
                block[:5]
            )

            text = clean_pdf_text(text)

            if not text:
                continue

            lines.append(
                {
                    "text": text,
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                }
            )

        lines.sort(
            key=lambda item: item["y0"]
        )

        pages.append(lines)

    document.close()

    return pages


def find_question_headers(
    page_lines
):
    headers = []

    for page_number, lines in enumerate(
        page_lines
    ):
        for index, line in enumerate(
            lines
        ):
            text = line["text"].strip()

            match = re.match(
                r"^(?:QUESTION\s*)?(\d{1,2})"
                r"[\.:]?\s*$",
                text,
                re.IGNORECASE,
            )

            if match:
                number = int(
                    match.group(1)
                )

                if 1 <= number <= 20:
                    headers.append(
                        {
                            "number": number,
                            "page": page_number,
                            "index": index,
                            "y": line["y0"],
                        }
                    )

    return headers


def find_subquestions(lines):
    subquestions = []

    for index, line in enumerate(
        lines
    ):
        text = line["text"].strip()

        match = re.match(
            r"^\(?([a-z])\)?[\.:]?\s+",
            text,
            re.IGNORECASE,
        )

        if match:
            subquestions.append(
                {
                    "index": index,
                    "letter": (
                        match.group(1).lower()
                    ),
                    "y": line["y0"],
                }
            )

    return subquestions


def parse_exam_questions(
    pdf_path
):
    page_lines = get_pdf_lines(
        pdf_path
    )

    headers = find_question_headers(
        page_lines
    )

    questions = []

    for header_index, header in enumerate(
        headers
    ):
        page_number = header["page"]

        lines = page_lines[
            page_number
        ]

        start_index = (
            header["index"] + 1
        )

        if (
            header_index + 1
            < len(headers)
            and headers[
                header_index + 1
            ]["page"]
            == page_number
        ):
            end_index = headers[
                header_index + 1
            ]["index"]
        else:
            end_index = len(lines)

        section = lines[
            start_index:end_index
        ]

        subquestions = find_subquestions(
            section
        )

        if not subquestions:
            text = clean_pdf_text(
                "\n".join(
                    line["text"]
                    for line in section
                )
            )

            if text:
                questions.append(
                    {
                        "number": header[
                            "number"
                        ],
                        "letter": "",
                        "text": text,
                        "page": page_number,
                    }
                )

            continue

        for sub_index, subquestion in enumerate(
            subquestions
        ):
            start = subquestion[
                "index"
            ]

            if (
                sub_index + 1
                < len(subquestions)
            ):
                end = subquestions[
                    sub_index + 1
                ]["index"]
            else:
                end = len(section)

            sub_section = section[
                start:end
            ]

            text = clean_pdf_text(
                "\n".join(
                    line["text"]
                    for line in sub_section
                )
            )

            prefix = re.compile(
                r"^\s*\(?"
                + re.escape(
                    subquestion[
                        "letter"
                    ]
                )
                + r"\)?[\.:]?\s*",
                re.IGNORECASE,
            )

            text = prefix.sub(
                "",
                text,
                count=1,
            )

            if text:
                questions.append(
                    {
                        "number": header[
                            "number"
                        ],
                        "letter": (
                            subquestion[
                                "letter"
                            ]
                        ),
                        "text": text,
                        "page": page_number,
                    }
                )

    return questions


def extract_formula(text):
    formulas = []

    patterns = [
        r"y\s*=\s*[^.;\n]+",
        r"f\s*\(\s*x\s*\)\s*=\s*[^.;\n]+",
        r"[a-zA-Z]\s*['′]\s*=\s*[^.;\n]+",
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE,
        )

        for match in matches:
            match = match.strip()

            if match not in formulas:
                formulas.append(match)

    return "\n".join(
        formulas
    )


def extract_page_images(
    pdf_path,
    page_number,
    question_number,
    sub_letter,
    asset_directory,
):
    document = pymupdf.open(
        str(pdf_path)
    )

    page = document[
        page_number
    ]

    image_paths = []

    for image_number, image_info in enumerate(
        page.get_images(
            full=True
        )
    ):
        xref = image_info[0]

        try:
            image = document.extract_image(
                xref
            )

            extension = image.get(
                "ext",
                "png",
            )

            filename = (
                f"q{question_number}"
                f"{sub_letter or ''}"
                f"_image{image_number}."
                f"{extension}"
            )

            output_path = (
                pathlib.Path(
                    asset_directory
                )
                / filename
            )

            with open(
                output_path,
                "wb",
            ) as file:
                file.write(
                    image["image"]
                )

            image_paths.append(
                str(output_path)
            )

        except Exception:
            continue

    document.close()

    return image_paths


def parse_marking_schedule(
    schedule_path
):
    document = pymupdf.open(
        str(schedule_path)
    )

    pages = []

    for page in document:
        pages.append(
            clean_pdf_text(
                page.get_text()
            )
        )

    document.close()

    return "\n\n".join(
        pages
    )


def extract_schedule_answers(
    schedule_text
):
    answers = {}

    current_question = None
    current_letter = None

    for raw_line in schedule_text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        question_match = re.match(
            r"^(?:Question|QUESTION)"
            r"\s*(\d+)",
            line,
            re.IGNORECASE,
        )

        if question_match:
            current_question = int(
                question_match.group(1)
            )

            current_letter = None

            continue

        sub_match = re.match(
            r"^\(?([a-h])"
            r"[\.\):]\s*(.*)$",
            line,
            re.IGNORECASE,
        )

        if (
            current_question is not None
            and sub_match
        ):
            current_letter = (
                sub_match.group(1).lower()
            )

            content = (
                sub_match.group(2).strip()
            )

            key = (
                current_question,
                current_letter,
            )

            answers.setdefault(
                key,
                [],
            )

            if content:
                answers[key].append(
                    content
                )

            continue

        if (
            current_question is not None
            and current_letter is not None
        ):
            key = (
                current_question,
                current_letter,
            )

            answers.setdefault(
                key,
                []
            ).append(line)

    return answers


def normalize_answer(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    replacements = {
        "−": "-",
        "×": "*",
        "÷": "/",
        "π": "pi",
        "∞": "oo",
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new,
        )

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    return value


def extract_numbers(text):
    return [
        float(number)
        for number in re.findall(
            r"[-+]?(?:\d+(?:\.\d*)?"
            r"|\.\d+)(?:[eE][-+]?\d+)?",
            text,
        )
    ]


def numbers_equivalent(
    first,
    second,
):
    first_numbers = extract_numbers(
        first
    )

    second_numbers = extract_numbers(
        second
    )

    if not first_numbers:
        return False

    if len(first_numbers) != len(
        second_numbers
    ):
        return False

    return all(
        math.isclose(
            first_value,
            second_value,
            rel_tol=1e-8,
            abs_tol=1e-8,
        )
        for first_value, second_value
        in zip(
            first_numbers,
            second_numbers,
        )
    )


def symbolic_equivalent(
    first,
    second,
):
    try:
        first = normalize_answer(
            first
        ).replace(
            "^",
            "**",
        )

        second = normalize_answer(
            second
        ).replace(
            "^",
            "**",
        )

        locals_dictionary = {
            "pi": sympy.pi,
            "sqrt": sympy.sqrt,
            "sin": sympy.sin,
            "cos": sympy.cos,
            "tan": sympy.tan,
            "ln": sympy.log,
            "log": sympy.log,
            "e": sympy.E,
        }

        first_expression = sympy.sympify(
            first,
            locals=locals_dictionary,
        )

        second_expression = sympy.sympify(
            second,
            locals=locals_dictionary,
        )

        return (
            sympy.simplify(
                first_expression
                - second_expression
            )
            == 0
        )

    except Exception:
        return False


def answer_is_correct(
    user_answer,
    acceptable_answers,
):
    user_answer = normalize_answer(
        user_answer
    )

    if not user_answer:
        return False

    for acceptable in acceptable_answers:
        acceptable = normalize_answer(
            acceptable
        )

        if user_answer == acceptable:
            return True

        if numbers_equivalent(
            user_answer,
            acceptable,
        ):
            return True

        if symbolic_equivalent(
            user_answer,
            acceptable,
        ):
            return True

    return False


def build_question_set(
    exam_path,
    schedule_path,
):
    exam_text = extract_pdf_text(
        exam_path
    )

    standard_number = (
        extract_standard_number(
            exam_text
        )
    )

    if not standard_number:
        raise ValueError(
            "Could not determine the "
            "NZQA standard number."
        )

    year = extract_year(
        exam_text
    )

    parsed_questions = (
        parse_exam_questions(
            exam_path
        )
    )

    if not parsed_questions:
        raise ValueError(
            "No questions could be "
            "detected in the exam PDF."
        )

    schedule_text = (
        parse_marking_schedule(
            schedule_path
        )
    )

    schedule_answers = (
        extract_schedule_answers(
            schedule_text
        )
    )

    assets_directory = (
        get_question_assets_directory()
        / f"{standard_number}_{year}"
    )

    if assets_directory.exists():
        shutil.rmtree(
            assets_directory
        )

    assets_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    question_list = []

    for parsed_question in parsed_questions:
        number = parsed_question[
            "number"
        ]

        letter = parsed_question[
            "letter"
        ]

        text = parsed_question[
            "text"
        ]

        formula = extract_formula(
            text
        )

        images = extract_page_images(
            exam_path,
            parsed_question[
                "page"
            ],
            number,
            letter,
            assets_directory,
        )

        answers = schedule_answers.get(
            (
                number,
                letter,
            ),
            [],
        )

        question_list.append(
            Question(
                question_no=number,
                question_sub_let=letter,
                question_text=text,
                question_formula=(
                    formula or None
                ),
                question_images=images,
                correct_answer=(
                    answers[-1]
                    if answers
                    else ""
                ),
                acceptable_answers=answers,
                answer_working="\n".join(
                    answers
                ),
            )
        )

    return QuestionSet(
        question_set_name=(
            f"{standard_number}_{year}"
        ),
        question_year=year or None,
        question_list=question_list,
    )


def question_title(question):
    if question.question_sub_let:
        return (
            f"Question "
            f"{question.question_no}"
            f"({question.question_sub_let})"
        )

    return (
        f"Question "
        f"{question.question_no}"
    )


def humanize_time(seconds):
    seconds = max(int(round(seconds)), 0)

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {secs}s"

    if minutes:
        return f"{minutes}m {secs}s"

    return f"{secs}s"


def quiz_page(
    page,
    question_set,
    duration_seconds=None,
):
    questions = (
        question_set.question_list
    )

    is_timed = duration_seconds is not None

    current_index = 0

    score = 0

    answered = {}

    quiz_start_time = time.monotonic()

    timer_running = True

    timer_generation = 0

    timer_text = ft.Text(
        humanize_time(
            duration_seconds if is_timed else 0
        ),
        size=18,
        weight=ft.FontWeight.BOLD,
    )

    progress_text = ft.Text(
        size=18,
        weight=ft.FontWeight.BOLD,
    )

    score_text = ft.Text(
        size=16,
    )

    question_title_text = ft.Text(
        size=24,
        weight=ft.FontWeight.BOLD,
    )

    question_text = ft.Text(
        size=18,
        selectable=True,
    )

    formula_text = ft.Text(
        size=17,
        selectable=True,
    )

    image_column = ft.Column(
        spacing=10,
    )

    answer_field = ft.TextField(
        label="Your answer",
        multiline=True,
        min_lines=3,
        max_lines=6,
    )

    feedback_text = ft.Text(
        size=18,
    )

    working_text = ft.Text(
        selectable=True,
    )

    previous_button = ft.FilledButton(
        "Previous"
    )

    check_button = ft.FilledButton(
        "Check Answer"
    )

    next_button = ft.FilledButton(
        "Next"
    )

    async def update_timer(generation):
        while (
            timer_running
            and generation == timer_generation
        ):
            await asyncio.sleep(1)

            if (
                not timer_running
                or generation != timer_generation
            ):
                break

            elapsed = (
                time.monotonic()
                - quiz_start_time
            )

            if is_timed:
                remaining = max(
                    duration_seconds - elapsed,
                    0,
                )

                timer_text.value = (
                    humanize_time(remaining)
                )

                if remaining <= 0:
                    stop_timer()
                    show_results()
                    break
            else:
                timer_text.value = (
                    humanize_time(elapsed)
                )

            try:
                page.update()
            except Exception:
                break

    def start_timer():
        nonlocal timer_running
        nonlocal timer_generation
        nonlocal quiz_start_time

        timer_generation += 1

        generation = timer_generation

        quiz_start_time = time.monotonic()

        timer_running = True

        asyncio.create_task(
            update_timer(
                generation
            )
        )

    def stop_timer():
        nonlocal timer_running
        nonlocal timer_generation

        timer_running = False
        timer_generation += 1

    def render_question():
        nonlocal current_index

        question = questions[
            current_index
        ]

        progress_text.value = (
            f"{current_index + 1} "
            f"of {len(questions)}"
        )

        question_title_text.value = (
            question_title(
                question
            )
        )

        question_text.value = (
            question.question_text
        )

        formula_text.value = (
            question.question_formula
            or ""
        )

        answer_field.value = ""

        feedback_text.value = ""

        working_text.value = ""

        image_column.controls.clear()

        for image_path in (
            question.question_images
        ):
            image_file = pathlib.Path(
                image_path
            )

            if image_file.exists():
                image_column.controls.append(
                    ft.Image(
                        src=str(
                            image_file
                        ),
                        fit=ft.BoxFit.CONTAIN,
                        height=350,
                    )
                )

        if current_index in answered:
            result = answered[
                current_index
            ]

            answer_field.value = (
                result["answer"]
            )

            if result["correct"]:
                feedback_text.value = (
                    "Correct!"
                )
            else:
                feedback_text.value = (
                    "Incorrect."
                )

                working_text.value = (
                    "Marking schedule:\n"
                    f"{question.correct_answer}"
                )

            check_button.disabled = True

        else:
            check_button.disabled = False

        previous_button.disabled = (
            current_index == 0
        )

        next_button.disabled = (
            current_index
            == len(questions) - 1
        )

        score_text.value = (
            f"Score: "
            f"{score}/"
            f"{len(questions)}"
        )

        page.update()

    def check_answer(e):
        nonlocal score

        question = questions[
            current_index
        ]

        answer = (
            answer_field.value
            or ""
        ).strip()

        if not answer:
            feedback_text.value = (
                "Please enter an answer."
            )

            page.update()

            return

        if current_index in answered:
            return

        correct = answer_is_correct(
            answer,
            question.acceptable_answers,
        )

        answered[
            current_index
        ] = {
            "answer": answer,
            "correct": correct,
        }

        if correct:
            score += 1

            feedback_text.value = (
                "Correct!"
            )

            working_text.value = ""

        else:
            feedback_text.value = (
                "Incorrect."
            )

            working_text.value = (
                "Marking schedule answer:\n"
                f"{question.correct_answer}"
            )

        check_button.disabled = True

        score_text.value = (
            f"Score: "
            f"{score}/"
            f"{len(questions)}"
        )

        page.update()

    def previous_question(e):
        nonlocal current_index

        if current_index > 0:
            current_index -= 1

            render_question()

    def show_results():
        stop_timer()

        elapsed = (
            time.monotonic()
            - quiz_start_time
        )

        attempted = len(
            answered
        )

        percentage = (
            score / len(questions) * 100
            if questions
            else 0
        )

        result_text = ft.Column(
            controls=[
                ft.Text(
                    "Quiz Complete",
                    size=30,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    f"Score: "
                    f"{score}/"
                    f"{len(questions)}",
                    size=22,
                ),
                ft.Text(
                    f"Percentage: "
                    f"{percentage:.1f}%",
                    size=20,
                ),
                ft.Text(
                    f"Attempted: "
                    f"{attempted}/"
                    f"{len(questions)}",
                    size=18,
                ),
                ft.Text(
                    f"Time: "
                    f"{humanize_time(elapsed)}",
                    size=18,
                ),
            ],
            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
        )

        def restart(e):
            nonlocal current_index
            nonlocal score
            nonlocal quiz_start_time
            nonlocal timer_running

            current_index = 0
            score = 0

            answered.clear()

            page.pop_dialog()

            render_question()

            if is_timed:
                start_timer()
            else:
                quiz_start_time = time.monotonic()

        def home(e):
            stop_timer()

            page.pop_dialog()

            page.navigate(
                "/home"
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Results"
            ),
            content=result_text,
            actions=[
                ft.FilledButton(
                    "Restart",
                    on_click=restart,
                ),
                ft.FilledButton(
                    "Back to Home",
                    on_click=home,
                ),
            ],
        )

        page.show_dialog(
            dialog
        )

    def next_question(e):
        nonlocal current_index

        if (
            current_index
            < len(questions) - 1
        ):
            current_index += 1

            render_question()

        else:
            show_results()

    check_button.on_click = (
        check_answer
    )

    previous_button.on_click = (
        previous_question
    )

    next_button.on_click = (
        next_question
    )

    back_button = ft.FilledButton(
        "Back to Home",
        on_click=lambda e: (
            stop_timer(),
            page.navigate(
                "/home"
            ),
        ),
    )

    header_controls = [
        back_button,
        ft.Container(
            expand=True
        ),
        ft.Text(
            question_set.question_set_name,
            size=20,
            weight=ft.FontWeight.BOLD,
        ),
        ft.Container(
            expand=True
        ),
    ]

    if is_timed:
        header_controls.extend(
            [
                ft.Icon(
                    ft.Icons.TIMER_OUTLINED
                ),
                timer_text,
            ]
        )

    header = ft.Row(
        controls=header_controls
    )

    quiz_controls = ft.Column(
        controls=[
            header,
            ft.Divider(),
            ft.Row(
                controls=[
                    progress_text,
                    ft.Container(
                        expand=True
                    ),
                    score_text,
                ]
            ),
            question_title_text,
            question_text,
            formula_text,
            image_column,
            answer_field,
            ft.Row(
                controls=[
                    check_button,
                    feedback_text,
                ]
            ),
            working_text,
            ft.Divider(),
            ft.Row(
                controls=[
                    previous_button,
                    next_button,
                ],
                alignment=(
                    ft.MainAxisAlignment.CENTER
                ),
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    render_question()

    if is_timed:
        start_timer()

    return ft.View(
        route="/quiz",
        controls=[
            ft.Container(
                content=quiz_controls,
                padding=20,
                expand=True,
            )
        ],
    )


def home_page(page):
    page.title = "Home"

    current_user_id = page.session.store.get("User_ID")
    engine = User.db_config()

    with Session(engine) as session:
        statement = select(User).where(
            User.user_id == current_user_id
        )
        user = session.exec(statement).first()

    if user is None:
        return ft.View(
            route="/home",
            controls=[
                ft.Text("User not found.")
            ],
        )

    user_name = Name.model_validate(
        user.user_name
    ).first_name

    welcome_message = ft.Text(
        f"Welcome, {user_name}!",
        theme_style=ft.TextThemeStyle.DISPLAY_SMALL,
    )

    exam_picker = ft.FilePicker()
    schedule_picker = ft.FilePicker()

    status_text = ft.Text("")
    progress_ring = ft.ProgressRing(
        visible=False,
        width=20,
        height=20,
    )

    saved_list = ft.Column(spacing=5)

    def show_error(message):
        def close_dialog(e):
            page.pop_dialog()

        page.show_dialog(
            ft.AlertDialog(
                modal=False,
                title=ft.Text("Couldn't create quiz"),
                content=ft.Text(message),
                actions=[
                    ft.FilledButton(
                        "Dismiss",
                        on_click=close_dialog,
                    )
                ],
            )
        )

    def start_question_set(question_set, duration_seconds=None):
        page.session.store.set(
            "Current_Question_Set",
            question_set.model_dump_json(),
        )
        page.session.store.set(
            "Quiz_Duration_Seconds",
            duration_seconds,
        )
        page.navigate("/quiz")

    quiz_time_options_minutes = list(
        range(15, 181, 15)
    )

    def open_start_quiz_dialog(question_set):
        default_index = quiz_time_options_minutes.index(60)
        selected = {"index": default_index}

        minutes_value_text = ft.Text(
            f"{quiz_time_options_minutes[default_index]} minutes",
            size=16,
            weight=ft.FontWeight.BOLD,
        )

        def update_spinbox_buttons():
            decrease_button.disabled = (
                selected["index"] == 0
            )
            increase_button.disabled = (
                selected["index"]
                == len(quiz_time_options_minutes) - 1
            )

        def change_minutes(delta):
            def handler(e):
                new_index = selected["index"] + delta
                new_index = max(
                    0,
                    min(
                        len(quiz_time_options_minutes) - 1,
                        new_index,
                    ),
                )
                selected["index"] = new_index
                minutes_value_text.value = (
                    f"{quiz_time_options_minutes[new_index]} minutes"
                )
                update_spinbox_buttons()
                page.update()

            return handler

        decrease_button = ft.IconButton(
            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
            tooltip="15 minutes less",
            on_click=change_minutes(-1),
        )

        increase_button = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            tooltip="15 minutes more",
            on_click=change_minutes(1),
        )

        update_spinbox_buttons()

        minutes_spinbox = ft.Row(
            controls=[
                decrease_button,
                minutes_value_text,
                increase_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
            visible=False,
        )

        def on_mode_change(e):
            minutes_spinbox.visible = (
                mode_radio_group.value == "timed"
            )
            page.update()

        mode_radio_group = ft.RadioGroup(
            value="untimed",
            on_change=on_mode_change,
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Radio(
                        value="untimed",
                        label="Untimed",
                    ),
                    ft.Radio(
                        value="timed",
                        label="Timed",
                    ),
                ],
            ),
        )

        def start_clicked(e):
            page.pop_dialog()

            if mode_radio_group.value == "timed":
                minutes = quiz_time_options_minutes[
                    selected["index"]
                ]
                start_question_set(
                    question_set,
                    minutes * 60,
                )
            else:
                start_question_set(question_set)

        start_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text(
                f'Start "{question_set.question_set_name}"'
            ),
            content=ft.Column(
                tight=True,
                controls=[
                    mode_radio_group,
                    minutes_spinbox,
                ],
            ),
            actions=[
                ft.FilledButton(
                    "Start Quiz",
                    on_click=start_clicked,
                ),
                ft.FilledButton(
                    "Cancel",
                    on_click=lambda e: page.pop_dialog(),
                ),
            ],
        )

        page.show_dialog(start_dialog)

    def refresh_saved_quizzes():
        saved_list.controls.clear()

        files = question_set_files()

        if not files:
            saved_list.controls.append(
                ft.Text("No saved quizzes yet.")
            )
        else:
            for file_path in files:
                def play_saved(e, path=file_path):
                    loaded_set = QuestionSet.load_from_json(path)

                    if loaded_set is None:
                        show_error(
                            "That saved quiz file could not be read."
                        )
                        return

                    open_start_quiz_dialog(loaded_set)

                saved_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(
                                        file_path.stem,
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED,
                                        icon_size=32,
                                        tooltip="Start quiz",
                                        on_click=play_saved,
                                    ),
                                ],
                            ),
                            padding=10,
                        ),
                    )
                )

        page.update()

    async def create_quiz(e):
        exam_files = await exam_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["pdf"],
        )

        if not exam_files:
            return

        schedule_files = await schedule_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["pdf"],
        )

        if not schedule_files:
            return

        create_button.disabled = True
        progress_ring.visible = True
        status_text.value = "Building quiz from PDFs..."
        page.update()

        try:
            new_question_set = await asyncio.to_thread(
                build_question_set,
                exam_files[0].path,
                schedule_files[0].path,
            )
            new_question_set.save_to_json()
        except ValueError as error:
            show_error(str(error))
            return
        except Exception:
            show_error(
                "Something went wrong while reading those PDFs."
            )
            return
        finally:
            create_button.disabled = False
            progress_ring.visible = False
            status_text.value = ""
            page.update()

        refresh_saved_quizzes()
        open_start_quiz_dialog(new_question_set)

    create_button = ft.FilledButton(
        "Create Quiz from PDFs",
        icon=ft.Icons.UPLOAD_FILE_ROUNDED,
        on_click=create_quiz,
    )

    home_column = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            welcome_message,
            ft.Row(
                controls=[create_button, progress_ring],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            status_text,
            ft.Divider(),
            ft.Text(
                "Your saved quizzes",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),
            saved_list,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    refresh_saved_quizzes()

    return ft.View(
        route="/home",
        controls=[
            ft.Container(
                content=home_column,
                padding=20,
                expand=True,
            )
        ],
    )



def settings_dialog(page):
    user_id_icon = ft.Icon(
        ft.Icons.ACCOUNT_CIRCLE_ROUNDED,
        color=ft.Colors.PRIMARY,
        size=40,
    )

    user_id_text_field = ft.TextField(
        label="User ID",
        max_length=5,
        counter="",
        input_filter=ft.NumbersOnlyInputFilter(),
        read_only=True,
        value=f"{page.session.store.get('User_ID')}",
    )

    user_name_field = ft.Row(
        controls=[user_id_icon, user_id_text_field],
        tight=True,
        tooltip="User ID",
    )

    user_password_icon = ft.Icon(
        ft.Icons.PASSWORD,
        color=ft.Colors.SECONDARY,
        size=40,
    )

    def password_change(e):
        current_password_text_field = ft.TextField(
            label="Current Password/Pin",
            password=True,
            can_reveal_password=True,
        )

        new_password_text_field = ft.TextField(
            label="Password/Pin",
            password=True,
            can_reveal_password=True,
        )

        current_password_field = ft.Row(
            [user_password_icon, current_password_text_field],
            tight=True,
            tooltip="Current Password/Pin",
        )

        new_password_field = ft.Row(
            [user_password_icon, new_password_text_field],
            tight=True,
            tooltip="Password/Pin",
        )

        new_password_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[
                current_password_field,
                new_password_field,
            ],
        )

        new_password_fields = ft.Container(
            content=new_password_column,
            padding=10,
        )

        def change_password_verify(e):
            new_value = new_password_text_field.value or ""

            score, _ = password_strength(new_value)

            if (
                not current_password_text_field.value
                or not new_value
                or score < 3
            ):
                def close_dialog(e):
                    page.pop_dialog()

                create_user_input_fail_dialog = ft.AlertDialog(
                    modal=False,
                    title=ft.Text("Input is of Incorrect Type"),
                    content=ft.Text(
                        "Input is of Incorrect Type, please re-enter "
                        "your Password('s) and ensure they are of the "
                        "correct types or are not the original value "
                        "(i.e not blank)"
                    ),
                    scrollable=False,
                    actions=[
                        ft.FilledButton(
                            "Dismiss",
                            on_click=close_dialog,
                        )
                    ],
                )

                page.show_dialog(create_user_input_fail_dialog)
                return False

            engine = User.db_config()

            with Session(engine) as session:
                statement = select(User).where(
                    User.user_id
                    == page.session.store.get("User_ID")
                )

                user = session.exec(statement).first()

                if user is None:
                    return False

                try:
                    password_hasher.verify(
                        user.user_pass,
                        current_password_text_field.value,
                    )
                except (
                    InvalidHashError,
                    VerificationError,
                ):
                    def close_dialog(e):
                        page.pop_dialog()

                    fail_dialog = ft.AlertDialog(
                        modal=False,
                        title=ft.Text("Input is of Incorrect Type"),
                        content=ft.Text(
                            "Input is of Incorrect Type, please re-enter "
                            "your Password('s) and ensure they are of the "
                            "correct types or are not the original value "
                            "(i.e not blank)"
                        ),
                        scrollable=False,
                        actions=[
                            ft.FilledButton(
                                "Dismiss",
                                on_click=close_dialog,
                            )
                        ],
                    )

                    page.show_dialog(fail_dialog)
                    return False

                user.user_pass = password_hasher.hash(
                    new_value
                )
                session.commit()

            page.pop_dialog()

        create_user_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Change Password"),
            content=new_password_fields,
            actions=[
                ft.FilledButton(
                    "Change Password",
                    on_click=change_password_verify,
                )
            ],
        )

        page.show_dialog(create_user_dialog)
        return False

    password_change_button = ft.FilledButton(
        "Reset Password",
        on_click=password_change,
    )

    user_pass_textfield = ft.TextField(
        label="Password/Pin",
        password=True,
        can_reveal_password=False,
        read_only=True,
        value="Password stored securely",
    )

    user_password_field = ft.Row(
        controls=[user_password_icon, user_pass_textfield],
        tight=True,
        tooltip="Password/Pin",
    )

    user_info_fields = ft.Column(
        tight=True,
        controls=[
            user_name_field,
            user_password_field,
            password_change_button,
        ],
    )

    user_info_container = ft.Container(
        alignment=ft.Alignment.CENTER_LEFT,
        content=user_info_fields,
    )

    def toggle_theme(e):
        page.theme_mode = (
            ft.ThemeMode.DARK
            if e.control.value
            else ft.ThemeMode.LIGHT
        )

        theme_icon.icon = (
            ft.Icons.DARK_MODE_ROUNDED
            if e.control.value
            else ft.Icons.LIGHT_MODE_ROUNDED
        )

        page.update()

    theme_icon = ft.Icon(
        ft.Icons.DARK_MODE_ROUNDED
        if page.theme_mode == ft.ThemeMode.DARK
        else ft.Icons.LIGHT_MODE_ROUNDED,
        color=ft.Colors.SECONDARY,
        size=40,
    )

    theme_toggle = ft.Switch(
        value=page.theme_mode == ft.ThemeMode.DARK,
        tooltip="Toggle light/dark theme",
        on_change=toggle_theme,
    )

    theme_row = ft.Row(
        controls=[
            theme_icon,
            theme_toggle,
        ],
        tight=True,
    )

    settings_column = ft.Column(
        tight=True,
        controls=[
            user_info_container,
            ft.Divider(),
            theme_row,
        ],
    )

    return ft.AlertDialog(
        modal=False,
        title=ft.Text("Settings"),
        content=ft.Container(
            content=settings_column,
            padding=10,
            width=350,
        ),
        actions=[
            ft.FilledButton(
                "Close",
                on_click=lambda e: page.pop_dialog(),
            )
        ],
    )



def login_page(page):
    page.title = "Login"

    login_title = ft.Text(
        "Login",
        theme_style=ft.TextThemeStyle.DISPLAY_SMALL,
    )

    user_id_icon = ft.Icon(
        ft.Icons.ACCOUNT_CIRCLE_ROUNDED,
        color=ft.Colors.PRIMARY,
        size=40,
    )

    user_id_text_field = ft.TextField(
        label="User ID",
        max_length=5,
        counter="",
        input_filter=ft.NumbersOnlyInputFilter(),
    )

    user_name_field = ft.Row(
        [user_id_icon, user_id_text_field],
        tight=True,
        tooltip="User ID",
    )

    user_password_icon = ft.Icon(
        ft.Icons.PASSWORD,
        color=ft.Colors.PRIMARY,
        size=40,
    )

    user_password_text_field = ft.TextField(
        label="Password/Pin",
        password=True,
        can_reveal_password=True,
    )

    user_password_field = ft.Row(
        [user_password_icon, user_password_text_field],
        tight=True,
        tooltip="Password/Pin",
    )

    def login_on_click(e):
        try:
            if len(user_id_text_field.value or "") != 5:
                raise ValueError

            user_id_ent = int(user_id_text_field.value)

            if not user_password_text_field.value:
                raise ValueError

        except ValueError:
            def close_dialog(e):
                page.pop_dialog()

            input_fail_dialog = ft.AlertDialog(
                modal=False,
                title=ft.Text("Input is of Incorrect Type"),
                content=ft.Text(
                    "Input is of Incorrect Type, please re-enter "
                    "your user ID and/or Password and ensure they "
                    "are of the correct types (i.e not blank)"
                ),
                scrollable=False,
                actions=[
                    ft.FilledButton(
                        "Dismiss",
                        on_click=close_dialog,
                    )
                ],
            )

            page.show_dialog(input_fail_dialog)
            return False

        engine = User.db_config()

        login_success = User.login(
            engine,
            user_id_ent,
            user_password_text_field.value,
        )

        if login_success:
            page.session.store.set(
                "User_ID",
                user_id_ent,
            )
            page.navigate("/home")

        else:
            def close_dialog(e):
                page.pop_dialog()

            login_fail_dialog = ft.AlertDialog(
                modal=False,
                title=ft.Text("Login Unsuccesful"),
                content=ft.Text(
                    "Login Unsuccesful, user ID and/or Password "
                    "may be incorrect, please re-enter these "
                    "values and try again"
                ),
                scrollable=False,
                actions=[
                    ft.FilledButton(
                        "Dismiss",
                        on_click=close_dialog,
                    )
                ],
            )

            page.show_dialog(login_fail_dialog)

    login_button = ft.FilledButton(
        content=ft.Text("Login"),
        on_click=login_on_click,
    )

    def on_create_user_button_click(e):
        def close_dialog(e):
            page.pop_dialog()

        create_user_fname_text_field = ft.TextField(
            label="First Name",
        )

        create_user_lname_text_field = ft.TextField(
            label="Last Name",
        )

        name_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[
                create_user_fname_text_field,
                create_user_lname_text_field,
            ],
        )

        user_name_icon = ft.Icon(
            ft.Icons.BADGE_ROUNDED,
            color=ft.Colors.PRIMARY,
            size=40,
        )

        create_user_name_field = ft.Row(
            [user_name_icon, name_column],
            tight=True,
            tooltip="Name",
        )

        create_user_id_text_field = ft.TextField(
            label="User ID",
            max_length=5,
            counter="",
            input_filter=ft.NumbersOnlyInputFilter(),
        )

        create_user_id_field = ft.Row(
            [user_id_icon, create_user_id_text_field],
            tight=True,
            tooltip="User ID",
        )

        create_user_password_text_field = ft.TextField(
            label="Password/Pin",
            password=True,
            can_reveal_password=True,
        )

        create_user_password_field = ft.Row(
            [user_password_icon, create_user_password_text_field],
            tight=True,
            tooltip="Password/Pin",
        )

        create_user_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[
                create_user_name_field,
                create_user_id_field,
                create_user_password_field,
            ],
        )

        create_user_fields = ft.Container(
            content=create_user_column,
            padding=10,
        )

        def on_close(engine, user_name, user_id, user_pass):
            is_user_creation_success = User.create_user(
                engine,
                user_name,
                user_id,
                user_pass,
            )

            def close_created_dialog(e):
                page.pop_dialog()

            if not is_user_creation_success:
                unique_fail_dialog = ft.AlertDialog(
                    modal=False,
                    title=ft.Text(
                        "User Information entered is not unique"
                    ),
                    content=ft.Text(
                        "User Information entered is not unique, "
                        "please re-enter your user ID and/or Password "
                        "and ensure they are unique values"
                    ),
                    scrollable=False,
                    actions=[
                        ft.FilledButton(
                            "Dismiss",
                            on_click=close_created_dialog,
                        )
                    ],
                )

                page.show_dialog(unique_fail_dialog)
                return False

            page.pop_dialog()

            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "User Created Succesfully! Please re-enter "
                        "your login information above to login in "
                    ),
                    show_close_icon=True,
                    duration=10000,
                )
            )

        def create_user_verify(e):
            try:
                if len(create_user_id_text_field.value or "") == 5:
                    create_user_id_ent = int(
                        create_user_id_text_field.value
                    )
                else:
                    raise ValueError

                if not create_user_password_text_field.value:
                    raise ValueError

                if (
                    create_user_fname_text_field.value == ""
                    or create_user_lname_text_field.value == ""
                ):
                    raise ValueError

            except ValueError:
                def close_dialog(e):
                    page.pop_dialog()

                create_user_input_fail_dialog = ft.AlertDialog(
                    modal=False,
                    title=ft.Text("Input is of Incorrect Type"),
                    content=ft.Text(
                        "Input is of Incorrect Type, please re-enter "
                        "your user ID and/or Password and ensure they "
                        "are of the correct types (i.e not blank)"
                    ),
                    scrollable=False,
                    actions=[
                        ft.FilledButton(
                            "Dismiss",
                            on_click=close_dialog,
                        )
                    ],
                )

                page.show_dialog(create_user_input_fail_dialog)
                return False

            engine = User.db_config()

            create_user_name = Name(
                first_name=create_user_fname_text_field.value,
                last_name=create_user_lname_text_field.value,
            )

            on_close(
                engine,
                create_user_name,
                create_user_id_ent,
                create_user_password_text_field.value,
            )

        create_user_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Create User"),
            content=create_user_fields,
            actions=[
                ft.FilledButton(
                    "Create User",
                    on_click=create_user_verify,
                )
            ],
        )

        page.show_dialog(create_user_dialog)
        return False

    create_user_button = ft.FilledButton(
        content=ft.Text("Create User"),
        on_click=on_create_user_button_click,
    )

    actions_row = ft.Row(
        [login_button, create_user_button],
        tight=True,
    )

    login_fields = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            login_title,
            user_name_field,
            user_password_field,
            actions_row,
        ],
    )

    login_card = ft.Card(
        shadow_color=ft.Colors.ON_SURFACE_VARIANT,
        content=ft.Container(
            padding=10,
            content=login_fields,
        ),
        opacity=0.65,
    )

    return ft.View(
        route="/login",
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[login_card],
    )



def main(page):
    page.title = "NCEA Quiz"

    page.theme_mode = ft.ThemeMode.DARK

    page.horizontal_alignment = ft.MainAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    page.padding = 10

    def logout(e):
        def user_confirm_logout(e):
            page.pop_dialog()
            page.session.store.clear()
            page.navigate("/login")

        yes_button = ft.FilledButton(
            "Yes",
            on_click=user_confirm_logout,
        )

        no_button = ft.FilledButton(
            "No",
            on_click=lambda e: page.pop_dialog(),
        )

        user_confirm_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Logout"),
            content=ft.Text(
                "Are you sure you wish to logout?"
            ),
            actions=[yes_button, no_button],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.show_dialog(user_confirm_dialog)

    logout_button = ft.FilledButton(
        content=ft.Text("Logout"),
        on_click=logout,
    )

    logout_container = ft.Container(
        content=logout_button,
        alignment=ft.Alignment.TOP_RIGHT,
    )

    def home_route_change(e):
        if e.control.selected_index == 1:
            navigation_bar.selected_index = 0
            page.show_dialog(settings_dialog(page))
        else:
            page.navigate("/home")

    navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=home_route_change,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_ROUNDED,
                label="Home",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ACCOUNT_CIRCLE_ROUNDED,
                label="",
                tooltip="Settings",
            ),
        ],
    )

    page.session.store.set(
        "User_ID",
        "",
    )

    def route_change(e):
        page.views.clear()

        route = page.route

        logged_in = (
            page.session.store.get("User_ID")
            != ""
        )

        if route == "/login":
            page.views.append(
                login_page(page)
            )

        elif route == "/home" and logged_in:
            navigation_bar.selected_index = 0
            navigation_bar.destinations[1].label = (
                f"{page.session.store.get('User_ID')}"
            )

            view = home_page(page)
            view.navigation_bar = navigation_bar
            page.views.append(view)

            page.add(logout_container)

        elif route == "/quiz" and logged_in:
            question_set_json = (
                page.session.store.get(
                    "Current_Question_Set"
                )
            )

            if not question_set_json:
                page.navigate("/home")
                return

            try:
                question_set = (
                    QuestionSet.model_validate_json(
                        question_set_json
                    )
                )
            except Exception:
                page.navigate("/home")
                return

            duration_seconds = page.session.store.get(
                "Quiz_Duration_Seconds"
            )

            page.views.append(
                quiz_page(
                    page,
                    question_set,
                    duration_seconds,
                )
            )

        else:
            page.navigate("/login")
            return

        page.update()

    page.on_route_change = route_change

    page.navigate("/login")




if __name__ == "__main__":
    ft.run(main)