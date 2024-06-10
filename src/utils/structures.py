import dataclasses
from dataclasses import dataclass, field
import datetime


@dataclasses.dataclass
class UserData:
    user_id: int
    username: str
    email: str | None = None
    generations: int = 0
    today_generations: int = 0
    last_generation_date: datetime.datetime | None = None
    messages: list = field(default_factory=lambda: [])
    bot_state: str = field(default_factory=lambda: "default")
    first_message_index: int = 0
    temp_data: dict = field(default_factory=lambda: {})
    stuck_reminder_enabled: bool = field(default_factory=lambda: True)
    bot_role: str = field(default_factory=lambda: 'english tutor')
    reminder_enable: bool = field(default_factory=lambda: True)
    reminders: dict = field(default_factory=lambda: { \
                                                     "days": [], \
                                                     "time": datetime.datetime.combine(datetime.date.today(), datetime.time(hour=12)), \
                                                     "has_been_requested_before": False, \
                                                     "last_reminder_sent": datetime.datetime.combine(datetime.date.today(), datetime.time(hour=0)), \
                                                     "last_reminder_message_id": None})
    user_file_idx: int = field(default_factory=lambda: 0)
    utm_campaign: str | None = field(default_factory=lambda: None)

    def __getitem__(self, item):
        return getattr(self, item)
