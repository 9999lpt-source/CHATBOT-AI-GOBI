import edge_tts
import av

VOICE = "vi-VN-HoaiMyNeural"

class EdgeTTSService:
    def __init__(self):
        pass

    async def stream_tts_pcm(self, text: str, chunk_size: int = 2048):
        if not text or not text.strip():
            return

        try:
            communicate = edge_tts.Communicate(text, VOICE)
            
            # Khởi tạo Codec và Resampler một lần duy nhất
            codec = av.CodecContext.create('mp3', 'r')
            resampler = av.AudioResampler(
                format='s16',       # 16-bit PCM
                layout='mono',      # Ép về 1 kênh Mono chuẩn cho loa ESP32
                rate=16000          # Ép cứng về 16000 Hz
            )
            
            pcm_buffer = bytearray()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    # Parse các gói MP3 từ Edge-TTS
                    packets = codec.parse(chunk["data"])
                    for packet in packets:
                        frames = codec.decode(packet)
                        for frame in frames:
                            # Resample trực tiếp cả frame sang format 16kHz S16 Mono
                            resampled_frames = resampler.resample(frame)
                            for r_frame in resampled_frames:
                                # Lấy raw bytes từ mảng đệm C nhanh hơn
                                pcm_buffer.extend(r_frame.planes[0].to_bytes())

                                # Đủ kích thước chunk thì yield ngay xuống WebSocket
                                while len(pcm_buffer) >= chunk_size:
                                    yield bytes(pcm_buffer[:chunk_size])
                                    del pcm_buffer[:chunk_size]

            # Xả sạch phần dữ liệu còn dư trong Resampler buffer (mẹo giúp không bị mất chữ cuối)
            rest_frames = resampler.resample(None)
            for r_frame in rest_frames:
                pcm_buffer.extend(r_frame.planes[0].to_bytes())

            # Send nấc cuối cùng nếu còn sót lại vài byte
            while len(pcm_buffer) >= chunk_size:
                yield bytes(pcm_buffer[:chunk_size])
                del pcm_buffer[:chunk_size]
                
            if len(pcm_buffer) > 0:
                yield bytes(pcm_buffer)

        except Exception as e:
            print(f"❌ [TTS ERROR]: Lỗi stream TTS: {e}", flush=True)