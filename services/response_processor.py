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
        clean_text = raw_llm_text

        # Ví dụ bóc tách các thẻ lệnh dạng [CMD: LED_ON] hoặc [CMD: SERVO_90]
        cmd_matches = re.findall(r'\[CMD:\s*([^\]]+)\]', raw_llm_text)
        if cmd_matches:
            for cmd in cmd_matches:
                commands.append(cmd.strip())
            # Loại bỏ thẻ lệnh khỏi câu thoại để TTS không đọc ra từ [CMD: ...]
            clean_text = re.sub(r'\[CMD:\s*[^\]]+\]', '', clean_text).strip()
        return {
            "commands": commands,
            "speech_text": clean_text
        }