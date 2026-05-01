from gensim.models import FastText
from gensim.models.fasttext import save_facebook_model

sentences = []
with open("embeddings_data_all.txt", "r") as f:
    for line in f:
        sentences.append(line.strip().split())

model = FastText(
    vector_size=300,
    window=5,
    negative=10,
    min_n=1,
    max_n=5,
    sentences=sentences,
    epochs=10,
    sg=0,  # CBOW
)

model.save("cypriot.model")
save_facebook_model(model, "cypriot.bin")
model.wv.save_word2vec_format("cypriot.vec", binary=False)
