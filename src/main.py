from typing import Sequence
import flet as ft
from faker import Faker
from sqlmodel import Field, SQLModel, create_engine


class User(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    name: dict[str]
    password: str
    
def db():
    db_file_name = "users.db"
    
    engine = create_engine(f"sqlite://{db_file_name}")
    SQLModel.metadate.create_all(engine)

    def login(User):
        pass
    
    


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

    user_name_text_field = ft.TextField(label="User ID", max_length=5, counter="")

    user_name_field = ft.Row([user_name_icon, user_name_text_field], tight=True)

    #Password fields

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40)

    user_name_text_field = ft.TextField(label="Password/Pin", password=True, can_reveal_password=True)

    user_password_field = ft.Row([user_password_icon, user_name_text_field], tight=True)

    #Login button

    def test(e): print("test")

    login_button = ft.FilledButton(content=ft.Text("Login"), on_click=test)

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
