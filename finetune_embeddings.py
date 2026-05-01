from gensim.models.fasttext import load_facebook_model, save_facebook_model
import fasttext.util

fasttext.util.download_model("el", if_exists="ignore")

model = load_facebook_model("cc.el.300.bin")

sentences = []
with open("embeddings_data_all.txt", "r") as f:
    for line in f:
        sentences.append(line.strip().split())

model.build_vocab(corpus_iterable=sentences, update=True)

model.train(corpus_iterable=sentences, total_examples=len(sentences), epochs=10)

model.save("cypriot_greek_finetuned.model")
save_facebook_model(model, "cypriot_greek_finetuned.bin")
model.wv.save_word2vec_format("cypriot_greek_finetuned.vec", binary=False)
