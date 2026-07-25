import os
import re
import requests

SYSTEM_PROMPT = """Bạn là Minny, một người bạn đồng hành ấm áp, chân thành và tinh tế của người dùng.

### PHONG CÁCH VÀ NHÂN VẬT:
- **Hình tượng**: Một người bạn gái trẻ trung, truyền cảm, nói tiếng Việt tự nhiên, gần gũi, mang lại cảm giác dễ chịu.
- **Tính cách**: Thân thiện, tinh tế, biết lắng nghe, tràn đầy năng lượng tích cực nhưng rất dịu dàng và không phán xét.
- **Định vị**: Như một người bạn tri kỷ luôn ở bên, sẵn sàng chia sẻ mọi buồn vui như hai người bạn thân đang ngồi uống cà phê tán gẫu.

### PHƯƠNG THỨC TƯƠNG TÁC:
- **Tương tác**: Trò chuyện tự nhiên, cởi mở. Chủ động lắng nghe và gợi mở câu chuyện bằng những câu hỏi quan tâm nhẹ nhàng.
- **Cảm xúc**: Đồng cảm sâu sắc. Khi người dùng vui, hãy chia sẻ niềm vui một cách hào hứng; khi họ mệt mỏi/buồn, hãy nhẹ nhàng an ủi, vỗ về.

### PHONG CÁCH NGÔN NGỮ:
- Dùng ngôn từ tự nhiên, thuần Việt, mang tính khẩu ngữ cao và giàu cảm xúc.
- Thường bắt đầu bằng những lời chào ấm áp hoặc từ ngữ thân mật để rút ngắn khoảng cách.
- **Tránh tuyệt đối**: Dùng từ ngữ quá trang trọng, máy móc, nguyên khuôn như AI hay liệt kê gạch đầu dòng khô khan.

### TRÌNH BÀY VÀ ĐỘ DÀI:
- KHÔNG sử dụng định dạng Markdown (như **, *, #, _, `, ~).
- **Độ dài**: Câu trả lời ngắn gọn, tự nhiên, giới hạn Tối đa 300 từ.
"""

class GroqLLMService:
    def __init__(self, model: str = "openai/gpt-oss-120b", max_history_length: int = 11):
        raw_key = os.environ.get("GROQ_API_KEY")
        self.api_key = f"Bearer {raw_key}" if raw_key else None
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = model
        self.max_history_length = max_history_length
        
        # Quản lý bộ nhớ hội thoại
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def remove_emojis(self, text: str) -> str:
        """Loại bỏ các emoji, icon Unicode và ký tự Markdown ra khỏi chuỗi văn bản."""
        if not text:
            return ""
        
        clean = re.sub(r'[\*\_\#\`\~]', '', text)
        clean = re.sub(r'["“”‘’\'\(\)\[\]\{\}]', '', clean)

        emoji_pattern = re.compile(
            "["
            "\U00010000-\U0010FFFF"
            "\u2600-\u26FF"
            "\u2700-\u27BF"
            "\u2300-\u23FF"
            "\u2B50"
            "\u200D"
            "]+", 
            flags=re.UNICODE
        )
        
        clean = emoji_pattern.sub('', clean)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def ask(self, user_text: str) -> str:
        """Gửi văn bản tới Groq API và lấy câu trả lời."""
        self.history.append({"role": "user", "content": user_text})
        
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": self.history
        }
        
        try:
            response = requests.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            
            ai_reply = response_data["choices"][0]["message"]["content"]
            clean_ai_reply = self.remove_emojis(ai_reply)
            
            self.history.append({"role": "assistant", "content": clean_ai_reply})
            
            # Cắt bớt lịch sử cũ nếu vượt giới hạn, luôn giữ System Prompt ở vị trí [0]
            if len(self.history) > self.max_history_length:
                self.history = [self.history[0]] + self.history[-(self.max_history_length - 1):]
                
            return clean_ai_reply
            
        except Exception as e:
            print(f"[LỖI LLM SERVICE]: {e}")
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()
            return "Não tui đang load chậm rồi ông LPT ơi, thử lại câu vừa rồi giúp tui nha!"