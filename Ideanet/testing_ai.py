from app.ai import embed, cosine, ask_gemma

# Test 1: embeddings work and have the right size
v = embed("hello world")
print("vector length:", len(v))           # expect 768

# Test 2: similar meanings score higher than different meanings
a = embed("An app that tracks calories using photos of your food")
b = embed("A calorie counter that uses your phone camera")
c = embed("A multiplayer space shooter game")
print("similar pair:  ", round(cosine(a, b), 3))   # expect high (roughly 0.75+)
print("different pair:", round(cosine(a, c), 3))   # expect clearly lower

# Test 3: Gemma returns parseable JSON
print(ask_gemma('Reply ONLY as JSON: {"ok": true, "word": "<any fruit>"}'))