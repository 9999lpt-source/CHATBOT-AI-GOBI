import edge_tts
import av
import re
import asyncio

VOICE = "vi-VN-HoaiMyNeural"

class EdgeTTSService:
    def __init__(self):
        pass

    async def stream_tts_pcm(self, text: str, chunk_size: int = 2048):
        if not text or not text.strip():
            return
        
        # Tách văn bản dựa theo dấu . ? ! \n
        raw_sentences = re.split(r"[.?!;\n]+", text)
        
        # Lọc các câu có chữ
        chunks_to_speak = [
            s.strip()
            for s in raw_sentences
            if s.strip() and re.search(r"\w+", s)
        ]
        
        # Tính toán thời gian thực của 1 chunk (2048 bytes @ 16kHz 16-bit Mono = 64ms)
        # Hệ số 0.85 (khoảng 54ms) giúp Server chạy nhanh hơn loa chút ít để đệm
        sample_rate = 16000
        chunk_duration = (chunk_size / (sample_rate * 2)) * 0.85 

        for sentence in chunks_to_speak:
            try:
                communicate = edge_tts.Communicate(sentence, VOICE)
                codec = av.CodecContext.create('mp3', 'r')
            
                # Khởi tạo bộ Chuyển đổi Sample Rate về đúng 16000Hz, Mono, 16-bit
                resampler = av.AudioResampler(
                    format='s16',       # 16-bit PCM
                    layout='mono',      # 1 kênh Mono
                    rate=sample_rate    # Ép về 16000 Hz cho ESP32
                )
            
                pcm_buffer = bytearray()

                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        packets = codec.parse(chunk["data"])
                        for packet in packets:
                            frames = codec.decode(packet)
                            for frame in frames:
                                resampled_frames = resampler.resample(frame)
                                for r_frame in resampled_frames:
                                    raw_pcm = r_frame.to_ndarray().tobytes()
                                    pcm_buffer.extend(raw_pcm)

                                    while len(pcm_buffer) >= chunk_size:
                                        yield bytes(pcm_buffer[:chunk_size])
                                        del pcm_buffer[:chunk_size]
                                        # Nhường Event Loop & Điều tiết tốc độ cho ESP32
                                        await asyncio.sleep(chunk_duration)

                # --- 1. FLUSH CODEC (Xả hết các frame MP3 còn đọng) ---
                for packet in codec.parse(None):
                    for frame in codec.decode(packet):
                        resampled_frames = resampler.resample(frame)
                        for r_frame in resampled_frames:
                            pcm_buffer.extend(r_frame.to_ndarray().tobytes())

                # --- 2. FLUSH RESAMPLER (Xả hết các sample PCM còn đọng) ---
                rest_frames = resampler.resample(None)
                if rest_frames:
                    for r_frame in rest_frames:
                        pcm_buffer.extend(r_frame.to_ndarray().tobytes())

                # --- 3. YIELD PHẦN DƯ BỘ ĐỆM CỦA CÂU ---
                while len(pcm_buffer) >= chunk_size:
                    yield bytes(pcm_buffer[:chunk_size])
                    del pcm_buffer[:chunk_size]
                    await asyncio.sleep(chunk_duration)

                if len(pcm_buffer) > 0:
                    yield bytes(pcm_buffer)
                    await asyncio.sleep(chunk_duration)

            except Exception as e:
                print(f"❌ [TTS ERROR]: Lỗi stream TTS câu '{sentence}': {e}", flush=True)