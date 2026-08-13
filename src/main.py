import os

import flet as ft
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine, select
\e

class User(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    # name: dict[str, str] = Field(sa_column=Column(JSON))
    user_id: int = Field(ge=1000, le=9999, unique=True, nullable=False)
    user_pass: str = Field(nullable=False)

    @classmethod
    def create_user(cls, engine, user_id_ent, user_pass_ent) -> bool:
        with Session(engine) as session:
            new_user = cls(user_id=user_id_ent, user_pass=user_pass_ent)

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
                # case "User Name" if type(new_value) is str:
                #     user.name = new_value
                case "ID" if type(new_value) is int:
                    user.user_id = new_value
                case "Password" if type(new_value) is str:
                    user = session.exec(statement).first()
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


def home_page(page: ft.Page) -> ft.View:
    page.title = "Home"

    current_user_id = page.session.store.get("User_ID")

    welcome_message = ft.Text(
        f"Welcome, {current_user_id}!", theme_style=ft.TextThemeStyle.DISPLAY_SMALL
    )

    return ft.View(
        route="/home",
        controls=[
            ft.Container(
                alignment=ft.Alignment.TOP_CENTER, content=welcome_message, expand=True
            )
        ],
    )


def login_page(page: ft.Page) -> ft.View:
    # Page Title

    page.title = "Login"

    login_title = ft.Text("Login", theme_style=ft.TextThemeStyle.DISPLAY_SMALL)

    # User ID Fields

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

    # Password fields

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40)

    user_password_text_field = ft.TextField(
        label="Password/Pin", password=True, can_reveal_password=True
    )

    user_password_field = ft.Row(
        [user_password_icon, user_password_text_field],
        tight=True,
        tooltip="Password/Pin",
    )

    # Login button

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

        # User ID Fields
        create_user_id_text_field = ft.TextField(
            label="User ID",
            max_length=5,
            counter="",
            input_filter=ft.NumbersOnlyInputFilter(),
        )

        create_user_name_field = ft.Row(
            [user_id_icon, create_user_id_text_field], tight=True, tooltip="User ID"
        )

        # Password fields
        create_user_password_text_field = ft.TextField(
            label="Password/Pin", password=True, can_reveal_password=True
        )

        user_password_field = ft.Row(
            [user_password_icon, create_user_password_text_field],
            tight=True,
            tooltip="Password/Pin",
        )

        create_user_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[create_user_name_field, user_password_field],
        )

        create_user_fields = ft.Container(content=create_user_column, padding=10)

        def on_close(engine, user_id, user_pass):
            is_user_creation_success = User.create_user(engine, user_id, user_pass)

            def close_dialog(e):
                page.pop_dialog()

            if is_user_creation_success != True:
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

        def create_user_verify(e):
            try:
                create_user_id_ent = int(create_user_id_text_field.value)

                if create_user_password_text_field.value == "":
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

            on_close(engine, create_user_id_ent, create_user_password_text_field_ent)

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

    # Login fields

    login_fields = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[login_title, user_name_field, user_password_field, actions_row],
    )

    login_card = ft.Card(
        shadow_color=ft.Colors.ON_SURFACE_VARIANT,
        content=ft.Container(padding=10, content=login_fields),
        opacity=0.65,
    )

    return ft.View(
        route="/login",
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
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

    # Password fields

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.SECONDARY, size=40)

    def password_change(e):
        def close_dialog(e):
            page.pop_dialog()

        user_password_icon = ft.Icon(
            ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40
        )

        # Current Password Field
        current_password_text_field = ft.TextField(
            label="Current Password/Pin", password=True, can_reveal_password=True
        )

        current_password_field = ft.Row(
            [user_password_icon, current_password_text_field],
            tight=True,
            tooltip="Current Password/Pin",
        )

        # Password fields
        new_password_text_field = ft.TextField(
            label="Password/Pin", password=True, can_reveal_password=True
        )

        new_password_field = ft.Row(
            [user_password_icon, new_password_text_field],
            tight=True,
            tooltip="Password/Pin",
        )

        new_password_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[current_password_field, new_password_field],
        )

        new_password_fields = ft.Container(content=new_password_column, padding=10)

        def close_change_dialog(e):
            page.pop_dialog()

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
                if current_password_text_field.value == "" or new_password_field == "":
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

        if user_pass_textfield.password == True:
            user_reveal_pass.icon = ft.Icons.VISIBILITY_OFF_ROUNDED

            user_password_icon = ft.Icon(
                ft.Icons.PASSWORD, color=ft.Colors.SECONDARY, size=40
            )

            password_text_field = ft.TextField(
                label="Password/Pin", password=True, can_reveal_password=True
            )

            password_field = ft.Row(
                [user_password_icon, password_text_field],
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
            ft.NavigationBarDestination(icon=ft.Icons.ACCOUNT_CIRCLE_ROUNDED, label=""),
        ],
    )

    page.session.store.set("User_ID", "")

    def on_route_change(e=None):
        page.views.clear()

        template_route = ft.TemplateRoute(page.route)

        if template_route.match("/home") and page.session.store.get("User_ID") != "":
            page.views.append(home_page(page))
            page.navigation_bar = navigation_bar
            navigation_bar.destinations[
                1
            ].label = f"{page.session.store.get('User_ID')}"
        elif page.route == "/login":
            page.views.append(login_page(page))
        elif page.route == "/settings" and page.session.store.get("User_ID") != "":
            page.views.append(settings_page(page))
            page.add(logout_container)
            page.navigation_bar = navigation_bar
            navigation_bar.destinations[
                1
            ].label = f"{page.session.store.get('User_ID')}"

        page.update()

    page.on_route_change = on_route_change

    on_route_change()

    page.navigate("/login")


if __name__ == "__main__":
    ft.run(main)
