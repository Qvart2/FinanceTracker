import json
import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup

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


# Глобальные данные, загружаем один раз при старте
data = load_data()


# ---------------------------
# Доп. функции для кошельков (из main1.py)
# ---------------------------
def add_wallet(name, currency, balance):
    """Добавляет новый кошелёк в данные и сохраняет их."""
    global data
    wallet = {"name": name, "currency": currency, "balance": balance}
    data.setdefault("wallets", []).append(wallet)
    save_data(data)


def delete_wallet(name):
    """Удаляет кошелёк по имени."""
    global data
    data["wallets"] = [wallet for wallet in data.get("wallets", []) if wallet["name"] != name]
    save_data(data)


def calculate_total_balance():
    """Подсчитывает итоговый баланс по всем кошелькам."""
    total_balance = {}
    for wallet in data.get("wallets", []):
        currency = wallet.get("currency")
        balance = wallet.get("balance", 0)
        try:
            balance = float(balance)
        except (TypeError, ValueError):
            balance = 0
        total_balance[currency] = total_balance.get(currency, 0) + balance
    return total_balance


# ---------------------------
# Экраны приложения
# ---------------------------
class MainMenu(Screen):
    pass


class WalletScreen(Screen):
    def on_pre_enter(self):
        """Обновляет список кошельков при открытии экрана."""
        self.update_wallet_list()

    def update_wallet_list(self):
        """Обновляет список кошельков на экране."""
        container = self.ids.wallet_list
        container.clear_widgets()

        if not data.get("wallets"):
            container.add_widget(Label(text="Список кошельков пуст.", font_size="16sp", color=(0, 0, 0, 1)))
        else:
            for wallet in data["wallets"]:
                wallet_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=10, padding=[6, 6])
                wallet_label = Label(
                    text=f"Имя: {wallet['name']}, Баланс: {wallet['balance']} {wallet['currency']}",
                    size_hint_x=0.8,
                    halign="left",
                    valign="middle",
                    color=(0, 0, 0, 1)  # ← добавлен чёрный цвет текста
                )
                wallet_label.bind(size=lambda lbl, _: setattr(lbl, "text_size", (lbl.width, None)))
                delete_button = Button(
                    text="Удалить",
                    size_hint_x=0.2,
                    background_normal="",
                    background_color=(0.8, 0.2, 0.2, 1),
                    color=(1, 1, 1, 1),
                    on_release=lambda btn, name=wallet["name"]: self.confirm_delete_wallet(name)
                )
                wallet_layout.add_widget(wallet_label)
                wallet_layout.add_widget(delete_button)
                container.add_widget(wallet_layout)


    def show_add_wallet_form(self, *args):
        """Показывает форму для добавления кошелька."""
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        self.wallet_name_input = TextInput(hint_text="Имя кошелька", multiline=False)
        self.wallet_currency_input = TextInput(hint_text="Валюта", multiline=False)
        self.wallet_balance_input = TextInput(hint_text="Баланс", multiline=False, input_filter="float")

        box.add_widget(self.wallet_name_input)
        box.add_widget(self.wallet_currency_input)
        box.add_widget(self.wallet_balance_input)

        save_button = Button(text="Сохранить", size_hint_y=None, height=44)
        save_button.bind(on_release=self.save_wallet)
        box.add_widget(save_button)

        self.add_wallet_popup = Popup(title="Добавить кошелёк", content=box, size_hint=(0.9, 0.6))
        self.add_wallet_popup.open()

    def save_wallet(self, instance):
        """Сохраняет новый кошелёк и обновляет список."""
        name = (self.wallet_name_input.text or "").strip()
        currency = (self.wallet_currency_input.text or "").strip()
        balance_text = (self.wallet_balance_input.text or "0").strip()
        if not name or not currency:
            error_popup = Popup(title="Ошибка", content=Label(text="Введите имя и валюту!"), size_hint=(0.6, 0.3))
            error_popup.open()
            return
        try:
            balance = float(balance_text)
            add_wallet(name, currency, balance)
            self.update_wallet_list()
            self.add_wallet_popup.dismiss()
        except ValueError:
            error_popup = Popup(title="Ошибка", content=Label(text="Неверный формат баланса!"), size_hint=(0.6, 0.3))
            error_popup.open()

    def confirm_delete_wallet(self, name):
        """Показывает диалог подтверждения удаления кошелька."""
        self.delete_name = name
        box = BoxLayout(orientation="vertical", padding=10, spacing=10)
        box.add_widget(Label(text=f"Удалить кошелёк '{name}'?"))
        btn_layout = BoxLayout(size_hint_y=None, height=48, spacing=10)
        yes = Button(text="Да")
        no = Button(text="Нет")
        yes.bind(on_release=self.delete_wallet_confirmed)
        no.bind(on_release=self.delete_wallet_canceled)
        btn_layout.add_widget(yes)
        btn_layout.add_widget(no)
        box.add_widget(btn_layout)
        self.delete_popup = Popup(title="Подтверждение", content=box, size_hint=(0.6, 0.4))
        self.delete_popup.open()

    def delete_wallet_confirmed(self, instance):
        """Удаляет кошелёк после подтверждения."""
        delete_wallet(self.delete_name)
        self.update_wallet_list()
        self.delete_popup.dismiss()

    def delete_wallet_canceled(self, instance):
        """Отменяет удаление кошелька."""
        self.delete_popup.dismiss()

    def show_total_balance(self):
        """Показывает итоговый баланс по всем кошелькам."""
        total_balance = calculate_total_balance()

        if not total_balance:
            total_balance_text = "Нет кошельков для подсчёта баланса."
        else:
            total_balance_text = "Итоговый баланс:\n"
            for currency, balance in total_balance.items():
                total_balance_text += f"{balance} {currency}\n"

        popup = Popup(title="Итоговый баланс", content=Label(text=total_balance_text), size_hint=(0.7, 0.5))
        popup.open()


class ExpenseScreen(Screen):
    """
    Экран добаления доходов и расходов
    """
    def add_income(self):
        """Добавление дохода"""
        try:
            val = float(self.ids.sum_input.text)
        except (ValueError, TypeError):
            return
        data.setdefault("incomes", []).append({"amount": val})
        save_data(data)

    def add_expense(self):
        """Добавление расхода"""
        try:
            val = float(self.ids.sum_input.text)
        except (ValueError, TypeError):
            return
        data.setdefault("expenses", []).append({"amount": val})
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
# KV-разметка (из main.py, с добавленным WalletScreen контентом)
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

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True

            BoxLayout:
                id: wallet_list
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: 5
                padding: 5

        BoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: 50
            spacing: 10

            StyledButton:
                text: "Добавить кошелёк"
                on_release: root.show_add_wallet_form()

            StyledButton:
                text: "Итоговый баланс"
                on_release: root.show_total_balance()

        StyledButton:
            text: "Назад"
            background_color: rgba("#95A5A6")
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
