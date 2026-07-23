from ctypes import alignment
import flet as ft
import sqlite3 as sql

def login(user_id, user_password):
    pass

def home_page(page:ft.Page):
    page.title = "Home"

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.CrossAxisAlignment.CENTER


    nav_bar = ft.NavigationRail(selected_index=0, destinations=[
        ft.NavigationRailDestination(icon=ft.Icons.STAR, label="Star"),
        ft.NavigationRailDestination(icon=ft.Icon(ft.Icons.ADD),label="Add"),
        ft.NavigationRailDestination(icon=ft.Icons.DELETE, label=ft.Text("Delete"))])

    page.add(ft.Column(alignment=ft.MainAxisAlignment.START, expand=True, controls=nav_bar))



"""def main(page: ft.Page):
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

    login_button = ft.FilledButton("Login")

    #Login fields 

    login_fields = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                             controls=[login_title, user_name_field, user_password_field, login_button])

    

    page.add(ft.Card(shadow_color=ft.Colors.ON_SURFACE_VARIANT, 
                     content=ft.Container(padding=10, content=login_fields),
                     opacity=0.65
                    )
            )"""

    

if __name__ == "__main__":
    ft.run(home_page)
