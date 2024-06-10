import os
import re

import pandas as pd
import yaml
from langchain_community.document_loaders import DataFrameLoader, UnstructuredFileLoader, AsyncHtmlLoader, PyPDFLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

config_fname = os.environ.get("APP_CONFIG", "config.yaml")
with open(config_fname, encoding='utf-8') as f:
    OPENAI_API_KEY = yaml.safe_load(f.read())["app"]["openai"]["api_key"]


def similarity_init(path, save_path, chunk_size=1000):
    with open(path, 'r', encoding='utf-8') as f:
        documents = [{"id": 1, "text": f.read()}]

    df = pd.DataFrame(documents)
    loader = DataFrameLoader(df, page_content_column='text')
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    db = FAISS.from_documents(texts, embeddings)
    db.as_retriever()
    db.save_local(save_path)

    # query_result = db.similarity_search_with_score('какие парни тебе нравятся?')

    return db


def is_url(string):
    # Регулярное выражение для проверки URL
    regex = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:[/?#][^\s]*)?$'
    return re.match(regex, string) is not None


class SimilaritySearch:
    def __init__(self, path, save_path, chunk_size=1000, load_path=None, threshold=0.5):

        # with open(path, 'r', encoding='utf-8') as f:
        #     documents = [{"id": 1, "text": f.read()}]
        #
        # df = pd.DataFrame(documents)
        # loader = DataFrameLoader(df, page_content_column='text')
        # documents = loader.load()

        # if path.endswith('.txt'):
        #     with open(path, 'r', encoding='utf-8') as f:
        #         text = f.read()
        #         if text.startswith('http'):
        #             loader = AsyncHtmlLoader(text)
        #             documents = loader.load()

        # loader = UnstructuredFileLoader(path, strategy='fast')
        # documents = loader.load()

        if path.endswith('.txt'):
            with open(path, 'r', encoding='utf-8') as file:
                file_text = file.read()
            if is_url(file_text):  # web scraping
                loader = AsyncHtmlLoader(file_text)
                documents = loader.load()
                html2text = Html2TextTransformer()
                documents = html2text.transform_documents(documents)
            else:  # simple txt files
                documents = [{"id": 1, "text": file_text}]
                df = pd.DataFrame(documents)
                loader = DataFrameLoader(df, page_content_column='text')
                documents = loader.load()
        elif path.endswith('.pdf'):  # pdf files
            loader = PyPDFLoader(path)
            documents = loader.load()
        else:
            raise ValueError("source file must be txt or pdf")

        print(documents)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=0)
        texts = text_splitter.split_documents(documents)
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

        if load_path is not None:
            db = FAISS.load_local(load_path, embeddings, allow_dangerous_deserialization=True)
        else:
            db = FAISS.from_documents(texts, embeddings)
            db.as_retriever()
            db.save_local(save_path)

        self.texts = texts
        self.db = db
        self.threshold = threshold

    def search(self, text, cnt=1, threshold=None):
        if threshold is None:
            threshold = self.threshold
        documents = self.db.similarity_search_with_score(text)
        print('documents: ', documents)
        answer = ''
        i = 0
        while i < len(documents) and i < cnt:
            if documents[i][1] < threshold:
                answer += documents[i][0].page_content
            i += 1
        return answer

    def get_piece(self, idx):
        if idx >= len(self.texts):
            idx = 0
        return self.texts[idx].page_content, idx + 1

    # @classmethod
    # def from_file(cls, load_path):
    #     instance = cls.__new__(cls)
    #     embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    #     instance.db = FAISS.load_local(load_path, embeddings, allow_dangerous_deserialization=True)
    #     return instance


async def setup_legend(app):
    app.Legend = SimilaritySearch('assets/legend_en.txt', 'assets/legend_faiss_index', threshold=0.6)
