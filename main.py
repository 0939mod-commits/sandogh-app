import flet as ft
import sqlite3
import os

def main(page: ft.Page):
    page.title = "مدیریت صندوق قرض‌الحسنه هوشمند"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.theme = ft.Theme(color_scheme_seed=ft.colors.INDIGO)

    db_path = "sandogh.db"

    # تابع ایمن برای اجرای دستورات دیتابیس بدون ایجاد قفل
    def run_query(query, params=()):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        res = cursor.fetchall()
        conn.commit()
        conn.close()
        return res

    # ایجاد جداول مورد نیاز
    run_query("CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, amount TEXT, monthly TEXT, count TEXT)")
    run_query("CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, filename TEXT, filepath TEXT, installment_num INTEGER)")
    run_query("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, installment_num INTEGER)")

    # ارتقای خودکار دیتابیس‌های قدیمی کاربران (افزودن ستون filepath و installment_num در صورت عدم وجود)
    try:
        run_query("ALTER TABLE receipts ADD COLUMN filepath TEXT")
    except sqlite3.OperationalError:
        pass 
    try:
        run_query("ALTER TABLE receipts ADD COLUMN installment_num INTEGER")
    except sqlite3.OperationalError:
        pass

    # جداکننده سه رقمی
    def format_num(val):
        if not val:
            return "0"
        v = str(val).replace(",", "")
        return "{:,}".format(int(v)) if v.isdigit() else str(val)

    # قالب‌بندی همزمان با تایپ کردن
    def format_val(e):
        val = e.control.value.replace(",", "")
        if val.isdigit():
            e.control.value = "{:,}".format(int(val))
        else:
            e.control.value = val
        page.update()

    # کانتینرها برای صفحات اصلی و جزئیات
    main_view = ft.Column(spacing=15)
    details_view = ft.Column(visible=False, spacing=15)
    selected_mid = None  # ذخیره موقت شناسه عضو انتخاب شده
    uploading_installment_num = None  # ذخیره شماره قسطی که در حال آپلود رسید برای آن هستیم

    # به روز رسانی لیست اعضا با نمایش زنده درصد پیشرفت
    def refresh_list():
        main_view.controls.clear()
        try:
            members = run_query("SELECT id, name, amount, count FROM members")
            for m in members:
                mid = m[0]
                name = m[1]
                amount = m[2]
                total_installments = int(m[3]) if (m[3] and str(m[3]).isdigit()) else 0
                
                # شمارش اقساط پرداخت شده به صورت زنده
                paid_rows = run_query("SELECT id FROM payments WHERE member_id=?", (mid,))
                paid_count = len(paid_rows)

                # محاسبه درصد پیشرفت جهت نمایش در صفحه اصلی
                progress_ratio = paid_count / total_installments if total_installments > 0 else 0.0
                progress_percentage = int(progress_ratio * 100)

                # گرفتن حرف اول اسم برای آواتار
                first_letter = name[0] if name else "👤"

                # ایجاد رویدادهای کلیک مجزا
                def make_delete_click(member_id):
                    return lambda e: delete_member(member_id)

                def make_details_click(member_id):
                    return lambda e: show_details(member_id)

                # ساخت بخش پیشرفت مینیاتوری در کارت اصلی
                subtitle_controls = [
                    ft.Text(
                        f"وام: {format_num(amount)} تومان | اقساط: {paid_count} از {total_installments} پرداخت شده",
                        size=12,
                    )
                ]
                if total_installments > 0:
                    subtitle_controls.append(
                        ft.Row([
                            ft.ProgressBar(value=progress_ratio, color=ft.colors.GREEN_500, height=4, expand=True),
                            ft.Text(f"{progress_percentage}%", size=11, weight="bold", color=ft.colors.GREEN_600)
                        ], spacing=10)
                    )

                main_view.controls.append(
                    ft.Card(
                        elevation=3,
                        content=ft.ListTile(
                            leading=ft.CircleAvatar(
                                content=ft.Text(first_letter, color="white", weight="bold"),
                                bgcolor=ft.colors.PRIMARY,
                            ),
                            title=ft.Text(name, weight="bold", size=16),
                            subtitle=ft.Column(controls=subtitle_controls, spacing=5),
                            trailing=ft.IconButton(
                                icon=ft.icons.DELETE_FOREVER_OUTLINED,
                                icon_color=ft.colors.RED_400,
                                on_click=make_delete_click(mid)
                            ),
                            on_click=make_details_click(mid)
                        )
                    )
                )
        except Exception as ex:
            print(f"Error refreshing list: {ex}")
        page.update()

    # حذف ایمن عضو و تمام داده‌های مربوط به آن
    def delete_member(mid):
        try:
            run_query("DELETE FROM members WHERE id=?", (mid,))
            run_query("DELETE FROM receipts WHERE member_id=?", (mid,))
            run_query("DELETE FROM payments WHERE member_id=?", (mid,))
        except Exception as ex:
            print(f"Error deleting member: {ex}")
        refresh_list()

    # بازگشت به لیست اصلی همراه با بروزرسانی زنده اطلاعات صفحه اول
    def go_back(e):
        nonlocal selected_mid
        selected_mid = None
        main_view.visible = True
        details_view.visible = False
        refresh_list() # فراخوانی مجدد جهت آپدیت آمار در صفحه اصلی

    # باز کردن رسید آپلود شده در ویندوز و اندروید به صورت سازگار و ایمن
    def open_receipt_file(path):
        if path:
            try:
                # اگر سیستم‌عامل متد startfile را دارد (ویندوز)
                if hasattr(os, "startfile"):
                    if os.path.exists(path):
                        os.startfile(path)
                else:
                    # برای اندروید و پلتفرم‌های موبایل از لانچر داخلی فلت استفاده می‌کنیم
                    page.launch_url(f"file://{path}")
            except Exception as ex:
                print(f"Error opening file: {ex}")

    # ذخیره/حذف وضعیت پرداخت قسط در دیتابیس (با بررسی ترتیبی بودن)
    def toggle_installment(member_id, inst_num, checked):
        try:
            if checked:
                # شرط ترتیب: تنها در صورتی فعال می‌شود که قسط اول باشد یا قسط قبلی پرداخت شده باشد
                is_valid = False
                if inst_num == 1:
                    is_valid = True
                else:
                    prev_exists = run_query("SELECT id FROM payments WHERE member_id=? AND installment_num=?", (member_id, inst_num - 1))
                    if prev_exists:
                        is_valid = True
                
                if is_valid:
                    exists = run_query("SELECT id FROM payments WHERE member_id=? AND installment_num=?", (member_id, inst_num))
                    if not exists:
                        run_query("INSERT INTO payments (member_id, installment_num) VALUES (?,?)", (member_id, inst_num))
            else:
                # قانون ترتیبی: اگر تیک قسطی برداشته شود، تمام اقساط بعدی آن هم لغو تیک می‌شوند
                run_query("DELETE FROM payments WHERE member_id=? AND installment_num>=?", (member_id, inst_num))
                # حذف رسیدهای مرتبط با اقساط لغو شده
                run_query("DELETE FROM receipts WHERE member_id=? AND installment_num>=?", (member_id, inst_num))
        except Exception as ex:
            print(f"Error toggling installment: {ex}")

    # نمایش جزئیات و رسیدهای هر عضو (طراحی جدید داشبوردی)
    def show_details(mid):
        nonlocal selected_mid
        selected_mid = mid
        
        main_view.visible = False
        details_view.visible = True
        details_view.controls.clear()
        
        try:
            member_info = run_query("SELECT name, amount, monthly, count FROM members WHERE id=?", (mid,))
            if not member_info:
                go_back(None)
                return
            
            info = member_info[0]
            paid_installment_rows = run_query("SELECT installment_num FROM payments WHERE member_id=?", (mid,))
            paid_installments = {row[0] for row in paid_installment_rows}

            # بارگذاری رسیدهای ثبت شده به تفکیک شماره قسط
            receipt_rows = run_query("SELECT filename, filepath, installment_num FROM receipts WHERE member_id=?", (mid,))
            receipts_by_inst = {row[2]: (row[0], row[1]) for row in receipt_rows if row[2] is not None}

            # محاسبات مالی زنده برای آمار جزئیات
            total_amount = int(info[1]) if info[1] else 0
            monthly_amount = int(info[2]) if info[2] else 0
            total_installments = int(info[3]) if (info[3] and str(info[3]).isdigit()) else 0
            
            paid_count = len(paid_installments)
            total_paid = paid_count * monthly_amount
            remaining_debt = total_amount - total_paid
            if remaining_debt < 0:
                remaining_debt = 0
            
            progress_ratio = paid_count / total_installments if total_installments > 0 else 0.0

            # رنگ‌بندی‌های پویا بر اساس دارک مود / لایت مود
            is_dark = page.theme_mode == ft.ThemeMode.DARK
            text_color = ft.colors.WHITE if is_dark else ft.colors.BLACK
            subtitle_color = ft.colors.GREY_400 if is_dark else ft.colors.GREY_600
            
            blue_bg = ft.colors.BLUE_900 if is_dark else ft.colors.BLUE_50
            green_bg = ft.colors.GREEN_900 if is_dark else ft.colors.GREEN_50
            red_bg = ft.colors.RED_900 if is_dark else ft.colors.RED_50
            
            blue_border = ft.colors.BLUE_700 if is_dark else ft.colors.BLUE_100
            green_border = ft.colors.GREEN_700 if is_dark else ft.colors.GREEN_100
            red_border = ft.colors.RED_700 if is_dark else ft.colors.RED_100

            # ساخت لیست تعاملی و کارتونی وضعیت پرداخت اقساط
            installment_controls = []
            for i in range(1, total_installments + 1):
                is_checked = i in paid_installments
                
                # شرط فعال بودن تیک: قسط اول باشد یا قسط قبلی تیک خورده باشد
                is_enabled = (i == 1) or ((i - 1) in paid_installments)
                
                def make_check_change(inst_num):
                    return lambda e: (toggle_installment(mid, inst_num, e.control.value), show_details(mid))
                
                # دکمه‌های مربوط به رسید این قسط خاص
                receipt_action_buttons = []
                
                if i in receipts_by_inst:
                    # اگر رسید برای این قسط آپلود شده است، آیکون نمایش عکس را فعال کن
                    fname, fpath = receipts_by_inst[i]
                    def make_open_receipt(path):
                        return lambda e: open_receipt_file(path)
                    
                    receipt_action_buttons.append(
                        ft.IconButton(
                            icon=ft.icons.IMAGE_OUTLINED,
                            icon_color=ft.colors.PRIMARY,
                            tooltip=f"نمایش رسید قسط {i} ({fname})",
                            on_click=make_open_receipt(fpath)
                        )
                    )
                elif is_enabled:
                    # اگر قسط فعلی آماده پرداخت است و هنوز رسیدی ندارد، دکمه آپلود را نشان بده
                    def make_upload_click(inst_num):
                        def trigger_upload(e):
                            nonlocal uploading_installment_num
                            uploading_installment_num = inst_num
                            fp.pick_files(allowed_extensions=["jpg", "png", "jpeg"])
                        return trigger_upload
                    
                    receipt_action_buttons.append(
                        ft.IconButton(
                            icon=ft.icons.UPLOAD_FILE,
                            icon_color=ft.colors.INDIGO_400,
                            tooltip=f"آپلود رسید برای قسط {i}",
                            on_click=make_upload_click(i)
                        )
                    )

                # طراحی کارت اختصاصی قسط
                installment_controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Checkbox(
                                label=f"قسط {i}",
                                value=is_checked,
                                disabled=not is_enabled,
                                on_change=make_check_change(i),
                                active_color=ft.colors.GREEN_600
                            ),
                            ft.Row(controls=receipt_action_buttons, spacing=2)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor=green_bg if is_checked else (ft.colors.BLACK12 if not is_enabled else (ft.colors.GREY_900 if is_dark else ft.colors.WHITE)),
                        border_radius=8,
                        border=ft.border.all(1, green_border if is_checked else (ft.colors.GREY_700 if is_dark else ft.colors.GREY_300)),
                        padding=ft.padding.symmetric(horizontal=10, vertical=2),
                        width=180
                    )
                )

            # افزودن ویجت‌های زیبای آمار و پیشرفت به داشبورد جزئیات
            details_view.controls.extend([
                # هدر زیبای پروفایل کاربر
                ft.Row([
                    ft.CircleAvatar(
                        content=ft.Text(info[0][0] if info[0] else "👤", color="white", weight="bold", size=20),
                        bgcolor=ft.colors.PRIMARY,
                        radius=25
                    ),
                    ft.Column([
                        ft.Text(info[0], size=22, weight="bold"),
                        ft.Text("عضو فعال صندوق قرض‌الحسنه", size=12, color=subtitle_color)
                    ], spacing=2)
                ], alignment=ft.MainAxisAlignment.START),
                
                # کارت‌های آمار سه‌گانه با توزیع عالی
                ft.Row([
                    ft.Container(
                        expand=True,
                        content=ft.Column([
                            ft.Text("کل وام", size=11, color=subtitle_color),
                            ft.Text(f"{format_num(info[1])}", size=14, weight="bold", color=text_color)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12, bgcolor=blue_bg, border_radius=10, border=ft.border.all(1, blue_border)
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.Column([
                            ft.Text("پرداخت شده", size=11, color=subtitle_color),
                            ft.Text(f"{format_num(total_paid)}", size=14, weight="bold", color=ft.colors.GREEN_400 if is_dark else ft.colors.GREEN_700)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12, bgcolor=green_bg, border_radius=10, border=ft.border.all(1, green_border)
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.Column([
                            ft.Text("مانده بدهی", size=11, color=subtitle_color),
                            ft.Text(f"{format_num(remaining_debt)}", size=14, weight="bold", color=ft.colors.RED_400 if is_dark else ft.colors.RED_700)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=12, bgcolor=red_bg, border_radius=10, border=ft.border.all(1, red_border)
                    ),
                ], spacing=10),

                # کارت نوار پیشرفت تسویه اقساط
                ft.Card(
                    elevation=2,
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("پیشرفت تسویه وام:", size=13, weight="bold"),
                                ft.Text(f"{int(progress_ratio * 100)}%", size=13, weight="bold", color=ft.colors.GREEN_400 if is_dark else ft.colors.GREEN_700)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.ProgressBar(value=progress_ratio, color=ft.colors.GREEN_500, bgcolor=ft.colors.GREY_700 if is_dark else ft.colors.GREY_200, height=8),
                            ft.Text(f"جزئیات قسط: {info[3]} قسط {format_num(info[2])} تومانی", size=11, color=subtitle_color)
                        ], spacing=8),
                        padding=15
                    )
                ),

                ft.Divider(height=10),
                
                # بخش چک‌باکس‌های پرداخت اقساط
                ft.Text("وضعیت پرداخت اقساط و مدارک رسید (به ترتیب تیک بزنید):", weight="bold", size=15),
                ft.Container(
                    content=ft.Row(controls=installment_controls, wrap=True, spacing=10, run_spacing=10),
                    padding=12,
                    bgcolor=ft.colors.BLACK12 if is_dark else ft.colors.GREY_100,
                    border_radius=12
                ) if installment_controls else ft.Text("تعداد اقساط مشخص نشده است.", color=subtitle_color),
                
                # دکمه‌های ناوبری داخل کانتینر مجزا جهت رفع خطای مارجین Row
                ft.Container(
                    content=ft.Row([
                        ft.ElevatedButton(
                            "بازگشت به لیست",
                            icon=ft.icons.ARROW_BACK,
                            on_click=go_back,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                        )
                    ], alignment=ft.MainAxisAlignment.END),
                    margin=ft.margin.only(top=10)
                )
            ])
        except Exception as ex:
            print(f"Error showing details: {ex}")
            go_back(None)
            
        page.update()

    # مدیریت رویداد فایل پیکر (ثبت رسید به محض انتخاب فایل به قسط مشخص شده)
    def on_file_selected(e: ft.FilePickerResultEvent):
        nonlocal selected_mid, uploading_installment_num
        if e.files and selected_mid is not None and uploading_installment_num is not None:
            file = e.files[0]
            try:
                # ذخیره رسید با درج قسط مربوطه
                run_query(
                    "INSERT INTO receipts (member_id, filename, filepath, installment_num) VALUES (?,?,?,?)",
                    (selected_mid, file.name, file.path, uploading_installment_num)
                )
                # با آپلود موفق رسید، تیک این قسط به صورت خودکار زده شود
                toggle_installment(selected_mid, uploading_installment_num, True)
            except Exception as ex:
                print(f"Error saving receipt: {ex}")
            
            uploading_installment_num = None
            show_details(selected_mid)

    fp = ft.FilePicker(on_result=on_file_selected)
    page.overlay.append(fp)

    # افزودن عضو جدید به دیتابیس
    def add_member_click(e):
        if not n.value:
            return
        
        name_val = n.value
        amount_val = a.value.replace(",", "") if a.value else "0"
        monthly_val = m.value.replace(",", "") if m.value else "0"
        count_val = c.value if c.value else "0"
        
        try:
            run_query(
                "INSERT INTO members (name, amount, monthly, count) VALUES (?,?,?,?)",
                (name_val, amount_val, monthly_val, count_val)
            )
            n.value = ""
            a.value = ""
            m.value = ""
            c.value = ""
            refresh_list()
        except Exception as ex:
            print(f"Error adding member: {ex}")

    # محاسبه خودکار قسط
    def calculate_installment_click(e):
        try:
            amt = int(a.value.replace(",", "")) if a.value else 0
            cnt = int(c.value) if c.value else 1
            if cnt <= 0:
                cnt = 1
            m.value = "{:,}".format(amt // cnt)
            page.update()
        except Exception as ex:
            print(f"Error calculating: {ex}")

    # المان‌های فرم ثبت‌نام شکیل با آیکون‌های راهنما
    n = ft.TextField(label="نام و نام خانوادگی عضو", prefix_icon=ft.icons.PERSON_OUTLINE, border_radius=10)
    a = ft.TextField(label="مبلغ کل وام (تومان)", prefix_icon=ft.icons.MONETIZATION_ON_OUTLINED, on_change=format_val, border_radius=10)
    c = ft.TextField(label="تعداد اقساط (ماه)", prefix_icon=ft.icons.CALENDAR_MONTH_OUTLINED, border_radius=10)
    m = ft.TextField(label="مبلغ هر قسط (تومان)", prefix_icon=ft.icons.PAYMENT_OUTLINED, on_change=format_val, border_radius=10)

    # سیستم تغییر تم (تاریک/روشن) به همراه هماهنگ‌سازی نئون امضا
    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            theme_btn.icon = ft.icons.LIGHT_MODE_ROUNDED
            theme_btn.icon_color = ft.colors.YELLOW_400
            
            # استایل نئونی پررنگ‌تر برای حالت تاریک
            footer.border = ft.border.all(1.5, ft.colors.CYAN_ACCENT_400)
            footer.shadow = ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.colors.CYAN_ACCENT_400)
            footer_text.color = ft.colors.CYAN_ACCENT_400
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_btn.icon = ft.icons.DARK_MODE_ROUNDED
            theme_btn.icon_color = ft.colors.PRIMARY
            
            # استایل ملایم‌تر برای حالت روشن جهت خوانایی بیشتر
            footer.border = ft.border.all(1.2, ft.colors.CYAN_700)
            footer.shadow = ft.BoxShadow(spread_radius=0.5, blur_radius=8, color=ft.colors.CYAN_100)
            footer_text.color = ft.colors.CYAN_800
        
        # بارگذاری مجدد نمای فعلی جهت اعمال تم مگنتیک
        if details_view.visible and selected_mid is not None:
            show_details(selected_mid)
        else:
            refresh_list()
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.icons.DARK_MODE_ROUNDED,
        icon_color=ft.colors.PRIMARY,
        on_click=toggle_theme,
        tooltip="تغییر تم برنامه"
    )

    # امضای زیبای توسعه‌دهنده به صورت نئونی با کلاس
    footer_text = ft.Text(
        "Designed & Developed by Mohammad",
        size=11,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.CYAN_800,
        font_family="Consolas" # فونت برنامه‌نویسی جذاب
    )

    footer = ft.Container(
        content=footer_text,
        alignment=ft.alignment.center,
        border=ft.border.all(1.2, ft.colors.CYAN_700),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=15, vertical=8),
        shadow=ft.BoxShadow(
            spread_radius=0.5,
            blur_radius=8,
            color=ft.colors.CYAN_100,
        ),
        margin=ft.margin.only(top=30, bottom=15),
        width=270,
    )

    # ساختار صفحه اصلی اپلیکیشن
    page.add(
        ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color=ft.colors.PRIMARY, size=35),
                    ft.Column([
                        ft.Text("صندوق قرض‌الحسنه هوشمند", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY),
                        ft.Text("مدیریت بی‌نقص واریزی‌ها، اقساط و مدارک اعضا", size=12, color=ft.colors.GREY_600)
                    ], spacing=2)
                ], alignment=ft.MainAxisAlignment.START),
                theme_btn
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            margin=ft.margin.only(bottom=10, top=10)
        ),
        ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column([
                    ft.Text("ثبت پرونده و عضویت جدید", size=17, weight="bold", color=ft.colors.PRIMARY),
                    n, a, c,
                    ft.Row([
                        ft.ElevatedButton(
                            "محاسبه قسط",
                            icon=ft.icons.CALCULATE_OUTLINED,
                            on_click=calculate_installment_click,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                bgcolor=ft.colors.GREY_100,
                                color=ft.colors.PRIMARY
                            )
                        )
                    ], alignment=ft.MainAxisAlignment.END),
                    m,
                    ft.ElevatedButton(
                        "ثبت نهایی عضو در صندوق",
                        icon=ft.icons.ADD_TASK_ROUNDED,
                        on_click=add_member_click,
                        bgcolor=ft.colors.PRIMARY,
                        color="white",
                        height=45,
                        width=250,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                ], spacing=12),
                padding=20
            )
        ),
        ft.Divider(height=30, thickness=1),
        ft.Text("لیست پرونده‌های فعال صندوق", size=18, weight="bold"),
        main_view,
        details_view,
        footer
    )
    
    refresh_list()

ft.app(target=main)