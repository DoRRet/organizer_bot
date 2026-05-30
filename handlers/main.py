from html import escape

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    register_user, add_project, get_projects, get_project, set_project_status, delete_project,
    add_entry, update_entry, get_entries, get_entry, delete_entry
)
from keyboards import (
    main_kb, projects_kb, project_kb, confirm_delete_project_kb,
    entries_kb, entry_detail_kb, confirm_delete_entry_kb, search_results_kb,
    ProjectCB, EntryCB
)

router = Router()

class StateProj(StatesGroup):
    title = State()
    desc = State()

class StateEntry(StatesGroup):
    content = State()
    media = State()

class StateEditEntry(StatesGroup):
    mode = State()
    text = State()
    media = State()

class StateSearch(StatesGroup):
    query = State()

def _media_from_message(message: Message):
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.document:
        return "document", message.document.file_id
    return None, None

def _safe_text(text: str) -> str:
    """Безопасный текст для HTML: экранирует <, >, &, и т.д."""
    if text is None:
        return ""
    return escape(str(text))

def _project_text(p, entries_count: int) -> str:
    title = _safe_text(p["title"] or "")
    status = _safe_text(p["status"] or "")
    desc = _safe_text(p["description"] or "")
    if len(desc) > 120:
        desc = desc[:117] + "..."
    parts = [
        f"<b>📁 {title}</b>",
        f"Статус: <b>{status}</b>",
        f"Заметок: <b>{entries_count}</b>",
    ]
    if desc:
        parts.append(f"Описание: {desc}")
    return "\n".join(parts)

def _note_text(e) -> str:
    content = _safe_text(e["content"] or "")
    created = _safe_text(e["created_at"] or "")
    return (
        f"<b>Заметка</b>\n"
        f"{content}\n\n"
        f"<i>{created}</i>"
    )

async def _safe_edit_or_answer(call: CallbackQuery, text: str, reply_markup=None):
    try:
        await call.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

async def _send_note(message_obj, e, kb):
    caption = _note_text(e)
    mt = e["media_type"]
    mf = e["media_file_id"]
    try:
        if mt == "photo" and mf:
            await message_obj.answer_photo(photo=mf, caption=caption, reply_markup=kb, parse_mode="HTML")
        elif mt == "document" and mf:
            await message_obj.answer_document(document=mf, caption=caption, reply_markup=kb, parse_mode="HTML")
        else:
            await message_obj.answer(caption, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # Fallback: plain text, без HTML
        plain = f"Заметка\n{e['content']}\n\n{e['created_at']}"
        await message_obj.answer(plain, reply_markup=kb)

@router.message(CommandStart())
async def start(message: Message):
    register_user(message.from_user.id, message.from_user.username)
    await message.answer("Привет! Это органайзер проектов и заметок.", reply_markup=main_kb())

@router.message(Command("menu"))
async def menu_cmd(message: Message):
    register_user(message.from_user.id, message.from_user.username)
    await message.answer("Главное меню:", reply_markup=main_kb())

@router.callback_query(F.data == "menu")
async def menu_cb(call: CallbackQuery):
    register_user(call.from_user.id, call.from_user.username)
    await _safe_edit_or_answer(call, "Главное меню:", main_kb())
    await call.answer()

@router.message(Command("add"))
async def quick_add(message: Message, state: FSMContext):
    text = message.text[len("/add"):].strip()
    if not text:
        await message.answer("Используй: /add текст заметки")
        return
    projects = get_projects(message.from_user.id, include_archived=False)
    pid = projects[0]["id"] if projects else add_project(message.from_user.id, "Входящие", "Быстрые заметки")
    eid = add_entry(message.from_user.id, pid, text, "none", None)
    e = get_entry(message.from_user.id, eid)
    if e:
        await _send_note(message, e, entry_detail_kb(e["id"], pid))

@router.callback_query(ProjectCB.filter(F.action == "new"))
async def new_project(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(StateProj.title)
    await call.message.answer("Название проекта:")
    await call.answer()

@router.message(StateProj.title)
async def proj_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Введи название проекта:")
        return
    await state.update_data(title=title)
    await state.set_state(StateProj.desc)
    await message.answer("Описание (можно пропустить):")

@router.message(StateProj.desc)
async def proj_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    title = (data.get("title") or "").strip()
    if not title:
        await message.answer("Ошибка состояния. Начни заново.", reply_markup=main_kb())
        await state.clear()
        return
    desc = (message.text or "").strip()
    pid = add_project(message.from_user.id, title, desc)
    await state.clear()
    p = get_project(message.from_user.id, pid)
    if p:
        await message.answer(_project_text(p, 0), reply_markup=project_kb(pid), parse_mode="HTML")

@router.callback_query(ProjectCB.filter(F.action == "list"))
async def list_projects(call: CallbackQuery):
    projects = get_projects(call.from_user.id, include_archived=False)
    if not projects:
        await _safe_edit_or_answer(call, "Пока нет проектов.", main_kb())
    else:
        await _safe_edit_or_answer(call, "Ваши проекты:", projects_kb(projects))
    await call.answer()

@router.callback_query(ProjectCB.filter(F.action == "archive"))
async def list_archive(call: CallbackQuery):
    projects = get_projects(call.from_user.id, include_archived=True)
    archived = [p for p in projects if p["status"] == "archived"]
    if not archived:
        await _safe_edit_or_answer(call, "Архив пуст.", main_kb())
    else:
        await _safe_edit_or_answer(call, "Архив проектов:", projects_kb(archived))
    await call.answer()

@router.callback_query(ProjectCB.filter(F.action == "open"))
async def open_project(call: CallbackQuery, callback_data: ProjectCB):
    p = get_project(call.from_user.id, callback_data.project_id)
    if not p:
        await call.answer("Проект не найден", show_alert=True)
        return
    entries = get_entries(call.from_user.id, p["id"])
    await _safe_edit_or_answer(call, _project_text(p, len(entries)), project_kb(p["id"]))
    await call.answer()

@router.callback_query(ProjectCB.filter(F.action == "entries"))
async def list_entries(call: CallbackQuery, callback_data: EntryCB):
    entries = get_entries(call.from_user.id, callback_data.project_id)
    if not entries:
        await _safe_edit_or_answer(call, "В этом проекте пока нет заметок.", project_kb(callback_data.project_id))
    else:
        await _safe_edit_or_answer(call, "Заметки проекта:", entries_kb(entries, callback_data.project_id))
    await call.answer()

@router.callback_query(ProjectCB.filter(F.action == "confirm_delete"))
async def confirm_delete_project(call: CallbackQuery, callback_data: ProjectCB):
    await _safe_edit_or_answer(call, "Удалить проект?", confirm_delete_project_kb(callback_data.project_id))
    await call.answer()

@router.callback_query(ProjectCB.filter(F.action == "delete"))
async def delete_proj(call: CallbackQuery, callback_data: ProjectCB):
    delete_project(call.from_user.id, callback_data.project_id)
    await _safe_edit_or_answer(call, "Проект удалён.", main_kb())
    await call.answer()

@router.callback_query(ProjectCB.filter(F.action == "status_done"))
@router.callback_query(ProjectCB.filter(F.action == "status_pause"))
@router.callback_query(ProjectCB.filter(F.action == "status_active"))
@router.callback_query(ProjectCB.filter(F.action == "status_archive"))
async def set_status(call: CallbackQuery, callback_data: ProjectCB):
    pid = callback_data.project_id
    action = callback_data.action
    if action == "status_done":
        set_project_status(call.from_user.id, pid, "done")
    elif action == "status_pause":
        set_project_status(call.from_user.id, pid, "paused")
    elif action == "status_active":
        set_project_status(call.from_user.id, pid, "active")
    elif action == "status_archive":
        set_project_status(call.from_user.id, pid, "archived")
    p = get_project(call.from_user.id, pid)
    if not p:
        await call.answer("Проект не найден", show_alert=True)
        return
    await _safe_edit_or_answer(call, _project_text(p, len(get_entries(call.from_user.id, pid))), project_kb(pid))
    await call.answer()

@router.callback_query(EntryCB.filter(F.action == "new"))
async def new_entry(call: CallbackQuery, state: FSMContext, callback_data: EntryCB):
    await state.clear()
    await state.update_data(project_id=callback_data.project_id)
    await state.set_state(StateEntry.content)
    await call.message.answer("Текст заметки:")
    await call.answer()

@router.message(StateEntry.content)
async def entry_content(message: Message, state: FSMContext):
    content = (message.text or "").strip()
    if not content:
        await message.answer("Текст не может быть пустым. Введи текст заметки:")
        return
    await state.update_data(content=content)
    await state.set_state(StateEntry.media)
    await message.answer("Фото или файл, либо /skip:")

@router.message(StateEntry.media)
async def entry_media(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("project_id")
    content = data.get("content")
    if not pid or not content:
        await message.answer("Ошибка состояния. Начни заново.", reply_markup=main_kb())
        await state.clear()
        return
    if (message.text or "").strip() == "/skip":
        mt, mf = "none", None
    else:
        mt, mf = _media_from_message(message)
        if mt is None:
            await message.answer("Отправь фото/файл или /skip.")
            return
    eid = add_entry(message.from_user.id, pid, content, mt, mf)
    await state.clear()
    e = get_entry(message.from_user.id, eid)
    if e:
        await _send_note(message, e, entry_detail_kb(e["id"], pid))

@router.callback_query(EntryCB.filter(F.action == "open"))
async def open_entry(call: CallbackQuery, callback_data: EntryCB):
    e = get_entry(call.from_user.id, callback_data.entry_id)
    if not e:
        await call.answer("Заметка не найдена", show_alert=True)
        return
    await call.answer()
    await _send_note(call.message, e, entry_detail_kb(e["id"], callback_data.project_id))

@router.callback_query(EntryCB.filter(F.action == "edit"))
async def edit_entry(call: CallbackQuery, state: FSMContext, callback_data: EntryCB):
    e = get_entry(call.from_user.id, callback_data.entry_id)
    if not e:
        await call.answer("Заметка не найдена", show_alert=True)
        return
    await state.clear()
    await state.update_data(entry_id=e["id"], project_id=e["project_id"], old_content=e["content"])
    await state.set_state(StateEditEntry.mode)
    current = "без медиа"
    if e["media_type"] == "photo":
        current = "с фото"
    elif e["media_type"] == "document":
        current = "с файлом"
    await call.message.answer(f"Что изменить?\nТекущий вид: {current}\n\n1) Текст\n2) Медиа\n3) Текст и медиа")
    await call.answer()

@router.message(StateEditEntry.mode)
async def edit_mode(message: Message, state: FSMContext):
    choice = (message.text or "").strip().lower()
    if choice not in {"1", "2", "3", "текст", "медиа", "текст и медиа"}:
        await message.answer("Выбери: 1) Текст 2) Медиа 3) Текст и медиа")
        return
    await state.update_data(choice=choice)
    if choice in {"1", "текст"}:
        await state.set_state(StateEditEntry.text)
        await message.answer("Новый текст заметки:")
    elif choice in {"2", "медиа"}:
        await state.set_state(StateEditEntry.media)
        await message.answer("Новое фото/файл или /skip:")
    else:
        await state.set_state(StateEditEntry.text)
        await message.answer("Новый текст заметки:")

@router.message(StateEditEntry.text)
async def edit_text(message: Message, state: FSMContext):
    data = await state.get_data()
    entry_id = data.get("entry_id")
    project_id = data.get("project_id")
    choice = data.get("choice")
    new_text = (message.text or "").strip()
    if not entry_id or not project_id:
        await message.answer("Ошибка состояния. Начни заново.", reply_markup=main_kb())
        await state.clear()
        return
    if not new_text:
        await message.answer("Текст не может быть пустым.")
        return
    if choice in {"1", "текст"}:
        update_entry(message.from_user.id, entry_id, content=new_text)
        await state.clear()
    else:
        await state.update_data(new_text=new_text)
        await state.set_state(StateEditEntry.media)
        await message.answer("Теперь отправь фото/файл или /skip:")

@router.message(StateEditEntry.media)
async def edit_media(message: Message, state: FSMContext):
    data = await state.get_data()
    entry_id = data.get("entry_id")
    project_id = data.get("project_id")
    choice = data.get("choice")
    new_text = data.get("new_text")
    if not entry_id or not project_id:
        await message.answer("Ошибка состояния. Начни заново.", reply_markup=main_kb())
        await state.clear()
        return
    if choice in {"2", "медиа"}:
        if (message.text or "").strip() == "/skip":
            update_entry(message.from_user.id, entry_id, media_type="none", media_file_id=None)
            await state.clear()
        else:
            mt, mf = _media_from_message(message)
            if mt is None:
                await message.answer("Отправь фото/файл или /skip.")
                return
            update_entry(message.from_user.id, entry_id, media_type=mt, media_file_id=mf)
            await state.clear()
    elif choice in {"3", "текст и медиа"}:
        if not new_text:
            await message.answer("Ошибка состояния. Начни заново.", reply_markup=main_kb())
            await state.clear()
            return
        if (message.text or "").strip() == "/skip":
            update_entry(message.from_user.id, entry_id, content=new_text, media_type="none", media_file_id=None)
            await state.clear()
        else:
            mt, mf = _media_from_message(message)
            if mt is None:
                await message.answer("Отправь фото/файл или /skip.")
                return
            update_entry(message.from_user.id, entry_id, content=new_text, media_type=mt, media_file_id=mf)
            await state.clear()
    e = get_entry(message.from_user.id, entry_id)
    if e:
        await _send_note(message, e, entry_detail_kb(e["id"], project_id))

@router.callback_query(EntryCB.filter(F.action == "confirm_delete"))
async def confirm_delete_entry(call: CallbackQuery, callback_data: EntryCB):
    e = get_entry(call.from_user.id, callback_data.entry_id)
    if not e:
        await call.answer("Заметка не найдена", show_alert=True)
        return
    await _safe_edit_or_answer(call, "Удалить заметку?", confirm_delete_entry_kb(e["id"], e["project_id"]))
    await call.answer()

@router.callback_query(EntryCB.filter(F.action == "delete"))
async def delete_entry_cb(call: CallbackQuery, callback_data: EntryCB):
    delete_entry(call.from_user.id, callback_data.entry_id)
    p = get_project(call.from_user.id, callback_data.project_id)
    if p:
        await _safe_edit_or_answer(call, "Заметка удалена.", project_kb(p["id"]))
    else:
        await _safe_edit_or_answer(call, "Заметка удалена.", main_kb())
    await call.answer()

@router.callback_query(F.data == "search")
async def search_start(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(StateSearch.query)
    await call.message.answer("Введи запрос:")
    await call.answer()

@router.message(StateSearch.query)
async def search_query(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("Запрос не может быть пустым.", reply_markup=main_kb())
        return
    projects = get_projects(message.from_user.id, include_archived=True)
    matched = []
    for p in projects:
        for e in get_entries(message.from_user.id, p["id"]):
            if query.lower() in e["content"].lower():
                matched.append((p, e))
    await state.clear()
    if not matched:
        await message.answer(f"Ничего не найдено по запросу «{query}».", reply_markup=main_kb())
        return
    await message.answer(f"Найдено: {len(matched)}\nВыбери заметку:", reply_markup=search_results_kb(matched))