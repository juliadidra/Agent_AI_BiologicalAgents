class WahaHelpers:
    def block_group_messages(chat_id) -> bool:
        if "@g" in chat_id:
            return True
        return False