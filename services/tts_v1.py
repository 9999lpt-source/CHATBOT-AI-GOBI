import io
import asyncio
import edge_tts
import pygame

# --- CẤU HÌNH GIỌNG NÓI TIẾNG VIỆT ---
# Giọng Nam: "vi-VN-HoaiAnNeural" hoặc Giọng Nữ: "vi-VN-NamMinhNeural"
VOICE_ACTOR = "vi-VN-HoaiMyNeural" 

class EdgeTTSService:
    def __init__(self):
        """Khởi tạo bộ phát âm thanh pygame trên RAM"""
        pygame.mixer.init()

    async def get_tts_bytes(self, text: str):
        """Chuyển đổi text thành âm thanh và phát trực tiếp ra loa Laptop"""
        if not text or not text.strip():
            return

        print(f"🔊 [EDGE TTS]: Đang chuyển câu chữ sang giọng nói...")
        
        try:
            # 1. Khởi tạo tiến trình Edge TTS để lấy dữ liệu âm thanh
            communicate = edge_tts.Communicate(text, VOICE_ACTOR)
            audio_buffer = io.BytesIO()

            # 2. Hứng từng luồng bytes âm thanh đổ về và ghi thẳng vào RAM
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            # Đưa con trỏ buffer về đầu file để chuẩn bị đọc
            audio_buffer.seek(0)

            # 3. Sử dụng Pygame Mixer để load dữ liệu bytes và phát ra loa Laptop
            print("🎶 [LAPTOP SPEAKER]: GOBI đang nói qua loa máy tính...")
            pygame.mixer.music.load(audio_buffer, "mp3")
            pygame.mixer.music.play()

            # Chờ cho đến khi loa Laptop phát xong hoàn toàn câu nói mới chạy tiếp
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            print("🤫 [TTS FINISHED]: GOBI đã nói xong.")

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi khi phát âm thanh ra loa laptop: {e}")