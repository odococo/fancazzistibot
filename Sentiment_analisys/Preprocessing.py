import gc
import os
import time
from multiprocessing import Pool
from os import system

import pandas as pd
from gensim.parsing.preprocessing import strip_punctuation2, strip_tags
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectPercentile
from sklearn.feature_selection import chi2


class Preprocessing():

    def __init__(self):

        # inizializing tfidfVectorizer
        self.vectorizer = TfidfVectorizer(min_df=1, max_df=0.80, sublinear_tf=True, max_features=51000,
                                          strip_accents='unicode', token_pattern=r'\w{1,}',
                                          ngram_range=(1, 2), analyzer="word")

    def spot_differences(self, old, new, what, words):

        i = 0
        j = 0
        ris = ""
        print("difference for: " + what)
        for old_row, new_row in zip(old, new):
            for old_cell, new_cell in zip(old_row, new_row):
                if (old_cell + 0.3 <= new_cell):
                    ris += "difference for cell [" + str(i) + ", " + str(j) + ", " + words[j] + " ]\t" + str(
                        old_cell) + " -> " + str(new_cell) + "\n"

                j += 1
            j = 0
            i += 1
        with open("difference_" + what + ".txt", "w") as file:
            file.write(ris)

    def sentences_polishing(self, words_lst, what, deep_polishing=False):

        # calculating char numers for entire review list
        lst_len_start = sum(len(s) for s in words_lst)
        print("Cleaning for list with " + str(lst_len_start) + " chars, for " + what)

        # deleting html tags
        words_lst = [strip_tags(x) for x in words_lst]

        # deleting punctuation
        words_lst = [strip_punctuation2(x) for x in words_lst]

        if deep_polishing:
            # Initializing pool for multiprocessing
            pool = Pool(processes=10)

            # for every review, apply function and save result
            words_lst = pool.map(self.stopWords, words_lst)
            pool.close()
            pool.join()

        # deleting empty reviews
        words_lst = [x for x in words_lst if x]

        # recalculating list char and printing results
        lst_len_end = sum(len(s) for s in words_lst)
        cleaned = lst_len_start - lst_len_end
        print(
            "Deleted " + str(cleaned) + " (" + str(int(cleaned / lst_len_start * 100)) + "%) chars, for " + what + "\n")

        # freeing memory
        gc.collect()

        return words_lst

    def stopWords(self, review):

        # splitting into words
        words_list = review.split()

        # deleting words with less than 3 chars
        words_list = [x for x in words_list if len(x) > 2]

        # removing stop words
        words_list = [word for word in words_list if word not in stopwords.words('italian')]

        # removing numbers
        words_list = [word for word in words_list if word.isalpha()]

        return " ".join(words_list)

    def polish_tfidf_kbest(self, train_set_labled, train_set_unlabled, test_set):
        # splitting  train test
        xtrainL = train_set_labled["review"]
        xtrainU = train_set_unlabled["review"]
        xtest = test_set["review"]
        ytrain = train_set_labled["sentiment"]

        print("Starting trasformation from string to vector...")

        # transforming to vector
        xtrain_vec, xtest_vec, vect = self.string2vecTFIDF(xtrainL, xtrainU, xtest)

        feature_names = vect.get_feature_names()

        print("Executing chi2 test...")

        reduced_xtrain_vec, reduced_xtest_vec = self.dimensionality_reductionKB(xtrain_vec, ytrain, xtest_vec,
                                                                                         feature_names)
        return reduced_xtrain_vec, reduced_xtest_vec, ytrain, feature_names

    def string2vecTFIDF(self, x_train_str_labled, x_train_str_unlabled, x_test_str):
        print("Vectorizing words")
        start = time.time()

        # cleaning every dataset
        clean_x_trainL = self.sentences_polishing(list(x_train_str_labled), "XtrainLabled")
        clean_x_trainU = self.sentences_polishing(list(x_train_str_unlabled), "XTrainUnlabled")
        clean_x_test = self.sentences_polishing(list(x_test_str), "XTest")

        # fitting train labled and unlabled into tfidf
        self.vectorizer = self.vectorizer.fit(clean_x_trainL + clean_x_trainU)
        # transforming train dataset
        x_train_vec = self.vectorizer.transform(clean_x_trainL).toarray()
        print("Train dataset transformed, created dictionary with " + str(len(self.vectorizer.vocabulary_)) + " words")

        # transforming test dataset
        x_test_vec = self.vectorizer.transform(clean_x_test).toarray()

        # taking time and printing result
        end = time.time()
        tot = end - start

        print("Cleaning and transformation for  test dataset done\nTotal time: " + str(int(tot / 60)) + "' " + str(
            int(tot % 60)) + "''")

        # freeing memory
        gc.collect()

        return x_train_vec, x_test_vec, self.vectorizer

    def dimensionality_reductionKB(self, xtrain, ytrain, xtest, names, percentage=15):
        print("Starting reduction...")
        start = time.time()

        kbest = SelectPercentile(chi2, percentile=percentage)
        new_xtrain = kbest.fit_transform(xtrain, ytrain)
        print("xtrain reduced!")
        new_xtest = kbest.transform(xtest)
        end = time.time()
        tot = end - start

        # spot_differences(xtrain,new_xtrain,"xtrain for chi2",names)

        print("xtest reduced!\nTotal time: " + str(int(tot / 60)) + "' " + str(int(tot % 60)) + "''\n")

        # freeing memory
        gc.collect()

        return new_xtrain, new_xtest

