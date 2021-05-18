import pandas as pd
import numpy as np
import os
import time
import shutil

import multiprocessing
from collections import Counter

# Cantidad de Cores a ejecutar
n_core = 5

# Lista de Procesos con cada tipo de review
review_process = list()

# Lista con caracteres especiales
_Review__characters = [',', '.', '(', ')', '?', '!', '\"', '-', ':', '/']
_Review__characters.extend([str(i) for i in range(10)])

_Review__top_common = 20

# Lista con las stopword
# stopwords_path = 'stopwords/stop_words_en_nltk.txt'
stopwords_path = 'stopwords/stop_words_en_1298.txt'
# stopwords_path = 'stopwords/stop_words_en_nltk.txt'

_Review__stopwords = list()
with open(stopwords_path) as f:
    lines = f.readlines()
    for line in lines:
        _Review__stopwords.extend([line.replace("\n", "")])

train_csv_path = 'train_csv'
split_csv_path = 'split_csv'
amount_time = [['amount', 'serial_time', 'process_time']]

class Review():

    most_common_word = None

    def __init__(self, dataset):
        self.dataset = dataset
    
    def count_words(self):
        self.most_common_word = list()
        for index, row in self.dataset.iterrows():
            word_string = str(row.iloc[2]).lower()
            for character in __characters:
                word_string = word_string.replace(character, "")

            word_string = word_string.split()
            for w in word_string:
                if w not in __stopwords:
                    self.most_common_word.append(w)
        counter = Counter(self.most_common_word)
        self.most_common_word = counter.most_common(__top_common)
    
    def get_characters(self):
        return __characters

# lista = [review 1, review 2] --> Core 1
# lista = [review 3, review 4, review 5] --> Core 2

class ReviewProcess(multiprocessing.Process):

    def __init__(self, review_list):
        multiprocessing.Process.__init__(self)
        self.review_list = review_list
    
    def run(self):
        for r in self.review_list:
            r.count_words()
        return


def load_review_data(file_path_list):
    global review_process

    review_process = list()
    for f in file_path_list:
        df = read_csv(f)
        review_process.append(Review(df))

def print_review_most_common():
    for r in review_process:
        print(r.most_common_word, '\n')

def start_serial():
    start_time = time.time()
    for r in review_process:
        r.count_words()
    serial_total_time = time.time() - start_time
    print(f'Tiempo Serial: {serial_total_time}')
    print_review_most_common()
    return serial_total_time
    

def start_process():
    review_len = len(review_process)
    start_time = time.time()
    n = int(review_len/n_core)
    start_index = 0
    end_index = n
    review_process_list = list()
    for i in range(n_core):
        if i == n_core - 1:
            end_index = review_len
        r_p = review_process[start_index:end_index]
        review_process_item = ReviewProcess(r_p)
        review_process_item.start()
        review_process_list.append(review_process_item)
        start_index = end_index
        end_index += n

    for r_p in review_process_list:
        r_p.join()
    process_total_time = time.time() - start_time
    print(f'Tiempo por Procesos: {process_total_time}')
    print_review_most_common()
    return process_total_time
    
def split_into_reviews(df):
    review_id = df.iloc[:, 0].values
    review_id = np.unique(review_id)

    if not os.path.exists(split_csv_path):
        os.makedirs(split_csv_path)

    for r_id in review_id:
        data_by_id = df[df.iloc[:, 0] == r_id]
        path = split_csv_path + '/train-' + str(r_id) + '.csv'
        data_by_id.to_csv(path, index=False, header=False)

def read_files_path(root_path, absolute=True):
    file_path = list()
    for f in os.listdir(root_path):
        if absolute:
            path = os.path.abspath(root_path + "/" + f)
        else:
            path = root_path + "/" + f
        file_path.append(path)
    return file_path

def delete_file_path(root_path):
    if os.path.exists(root_path):
        shutil.rmtree(root_path)

def delete_all():
    delete_file_path(train_csv_path)
    delete_file_path(split_csv_path)

def make_sample(train_path, n=0.1, random_state=0):
    if not os.path.exists(train_csv_path):
        os.makedirs(train_csv_path)
    dataframe = pd.read_csv(train_path, header=None)
    dataframe = dataframe.sample(frac=n, random_state=random_state)
    path = train_csv_path + '/train-' + str(n) + '.csv'
    dataframe.to_csv(path, index=False, header=False)
    print(f'Sample [{dataframe.shape[0]}] complete.')
    dataframe = None

def make_sample_step(train_path, step=0.05):
    i = step
    while i <= 1.0:
        make_sample(train_path, i)
        i += step
        i = round(i, 2)

def start():
    train_csv_path_list = read_files_path(train_csv_path)
    for f in train_csv_path_list:
        df = read_csv(f)
        split_into_reviews(df)
        split_review_path_list = read_files_path(split_csv_path)
        load_review_data(split_review_path_list)

        serial_total_time = start_serial()
        process_total_time = start_process()
        
        amount_time.append([df.shape[0], serial_total_time, process_total_time])
        delete_file_path(split_csv_path)
    return amount_time

def read_csv(path):
    return pd.read_csv(path, header=None)