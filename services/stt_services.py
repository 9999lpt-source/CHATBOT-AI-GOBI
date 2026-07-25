import io
import os
import wave
import time
import requests

# --- CẤU HÌNH ÂM THANH ĐỒNG BỘ VỚI ESP32 ---
CHANNELS = 1        # Mono
SAMPLE_RATE = 16000  # 16kHz
SAMPLE_WIDTH = 2    # 16-bit PCM (2 bytes)

# Lấy chung cấu hình API Key giống hệt bên llm_services của ông
raw_key = os.environ.get("GROQ_API_KEY")
GROQ_API_KEY = f"Bearer {raw_key}" if raw_key else None
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

class GroqSTTService:
    def __init__(self, api_key: str = None):
        """Không cần khởi tạo client phức tạp nữa, dùng requests trực tiếp"""
        pass

    def convert_bytes_to_wav(self, audio_frames: list) -> bytes:
        """Đóng gói mảng bytes thô từ ESP32 thành định dạng WAV ngay trên RAM"""
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(audio_frames))
            
        return wav_buffer.getvalue()

    async def transcribe_audio(self, audio_frames: list) -> str:
        """Gửi dữ liệu âm thanh trực tiếp lên Groq Whisper bằng HTTP POST Requests"""
        if not audio_frames:
            return ""
            
        start_time = time.time()
        print("🤖 [GROQ STT]: Đang gửi trực tiếp dữ liệu âm thanh từ RAM lên API...")
        
        try:
            # 1. Tạo file âm thanh WAV ảo trên RAM
            wav_data = self.convert_bytes_to_wav(audio_frames)
            
            # 2. Cấu hình Headers và Form Data theo chuẩn REST API của Groq
            headers = {
                "Authorization": GROQ_API_KEY # Ăn khớp 100% với định dạng Bearer
            }
            
            # Định dạng payload gửi file và các tham số ép nhận diện tiếng Việt
            files = {
                "file": ("gobi_input.wav", wav_data, "audio/wav")
            }
            data = {
                "model": "whisper-large-v3",
                "language": "vi",
                "temperature": "0.0"
            }

            # 3. Tạo hàm gọi HTTP POST đồng bộ để chạy trong Executor tránh nghẽn WebSocket
            def send_request():
                response = requests.post(GROQ_STT_URL, headers=headers, files=files, data=data)
                response.raise_for_status()
                return response.json()

            # 4. Kích hoạt gửi bất đồng bộ
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, send_request)
            
            latency = time.time() - start_time
            user_text = result.get("text", "")
            
            print(f"✨ [STT SUCCESS] ({latency:.2f}s): \"{user_text}\"")
            return user_text

        except Exception as e:
            print(f"❌ [STT ERROR]: Lỗi khi gửi requests dịch giọng nói: {e}")
            return ""