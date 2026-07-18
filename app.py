import asyncio
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from services.llm_services import ask_groq_ai
from services.stt_services import GroqSTTService
from services.tts_services import EdgeTTSService

app = FastAPI()

stt_service = GroqSTTService()
tts_service = EdgeTTSService()

# Cấu hình kích thước gói tin gửi xuống ESP32 (2048 bytes = 1024 samples 16-bit)
CHUNK_SIZE = 2048 

@app.get("/")
def read_root():
    return {"status": "online", "message": "GOBI Server is running!"}

@app.websocket("/ws/gobi")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[SERVER] ESP32-S3 đã bắt tay kết nối WebSocket thành công! 🔌")
    
    audio_frames = []
    is_recording = False
    last_packet_time = time.time()
    
    try:
        while True:
            try:
                # Chờ nhận gói bytes âm thanh từ Micro ESP32 gửi lên
                audio_bytes = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.1)
                
                if not is_recording:
                    print("\n🎤 [RECORDING]: GOBI bắt đầu nhận luồng âm thanh...")
                    is_recording = True
                    audio_frames = [] 
                    await websocket.send_text("-> GOBI đang nghe...")
                
                audio_frames.append(audio_bytes)
                last_packet_time = time.time()

            except asyncio.TimeoutError:
                pass

            # Cơ chế buông tay (0.5 giây im lặng)
            if is_recording and (time.time() - last_packet_time > 0.5):
                print("🤫 [SILENCE]: Phát hiện ngừng gửi dữ liệu (Buông tay). Bắt đầu dịch...")
                is_recording = False
                await websocket.send_text("-> GOBI đang dịch giọng nói...")
                
                user_text = await stt_service.transcribe_audio(audio_frames)
                audio_frames = [] 
                
                if user_text and user_text.strip():
                    print(f"\n[LPT (Giọng nói)]: \"{user_text}\"")
                    await websocket.send_text("-> GOBI đang suy nghĩ...")
                    
                    # Chạy hàm sync trong executor để không block event loop của FastAPI
                    loop = asyncio.get_running_loop()
                    ai_reply = await loop.run_in_executor(None, ask_groq_ai, user_text)
                    print(f"[GOBI]: {ai_reply}")
                    
                    # Bắn chữ về màn hình OLED trước
                    await websocket.send_text(f"-> GOBI: {ai_reply}")
                    
                    # Tiến hành lấy dữ liệu âm thanh PCM từ Edge-TTS
                    pcm_data = await tts_service.get_tts_bytes(ai_reply)
                    if pcm_data:
                        total_length = len(pcm_data)
                        
                        for i in range(0, total_length, CHUNK_SIZE):
                            chunk = pcm_data[i:i + CHUNK_SIZE]
                            await websocket.send_bytes(chunk)
                            await asyncio.sleep(0.005)
                            
                    else:
                        await websocket.send_text("-> GOBI: Lỗi giọng nói rồi ông ơi!")
                        
                else:
                    print("⚠️ [STT]: Không nhận diện được từ nào hoặc âm thanh trống.")
                    await websocket.send_text("-> GOBI: Tui chưa nghe rõ, ông nói lại nha!")

    except WebSocketDisconnect:
        print("[SERVER] ESP32-S3 đã ngắt kết nối WebSocket. 📴")
    except Exception as e:
        print(f"[SERVER] Có lỗi xảy ra trong kết nối: {e}")
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)