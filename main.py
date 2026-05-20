import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
import csv
import json
from datetime import datetime, date
import calendar
import os
import platform
import yfinance as yf

# 💡 畫圖大師 Matplotlib
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- 🚀 全局系統防禦機制 ---
is_mac = platform.system() == 'Darwin'
if is_mac:
    matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'PingFang TC']
else:
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

FONT_NAME = "PingFang TC" if is_mac else "Segoe UI"
DATA_FILE = "records.csv"
CONFIG_FILE = "config.json"
calendar.setfirstweekday(calendar.SUNDAY)

# 🎨 莫蘭迪圓餅圖專用色盤
EXPENSE_COLORS = ['#FF9999', '#FFB366', '#FFD966', '#B3E6B3', '#99CCFF', '#C299FF', '#FF99CC', '#E0E0E0']
INCOME_COLORS = ['#99CCFF', '#99FFCC', '#FFFF99', '#FFCC99', '#E0E0E0']

# 全球常用離線備用匯率表 (1外幣 = ?台幣)
FALLBACK_RATES = {
    "TWD": 1.0, "USD": 32.5, "JPY": 0.21, "EUR": 34.5, "KRW": 0.024, "GBP": 40.5, 
    "AUD": 21.5, "CAD": 23.5, "CNY": 4.5, "HKD": 4.1, "SGD": 24.0, "THB": 0.9,
    "VND": 0.0013, "MYR": 6.8, "IDR": 0.002, "PHP": 0.55, "NZD": 19.5, "CHF": 35.5
}

def get_default_cates():
    return {"支出": ["飲食", "交通", "娛樂", "服飾", "美容", "學習", "醫藥", "其他"], "收入": ["薪資", "紅包", "獎學金", "投資", "其他"]}

class FlatButton(tk.Label):
    def __init__(self, master, text="", command=None, **kwargs):
        self.command = command
        super().__init__(master, text=text, anchor="center", **kwargs)
        self.bind("<Button-1>", self.on_click)
    def on_click(self, event):
        if self.command: self.command()

class CollegeBudgetAppV31_4:
    def __init__(self, root):
        self.root = root
        self.root.title("大學生的小金庫")
        self.root.geometry("420x880")
        
        self.load_config()
        self.apply_theme()

        self.expression = ""; self.record_type = "支出"
        self.selected_category = ""; self.is_add_panel_visible = False
        self.btn_dict = {}; self.category_btns = [] 
        self.current_date = date.today()  
        self.view_year = self.current_date.year; self.view_month = self.current_date.month

        if not os.path.isfile(DATA_FILE):
            with open(DATA_FILE, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow(["日期", "類型", "類別", "金額", "備註"])

        self.root.bind("<Key>", self.handle_keypress)
        self.build_ui()
        self.auto_deduct_subscriptions()

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except:
            self.config = {
                "categories": get_default_cates(),
                "budget": 8000,
                "dark_mode": False,
                "subscriptions": [],
                "gemini_api_key": ""
            }
            self.save_config()

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    def auto_deduct_subscriptions(self):
        subs = self.config.get("subscriptions", [])
        if not subs: return
        today = date.today()
        current_month_prefix = today.strftime("%Y-%m")
        existing_auto_notes = set()
        
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    if row["日期"].startswith(current_month_prefix) and "自動扣款" in row.get("備註", ""):
                        existing_auto_notes.add(row["備註"])
        
        added_new = False
        for sub in subs:
            note_tag = f"[自動扣款] {sub['name']}"
            if today.day >= sub["day"] and note_tag not in existing_auto_notes:
                with open(DATA_FILE, "a", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerow([today.strftime("%Y-%m-%d"), "支出", sub["category"], sub["amount"], note_tag])
                added_new = True
        
        if added_new:
            messagebox.showinfo("系統通知", "已為您自動扣除本月到期的訂閱服務費用！")
            self.refresh_calendar()

    def manage_subscriptions(self):
        subs = self.config.get("subscriptions", [])
        sub_list = "\n".join([f"• 每月 {s['day']} 號：{s['name']} (${s['amount']})" for s in subs])
        msg = f"目前訂閱清單：\n{sub_list}\n\n你想新增一個訂閱嗎？\n(輸入格式： 名稱,金額,扣款日,類別  例如： Netflix,390,15,娛樂)"
        new_sub_str = simpledialog.askstring("訂閱管理", msg, parent=self.root)
        if new_sub_str:
            try:
                name, amt, day, cate = new_sub_str.split(",")
                self.config.setdefault("subscriptions", []).append({
                    "name": name.strip(), "amount": float(amt.strip()), 
                    "day": int(day.strip()), "category": cate.strip()
                })
                self.save_config()
                messagebox.showinfo("成功", f"已新增訂閱：{name.strip()}")
                self.auto_deduct_subscriptions() 
            except:
                messagebox.showerror("錯誤", "格式錯誤！請確保用半形逗號分隔四個項目。")

    def apply_theme(self):
        if self.config.get("dark_mode", False):
            self.bg_main = "#1C1C1E"; self.display_bg = "#2C2C2E"
            self.text_color = "#F5F5F7"; self.text_muted = "#8E8E93"
            self.num_btn_bg = "#3A3A3C"; self.op_btn_bg = "#48484A"
        else:
            self.bg_main = "#F9F8F6"; self.display_bg = "#FFFFFF"
            self.text_color = "#1D1D1F"; self.text_muted = "#8E8E93"
            self.num_btn_bg = "#F2F2F7"; self.op_btn_bg = "#E5E5EA"
        self.clear_btn_bg = "#FF6B6B"; self.cate_btn_bg = "#4A90E2"
        self.save_text_color = "#FFFFFF"; self.feedback_color = "#8E8E93"
        self.root.configure(bg=self.bg_main)
        matplotlib.rcParams['text.color'] = self.text_color

    def toggle_theme(self):
        self.config["dark_mode"] = not self.config.get("dark_mode", False)
        self.save_config(); self.apply_theme()
        for widget in self.root.winfo_children(): widget.destroy()
        self.build_ui()

    def build_ui(self):
        self.calendar_frame = tk.Frame(self.root, bg=self.bg_main)
        self.add_panel_frame = tk.Frame(self.root, bg=self.bg_main)
        self.chart_panel_frame = tk.Frame(self.root, bg=self.bg_main)
        self.calendar_frame.pack(fill="both", expand=True)
        
        self.init_calendar_content()
        self.init_add_panel_content()
        self.init_chart_panel_content()

        self.fab = FlatButton(self.root, text="＋", font=("Arial", 36), bg=self.clear_btn_bg, fg=self.save_text_color, command=self.show_add_record_panel)
        self.fab.place(relx=0.5, rely=0.92, anchor="center", width=65, height=65)
        self.refresh_calendar()

    def init_calendar_content(self):
        root = self.calendar_frame
        top_frame = tk.Frame(root, bg=self.bg_main); top_frame.pack(fill="x", pady=(20, 5), padx=15)
        theme_icon = "🌞" if self.config.get("dark_mode", False) else "🌙"
        FlatButton(top_frame, text=theme_icon, bg=self.bg_main, fg=self.text_color, font=(FONT_NAME, 16), command=self.toggle_theme).pack(side="left")
        
        cb_frame = tk.Frame(top_frame, bg=self.bg_main); cb_frame.pack(side="left", expand=True)
        FlatButton(cb_frame, text="◀", bg=self.bg_main, fg=self.text_color, font=(FONT_NAME, 14), command=self.prev_month).pack(side="left")
        self.cal_year_var = tk.StringVar(value=str(self.view_year)); self.cal_month_var = tk.StringVar(value=f"{self.view_month:02d}")
        ttk.Combobox(cb_frame, textvariable=self.cal_year_var, values=[str(y) for y in range(2020, 2031)], width=5, font=(FONT_NAME, 12, "bold"), state="readonly").pack(side="left", padx=2)
        ttk.Combobox(cb_frame, textvariable=self.cal_month_var, values=[f"{m:02d}" for m in range(1, 13)], width=3, font=(FONT_NAME, 12, "bold"), state="readonly").pack(side="left", padx=2)
        FlatButton(cb_frame, text="▶", bg=self.bg_main, fg=self.text_color, font=(FONT_NAME, 14), command=self.next_month).pack(side="left")

        sub_btn = FlatButton(top_frame, text="🔁 訂閱", font=(FONT_NAME, 11, "bold"), bg=self.op_btn_bg, fg=self.text_color)
        sub_btn.command = lambda: [self.visual_feedback(sub_btn), self.manage_subscriptions()]
        sub_btn.pack(side="right", ipady=2, ipadx=5)

        self.cal_grid_frame = tk.Frame(root, bg=self.bg_main); self.cal_grid_frame.pack(fill="x", padx=10, pady=5)
        for i in range(7): self.cal_grid_frame.columnconfigure(i, weight=1)

        budget_container = tk.Frame(root, bg=self.bg_main); budget_container.pack(fill="x", padx=20, pady=5)
        budget_text_frame = tk.Frame(budget_container, bg=self.bg_main); budget_text_frame.pack(fill="x")
        tk.Label(budget_text_frame, text="每月預算進度", font=(FONT_NAME, 11, "bold"), bg=self.bg_main, fg=self.text_color).pack(side="left")
        self.lbl_budget_val = tk.Label(budget_text_frame, text="$0 / $8000 ✎", font=(FONT_NAME, 12, "bold"), bg=self.bg_main, fg=self.cate_btn_bg)
        self.lbl_budget_val.pack(side="right"); self.lbl_budget_val.bind("<Button-1>", lambda e: self.change_budget_dialog()) 

        self.budget_canvas = tk.Canvas(budget_container, height=14, bg=self.op_btn_bg, highlightthickness=0)
        self.budget_canvas.pack(fill="x", pady=5)

        tk.Frame(root, bg=self.op_btn_bg, height=1).pack(fill="x", padx=15)
        self.summary_frame = tk.Frame(root, bg=self.bg_main); self.summary_frame.pack(fill="x", padx=20, pady=10)
        self.lbl_exp = tk.Label(self.summary_frame, text="支出: $0", fg=self.clear_btn_bg, bg=self.bg_main, font=(FONT_NAME, 11, "bold")); self.lbl_exp.pack(side="left", expand=True)
        self.lbl_inc = tk.Label(self.summary_frame, text="收入: $0", fg=self.cate_btn_bg, bg=self.bg_main, font=(FONT_NAME, 11, "bold")); self.lbl_inc.pack(side="left", expand=True)
        self.lbl_bal = tk.Label(self.summary_frame, text="結餘: $0", fg=self.text_color, bg=self.bg_main, font=(FONT_NAME, 11, "bold")); self.lbl_bal.pack(side="left", expand=True)
        tk.Frame(root, bg=self.op_btn_bg, height=1).pack(fill="x", padx=15)

        search_frame = tk.Frame(root, bg=self.bg_main); search_frame.pack(fill="x", padx=20, pady=(10, 0))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=(FONT_NAME, 12), bg=self.op_btn_bg, fg=self.text_color, insertbackground=self.text_color, relief="flat", highlightthickness=0)
        self.search_entry.pack(fill="x", ipady=5); self.search_entry.insert(0, "搜尋全月明細...")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END) if self.search_var.get() == "搜尋全月明細..." else None)
        self.search_entry.bind("<FocusOut>", lambda e: self.search_entry.insert(0, "搜尋全月明細...") if not self.search_var.get() else None)

        title_frame = tk.Frame(root, bg=self.bg_main); title_frame.pack(fill="x", padx=20, pady=(10, 0))
        self.list_title_lbl = tk.Label(title_frame, text="今日明細", font=(FONT_NAME, 13, "bold"), bg=self.bg_main, fg=self.text_color); self.list_title_lbl.pack(side="left")
        
        self.dash_curr_var = tk.StringVar(value="TWD")
        dash_cb = ttk.Combobox(title_frame, textvariable=self.dash_curr_var, values=list(FALLBACK_RATES.keys()), width=4, state="readonly")
        dash_cb.pack(side="left", padx=10); dash_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_calendar())

        self.chart_btn = FlatButton(title_frame, text="報表分析", font=(FONT_NAME, 11, "bold"), bg=self.cate_btn_bg, fg=self.save_text_color)
        self.chart_btn.command = lambda: [self.visual_feedback(self.chart_btn), self.show_chart_panel()]; self.chart_btn.pack(side="right", ipady=2, ipadx=8)

        tree_frame = tk.Frame(root, bg=self.bg_main); tree_frame.pack(fill="both", expand=True, padx=15, pady=5)
        style = ttk.Style(); style.theme_use("clam")
        style.configure("Treeview", font=(FONT_NAME, 11), rowheight=35, background=self.display_bg, fieldbackground=self.display_bg, borderwidth=0, foreground=self.text_color)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Date", "Category", "Amount", "Note"), show="", style="Treeview")
        self.tree.column("Date", width=40, anchor="w"); self.tree.column("Category", width=80, anchor="w")
        self.tree.column("Amount", width=70, anchor="e"); self.tree.column("Note", width=120, anchor="e")
        self.tree.pack(fill="both", expand=True, pady=(0, 70))
        self.search_var.trace_add("write", lambda *args: self.refresh_calendar())

    def change_budget_dialog(self):
        new_b = simpledialog.askinteger("預算設定", "請輸入每月預算上限 (TWD)：", initialvalue=self.config.get("budget", 8000), parent=self.root)
        if new_b is not None: self.config["budget"] = new_b; self.save_config(); self.refresh_calendar()

    def refresh_calendar(self):
        for widget in self.cal_grid_frame.winfo_children(): widget.destroy()
        days = ["日", "一", "二", "三", "四", "五", "六"]
        for i, d in enumerate(days): tk.Label(self.cal_grid_frame, text=d, font=(FONT_NAME, 10), fg=self.text_muted, bg=self.bg_main).grid(row=0, column=i, pady=(0, 5))
        month_days = calendar.monthcalendar(self.view_year, self.view_month)
        for r, week in enumerate(month_days):
            for c, day in enumerate(week):
                if day != 0:
                    is_selected = (self.current_date.year == self.view_year and self.current_date.month == self.view_month and self.current_date.day == day)
                    bg_c = "#FFB703" if is_selected else self.bg_main; fg_c = "#FFFFFF" if is_selected else self.text_color
                    lbl = FlatButton(self.cal_grid_frame, text=str(day), font=(FONT_NAME, 12), bg=bg_c, fg=fg_c, width=3)
                    lbl.command = lambda d=day: self.select_date(d); lbl.grid(row=r+1, column=c, pady=2)

        for item in self.tree.get_children(): self.tree.delete(item)
        target_month_str = f"{self.view_year}-{self.view_month:02d}"; target_day_str = self.current_date.strftime("%Y-%m-%d")
        keyword = self.search_var.get().strip(); is_searching = keyword != "" and keyword != "搜尋全月明細..."
        month_out = 0.0; day_in = 0.0; day_out = 0.0

        display_curr = self.dash_curr_var.get()
        rate_multiplier = 1.0 / FALLBACK_RATES.get(display_curr, 1.0)
        curr_symbol = "" if display_curr == "TWD" else display_curr

        try:
            with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    note_text = row.get("備註", "")
                    amt_twd = float(row["金額"]); row_date = row["日期"]; clean_cate = self.clean_old_emoji(row["類別"])
                    
                    if row_date.startswith(target_month_str) and row["類型"] == "支出": month_out += amt_twd
                    
                    show_in_list = False
                    if is_searching:
                        if row_date.startswith(target_month_str) and (keyword.lower() in clean_cate.lower() or keyword.lower() in note_text.lower()):
                            show_in_list = True; self.list_title_lbl.config(text=f"搜尋：{keyword}")
                    else:
                        if row_date == target_day_str:
                            show_in_list = True; self.list_title_lbl.config(text="今日明細")

                    if show_in_list:
                        display_date = row_date[-2:] if is_searching else ""
                        disp_amt = amt_twd * rate_multiplier
                        short_note = (note_text[:6] + '..') if len(note_text) > 6 else note_text 
                        
                        if row["類型"] == "收入":
                            day_in += amt_twd if not is_searching else 0
                            self.tree.insert("", "end", values=(display_date, clean_cate, f"{disp_amt:.1f}", short_note), tags=("in",))
                        else:
                            day_out += amt_twd if not is_searching else 0
                            self.tree.insert("", "end", values=(display_date, clean_cate, f"-{disp_amt:.1f}", short_note), tags=("out",))
            self.tree.tag_configure("in", foreground=self.cate_btn_bg); self.tree.tag_configure("out", foreground=self.clear_btn_bg)
        except: pass

        disp_day_out = day_out * rate_multiplier; disp_day_in = day_in * rate_multiplier; disp_bal = (day_in - day_out) * rate_multiplier
        self.lbl_exp.config(text=f"支出: {curr_symbol}${disp_day_out:.1f}"); self.lbl_inc.config(text=f"收入: {curr_symbol}${disp_day_in:.1f}")
        self.lbl_bal.config(text=f"結餘: {curr_symbol}${disp_bal:.1f}")
        self.update_budget_progress(month_out)

    def update_budget_progress(self, current_spend):
        bg = self.config.get("budget", 8000)
        self.lbl_budget_val.config(text=f"${current_spend:g} / ${bg:g} ✎")
        percent = current_spend / bg if bg > 0 else 0
        color = "#34C759"
        if percent >= 1.0: color = "#FF3B30"
        elif percent >= 0.8: color = "#FF9500"
        self.budget_canvas.delete("all")
        w = self.budget_canvas.winfo_width(); w = 360 if w <= 1 else w
        self.budget_canvas.create_rectangle(0, 0, min(w, w * percent), 14, fill=color, outline="")

    def select_date(self, day): self.current_date = date(self.view_year, self.view_month, day); self.search_var.set(""); self.refresh_calendar()
    def on_month_year_changed(self, event=None): self.view_year = int(self.cal_year_var.get()); self.view_month = int(self.cal_month_var.get()); self.auto_select_day(); self.refresh_calendar(); self.chart_year_var.set(str(self.view_year)); self.chart_month_var.set(f"{self.view_month:02d}")
    def prev_month(self): self.view_month, self.view_year = (12, self.view_year-1) if self.view_month == 1 else (self.view_month-1, self.view_year); self.cal_year_var.set(str(self.view_year)); self.cal_month_var.set(f"{self.view_month:02d}"); self.on_month_year_changed()
    def next_month(self): self.view_month, self.view_year = (1, self.view_year+1) if self.view_month == 12 else (self.view_month+1, self.view_year); self.cal_year_var.set(str(self.view_year)); self.cal_month_var.set(f"{self.view_month:02d}"); self.on_month_year_changed()
    def auto_select_day(self): today = date.today(); self.current_date = today if (self.view_year == today.year and self.view_month == today.month) else date(self.view_year, self.view_month, 1)
    def clean_old_emoji(self, text):
        for e in ["🍔", "🚌", "🎁", "👗", "💄", "📚", "🏥", "🏠", "💰", "🧧", "🏮", "📈", "💵", " "]: text = text.replace(e, "")
        return text.strip()

    def init_chart_panel_content(self):
        root = self.chart_panel_frame
        top_frame = tk.Frame(root, bg=self.bg_main); top_frame.pack(fill="x", padx=10, pady=(15, 10))
        self.back_btn = FlatButton(top_frame, text="◀ 返回", font=(FONT_NAME, 14, "bold"), bg=self.bg_main, fg=self.text_muted)
        self.back_btn.command = lambda: [self.visual_feedback(self.back_btn), self.hide_chart_panel()]; self.back_btn.pack(side="left", ipadx=10, ipady=10)
        
        cb_frame = tk.Frame(top_frame, bg=self.bg_main); cb_frame.pack(side="left", expand=True, padx=(10,0))
        self.chart_year_var = tk.StringVar(value=str(self.view_year)); self.chart_month_var = tk.StringVar(value=f"{self.view_month:02d}")
        self.chart_year_cb = ttk.Combobox(cb_frame, textvariable=self.chart_year_var, values=[str(y) for y in range(2020, 2031)], width=5, font=(FONT_NAME, 12, "bold"), state="readonly")
        self.chart_year_cb.pack(side="left"); self.chart_year_cb.bind("<<ComboboxSelected>>", self.on_chart_date_changed)
        self.chart_month_cb = ttk.Combobox(cb_frame, textvariable=self.chart_month_var, values=[f"{m:02d}" for m in range(1, 13)], width=3, font=(FONT_NAME, 12, "bold"), state="readonly")
        self.chart_month_cb.pack(side="left"); self.chart_month_cb.bind("<<ComboboxSelected>>", self.on_chart_date_changed)
        
        ai_btn = FlatButton(top_frame, text="🤖 AI顧問", font=(FONT_NAME, 12, "bold"), bg="#8E8E93", fg=self.save_text_color)
        ai_btn.command = lambda: [self.visual_feedback(ai_btn), self.ask_ai_advisor()]
        ai_btn.pack(side="right", padx=2, ipady=4, ipadx=4)
        
        export_btn = FlatButton(top_frame, text="📥 匯出", font=(FONT_NAME, 12, "bold"), bg=self.cate_btn_bg, fg=self.save_text_color)
        export_btn.command = lambda: [self.visual_feedback(export_btn), self.export_to_excel()]
        export_btn.pack(side="right", padx=2, ipady=4, ipadx=4)

        self.chart_canvas_frame = tk.Frame(root, bg=self.bg_main); self.chart_canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def ask_ai_advisor(self):
        try: import google.generativeai as genai
        except ImportError:
            messagebox.showerror("錯誤", "請確認套件有安裝：\npip install google-generativeai")
            return

        api_key = self.config.get("gemini_api_key", "")
        if not api_key:
            api_key = simpledialog.askstring("API 金鑰", "請輸入你的 Google Gemini API Key：\n(可在 Google AI Studio 免費獲取)", parent=self.root)
            if not api_key: return
            self.config["gemini_api_key"] = api_key; self.save_config()
        
        y, m = self.chart_year_var.get(), self.chart_month_var.get()
        target = f"{y}-{m}"; ed_data = {}; out_tot = 0; in_tot = 0
        try:
            with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    if r["日期"].startswith(target):
                        amt = float(r["金額"])
                        if r["類型"] == "支出":
                            ed_data[self.clean_old_emoji(r["類別"])] = ed_data.get(self.clean_old_emoji(r["類別"]), 0) + amt
                            out_tot += amt
                        else: in_tot += amt
        except: pass
        
        if out_tot == 0:
            messagebox.showinfo("提示", "這個月還沒花錢，顧問無話可說！"); return

        summary = "、".join([f"{k}花費{v}元" for k, v in ed_data.items()])
        prompt = f"我是一個台灣的大學生，這是我 {y}年{m}月 的記帳資料：總支出 {out_tot} 元，總收入 {in_tot} 元。各項支出包含：{summary}。請扮演一個「毒舌但中肯」的資深財務顧問，用台灣繁體中文，針對我的花費習慣給我一段大約 100 字的無情吐槽與實用理財建議。"

        try:
            genai.configure(api_key=api_key); model = genai.GenerativeModel('gemini-2.5-flash')
            messagebox.showinfo("連線中", "💸 顧問正在審視你慘不忍睹的帳本，請按確認並稍候...")
            response = model.generate_content(prompt)
            messagebox.showinfo("🤖 毒舌顧問的點評", response.text)
        except Exception as e:
            messagebox.showerror("API 錯誤", f"呼叫失敗，請檢查網路或 API Key 是否正確！\n{e}")

    def export_to_excel(self):
        y, m = self.chart_year_var.get(), self.chart_month_var.get()
        target = f"{y}-{m}"
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"記帳報表_{y}年{m}月.csv", title="匯出報表", filetypes=[("Excel 可讀 CSV", "*.csv")])
        if not file_path: return
        try:
            with open(DATA_FILE, "r", encoding="utf-8-sig") as f_in, open(file_path, "w", newline="", encoding="utf-8-sig") as f_out:
                reader = csv.DictReader(f_in); writer = csv.writer(f_out)
                writer.writerow(["日期", "收支類型", "類別", "新台幣金額", "備註說明"]) 
                count = 0
                for r in reader:
                    if r["日期"].startswith(target):
                        writer.writerow([r["日期"], r["類型"], r["類別"], r["金額"], r.get("備註", "")]); count += 1
            messagebox.showinfo("匯出成功", f"成功匯出 {count} 筆紀錄至\n{file_path}\n(可直接用 Excel 開啟)")
        except Exception as e: messagebox.showerror("匯出失敗", str(e))

    def on_chart_date_changed(self, event=None): self.draw_pie_charts(int(self.chart_year_var.get()), int(self.chart_month_var.get()))
    def show_chart_panel(self): self.calendar_frame.pack_forget(); self.fab.place_forget(); self.chart_panel_frame.pack(fill="both", expand=True); self.draw_pie_charts(self.view_year, self.view_month) 
    def hide_chart_panel(self): 
        self.chart_panel_frame.pack_forget(); self.calendar_frame.pack(fill="both", expand=True)
        self.fab.place(relx=0.5, rely=0.92, anchor="center", width=65, height=65); self.refresh_calendar()

    def draw_pie_charts(self, y, m):
        for w in self.chart_canvas_frame.winfo_children(): w.destroy()
        target = f"{y}-{m:02d}"; ed = {}; id = {}
        try:
            with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f); [ (ed.update({self.clean_old_emoji(r["類別"]): ed.get(self.clean_old_emoji(r["類別"]),0)+float(r["金額"])}) if r["類型"]=="支出" else id.update({self.clean_old_emoji(r["類別"]): id.get(self.clean_old_emoji(r["類別"]),0)+float(r["金額"])})) for r in reader if r["日期"].startswith(target)]
        except: pass
        fig = Figure(figsize=(4, 7), facecolor=self.bg_main)
        ax1 = fig.add_subplot(211); ax2 = fig.add_subplot(212)
        title_args = {'fontsize': 14, 'fontweight': 'bold', 'color': self.text_color}
        if ed: ax1.pie(ed.values(), labels=ed.keys(), autopct='%1.1f%%', colors=EXPENSE_COLORS, wedgeprops={'edgecolor': self.bg_main}, textprops={'color': self.text_color}); ax1.set_title("支出結構", fontdict=title_args)
        else: ax1.text(0.5, 0.5, "本月尚無支出", ha='center', color=self.text_muted); ax1.axis('off')
        if id: ax2.pie(id.values(), labels=id.keys(), autopct='%1.1f%%', colors=INCOME_COLORS, wedgeprops={'edgecolor': self.bg_main}, textprops={'color': self.text_color}); ax2.set_title("收入結構", fontdict=title_args)
        else: ax2.text(0.5, 0.5, "本月尚無收入", ha='center', color=self.text_muted); ax2.axis('off')
        fig.tight_layout(); FigureCanvasTkAgg(fig, master=self.chart_canvas_frame).get_tk_widget().pack(fill="both", expand=True)

    def init_add_panel_content(self):
        root = self.add_panel_frame
        top_frame = tk.Frame(root, bg=self.bg_main); top_frame.pack(fill="x", padx=10, pady=(15, 5))
        self.cancel_btn = FlatButton(top_frame, text="◀ 取消", font=(FONT_NAME, 14, "bold"), bg=self.bg_main, fg=self.text_muted)
        self.cancel_btn.command = lambda: [self.visual_feedback(self.cancel_btn), self.hide_add_record_panel()]
        self.cancel_btn.pack(side="left", ipadx=10, ipady=5)
        self.add_date_label = tk.Label(top_frame, text="", bg=self.bg_main, fg=self.text_color, font=(FONT_NAME, 14, "bold")); self.add_date_label.pack(side="left", expand=True)
        self.display_var = tk.StringVar(value="0")
        tk.Label(root, textvariable=self.display_var, font=(FONT_NAME, 40, "bold"), anchor="e", bg=self.display_bg, fg=self.text_color, padx=15, height=2).pack(fill="x", padx=20, pady=(0, 5))
        
        curr_f = tk.Frame(root, bg=self.bg_main); curr_f.pack(fill="x", padx=20)
        self.curr_var = tk.StringVar(value="USD")
        ttk.Combobox(curr_f, textvariable=self.curr_var, values=list(FALLBACK_RATES.keys())[1:], width=5, state="readonly").pack(side="left")
        self.conv_btn = FlatButton(curr_f, text="🔄 換算為 TWD", font=(FONT_NAME, 11, "bold"), bg=self.cate_btn_bg, fg=self.save_text_color)
        self.conv_btn.command = lambda: [self.visual_feedback(self.conv_btn), self.convert_currency_to_twd()]; self.conv_btn.pack(side="right", ipady=4, ipadx=10)
        
        self.status_label = tk.Label(root, text="輸入外幣後點擊換算", bg=self.bg_main, fg=self.text_muted, font=(FONT_NAME, 10)); self.status_label.pack(pady=(5, 5))
        
        type_f = tk.Frame(root, bg=self.bg_main); type_f.pack(fill="x", padx=20, pady=(0, 5)); type_f.columnconfigure(0, weight=1); type_f.columnconfigure(1, weight=1)
        self.out_btn = FlatButton(type_f, text="支出", font=(FONT_NAME, 12, "bold"), bg=self.clear_btn_bg, fg=self.save_text_color)
        self.out_btn.command = lambda: self.set_type("支出"); self.out_btn.grid(row=0, column=0, sticky="nsew", padx=3, ipady=8)
        self.in_btn = FlatButton(type_f, text="收入", font=(FONT_NAME, 12), bg=self.num_btn_bg, fg=self.text_color)
        self.in_btn.command = lambda: self.set_type("收入"); self.in_btn.grid(row=0, column=1, sticky="nsew", padx=3, ipady=8)
        
        note_frame = tk.Frame(root, bg=self.bg_main); note_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(note_frame, text="✎ 備註：", bg=self.bg_main, fg=self.text_muted, font=(FONT_NAME, 11)).pack(side="left")
        self.note_var = tk.StringVar()
        tk.Entry(note_frame, textvariable=self.note_var, font=(FONT_NAME, 12), bg=self.op_btn_bg, fg=self.text_color, insertbackground=self.text_color, relief="flat").pack(side="left", fill="x", expand=True, ipady=4, padx=(5,0))

        calc_f = tk.Frame(root, bg=self.bg_main); calc_f.pack(pady=0, padx=20, fill="both")
        for i in range(4): calc_f.columnconfigure(i, weight=1)
        btns = [
            ['C', self.clear_btn_bg], ['⌫', self.op_btn_bg], ['%', self.op_btn_bg], ['/', self.op_btn_bg],
            ['7', self.num_btn_bg], ['8', self.num_btn_bg], ['9', self.num_btn_bg], ['*', self.op_btn_bg],
            ['4', self.num_btn_bg], ['5', self.num_btn_bg], ['6', self.num_btn_bg], ['-', self.op_btn_bg],
            ['1', self.num_btn_bg], ['2', self.num_btn_bg], ['3', self.num_btn_bg], ['+', self.op_btn_bg],
            ['00', self.num_btn_bg], ['0', self.num_btn_bg], ['.', self.num_btn_bg], ['=', self.cate_btn_bg]
        ]
        for i, (c, cl) in enumerate(btns):
            fg_color = self.save_text_color if cl in [self.clear_btn_bg, self.cate_btn_bg] else self.text_color
            btn = FlatButton(calc_f, text=c, font=("Arial", 16, "bold"), bg=cl, fg=fg_color)
            btn.command = lambda x=c, b=btn: [self.visual_feedback(b), self.on_calc_click(x)]; btn.grid(row=i//4, column=i%4, padx=4, pady=4, sticky="nsew", ipady=6)
            self.btn_dict[c] = btn
        
        self.cate_label_var = tk.StringVar(value="請選擇類別")
        tk.Label(root, textvariable=self.cate_label_var, bg=self.bg_main, fg=self.text_muted).pack(pady=(2, 2))
        self.cate_frame = tk.Frame(root, bg=self.bg_main); self.cate_frame.pack(pady=0, padx=20, fill="both")
        for i in range(4): self.cate_frame.columnconfigure(i, weight=1)
        
        self.update_category_buttons()
        self.save_btn = FlatButton(root, text="完成並儲存", font=(FONT_NAME, 16, "bold"), bg=self.clear_btn_bg, fg=self.save_text_color)
        self.save_btn.command = lambda: self.save_record(); self.save_btn.pack(fill="x", padx=20, pady=5, ipady=10)

    def convert_currency_to_twd(self):
        try:
            val = float(eval(self.expression) if self.expression else 0)
            if val <= 0: return
            self.status_label.config(text="⏳ 取得匯率中...")
            ticker = yf.Ticker(f"{self.curr_var.get()}TWD=X")
            rate = ticker.history(period="1d")['Close'].iloc[-1]
            twd = round(val * rate)
            self.expression = str(twd); self.display_var.set(self.expression)
            self.status_label.config(text=f"✅ 即時匯率 {rate:.4f} ({twd} TWD)", fg=self.cate_btn_bg)
        except: 
            fallback = FALLBACK_RATES.get(self.curr_var.get(), 1)
            twd = round(val * fallback); self.expression = str(twd); self.display_var.set(self.expression)
            self.status_label.config(text=f"⚠️ 離線匯率 {fallback} ({twd} TWD)", fg=self.clear_btn_bg)

    def set_type(self, t):
        self.record_type = t
        self.out_btn.configure(bg=self.clear_btn_bg if t=="支出" else self.num_btn_bg, fg=self.save_text_color if t=="支出" else self.text_color)
        self.in_btn.configure(bg=self.cate_btn_bg if t=="收入" else self.num_btn_bg, fg=self.save_text_color if t=="收入" else self.text_color)
        self.save_btn.configure(bg=self.clear_btn_bg if t=="支出" else self.cate_btn_bg)
        self.update_category_buttons()

    def update_category_buttons(self):
        for w in self.cate_frame.winfo_children(): w.destroy()
        self.category_btns = []; cates = self.config.get("categories", get_default_cates())[self.record_type]
        for i, n in enumerate(cates):
            btn = FlatButton(self.cate_frame, text=n, font=(FONT_NAME, 10), bg=self.display_bg, fg=self.text_color)
            btn.command = lambda x=n, b=btn: self.set_category(x, b); btn.grid(row=i//4, column=i%4, padx=3, pady=3, sticky="nsew", ipady=6)
            self.category_btns.append(btn)
        add_b = FlatButton(self.cate_frame, text="+新增", font=(FONT_NAME, 10, "bold"), bg=self.op_btn_bg, fg=self.text_color)
        add_b.command = self.add_custom_category; add_b.grid(row=len(cates)//4, column=len(cates)%4, padx=3, pady=3, sticky="nsew", ipady=6)

    def add_custom_category(self):
        n = simpledialog.askstring("新增", "名稱：", parent=self.root)
        if n and n not in self.config["categories"][self.record_type]: self.config["categories"][self.record_type].append(n[:6]); self.save_config(); self.update_category_buttons()

    def set_category(self, c, b):
        self.selected_category = c; self.cate_label_var.set(f"已選擇：{c}")
        for btn in self.category_btns: btn.configure(bg=self.display_bg, fg=self.text_color)
        b.configure(bg=self.clear_btn_bg if self.record_type=="支出" else self.cate_btn_bg, fg=self.save_text_color)

    def on_calc_click(self, c):
        self.status_label.config(text="輸入外幣後點擊換算，或直接輸入台幣", fg=self.text_muted)
        if c == 'C': self.expression = ""; self.display_var.set("0")
        elif c == '⌫': self.expression = self.expression[:-1]; self.display_var.set(self.expression if self.expression else "0")
        elif c == '=': 
            try: self.expression = str(eval(self.expression)); self.display_var.set(self.expression)
            except: pass
        elif c == '%':  
            try: self.expression = str(eval(self.expression) / 100); self.display_var.set(self.expression)
            except: pass
        else: self.expression += c; self.display_var.set(self.expression)

    def show_add_record_panel(self):
        self.add_date_label.config(text=self.current_date.strftime("%Y/%m/%d")); self.calendar_frame.pack_forget(); self.fab.place_forget(); self.add_panel_frame.pack(fill="both", expand=True); self.is_add_panel_visible = True

    def hide_add_record_panel(self):
        self.add_panel_frame.pack_forget(); self.calendar_frame.pack(fill="both", expand=True); self.fab.place(relx=0.5, rely=0.92, anchor="center", width=65, height=65)
        self.expression = ""; self.display_var.set("0"); self.note_var.set(""); self.refresh_calendar(); self.is_add_panel_visible = False

    def handle_keypress(self, e):
        if not self.is_add_panel_visible: return
        if e.char in "0123456789+-*/.%" and e.char != "":
            if e.char in self.btn_dict: self.visual_feedback(self.btn_dict[e.char])
            self.on_calc_click(e.char)
        elif e.keysym in ['BackSpace', 'Delete']:
            if '⌫' in self.btn_dict: self.visual_feedback(self.btn_dict['⌫'])
            self.on_calc_click('⌫')
        elif e.keysym == 'Return':
            if '=' in self.btn_dict: self.visual_feedback(self.btn_dict['='])
            self.on_calc_click('=')
        elif e.char.upper() == 'C':
            if 'C' in self.btn_dict: self.visual_feedback(self.btn_dict['C'])
            self.on_calc_click('C')

    def visual_feedback(self, b):
        old = b.cget("bg"); b.configure(bg=self.feedback_color); self.root.after(100, lambda: b.configure(bg=old))

    def save_record(self):
        try:
            amt = float(eval(self.expression))
            if amt <= 0 or not self.selected_category: return
            with open(DATA_FILE, "a", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow([self.current_date.strftime("%Y-%m-%d"), self.record_type, self.selected_category, amt, self.note_var.get().strip()])
            self.hide_add_record_panel()
        except: pass

if __name__ == "__main__":
    root = tk.Tk(); app = CollegeBudgetAppV31_4(root); root.mainloop()