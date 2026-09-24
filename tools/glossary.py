"""Translations of every eos_invoices message: (de, ru, zh_Hans).

The German, Russian and Simplified Chinese translations are machine-generated and may be inaccurate.
Checked for sense, not by a native speaker - a correction goes here.

The source of truth for the catalogues - tools/translate.py writes these into
the .po files and refuses to run while a message is missing here. Add a new
message here, never in a .po file: the next run would overwrite a hand edit.

EVE jargon stays English in every language: Corporation, Alliance, Main,
Reason, ISK. A term Alliance Auth translates itself (Alliance, Reason,
Corporation) needs the "EVE jargon" context in the code as well, or AA's
catalogue wins and the English never shows.

A short word Alliance Auth translates differently ("Open", "Amount", "Name")
needs the "eos-invoices" context in the code; the translation test in
tests/test_translations.py names every such clash.

Plural forms: de 2, ru 3, zh_Hans 1.
"""

LANGUAGES = ("de", "ru", "zh_Hans")

PLURAL_FORMS = {
    "de": "nplurals=2; plural=(n != 1);",
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    "zh_Hans": "nplurals=1; plural=0;",
}

TRANSLATIONS = {
    "Invoices": ("Rechnungen", "Счета", "账单"),
    "Not installed": ("Nicht installiert", "Не установлено", "未安装"),
    "Alliance": ("Alliance", "Alliance", "Alliance"),
    "Only Corporations in this Alliance see their outstanding payments. Without an Alliance nobody sees anything.": (
        "Nur Corporations dieser Alliance sehen ihre offenen Zahlungen. Ohne Alliance sieht niemand etwas.",
        "Только Corporation из этой Alliance видят свои неоплаченные платежи. Без Alliance никто ничего не видит.",
        "只有此 Alliance 中的 Corporation 能看到其未付款项。未设置 Alliance 时，任何人都看不到内容。",
    ),
    "Configuration": ("Konfiguration", "Конфигурация", "配置"),
    "Field is true": ("Feld ist wahr", "Поле истинно", "字段为真"),
    "Field is not empty": ("Feld ist nicht leer", "Поле не пустое", "字段不为空"),
    "Field equals value": ("Feld entspricht Wert", "Поле равно значению", "字段等于指定值"),
    "Name": ("Name", "Название", "名称"),
    "Enabled": ("Aktiv", "Включено", "已启用"),
    "Model": ("Modell", "Модель", "模型"),
    "The model holding one row per payment, as app_label.ModelName.": (
        "Das Modell mit einer Zeile pro Zahlung, als app_label.ModelName.",
        "Модель, содержащая одну строку на каждый платёж, в формате app_label.ModelName.",
        "每笔款项占一行的模型，格式为 app_label.ModelName。",
    ),
    "Corporation ID field": ("Feld Corporation-ID", "Поле ID Corporation", "Corporation ID 字段"),
    "Field holding the EVE Corporation ID, e.g. corp_id or corporation__corporation_id.": (
        "Feld mit der EVE-Corporation-ID, z. B. corp_id oder corporation__corporation_id.",
        "Поле с ID Corporation в EVE, например corp_id или corporation__corporation_id.",
        "存放 EVE Corporation ID 的字段，例如 corp_id 或 corporation__corporation_id。",
    ),
    "Amount field": ("Feld Betrag", "Поле суммы", "金额字段"),
    "Field holding the amount owed in ISK.": (
        "Feld mit dem geschuldeten Betrag in ISK.",
        "Поле с суммой долга в ISK.",
        "存放应付 ISK 金额的字段。",
    ),
    "Paid field": ("Feld Bezahlt", "Поле оплаты", "已付字段"),
    "Field that tells whether a payment has been made.": (
        "Feld, das angibt, ob eine Zahlung erfolgt ist.",
        "Поле, показывающее, был ли произведён платёж.",
        "表示是否已付款的字段。",
    ),
    "Paid when": ("Bezahlt, wenn", "Оплачено, если", "已付条件"),
    "Paid value": ("Wert für bezahlt", "Значение оплаты", "已付值"),
    'Only for "Field equals value": the value that means paid.': (
        "Nur für „Feld entspricht Wert“: der Wert, der bezahlt bedeutet.",
        "Только для «Поле равно значению»: значение, означающее оплату.",
        "仅用于“字段等于指定值”：表示已付的值。",
    ),
    "Reason": ("Reason", "Reason", "Reason"),
    "Reason to enter with the payment in game. Field names in braces are replaced by their values, with an optional format: {corp_id}/{month:02d}/{year}": (
        "Reason, der bei der Zahlung im Spiel angegeben wird. Feldnamen in geschweiften Klammern werden durch ihre Werte ersetzt, optional mit Format: {corp_id}/{month:02d}/{year}",
        "Reason, который указывается при платеже в игре. Имена полей в фигурных скобках заменяются их значениями, формат необязателен: {corp_id}/{month:02d}/{year}",
        "游戏内付款时填写的 Reason。花括号中的字段名会被替换为其值，可选格式：{corp_id}/{month:02d}/{year}",
    ),
    "Description": ("Beschreibung", "Описание", "描述"),
    "What a row is for, shown next to the amount. Same placeholders as the reason, e.g. {month:02d}/{year}": (
        "Wofür eine Zeile steht, angezeigt neben dem Betrag. Dieselben Platzhalter wie beim Reason, z. B. {month:02d}/{year}",
        "Назначение строки, показывается рядом с суммой. Те же заполнители, что и в Reason, например {month:02d}/{year}",
        "该行的用途，显示在金额旁。占位符与 Reason 相同，例如 {month:02d}/{year}",
    ),
    "Date field": ("Feld Datum", "Поле даты", "日期字段"),
    "Optional date or datetime field; rows are sorted by it, newest first.": (
        "Optionales Datums- oder Zeitstempelfeld; die Zeilen werden danach sortiert, neueste zuerst.",
        "Необязательное поле даты или даты-времени; строки сортируются по нему, сначала новые.",
        "可选的日期或日期时间字段；按其排序，最新的在前。",
    ),
    "Pay to": ("Zahlen an", "Платить", "付款给"),
    "Whom to send the ISK to, e.g. the holding Corporation.": (
        "An wen die ISK gehen, z. B. die Holding-Corporation.",
        "Кому отправлять ISK, например холдинговой Corporation.",
        "ISK 的收款方，例如控股 Corporation。",
    ),
    "The Corporation that receives the ISK. Lists the Corporations of the Alliance chosen on the Alliance tab.": (
        "Die Corporation, die die ISK erhält. Zur Auswahl stehen die Corporations der Alliance, die im Tab Alliance gewählt ist.",
        "Corporation, получающая ISK. В списке — Corporation из Alliance, выбранной на вкладке Alliance.",
        "接收 ISK 的 Corporation。列表为 Alliance 标签页中所选 Alliance 的各个 Corporation。",
    ),
    "Rows of this source cannot be marked as paid here.": (
        "Zeilen dieser Quelle können hier nicht als bezahlt markiert werden.",
        "Строки этого источника нельзя отметить здесь как оплаченные.",
        "此来源的行无法在此标记为已付。",
    ),
    "The payment no longer exists.": (
        "Die Zahlung existiert nicht mehr.",
        "Этот платёж больше не существует.",
        "该款项已不存在。",
    ),
    "Mark this payment as paid?": (
        "Diese Zahlung als bezahlt markieren?",
        "Отметить этот платёж как оплаченный?",
        "将此款项标记为已付？",
    ),
    "Mark as paid": ("Als bezahlt markieren", "Отметить как оплаченный", "标记为已付"),
    "Marked as paid.": ("Als bezahlt markiert.", "Отмечено как оплаченное.", "已标记为已付。"),
    "Marked by": ("Markiert von", "Отметил", "标记人"),
    "Source": ("Quelle", "Источник", "来源"),
    "Row": ("Zeile", "Строка", "行"),
    "Corporation ID": ("Corporation-ID", "ID Corporation", "Corporation ID"),
    "Corporation": ("Corporation", "Corporation", "Corporation"),
    "Payment log entry": ("Protokolleintrag", "Запись журнала", "日志条目"),
    "Payment log": ("Zahlungsprotokoll", "Журнал платежей", "款项日志"),
    "More than %(limit)s open payments; only the newest are shown.": (
        "Mehr als %(limit)s offene Zahlungen; nur die neuesten werden angezeigt.",
        "Более %(limit)s неоплаченных платежей; показаны только самые новые.",
        "未付款项超过 %(limit)s 笔；仅显示最新的。",
    ),
    "This payment is already marked as paid.": (
        "Diese Zahlung ist bereits als bezahlt markiert.",
        "Этот платёж уже отмечен как оплаченный.",
        "此款项已标记为已付。",
    ),
    "All Corporations": ("Alle Corporations", "Все Corporation", "所有 Corporation"),
    "Log": ("Protokoll", "Журнал", "日志"),
    "Payments marked as paid": (
        "Als bezahlt markierte Zahlungen",
        "Платежи, отмеченные как оплаченные",
        "已标记为已付的款项",
    ),
    "Nothing has been marked as paid yet.": (
        "Bisher wurde nichts als bezahlt markiert.",
        "Пока ничего не отмечено как оплаченное.",
        "尚未有任何款项被标记为已付。",
    ),
    "This payment belongs to another Corporation.": (
        "Diese Zahlung gehört zu einer anderen Corporation.",
        "Этот платёж принадлежит другой Corporation.",
        "此款项属于其他 Corporation。",
    ),
    "Mark all as paid": ("Alle als bezahlt markieren", "Отметить все как оплаченные", "全部标记为已付"),
    "No Corporation given.": ("Keine Corporation angegeben.", "Corporation не указана.", "未指定 Corporation。"),
    "Undone": ("Zurückgenommen", "Отменено", "已撤销"),
    "Undone by": ("Zurückgenommen von", "Отменил", "撤销人"),
    "Undone by %(name)s": ("Zurückgenommen von %(name)s", "Отменил %(name)s", "由 %(name)s 撤销"),
    "Undo": ("Zurücknehmen", "Отменить", "撤销"),
    "Undo this and set the payment open again?": (
        "Zurücknehmen und die Zahlung wieder auf offen setzen?",
        "Отменить и снова отметить платёж как неоплаченный?",
        "撤销并将此款项重新设为未付？",
    ),
    "Undone: the payment is open again.": (
        "Zurückgenommen: Die Zahlung ist wieder offen.",
        "Отменено: платёж снова не оплачен.",
        "已撤销：该款项重新变为未付。",
    ),
    "This entry cannot be undone.": (
        "Dieser Eintrag kann nicht zurückgenommen werden.",
        "Эту запись нельзя отменить.",
        "此条目无法撤销。",
    ),
    "The paid field of this source has changed since.": (
        "Das Bezahlt-Feld dieser Quelle wurde inzwischen geändert.",
        "Поле оплаты этого источника с тех пор изменилось.",
        "此来源的已付字段已被更改。",
    ),
    "The payment has been changed since it was marked; it was left as it is.": (
        "Die Zahlung wurde seit dem Markieren geändert; sie bleibt unverändert.",
        "Платёж изменился после отметки; он оставлен без изменений.",
        "该款项在标记后已被更改；保持不变。",
    ),
    "Select all": ("Alle auswählen", "Выбрать все", "全选"),
    "Mark selected as paid": ("Auswahl als bezahlt markieren", "Отметить выбранные как оплаченные", "将所选标记为已付"),
    "Mark the selected payments as paid?": (
        "Die ausgewählten Zahlungen als bezahlt markieren?",
        "Отметить выбранные платежи как оплаченные?",
        "将所选款项标记为已付？",
    ),
    "Nothing was selected.": ("Es wurde nichts ausgewählt.", "Ничего не выбрано.", "未选择任何内容。"),
    "The texts of this app are machine-generated and may be inaccurate.": (
        "Die Texte dieser App sind maschinell erzeugt und können ungenau sein.",
        "Тексты этого приложения созданы автоматически и могут быть неточными.",
        "本应用的文本由机器生成，可能不准确。",
    ),
    "Payment source": ("Zahlungsquelle", "Источник платежей", "款项来源"),
    "Payment sources": ("Zahlungsquellen", "Источники платежей", "款项来源"),
    "You have no main character.": (
        "Du hast keinen Main Character.",
        "У вас нет Main-персонажа.",
        "你没有 Main 角色。",
    ),
    "No Alliance has been configured for this app yet.": (
        "Für diese App wurde noch keine Alliance eingerichtet.",
        "Для этого приложения ещё не настроена Alliance.",
        "此应用尚未配置 Alliance。",
    ),
    "%(corporation)s is not a member of %(alliance)s.": (
        "%(corporation)s ist kein Mitglied von %(alliance)s.",
        "%(corporation)s не состоит в %(alliance)s.",
        "%(corporation)s 不是 %(alliance)s 的成员。",
    ),
    "Unknown model %(label)s.": (
        "Unbekanntes Modell %(label)s.",
        "Неизвестная модель %(label)s.",
        "未知模型 %(label)s。",
    ),
    "Invalid field name %(name)s.": (
        "Ungültiger Feldname %(name)s.",
        "Недопустимое имя поля %(name)s.",
        "无效的字段名 %(name)s。",
    ),
    "%(model)s has no field %(field)s. Available: %(fields)s": (
        "%(model)s hat kein Feld %(field)s. Vorhanden: %(fields)s",
        "У %(model)s нет поля %(field)s. Доступны: %(fields)s",
        "%(model)s 没有字段 %(field)s。可用字段：%(fields)s",
    ),
    "%(field)s is not a relation and cannot be followed.": (
        "%(field)s ist keine Relation und kann nicht verfolgt werden.",
        "%(field)s не является связью, по нему нельзя перейти.",
        "%(field)s 不是关联字段，无法继续访问。",
    ),
    "%(field)s points at many rows; only single relations can be followed.": (
        "%(field)s verweist auf viele Zeilen; nur Einzelrelationen können verfolgt werden.",
        "%(field)s указывает на множество строк; переходить можно только по одиночным связям.",
        "%(field)s 指向多行；只能访问单一关联。",
    ),
    "%(path)s ends at a relation. Name a field on it, e.g. %(path)s__%(example)s.": (
        "%(path)s endet an einer Relation. Gib ein Feld darauf an, z. B. %(path)s__%(example)s.",
        "%(path)s заканчивается на связи. Укажите её поле, например %(path)s__%(example)s.",
        "%(path)s 止于一个关联。请指定其字段，例如 %(path)s__%(example)s。",
    ),
    "Malformed template: %(error)s": (
        "Fehlerhafte Vorlage: %(error)s",
        "Некорректный шаблон: %(error)s",
        "模板格式错误：%(error)s",
    ),
    "Invalid placeholder {%(name)s}. Use a field name with an optional format.": (
        "Ungültiger Platzhalter {%(name)s}. Verwende einen Feldnamen mit optionalem Format.",
        "Недопустимый заполнитель {%(name)s}. Используйте имя поля с необязательным форматом.",
        "无效的占位符 {%(name)s}。请使用字段名，可附加格式。",
    ),
    "The Corporation ID field must be an integer field.": (
        "Das Feld Corporation-ID muss ein Ganzzahlfeld sein.",
        "Поле ID Corporation должно быть целочисленным.",
        "Corporation ID 字段必须是整数字段。",
    ),
    "The amount field must be a number field.": (
        "Das Feld Betrag muss ein Zahlenfeld sein.",
        "Поле суммы должно быть числовым.",
        "金额字段必须是数字字段。",
    ),
    '"Field is true" needs a boolean field.': (
        "„Feld ist wahr“ braucht ein boolesches Feld.",
        "«Поле истинно» требует логического поля.",
        "“字段为真”需要布尔字段。",
    ),
    "Enter the value that means paid.": (
        "Gib den Wert an, der bezahlt bedeutet.",
        "Укажите значение, означающее оплату.",
        "请输入表示已付的值。",
    ),
    "The date field must be a date or datetime field.": (
        "Das Feld Datum muss ein Datums- oder Zeitstempelfeld sein.",
        "Поле даты должно быть полем даты или даты-времени.",
        "日期字段必须是日期或日期时间字段。",
    ),
    "Overview": ("Übersicht", "Обзор", "概览"),
    "Sources": ("Quellen", "Источники", "来源"),
    "Outstanding": ("Offen", "К оплате", "未付"),
    "Outstanding only": ("Nur offene", "Только неоплаченные", "仅未付"),
    "Including paid": ("Inklusive bezahlte", "Включая оплаченные", "包括已付"),
    "This source cannot be read at the moment.": (
        "Diese Quelle kann derzeit nicht gelesen werden.",
        "Этот источник сейчас недоступен для чтения.",
        "此来源暂时无法读取。",
    ),
    "Nothing outstanding.": ("Nichts offen.", "Задолженностей нет.", "没有未付款项。"),
    "Date": ("Datum", "Дата", "日期"),
    "Amount": ("Betrag", "Сумма", "金额"),
    "Status": ("Status", "Статус", "状态"),
    "Copy": ("Kopieren", "Копировать", "复制"),
    "Paid": ("Bezahlt", "Оплачено", "已付"),
    "Open": ("Offen", "Открыто", "未付"),
    "No payment sources are configured.": (
        "Es sind keine Zahlungsquellen eingerichtet.",
        "Источники платежей не настроены.",
        "尚未配置款项来源。",
    ),
    "Save": ("Speichern", "Сохранить", "保存"),
    "Add source": ("Quelle hinzufügen", "Добавить источник", "添加来源"),
    "Fields": ("Felder", "Поля", "字段"),
    "Field names of the chosen model. Related models are reached with a double underscore, as in a Django query.": (
        "Feldnamen des gewählten Modells. Verknüpfte Modelle erreicht man mit doppeltem Unterstrich, wie in einer Django-Abfrage.",
        "Имена полей выбранной модели. Связанные модели доступны через двойное подчёркивание, как в запросе Django.",
        "所选模型的字段名。与 Django 查询相同，用双下划线访问关联模型。",
    ),
    "Display": ("Anzeige", "Отображение", "显示"),
    "Cancel": ("Abbrechen", "Отмена", "取消"),
    "Each source is a model of another app with one row per payment a Corporation owes. The overview reads every enabled source for the Corporation of the viewer's main character.": (
        "Jede Quelle ist ein Modell einer anderen App mit einer Zeile pro Zahlung, die eine Corporation schuldet. Die Übersicht liest jede aktive Quelle für die Corporation des Main Characters des Betrachters.",
        "Каждый источник — это модель другого приложения, где каждая строка — платёж, который должна Corporation. Обзор читает все включённые источники для Corporation Main-персонажа пользователя.",
        "每个来源都是另一个应用的模型，每行代表一笔 Corporation 应付的款项。概览会读取所有已启用的来源，针对查看者 Main 角色所在的 Corporation。",
    ),
    "Disabled": ("Deaktiviert", "Отключено", "已停用"),
    "Delete %(name)s?": ("%(name)s löschen?", "Удалить %(name)s?", "删除 %(name)s？"),
    "Saved %(name)s.": ("%(name)s gespeichert.", "%(name)s сохранён.", "已保存 %(name)s。"),
    "Deleted %(name)s.": ("%(name)s gelöscht.", "%(name)s удалён.", "已删除 %(name)s。"),
    "Settings saved.": ("Einstellungen gespeichert.", "Настройки сохранены.", "设置已保存。"),
}

PLURALS = {
    "Mark %(counter)s payment of %(corporation)s in %(source)s as paid?": (
        [
            "%(counter)s Zahlung von %(corporation)s in %(source)s als bezahlt markieren?",
            "Alle %(counter)s Zahlungen von %(corporation)s in %(source)s als bezahlt markieren?",
        ],
        [
            "Отметить %(counter)s платёж %(corporation)s в %(source)s как оплаченный?",
            "Отметить все %(counter)s платежа %(corporation)s в %(source)s как оплаченные?",
            "Отметить все %(counter)s платежей %(corporation)s в %(source)s как оплаченные?",
        ],
        ["将 %(corporation)s 在 %(source)s 中的全部 %(counter)s 笔款项标记为已付？"],
    ),
    "Marked %(count)s payment as paid.": (
        ["%(count)s Zahlung als bezahlt markiert.", "%(count)s Zahlungen als bezahlt markiert."],
        [
            "%(count)s платёж отмечен как оплаченный.",
            "%(count)s платежа отмечены как оплаченные.",
            "%(count)s платежей отмечены как оплаченные.",
        ],
        ["已将 %(count)s 笔款项标记为已付。"],
    ),
    "%(count)s payment was skipped: already paid, gone or of another Corporation.": (
        [
            "%(count)s Zahlung übersprungen: bereits bezahlt, nicht mehr vorhanden oder von einer anderen Corporation.",
            "%(count)s Zahlungen übersprungen: bereits bezahlt, nicht mehr vorhanden oder von einer anderen Corporation.",
        ],
        [
            "%(count)s платёж пропущен: уже оплачен, удалён или принадлежит другой Corporation.",
            "%(count)s платежа пропущены: уже оплачены, удалены или принадлежат другой Corporation.",
            "%(count)s платежей пропущены: уже оплачены, удалены или принадлежат другой Corporation.",
        ],
        ["已跳过 %(count)s 笔款项：已付、已不存在或属于其他 Corporation。"],
    ),
    "%(counter)s Corporation with nothing outstanding": (
        ["%(counter)s Corporation ohne offene Zahlungen", "%(counter)s Corporations ohne offene Zahlungen"],
        [
            "%(counter)s Corporation без задолженностей",
            "%(counter)s Corporation без задолженностей",
            "%(counter)s Corporation без задолженностей",
        ],
        ["%(counter)s 个 Corporation 没有未付款项"],
    ),
    "%(counter)s row": (
        ["%(counter)s Zeile", "%(counter)s Zeilen"],
        ["%(counter)s строка", "%(counter)s строки", "%(counter)s строк"],
        ["%(counter)s 行"],
    ),
}
