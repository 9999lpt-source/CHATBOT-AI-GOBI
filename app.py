from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import time
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from services.stt_services import GroqSTTService
from services.llm_services import GroqLLMService
from services.tts_services import EdgeTTSService
from services.response_processor import ResponseProcessor

app = FastAPI()

# Khởi tạo các services
stt_service = GroqSTTService()
llm_service = GroqLLMService()
tts_service = EdgeTTSService()
response_processor = ResponseProcessor()

CHUNK_SIZE = 2048 

@app.get("/")
def read_root():
    return {"status": "online", "message": "GOBI Server is running!"}

@app.websocket("/ws/gobi")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[SERVER] ESP32-S3 kết nối thành công! 🔌", flush=True)

    current_pipeline_task: asyncio.Task = None
    audio_queue = asyncio.Queue()
    recording_event = asyncio.Event()

    async def send_signal(sig_type: str, data: dict = None):
        payload = {"signal": sig_type}
        if data:
            payload["data"] = data
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    async def cancel_current_pipeline():
        nonlocal current_pipeline_task
        if current_pipeline_task and not current_pipeline_task.done():
            current_pipeline_task.cancel()
            try:
                await current_pipeline_task
            except asyncio.CancelledError:
                print("🛑 [SERVER]: Đã ngắt chu trình xử lý trước đó.", flush=True)
        current_pipeline_task = None
        recording_event.clear()
        
        while not audio_queue.empty():
            audio_queue.get_nowait()

    async def run_pipeline():
        try:
            print("\n🎤 [RECORDING]: Bắt đầu nhận âm thanh từ ESP32...", flush=True)
            await send_signal("status", {"message": "GOBI đang nghe..."})
            
            audio_frames = []
            
            # Vòng lặp thu âm cho đến khi buông tay (recording_event bị tắt)
            while recording_event.is_set():
                try:
                    chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                    audio_frames.append(chunk)
                except asyncio.TimeoutError:
                    continue

            if not audio_frames:
                print("⚠️ [STT]: Không nhận được dữ liệu âm thanh.", flush=True)
                await send_signal("stop_sig", {"reason": "no_audio"})
                return

            # Chuyển sang STT
            print("🤫 [STT]: Dừng thu âm, bắt đầu dịch giọng nói...", flush=True)
            await send_signal("status", {"message": "GOBI đang dịch giọng nói..."})
            
            user_text = await stt_service.transcribe_audio(audio_frames)
            
            if not user_text or not user_text.strip():
                print("⚠️ [STT]: Không nhận diện được lời nói.", flush=True)
                await send_signal("status", {"message": "Tui chưa nghe rõ, ông nói lại nha!"})
                await send_signal("stop_sig", {"reason": "empty_stt"})
                return

            print(f"\n[LPT (Giọng nói)]: \"{user_text}\"", flush=True)

            # Chuyển sang LLM
            await send_signal("status", {"message": "GOBI đang suy nghĩ..."})
            loop = asyncio.get_running_loop()
            raw_ai_reply = await loop.run_in_executor(None, llm_service.ask, user_text)

            # Bóc tách câu trả lời
            processed_data = response_processor.process(raw_ai_reply)
            print(raw_ai_reply, flush=True)
            commands = processed_data["commands"]
            speech_text = processed_data["speech_text"]

            if commands:
                print(f"⚙️ [COMMANDS]: {commands}", flush=True)
                await send_signal("command", {"actions": commands})

            print(f"[GOBI]: {speech_text}", flush=True)

            # Stream TTS
            if speech_text:
                await send_signal("status", {"message": f"GOBI: {speech_text}"})
                print("🚀 [SERVER]: Đang stream PCM xuống ESP32...", flush=True)
                
                sentences = [s.strip() for s in re.split(r'([.?!;\n]+)', speech_text) if s.strip()]
                
                chunks_to_speak = []
                temp_sentence = ""
                
                for part in sentences:
                    temp_sentence += part
                    if part in [".", "?", "!", ";", "\n"]:
                        chunks_to_speak.append(temp_sentence)
                        temp_sentence = ""
                if temp_sentence:
                    chunks_to_speak.append(temp_sentence)

                total_bytes_sent = 0
                for sentence in chunks_to_speak:
                    if not sentence.strip():
                        continue
                    try:
                        async for pcm_chunk in tts_service.stream_tts_pcm(sentence, chunk_size=CHUNK_SIZE):
                            await asyncio.sleep(0) 
                            await websocket.send_bytes(pcm_chunk)
                            total_bytes_sent += len(pcm_chunk)
                    except Exception as tts_err:
                        print(f"❌ [TTS ERROR]: Lỗi đọc câu \"{sentence[:20]}...\": {tts_err}", flush=True)

                print(f"✅ [SERVER]: Hoàn tất gửi luồng âm thanh PCM! (Tổng: {total_bytes_sent} bytes)", flush=True)

            # Báo hoàn tất chu trình
            await send_signal("stop_sig", {"reason": "completed"})

        except asyncio.CancelledError:
            print("⚠️ [PIPELINE]: Task bị hủy giữa chừng.", flush=True)
            raise
        except Exception as e:
            print(f"❌ [PIPELINE ERROR]: {e}", flush=True)
            await send_signal("stop_sig", {"reason": "error", "message": str(e)})

    # Luồng nhận tin nhắn WebSocket
    try:
        while True:
            message = await websocket.receive()

            if "text" in message and message["text"]:
                text_data = message["text"].strip()
                print(message, flush=True)
                
                sig_type = text_data
                try:
                    parsed_json = json.loads(text_data)
                    sig_type = parsed_json.get("signal", text_data)
                except json.JSONDecodeError:
                    pass

                # --- 1. CHẠM NÚT: BẮT ĐẦU CHU TRÌNH MỚI --- 
                if sig_type == "start_sig":
                    print("\n📩 [SIGNAL]: Nhận 'start_sig' -> Bắt đầu thu âm!", flush=True)
                    await cancel_current_pipeline()
                    recording_event.set()
                    current_pipeline_task = asyncio.create_task(run_pipeline())

                # --- 2. BUÔNG TAY: DỪNG THU ÂM (ĐỂ BẮT ĐẦU DỊCH STT) ---
                elif sig_type == "stop_rec_sig":
                    print("\n📩 [SIGNAL]: Nhận 'stop_rec_sig' -> Buông tay, chốt file audio!", flush=True)
                    recording_event.clear() # Chỉ tắt cờ thu âm, KHÔNG hủy task!

                # --- 3. TÍN HIỆU HỦY KHẨN CẤP (NẾU CÓ) ---
                elif sig_type == "cancel_sig":
                    print("\n📩 [SIGNAL]: Nhận 'cancel_sig' -> Dừng toàn bộ!", flush=True)
                    await cancel_current_pipeline()
                    await send_signal("stop_sig", {"reason": "user_cancelled"})

            elif "bytes" in message and message["bytes"]:
                if recording_event.is_set():
                    await audio_queue.put(message["bytes"])

    except WebSocketDisconnect:
        print("[SERVER] ESP32-S3 đã ngắt kết nối WebSocket. 📴", flush=True)
        await cancel_current_pipeline()
    except Exception as e:
        print(f"[SERVER] Lỗi WebSocket: {e}", flush=True)
        await cancel_current_pipeline()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)