import json
import os
import pathlib
import re

import flet as ft
import pdfplumber
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import JSON, Column, Field, Session, SQLModel, create_engine, select


class Name(BaseModel):
    first_name: str
    last_name: str


class User(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(primary_key=True)
    user_name: Name = Field(sa_column=Column(JSON))
    user_id: int = Field(ge=1000, le=9999, unique=True, nullable=False)
    user_pass: str = Field(nullable=False)

    @classmethod
    def create_user(
        cls, engine, user_name_ent: Name, user_id_ent: int, user_pass_ent: str
    ) -> bool:
        with Session(engine) as session:
            new_user = cls(
                user_name=user_name_ent.model_dump(),
                user_id=user_id_ent,
                user_pass=user_pass_ent,
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
        cls, engine, user_id, value_to_change: str, new_value: str | int | None = None
    ) -> bool:
        with Session(engine) as session:
            statement = select(cls).where(cls.user_id == user_id)
            user = session.exec(statement).first()

            match value_to_change:
                case "ID" if isinstance(new_value, int):
                    user.user_id = new_value
                case "Password" if isinstance(new_value, str):
                    user.user_pass = new_value
                case _:
                    return False

            session.commit()
            return True

    @classmethod
    def remove_user(cls, engine, user_name_ent, user_id_ent, user_pass_ent) -> None:
        with Session(engine) as session:
            statement = select(User).where(
                User.user_id == user_id_ent, User.user_pass == user_pass_ent
            )
            user = session.exec(statement).first()
            if user is not None:
                session.delete(user)
                session.commit()

    @classmethod
    def login(cls, engine, user_id_ent: int, user_pass_ent: str) -> bool:
        with Session(engine) as session:
            statement = select(cls).where(
                cls.user_id == user_id_ent, cls.user_pass == user_pass_ent
            )
            user_exists = session.exec(statement).first()
            return user_exists is not None

    @staticmethod
    def db_config():
        db_file_name = os.path.join(os.path.dirname(__file__), "users.db")
        engine = create_engine(f"sqlite:///{db_file_name}")
        SQLModel.metadata.create_all(engine)
        return engine


class Question(BaseModel):
    question_no: int
    question_sub_let: str = Field(max_length=1)
    question_text: str
    question_formula: str | None
    correct_answer: str | None = None


class QuestionSet(BaseModel):
    question_set_name: str
    question_year: str | None
    question_list: list[Question]

    def save_to_json(self):
        with open(f"{self.question_set_name}.json", "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=4))

    @classmethod
    def load_from_json(cls, json_file_to_read):
        try:
            if not json_file_to_read.endswith(".json"):
                json_file_to_read = f"{json_file_to_read}.json"

            with open(json_file_to_read, "r", encoding="utf-8") as f:
                output_from_file = json.load(f)

            question_set = cls.model_validate(output_from_file)
            return question_set
        except ValueError:
            return "Inputed File invaild"
        except FileNotFoundError:
            return "File couldn't be found"


QUESTION_WORD_TO_NUMBER = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
    "SIX": 6,
    "SEVEN": 7,
    "EIGHT": 8,
    "NINE": 9,
    "TEN": 10,
}

SUBPART_PATTERN = re.compile(r"^\(?([a-d])\)\s*(.*)$", re.IGNORECASE)
QUESTION_HEADER_PATTERN = re.compile(r"^QUESTION\s+([A-Z]+)", re.IGNORECASE)
SCHEDULE_Q_PATTERN = re.compile(r"Q?\s*(\d+)\s*\(?([a-d])\)?", re.IGNORECASE)


def parse_ncea_pdf(pdf_path: str) -> QuestionSet:
    questions: list[Question] = []
    current_question: Question | None = None
    current_question_no: int | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                header_match = QUESTION_HEADER_PATTERN.match(stripped)
                if header_match:
                    word = header_match.group(1).upper()
                    current_question_no = QUESTION_WORD_TO_NUMBER.get(word)
                    current_question = None
                    continue

                sub_match = SUBPART_PATTERN.match(stripped)
                if sub_match and current_question_no is not None:
                    if current_question is not None:
                        questions.append(current_question)

                    sub_letter = sub_match.group(1).lower()
                    text_part = sub_match.group(2)

                    current_question = Question(
                        question_no=current_question_no,
                        question_sub_let=sub_letter,
                        question_text=text_part,
                        question_formula=None,
                    )
                else:
                    if current_question is not None:
                        current_question.question_text += " " + stripped

        if current_question is not None:
            questions.append(current_question)

    question_set_name = pathlib.Path(pdf_path).stem

    return QuestionSet(
        question_set_name=question_set_name,
        question_year=None,
        question_list=questions,
    )


def parse_mark_schedule(pdf_path: str) -> dict[tuple[int, str], str]:
    answers: dict[tuple[int, str], str] = {}
    current_key: tuple[int, str] | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                match = SCHEDULE_Q_PATTERN.match(stripped.replace(" ", ""))
                if match:
                    q_no = int(match.group(1))
                    sub = match.group(2).lower()
                    current_key = (q_no, sub)
                    continue

                if current_key is not None:
                    if current_key not in answers:
                        answers[current_key] = stripped
                    else:
                        answers[current_key] += " " + stripped

    return answers


def normalize_answer(ans: str) -> str:
    return ans.strip().lower().replace(" ", "")


def is_equivalent(user_answer: str, correct_answer: str | None) -> bool:
    if correct_answer is None:
        return False

    try:
        u = float(user_answer)
        c = float(correct_answer)
        return abs(u - c) <= 1e-2
    except ValueError:
        pass

    return normalize_answer(user_answer) == normalize_answer(correct_answer)


def home_page(page: ft.Page) -> ft.View:
    page.title = "Home"

    current_user_id = page.session.store.get("User_ID")
    engine = User.db_config()

    with Session(engine) as session:
        statement = select(User).where(User.user_id == current_user_id)
        user = session.exec(statement).first()
        user_name = Name.model_validate(user.user_name).first_name

    welcome_message = ft.Text(
        f"Welcome, {user_name}!", theme_style=ft.TextThemeStyle.DISPLAY_SMALL
    )

    question_sets_dir = pathlib.Path(__file__).parent / "question_sets"

    if not question_sets_dir.exists():
        question_sets_dir.mkdir(parents=True, exist_ok=True)

    json_path = question_sets_dir / "question_set_schema.json"

    if not json_path.exists():
        with open(json_path, "w") as f:
            json_schema = QuestionSet.model_json_schema()
            json.dump(json_schema, f, indent=4)

    exam_path_text = ft.Text("No exam selected")
    schedule_path_text = ft.Text("No schedule selected")

    def on_exam_result(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            exam_file = e.files[0]
            page.session.store.set("Exam_PDF", exam_file.path)
            exam_path_text.value = exam_file.name
            page.update()

    def on_schedule_result(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            schedule_file = e.files[0]
            page.session.store.set("Schedule_PDF", schedule_file.path)
            schedule_path_text.value = schedule_file.name
            page.update()

    exam_picker = ft.FilePicker(on_result=on_exam_result)
    schedule_picker = ft.FilePicker(on_result=on_schedule_result)

    page.overlay.append(exam_picker)
    page.overlay.append(schedule_picker)

    async def select_exam(e):
        await exam_picker.pick_files(allow_multiple=False)

    async def select_schedule(e):
        await schedule_picker.pick_files(allow_multiple=False)

    def open_upload_dialog(e):
        def close_dialog(e):
            page.pop_dialog()

        def start_quiz(e):
            exam_path = page.session.store.get("Exam_PDF")
            schedule_path = page.session.store.get("Schedule_PDF")
            if not exam_path or not schedule_path:
                return
            page.pop_dialog()
            page.navigate("/quiz")

        dialog_content = ft.Column(
            controls=[
                ft.Text("Select NCEA Exam Paper and Marking Schedule"),
                ft.Row(
                    controls=[
                        ft.FilledButton("Select Exam PDF", on_click=select_exam),
                        exam_path_text,
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            "Select Schedule PDF", on_click=select_schedule
                        ),
                        schedule_path_text,
                    ]
                ),
            ]
        )

        upload_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Create Quiz from NCEA Paper"),
            content=dialog_content,
            actions=[
                ft.FilledButton("Start Quiz", on_click=start_quiz),
                ft.FilledButton("Close", on_click=close_dialog),
            ],
        )

        page.show_dialog(upload_dialog)

    upload_button = ft.FilledButton(
        content=ft.Text("Create Quiz from NCEA Paper"), on_click=open_upload_dialog
    )

    welcome_container = ft.Container(
        alignment=ft.Alignment.TOP_CENTER,
        content=ft.Column(
            controls=[
                welcome_message,
                upload_button,
            ]
        ),
        expand=True,
    )

    return ft.View(
        route="/home",
        controls=[welcome_container],
    )


def login_page(page: ft.Page) -> ft.View:
    page.title = "Login"

    login_title = ft.Text("Login", theme_style=ft.TextThemeStyle.DISPLAY_SMALL)

    user_id_icon = ft.Icon(
        ft.Icons.ACCOUNT_CIRCLE_ROUNDED, color=ft.Colors.PRIMARY, size=40
    )

    user_id_text_field = ft.TextField(
        label="User ID",
        max_length=5,
        counter="",
        input_filter=ft.NumbersOnlyInputFilter(),
    )

    user_name_field = ft.Row(
        [user_id_icon, user_id_text_field], tight=True, tooltip="User ID"
    )

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40)

    user_password_text_field = ft.TextField(
        label="Password/Pin", password=True, can_reveal_password=True
    )

    user_password_field = ft.Row(
        [user_password_icon, user_password_text_field],
        tight=True,
        tooltip="Password/Pin",
    )

    def login_on_click(e):
        try:
            if len(user_id_text_field.value) != 5:
                raise ValueError

            user_id_ent = int(user_id_text_field.value)

            if user_password_text_field.value == "":
                raise ValueError

        except ValueError:
            def close_dialog(e):
                page.pop_dialog()

            input_fail_dialog = ft.AlertDialog(
                modal=False,
                title=ft.Text("Input is of Incorrect Type"),
                content=ft.Text(
                    "Input is of Incorrect Type, please re-enter your user ID and/or Password and ensure they are of the correct types (i.e not blank)"
                ),
                scrollable=False,
                actions=[ft.FilledButton("Dismiss", on_click=close_dialog)],
            )

            page.show_dialog(input_fail_dialog)
            return False

        engine = User.db_config()
        user_password_ent = user_password_text_field.value

        login_success = User.login(engine, user_id_ent, user_password_ent)

        if login_success:
            page.session.store.set("User_ID", user_id_ent)
            page.navigate("/home")
        else:
            def close_dialog(e):
                page.pop_dialog()

            login_fail_dialog = ft.AlertDialog(
                modal=False,
                title=ft.Text("Login Unsuccesful"),
                content=ft.Text(
                    "Login Unsuccesful, user ID and/or Password may be incorrect, please re-enter these values and try again"
                ),
                scrollable=False,
                actions=[ft.FilledButton("Dismiss", on_click=close_dialog)],
            )

            page.show_dialog(login_fail_dialog)

    login_button = ft.FilledButton(content=ft.Text("Login"), on_click=login_on_click)

    def on_create_user_button_click(e):
        def close_dialog(e):
            page.pop_dialog()

        create_user_fname_text_field = ft.TextField(label="First Name")
        create_user_lname_text_field = ft.TextField(label="Last Name")

        name_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[create_user_fname_text_field, create_user_lname_text_field],
        )

        user_name_icon = ft.Icon(
            ft.Icons.BADGE_ROUNDED, color=ft.Colors.PRIMARY, size=40
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
            [user_id_icon, create_user_id_text_field], tight=True, tooltip="User ID"
        )

        create_user_password_text_field = ft.TextField(
            label="Password/Pin", password=True, can_reveal_password=True
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

        create_user_fields = ft.Container(content=create_user_column, padding=10)

        def on_close(engine, user_name, user_id, user_pass):
            is_user_creation_success = User.create_user(
                engine, user_name, user_id, user_pass
            )

            def close_dialog():
                page.pop_dialog()

            if not is_user_creation_success:
                unique_fail_dialog = ft.AlertDialog(
                    modal=False,
                    title=ft.Text("User Information entered is not unique"),
                    content=ft.Text(
                        "User Information entered is not unique, please re-enter your user ID and/or Password and ensure they are unique values"
                    ),
                    scrollable=False,
                    actions=[ft.FilledButton("Dismiss", on_click=close_dialog)],
                )

                page.show_dialog(unique_fail_dialog)
                return False
            else:
                page.pop_dialog()
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text(
                            "User Created Succesfully! Please re-enter your login information above to login in "
                        ),
                        show_close_icon=True,
                        duration=10000,
                    )
                )

        def create_user_verify(e):
            try:
                if len(create_user_id_text_field.value) == 5:
                    create_user_id_ent = int(create_user_id_text_field.value)
                else:
                    raise ValueError

                if create_user_password_text_field.value == "":
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
                        "Input is of Incorrect Type, please re-enter your user ID and/or Password and ensure they are of the correct types (i.e not blank)"
                    ),
                    scrollable=False,
                    actions=[ft.FilledButton("Dismiss", on_click=close_dialog)],
                )

                page.show_dialog(create_user_input_fail_dialog)
                return False

            engine = User.db_config()
            create_user_password_text_field_ent = create_user_password_text_field.value
            create_user_name = Name(
                first_name=create_user_fname_text_field.value,
                last_name=create_user_lname_text_field.value,
            )

            on_close(
                engine,
                create_user_name,
                create_user_id_ent,
                create_user_password_text_field_ent,
            )

        create_user_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Create User"),
            content=create_user_fields,
            actions=[ft.FilledButton("Create User", on_click=create_user_verify)],
        )

        page.show_dialog(create_user_dialog)
        return False

    create_user_button = ft.FilledButton(
        content=ft.Text("Create User"), on_click=on_create_user_button_click
    )

    actions_row = ft.Row([login_button, create_user_button], tight=True)

    login_fields = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[login_title, user_name_field, user_password_field, actions_row],
    )

    login_card = ft.Card(
        shadow_color=ft.Colors.ON_SURFACE_VARIANT,
        content=ft.Container(padding=10, content=login_fields),
        opacity=0.65,
    )

    db_path = pathlib.Path(__file__).parent / "users.db"

    if not db_path.exists():
        on_create_user_button_click(None)

    return ft.View(
        route="/login",
        horizontal_alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[login_card],
    )


def settings_page(page: ft.Page) -> ft.View:
    page.title = "Settings"

    title = ft.Text("Settings", theme_style=ft.TextThemeStyle.DISPLAY_MEDIUM)

    user_id_icon = ft.Icon(
        ft.Icons.ACCOUNT_CIRCLE_ROUNDED, color=ft.Colors.PRIMARY, size=40
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
        controls=[user_id_icon, user_id_text_field], tight=True, tooltip="User ID"
    )

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.SECONDARY, size=40)

    def password_change(e):
        def close_dialog(e):
            page.pop_dialog()

        user_password_icon_inner = ft.Icon(
            ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40
        )

        current_password_text_field = ft.TextField(
            label="Current Password/Pin", password=True, can_reveal_password=True
        )

        current_password_field = ft.Row(
            [user_password_icon_inner, current_password_text_field],
            tight=True,
            tooltip="Current Password/Pin",
        )

        new_password_text_field = ft.TextField(
            label="Password/Pin", password=True, can_reveal_password=True
        )

        new_password_field = ft.Row(
            [user_password_icon_inner, new_password_text_field],
            tight=True,
            tooltip="Password/Pin",
        )

        new_password_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[current_password_field, new_password_field],
        )

        new_password_fields = ft.Container(content=new_password_column, padding=10)

        def on_close(pass_values):
            engine = User.db_config()
            User.update_user_info(
                engine,
                page.session.store.get("User_ID"),
                "Password",
                pass_values["New_Password"],
            )
            page.pop_dialog()

        def change_password_verify(e):
            try:
                if current_password_text_field.value == "" or new_password_text_field.value == "":
                    raise ValueError

                pass_values = {
                    "Current_Password": current_password_text_field.value,
                    "New_Password": new_password_text_field.value,
                }

                engine = User.db_config()

                with Session(engine) as session:
                    statement = select(User).where(
                        User.user_id == page.session.store.get("User_ID"),
                        User.user_pass == pass_values["Current_Password"],
                    )
                    user = session.exec(statement).first()

                    if user is None:
                        raise ValueError

            except ValueError:
                def close_dialog(e):
                    page.pop_dialog()

                create_user_input_fail_dialog = ft.AlertDialog(
                    modal=False,
                    title=ft.Text("Input is of Incorrect Type"),
                    content=ft.Text(
                        "Input is of Incorrect Type, please re-enter your Password('s) and ensure they are of the correct types or are not the original value(i.e not blank)"
                    ),
                    scrollable=False,
                    actions=[ft.FilledButton("Dismiss", on_click=close_dialog)],
                )

                page.show_dialog(create_user_input_fail_dialog)
                return False

            on_close(pass_values)

        create_user_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Change Password"),
            content=new_password_fields,
            actions=[
                ft.FilledButton("Change Password", on_click=change_password_verify)
            ],
        )

        page.show_dialog(create_user_dialog)
        return False

    password_change_button = ft.FilledButton("Reset Password", on_click=password_change)

    check_pass_engine = User.db_config()

    with Session(check_pass_engine) as session:
        statement = select(User).where(
            User.user_id == page.session.store.get("User_ID"),
        )
        user = session.exec(statement).first()

        user_pass = user.user_pass

    def show_pass(e):
        if user_pass_textfield.password:
            user_reveal_pass.icon = ft.Icons.VISIBILITY_OFF_ROUNDED

            user_password_icon_inner = ft.Icon(
                ft.Icons.PASSWORD, color=ft.Colors.SECONDARY, size=40
            )

            password_text_field = ft.TextField(
                label="Password/Pin", password=True, can_reveal_password=True
            )

            password_field = ft.Row(
                [user_password_icon_inner, password_text_field],
                tight=True,
                tooltip="Current Password/Pin",
            )

            def close_dialog(e):
                page.pop_dialog()

            def check_pass_ent(e):
                try:
                    if password_text_field.value == "":
                        raise ValueError

                    engine = User.db_config()

                    with Session(engine) as session:
                        statement = select(User).where(
                            User.user_id == page.session.store.get("User_ID"),
                            User.user_pass == password_text_field.value,
                        )
                        user = session.exec(statement).first()

                        if user is None:
                            raise ValueError
                        else:
                            user_pass_textfield.password = False
                            user_reveal_pass.icon = ft.Icons.VISIBILITY_OFF_ROUNDED
                            page.pop_dialog()
                            page.update()

                except ValueError:
                    def close_dialog(e):
                        page.pop_dialog()

                    pass_input_fail_dialog = ft.AlertDialog(
                        modal=False,
                        title=ft.Text("Password Incorrect"),
                        content=ft.Text(
                            "Input is of Incorrect Type or is incorrect, please re-enter your Password and ensure they are of the correct types and value (i.e not blank)"
                        ),
                        scrollable=False,
                        actions=[ft.FilledButton("Dismiss", on_click=close_dialog)],
                    )

                    page.show_dialog(pass_input_fail_dialog)
                    return False

            check_pass_dialog = ft.AlertDialog(
                modal=False,
                title=ft.Text("Password Verification"),
                content=password_field,
                actions=[ft.FilledButton("Check Password", on_click=check_pass_ent)],
            )

            page.show_dialog(check_pass_dialog)

        else:
            user_reveal_pass.icon = ft.Icons.VISIBILITY_ROUNDED
            user_pass_textfield.password = True
            page.update()

    user_reveal_pass = ft.IconButton(
        icon=ft.Icons.VISIBILITY_ROUNDED, on_click=show_pass
    )

    user_pass_textfield = ft.TextField(
        label="Password/Pin",
        password=True,
        can_reveal_password=False,
        read_only=True,
        value=user_pass,
        suffix=user_reveal_pass,
    )

    user_password_field = ft.Row(
        controls=[user_password_icon, user_pass_textfield],
        tight=True,
        tooltip="Password/Pin",
    )

    user_info_fields = ft.Column(
        tight=True,
        controls=[user_name_field, user_password_field, password_change_button],
    )

    user_info_container = ft.Container(
        alignment=ft.Alignment.CENTER_LEFT, content=user_info_fields
    )

    settings_column = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[title, user_info_container],
    )

    settings_view = ft.View(
        route="/settings",
        controls=[
            ft.Container(
                alignment=ft.Alignment.TOP_CENTER, content=settings_column, expand=True
            )
        ],
    )
    return settings_view


def quiz_page(page: ft.Page) -> ft.View:
    exam_path = page.session.store.get("Exam_PDF")
    schedule_path = page.session.store.get("Schedule_PDF")

    question_set = parse_ncea_pdf(exam_path)
    answers = parse_mark_schedule(schedule_path)

    for q in question_set.question_list:
        key = (q.question_no, q.question_sub_let)
        if key in answers:
            q.correct_answer = answers[key]

    page.title = f"Quiz: {question_set.question_set_name}"

    current_index = 0
    score = 0

    question_text = ft.Text("", size=20, weight="bold")
    answer_field = ft.TextField(label="Your Answer", multiline=True)
    feedback_text = ft.Text("", size=16)

    time_left = 900
    timer_text = ft.Text(f"Time: {time_left}", size=18)

    def load_question():
        nonlocal current_index
        if current_index < len(question_set.question_list):
            q = question_set.question_list[current_index]
            question_text.value = f"{q.question_no}{q.question_sub_let}. {q.question_text}"
            feedback_text.value = ""
            answer_field.value = ""
        else:
            finish_quiz()
        page.update()

    def finish_quiz():
        dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Quiz Complete"),
            content=ft.Text(
                f"Your score: {score}/{len(question_set.question_list)}"
            ),
            actions=[ft.FilledButton("OK", on_click=lambda e: page.pop_dialog())],
        )
        page.show_dialog(dialog)

    def submit_answer(e):
        nonlocal current_index, score
        if current_index < len(question_set.question_list):
            q = question_set.question_list[current_index]
            user_ans = answer_field.value
            if is_equivalent(user_ans, q.correct_answer):
                score += 1
                feedback_text.value = "Correct!"
            else:
                if q.correct_answer is not None:
                    feedback_text.value = f"Incorrect. Correct answer: {q.correct_answer}"
                else:
                    feedback_text.value = "No official answer available."
            current_index += 1
            load_question()
        page.update()

    def tick_timer():
        nonlocal time_left
        time_left -= 1
        if time_left <= 0:
            time_left = 0
            timer_text.value = f"Time: {time_left}"
            page.update()
            finish_quiz()
        else:
            timer_text.value = f"Time: {time_left}"
            page.update()

    page.run_interval(tick_timer, 1000)

    submit_button = ft.FilledButton("Submit", on_click=submit_answer)

    load_question()

    quiz_column = ft.Column(
        controls=[
            timer_text,
            question_text,
            answer_field,
            submit_button,
            feedback_text,
        ]
    )

    return ft.View(
        route="/quiz",
        controls=[
            ft.Container(
                alignment=ft.Alignment.TOP_CENTER,
                content=quiz_column,
                expand=True,
            )
        ],
    )


def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.MainAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 10

    def logout(e):
        def user_confirm_logout(e):
            page.pop_dialog()
            page.session.store.clear()
            page.navigate("/login")

        yes_button = ft.FilledButton("Yes", on_click=user_confirm_logout)
        no_button = ft.FilledButton("No", on_click=lambda e: page.pop_dialog())

        user_confirm_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Logout"),
            content=ft.Text("Are you sure you wish to logout?"),
            actions=[yes_button, no_button],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.show_dialog(user_confirm_dialog)

    logout_button = ft.FilledButton(content=ft.Text("Logout"), on_click=logout)

    logout_container = ft.Container(
        content=logout_button, alignment=ft.Alignment.TOP_RIGHT
    )

    def home_route_change(e):
        if e.control.selected_index == 0:
            page.navigate("/home")
        elif e.control.selected_index == 1:
            page.navigate("/settings")

    navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=home_route_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_ROUNDED, label="Home"),
            ft.NavigationBarDestination(
                icon=ft.Icons.ACCOUNT_CIRCLE_ROUNDED, label="", tooltip="Settings"
            ),
        ],
    )

    page.session.store.set("User_ID", "")

    def on_route_change(e=None):
        page.views.clear()

        template_route = ft.TemplateRoute(page.route)

        if template_route.match("/home") and page.session.store.get("User_ID") != "":
            page.views.append(home_page(page))
            page.navigation_bar = navigation_bar
            navigation_bar.destinations[1].label = (
                f"{page.session.store.get('User_ID')}"
            )
        elif page.route == "/login":
            page.views.append(login_page(page))
        elif page.route == "/settings" and page.session.store.get("User_ID") != "":
            page.views.append(settings_page(page))
            page.add(logout_container)
            page.navigation_bar = navigation_bar
            navigation_bar.destinations[1].label = (
                f"{page.session.store.get('User_ID')}"
            )
        elif page.route == "/quiz" and page.session.store.get("User_ID") != "":
            page.views.append(quiz_page(page))
            page.navigation_bar = navigation_bar
            navigation_bar.destinations[1].label = (
                f"{page.session.store.get('User_ID')}"
            )

        page.update()

    page.on_route_change = on_route_change
    on_route_change()
    page.navigate("/login")


if __name__ == "__main__":
    ft.run(main)
