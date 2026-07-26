import json
import re

class ResponseProcessor:
    def __init__(self):
        pass

    def process(self, raw_llm_text: str) -> dict:
        """
        Bóc tách câu trả lời từ LLM.
        Trả về dictionary chứa:
        - 'commands': Danh sách các lệnh điều khiển gửi xuống ESP32
        - 'speech_text': Văn bản thoại sạch dùng để stream TTS
        """
        if not raw_llm_text:
            return {"commands": [], "speech_text": ""}

        commands = []
        
        # 1. Bóc tách tất cả các lệnh nằm trong ngoặc vuông [...]
        cmd_matches = re.findall(r'\[(.*?)\]', raw_llm_text)
        if cmd_matches:
            for cmd in cmd_matches:
                if cmd.strip():
                    commands.append(cmd.strip())

        # 2. Xóa TOÀN BỘ các thẻ trong ngoặc vuông [...] khỏi câu thoại (bao gồm cả khoảng trắng thừa đằng sau)
        clean_text = re.sub(r'\[.*?\]\s*', '', raw_llm_text).strip()

        return {
            "commands": commands,
            "speech_text": clean_text
        }