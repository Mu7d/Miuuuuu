import telebot

BOT_TOKEN = "7687570987:AAHUH4shgLHV7nARtaklh6TpQnB91PsDmhE"
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 5457132722

# قائمة المواد مع عدد وحداتها (بدون مادة Computer)
subject_credits = {
    "Math": 12,
    "Physics": 12,
    "English": 9,
    "Statistics": 9,
    "Arabic": 6
}
subjects_order = list(subject_credits.keys())

# تحويل الدرجات إلى قيم رقمية (مقياس 4)
grade_mapping = {
    "F": 0, "D": 0.5, "DD": 1, "C": 1.5, "CC": 2,
    "B": 2.5, "BB": 3, "A": 3.5, "AA": 4
}

# قاموس لتخزين بيانات الدرجات لكل مادة
# الشكل: { subject: { student_number: letter_grade, ... }, ... }
subject_grades = {}

# حالة رفع ملفات المواد عند المسؤول (admin)
admin_upload_state = {}

# حالة انتظار إدخال الرقم الدراسي من الطالب
# سيتم تعيينها عند الضغط على /start وتبقى حتى يتوقف الطالب عن إرسال الأرقام
student_state = {}

# ------------------------------
# رفع ملفات المواد (للمسؤول)
# ------------------------------
@bot.message_handler(commands=['uploadsubjects'])
def start_upload_subjects(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Access denied.")
        return
    # بدء رفع الملفات وفق ترتيب المواد
    admin_upload_state["subjects_list"] = subjects_order.copy()
    admin_upload_state["current_index"] = 0
    bot.send_message(
        message.chat.id,
        f"أنا الادمن: ادخل ملف مادة *{admin_upload_state['subjects_list'][0]}*.\n"
        "يُرجى إرسال ملف بصيغة TXT يحتوي على أسطر بالصيغة:\n`student_number: grade`",
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['document'])
def handle_subject_document(message):
    if message.chat.id != ADMIN_ID or "subjects_list" not in admin_upload_state:
        return
    file_name = message.document.file_name
    if not file_name.endswith(".txt"):
        bot.send_message(message.chat.id, "❌ تنسيق الملف غير صالح. يرجى إرسال ملف بصيغة `.txt`.")
        return
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    try:
        text = downloaded_file.decode("utf-8")
    except Exception:
        bot.send_message(message.chat.id, "❌ حدث خطأ في فك تشفير الملف. تأكد أن الملف مشفر بصيغة UTF-8.")
        return

    lines = text.splitlines()
    data = {}
    for line in lines:
        line = line.strip()
        if not line or ':' not in line:
            continue
        parts = line.split(':')
        if len(parts) != 2:
            continue
        student_number = parts[0].strip()
        grade = parts[1].strip().upper()
        if grade not in grade_mapping:
            continue
        data[student_number] = grade

    current_index = admin_upload_state["current_index"]
    current_subject = admin_upload_state["subjects_list"][current_index]
    subject_grades[current_subject] = data

    bot.send_message(
        message.chat.id,
        f"✅ تم رفع ملف مادة *{current_subject}* بنجاح.",
        parse_mode="Markdown"
    )

    admin_upload_state["current_index"] += 1
    if admin_upload_state["current_index"] < len(admin_upload_state["subjects_list"]):
        next_subject = admin_upload_state["subjects_list"][admin_upload_state["current_index"]]
        bot.send_message(
            message.chat.id,
            f"أنا الادمن: ادخل ملف مادة *{next_subject}*.\n"
            "يُرجى إرسال ملف بصيغة TXT يحتوي على أسطر بالصيغة:\n`student_number: grade`",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "✅ تم رفع جميع ملفات المواد بنجاح.")
        admin_upload_state.clear()

# ------------------------------
# بدء التفاعل مع الطالب وحساب الدرجات بناءً على الرقم الدراسي
# ------------------------------
@bot.message_handler(commands=['start'])
def student_start(message):
    chat_id = message.chat.id
    # التأكد من رفع جميع ملفات المواد أولاً
    if any(subject not in subject_grades for subject in subjects_order):
        bot.send_message(chat_id, "⚠ لم يتم رفع جميع ملفات المواد بعد. يرجى التواصل مع المسؤول.")
        return
    student_state[chat_id] = "awaiting_student_number"
    bot.send_message(chat_id, "🔢 من فضلك أدخل رقمك الدراسي:")

@bot.message_handler(func=lambda message: message.text and message.text.strip().isdigit())
def process_student_number(message):
    chat_id = message.chat.id
    student_number = message.text.strip()
    
    # نتحقق من أن الطالب في حالة انتظار إدخال الرقم الدراسي
    if chat_id not in student_state or student_state[chat_id] != "awaiting_student_number":
        return  # تجاهل الرسائل إذا لم يكن في الحالة المطلوبة
    
    # التحقق من وجود الطالب في ملف مادة Math (المادة الأساسية)
    if student_number not in subject_grades.get("Math", {}):
        bot.send_message(chat_id, "❌ أنت لست ضمن مجموعة 2,7.")
        return

    # التحقق من تواجد بيانات الطالب في جميع المواد
    for subject in subjects_order:
        if student_number not in subject_grades.get(subject, {}):
            bot.send_message(chat_id, "❌ بيانات درجاتك غير مكتملة. أنت لست ضمن مجموعة 2,7.")
            return

    # حساب المعدل وعرض الدرجات
    response = "📜 درجاتك:\n"
    total_credits = 0
    weighted_sum = 0
    for subject in subjects_order:
        letter = subject_grades[subject][student_number]
        numeric = grade_mapping.get(letter, 0)
        credits = subject_credits[subject]
        total_credits += credits
        weighted_sum += numeric * credits
        response += f"• {subject}: {letter} ({numeric:.2f}/4) - وحدات: {credits}\n"

    gpa = weighted_sum / total_credits if total_credits > 0 else 0
    response += f"\n📊 معدلك (GPA): {gpa:.2f} / 4"
    bot.send_message(chat_id, response)
    # الحالة تظل محفوظة حتى يتم إيقافها أو إعادة تشغيل /start يدوياً

if __name__ == "__main__":
    bot.polling()