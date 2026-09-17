# Brief-Spec Chronicle video renderer

This optional renderer turns a canonical Project Chronicle into an offline MP4, caption file,
transcript, storyboard, and render receipt. It uses Playwright for deterministic scene images,
Brief-Spec audio for narration, and `ffmpeg`/`ffprobe` for encoding and verification.

Network speech is never selected automatically. Byte determinism is asserted only within the same
Chromium, ffmpeg, renderer, font, and platform fingerprint.
