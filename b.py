import os
import json
from collections import Counter
import telebot

# الإعدادات الأساسية
BOT_TOKEN = "7955481997:AAH2hkGqUatciuV_m_EMOno9FA6Ur4LEuO8"
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")
bot = telebot.TeleBot(BOT_TOKEN)
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "5457132722").split(",")]

# تعريف المواد مع عدد الساعات (بما في ذلك مادة "الحاسوب")
subject_credits = {
    "Math": 12,
    "Physics": 12,
    "English": 9,
    "Statistics": 9,
    "Arabic": 6,
    "الحاسوب": 9
}
# ترتيب المواد المطلوب رفع بياناتها بالترتيب
subjects_order = ["Math", "Physics", "English", "Statistics", "Arabic", "الحاسوب"]

grade_mapping = {"F": 0, "D": 0.5, "DD": 1, "C": 1.5, "CC": 2, "B": 2.5, "BB": 3, "A": 3.5, "AA": 4}

# تخزين بيانات درجات المواد: { subject_name: { student_number: grade } }
subject_grades = {}

student_state = {}
allowed_ids = {}  # { student_number: [list of allowed user ids] }

special_student_messages = {
    "12345": "🎉 مبروك! درجاتك مميزة وتستحق الثناء.",
    "67890": "🌟 أداء ممتاز، استمر في التألق!",
}

special_state = {}  # لحالة تعيين رسالة خاصة

# حالة رفع المواد (لتتبع عملية رفع ملف لكل مادة)
# ستُخزن الحالة للمشرف في شكل: { admin_id: {"subjects": [...], "index": 0} }
upload_state = {}

# تحميل البيانات من ملف JSON إذا كانت موجودة
try:
    with open("subject_grades.json", "r") as f:
        subject_grades = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    subject_grades = {}

# دوال المساعدة لحساب المعدلات والإحصائيات (لم يتم تعديلها هنا)
def calculate_gpa(student_number):
    total_credits = 0
    weighted_sum = 0
    for subject in subjects_order:
        if student_number not in subject_grades.get(subject, {}):
            return None
        letter = subject_grades[subject][student_number]
        numeric = grade_mapping.get(letter, 0)
        credits = subject_credits[subject]
        total_credits += credits
        weighted_sum += numeric * credits
    return weighted_sum / total_credits if total_credits > 0 else 0

def get_grade_stats():
    stats = {}
    for subject in subjects_order:
        grades = list(subject_grades.get(subject, {}).values())
        total_students = len(grades)
        if total_students == 0:
            continue
        counts = {}
        percentages = {}
        for grade in grade_mapping.keys():
            count = grades.count(grade)
            counts[grade] = count
            percentages[grade] = (count / total_students) * 100
        stats[subject] = {"counts": counts, "percentages": percentages}
    return stats

def get_top_students(max_rank=10):
    student_gpas = {}
    for student_number in subject_grades.get("Math", {}):
        gpa = calculate_gpa(student_number)
        if gpa is not None:
            student_gpas[student_number] = gpa
    sorted_students = sorted(student_gpas.items(), key=lambda x: x[1], reverse=True)
    top_list = []
    dense_rank = 0
    last_gpa = None
    for student_number, gpa in sorted_students:
        if last_gpa is None or gpa != last_gpa:
            dense_rank += 1
            last_gpa = gpa
        if dense_rank <= max_rank:
            top_list.append((student_number, gpa, dense_rank))
        else:
            break
    return top_list

def get_subject_averages():
    subject_averages = {}
    for subject in subjects_order:
        grades = subject_grades.get(subject, {})
        if not grades:
            continue
        total = sum(grade_mapping.get(grade, 0) for grade in grades.values())
        subject_averages[subject] = total / len(grades)
    return sorted(subject_averages.items(), key=lambda x: x[1], reverse=True)

# أوامر الأدمن الأساسية (الإحصائيات وترتيب الطلاب، الخ) هنا لم نغيرها
@bot.message_handler(commands=['gradestats'])
def grade_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية.")
        return
    stats = get_grade_stats()
    if not stats:
        bot.send_message(message.chat.id, "لا توجد بيانات درجات متاحة.")
        return
    response = "📊 إحصائيات الدرجات:\n"
    for subject, data in stats.items():
        response += f"\n**{subject}:**\n"
        for grade, count in data["counts"].items():
            response += f"- {grade}: {count} طلاب\n"
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(commands=['topstudents'])
def top_students(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية.")
        return
    top_students_list = get_top_students(10)
    if not top_students_list:
        bot.send_message(message.chat.id, "لا توجد بيانات طلاب متاحة.")
        return
    response = "🏆 الطلاب الأوائل:\n"
    for student_number, gpa, rank in top_students_list:
        response += f"{rank}. الطالب {student_number}: GPA {gpa:.2f}\n"
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['subjectranks'])
def subject_ranks(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية.")
        return
    ranked_subjects = get_subject_averages()
    if not ranked_subjects:
        bot.send_message(message.chat.id, "لا توجد بيانات للمواد.")
        return
    response = "📊 ترتيب المواد بناءً على المعدل العام:\n"
    for i, (subject, avg) in enumerate(ranked_subjects, 1):
        response += f"{i}. {subject}: متوسط {avg:.2f}\n"
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['setallowedids'])
def set_allowed_ids(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية.")
        return
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "الاستخدام: /setallowedids <student_number> <chat_id1,chat_id2,...>")
        return
    student_number = args[1]
    chat_ids = args[2].split(',')
    allowed_ids[student_number] = [int(cid) for cid in chat_ids if cid.isdigit()]
    bot.send_message(message.chat.id, f"✅ تم تعيين IDs المسموح لها للطالب {student_number}.")

@bot.message_handler(commands=['setspecial'])
def set_special(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية.")
        return
    special_state[message.from_user.id] = {"state": "awaiting_student_number"}
    bot.send_message(message.chat.id, "🔢 الرجاء إدخال الرقم الدراسي المميز:")

@bot.message_handler(func=lambda message: message.from_user.id in special_state)
def process_special_state(message):
    admin_id = message.from_user.id
    state = special_state[admin_id]
    if state["state"] == "awaiting_student_number":
        student_number = message.text.strip()
        special_state[admin_id] = {"state": "awaiting_message", "student_number": student_number}
        bot.send_message(message.chat.id, f"✅ تم حفظ الرقم الدراسي {student_number}.\nالآن أدخل الرسالة الخاصة لهذا الرقم:")
    elif state["state"] == "awaiting_message":
        special_message = message.text.strip()
        student_number = state["student_number"]
        special_student_messages[student_number] = special_message
        bot.send_message(message.chat.id, f"✅ تم تعيين الرسالة الخاصة للرقم الدراسي {student_number}.")
        del special_state[admin_id]

# أمر بدء رفع درجات المواد لكل مادة بالتتابع
@bot.message_handler(commands=['uploadsubjects'])
def start_upload_subjects(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية.")
        return
    # تهيئة الحالة مع قائمة المواد وترتيبها
    upload_state[message.from_user.id] = {
        "subjects": subjects_order.copy(),
        "index": 0
    }
    current_subject = upload_state[message.from_user.id]["subjects"][0]
    bot.send_message(message.chat.id,
                     f"🔢 يرجى إرسال ملف txt الخاص بمادة: {current_subject}\nالصيغة: رقم دراسي : درجة")

# هنا نستخدم handler خاص للملفات (document) أثناء عملية رفع المواد
@bot.message_handler(content_types=['document'], func=lambda message: message.from_user.id in upload_state)
def process_upload_subject_file(message):
    admin_id = message.from_user.id
    state = upload_state[admin_id]
    subjects_list = state["subjects"]
    current_index = state["index"]
    current_subject = subjects_list[current_index]
    
    if not message.document.file_name.lower().endswith(".txt"):
        bot.send_message(message.chat.id, "❌ يجب أن يكون الملف بصيغة txt.")
        return
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_content = downloaded_file.decode("utf-8")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ حدث خطأ أثناء تحميل الملف.")
        return

    # معالجة الملف وفق التنسيق "رقم دراسي : درجة"
    grades_data = {}
    for line in file_content.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        student_number, grade = line.split(":", 1)
        grades_data[student_number.strip()] = grade.strip()
    
    # حفظ بيانات المادة الحالية
    subject_grades[current_subject] = grades_data
    try:
        with open("subject_grades.json", "w") as f:
            json.dump(subject_grades, f)
    except Exception as e:
        bot.send_message(message.chat.id, "❌ حدث خطأ أثناء حفظ البيانات.")
        return

    bot.send_message(message.chat.id, f"✅ تم رفع بيانات مادة {current_subject} بنجاح.")
    state["index"] += 1
    if state["index"] < len(subjects_list):
        next_subject = subjects_list[state["index"]]
        bot.send_message(message.chat.id,
                         f"🔢 يرجى إرسال ملف txt الخاص بمادة: {next_subject}\nالصيغة: رقم دراسي : درجة")
    else:
        bot.send_message(message.chat.id, "✅ تم رفع بيانات جميع المواد بنجاح.")
        del upload_state[admin_id]

# أوامر الطلاب كما في النسخ السابقة
@bot.message_handler(commands=['start'])
def student_start(message):
    missing_subjects = [subject for subject in subjects_order if subject not in subject_grades or not subject_grades[subject]]
    if missing_subjects:
        bot.send_message(message.chat.id, "⚠ لم يتم رفع درجات جميع المواد بعد. تواصل مع الأدمن.")
        return
    student_state[message.chat.id] = "awaiting_student_number"
    bot.send_message(message.chat.id, "🔢 يرجى إدخال رقم الطالب:")

@bot.message_handler(func=lambda message: message.text and message.text.strip().isdigit())
def process_student_number(message):
    chat_id = message.chat.id
    student_number = message.text.strip()
    
    if student_number in allowed_ids and (message.from_user.id not in allowed_ids[student_number] and message.from_user.id not in ADMIN_IDS):
        bot.send_message(chat_id, "❌ ليس لديك صلاحية لرؤية درجات هذا الطالب.")
        return
    
    if student_number not in subject_grades.get("Math", {}) and message.from_user.id not in ADMIN_IDS:
        bot.send_message(chat_id, "❌ أنت لست في المجموعة 2,7.")
        return
    
    if message.from_user.id not in ADMIN_IDS:
        for subject in subjects_order:
            if student_number not in subject_grades.get(subject, {}):
                bot.send_message(chat_id, "❌ بيانات درجاتك غير مكتملة. أنت لست في المجموعة 2,7.")
                return
    
    response = "📜 درجات الطالب:\n"
    total_credits = 0
    weighted_sum = 0
    complete = True
    for subject in subjects_order:
        if student_number in subject_grades.get(subject, {}):
            letter = subject_grades[subject][student_number]
            numeric = grade_mapping.get(letter, 0)
            credits = subject_credits[subject]
            total_credits += credits
            weighted_sum += numeric * credits
            response += f"• {subject}: {letter} ({numeric:.2f}/4) - الساعات: {credits}\n"
        else:
            complete = False
            response += f"• {subject}: N/A\n"
    
    if complete:
        gpa = weighted_sum / total_credits if total_credits > 0 else 0
        response += f"\n📊 المعدل التراكمي: {gpa:.2f} / 4"
    else:
        response += "\n❗ درجات الطالب غير مكتملة لحساب المعدل التراكمي."
    
    if student_number in special_student_messages:
        response += f"\n\n{special_student_messages[student_number]}"
    
    response += "\n\nأرسل رقم طالب آخر أو اكتب /stop للخروج."
    bot.send_message(chat_id, response)

@bot.message_handler(commands=['stop'])
def stop_student_mode(message):
    chat_id = message.chat.id
    if chat_id in student_state:
        del student_state[chat_id]
    bot.send_message(chat_id, "✅ تم الخروج من وضع الطالب.")

if __name__ == "__main__":
    bot.polling()
