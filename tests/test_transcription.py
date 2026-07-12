def test_transcription_stub():
    from backend.audio.transcriber import transcribe_file
    segs = transcribe_file('dummy.wav')
    assert isinstance(segs, list)
    assert segs and 'text' in segs[0]
