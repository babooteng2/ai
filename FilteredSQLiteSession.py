import copy
from agents import SQLiteSession


# action 필드만 제거하는 커스텀 세션 (이미지 메시지는 유지)
class FilteredSQLiteSession(SQLiteSession):
    """action 필드만 제거하고 모든 메시지는 유지하는 SQLite 세션"""

    def __init__(self, session_id: str, database: str):
        """부모 클래스 초기화"""
        super().__init__(session_id, database)

    def _remove_action_recursive(self, obj):
        """재귀적으로 action 필드 제거"""
        if isinstance(obj, dict):
            # action 필드 제거
            cleaned = {k: v for k, v in obj.items() if k != "action"}
            # 재귀적으로 모든 값 처리
            return {k: self._remove_action_recursive(v) for k, v in cleaned.items()}
        elif isinstance(obj, list):
            return [self._remove_action_recursive(item) for item in obj]
        else:
            return obj

    async def get_items(self):
        items = await super().get_items()
        # action 필드만 제거하고 모든 메시지 유지
        cleaned_items = [
            self._remove_action_recursive(copy.deepcopy(item)) for item in items
        ]
        return cleaned_items
