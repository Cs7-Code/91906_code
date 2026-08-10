import os

import flet as ft
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine, select


class User(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    #name: dict[str, str] = Field(sa_column=Column(JSON))
    user_id: int = Field(ge=1000, le=9999, unique=True, nullable=False)
    user_pass: str = Field(nullable=False)

    @classmethod
    def create_user(
        cls, engine, user_name_ent, user_id_ent, user_pass_ent
    ) -> str | None:
        with Session(engine) as session:
            new_user = cls(
                name=user_name_ent, user_id=user_id_ent, user_pass=user_pass_ent
            )

            try:
                session.add(new_user)
                session.commit()
                return None
            except IntegrityError:
                session.rollback()
                return "User creation failed (User ID not unique)"
            except Exception:
                session.rollback()
                return f"An error occured (Error Details: {Exception})"

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

            print(engine, user_id_ent, user_pass_ent)

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
        


"""def home_page(page: ft.Page):
    def home_view():
        page.clean()
        page.update()
        temp_user = Faker().last_name()

        welcome_message = ft.Text(f"Welcome, {temp_user}!", theme_style=ft.TextThemeStyle.DISPLAY_SMALL)

        page.add(ft.Container(alignment=ft.Alignment.TOP_CENTER, content=welcome_message, expand=True))
    
    def settings_view():
        page.clean()
        page.update()
        page.add(ft.Text("This is settings"))


    def handle_change(e):
        if e.control.selected_index == 0:
            home_view()
        if e.control.selected_index == 1:
            settings_view()


    page.title = "Home"

    page.padding = 10

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.CrossAxisAlignment.CENTER

    page.navigation_bar= ft.NavigationBar(
        selected_index=0,
        on_change=handle_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME_ROUNDED, label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.ACCOUNT_CIRCLE_ROUNDED, label="Test User")
            
        ]
    )

    temp_user = Faker().last_name()

    welcome_message = ft.Text(f"Welcome, {temp_user}!", theme_style=ft.TextThemeStyle.DISPLAY_SMALL)

    page.add(ft.Container(alignment=ft.Alignment.TOP_CENTER, content=welcome_message, expand=True))"""


def main(page: ft.Page):
    #Configuring Page 
    page.title = "Login"

    page.theme_mode = ft.ThemeMode.LIGHT

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.CrossAxisAlignment.CENTER

    page.bgcolor = ft.Colors.TRANSPARENT

    page.decoration = ft.BoxDecoration(image=ft.DecorationImage(src="Login_page_background.jpg", fit=ft.BoxFit.FILL))

    
    #Page Title

    login_title = ft.Text("Login", theme_style=ft.TextThemeStyle.DISPLAY_SMALL)

    #User ID Fields 

    user_name_icon = ft.Icon(ft.Icons.ACCOUNT_CIRCLE_ROUNDED, color=ft.Colors.PRIMARY, size=40)

    user_id_text_field = ft.TextField(label="User ID", max_length=5, counter="")

    user_name_field = ft.Row([user_name_icon, user_id_text_field], tight=True)

    #Password fields

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40)

    user_password_text_field = ft.TextField(label="Password/Pin", password=True, can_reveal_password=True)

    user_password_field = ft.Row([user_password_icon, user_password_text_field], tight=True)

    #Login button

    def login_on_click(): 
        engine = User.db_config()

        login_success = User.login(engine, int(user_id_text_field.value), str(user_password_text_field.value))

        print(login_success)

    login_button = ft.FilledButton(content=ft.Text("Login"), on_click=login_on_click)


    #Login fields 

    login_fields = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                             controls=[login_title, user_name_field, user_password_field, login_button])

    

    page.add(ft.Card(shadow_color=ft.Colors.ON_SURFACE_VARIANT, 
                     content=ft.Container(padding=10, content=login_fields),
                     opacity=0.65
                    )
            )


if __name__ == "__main__":
    ft.run(main)
    
