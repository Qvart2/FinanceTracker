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
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=48,
                spacing=10,
                padding=[6, 6]
            )

            # Лейбл категории
            lbl = Label(
                text=cat,
                halign="left",
                valign="middle",
                size_hint_x=1,
                color=(0, 0, 0, 1),
                font_size=16
            )
            lbl.bind(
                size=lambda instance, value: setattr(instance, "text_size", (instance.width, None))
            )

            btn = Button(
                text="X",
                size_hint=(None, None),
                size=(36, 36),
                font_size=18,
                background_normal="",
                background_color=(0.85, 0.2, 0.2, 1),
                color=(1, 1, 1, 1)
            )
            btn.bind(on_release=lambda widget, c=cat: self.remove_category(c))

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
# KV-разметка
# ---------------------------
kv = """
#:import rgba kivy.utils.get_color_from_hex

<StyledButton@Button>:
    size_hint_y: None
    height: 45
    background_normal: ""
    background_color: rgba("#4d6fa3")
    color: 1, 1, 1, 1
    font_size: 16
    bold: True

<StyledLabel@Label>:
    font_size: 20
    color: 0, 0, 0, 1

<TextInput>:
    background_color: 1, 1, 1, 1
    foreground_color: 0, 0, 0, 1
    padding: [10, 10]
    font_size: 16

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
        spacing: 15
        padding: 30
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Финансовый менеджер"
            font_size: 28
            bold: True

        StyledButton:
            text: "Кошельки"
            on_release: app.root.current = "wallets"

        StyledButton:
            text: "Доходы и расходы"
            on_release: app.root.current = "expenses"

        StyledButton:
            text: "Категории"
            on_release: app.root.current = "categories"

        StyledButton:
            text: "Статистика"
            on_release: app.root.current = "stats"

        StyledButton:
            text: "Выход"
            background_color: rgba("#E74C3C")
            on_release: app.stop()

<WalletScreen>:
    name: "wallets"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Экран кошельков"
            font_size: 22

        StyledButton:
            text: "Назад"
            on_release: app.root.current = "menu"

<ExpenseScreen>:
    name: "expenses"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Добавление доходов и расходов"
            font_size: 22

        TextInput:
            id: sum_input
            hint_text: "Введите сумму"
            input_filter: "float"
            multiline: False
            size_hint_y: None
            height: 45

        StyledButton:
            text: "Добавить доход"
            on_release: root.add_income()

        StyledButton:
            text: "Добавить расход"
            on_release: root.add_expense()

        StyledButton:
            text: "Назад"
            background_color: rgba("#95A5A6")
            on_release: app.root.current = "menu"

<CategoryScreen>:
    name: "categories"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Категории расходов"
            font_size: 22

        TextInput:
            id: category_input
            hint_text: "Введите название категории"
            size_hint_y: None
            height: 45

        StyledButton:
            text: "Добавить категорию"
            on_release:
                root.add_category(category_input.text)
                category_input.text = ""

        StyledLabel:
            text: "Список категорий:"
            font_size: 18

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

        StyledButton:
            text: "Назад"
            background_color: rgba("#95A5A6")
            on_release: app.root.current = "menu"

<StatsScreen>:
    name: "stats"
    BoxLayout:
        orientation: "vertical"
        spacing: 10
        padding: 20
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Экран статистики"
            font_size: 22

        StyledButton:
            text: "Назад"
            background_color: rgba("#95A5A6")
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
