from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class ProjectCB(CallbackData, prefix="p"):
    action: str
    project_id: int = 0

class EntryCB(CallbackData, prefix="e"):
    action: str
    entry_id: int = 0
    project_id: int = 0

def main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Новый проект", callback_data=ProjectCB(action="new").pack())
    kb.button(text="📁 Проекты", callback_data=ProjectCB(action="list").pack())
    kb.button(text="📦 Архив", callback_data=ProjectCB(action="archive").pack())
    kb.button(text="🔎 Поиск", callback_data="search")
    kb.adjust(1)
    return kb.as_markup()

def projects_kb(projects):
    kb = InlineKeyboardBuilder()
    for p in projects:
        kb.button(text=f"📁 {p['title']}", callback_data=ProjectCB(action="open", project_id=p["id"]).pack())
    kb.button(text="⬅️ Меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()

def project_kb(project_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Заметка", callback_data=EntryCB(action="new", project_id=project_id).pack())
    kb.button(text="📄 Заметки", callback_data=ProjectCB(action="entries", project_id=project_id).pack())
    kb.button(text="✅ Завершить", callback_data=ProjectCB(action="status_done", project_id=project_id).pack())
    kb.button(text="⏸ Пауза", callback_data=ProjectCB(action="status_pause", project_id=project_id).pack())
    kb.button(text="▶️ Активен", callback_data=ProjectCB(action="status_active", project_id=project_id).pack())
    kb.button(text="📦 В архив", callback_data=ProjectCB(action="status_archive", project_id=project_id).pack())
    kb.button(text="🗑 Удалить", callback_data=ProjectCB(action="confirm_delete", project_id=project_id).pack())
    kb.button(text="⬅️ Назад", callback_data=ProjectCB(action="list").pack())
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def confirm_delete_project_kb(project_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=ProjectCB(action="delete", project_id=project_id).pack())
    kb.button(text="❌ Отмена", callback_data=ProjectCB(action="open", project_id=project_id).pack())
    kb.adjust(2)
    return kb.as_markup()

def entries_kb(entries, project_id):
    kb = InlineKeyboardBuilder()
    for e in entries:
        title = e["content"][:32].replace("\n", " ")
        kb.button(text=f"📝 {title}", callback_data=EntryCB(action="open", entry_id=e["id"], project_id=project_id).pack())
    kb.button(text="⬅️ Назад", callback_data=ProjectCB(action="open", project_id=project_id).pack())
    kb.adjust(1)
    return kb.as_markup()

def entry_detail_kb(entry_id, project_id, back_to_search=False):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать", callback_data=EntryCB(action="edit", entry_id=entry_id, project_id=project_id).pack())
    kb.button(text="🗑 Удалить", callback_data=EntryCB(action="confirm_delete", entry_id=entry_id, project_id=project_id).pack())
    kb.button(text="⬅️ К заметкам", callback_data=ProjectCB(action="entries", project_id=project_id).pack())
    kb.button(text="⬅️ К проекту", callback_data=ProjectCB(action="open", project_id=project_id).pack())
    if back_to_search:
        kb.button(text="⬅️ К поиску", callback_data="search_back")
    kb.button(text="⬅️ Меню", callback_data="menu")
    kb.adjust(2, 2, 1)
    return kb.as_markup()

def confirm_delete_entry_kb(entry_id, project_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=EntryCB(action="delete", entry_id=entry_id, project_id=project_id).pack())
    kb.button(text="❌ Отмена", callback_data=EntryCB(action="open", entry_id=entry_id, project_id=project_id).pack())
    kb.adjust(2)
    return kb.as_markup()

def search_results_kb(results):
    kb = InlineKeyboardBuilder()
    for p, e in results:
        title = e["content"][:32].replace("\n", " ")
        kb.button(text=f"🔎 {p['title']} • {title}", callback_data=EntryCB(action="open", entry_id=e["id"], project_id=p["id"]).pack())
    kb.button(text="⬅️ Меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()