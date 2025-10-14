import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
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

from datetime import datetime

def update_exchange_rates():
    """Загружает курсы валют с сайта ЦБ РФ и сохраняет их в data."""
    global data
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        xml_data = ET.fromstring(response.text)

        rates = {"RUB": 1.0}
        for valute in xml_data.findall("Valute"):
            code = valute.find("CharCode").text
            rate = float(valute.find("Value").text.replace(",", "."))
            nominal = int(valute.find("Nominal").text)
            rates[code] = rate / nominal

        data["currencies"] = rates
        data["last_rates_update"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_data(data)
        return True
    except Exception as e:
        print("Ошибка при обновлении курсов:", e)
        return False

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
        """Обновляет список кошельков и дату курсов при открытии экрана."""
        self.update_wallet_list()
        # 🟩 добавь вот эту строку:
        self.ids.last_update_label.text = f"Курсы обновлены: {data.get('last_rates_update', 'неизвестно')}"


    def update_rates(self):
        """Обновляет курсы валют с сайта ЦБ РФ."""
        if update_exchange_rates():
            popup = Popup(title="Успешно", content=Label(text="Курсы валют обновлены!"), size_hint=(0.6, 0.3))
            popup.open()
        else:
            popup = Popup(title="Ошибка", content=Label(text="Не удалось обновить курсы."), size_hint=(0.6, 0.3))
            popup.open()

        self.ids.last_update_label.text = f"Курсы обновлены: {data.get('last_rates_update', 'неизвестно')}"

    def update_wallet_list(self):
        """Обновляет список кошельков на экране."""
        container = self.ids.wallet_list
        container.clear_widgets()

        if not data.get("wallets"):
            container.add_widget(Label(text="Список кошельков пуст.", font_size="16sp", color=(0, 0, 0, 1)))
        else:
            for wallet in data["wallets"]:
                # Пропускаем некорректные записи
                if not all(k in wallet for k in ("name", "currency", "balance")):
                    continue

                # Вычисляем курс и рублёвое значение
                rate = data.get("currencies", {}).get(wallet["currency"], 1)
                try:
                    rub_value = float(wallet["balance"]) * rate
                except (TypeError, ValueError):
                    rub_value = 0.0

                # Формируем строку текста
                text = f"Имя: {wallet['name']}, Баланс: {wallet['balance']} {wallet['currency']} (≈ {rub_value:.2f} RUB)"

                # Элементы интерфейса
                wallet_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=10, padding=[6, 6])
                wallet_label = Label(
                    text=text,
                    size_hint_x=0.8,
                    halign="left",
                    valign="middle",
                    color=(0, 0, 0, 1)
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
        from kivy.uix.spinner import Spinner

        # Список валют: отображаем красиво, сохраняем код
        self.CURRENCY_LABELS = {
            "RUB": "Рубль (RUB)",
            "USD": "Доллар (USD)",
            "EUR": "Евро (EUR)"
        }

        box = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # Поле для имени кошелька
        self.wallet_name_input = TextInput(hint_text="Имя кошелька", multiline=False)
        box.add_widget(self.wallet_name_input)

        # Выпадающий список валют
        self.wallet_currency_spinner = Spinner(
            text="Выберите валюту",
            values=list(self.CURRENCY_LABELS.values()),
            size_hint_y=None,
            height=44
        )
        box.add_widget(self.wallet_currency_spinner)

        # Поле для баланса
        self.wallet_balance_input = TextInput(hint_text="Баланс", multiline=False, input_filter="float")
        box.add_widget(self.wallet_balance_input)

        # Кнопка сохранения
        save_button = Button(text="Сохранить", size_hint_y=None, height=44)
        save_button.bind(on_release=self.save_wallet)
        box.add_widget(save_button)

        # Окно добавления
        self.add_wallet_popup = Popup(title="Добавить кошелёк", content=box, size_hint=(0.9, 0.6))
        self.add_wallet_popup.open()

    def save_wallet(self, instance):
        """Сохраняет новый кошелёк и обновляет список."""
        name = (self.wallet_name_input.text or "").strip()
        balance_text = (self.wallet_balance_input.text or "0").strip()
        selected_label = self.wallet_currency_spinner.text

        # Определяем код валюты из выбранной надписи
        currency = None
        for code, label in self.CURRENCY_LABELS.items():
            if label == selected_label:
                currency = code
                break

        # Проверки
        if not name or not currency:
            error_popup = Popup(title="Ошибка", content=Label(text="Введите имя и выберите валюту!"), size_hint=(0.6, 0.3))
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
    def on_pre_enter(self):
        """Обновляет списки доходов и расходов"""
        self.update_lists()

    def show_add_ExpenseIncome_form(self, *args):
        """Показывает форму для добавления записей"""
        from kivy.uix.spinner import Spinner

        self.CURRENCY_LABELS = {
            "RUB": "Рубль (RUB)",
            "USD": "Доллар (USD)",
            "EUR": "Евро (EUR)"
        }

        box = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # Выпадающий список для выбора действия доход/расход
        self.action_spinner = Spinner(
            text="Выберите действие",
            values=["Добавить расход", "Добавить доход"],
            size_hint_y=None,
            height=44
        )
        box.add_widget(self.action_spinner)

        # Выпадающий список валют
        self.wallet_currency_spinner = Spinner(
            text="Выберите валюту",
            values=list(self.CURRENCY_LABELS.values()),
            size_hint_y=None,
            height=44
        )
        box.add_widget(self.wallet_currency_spinner)

        # Поле ввода суммы
        self.amount_input = TextInput(hint_text="Сумма", multiline=False, input_filter="float")
        box.add_widget(self.amount_input)

        # Кнопка сохранения
        save_button = Button(text="Сохранить", size_hint_y=None, height=44)
        save_button.bind(on_release=self.save_record)
        box.add_widget(save_button)

        # Окно добавления
        self.add_wallet_popup = Popup(title="Добавить запись", content=box, size_hint=(0.9, 0.5))
        self.add_wallet_popup.open()

    def update_lists(self):
        """Обновляем списки"""
        self.populate_record_list(self.ids.income_list, data.get("incomes", []), "incomes")
        self.populate_record_list(self.ids.expense_list, data.get("expenses", []), "expenses")

    def populate_record_list(self, container, records, key):
        """Заполняем контейнер записями"""
        container.clear_widgets()
        if not records:
            container.add_widget(Label(text="Пусто", size_hint_y=None, height=36, color=(0,0,0,1)))
            return

        rates = data.get("currencies", {}) or {}

        for rec in records:
            rid = rec.get("id", "")
            cur = rec.get("currency", "")
            amt = rec.get("amount", "")
            txt = f"id: {rid} | {amt} {cur}"

            try:
                amount = float(amt)
            except (TypeError, ValueError):
                amount = 0.0

            rate = rates.get(cur, 1.0)
            try:
                rub_value = amount * float(rate)
            except Exception:
                rub_value = 0.0

            txt = f"id: {rid} | {amount} {cur} (≈ {rub_value:.2f} RUB)"

            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=44, spacing=8, padding=[6,6])

            lbl = Label(text=txt, size_hint_x=0.78, halign="left", valign="middle", color=(0,0,0,1))
            lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (inst.width, None)))

            btn = Button(text="Удалить", size_hint_x=0.22, background_normal="", background_color=(0.8,0.2,0.2,1), color=(1,1,1,1))
            btn.bind(on_release=lambda b, k=key, r=rid: self.confirm_delete_record(k, r))

            row.add_widget(lbl)
            row.add_widget(btn)
            container.add_widget(row)


    def save_record(self, instance):
        """Сохраняет новую запись"""
        amount_text = (self.amount_input.text or "0").strip()
        selected_label = self.wallet_currency_spinner.text

        # Определяем валюту из выбранной надписи
        currency = next((code for code, label in self.CURRENCY_LABELS.items() if label == selected_label), None)
        if not currency:
            Popup(title="Ошибка", content=Label(text="Выберите валюту!"), size_hint=(0.6, 0.3)).open()
            return

        try:
            amount = float(amount_text)
        except ValueError:
            Popup(title="Ошибка", content=Label(text="Неверный формат суммы!"), size_hint=(0.6, 0.3)).open()
            return

        # Определяем ключ incomes/expenses
        action_text = (self.action_spinner.text or "").lower()
        if "доход" in action_text:
            key = "incomes"
        elif "расход" in action_text:
            key = "expenses"
        else:
            Popup(title="Ошибка", content=Label(text="Выберите действие: доход или расход!"), size_hint=(0.6, 0.3)).open()
            return

        new_id = self.numbering_id(key)
        record = {"id": new_id, "currency": currency, "amount": amount}
        data.setdefault(key, []).append(record)
        save_data(data)

        try:
            if hasattr(self, "add_wallet_popup"):
                self.add_wallet_popup.dismiss()
        except Exception:
            pass
        
        self.update_lists()

    def show_list(self, key):
        """Показывает список записей"""
        container = self.ids.rec_list
        container.clear_widgets()

        records = data.get(key) or []
        if not records:
            container.add_widget(Label(text="Список пустой", size_hint_y=None, height=40, color=(0, 0, 0, 1)))
            return

        rates = data.get("currencies", {}) or {}
        
        for rec in records:
            rid = rec.get("id", "")
            cur = rec.get("currency", "")
            amt = rec.get("amount", "")
            text = f"id: {rid} | {amt} {cur}"

            try:
                amount = float(amt)
            except (TypeError, ValueError):
                amount = 0.0

            rate = rates.get(cur, 1.0)
            try:
                rub_value = amount * float(rate)
            except Exception:
                rub_value = 0.0

            text = f"id: {rid} | {amount} {cur} (≈ {rub_value:.2f} RUB)"

            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=10, padding=[6, 6])
            
            lbl = Label(
                text=text,
                size_hint_x=0.8,
                halign="left",
                valign="middle",
                color=(0, 0, 0, 1)
            )
            lbl.bind(size=lambda instance, value: setattr(instance, "text_size", (instance.width, None)))

            delete_button = Button(
                text="Удалить",
                size_hint_x=0.2,
                background_normal="",
                background_color=(0.8, 0.2, 0.2, 1),
                color=(1, 1, 1, 1)
            )
            delete_button.bind(on_release=lambda btn, k=key, r=rid: self.confirm_delete_record(k, r))

            row.add_widget(lbl)
            row.add_widget(delete_button)
            container.add_widget(row)

    def confirm_delete_record(self, key, rec_id):
        """Подтверждение удаления записи"""
        self.del_key = key
        self.del_id = rec_id
        
        box = BoxLayout(orientation="vertical", padding=10, spacing=10)
        box.add_widget(Label(text=f"Удалить запись id={rec_id}?"))
        btn_layout = BoxLayout(size_hint_y=None, height=48, spacing=10)
        yes = Button(text="Да")
        no = Button(text="Нет")
        yes.bind(on_release=self.delete_record_confirmed)
        no.bind(on_release=self.delete_record_canceled)
        btn_layout.add_widget(yes)
        btn_layout.add_widget(no)
        box.add_widget(btn_layout)

        self.del_popup = Popup(title="Подтверждение удаления", content=box, size_hint=(0.6, 0.4))
        self.del_popup.open()

    def delete_record_confirmed(self, instance):
        """Удаление записи"""
        key = getattr(self, "del_key", None)
        rid = getattr(self, "del_id", None)
        if key is None or rid is None:
            if hasattr(self, "del_popup"):
                self.del_popup.dismiss()
            return

        records = data.get(key) or []
        new_list = [r for r in records if r.get("id") != rid]
        data[key] = new_list
        save_data(data)
        self.update_lists()
        
        if hasattr(self, "del_popup"):
            self.del_popup.dismiss()

    def delete_record_canceled(self, instance):
        """Отмена удаления."""
        if hasattr(self, "del_popup"):
            self.del_popup.dismiss()

    # TODO: Можно убрать нумерацию id, т.к id уже не нужен для удаления записи, но пока оставил, возможно будет удобен для конкретики
    @staticmethod
    def numbering_id(key):
        """Нумерация id"""
        rec = data.get(key) or []
        try:
            existing = set(int(item.get("id", 0)) for item in rec if isinstance(item, dict) and "id" in item)
        except Exception:
            existing = set()

        new_id = 1
        while new_id in existing:
            new_id += 1
        return new_id


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
                text: "Обновить курсы"
                on_release: root.update_rates()

        BoxLayout:
            size_hint_y: None
            height: 25
            padding: [5, 0, 5, 0]

            Label:
                id: last_update_label
                text: "Курсы обновлены: неизвестно"
                font_size: 13
                color: 0.4, 0.4, 0.4, 1   # серый текст
                halign: "right"
                valign: "middle"
                text_size: self.size


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
            text: "Доходы и расходы"
            font_size: 22
            size_hint_y: None
            height: 40

        BoxLayout:
            size_hint_y: None
            height: "40dp"
            spacing: 10

            StyledButton:
                text: "Добавить запись"
                on_release: root.show_add_ExpenseIncome_form()

        BoxLayout:
            orientation: "horizontal"
            spacing: 10
            size_hint_y: 1

            BoxLayout:
                orientation: "vertical"
                size_hint_x: 0.5
                spacing: 6

                StyledLabel:
                    text: "Доходы"
                    font_size: 18
                    size_hint_y: None
                    height: 30

                ScrollView:
                    do_scroll_x: False
                    do_scroll_y: True

                    BoxLayout:
                        id: income_list
                        orientation: "vertical"
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: 5
                        padding: 5

            BoxLayout:
                orientation: "vertical"
                size_hint_x: 0.5
                spacing: 6

                StyledLabel:
                    text: "Расходы"
                    font_size: 18
                    size_hint_y: None
                    height: 30

                ScrollView:
                    do_scroll_x: False
                    do_scroll_y: True

                    BoxLayout:
                        id: expense_list
                        orientation: "vertical"
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: 5
                        padding: 5

        StyledButton:
            text: "Назад"
            size_hint_y: None
            height: "48dp"
            size_hint_x: 1
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
        # При запуске проверяем и обновляем курсы валют
        if "currencies" not in data or not data["currencies"]:
            print("Курсы валют не найдены, загружаем с сайта ЦБ...")
            update_exchange_rates()
        else:
            # Попробуем тихо обновить курсы (если есть интернет)
            try:
                update_exchange_rates()
                print("Курсы валют успешно обновлены при запуске.")
            except Exception as e:
                print("Не удалось обновить курсы при запуске:", e)

        return Builder.load_string(kv)

if __name__ == "__main__":
    FinanceApp().run()
