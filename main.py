import json
import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen


# ---------------------------
# Работа с JSON (хранение данных)
# ---------------------------
DATA_FILE = "data.json"


def load_data():
    """Загрузка данных из файла JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "wallets": [],
            "incomes": [],
            "expenses": [],
            "categories": []
        }


def save_data(data):
    """Сохранение данных в файл JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


data = load_data()


# ---------------------------
# Экраны приложения
# ---------------------------
class MainMenu(Screen):
    pass


class WalletScreen(Screen):
    pass


class ExpenseScreen(Screen):
    pass


class CategoryScreen(Screen):
    pass


class StatsScreen(Screen):
    pass


# ---------------------------
# ScreenManager
# ---------------------------
class FinanceManager(ScreenManager):
    pass


# ---------------------------
# KV-разметка (основной UI)
# ---------------------------
kv = """
FinanceManager:
    MainMenu:
    WalletScreen:
    ExpenseScreen:
    CategoryScreen:
    StatsScreen:

<MainMenu>:
    name: "menu"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20

        Label:
            text: "Финансовый менеджер"
            font_size: "24sp"

        Button:
            text: "Кошельки"
            on_release: app.root.current = "wallets"

        Button:
            text: "Доходы и расходы"
            on_release: app.root.current = "expenses"

        Button:
            text: "Категории"
            on_release: app.root.current = "categories"

        Button:
            text: "Статистика"
            on_release: app.root.current = "stats"

        Button:
            text: "Выход"
            on_release: app.stop()

<WalletScreen>:
    name: "wallets"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20

        Label:
            text: "Экран кошельков (тут будет список и добавление)"
            font_size: "18sp"

        Button:
            text: "Назад"
            size_hint: None, None
            size: 200, 50
            pos_hint: {"center_x": 0.5}
            on_release: app.root.current = "menu"

<ExpenseScreen>:
    name: "expenses"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20

        Label:
            text: "Экран доходов/расходов"
            font_size: "18sp"

        Button:
            text: "Назад"
            size_hint: None, None
            size: 200, 50
            pos_hint: {"center_x": 0.5}
            on_release: app.root.current = "menu"

<CategoryScreen>:
    name: "categories"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20

        Label:
            text: "Экран категорий"
            font_size: "18sp"

        Button:
            text: "Назад"
            size_hint: None, None
            size: 200, 50
            pos_hint: {"center_x": 0.5}
            on_release: app.root.current = "menu"

<StatsScreen>:
    name: "stats"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20

        Label:
            text: "Экран статистики"
            font_size: "18sp"

        Button:
            text: "Назад"
            size_hint: None, None
            size: 200, 50
            pos_hint: {"center_x": 0.5}
            on_release: app.root.current = "menu"
"""


# ---------------------------
# Основное приложение
# ---------------------------
class FinanceApp(App):
    def build(self):
        return Builder.load_string(kv)


if __name__ == "__main__":
    FinanceApp().run()
