from utils.telebot import UnlimitedCallbackData

SuggestCallbackData = UnlimitedCallbackData("suggest", prefix="suggest")
MenuCallbackData = UnlimitedCallbackData("mode", "message_id", prefix="menu_button")
PronunciationCallbackData = UnlimitedCallbackData("action", prefix="pronunciation")
StuckReminderCallbackData = UnlimitedCallbackData("stuck_reminder_enable", prefix="stuck_reminder")
DailyReminderCallbackData = UnlimitedCallbackData("action", prefix="daily_reminder")
DailyReminderSetupScheduleCallbackData = UnlimitedCallbackData("schedule", "message_id", "confirm", prefix="setup_daily_reminder")
DailyReminderSetupScheduleCallbackData2 = UnlimitedCallbackData("schedule", "message_id", "confirm", prefix="setup2_daily_reminder")
RolesCallbackData = UnlimitedCallbackData("role", prefix="roles")
FileUploadCallbackData = UnlimitedCallbackData("bot_state", prefix="file_upload")
