import flet as ft
import sqlite3 as sql

def login(user_id, user_password):
    conn = sql.connect("user.db")

    curs = conn.cusor()




def main(page: ft.Page):
    #Configuring Page 
    page.title = "Login"

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.CrossAxisAlignment.CENTER

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

    #Login fields 

    login_fields = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                             controls=[login_title, user_name_field, user_password_field])

    

    page.add(ft.Card(shadow_color=ft.Colors.ON_SURFACE_VARIANT, 
                     content=ft.Container(padding=10, content=login_fields)
                    )
            )

    #Login button

    page.add(ft.FilledButton("Login"))

if __name__ == "__main__":
    ft.run(main)
