# Internal
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from pedro.brain.modules.telegram import Telegram
# Project
from pedro.data_structures.agenda import Agenda
from pedro.brain.modules.database import Database
from pedro.brain.modules.datetime_manager import DatetimeManager

class AgendaManager:
    """
    Manager class for handling agenda operations.
    Provides methods to create, read, update, and delete agenda items.
    """

    def __init__(self, telegram: Telegram, db_path: str = "database/pedro_database.json"):
        """
        Initialize the AgendaManager with a database connection.

        Args:
            db_path: Path to the database file
        """
        self.db = Database(db_path)
        self.table_name = "agenda"

        asyncio.create_task(self.check_agenda(telegram))

    def add_agenda_item(self, 
                        frequency: str, 
                        created_by: int, 
                        celebrate_at: datetime, 
                        for_chat: int, 
                        message: str = "", 
                        anniversary: str = "") -> Agenda:
        """
        Add a new agenda item to the database.

        Args:
            frequency: Frequency of the event ("annual", "monthly", "once")
            created_by: ID of the user who created the event
            celebrate_at: Date and time to celebrate the event
            for_chat: ID of the chat where the event should be celebrated
            message: Optional message for the event
            anniversary: Optional anniversary information

        Returns:
            The created Agenda object
        """
        # Get all existing agenda items to find the highest ID
        existing_items = self.get_all_agenda_items()

        # Find the highest existing ID
        highest_id = -1
        for item in existing_items:
            try:
                item_id = int(item.id)
                if item_id > highest_id:
                    highest_id = item_id
            except ValueError:
                # Skip items with non-integer IDs (e.g., legacy UUID IDs)
                pass

        # Generate a new sequential ID
        new_id = str(highest_id + 1)

        agenda_item = Agenda(
            id=new_id,
            frequency=frequency,
            created_by=created_by,
            created_at=datetime.now(),
            celebrate_at=celebrate_at,
            for_chat=for_chat,
            message=message,
            anniversary=anniversary,
            last_celebration=None
        )

        # Convert datetime objects to strings for database storage
        agenda_dict = {
            "id": agenda_item.id,
            "frequency": agenda_item.frequency,
            "created_by": agenda_item.created_by,
            "created_at": agenda_item.created_at.isoformat(),
            "celebrate_at": agenda_item.celebrate_at.isoformat(),
            "for_chat": agenda_item.for_chat,
            "message": agenda_item.message,
            "anniversary": agenda_item.anniversary,
            "last_celebration": None
        }

        self.db.insert(self.table_name, agenda_dict)
        return agenda_item

    def get_all_agenda_items(self) -> List[Agenda]:
        """
        Get all agenda items from the database.

        Returns:
            List of Agenda objects
        """
        items = self.db.get_all(self.table_name)
        return [self._dict_to_agenda(item) for item in items]

    def get_agenda_items_for_chat(self, chat_id: int) -> List[Agenda]:
        """
        Get all agenda items for a specific chat.

        Args:
            chat_id: ID of the chat

        Returns:
            List of Agenda objects for the specified chat
        """
        items = self.db.search(self.table_name, {"for_chat": chat_id})
        return [self._dict_to_agenda(item) for item in items]

    def get_agenda_item_by_id(self, item_id: str) -> Optional[Agenda]:
        """
        Get an agenda item by its ID.

        Args:
            item_id: ID of the agenda item

        Returns:
            Agenda object if found, None otherwise
        """
        items = self.db.search(self.table_name, {"id": item_id})
        return self._dict_to_agenda(items[0]) if items else None

    def update_agenda_item(self, item_id: str, data: Dict[str, Any]) -> bool:
        """
        Update an agenda item.

        Args:
            item_id: ID of the agenda item to update
            data: Dictionary with fields to update

        Returns:
            True if the update was successful, False otherwise
        """
        # Convert datetime objects to strings
        if "created_at" in data and isinstance(data["created_at"], datetime):
            data["created_at"] = data["created_at"].isoformat()
        if "celebrate_at" in data and isinstance(data["celebrate_at"], datetime):
            data["celebrate_at"] = data["celebrate_at"].isoformat()
        if "last_celebration" in data and isinstance(data["last_celebration"], datetime):
            data["last_celebration"] = data["last_celebration"].isoformat()

        result = self.db.update(self.table_name, data, {"id": item_id})
        return len(result) > 0

    def delete_agenda_item(self, item_id: str) -> bool:
        """
        Delete an agenda item.

        Args:
            item_id: ID of the agenda item to delete

        Returns:
            True if the deletion was successful, False otherwise
        """
        result = self.db.remove(self.table_name, {"id": item_id})
        return len(result) > 0

    def mark_as_celebrated(self, item_id: str) -> bool:
        """
        Mark an agenda item as celebrated by updating its last_celebration field.

        Args:
            item_id: ID of the agenda item

        Returns:
            True if the update was successful, False otherwise
        """
        return self.update_agenda_item(item_id, {"last_celebration": datetime.now()})

    def get_upcoming_celebrations(self, days_ahead: int = 7) -> List[Agenda]:
        """
        Get upcoming celebrations within the specified number of days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming Agenda items
        """
        all_items = self.get_all_agenda_items()
        now = datetime.now()
        upcoming = []

        for item in all_items:
            # For "once" events, check if the celebration date is within the range
            if item.frequency == "once":
                if now <= item.celebrate_at <= now.replace(hour=23, minute=59, second=59) + timedelta(days=days_ahead):
                    upcoming.append(item)

            # For "annual" events, check if the anniversary is coming up
            elif item.frequency == "annual":
                this_year_date = item.celebrate_at.replace(year=now.year)
                if this_year_date < now:
                    this_year_date = this_year_date.replace(year=now.year + 1)

                if now <= this_year_date <= now.replace(hour=23, minute=59, second=59) + timedelta(days=days_ahead):
                    upcoming.append(item)

            # For "monthly" events, check if the monthly date is coming up
            elif item.frequency == "monthly":
                this_month_date = item.celebrate_at.replace(month=now.month, year=now.year)
                if this_month_date < now:
                    if now.month == 12:
                        this_month_date = this_month_date.replace(month=1, year=now.year + 1)
                    else:
                        this_month_date = this_month_date.replace(month=now.month + 1)

                if now <= this_month_date <= now.replace(hour=23, minute=59, second=59) + timedelta(days=days_ahead):
                    upcoming.append(item)

        return upcoming

    def _dict_to_agenda(self, data: Dict[str, Any]) -> Agenda:
        """
        Convert a dictionary to an Agenda object.

        Args:
            data: Dictionary with agenda data

        Returns:
            Agenda object
        """
        return Agenda(
            id=data["id"],
            frequency=data["frequency"],
            created_by=data["created_by"],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            celebrate_at=datetime.fromisoformat(data["celebrate_at"]) if isinstance(data["celebrate_at"], str) else data["celebrate_at"],
            for_chat=data["for_chat"],
            message=data["message"],
            anniversary=data["anniversary"],
            last_celebration=datetime.fromisoformat(data["last_celebration"]) if data["last_celebration"] and isinstance(data["last_celebration"], str) else data["last_celebration"]
        )

    async def check_agenda(self, telegram: Telegram):
        while True:
            try:
                datetime_manager = DatetimeManager()
                today = datetime_manager.now()

                day = today.day
                month = today.month
                year = today.year

                for entry in self.get_all_agenda_items():
                    string_date = str(entry.celebrate_at).split(' ')[0]

                    if entry.frequency == "monthly":
                        date = datetime.strptime(string_date, "%Y-%m-%d")

                        # For events scheduled on the 31st, we want to trigger on the last day of each month
                        if str(date.day) == "31":
                            # Calculate the last day of the current month
                            last_day_of_month = (datetime(year, month, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                            # Check if today is the last day of the month
                            if day == last_day_of_month.day:
                                if entry.last_celebration is None or entry.last_celebration.month != month:
                                    entry.last_celebration = today
                                    self.mark_as_celebrated(entry.id)

                                    if telegram:
                                        await telegram.send_message(
                                            message_text=entry.message,
                                            chat_id=entry.for_chat
                                        )
                                continue

                            # Calculate the last day of the target month
                            next_month = date.replace(day=28) + timedelta(days=4)
                            date = next_month - timedelta(days=next_month.day)

                        if date.day == day:
                            if entry.last_celebration is None or entry.last_celebration.month != month:
                                entry.last_celebration = today
                                self.mark_as_celebrated(entry.id)

                                if telegram:
                                    await telegram.send_message(
                                        message_text=entry.message,
                                        chat_id=entry.for_chat
                                    )

                    else:
                        date = datetime.strptime(string_date, "%Y-%m-%d")

                        if date.day == day and date.month == month and (
                                (
                                    not entry.frequency == "annual" and date.year == year
                                )
                                or entry.frequency == "annual"
                        ):
                            if entry.last_celebration is None or entry.last_celebration.year != year:
                                entry.last_celebration = today
                                self.mark_as_celebrated(entry.id)

                                if telegram:
                                    if entry.anniversary:
                                        await telegram.send_message(
                                            message_text=f"feliz aniversário {entry.anniversary}\n{entry.message}".upper(),
                                            chat_id=entry.for_chat
                                        )

                                        await telegram.send_video(
                                            video=open(f'gifs/birthday0.mp4', 'rb').read(),
                                            chat_id=entry.for_chat
                                        )
                                    else:
                                        await telegram.send_message(
                                            message_text=entry.message,
                                            chat_id=entry.for_chat
                                        )
            except Exception as exc:
                logging.exception(f"Error in check_agenda: {exc}")

            await asyncio.sleep(10)
