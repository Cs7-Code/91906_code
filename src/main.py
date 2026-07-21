import flet as ft


def main(page: ft.Page):
    page.title = "Login"

    page.add(ft.Text("Login"))

    user_name_icon = ft.Icon(ft.Icons.ACCOUNT_CIRCLE_ROUNDED, color=ft.Colors.PRIMARY, size=40)

    user_name_text_field = ft.TextField(label="User ID")

    user_name_field = ft.Row([user_name_icon, user_name_text_field])

    page.add(user_name_field)

    user_password_icon = ft.Icon(ft.Icons.PASSWORD, color=ft.Colors.PRIMARY, size=40)

    user_name_text_field = ft.TextField(label="User ID")

    user_password_field = ft.Row([user_password_icon, user_name_text_field])

    page.add(user_password_field)
    

    page.add(ft.FilledButton("Login"))

if __name__ == "__main__":
    ft.run(main)
