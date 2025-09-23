import json
import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button


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
    """
    Экран добаления доходов и расходов
    """
    def add_income(self):
        """Добавление дохода"""
        val = float(self.ids.sum_input.text)
        data.setdefault("incomes").append({"amount": val})
        save_data(data)

    def add_expense(self):
        """Добавление расхода"""
        val = float(self.ids.sum_input.text)
        data.setdefault("expenses").append({"amount": val})
        save_data(data)

    def list_actions(self):
        """"Получение списка доходов и расходов"""
        pass

    def remove_record(self):
        """"Удаление записи"""
        pass

class CategoryScreen(Screen):
    def on_pre_enter(self):
        self.update_category_list()

    def add_category(self, name):
        name = (name or "").strip()
        if not name:
            return
        if name not in data["categories"]:
            data["categories"].append(name)
            save_data(data)
            self.update_category_list()

    def remove_category(self, name):
        if name in data["categories"]:
            data["categories"].remove(name)
            save_data(data)
            self.update_category_list()

    def update_category_list(self):
        container = self.ids.category_list
        container.clear_widgets()
        for cat in data["categories"]:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=10)

            lbl = Label(text=cat, halign="left", valign="middle")
            lbl.bind(size=lbl.setter("text_size"))  # перенос текста если длинный

            btn = Button(
                text="X",
                size_hint=(None, None),
                size=(40, 40),
                background_color=(1, 0, 0, 1),
                color=(1, 1, 1, 1),
                on_release=lambda x, c=cat: self.remove_category(c)
            )

            row.add_widget(lbl)
            row.add_widget(btn)
            container.add_widget(row)



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
            text: "Добавление доходов и расходов"
            font_size: "18sp"

        TextInput:
            id: sum_input
            hint_text: "Введите доход или расход"

            input_filter: "float"
            multiline: False
            size_hint_y: None
            height: "40dp"

        BoxLayout:
            size_hint_y: None

            height: "120dp"
            orientation: "vertical"
            spacing: 8

            Button:
                text: "Добавить доходы"
                on_release: root.add_income()

            Button:
                text: "Добавить расходы"
                on_release: root.add_expense()

            Button:
                text: "Назад"
                size_hint: None, None
                size: 200, 50
                pos_hint: {"center_x": 0.5}
                on_release: app.root.current = "menu"
        AnchorLayout

<CategoryScreen>:
    name: "categories"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20

        Label:
            text: "Категории расходов"
            font_size: "20sp"

        TextInput:
            id: category_input
            hint_text: "Введите название категории"
            size_hint_y: None
            height: 40

        Button:
            text: "Добавить категорию"
            size_hint_y: None
            height: 40
            on_release:
                root.add_category(category_input.text)
                category_input.text = ""

        Label:
            text: "Список категорий:"
            font_size: "16sp"

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True

            BoxLayout:
                id: category_list
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: 5
                padding: 5

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
