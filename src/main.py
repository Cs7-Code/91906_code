import os

import flet as ft
from flet.controls.material import navigation_bar
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine, select


class User(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    #name: dict[str, str] = Field(sa_column=Column(JSON))
    user_id: int = Field(ge=1000, le=9999, unique=True, nullable=False)
    user_pass: str = Field(nullable=False)

    @classmethod
    def create_user(
        cls, engine, user_id_ent, user_pass_ent
    ) -> bool:
        with Session(engine) as session:
            new_user = cls(
                user_id=user_id_ent, user_pass=user_pass_ent
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
            statement = select(User).where(User.user_id == user_id)
            user = session.exec(statement).first()

            match value_to_change:
                case "User Name" if type(new_value) is str:
                    user.name = new_value
                case "ID" if type(new_value) is int:
                    user.user_id = new_value
                case "Password" if type(new_value) is dict(str, str):
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

    """page.padding = 10

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.CrossAxisAlignment.CENTER"""

    welcome_message = ft.Text(
        "Welcome, test!", theme_style=ft.TextThemeStyle.DISPLAY_SMALL
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

    user_name_field = ft.Row([user_id_icon, user_id_text_field], tight=True, tooltip="User ID")

    # Password fields

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40)

    user_password_text_field = ft.TextField(
        label="Password/Pin", password=True, can_reveal_password=True
    )

    user_password_field = ft.Row(
        [user_password_icon, user_password_text_field], tight=True, tooltip="Password/Pin"
    )

    # Login button

    def login_on_click(e):
        try:
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
                actions=[ft.TextButton("Dismiss", on_click=close_dialog)],
            )

            page.show_dialog(input_fail_dialog)
            return False

        engine = User.db_config()

        user_password_ent = user_password_text_field.value
            
        login_success = User.login(engine, user_id_ent, user_password_ent)

        if login_success:
            #current_user_id = int(user_id_text_field.value)
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
                actions=[ft.TextButton("Dismiss", on_click=close_dialog)],
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

        create_user_name_field = ft.Row([user_id_icon, create_user_id_text_field], tight=True, tooltip="User ID")

        # Password fields
        create_user_password_text_field = ft.TextField(
        label="Password/Pin", password=True, can_reveal_password=True
        )

        user_password_field = ft.Row(
        [user_password_icon, create_user_password_text_field], tight=True, tooltip="Password/Pin"
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
                    actions=[ft.TextButton("Dismiss", on_click=close_dialog)],
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
                    actions=[ft.TextButton("Dismiss", on_click=close_dialog)],
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
            actions=[ft.TextButton("Create User", on_click=create_user_verify)],
        )

        page.show_dialog(create_user_dialog)
        return False
        

    create_user_button = ft.FilledButton(content=ft.Text("Create User"), on_click=on_create_user_button_click)

    actions_row = ft.Row(
        [login_button, create_user_button], tight=True
    )

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
        horizontal_alignment = ft.CrossAxisAlignment.CENTER,
        vertical_alignment = ft.CrossAxisAlignment.CENTER,
        controls=[login_card],
    )


def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK

    page.horizontal_alignment = ft.MainAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    

    #global current_user_id

    #current_user_id = None

    def on_route_change(e=None):
        page.views.clear()

        if page.route == "/home":
            page.views.append(home_page(page))

            page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_ROUNDED, label="Home"),
                ft.NavigationBarDestination(icon=ft.Icons.ACCOUNT_CIRCLE_ROUNDED, label="Test User")
        
            ], 
            ) 
        else:
            page.views.append(login_page(page))
            
            

        page.update()

    page.on_route_change = on_route_change

    on_route_change()


if __name__ == "__main__":
    ft.run(main)
