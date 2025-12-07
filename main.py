import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import matplotlib.pyplot as plt
from kivy_garden.matplotlib import FigureCanvasKivyAgg
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from threading import Thread
from matplotlib import use
import shutil
import logging
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ObjectProperty
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.metrics import dp, sp

use("Agg")

logging.basicConfig(level=logging.ERROR)

# ---------------------------
# Работа с JSON (хранение данных)
# ---------------------------
DATA_FILE = "data.json"


def load_data():
    """Загрузка данных из файла JSON"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error("Поврежденный JSON файл, возвращаем дефолтные данные")
            return {
                "wallets": [],
                "incomes": [],
                "expenses": [],
                "categories": [],
                "deleted_records": []
            }
    else:
        return {
            "wallets": [],
            "incomes": [],
            "expenses": [],
            "categories": [],
            "deleted_records": []
        }


def save_data(data):
    """Сохранение данных в файл JSON с бэкапом"""
    if os.path.exists(DATA_FILE):
        shutil.copy(DATA_FILE, DATA_FILE + ".bak")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def update_exchange_rates(show_popup=False):
    """Загружает курсы валют с сайта ЦБ РФ и сохраняет их в data."""
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

        app = App.get_running_app()
        app.data["currencies"] = rates
        app.data["last_rates_update"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_data(app.data)
        if show_popup:
            popup = Popup(title="Успешно", content=Label(text="Курсы валют обновлены!"), size_hint=(0.6, 0.3))
            popup.open()
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка сети при обновлении курсов: {e}")
        if show_popup:
            popup = Popup(title="Ошибка", content=Label(text="Не удалось обновить курсы (проверьте интернет)."), size_hint=(0.6, 0.3))
            popup.open()
        return False
    except Exception as e:
        logging.error(f"Ошибка при обновлении курсов: {e}")
        if show_popup:
            popup = Popup(title="Ошибка", content=Label(text="Не удалось обновить курсы."), size_hint=(0.6, 0.3))
            popup.open()
        return False


def move_to_trash(key, rec_id):
    """Перемещает запись в корзину и корректирует баланс кошелька"""
    app = App.get_running_app()
    records = app.data.get(key) or []
    rec = next((r for r in records if r.get("id") == rec_id), None)
    if rec:
        # Корректируем баланс
        wallet_name = rec.get("wallet")
        amount = float(rec.get("amount", 0))
        sign = -1 if key == "incomes" else 1  # Для доходов вычитаем, для расходов прибавляем
        wallet = next((w for w in app.data.get("wallets", []) if w.get("name") == wallet_name), None)
        if wallet:
            wallet["balance"] = float(wallet.get("balance", 0)) + sign * amount

        # Добавляем метку времени и тип записи
        rec["deleted_at"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        rec["record_type"] = key
        app.data["deleted_records"].append(rec)
        # Удаляем из исходного списка
        app.data[key] = [r for r in records if r.get("id") != rec_id]
        save_data(app.data)


def restore_from_trash(rec_id):
    """Восстановление записи из корзины и корректировка баланса"""
    app = App.get_running_app()
    trash = app.data.get("deleted_records") or []
    rec = next((r for r in trash if r.get("id") == rec_id), None)
    if rec:
        key = rec["record_type"]
        # Корректируем баланс обратно
        wallet_name = rec.get("wallet")
        amount = float(rec.get("amount", 0))
        sign = 1 if key == "incomes" else -1  # Для доходов прибавляем, для расходов вычитаем
        wallet = next((w for w in app.data.get("wallets", []) if w.get("name") == wallet_name), None)
        if wallet:
            wallet["balance"] = float(wallet.get("balance", 0)) + sign * amount

        app.data.setdefault(key, []).append(rec)
        app.data["deleted_records"] = [r for r in trash if r.get("id") != rec_id]
        save_data(app.data)


def permanently_delete_from_trash(rec_id):
    """Полное удаление записи в корзине"""
    app = App.get_running_app()
    trash = app.data.get("deleted_records") or []
    app.data["deleted_records"] = [r for r in trash if r.get("id") != rec_id]
    save_data(app.data)


# ---------------------------
# Доп. функции для кошельков
# ---------------------------
def add_wallet(name, currency, balance):
    """Добавляет новый кошелёк в данные и сохраняет их."""
    app = App.get_running_app()
    wallet = {"name": name, "currency": currency, "balance": balance}
    app.data.setdefault("wallets", []).append(wallet)
    save_data(app.data)


def delete_wallet(name):
    """Удаляет кошелёк по имени и перемещает связанные записи в корзину"""
    app = App.get_running_app()
    # Переместить связанные записи в корзину
    for key in ["incomes", "expenses"]:
        records = [r for r in app.data.get(key, []) if r["wallet"] == name]
        for rec in records:
            move_to_trash(key, rec["id"])
    # Удалить кошелек
    app.data["wallets"] = [wallet for wallet in app.data.get("wallets", []) if wallet["name"] != name]
    save_data(app.data)


def calculate_total_balance():
    """Подсчитывает итоговый баланс по всем кошелькам."""
    app = App.get_running_app()
    total_balance = {}
    for wallet in app.data.get("wallets", []):
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
        app = App.get_running_app()
        self.ids.last_update_label.text = f"Курсы обновлены: {app.data.get('last_rates_update', 'неизвестно')}"

    def update_rates(self):
        """Обновляет курсы валют с сайта ЦБ РФ."""
        update_exchange_rates(show_popup=True)
        app = App.get_running_app()
        self.ids.last_update_label.text = f"Курсы обновлены: {app.data.get('last_rates_update', 'неизвестно')}"

    def update_wallet_list(self):
        """Обновляет список кошельков на экране."""
        app = App.get_running_app()
        rates = app.data.get("currencies", {})
        data_list = []
        for wallet in app.data.get("wallets", []):
            if not all(k in wallet for k in ("name", "currency", "balance")):
                continue
            rate = rates.get(wallet["currency"], 1)
            try:
                balance = float(wallet["balance"])
                rub_value = balance * rate
            except (TypeError, ValueError):
                balance = 0.0
                rub_value = 0.0
            text = f"Имя: {wallet['name']}, Баланс: {balance:.2f} {wallet['currency']} (≈ {rub_value:.2f} RUB)"
            data_list.append({'text': text, 'name': wallet['name']})
        self.ids.wallet_rv.data = data_list

    def show_add_wallet_form(self, *args):
        """Показывает форму для добавления кошелька."""
        from kivy.uix.spinner import Spinner

        box = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # Имя кошелька
        self.wallet_name_input = TextInput(hint_text="Имя кошелька", multiline=False)
        box.add_widget(self.wallet_name_input)

        currencies = ["RUB", "USD", "EUR"]

        self.wallet_currency_spinner = Spinner(
            text="Выберите валюту",
            values=currencies,
            size_hint_y=None,
            height=dp(50)
        )
        box.add_widget(self.wallet_currency_spinner)

        # Баланс
        self.wallet_balance_input = TextInput(
            hint_text="Баланс",
            multiline=False,
            input_filter="float"
        )
        box.add_widget(self.wallet_balance_input)

        save_button = Button(
            text="Сохранить",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_color=(0.3, 0.5, 0.9, 1),
            color=(1, 1, 1, 1),
            font_size=sp(18)
        )
        save_button.bind(on_release=self.save_wallet)
        box.add_widget(save_button)

        self.add_wallet_popup = Popup(
            title="Добавить кошелёк",
            content=box,
            size_hint=(0.9, 0.6)
        )
        self.add_wallet_popup.open()

    def save_wallet(self, instance):
        """Сохраняет новый кошелёк и обновляет список."""

        name = (self.wallet_name_input.text or "").strip()
        balance_text = (self.wallet_balance_input.text or "0").strip()
        currency = self.wallet_currency_spinner.text

        # Проверка выбора валюты
        if not name or currency == "Выберите валюту":
            Popup(
                title="Ошибка",
                content=Label(text="Введите имя и выберите валюту!"),
                size_hint=(0.6, 0.3)
            ).open()
            return

        try:
            balance = float(balance_text)
            add_wallet(name, currency, balance)
            self.update_wallet_list()
            self.add_wallet_popup.dismiss()

        except ValueError:
            Popup(
                title="Ошибка",
                content=Label(text="Неверный формат баланса!"),
                size_hint=(0.6, 0.3)
            ).open()


    def confirm_delete_wallet(self, name):
        """Показывает диалог подтверждения удаления кошелька."""
        self.delete_name = name
        box = BoxLayout(orientation="vertical", padding=10, spacing=10)
        box.add_widget(Label(text=f"Удалить кошелёк '{name}' и все его записи?"))
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


class WalletRow(RecycleDataViewBehavior, BoxLayout):
    """Viewclass for wallet RecycleView"""
    text = StringProperty()
    name = StringProperty()
    index = None

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        super().refresh_view_attrs(rv, index, data)  # Замени на super() без аргументов


class WalletRow(RecycleDataViewBehavior, BoxLayout):
    """Viewclass for wallet RecycleView"""
    text = StringProperty()
    name = StringProperty()
    index = None

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        super(WalletRow, self).refresh_view_attrs(rv, index, data)


class ExpenseScreen(Screen):
    """
    Экран добавления доходов и расходов
    """
    def on_pre_enter(self):
        """Обновляет списки доходов и расходов"""
        self.update_lists()

    def show_add_ExpenseIncome_form(self, *args):
        """Показывает форму для добавления дохода или расхода"""
        from kivy.uix.spinner import Spinner
        from kivy.metrics import dp, sp

        app = App.get_running_app()
        wallet_names = [w.get("name") for w in app.data.get("wallets", [])]
        category_names = app.data.get("categories", []) or []

        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))

        # --- Тип действия ---
        self.action_spinner = Spinner(
            text="Выберите действие",
            values=["Добавить доход", "Добавить расход"],
            size_hint_y=None,
            height=dp(50),
            font_size=sp(18)
        )
        box.add_widget(self.action_spinner)

        # --- Выбор кошелька ---
        self.wallet_spinner = Spinner(
            text="Выберите кошелёк",
            values=wallet_names or ["Нет кошельков"],
            size_hint_y=None,
            height=dp(50),
            font_size=sp(18)
        )
        box.add_widget(self.wallet_spinner)

        # --- Выбор категории ---
        self.category_spinner = Spinner(
            text="Выберите категорию",
            values=category_names or ["Нет категорий"],
            size_hint_y=None,
            height=dp(50),
            font_size=sp(18)
        )
        box.add_widget(self.category_spinner)

        # --- Сумма ---
        self.amount_input = TextInput(
            hint_text="Сумма (в валюте кошелька)",
            multiline=False,
            input_filter="float",
            size_hint_y=None,
            height=dp(50),
            font_size=sp(18),
            padding=[dp(10), dp(10)]
        )
        box.add_widget(self.amount_input)

        # --- Кнопка Сохранить ---
        save_button = Button(
            text="Сохранить",
            size_hint_y=None,
            height=dp(56),
            background_normal="",
            background_color=(0.2, 0.6, 0.9, 1),
            color=(1, 1, 1, 1),
            font_size=sp(18),
            bold=True
        )
        save_button.bind(on_release=self.save_record)
        box.add_widget(save_button)

        # --- POPUP ---
        self.add_record_popup = Popup(
            title="Добавить запись",
            content=box,
            size_hint=(0.9, 0.65)
        )
        self.add_record_popup.open()


    def update_lists(self):
        """Обновляем списки"""
        app = App.get_running_app()
        rates = app.data.get("currencies", {})
        incomes = app.data.get("incomes", [])
        expenses = app.data.get("expenses", [])

        income_data = self.get_record_data(incomes, rates, "incomes")
        expense_data = self.get_record_data(expenses, rates, "expenses")

        self.ids.income_rv.data = income_data
        self.ids.expense_rv.data = expense_data

    def get_record_data(self, records, rates, key):
        data_list = []
        for rec in records:
            rid = rec.get("id", "")
            cur = rec.get("currency", "")
            amt = rec.get("amount", 0)
            try:
                amount = float(amt)
            except (TypeError, ValueError):
                amount = 0
            rate = rates.get(cur, 1)
            try:
                rub_value = amount * float(rate)
            except Exception:
                rub_value = 0
            text = f"id: {rid} | {amount} {cur} | кошелёк: {rec.get('wallet', '—')} | категория: {rec.get('category', '—')} (≈ {rub_value:.2f} RUB)"
            data_list.append({'text': text, 'rid': rid, 'key': key})
        return data_list

    def save_record(self, instance):
        """Сохраняет новую запись"""
        amount_text = (self.amount_input.text or "0").strip()
        wallet_name = (self.wallet_spinner.text or "").strip()
        category_name = (self.category_spinner.text or "").strip()
        action_text = (self.action_spinner.text or "").lower()

        try:
            amount = float(amount_text)
            if amount <= 0:
                Popup(title="Ошибка", content=Label(text="Сумма должна быть положительной!"), size_hint=(0.6, 0.3)).open()
                return
        except ValueError:
            Popup(title="Ошибка", content=Label(text="Неверный формат суммы!"), size_hint=(0.6, 0.3)).open()
            return

        if "доход" in action_text:
            key = "incomes"
            sign = 1
        elif "расход" in action_text:
            key = "expenses"
            sign = -1
        else:
            Popup(title="Ошибка", content=Label(text="Выберите действие: доход или расход!"), size_hint=(0.6, 0.3)).open()
            return

        app = App.get_running_app()
        wallets = app.data.get("wallets")
        wallet = next((w for w in wallets if w.get("name") == wallet_name), None)
        if not wallet:
            Popup(title="Ошибка", content=Label(text="Выберите кошелёк или создайте новый!"), size_hint=(0.6, 0.3)).open()
            return

        categories = app.data.get("categories")
        if category_name not in categories:
            Popup(title="Ошибка", content=Label(text="Выберите категорию или создайте новую!"), size_hint=(0.6, 0.3)).open()
            return

        if sign < 0:
            current_bal = float(wallet.get("balance", 0))
            if current_bal < amount:
                Popup(title="Ошибка", content=Label(text="Недостаточно средств в кошельке!"), size_hint=(0.6, 0.3)).open()
                return

        new_id = self.numbering_id(key)
        record = {
            "id": new_id,
            "currency": wallet.get("currency", "RUB"),
            "amount": amount,
            "wallet": wallet_name,
            "category": category_name,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        app.data.setdefault(key, []).append(record)

        wallet["balance"] = float(wallet.get("balance", 0)) + sign * amount

        save_data(app.data)
        self.add_record_popup.dismiss()
        self.update_lists()

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
        """Переносит запись в корзину"""
        key = self.del_key
        rid = self.del_id
        move_to_trash(key, rid)
        self.update_lists()
        self.del_popup.dismiss()

    def delete_record_canceled(self, instance):
        """Отмена удаления."""
        self.del_popup.dismiss()

    @staticmethod
    def numbering_id(key):
        """Нумерация id"""
        app = App.get_running_app()
        rec = app.data.get(key) or []
        existing = set()
        for item in rec:
            try:
                existing.add(int(item.get("id", 0)))
            except ValueError:
                pass
        new_id = 1
        while new_id in existing:
            new_id += 1
        return new_id


class RecordRow(RecycleDataViewBehavior, BoxLayout):
    """Viewclass for record RecycleView"""
    text = StringProperty()
    rid = NumericProperty()
    key = StringProperty()
    index = None

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        super(RecordRow, self).refresh_view_attrs(rv, index, data)


class CategoryScreen(Screen):
    def on_pre_enter(self):
        self.update_category_list()

    def add_category(self, name):
        name = (name or "").strip()
        if not name:
            return
        app = App.get_running_app()
        if name not in app.data["categories"]:
            app.data["categories"].append(name)
            save_data(app.data)
            self.update_category_list()

    def remove_category(self, name):
        app = App.get_running_app()
        if name in app.data["categories"]:
            app.data["categories"].remove(name)
            save_data(app.data)
            self.update_category_list()

    def update_category_list(self):
        app = App.get_running_app()
        data_list = []
        for cat in app.data["categories"]:
            data_list.append({'text': cat})
        self.ids.category_rv.data = data_list


class CategoryRow(RecycleDataViewBehavior, BoxLayout):
    """Viewclass for category RecycleView"""
    text = StringProperty()
    index = None

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        super(CategoryRow, self).refresh_view_attrs(rv, index, data)


class StatsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status_load = False
        self.cached_incomes_by_day = None
        self.cached_expenses_by_day = None
        self.cached_category_totals = None

    def on_pre_enter(self):
        if self.status_load:
            self.update_charts()

    def start_preload(self):
        """Запускаем загрузку в потоке"""
        Thread(target=self.preload_charts, daemon=True).start()

    def preload_charts(self):
        """Берем данные для предзагрузки"""
        try:
            self.fig1, self.ax1 = plt.subplots(figsize=(6, 3))
            self.fig2, self.ax2 = plt.subplots(figsize=(4, 4))

            self.status_load = True
            Clock.schedule_once(lambda dt: self.update_charts())
        except Exception as e:
            logging.error(f"Ошибка загрузки графиков: {e}")

    def update_charts(self):
        app = App.get_running_app()
        incomes = app.data.get("incomes", [])
        expenses = app.data.get("expenses", [])

        # Кэшируем если изменилось
        if self.cached_incomes_by_day is None:
            self.cached_incomes_by_day = self.aggregate_by_day(incomes)
            self.cached_expenses_by_day = self.aggregate_by_day(expenses)
            self.cached_category_totals = self.aggregate_by_category(expenses)

        box = self.ids.stats_box
        box.clear_widgets()

        self.ax1.clear()
        self.ax2.clear()

        days = sorted(set(self.cached_incomes_by_day.keys()) | set(self.cached_expenses_by_day.keys()))
        income_values = [self.cached_incomes_by_day.get(d, 0) for d in days]
        expense_values = [self.cached_expenses_by_day.get(d, 0) for d in days]

        if days:
            self.ax1.plot(days, income_values, label="Доходы", linewidth=2, marker="o", color="green")
            self.ax1.plot(days, expense_values, label="Расходы", linewidth=2, marker="o", color="red")
            self.ax1.set_title("Доходы и расходы по датам")
            self.ax1.set_xlabel("Дата")
            self.ax1.set_ylabel("Сумма")
            self.ax1.legend()
            self.ax1.grid(True)
        else:
            self.ax1.text(0.5, 0.5, "Нет данных для отображения", ha="center", va="center")

        self.fig1.tight_layout()
        graph_widget1 = FigureCanvasKivyAgg(self.fig1)
        graph_widget1.size_hint_y = None
        graph_widget1.height = 400
        box.add_widget(graph_widget1)

        if self.cached_category_totals:
            labels = list(self.cached_category_totals.keys())
            values = list(self.cached_category_totals.values())
            self.ax2.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            self.ax2.set_title("Расходы по категориям")
        else:
            self.ax2.text(0.5, 0.5, "Нет данных по категориям", ha="center", va="center")

        self.fig2.tight_layout()
        graph_widget2 = FigureCanvasKivyAgg(self.fig2)
        graph_widget2.size_hint_y = None
        graph_widget2.height = 400
        box.add_widget(graph_widget2)

    def aggregate_by_day(self, records):
        totals = {}
        for r in records:
            date_str = r.get("date")
            amount = float(r.get("amount", 0))
            if not date_str:
                continue
            try:
                date = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
                key = date.strftime("%d.%m")
            except ValueError:
                key = "неизв."
                continue
            totals[key] = totals.get(key, 0) + amount
        return totals

    def aggregate_by_category(self, expenses):
        totals = {}
        for e in expenses:
            cat = e.get("category", "Без категории")
            amount = float(e.get("amount", 0))
            totals[cat] = totals.get(cat, 0) + amount
        return totals


def generate_report(data):
    import os
    import shutil
    from datetime import datetime
    from kivy.app import App
    from kivy.utils import platform

    try:
        app = App.get_running_app()
        if app:
            base_dir = app.user_data_dir
        else:
            base_dir = os.getcwd()

        os.makedirs(base_dir, exist_ok=True)

        lines = []
        lines.append("Финансовый отчёт")
        lines.append(f"Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        lines.append("")

        lines.append("Кошельки:")
        for w in data.get("wallets", []):
            lines.append(f"- {w.get('name','')} : {w.get('balance',0)} {w.get('currency','')}")
        lines.append("")

        lines.append("Доходы:")
        for r in data.get("incomes", []):
            lines.append(f"- id:{r.get('id','')} | {r.get('amount',0)} {r.get('currency','')} | {r.get('category','')} | {r.get('date','')}")
        lines.append("")

        lines.append("Расходы:")
        for r in data.get("expenses", []):
            lines.append(f"- id:{r.get('id','')} | {r.get('amount',0)} {r.get('currency','')} | {r.get('category','')} | {r.get('date','')}")
        lines.append("")

        total_in = sum(float(r.get('amount', 0)) for r in data.get('incomes', []))
        total_out = sum(float(r.get('amount', 0)) for r in data.get('expenses', []))
        balance = total_in - total_out

        lines.append(f"Итого доходов: {total_in:.2f}")
        lines.append(f"Итого расходов: {total_out:.2f}")
        lines.append(f"Чистый результат: {balance:.2f}")
        lines.append("")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        txt_filename = os.path.join(base_dir, f"financial_report_{timestamp}.txt")

        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # PNG УДАЛЁН НАВСЕГДА — больше не создаётся и не возвращается

        downloads_path = None
        if platform == "android":
            try:
                downloads_dir = "/storage/emulated/0/Download"
                if os.path.exists(downloads_dir):
                    downloads_path = os.path.join(
                        downloads_dir,
                        f"financial_report_{timestamp}.txt"
                    )
                    shutil.copy(txt_filename, downloads_path)
            except Exception as e:
                logging.error(f"Не удалось сохранить в папку Downloads: {e}")

        # Возвращаем только текстовый файл
        return {
            "internal": txt_filename,
            "downloads": downloads_path
            # "chart" — больше не возвращаем!
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"Ошибка при создании отчёта: {e}")
        return None


class TrashScreen(Screen):
    def on_pre_enter(self):
        """Обновляет список удалённых записей"""
        self.update_trash_list()

    def update_trash_list(self):
        """Заполняет контейнер записями из корзины"""
        app = App.get_running_app()
        trash = app.data.get("deleted_records", [])
        rates = app.data.get("currencies", {})
        data_list = []
        for rec in trash:
            rid = rec.get("id", "")
            cur = rec.get("currency", "")
            amt = rec.get("amount", 0)
            deleted_at = rec.get("deleted_at", "")
            try:
                amount = float(amt)
            except (TypeError, ValueError):
                amount = 0
            rate = rates.get(cur, 1)
            try:
                rub_value = amount * float(rate)
            except Exception:
                rub_value = 0
            text = f"id: {rid} | {amount} {cur} (≈ {rub_value:.2f} RUB) | Удалено: {deleted_at}"
            data_list.append({'text': text, 'rid': rid})
        self.ids.trash_rv.data = data_list

    def restore_record(self, rec_id):
        """Восстанавливает запись"""
        restore_from_trash(rec_id)
        self.update_trash_list()

    def confirm_permanently_delete_record(self, rec_id):
        """Подтверждение окончательного удаления"""
        self.del_id = rec_id

        box = BoxLayout(orientation="vertical", padding=10, spacing=10)
        box.add_widget(Label(text=f"Удалить навсегда запись id={rec_id}?"))
        btn_layout = BoxLayout(size_hint_y=None, height=48, spacing=10)
        yes = Button(text="Да")
        no = Button(text="Нет")
        yes.bind(on_release=self.permanently_delete_confirmed)
        no.bind(on_release=self.permanently_delete_canceled)
        btn_layout.add_widget(yes)
        btn_layout.add_widget(no)
        box.add_widget(btn_layout)

        self.del_popup = Popup(title="Подтверждение удаления", content=box, size_hint=(0.6, 0.4))
        self.del_popup.open()

    def permanently_delete_confirmed(self, instance):
        """Окончательно удаляет запись"""
        permanently_delete_from_trash(self.del_id)
        self.update_trash_list()
        self.del_popup.dismiss()

    def permanently_delete_canceled(self, instance):
        """Отмена удаления."""
        self.del_popup.dismiss()


class TrashRow(RecycleDataViewBehavior, BoxLayout):
    """Viewclass for trash RecycleView"""
    text = StringProperty()
    rid = NumericProperty()
    index = None

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        super(TrashRow, self).refresh_view_attrs(rv, index, data)


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
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<RecycleView>:
    do_scroll_x: False
    do_scroll_y: True
    bar_width: 0
    scroll_type: ['bars', 'content']
    canvas.before:
        Color:
            rgba: rgba("#F0F0F0")
        Rectangle:
            pos: self.pos
            size: self.size

<RecycleBoxLayout>:
    default_size: None, dp(56)
    default_size_hint: 1, None
    size_hint_y: None
    height: self.minimum_height
    orientation: 'vertical'
    spacing: dp(2)
    padding: dp(5)
    canvas.before:
        Color:
            rgba: rgba("#F0F0F0")
        Rectangle:
            pos: self.pos
            size: self.size

<WalletRow>, <RecordRow>, <CategoryRow>, <TrashRow>:
    canvas.before:
        Color:
            rgba: rgba("#F0F0F0")
        Rectangle:
            pos: self.pos
            size: self.size

<StyledButton@Button>:
    size_hint_y: None
    height: dp(56)
    background_normal: ""
    background_color: rgba("#4d6fa3")
    color: 1, 1, 1, 1
    font_size: sp(20)
    bold: True

<StyledLabel@Label>:
    font_size: sp(22)
    color: 0, 0, 0, 1

<TextInput>:
    background_color: 1, 1, 1, 1
    foreground_color: 0, 0, 0, 1
    padding: [dp(10), dp(10)]
    font_size: sp(18)

<WalletRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(48)
    spacing: dp(10)
    padding: dp(6)

    Label:
        text: root.text
        size_hint_x: 0.8
        halign: "left"
        valign: "middle"
        color: (0, 0, 0, 1)
        text_size: self.size

    Button:
        text: "Удалить"
        size_hint_x: 0.2
        background_normal: ""
        background_color: (0.8, 0.2, 0.2, 1)
        color: (1, 1, 1, 1)
        on_release: app.root.get_screen('wallets').confirm_delete_wallet(root.name)

<RecordRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: self.minimum_height
    spacing: dp(8)
    padding: [dp(6), dp(6)]

    Label:
        text: root.text
        size_hint_x: 0.78
        size_hint_y: None
        text_size: self.width, None
        height: self.texture_size[1]
        halign: "left"
        valign: "top"
        color: (0, 0, 0, 1)

    Button:
        text: "Удалить"
        size_hint_x: 0.22
        background_normal: ""
        background_color: (0.8,0.2,0.2,1)
        color: (1,1,1,1)
        on_release: app.root.get_screen('expenses').confirm_delete_record(root.key, root.rid)


<CategoryRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(48)
    spacing: dp(10)
    padding: [dp(6), dp(6)]

    Label:
        text: root.text
        halign: "left"
        valign: "middle"
        size_hint_x: 1
        color: (0, 0, 0, 1)
        font_size: sp(16)
        text_size: self.size

    Button:
        text: "X"
        size_hint: (None, None)
        size: (dp(36), dp(36))
        font_size: sp(18)
        background_normal: ""
        background_color: (0.85, 0.2, 0.2, 1)
        color: (1, 1, 1, 1)
        on_release: app.root.get_screen('categories').remove_category(root.text)

<TrashRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(48)
    spacing: dp(10)
    padding: [dp(6), dp(6)]

    Label:
        text: root.text
        size_hint_x: 0.6
        halign: "left"
        valign: "middle"
        color: (0, 0, 0, 1)
        text_size: self.size

    Button:
        text: "Восстановить"
        size_hint_x: 0.2
        background_normal: ""
        background_color: (0.2, 0.7, 0.2, 1)
        color: (1, 1, 1, 1)
        on_release: app.root.get_screen('trash').restore_record(root.rid)

    Button:
        text: "Удалить навсегда"
        size_hint_x: 0.2
        background_normal: ""
        background_color: (0.8, 0.2, 0.2, 1)
        color: (1, 1, 1, 1)
        on_release: app.root.get_screen('trash').confirm_permanently_delete_record(root.rid)

FinanceManager:
    MainMenu:
    WalletScreen:
    ExpenseScreen:
    CategoryScreen:
    StatsScreen:
    TrashScreen:

<MainMenu>:
    name: "menu"
    BoxLayout:
        orientation: "vertical"
        spacing: dp(15)
        padding: dp(30)
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Финансовый менеджер"
            font_size: sp(28)
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
            text: "Корзина"
            on_release: app.root.current = "trash"

        StyledButton:
            text: "Выход"
            background_color: rgba("#E74C3C")
            on_release: app.stop()

<WalletScreen>:
    name: "wallets"
    BoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(15)
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Экран кошельков"
            font_size: sp(22)

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True

            RecycleView:
                id: wallet_rv
                viewclass: 'WalletRow'
                RecycleBoxLayout:
                    default_size: None, dp(48)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(5)
                    padding: dp(5)

        BoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: dp(60)
            spacing: dp(10)

            StyledButton:
                text: "Добавить"
                size_hint_x: 1
                font_size: sp(16)
                on_release: root.show_add_wallet_form()

            StyledButton:
                text: "Баланс"
                size_hint_x: 1
                font_size: sp(16)
                on_release: root.show_total_balance()

            StyledButton:
                text: "Обновить"
                size_hint_x: 1
                font_size: sp(16)
                on_release: root.update_rates()

        BoxLayout:
            size_hint_y: None
            height: dp(25)
            padding: [dp(5), 0, dp(5), 0]

            Label:
                id: last_update_label
                text: "Курсы обновлены: неизвестно"
                font_size: sp(13)
                color: 0.4, 0.4, 0.4, 1
                halign: "right"
                valign: "middle"
                text_size: self.size

        StyledButton:
            text: "Назад"
            background_color: rgba("#95A5A6")
            font_size: sp(18)
            size_hint_y: None
            height: dp(60)
            on_release: app.root.current = "menu"

<ExpenseScreen>:
    name: "expenses"
    BoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(20)
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Доходы и расходы"
            font_size: sp(22)
            size_hint_y: None
            height: dp(40)

        BoxLayout:
            size_hint_y: None
            height: dp(40)
            spacing: dp(10)

            StyledButton:
                text: "Добавить запись"
                on_release: root.show_add_ExpenseIncome_form()

        TabbedPanel:
            do_default_tab: False
            size_hint_y: 1

            TabbedPanelItem:
                text: "Доходы"

                ScrollView:
                    do_scroll_x: False
                    do_scroll_y: True

                    RecycleView:
                        id: income_rv
                        viewclass: 'RecordRow'
                        RecycleBoxLayout:
                            default_size: None, dp(44)
                            default_size_hint: 1, None
                            size_hint_y: None
                            height: self.minimum_height
                            orientation: 'vertical'
                            spacing: dp(5)
                            padding: dp(5)

            TabbedPanelItem:
                text: "Расходы"

                ScrollView:
                    do_scroll_x: False
                    do_scroll_y: True

                    RecycleView:
                        id: expense_rv
                        viewclass: 'RecordRow'
                        RecycleBoxLayout:
                            default_size: None, dp(44)
                            default_size_hint: 1, None
                            size_hint_y: None
                            height: self.minimum_height
                            orientation: 'vertical'
                            spacing: dp(5)
                            padding: dp(5)

        StyledButton:
            text: "Назад"
            size_hint_y: None
            height: dp(48)
            size_hint_x: 1
            background_color: rgba("#95A5A6")
            on_release: app.root.current = "menu"

<CategoryScreen>:
    name: "categories"
    BoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(20)
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Категории расходов"
            font_size: sp(22)

        TextInput:
            id: category_input
            hint_text: "Введите название категории"
            size_hint_y: None
            height: dp(45)

        StyledButton:
            text: "Добавить категорию"
            on_release:
                root.add_category(category_input.text)
                category_input.text = ""

        StyledLabel:
            text: "Список категорий:"
            font_size: sp(18)

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True

            RecycleView:
                id: category_rv
                viewclass: 'CategoryRow'
                RecycleBoxLayout:
                    default_size: None, dp(48)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(5)
                    padding: dp(5)

        StyledButton:
            text: "Назад"
            background_color: rgba("#95A5A6")
            on_release: app.root.current = "menu"

<StatsScreen>:
    name: "stats"
    BoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(20)
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Статистика"
            font_size: sp(22)
            size_hint_y: None
            height: dp(40)

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True
            GridLayout:
                id: stats_box
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(30)
                padding: dp(10)

        StyledButton:
            text: "Сформировать отчёт"
            on_release: app.generate_report_action()

        StyledButton:
            text: "Назад"
            size_hint_y: None
            height: dp(48)
            background_color: rgba("#95A5A6")
            on_release: app.root.current = "menu"

<TrashScreen>:
    name: "trash"
    BoxLayout:
        orientation: "vertical"
        spacing: dp(10)
        padding: dp(20)
        canvas.before:
            Color:
                rgba: rgba("#F0F0F0")
            Rectangle:
                pos: self.pos
                size: self.size

        StyledLabel:
            text: "Корзина удалённых записей"
            font_size: sp(22)
            size_hint_y: None
            height: dp(40)

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True

            RecycleView:
                id: trash_rv
                viewclass: 'TrashRow'
                RecycleBoxLayout:
                    default_size: None, dp(48)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(5)
                    padding: dp(5)

        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: dp(10)

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
        self.data = load_data()
        if "currencies" not in self.data or not self.data["currencies"]:
            logging.info("Курсы валют не найдены, загружаем с сайта ЦБ...")
            update_exchange_rates()
        else:
            try:
                Thread(target=update_exchange_rates).start()
            except Exception as e:
                logging.error(f"Не удалось обновить курсы при запуске: {e}")

        return Builder.load_string(kv)

    def on_start(self):
        try:
            stats = self.root.get_screen("stats")
            stats.start_preload()
        except Exception as e:
            logging.error(f"Не удалось сделать предзагрузку статистики: {e}")

    def generate_report_action(self):
        """Самая простая и стабильная версия — только txt + понятное сообщение"""
        result = generate_report(self.data)
        if not result:
            Popup(title="Ошибка", content=Label(text="Не удалось создать отчёт")).open()
            return

        internal_path = result["internal"]
        downloads_path = result.get("downloads")
        in_downloads = False

        content = BoxLayout(orientation="vertical", padding=dp(25), spacing=dp(20))

        message = "Отчёт успешно сохранён!\n" \
                      "И доступен в папке Загрузки[/b]"

        label = Label(
            text=message,
            markup=True,
            halign="center",
            valign="middle",
            font_size=sp(19),
            line_height=1.7
        )
        label.bind(size=lambda *x: setattr(label, 'text_size', label.size))

        content.add_widget(label)

        close_btn = Button(text="Готово", size_hint_y=None, height=dp(50))
        content.add_widget(close_btn)

        popup = Popup(
            title="Готово",
            content=content,
            size_hint=(0.8, 0.5),
            auto_dismiss=False
        )
        popup.open()
        close_btn.bind(on_release=popup.dismiss)

if __name__ == "__main__":
    FinanceApp().run()