import math
import pandas as pd

from Sentiment_analisys.Processing import *


class Analyzer:


    def __init__(self, data_list_labled,data_list_unlabled, train_size_perc=0.6):

        size=len(data_list_labled)
        train_size=math.ceil(size*train_size_perc)

        self.TRAIN_SET_LABLED=pd.DataFrame(data_list_labled[:train_size])
        self.TEST_SET=pd.DataFrame(data_list_labled[train_size+1:])
        self.TRAIN_SET_UNLABLED=pd.DataFrame(data_list_unlabled)

        self.svc=None
        self.forest=None
        self.sgdc=None


    def train_models(self):

        self.svc=SVC_classifier(self.TRAIN_SET_LABLED,self.TRAIN_SET_UNLABLED,self.TEST_SET)
        self.sgdc=SGDC(self.TRAIN_SET_LABLED,self.TRAIN_SET_UNLABLED,self.TEST_SET)
        #self.forest=forest_classifier(self.TRAIN_SET_LABLED,self.TRAIN_SET_UNLABLED,self.TEST_SET)


    def predict(self,classifier, text):

        print("predicting")
        text=[{'review':elem['content']} for elem in text]
        text=pd.DataFrame(text)
        xtrain_vec, xtest_vec, ytrain, names=polish_tfidf_kbest(self.TRAIN_SET_LABLED,self.TRAIN_SET_UNLABLED,text)
        pred=classifier.predict(xtest_vec)
        return pred
