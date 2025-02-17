import flair
from flair.data import Sentence
from flair.embeddings import WordEmbeddings

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer

import torch
from tqdm import tqdm, trange

class AutoencodingDataset(torch.utils.data.Dataset):

  def __init__(self,
               sentences,
               augment=False,
               max_len=256,
               embedding=WordEmbeddings('glove'),
               classes=None):
    
    self.max_len = max_len
    self.embedding = embedding
    self.sentences = sentences
    self.augment = augment
    self.embedding_size = None
    self.classes = classes

  def set_max_len(self, max_len):
    self.max_len = max_len

  def set_embedding(self, embedding):
    self.embedding = embedding

  def set_sentences(self, sentences):
    self.sentences = sentences

  def get_max_len(self):
    return self.max_len

  def get_embedding(self):
    return self.embedding

  def get_sentences(self):
    return self.sentences

  def prepare_sentences(self):
    for i in trange(len(self.sentences)):
      self.sentences[i] = self.prep(self.sentences[i])
  
  def make_sentences(self):
    for i in trange(len(self.sentences)):
      self.sentences[i] = Sentence(self.sentences[i])

  def embed_sentences(self):
    for s in tqdm(self.sentences):
      self.embedding.embed(s)
    self.embedding_size = self.sentences[0][0].embedding.shape[0]

  def split_sentences(self):
    if self.classes:
      temp = []
      temp_classes = []
      for s, c in tqdm(zip(self.sentences, self.classes)):
        i = 1
        while len(s)//i > self.max_len:
          i += 1
        itl = len(s)//i
        for j in range(i):
          temp.append(s[j*itl:(j+1)*itl])
          temp_classes.append(c)
      self.classes = temp_classes
      self.sentences = temp
    else:
      temp = []
      for s in tqdm(self.sentences):
        i = 1
        while len(s)//i > self.max_len:
          i += 1
        itl = len(s)//i
        for j in range(i):
          temp.append(s[j*itl:(j+1)*itl])
      self.sentences = temp

  def preproces(self):
    print("Preparing sentences...")
    self.prepare_sentences()
    print("Making sentences...")
    self.make_sentences()
    print("Embedding sentences...")
    self.embed_sentences()
    print("Splitting sentences...")
    self.split_sentences()
    print("Done!")

  def __getitem__(self, idx):
    
    ret_2 = torch.cat([
        torch.stack([t.embedding for t in self.sentences[idx]]),
        torch.zeros(self.max_len - len(self.sentences[idx]), self.embedding_size, device=flair.device)
    ])
    
    if self.augment:
        text = Sentence(self.augment(self.sentences[idx].text))[:self.max_len]
        self.embedding.embed(text)
        ret_1 = torch.cat([
            torch.stack([t.embedding for t in text]),
            torch.zeros(self.max_len - len(text), self.embedding_size, device=flair.device)
        ])
    else:
        ret_1 = ret_2
    
    if self.classes:
        return ret_2, self.classes[idx]
    else:
        return ret_1, ret_2

  def __len__(self):
    return len(self.sentences)

  @staticmethod
  def prep(sentence, tokenizer = RegexpTokenizer(r'\S+'), stop_words=set(stopwords.words('english'))):
    return " ".join([
        word
        for word, tag in nltk.pos_tag(tokenizer.tokenize(sentence))
        if word not in stop_words
    ])