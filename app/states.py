from aiogram.fsm.state import State, StatesGroup
class ImageStates(StatesGroup):
    waiting_prompt = State()
    waiting_analysis_photo = State()
