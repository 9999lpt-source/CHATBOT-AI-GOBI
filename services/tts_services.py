import edge_tts
import av
import asyncio

VOICE = "vi-VN-HoaiMyNeural"

class EdgeTTSService:
    def __init__(self):
        pass

    async def stream_tts_pcm(self, text: str, chunk_size: int = 2048):
        if not text or not text.strip():
            return
        
        sample_rate = 16000
        # 2048 bytes / (16000 * 2) = 0.064s (64ms)
        # Giảm sleep xuống 0.045s để đẩy dữ liệu mượt hơn, giảm khoảng trống giữa các từ
        chunk_duration = 0.045 

        try:
            # 1. Chỉ khởi tạo 1 kết nối DUY NHẤT cho toàn bộ văn bản
            communicate = edge_tts.Communicate(text.strip(), VOICE)
            codec = av.CodecContext.create('mp3', 'r')
            
            resampler = av.AudioResampler(
                format='s16',
                layout='mono',
                rate=sample_rate
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
                                    await asyncio.sleep(chunk_duration)

            # --- FLUSH CODEC & RESAMPLER KHI KẾT THÚC CẢ ĐOẠN ---
            for packet in codec.parse(None):
                for frame in codec.decode(packet):
                    resampled_frames = resampler.resample(frame)
                    for r_frame in resampled_frames:
                        pcm_buffer.extend(r_frame.to_ndarray().tobytes())

            rest_frames = resampler.resample(None)
            if rest_frames:
                for r_frame in rest_frames:
                    pcm_buffer.extend(r_frame.to_ndarray().tobytes())

            # Yield hết phần còn lại
            while len(pcm_buffer) >= chunk_size:
                yield bytes(pcm_buffer[:chunk_size])
                del pcm_buffer[:chunk_size]
                await asyncio.sleep(chunk_duration)

            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)
                # Không cần sleep ở gói cuối cùng nữa để kết thúc tức thì

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi stream TTS: {e}", flush=True)